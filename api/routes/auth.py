"""
Authentication Routes
=====================
User registration, login, logout, and token management.

Controllers are thin - only handle:
- Request/response transformation
- HTTP status codes
- Delegating to service layer

No business logic in controllers - validation in schemas.

Author: Loan Analytics Team
Version: 2.0.0
"""

from datetime import datetime, timedelta
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session

from database.models import User, UserRole, UserStatus, UserSession
from api.dependencies import get_db, get_current_user
from api.auth import (
    hash_password, verify_password,
    create_token_pair, decode_token, create_verification_token,
    create_password_reset_token, TokenPayload
)
from api.config import get_settings
from api.schemas import (
    RegisterRequest,
    LoginRequest,
    TokenResponse,
    RefreshRequest,
    PasswordChangeRequest,
    UserResponse,
    MessageResponse
)

settings = get_settings()
router = APIRouter()


# =============================================================================
# Additional Request Schemas (not in centralized schemas yet)
# =============================================================================

from pydantic import BaseModel, EmailStr, Field


class PasswordResetRequest(BaseModel):
    """Password reset request (email)."""
    email: EmailStr


class PasswordResetConfirm(BaseModel):
    """Password reset confirmation."""
    token: str
    new_password: str = Field(..., min_length=8, max_length=128)


# =============================================================================
# Routes
# =============================================================================

@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(
    request: RegisterRequest,
    db: Session = Depends(get_db)
):
    """
    Register a new user account.
    
    Password requirements are validated in the schema:
    - Minimum 8 characters
    - At least one uppercase letter
    - At least one lowercase letter
    - At least one digit
    - At least one special character
    """
    # Check if email exists
    existing = db.query(User).filter(
        User.email == request.email.lower(),
        User.is_deleted == False
    ).first()
    
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered"
        )
    
    # Create verification token
    verification_token, verification_expires = create_verification_token()
    
    # Create user
    user = User(
        email=request.email.lower(),
        password_hash=hash_password(request.password),
        first_name=request.first_name,
        last_name=request.last_name,
        phone=request.phone,
        role=UserRole.APPLICANT,
        status=UserStatus.PENDING_VERIFICATION,
        verification_token=verification_token,
        verification_token_expires=verification_expires
    )
    
    db.add(user)
    db.commit()
    db.refresh(user)
    
    # TODO: Send verification email
    
    return UserResponse(
        id=str(user.id),
        email=user.email,
        first_name=user.first_name,
        last_name=user.last_name,
        full_name=user.full_name,
        phone=user.phone,
        role=user.role.value,
        status=user.status.value,
        email_verified=user.email_verified,
        last_login_at=None,
        created_at=user.created_at.isoformat()
    )


@router.post("/login", response_model=TokenResponse)
async def login(
    request: LoginRequest,
    req: Request,
    db: Session = Depends(get_db)
):
    """
    Login with email and password.
    
    Returns access and refresh tokens.
    """
    # Get user
    user = db.query(User).filter(
        User.email == request.email.lower(),
        User.is_deleted == False
    ).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )
    
    # Check if account is locked
    if user.locked_until and user.locked_until > datetime.utcnow():
        minutes_left = (user.locked_until - datetime.utcnow()).seconds // 60
        raise HTTPException(
            status_code=status.HTTP_423_LOCKED,
            detail=f"Account locked. Try again in {minutes_left} minutes."
        )
    
    # Verify password
    if not verify_password(request.password, user.password_hash):
        # Increment failed attempts
        user.failed_login_attempts += 1
        
        if user.failed_login_attempts >= settings.max_login_attempts:
            user.locked_until = datetime.utcnow() + timedelta(minutes=settings.lockout_minutes)
            db.commit()
            raise HTTPException(
                status_code=status.HTTP_423_LOCKED,
                detail=f"Account locked due to too many failed attempts. Try again in {settings.lockout_minutes} minutes."
            )
        
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )
    
    # Check account status
    if user.status == UserStatus.SUSPENDED:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account suspended. Contact support."
        )
    
    if user.status == UserStatus.INACTIVE:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account inactive. Please activate your account."
        )
    
    # Generate tokens
    token_data = create_token_pair(
        user_id=str(user.id),
        email=user.email,
        role=user.role.value,
        token_version=user.refresh_token_version
    )
    
    # Create session record
    session = UserSession(
        user_id=user.id,
        refresh_token_jti=token_data["refresh_jti"],
        access_token_jti=token_data["access_jti"],
        ip_address=req.client.host if req.client else None,
        user_agent=req.headers.get("User-Agent"),
        expires_at=token_data["refresh_expires"]
    )
    db.add(session)
    
    # Update user login info
    user.last_login_at = datetime.utcnow()
    user.last_login_ip = req.client.host if req.client else None
    user.failed_login_attempts = 0
    user.locked_until = None
    
    # Auto-activate if email not required
    if user.status == UserStatus.PENDING_VERIFICATION:
        user.status = UserStatus.ACTIVE  # In production, require email verification
    
    db.commit()
    
    return TokenResponse(
        access_token=token_data["access_token"],
        refresh_token=token_data["refresh_token"],
        token_type="bearer",
        expires_in=token_data["expires_in"]
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    request: RefreshRequest,
    db: Session = Depends(get_db)
):
    """
    Refresh access token using refresh token.
    """
    # Decode refresh token
    payload = decode_token(request.refresh_token)
    
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token"
        )
    
    if payload.type != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type"
        )
    
    # Check session exists and is not revoked
    session = db.query(UserSession).filter(
        UserSession.refresh_token_jti == payload.jti,
        UserSession.is_active == True,
        UserSession.revoked == False
    ).first()
    
    if not session:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session not found or revoked"
        )
    
    # Get user
    user = db.query(User).filter(
        User.id == UUID(payload.sub),
        User.is_deleted == False
    ).first()
    
    if not user or user.status != UserStatus.ACTIVE:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive"
        )
    
    # Check token version
    if payload.token_version != user.refresh_token_version:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has been invalidated"
        )
    
    # Generate new tokens
    token_data = create_token_pair(
        user_id=str(user.id),
        email=user.email,
        role=user.role.value,
        token_version=user.refresh_token_version
    )
    
    # Update session
    session.refresh_token_jti = token_data["refresh_jti"]
    session.access_token_jti = token_data["access_jti"]
    session.expires_at = token_data["refresh_expires"]
    session.last_used_at = datetime.utcnow()
    
    db.commit()
    
    return TokenResponse(
        access_token=token_data["access_token"],
        refresh_token=token_data["refresh_token"],
        token_type="bearer",
        expires_in=token_data["expires_in"]
    )


