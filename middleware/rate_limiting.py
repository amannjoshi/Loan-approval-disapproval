"""
Rate Limiting Middleware
========================
Production-grade rate limiting for FastAPI.

Features:
- Token bucket algorithm
- Per-client rate limiting
- Sliding window counters
- Configurable limits per endpoint

Author: Loan Analytics Team
Version: 1.0.0
"""

import time
import asyncio
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Dict, Optional, Callable, Awaitable
from datetime import datetime

from fastapi import Request, Response, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware

from api.routes.health import record_request


# =============================================================================
# Rate Limiter Configuration
# =============================================================================

@dataclass
class RateLimitConfig:
    """Rate limit configuration for an endpoint or client."""
    requests_per_second: float = 10.0
    burst_size: int = 20
    window_seconds: int = 60
    max_requests_per_window: int = 100


@dataclass
class ClientState:
    """Track rate limit state for a client."""
    tokens: float = 0.0
    last_update: float = field(default_factory=time.time)
    request_count: int = 0
    window_start: float = field(default_factory=time.time)
    blocked_until: Optional[float] = None


# =============================================================================
# Token Bucket Rate Limiter
# =============================================================================

class TokenBucketRateLimiter:
    """
    Token bucket rate limiter.
    
    Allows bursts of traffic while maintaining average rate limit.
    """
    
    def __init__(self, config: RateLimitConfig):
        self.config = config
        self.clients: Dict[str, ClientState] = {}
        self._lock = asyncio.Lock()
    
    def _get_client_key(self, request: Request) -> str:
        """Get unique client identifier."""
        # Try X-Forwarded-For for clients behind proxy
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        
        # Try X-Real-IP
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip
        
        # Fall back to direct client IP
        if request.client:
            return request.client.host
        
        return "unknown"
    
    async def is_allowed(self, request: Request) -> tuple[bool, dict]:
        """
        Check if request is allowed.
        
        Returns:
            Tuple of (allowed, metadata)
        """
        client_key = self._get_client_key(request)
        current_time = time.time()
        
        async with self._lock:
            # Get or create client state
            if client_key not in self.clients:
                self.clients[client_key] = ClientState(
                    tokens=self.config.burst_size,
                    last_update=current_time
                )
            
            state = self.clients[client_key]
            
            # Check if client is blocked
            if state.blocked_until and current_time < state.blocked_until:
                return False, {
                    "retry_after": int(state.blocked_until - current_time) + 1,
                    "client": client_key
                }
            
            # Refill tokens based on time elapsed
            time_passed = current_time - state.last_update
            new_tokens = time_passed * self.config.requests_per_second
            state.tokens = min(self.config.burst_size, state.tokens + new_tokens)
            state.last_update = current_time
            
            # Check sliding window
            if current_time - state.window_start >= self.config.window_seconds:
                state.window_start = current_time
                state.request_count = 0
            
            # Check window limit
            if state.request_count >= self.config.max_requests_per_window:
                state.blocked_until = state.window_start + self.config.window_seconds
                return False, {
                    "retry_after": int(state.blocked_until - current_time) + 1,
                    "client": client_key,
                    "reason": "window_limit_exceeded"
                }
            
            # Try to consume a token
            if state.tokens >= 1:
                state.tokens -= 1
                state.request_count += 1
                
                return True, {
                    "remaining_tokens": int(state.tokens),
                    "remaining_requests": self.config.max_requests_per_window - state.request_count,
                    "client": client_key
                }
            else:
                # No tokens available
                wait_time = (1 - state.tokens) / self.config.requests_per_second
                return False, {
                    "retry_after": int(wait_time) + 1,
                    "client": client_key,
                    "reason": "rate_limit_exceeded"
                }
    
    async def cleanup_old_clients(self, max_age_seconds: int = 3600):
        """Remove inactive clients from memory."""
        current_time = time.time()
        async with self._lock:
            expired_clients = [
                key for key, state in self.clients.items()
                if current_time - state.last_update > max_age_seconds
            ]
            for key in expired_clients:
                del self.clients[key]


# =============================================================================
# Endpoint-Specific Rate Limits
# =============================================================================

class EndpointRateLimiter:
    """
    Rate limiter with different limits per endpoint pattern.
    """
    
    def __init__(self):
        self.endpoint_configs: Dict[str, RateLimitConfig] = {}
        self.default_config = RateLimitConfig()
        self.limiters: Dict[str, TokenBucketRateLimiter] = {}
    
    def configure_endpoint(self, pattern: str, config: RateLimitConfig):
        """Configure rate limit for endpoint pattern."""
        self.endpoint_configs[pattern] = config
        self.limiters[pattern] = TokenBucketRateLimiter(config)
    
    def _match_endpoint(self, path: str) -> str:
        """Match request path to endpoint pattern."""
        for pattern in self.endpoint_configs:
            if path.startswith(pattern):
                return pattern
        return "default"
    
    async def is_allowed(self, request: Request) -> tuple[bool, dict]:
        """Check if request is allowed."""
        pattern = self._match_endpoint(request.url.path)
        
        if pattern not in self.limiters:
            self.limiters[pattern] = TokenBucketRateLimiter(self.default_config)
        
        return await self.limiters[pattern].is_allowed(request)


