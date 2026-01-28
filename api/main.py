"""
FastAPI Main Application
========================
Main FastAPI application with middleware, error handling, and routes.

Author: Loan Analytics Team
Version: 1.0.0
"""

import logging
import time
import uuid
from contextlib import asynccontextmanager
from typing import Callable

from fastapi import FastAPI, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from .config import get_settings
from database.connection import init_database, get_db

# Import middleware (optional - graceful fallback)
try:
    from middleware import RateLimitMiddleware, RequestIDMiddleware, TimingMiddleware
    MIDDLEWARE_AVAILABLE = True
except ImportError:
    MIDDLEWARE_AVAILABLE = False

# Import security middleware
try:
    from middleware.security import (
        SecurityHeadersMiddleware,
        HTTPSRedirectMiddleware,
        SecureLoggingMiddleware,
        RequestValidationMiddleware,
        setup_security_middleware
    )
    SECURITY_MIDDLEWARE_AVAILABLE = True
except ImportError:
    SECURITY_MIDDLEWARE_AVAILABLE = False

settings = get_settings()

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level),
    format=settings.log_format
)
logger = logging.getLogger(__name__)


# =============================================================================
# Lifespan Events
# =============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    # Startup
    logger.info("Starting Loan Approval API...")
    
    # Initialize database
    try:
        db = init_database()
        if db.health_check():
            logger.info("✅ Database connected")
        else:
            logger.warning("⚠️ Database health check failed")
    except Exception as e:
        logger.error(f"❌ Database connection failed: {e}")
    
    logger.info(f"🚀 {settings.app_name} v{settings.app_version} started")
    
    yield
    
    # Shutdown
    logger.info("Shutting down...")
    
    try:
        get_db().close()
        logger.info("Database connections closed")
    except Exception:
        pass
    
    logger.info("Shutdown complete")


# =============================================================================
# Application Factory
# =============================================================================

def create_app() -> FastAPI:
    """Create and configure FastAPI application."""
    
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description="REST API for Loan Approval System with XAI capabilities",
        docs_url=settings.docs_url if settings.debug else None,
        redoc_url=settings.redoc_url if settings.debug else None,
        openapi_url="/openapi.json" if settings.debug else None,
        lifespan=lifespan
    )
    
    # Add middleware
    setup_middleware(app)
    
    # Add exception handlers
    setup_exception_handlers(app)
    
    # Include routers
    setup_routes(app)
    
    return app


# =============================================================================
# Middleware
# =============================================================================

def setup_middleware(app: FastAPI):
    """Configure application middleware including security."""
    
    # CORS (configure before security middleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=settings.cors_allow_credentials,
        allow_methods=settings.cors_allow_methods,
        allow_headers=settings.cors_allow_headers,
    )
    
    # Security middleware stack (if available)
    if SECURITY_MIDDLEWARE_AVAILABLE:
        # Secure logging (innermost - no PII in logs)
        app.add_middleware(SecureLoggingMiddleware)
        logger.info("✅ Secure logging middleware enabled (PII redaction active)")
        
        # Request validation (SQL injection, XSS protection)
        app.add_middleware(RequestValidationMiddleware)
        logger.info("✅ Request validation middleware enabled")
        
        # Security headers (HSTS, CSP, X-Frame-Options, etc.)
        app.add_middleware(SecurityHeadersMiddleware)
        logger.info("✅ Security headers middleware enabled")
        
        # HTTPS redirect (production only)
        if settings.environment == "production":
            app.add_middleware(HTTPSRedirectMiddleware)
            logger.info("✅ HTTPS redirect middleware enabled")
    
    # Production middleware (rate limiting)
    if MIDDLEWARE_AVAILABLE and settings.environment == "production":
        # Rate limiting middleware
        app.add_middleware(
            RateLimitMiddleware,
            exclude_paths=["/health", "/ready", "/metrics", "/docs", "/openapi.json"]
        )
        logger.info("✅ Rate limiting middleware enabled")
    
    # Request ID middleware
    @app.middleware("http")
    async def add_request_id(request: Request, call_next: Callable) -> Response:
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        request.state.request_id = request_id
        
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        
        return response
    
    # Timing middleware
    @app.middleware("http")
    async def add_timing(request: Request, call_next: Callable) -> Response:
        start_time = time.time()
        
        response = await call_next(request)
        
        process_time = time.time() - start_time
        response.headers["X-Process-Time"] = f"{process_time:.4f}"
        
        return response
    
    # Logging middleware
    @app.middleware("http")
    async def log_requests(request: Request, call_next: Callable) -> Response:
        # Get request info
        request_id = getattr(request.state, "request_id", "unknown")
        method = request.method
        path = request.url.path
        client_ip = request.client.host if request.client else "unknown"
        
        logger.info(f"[{request_id}] {method} {path} - {client_ip}")
        
        response = await call_next(request)
        
        logger.info(f"[{request_id}] {method} {path} - {response.status_code}")
        
        return response