@router.post("/logout", response_model=MessageResponse)
async def logout(
    req: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Logout current session.
    
    Revokes the current session.
    """
    # Get token from header
    auth_header = req.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        token = auth_header[7:]
        payload = decode_token(token)
        
        if payload:
            # Revoke the session
            session = db.query(UserSession).filter(
                UserSession.access_token_jti == payload.jti,
                UserSession.user_id == current_user.id
            ).first()
            
            if session:
                session.is_active = False
                session.revoked = True
                session.revoked_at = datetime.utcnow()
                session.revoked_reason = "User logout"
                db.commit()
    
    return MessageResponse(success=True, message="Logged out successfully")


@router.post("/logout-all", response_model=MessageResponse)
async def logout_all_sessions(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Logout from all sessions.
    
    Invalidates all tokens by incrementing token version.
    """
    # Increment token version to invalidate all existing tokens
    current_user.refresh_token_version += 1
    
    # Revoke all sessions
    db.query(UserSession).filter(
        UserSession.user_id == current_user.id,
        UserSession.is_active == True
    ).update({
        "is_active": False,
        "revoked": True,
        "revoked_at": datetime.utcnow(),
        "revoked_reason": "Logout all sessions"
    })
    
    db.commit()
    
    return MessageResponse(success=True, message="Logged out from all sessions")


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: User = Depends(get_current_user)
):
    """Get current user information."""
    return UserResponse(
        id=str(current_user.id),
        email=current_user.email,
        first_name=current_user.first_name,
        last_name=current_user.last_name,
        full_name=current_user.full_name,
        phone=current_user.phone,
        role=current_user.role.value,
        status=current_user.status.value,
        email_verified=current_user.email_verified,
        last_login_at=current_user.last_login_at.isoformat() if current_user.last_login_at else None,
        created_at=current_user.created_at.isoformat()
    )


@router.post("/change-password", response_model=MessageResponse)
async def change_password(
    request: PasswordChangeRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Change password for current user."""
    # Verify current password
    if not verify_password(request.current_password, current_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect"
        )
    
    # Validate new password
    is_valid, issues = validate_password_strength(request.new_password)
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"message": "Password too weak", "issues": issues}
        )
    
    # Update password
    current_user.password_hash = hash_password(request.new_password)
    current_user.password_changed_at = datetime.utcnow()
    current_user.refresh_token_version += 1  # Invalidate all tokens
    
    db.commit()
    
    return MessageResponse(success=True, message="Password changed successfully. Please login again.")


@router.get("/sessions")
async def get_sessions(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all active sessions for current user."""
    sessions = db.query(UserSession).filter(
        UserSession.user_id == current_user.id,
        UserSession.is_active == True,
        UserSession.revoked == False
    ).order_by(UserSession.last_used_at.desc()).all()
    
    return {
        "sessions": [
            {
                "id": str(s.id),
                "device_name": s.device_name,
                "device_type": s.device_type,
                "browser": s.browser,
                "ip_address": s.ip_address,
                "location": s.location,
                "last_used_at": s.last_used_at.isoformat() if s.last_used_at else None,
                "created_at": s.created_at.isoformat()
            }
            for s in sessions
        ]
    }


@router.delete("/sessions/{session_id}", response_model=MessageResponse)
async def revoke_session(
    session_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Revoke a specific session."""
    session = db.query(UserSession).filter(
        UserSession.id == session_id,
        UserSession.user_id == current_user.id
    ).first()
    
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found"
        )
    
    session.is_active = False
    session.revoked = True
    session.revoked_at = datetime.utcnow()
    session.revoked_reason = "User revoked"
    
    db.commit()
    
    return MessageResponse(success=True, message="Session revoked")
