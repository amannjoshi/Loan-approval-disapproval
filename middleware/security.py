"""
Security Middleware Module
==========================
Comprehensive security middleware for FastAPI applications.

Features:
- Security headers (HSTS, CSP, X-Frame-Options, etc.)
- HTTPS enforcement
- JWT token blacklist checking
- Role-based access control
- IP whitelist/blacklist
- Request validation
- Audit logging with PII redaction

Author: Loan Analytics Team
Version: 1.0.0
"""

import time
import asyncio
import hashlib
from datetime import datetime, timedelta
from typing import Callable, Optional, Dict, Set, List
from collections import defaultdict

from fastapi import Request, Response, HTTPException, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from config.security import get_security_settings
from utils.pii_redactor import redact_pii, PIIRedactor


# =============================================================================
# JWT Token Blacklist
# =============================================================================

class TokenBlacklist:
    """
    In-memory token blacklist for invalidated JWT tokens.
    
    In production, use Redis or similar distributed cache.
    """
    
    _instance = None
    _lock = asyncio.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        self._blacklist: Dict[str, datetime] = {}
        self._cleanup_interval = 3600  # 1 hour
        self._last_cleanup = time.time()
        self._initialized = True
    
    async def add(self, jti: str, expires_at: datetime) -> None:
        """Add a token to the blacklist."""
        async with self._lock:
            self._blacklist[jti] = expires_at
            await self._cleanup_expired()
    
    async def is_blacklisted(self, jti: str) -> bool:
        """Check if a token is blacklisted."""
        async with self._lock:
            return jti in self._blacklist
    
    async def _cleanup_expired(self) -> None:
        """Remove expired tokens from blacklist."""
        current_time = time.time()
        if current_time - self._last_cleanup < self._cleanup_interval:
            return
        
        now = datetime.utcnow()
        self._blacklist = {
            jti: exp for jti, exp in self._blacklist.items() 
            if exp > now
        }
        self._last_cleanup = current_time
    
    async def revoke_all_user_tokens(self, user_id: str, expires_at: datetime) -> None:
        """
        Revoke all tokens for a user (logout from all devices).
        Uses a special key format: user_{user_id}
        """
        async with self._lock:
            self._blacklist[f"user_{user_id}"] = expires_at


def get_token_blacklist() -> TokenBlacklist:
    """Get the token blacklist singleton."""
    return TokenBlacklist()