# =============================================================================
# Exception Handlers
# =============================================================================

def setup_exception_handlers(app: FastAPI):
    """Configure exception handlers."""
    
    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException):
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "success": False,
                "error": {
                    "code": exc.status_code,
                    "message": exc.detail,
                    "type": "http_error"
                },
                "request_id": getattr(request.state, "request_id", None)
            }
        )
    
    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        errors = []
        for error in exc.errors():
            errors.append({
                "field": ".".join(str(loc) for loc in error["loc"]),
                "message": error["msg"],
                "type": error["type"]
            })
        
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "success": False,
                "error": {
                    "code": 422,
                    "message": "Validation error",
                    "type": "validation_error",
                    "details": errors
                },
                "request_id": getattr(request.state, "request_id", None)
            }
        )
    
    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception):
        logger.exception(f"Unhandled exception: {exc}")
        
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "success": False,
                "error": {
                    "code": 500,
                    "message": "Internal server error" if not settings.debug else str(exc),
                    "type": "internal_error"
                },
                "request_id": getattr(request.state, "request_id", None)
            }
        )


# =============================================================================
# Routes
# =============================================================================

def setup_routes(app: FastAPI):
    """Include API routers."""
    
    # Health check endpoint
    @app.get("/health", tags=["Health"])
    async def health_check():
        """Health check endpoint."""
        health = {
            "status": "healthy",
            "version": settings.app_version,
            "environment": settings.environment
        }
        
        # Check database
        try:
            db = get_db()
            if db.health_check():
                health["database"] = "connected"
            else:
                health["database"] = "unhealthy"
        except Exception:
            health["database"] = "disconnected"
        
        return health
    
    @app.get("/", tags=["Root"])
    async def root():
        """API root endpoint."""
        return {
            "name": settings.app_name,
            "version": settings.app_version,
            "docs": f"{settings.docs_url}" if settings.debug else None,
            "health": "/health"
        }
    
    # Import and include routers
    try:
        from .routes import auth_router, applicants_router, applications_router, admin_router, models_router
        from .routes.health import router as health_router
        
        # Health routes (no prefix - available at /health, /ready, /metrics)
        app.include_router(
            health_router,
            tags=["Health"]
        )
        
        app.include_router(
            auth_router,
            prefix=f"{settings.api_prefix}/auth",
            tags=["Authentication"]
        )
        
        app.include_router(
            applicants_router,
            prefix=f"{settings.api_prefix}/applicants",
            tags=["Applicants"]
        )
        
        app.include_router(
            applications_router,
            prefix=f"{settings.api_prefix}/applications",
            tags=["Loan Applications"]
        )
        
        app.include_router(
            admin_router,
            prefix=f"{settings.api_prefix}/admin",
            tags=["Admin"]
        )
        
        app.include_router(
            models_router,
            prefix=f"{settings.api_prefix}/models",
            tags=["Model Management"]
        )
        
        # Import rejection feedback router
        from .routes import rejection_feedback_router
        app.include_router(
            rejection_feedback_router,
            prefix=f"{settings.api_prefix}/rejection",
            tags=["Rejection Feedback & Improvement Suggestions"]
        )
        
    except ImportError as e:
        logger.warning(f"Some routes not available: {e}")


# Create the application instance
app = create_app()


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug,
        log_level=settings.log_level.lower()
    )
