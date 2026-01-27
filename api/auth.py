"""
JWT Authentication Module
=========================
JWT token generation, validation, and password hashing.

Author: Loan Analytics Team
Version: 1.0.0
"""

import uuid
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, Tuple

from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel, EmailStr, Field

from .config import get_settings

settings = get_settings()

# Password hashing context
pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto",
    bcrypt__rounds=settings.password_bcrypt_rounds
)


# =============================================================================
# Pydantic Models
# =============================================================================

class TokenPayload(BaseModel):
    """JWT token payload."""
    sub: str  # User ID
    email: str
    role: str
    type: str  # access or refresh
    jti: str  # JWT ID for tracking
    exp: datetime
    iat: datetime
    token_version: Optional[int] = None


class TokenPair(BaseModel):
    """Access and refresh token pair."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds


class UserCreate(BaseModel):
    """User registration data."""
    email: EmailStr
    password: str = Field(..., min_length=8)
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)
    phone: Optional[str] = None


class UserLogin(BaseModel):
    """User login credentials."""
    email: EmailStr
    password: str


class PasswordReset(BaseModel):
    """Password reset data."""
    token: str
    new_password: str = Field(..., min_length=8)


class PasswordChange(BaseModel):
    """Password change data."""
    current_password: str
    new_password: str = Field(..., min_length=8)


# =============================================================================
# Password Utilities
# =============================================================================

def hash_password(password: str) -> str:
    """Hash a password using bcrypt."""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    return pwd_context.verify(plain_password, hashed_password)


def validate_password_strength(password: str) -> Tuple[bool, list]:
    """
    Validate password strength.
    
    Returns:
        Tuple of (is_valid, list of issues)
    """
    issues = []
    
    if len(password) < settings.password_min_length:
        issues.append(f"Password must be at least {settings.password_min_length} characters")
    
    if not any(c.isupper() for c in password):
        issues.append("Password must contain at least one uppercase letter")
    
    if not any(c.islower() for c in password):
        issues.append("Password must contain at least one lowercase letter")
    
    if not any(c.isdigit() for c in password):
        issues.append("Password must contain at least one digit")
    
    if not any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in password):
        issues.append("Password must contain at least one special character")
    
    return len(issues) == 0, issues


# =============================================================================
# JWT Token Utilities
# =============================================================================

def create_access_token(
    user_id: str,
    email: str,
    role: str,
    token_version: int = 1,
    expires_delta: Optional[timedelta] = None
) -> Tuple[str, str, datetime]:
    """
    Create a JWT access token.
    
    Returns:
        Tuple of (token, jti, expiry_datetime)
    """
    jti = str(uuid.uuid4())
    now = datetime.utcnow()
    
    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + timedelta(minutes=settings.jwt_access_token_expire_minutes)
    
    payload = {
        "sub": user_id,
        "email": email,
        "role": role,
        "type": "access",
        "jti": jti,
        "exp": expire,
        "iat": now,
        "token_version": token_version
    }
    
    token = jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)
    return token, jti, expire


def create_refresh_token(
    user_id: str,
    email: str,
    role: str,
    token_version: int = 1,
    expires_delta: Optional[timedelta] = None
) -> Tuple[str, str, datetime]:
    """
    Create a JWT refresh token.
    
    Returns:
        Tuple of (token, jti, expiry_datetime)
    """
    jti = str(uuid.uuid4())
    now = datetime.utcnow()
    
    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + timedelta(days=settings.jwt_refresh_token_expire_days)
    
    payload = {
        "sub": user_id,
        "email": email,
        "role": role,
        "type": "refresh",
        "jti": jti,
        "exp": expire,
        "iat": now,
        "token_version": token_version
    }
    
    token = jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)
    return token, jti, expire


def create_token_pair(
    user_id: str,
    email: str,
    role: str,
    token_version: int = 1
) -> Dict[str, Any]:
    """
    Create both access and refresh tokens.
    
    Returns:
        Dictionary with tokens and metadata
    """
    access_token, access_jti, access_exp = create_access_token(
        user_id, email, role, token_version
    )
    
    refresh_token, refresh_jti, refresh_exp = create_refresh_token(
        user_id, email, role, token_version
    )
    
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "expires_in": settings.jwt_access_token_expire_minutes * 60,
        "access_jti": access_jti,
        "refresh_jti": refresh_jti,
        "access_expires": access_exp,
        "refresh_expires": refresh_exp
    }


def decode_token(token: str) -> Optional[TokenPayload]:
    """
    Decode and validate a JWT token.
    
    Returns:
        TokenPayload if valid, None if invalid
    """
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm]
        )
        
        return TokenPayload(
            sub=payload["sub"],
            email=payload["email"],
            role=payload["role"],
            type=payload["type"],
            jti=payload["jti"],
            exp=datetime.fromtimestamp(payload["exp"]),
            iat=datetime.fromtimestamp(payload["iat"]),
            token_version=payload.get("token_version")
        )
        
    except JWTError:
        return None


def is_token_expired(token: str) -> bool:
    """Check if a token is expired."""
    payload = decode_token(token)
    if not payload:
        return True
    return datetime.utcnow() > payload.exp


def get_token_jti(token: str) -> Optional[str]:
    """Extract JTI from token."""
    payload = decode_token(token)
    return payload.jti if payload else None


# =============================================================================
# Verification Tokens
# =============================================================================

def create_verification_token() -> Tuple[str, datetime]:
    """
    Create an email verification token.
    
    Returns:
        Tuple of (token, expiry_datetime)
    """
    token = str(uuid.uuid4())
    expiry = datetime.utcnow() + timedelta(hours=24)
    return token, expiry


def create_password_reset_token() -> Tuple[str, datetime]:
    """
    Create a password reset token.
    
    Returns:
        Tuple of (token, expiry_datetime)
    """
    token = str(uuid.uuid4())
    expiry = datetime.utcnow() + timedelta(hours=1)
    return token, expiry