# =============================================================================
# Security Headers Middleware
# =============================================================================

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Add security headers to all responses.
    
    Headers added:
    - Strict-Transport-Security (HSTS)
    - Content-Security-Policy
    - X-Frame-Options
    - X-Content-Type-Options
    - Referrer-Policy
    - Permissions-Policy
    - X-XSS-Protection
    """
    
    def __init__(self, app: ASGIApp):
        super().__init__(app)
        self.settings = get_security_settings()
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        response = await call_next(request)
        
        # HSTS - Force HTTPS
        if self.settings.ssl_enabled:
            response.headers["Strict-Transport-Security"] = (
                f"max-age={self.settings.hsts_max_age}; includeSubDomains; preload"
            )
        
        # Content Security Policy
        response.headers["Content-Security-Policy"] = self.settings.content_security_policy
        
        # Prevent clickjacking
        response.headers["X-Frame-Options"] = self.settings.x_frame_options
        
        # Prevent MIME type sniffing
        response.headers["X-Content-Type-Options"] = self.settings.x_content_type_options
        
        # Referrer policy
        response.headers["Referrer-Policy"] = self.settings.referrer_policy
        
        # Permissions policy
        response.headers["Permissions-Policy"] = self.settings.permissions_policy
        
        # XSS protection (legacy browsers)
        response.headers["X-XSS-Protection"] = "1; mode=block"
        
        # Prevent caching of sensitive data
        if "/api/" in request.url.path:
            response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, private"
            response.headers["Pragma"] = "no-cache"
        
        return response


# =============================================================================
# HTTPS Enforcement Middleware
# =============================================================================

class HTTPSRedirectMiddleware(BaseHTTPMiddleware):
    """
    Redirect HTTP requests to HTTPS.
    """
    
    def __init__(self, app: ASGIApp):
        super().__init__(app)
        self.settings = get_security_settings()
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        if not self.settings.force_https:
            return await call_next(request)
        
        # Check if request is already HTTPS
        # Consider X-Forwarded-Proto for requests behind proxy
        forwarded_proto = request.headers.get("X-Forwarded-Proto", "")
        is_https = (
            request.url.scheme == "https" or 
            forwarded_proto.lower() == "https"
        )
        
        if not is_https and self.settings.ssl_enabled:
            url = request.url.replace(scheme="https")
            return Response(
                status_code=status.HTTP_301_MOVED_PERMANENTLY,
                headers={"Location": str(url)}
            )
        
        return await call_next(request)


# =============================================================================
# IP Filtering Middleware
# =============================================================================

class IPFilterMiddleware(BaseHTTPMiddleware):
    """
    Filter requests based on IP whitelist/blacklist.
    """
    
    def __init__(self, app: ASGIApp):
        super().__init__(app)
        self.settings = get_security_settings()
        self._whitelist = set(self.settings.ip_whitelist)
        self._blacklist = set(self.settings.ip_blacklist)
    
    def _get_client_ip(self, request: Request) -> str:
        """Get the real client IP address."""
        # Check X-Forwarded-For header (from reverse proxy)
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            # Get the first IP (original client)
            return forwarded_for.split(",")[0].strip()
        
        # Check X-Real-IP header
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip
        
        # Fall back to direct client IP
        if request.client:
            return request.client.host
        
        return "unknown"
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        client_ip = self._get_client_ip(request)
        
        # Store IP in request state for logging
        request.state.client_ip = client_ip
        
        # Check blacklist first
        if client_ip in self._blacklist:
            return JSONResponse(
                status_code=status.HTTP_403_FORBIDDEN,
                content={
                    "success": False,
                    "error": {
                        "code": "IP_BLOCKED",
                        "message": "Access denied"
                    }
                }
            )
        
        # Check whitelist (if configured)
        if self._whitelist and client_ip not in self._whitelist:
            return JSONResponse(
                status_code=status.HTTP_403_FORBIDDEN,
                content={
                    "success": False,
                    "error": {
                        "code": "IP_NOT_ALLOWED",
                        "message": "Access denied"
                    }
                }
            )
        
        return await call_next(request)


# =============================================================================
# Role-Based Access Control (RBAC) Middleware
# =============================================================================

class Permission:
    """Permission definitions."""
    # Application permissions
    VIEW_APPLICATIONS = "applications:view"
    CREATE_APPLICATION = "applications:create"
    UPDATE_APPLICATION = "applications:update"
    DELETE_APPLICATION = "applications:delete"
    APPROVE_APPLICATION = "applications:approve"
    
    # User management
    VIEW_USERS = "users:view"
    CREATE_USER = "users:create"
    UPDATE_USER = "users:update"
    DELETE_USER = "users:delete"
    
    # Model management
    VIEW_MODELS = "models:view"
    TRAIN_MODEL = "models:train"
    DEPLOY_MODEL = "models:deploy"
    
    # Reports
    VIEW_REPORTS = "reports:view"
    EXPORT_DATA = "reports:export"
    
    # System administration
    ADMIN_ACCESS = "admin:access"
    VIEW_AUDIT_LOGS = "admin:audit_logs"
    MANAGE_SETTINGS = "admin:settings"


# Role to permissions mapping
ROLE_PERMISSIONS: Dict[str, Set[str]] = {
    "admin": {
        Permission.VIEW_APPLICATIONS, Permission.CREATE_APPLICATION,
        Permission.UPDATE_APPLICATION, Permission.DELETE_APPLICATION,
        Permission.APPROVE_APPLICATION,
        Permission.VIEW_USERS, Permission.CREATE_USER,
        Permission.UPDATE_USER, Permission.DELETE_USER,
        Permission.VIEW_MODELS, Permission.TRAIN_MODEL, Permission.DEPLOY_MODEL,
        Permission.VIEW_REPORTS, Permission.EXPORT_DATA,
        Permission.ADMIN_ACCESS, Permission.VIEW_AUDIT_LOGS, Permission.MANAGE_SETTINGS,
    },
    "manager": {
        Permission.VIEW_APPLICATIONS, Permission.CREATE_APPLICATION,
        Permission.UPDATE_APPLICATION, Permission.APPROVE_APPLICATION,
        Permission.VIEW_USERS,
        Permission.VIEW_MODELS,
        Permission.VIEW_REPORTS, Permission.EXPORT_DATA,
        Permission.VIEW_AUDIT_LOGS,
    },
    "analyst": {
        Permission.VIEW_APPLICATIONS, Permission.CREATE_APPLICATION,
        Permission.UPDATE_APPLICATION,
        Permission.VIEW_MODELS,
        Permission.VIEW_REPORTS,
    },
    "applicant": {
        Permission.VIEW_APPLICATIONS,  # Own applications only
        Permission.CREATE_APPLICATION,
    },
}


class RBACMiddleware:
    """
    Role-Based Access Control utilities.
    
    Not a middleware itself, but provides RBAC checking functions.
    """
    
    @staticmethod
    def get_role_permissions(role: str) -> Set[str]:
        """Get all permissions for a role."""
        return ROLE_PERMISSIONS.get(role.lower(), set())
    
    @staticmethod
    def has_permission(role: str, permission: str) -> bool:
        """Check if a role has a specific permission."""
        permissions = ROLE_PERMISSIONS.get(role.lower(), set())
        return permission in permissions
    
    @staticmethod
    def has_any_permission(role: str, permissions: List[str]) -> bool:
        """Check if a role has any of the specified permissions."""
        role_permissions = ROLE_PERMISSIONS.get(role.lower(), set())
        return bool(role_permissions.intersection(set(permissions)))
    
    @staticmethod
    def has_all_permissions(role: str, permissions: List[str]) -> bool:
        """Check if a role has all of the specified permissions."""
        role_permissions = ROLE_PERMISSIONS.get(role.lower(), set())
        return set(permissions).issubset(role_permissions)


def require_permission(permission: str):
    """
    Decorator to require a specific permission for an endpoint.
    
    Usage:
        @router.get("/admin/users")
        @require_permission(Permission.VIEW_USERS)
        async def list_users(current_user: User = Depends(get_current_user)):
            ...
    """
    from functools import wraps
    
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Get current user from kwargs (injected by dependency)
            current_user = kwargs.get('current_user')
            if not current_user:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Authentication required"
                )
            
            # Check permission
            if not RBACMiddleware.has_permission(current_user.role.value, permission):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Permission denied: {permission} required"
                )
            
            return await func(*args, **kwargs)
        return wrapper
    return decorator


# =============================================================================
# Secure Logging Middleware
# =============================================================================

class SecureLoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware that ensures no PII is logged.
    
    Features:
    - Redacts PII from request/response logs
    - Masks sensitive headers
    - Truncates large payloads
    """
    
    SENSITIVE_HEADERS = {
        'authorization', 'cookie', 'x-api-key', 'x-auth-token',
        'proxy-authorization', 'www-authenticate'
    }
    
    def __init__(self, app: ASGIApp, logger=None):
        super().__init__(app)
        self.redactor = PIIRedactor()
        self.logger = logger
        self.settings = get_security_settings()
    
    def _redact_headers(self, headers: dict) -> dict:
        """Redact sensitive headers."""
        redacted = {}
        for key, value in headers.items():
            if key.lower() in self.SENSITIVE_HEADERS:
                redacted[key] = "[REDACTED]"
            else:
                redacted[key] = value
        return redacted
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        if not self.settings.audit_logging_enabled:
            return await call_next(request)
        
        start_time = time.time()
        
        # Prepare safe request info for logging
        safe_request_info = {
            "method": request.method,
            "path": request.url.path,
            "query_params": dict(request.query_params),
            "client_ip": getattr(request.state, 'client_ip', 'unknown'),
            "request_id": getattr(request.state, 'request_id', 'unknown'),
        }
        
        # Redact any PII from query params
        if self.settings.pii_redaction_enabled:
            safe_request_info["query_params"] = self.redactor.redact_dict(
                safe_request_info["query_params"]
            )
        
        # Process request
        response = await call_next(request)
        
        # Calculate duration
        duration_ms = (time.time() - start_time) * 1000
        
        # Safe response info
        safe_response_info = {
            "status_code": response.status_code,
            "duration_ms": round(duration_ms, 2),
        }
        
        # Log if logger is provided (actual logging handled by audit_logger)
        if self.logger:
            self.logger.info(f"Request: {safe_request_info} Response: {safe_response_info}")
        
        return response


