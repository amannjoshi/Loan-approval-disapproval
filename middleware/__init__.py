"""
Middleware Package
==================
Production middleware components for FastAPI.

Features:
- Rate limiting (Token bucket, sliding window)
- Security headers (HSTS, CSP, X-Frame-Options)
- JWT token blacklist
- RBAC (Role-Based Access Control)
- PII redaction in logs
- HTTPS enforcement
- IP filtering

Author: Loan Analytics Team
Version: 2.0.0
"""

from middleware.rate_limiting import (
    RateLimitMiddleware,
    RequestIDMiddleware,
    TimingMiddleware,
    RateLimitConfig,
    EndpointRateLimiter,
    TokenBucketRateLimiter,
    create_rate_limiter_from_config
)

from middleware.security import (
    SecurityHeadersMiddleware,
    HTTPSRedirectMiddleware,
    IPFilterMiddleware,
    SecureLoggingMiddleware,
    RequestValidationMiddleware,
    TokenBlacklist,
    get_token_blacklist,
    RBACMiddleware,
    Permission,
    ROLE_PERMISSIONS,
    require_permission,
    setup_security_middleware
)

__all__ = [
    # Rate Limiting Middleware
    "RateLimitMiddleware",
    "RequestIDMiddleware",
    "TimingMiddleware",
    
    # Rate Limiting Configuration
    "RateLimitConfig",
    "EndpointRateLimiter",
    "TokenBucketRateLimiter",
    "create_rate_limiter_from_config",
    
    # Security Middleware
    "SecurityHeadersMiddleware",
    "HTTPSRedirectMiddleware",
    "IPFilterMiddleware",
    "SecureLoggingMiddleware",
    "RequestValidationMiddleware",
    
    # JWT Token Blacklist
    "TokenBlacklist",
    "get_token_blacklist",
    
    # RBAC
    "RBACMiddleware",
    "Permission",
    "ROLE_PERMISSIONS",
    "require_permission",
    
    # Setup
    "setup_security_middleware"
]