# =============================================================================
# Rate Limiting Middleware
# =============================================================================

class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    FastAPI middleware for rate limiting.
    
    Usage:
        app.add_middleware(
            RateLimitMiddleware,
            rate_limiter=rate_limiter,
            exclude_paths=["/health", "/metrics"]
        )
    """
    
    def __init__(
        self,
        app,
        rate_limiter: Optional[EndpointRateLimiter] = None,
        exclude_paths: list[str] = None,
        on_rate_limited: Optional[Callable[[Request, dict], Awaitable[Response]]] = None
    ):
        super().__init__(app)
        self.rate_limiter = rate_limiter or self._create_default_limiter()
        self.exclude_paths = exclude_paths or ["/health", "/ready", "/metrics", "/docs", "/openapi.json"]
        self.on_rate_limited = on_rate_limited
    
    def _create_default_limiter(self) -> EndpointRateLimiter:
        """Create rate limiter with default configuration."""
        limiter = EndpointRateLimiter()
        
        # Configure different limits for different endpoints
        limiter.configure_endpoint("/api/v1/auth", RateLimitConfig(
            requests_per_second=5,
            burst_size=10,
            max_requests_per_window=30
        ))
        
        limiter.configure_endpoint("/api/v1/applications", RateLimitConfig(
            requests_per_second=20,
            burst_size=50,
            max_requests_per_window=500
        ))
        
        limiter.configure_endpoint("/api/v1/predictions", RateLimitConfig(
            requests_per_second=10,
            burst_size=30,
            max_requests_per_window=200
        ))
        
        # Default for other endpoints
        limiter.default_config = RateLimitConfig(
            requests_per_second=50,
            burst_size=100,
            max_requests_per_window=1000
        )
        
        return limiter
    
    async def dispatch(self, request: Request, call_next) -> Response:
        """Process request with rate limiting."""
        start_time = time.time()
        
        # Skip rate limiting for excluded paths
        path = request.url.path
        if any(path.startswith(excluded) for excluded in self.exclude_paths):
            response = await call_next(request)
            duration = time.time() - start_time
            record_request(response.status_code, duration)
            return response
        
        # Check rate limit
        allowed, metadata = await self.rate_limiter.is_allowed(request)
        
        if not allowed:
            # Rate limited
            if self.on_rate_limited:
                return await self.on_rate_limited(request, metadata)
            
            retry_after = metadata.get("retry_after", 60)
            return Response(
                content=f'{{"error": "Rate limit exceeded", "retry_after": {retry_after}}}',
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                headers={
                    "Content-Type": "application/json",
                    "Retry-After": str(retry_after),
                    "X-RateLimit-Reset": str(int(time.time()) + retry_after)
                }
            )
        
        # Process request
        response = await call_next(request)
        
        # Record metrics
        duration = time.time() - start_time
        record_request(response.status_code, duration)
        
        # Add rate limit headers
        response.headers["X-RateLimit-Remaining"] = str(metadata.get("remaining_requests", 0))
        
        return response


# =============================================================================
# Request ID Middleware
# =============================================================================

class RequestIDMiddleware(BaseHTTPMiddleware):
    """
    Add unique request ID to each request for tracing.
    """
    
    async def dispatch(self, request: Request, call_next) -> Response:
        import uuid
        
        # Get existing request ID or generate new one
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        
        # Store in request state
        request.state.request_id = request_id
        
        # Process request
        response = await call_next(request)
        
        # Add request ID to response
        response.headers["X-Request-ID"] = request_id
        
        return response


# =============================================================================
# Timing Middleware
# =============================================================================

class TimingMiddleware(BaseHTTPMiddleware):
    """
    Add request timing headers.
    """
    
    async def dispatch(self, request: Request, call_next) -> Response:
        start_time = time.time()
        
        response = await call_next(request)
        
        # Calculate processing time
        process_time = time.time() - start_time
        
        # Add timing headers
        response.headers["X-Process-Time"] = f"{process_time:.4f}"
        response.headers["X-Response-Time"] = f"{int(process_time * 1000)}ms"
        
        return response


# =============================================================================
# Factory Functions
# =============================================================================

def create_rate_limiter_from_config(config: dict) -> EndpointRateLimiter:
    """
    Create rate limiter from configuration dictionary.
    
    Example config:
    {
        "endpoints": {
            "/api/v1/auth": {
                "requests_per_second": 5,
                "burst_size": 10,
                "max_requests_per_window": 30
            }
        },
        "default": {
            "requests_per_second": 50,
            "burst_size": 100,
            "max_requests_per_window": 1000
        }
    }
    """
    limiter = EndpointRateLimiter()
    
    for pattern, endpoint_config in config.get("endpoints", {}).items():
        limiter.configure_endpoint(pattern, RateLimitConfig(**endpoint_config))
    
    if "default" in config:
        limiter.default_config = RateLimitConfig(**config["default"])
    
    return limiter