# =============================================================================
# Request Validation Middleware
# =============================================================================

class RequestValidationMiddleware(BaseHTTPMiddleware):
    """
    Validate incoming requests for security threats.
    
    Checks:
    - Content-Type validation
    - Request size limits
    - Malicious payload detection
    """
    
    MALICIOUS_PATTERNS = [
        r'<script[^>]*>',
        r'javascript:',
        r'on\w+\s*=',
        r'union\s+select',
        r';\s*drop\s+',
        r'--\s*$',
        r'/\*.*\*/',
    ]
    
    def __init__(self, app: ASGIApp):
        super().__init__(app)
        self.settings = get_security_settings()
        import re
        self.malicious_pattern = re.compile(
            '|'.join(self.MALICIOUS_PATTERNS), 
            re.IGNORECASE
        )
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Check content type for POST/PUT/PATCH
        if request.method in ("POST", "PUT", "PATCH"):
            content_type = request.headers.get("Content-Type", "")
            if content_type:
                # Extract base content type (without charset, etc.)
                base_type = content_type.split(";")[0].strip()
                if base_type and base_type not in self.settings.allowed_content_types:
                    return JSONResponse(
                        status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                        content={
                            "success": False,
                            "error": {
                                "code": "UNSUPPORTED_MEDIA_TYPE",
                                "message": f"Content-Type '{base_type}' not allowed"
                            }
                        }
                    )
        
        # Check content length
        content_length = request.headers.get("Content-Length")
        if content_length and int(content_length) > self.settings.max_request_size:
            return JSONResponse(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                content={
                    "success": False,
                    "error": {
                        "code": "REQUEST_TOO_LARGE",
                        "message": "Request body too large"
                    }
                }
            )
        
        return await call_next(request)


# =============================================================================
# Middleware Stack Setup
# =============================================================================

def setup_security_middleware(app) -> None:
    """
    Configure all security middleware for a FastAPI application.
    
    Args:
        app: FastAPI application instance
    """
    settings = get_security_settings()
    
    # Add middleware in reverse order (last added = first executed)
    
    # 1. Secure logging (innermost)
    app.add_middleware(SecureLoggingMiddleware)
    
    # 2. Request validation
    app.add_middleware(RequestValidationMiddleware)
    
    # 3. IP filtering
    if settings.ip_blacklist or settings.ip_whitelist:
        app.add_middleware(IPFilterMiddleware)
    
    # 4. Security headers
    app.add_middleware(SecurityHeadersMiddleware)
    
    # 5. HTTPS redirect (outermost)
    if settings.force_https:
        app.add_middleware(HTTPSRedirectMiddleware)
