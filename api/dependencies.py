"""
FastAPI Dependencies
====================
Dependency injection for database, authentication, and authorization.

Author: Loan Analytics Team
Version: 1.0.0
"""

from typing import Optional, List, Callable
from uuid import UUID
from functools import wraps

from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from database.connection import get_db_session
from database.models import User, UserRole, UserStatus
from api.auth import decode_token, TokenPayload
from api.config import get_settings


settings = get_settings()
security = HTTPBearer(auto_error=False)


# =============================================================================
# Database Dependency
# =============================================================================

def get_db():
    """
    Get database session.
    
    Yields:
        Session: SQLAlchemy session
    """
    db = get_db_session()
    try:
        yield db
    finally:
        db.close()


# =============================================================================
# Authentication Dependencies
# =============================================================================

async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    """
    Get the current authenticated user from JWT token.
    
    Args:
        credentials: HTTP Bearer credentials
        db: Database session
    
    Returns:
        User: Authenticated user
        
    Raises:
        HTTPException: If authentication fails
    """
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    # Decode token
    payload = decode_token(credentials.credentials)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    # Check token type
    if payload.type != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    # Get user from database
    try:
        user_id = UUID(payload.sub)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    user = db.query(User).filter(
        User.id == user_id,
        User.is_deleted == False
    ).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    # Check user status
    if user.status != UserStatus.ACTIVE:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Account is {user.status.value}"
        )
    
    return user


async def get_current_user_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db)
) -> Optional[User]:
    """
    Get the current user if authenticated, None otherwise.
    
    Useful for endpoints that have optional authentication.
    """
    if not credentials:
        return None
    
    try:
        return await get_current_user(credentials, db)
    except HTTPException:
        return None


# =============================================================================
# Authorization Dependencies
# =============================================================================

def require_roles(*allowed_roles: UserRole):
    """
    Create a dependency that requires specific roles.
    
    Args:
        *allowed_roles: Allowed user roles
        
    Returns:
        Callable: Dependency function
    """
    async def role_checker(
        current_user: User = Depends(get_current_user)
    ) -> User:
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions. Required roles: {[r.value for r in allowed_roles]}"
            )
        return current_user
    
    return role_checker


# Predefined role dependencies
require_admin = require_roles(UserRole.ADMIN)
require_manager = require_roles(UserRole.MANAGER)
require_analyst = require_roles(UserRole.ANALYST)
require_manager_or_admin = require_roles(UserRole.MANAGER, UserRole.ADMIN)
require_analyst_or_above = require_roles(UserRole.ANALYST, UserRole.MANAGER, UserRole.ADMIN)


async def require_verified_email(
    current_user: User = Depends(get_current_user)
) -> User:
    """
    Require the user to have a verified email.
    """
    if not current_user.email_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Email verification required"
        )
    return current_user


# =============================================================================
# Request Context Dependencies
# =============================================================================

def get_client_ip(request: Request) -> str:
    """
    Get the client IP address from the request.
    
    Handles X-Forwarded-For header for proxied requests.
    """
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def get_user_agent(request: Request) -> str:
    """
    Get the User-Agent from the request.
    """
    return request.headers.get("User-Agent", "unknown")


# =============================================================================
# Pagination Dependencies
# =============================================================================

class PaginationParams:
    """
    Common pagination parameters.
    """
    def __init__(
        self,
        page: int = 1,
        page_size: int = 20,
        max_page_size: int = 100
    ):
        self.page = max(1, page)
        self.page_size = min(max(1, page_size), max_page_size)
        self.offset = (self.page - 1) * self.page_size


def get_pagination(
    page: int = 1,
    page_size: int = 20
) -> PaginationParams:
    """
    Get pagination parameters.
    """
    return PaginationParams(page=page, page_size=page_size)
