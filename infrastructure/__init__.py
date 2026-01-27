"""
Infrastructure Package
======================
System design components for production deployment.

Components:
- Load Balancer: Traffic distribution across servers
- Scaling: Auto-scaling and cluster coordination
- Health Checks: Server health monitoring

Author: Loan Analytics Team
Version: 1.0.0
"""

from .load_balancer import (
    LoadBalancer,
    ServerInstance,
    ServerStatus,
    LoadBalancingStrategy,
    CircuitBreaker,
    CircuitState,
    RateLimiter,
    DistributedRateLimiter,
    HealthCheckService,
    HealthCheckConfig,
    CircuitBreakerConfig,
    get_load_balancer,
    create_load_balancer_from_config
)

from .scaling import (
    AutoScaler,
    ScalingPolicy,
    ScalingDecision,
    ScalingDirection,
    MetricsCollector,
    MetricType,
    ServiceRegistry,
    ServiceInstance,
    ClusterCoordinator,
    get_service_registry,
    get_cluster_coordinator
)

__all__ = [
    # Load Balancer
    'LoadBalancer',
    'ServerInstance',
    'ServerStatus',
    'LoadBalancingStrategy',
    'CircuitBreaker',
    'CircuitState',
    'RateLimiter',
    'DistributedRateLimiter',
    'HealthCheckService',
    'HealthCheckConfig',
    'CircuitBreakerConfig',
    'get_load_balancer',
    'create_load_balancer_from_config',
    
    # Scaling
    'AutoScaler',
    'ScalingPolicy',
    'ScalingDecision',
    'ScalingDirection',
    'MetricsCollector',
    'MetricType',
    'ServiceRegistry',
    'ServiceInstance',
    'ClusterCoordinator',
    'get_service_registry',
    'get_cluster_coordinator'
]
