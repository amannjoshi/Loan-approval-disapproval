"""
Health Check & Metrics Endpoints
================================
Production health monitoring endpoints for:
- Load balancer health checks
- Kubernetes readiness/liveness probes
- Prometheus metrics

Author: Loan Analytics Team
Version: 1.0.0
"""

import time
import platform
import psutil
from datetime import datetime
from typing import Dict, Any, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import text
from sqlalchemy.orm import Session

from api.dependencies import get_db
from api.config import get_settings

router = APIRouter(tags=["Health"])

# Track startup time
STARTUP_TIME = datetime.utcnow()


# =============================================================================
# Health Check Models
# =============================================================================

class HealthStatus:
    """Health status constants."""
    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"
    DEGRADED = "degraded"


# =============================================================================
# Health Check Endpoints
# =============================================================================

@router.get("/health")
async def health_check():
    """
    Basic health check endpoint.
    
    Used by:
    - Load balancers (Nginx, HAProxy)
    - Container orchestrators (Docker, Kubernetes)
    - Monitoring systems
    
    Returns 200 if service is running.
    """
    return {
        "status": HealthStatus.HEALTHY,
        "timestamp": datetime.utcnow().isoformat(),
        "service": "loan-approval-api"
    }


@router.get("/health/live")
async def liveness_check():
    """
    Kubernetes liveness probe.
    
    Checks if the application is running.
    Returns 200 if alive, 500 if the process should be restarted.
    """
    return {
        "status": "alive",
        "timestamp": datetime.utcnow().isoformat()
    }


@router.get("/health/ready")
async def readiness_check(db: Session = Depends(get_db)):
    """
    Kubernetes readiness probe.
    
    Checks if the application is ready to receive traffic:
    - Database connection is working
    - Required services are available
    
    Returns 200 if ready, 503 if not ready.
    """
    checks = {}
    overall_status = HealthStatus.HEALTHY
    
    # Check database
    try:
        db.execute(text("SELECT 1"))
        checks["database"] = {
            "status": HealthStatus.HEALTHY,
            "message": "Connected"
        }
    except Exception as e:
        checks["database"] = {
            "status": HealthStatus.UNHEALTHY,
            "message": str(e)
        }
        overall_status = HealthStatus.UNHEALTHY
    
    # If unhealthy, return 503
    if overall_status == HealthStatus.UNHEALTHY:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "status": overall_status,
                "checks": checks,
                "timestamp": datetime.utcnow().isoformat()
            }
        )
    
    return {
        "status": overall_status,
        "checks": checks,
        "timestamp": datetime.utcnow().isoformat()
    }


@router.get("/health/detailed")
async def detailed_health_check(db: Session = Depends(get_db)):
    """
    Detailed health check with system metrics.
    
    Used for debugging and monitoring dashboards.
    Includes:
    - Service status
    - Database connectivity
    - System resources (CPU, memory)
    - Uptime information
    """
    settings = get_settings()
    checks = {}
    overall_status = HealthStatus.HEALTHY
    
    # Database check
    try:
        start = time.time()
        db.execute(text("SELECT 1"))
        db_latency = (time.time() - start) * 1000
        
        checks["database"] = {
            "status": HealthStatus.HEALTHY,
            "latency_ms": round(db_latency, 2)
        }
        
        if db_latency > 100:  # Slow query warning
            checks["database"]["status"] = HealthStatus.DEGRADED
            overall_status = HealthStatus.DEGRADED
            
    except Exception as e:
        checks["database"] = {
            "status": HealthStatus.UNHEALTHY,
            "error": str(e)
        }
        overall_status = HealthStatus.UNHEALTHY
    
    # System resources
    try:
        cpu_percent = psutil.cpu_percent(interval=0.1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        checks["system"] = {
            "status": HealthStatus.HEALTHY,
            "cpu_percent": cpu_percent,
            "memory_percent": memory.percent,
            "memory_available_mb": round(memory.available / 1024 / 1024, 2),
            "disk_percent": disk.percent,
            "disk_free_gb": round(disk.free / 1024 / 1024 / 1024, 2)
        }
        
        # Check thresholds
        if cpu_percent > 90 or memory.percent > 90:
            checks["system"]["status"] = HealthStatus.DEGRADED
            if overall_status == HealthStatus.HEALTHY:
                overall_status = HealthStatus.DEGRADED
                
    except Exception as e:
        checks["system"] = {
            "status": HealthStatus.DEGRADED,
            "error": str(e)
        }
    
    # Calculate uptime
    uptime = datetime.utcnow() - STARTUP_TIME
    
    return {
        "status": overall_status,
        "service": {
            "name": settings.app_name,
            "version": settings.app_version,
            "environment": settings.environment,
            "uptime_seconds": int(uptime.total_seconds()),
            "started_at": STARTUP_TIME.isoformat()
        },
        "host": {
            "hostname": platform.node(),
            "platform": platform.system(),
            "python_version": platform.python_version()
        },
        "checks": checks,
        "timestamp": datetime.utcnow().isoformat()
    }


# =============================================================================
# Metrics Endpoint (Prometheus format)
# =============================================================================

# Simple in-memory metrics (for demo - use prometheus_client in production)
_metrics: Dict[str, Any] = {
    "requests_total": 0,
    "requests_by_status": {},
    "request_duration_seconds": [],
    "active_connections": 0
}


def record_request(status_code: int, duration: float):
    """Record a request for metrics."""
    _metrics["requests_total"] += 1
    _metrics["requests_by_status"][status_code] = _metrics["requests_by_status"].get(status_code, 0) + 1
    
    # Keep last 1000 durations for percentile calculation
    _metrics["request_duration_seconds"].append(duration)
    if len(_metrics["request_duration_seconds"]) > 1000:
        _metrics["request_duration_seconds"] = _metrics["request_duration_seconds"][-1000:]


@router.get("/metrics")
async def prometheus_metrics():
    """
    Prometheus-compatible metrics endpoint.
    
    Returns metrics in Prometheus text format.
    """
    import statistics
    
    settings = get_settings()
    lines = []
    
    # Help and type declarations
    lines.append("# HELP loan_api_requests_total Total number of requests")
    lines.append("# TYPE loan_api_requests_total counter")
    lines.append(f'loan_api_requests_total {_metrics["requests_total"]}')
    
    # Requests by status
    lines.append("# HELP loan_api_requests_by_status Requests by HTTP status code")
    lines.append("# TYPE loan_api_requests_by_status counter")
    for status_code, count in _metrics["requests_by_status"].items():
        lines.append(f'loan_api_requests_by_status{{status="{status_code}"}} {count}')
    
    # Request duration
    if _metrics["request_duration_seconds"]:
        durations = _metrics["request_duration_seconds"]
        lines.append("# HELP loan_api_request_duration_seconds Request duration in seconds")
        lines.append("# TYPE loan_api_request_duration_seconds summary")
        lines.append(f'loan_api_request_duration_seconds{{quantile="0.5"}} {statistics.median(durations):.6f}')
        lines.append(f'loan_api_request_duration_seconds{{quantile="0.9"}} {sorted(durations)[int(len(durations) * 0.9)]:.6f}')
        lines.append(f'loan_api_request_duration_seconds{{quantile="0.99"}} {sorted(durations)[int(len(durations) * 0.99)]:.6f}')
        lines.append(f'loan_api_request_duration_seconds_sum {sum(durations):.6f}')
        lines.append(f'loan_api_request_duration_seconds_count {len(durations)}')
    
    # System metrics
    try:
        cpu = psutil.cpu_percent()
        memory = psutil.virtual_memory()
        
        lines.append("# HELP loan_api_cpu_percent CPU usage percentage")
        lines.append("# TYPE loan_api_cpu_percent gauge")
        lines.append(f"loan_api_cpu_percent {cpu}")
        
        lines.append("# HELP loan_api_memory_percent Memory usage percentage")
        lines.append("# TYPE loan_api_memory_percent gauge")
        lines.append(f"loan_api_memory_percent {memory.percent}")
        
        lines.append("# HELP loan_api_memory_bytes Memory usage in bytes")
        lines.append("# TYPE loan_api_memory_bytes gauge")
        lines.append(f"loan_api_memory_bytes {memory.used}")
    except:
        pass
    
    # Uptime
    uptime = (datetime.utcnow() - STARTUP_TIME).total_seconds()
    lines.append("# HELP loan_api_uptime_seconds Service uptime in seconds")
    lines.append("# TYPE loan_api_uptime_seconds counter")
    lines.append(f"loan_api_uptime_seconds {uptime:.0f}")
    
    # App info
    lines.append("# HELP loan_api_info Application information")
    lines.append("# TYPE loan_api_info gauge")
    lines.append(f'loan_api_info{{version="{settings.app_version}",environment="{settings.environment}"}} 1')
    
    return "\n".join(lines) + "\n"


# =============================================================================
# Ready endpoint alias
# =============================================================================

@router.get("/ready")
async def ready(db: Session = Depends(get_db)):
    """Alias for readiness check (commonly used path)."""
    return await readiness_check(db)
