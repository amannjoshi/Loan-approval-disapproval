"""
Horizontal Scaling Configuration
================================
Auto-scaling, container orchestration, and cluster management.

System Design Concepts:
- Horizontal Pod Autoscaler (HPA) patterns
- Service discovery
- Cluster coordination
- Auto-scaling policies

Author: Loan Analytics Team
Version: 1.0.0
"""

import os
import time
import logging
import threading
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Any, Callable
from collections import deque
import statistics

logger = logging.getLogger(__name__)


# =============================================================================
# Enums
# =============================================================================

class ScalingDirection(str, Enum):
    """Scaling direction."""
    UP = "scale_up"
    DOWN = "scale_down"
    NONE = "no_change"


class MetricType(str, Enum):
    """Types of metrics for scaling decisions."""
    CPU = "cpu"
    MEMORY = "memory"
    REQUEST_RATE = "request_rate"
    LATENCY = "latency"
    QUEUE_LENGTH = "queue_length"
    CONNECTIONS = "connections"
    CUSTOM = "custom"


# =============================================================================
# Data Classes
# =============================================================================

@dataclass
class ScalingPolicy:
    """Auto-scaling policy configuration."""
    min_replicas: int = 1
    max_replicas: int = 10
    target_cpu_percent: float = 70.0
    target_memory_percent: float = 80.0
    target_latency_ms: float = 500.0
    target_requests_per_second: float = 100.0
    scale_up_cooldown_seconds: int = 60
    scale_down_cooldown_seconds: int = 300
    scale_up_increment: int = 1
    scale_down_increment: int = 1


@dataclass
class MetricSample:
    """A single metric measurement."""
    metric_type: MetricType
    value: float
    timestamp: datetime = field(default_factory=datetime.utcnow)
    labels: Dict[str, str] = field(default_factory=dict)


@dataclass
class ScalingDecision:
    """Result of scaling evaluation."""
    direction: ScalingDirection
    current_replicas: int
    desired_replicas: int
    reason: str
    metrics: Dict[str, float]
    timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass
class ServiceInstance:
    """Represents a service instance in the cluster."""
    instance_id: str
    host: str
    port: int
    version: str
    started_at: datetime
    metadata: Dict[str, Any] = field(default_factory=dict)
    last_heartbeat: datetime = field(default_factory=datetime.utcnow)
    
    @property
    def is_healthy(self) -> bool:
        """Check if instance is healthy based on heartbeat."""
        age = (datetime.utcnow() - self.last_heartbeat).total_seconds()
        return age < 30  # 30 second timeout


# =============================================================================
# Metrics Collector
# =============================================================================

class MetricsCollector:
    """
    Collects and aggregates metrics for scaling decisions.
    
    Uses sliding window for smooth metric averaging.
    """
    
    def __init__(self, window_seconds: int = 60):
        self.window_seconds = window_seconds
        self.metrics: Dict[MetricType, deque] = {
            mt: deque() for mt in MetricType
        }
        self._lock = threading.Lock()
    
    def record(self, metric_type: MetricType, value: float):
        """Record a metric value."""
        with self._lock:
            sample = MetricSample(metric_type=metric_type, value=value)
            self.metrics[metric_type].append(sample)
            self._cleanup(metric_type)
    
    def _cleanup(self, metric_type: MetricType):
        """Remove old samples outside the window."""
        cutoff = datetime.utcnow() - timedelta(seconds=self.window_seconds)
        while (
            self.metrics[metric_type] and
            self.metrics[metric_type][0].timestamp < cutoff
        ):
            self.metrics[metric_type].popleft()
    
    def get_average(self, metric_type: MetricType) -> Optional[float]:
        """Get average value for metric type."""
        with self._lock:
            self._cleanup(metric_type)
            samples = self.metrics[metric_type]
            if not samples:
                return None
            return statistics.mean(s.value for s in samples)
    
    def get_percentile(
        self,
        metric_type: MetricType,
        percentile: float
    ) -> Optional[float]:
        """Get percentile value for metric type."""
        with self._lock:
            self._cleanup(metric_type)
            samples = self.metrics[metric_type]
            if not samples:
                return None
            values = sorted(s.value for s in samples)
            index = int(len(values) * percentile / 100)
            return values[min(index, len(values) - 1)]
    
    def get_all_averages(self) -> Dict[str, float]:
        """Get averages for all metric types."""
        return {
            mt.value: self.get_average(mt) or 0.0
            for mt in MetricType
        }


# =============================================================================
# Auto-Scaler
# =============================================================================

class AutoScaler:
    """
    Horizontal Pod Autoscaler (HPA) pattern implementation.
    
    Monitors metrics and makes scaling decisions based on policy.
    """
    
    def __init__(
        self,
        policy: ScalingPolicy,
        metrics_collector: Optional[MetricsCollector] = None,
        scale_callback: Optional[Callable[[int], None]] = None
    ):
        self.policy = policy
        self.metrics = metrics_collector or MetricsCollector()
        self.scale_callback = scale_callback
        
        self.current_replicas = policy.min_replicas
        self.last_scale_up: Optional[datetime] = None
        self.last_scale_down: Optional[datetime] = None
        self.decision_history: deque = deque(maxlen=100)
        
        self._running = False
        self._thread: Optional[threading.Thread] = None
    
    def start(self, interval_seconds: int = 15):
        """Start auto-scaling loop."""
        self._running = True
        self._thread = threading.Thread(
            target=self._scaling_loop,
            args=(interval_seconds,),
            daemon=True
        )
        self._thread.start()
        logger.info("Auto-scaler started")
    
    def stop(self):
        """Stop auto-scaling loop."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)
        logger.info("Auto-scaler stopped")
    
    def _scaling_loop(self, interval: int):
        """Main scaling decision loop."""
        while self._running:
            try:
                decision = self.evaluate()
                self.decision_history.append(decision)
                
                if decision.direction != ScalingDirection.NONE:
                    self._apply_scaling(decision)
                
            except Exception as e:
                logger.error(f"Auto-scaler error: {e}")
            
            time.sleep(interval)
    
    def evaluate(self) -> ScalingDecision:
        """Evaluate current metrics and make scaling decision."""
        metrics = self.metrics.get_all_averages()
        
        # Check CPU
        cpu = metrics.get(MetricType.CPU.value, 0)
        if cpu > self.policy.target_cpu_percent:
            return self._create_scale_up_decision(
                f"CPU {cpu:.1f}% exceeds target {self.policy.target_cpu_percent}%",
                metrics
            )
        
        # Check Memory
        memory = metrics.get(MetricType.MEMORY.value, 0)
        if memory > self.policy.target_memory_percent:
            return self._create_scale_up_decision(
                f"Memory {memory:.1f}% exceeds target {self.policy.target_memory_percent}%",
                metrics
            )
        
        # Check Latency (P95)
        latency = self.metrics.get_percentile(MetricType.LATENCY, 95)
        if latency and latency > self.policy.target_latency_ms:
            return self._create_scale_up_decision(
                f"P95 latency {latency:.0f}ms exceeds target {self.policy.target_latency_ms}ms",
                metrics
            )
        
        # Check for scale down opportunity
        if (
            cpu < self.policy.target_cpu_percent * 0.5 and
            memory < self.policy.target_memory_percent * 0.5 and
            self.current_replicas > self.policy.min_replicas
        ):
            return self._create_scale_down_decision(
                f"Resources under-utilized (CPU: {cpu:.1f}%, Memory: {memory:.1f}%)",
                metrics
            )
        
        return ScalingDecision(
            direction=ScalingDirection.NONE,
            current_replicas=self.current_replicas,
            desired_replicas=self.current_replicas,
            reason="Metrics within target range",
            metrics=metrics
        )
    
    def _create_scale_up_decision(
        self,
        reason: str,
        metrics: Dict[str, float]
    ) -> ScalingDecision:
        """Create scale up decision if cooldown allows."""
        if self.last_scale_up:
            elapsed = (datetime.utcnow() - self.last_scale_up).total_seconds()
            if elapsed < self.policy.scale_up_cooldown_seconds:
                return ScalingDecision(
                    direction=ScalingDirection.NONE,
                    current_replicas=self.current_replicas,
                    desired_replicas=self.current_replicas,
                    reason=f"Scale up cooldown ({int(self.policy.scale_up_cooldown_seconds - elapsed)}s remaining)",
                    metrics=metrics
                )
        
        desired = min(
            self.current_replicas + self.policy.scale_up_increment,
            self.policy.max_replicas
        )
        
        if desired == self.current_replicas:
            return ScalingDecision(
                direction=ScalingDirection.NONE,
                current_replicas=self.current_replicas,
                desired_replicas=self.current_replicas,
                reason="Already at maximum replicas",
                metrics=metrics
            )
        
        return ScalingDecision(
            direction=ScalingDirection.UP,
            current_replicas=self.current_replicas,
            desired_replicas=desired,
            reason=reason,
            metrics=metrics
        )
    
    def _create_scale_down_decision(
        self,
        reason: str,
        metrics: Dict[str, float]
    ) -> ScalingDecision:
        """Create scale down decision if cooldown allows."""
        if self.last_scale_down:
            elapsed = (datetime.utcnow() - self.last_scale_down).total_seconds()
            if elapsed < self.policy.scale_down_cooldown_seconds:
                return ScalingDecision(
                    direction=ScalingDirection.NONE,
                    current_replicas=self.current_replicas,
                    desired_replicas=self.current_replicas,
                    reason=f"Scale down cooldown ({int(self.policy.scale_down_cooldown_seconds - elapsed)}s remaining)",
                    metrics=metrics
                )
        
        desired = max(
            self.current_replicas - self.policy.scale_down_increment,
            self.policy.min_replicas
        )
        
        if desired == self.current_replicas:
            return ScalingDecision(
                direction=ScalingDirection.NONE,
                current_replicas=self.current_replicas,
                desired_replicas=self.current_replicas,
                reason="Already at minimum replicas",
                metrics=metrics
            )
        
        return ScalingDecision(
            direction=ScalingDirection.DOWN,
            current_replicas=self.current_replicas,
            desired_replicas=desired,
            reason=reason,
            metrics=metrics
        )
    
    def _apply_scaling(self, decision: ScalingDecision):
        """Apply scaling decision."""
        logger.info(
            f"Scaling {decision.direction.value}: "
            f"{decision.current_replicas} -> {decision.desired_replicas} "
            f"({decision.reason})"
        )
        
        self.current_replicas = decision.desired_replicas
        
        if decision.direction == ScalingDirection.UP:
            self.last_scale_up = datetime.utcnow()
        else:
            self.last_scale_down = datetime.utcnow()
        
        if self.scale_callback:
            try:
                self.scale_callback(decision.desired_replicas)
            except Exception as e:
                logger.error(f"Scale callback failed: {e}")
    
    def get_status(self) -> Dict[str, Any]:
        """Get auto-scaler status."""
        return {
            "current_replicas": self.current_replicas,
            "min_replicas": self.policy.min_replicas,
            "max_replicas": self.policy.max_replicas,
            "last_scale_up": self.last_scale_up.isoformat() if self.last_scale_up else None,
            "last_scale_down": self.last_scale_down.isoformat() if self.last_scale_down else None,
            "recent_decisions": [
                {
                    "direction": d.direction.value,
                    "from": d.current_replicas,
                    "to": d.desired_replicas,
                    "reason": d.reason,
                    "timestamp": d.timestamp.isoformat()
                }
                for d in list(self.decision_history)[-10:]
            ],
            "current_metrics": self.metrics.get_all_averages()
        }


# =============================================================================
# Service Registry
# =============================================================================

class ServiceRegistry:
    """
    Service Discovery and Registry.
    
    Manages service instances for discovery and load balancing.
    """
    
    def __init__(self, heartbeat_timeout_seconds: int = 30):
        self.heartbeat_timeout = heartbeat_timeout_seconds
        self.services: Dict[str, Dict[str, ServiceInstance]] = {}
        self._lock = threading.Lock()
    
    def register(
        self,
        service_name: str,
        instance_id: str,
        host: str,
        port: int,
        version: str = "1.0.0",
        metadata: Optional[Dict[str, Any]] = None
    ) -> ServiceInstance:
        """Register a service instance."""
        instance = ServiceInstance(
            instance_id=instance_id,
            host=host,
            port=port,
            version=version,
            started_at=datetime.utcnow(),
            metadata=metadata or {}
        )
        
        with self._lock:
            if service_name not in self.services:
                self.services[service_name] = {}
            
            self.services[service_name][instance_id] = instance
        
        logger.info(f"Registered {service_name}/{instance_id} at {host}:{port}")
        return instance
    
    def deregister(self, service_name: str, instance_id: str):
        """Deregister a service instance."""
        with self._lock:
            if service_name in self.services:
                if instance_id in self.services[service_name]:
                    del self.services[service_name][instance_id]
                    logger.info(f"Deregistered {service_name}/{instance_id}")
    
    def heartbeat(self, service_name: str, instance_id: str) -> bool:
        """Update heartbeat for an instance."""
        with self._lock:
            if (
                service_name in self.services and
                instance_id in self.services[service_name]
            ):
                self.services[service_name][instance_id].last_heartbeat = datetime.utcnow()
                return True
        return False
    
    def get_instances(
        self,
        service_name: str,
        healthy_only: bool = True
    ) -> List[ServiceInstance]:
        """Get all instances of a service."""
        with self._lock:
            if service_name not in self.services:
                return []
            
            instances = list(self.services[service_name].values())
            
            if healthy_only:
                instances = [i for i in instances if i.is_healthy]
            
            return instances
    
    def get_all_services(self) -> Dict[str, List[ServiceInstance]]:
        """Get all registered services and their instances."""
        with self._lock:
            return {
                name: list(instances.values())
                for name, instances in self.services.items()
            }
    
    def cleanup_stale(self):
        """Remove stale instances that haven't sent heartbeat."""
        with self._lock:
            for service_name in list(self.services.keys()):
                stale = [
                    instance_id
                    for instance_id, instance in self.services[service_name].items()
                    if not instance.is_healthy
                ]
                
                for instance_id in stale:
                    del self.services[service_name][instance_id]
                    logger.warning(f"Removed stale instance {service_name}/{instance_id}")


# =============================================================================
# Cluster Coordinator
# =============================================================================

class ClusterCoordinator:
    """
    Coordinates scaling and service discovery.
    
    Integrates:
    - Service registry
    - Auto-scaler
    - Load balancer
    """
    
    def __init__(
        self,
        service_registry: Optional[ServiceRegistry] = None,
        auto_scaler: Optional[AutoScaler] = None
    ):
        self.registry = service_registry or ServiceRegistry()
        self.scaler = auto_scaler
        self._cleanup_thread: Optional[threading.Thread] = None
        self._running = False
    
    def start(self):
        """Start cluster coordination."""
        self._running = True
        
        # Start cleanup thread
        self._cleanup_thread = threading.Thread(
            target=self._cleanup_loop,
            daemon=True
        )
        self._cleanup_thread.start()
        
        # Start auto-scaler if configured
        if self.scaler:
            self.scaler.start()
        
        logger.info("Cluster coordinator started")
    
    def stop(self):
        """Stop cluster coordination."""
        self._running = False
        
        if self.scaler:
            self.scaler.stop()
        
        if self._cleanup_thread:
            self._cleanup_thread.join(timeout=5)
        
        logger.info("Cluster coordinator stopped")
    
    def _cleanup_loop(self):
        """Periodic cleanup of stale instances."""
        while self._running:
            try:
                self.registry.cleanup_stale()
            except Exception as e:
                logger.error(f"Cleanup error: {e}")
            
            time.sleep(10)
    
    def get_cluster_status(self) -> Dict[str, Any]:
        """Get comprehensive cluster status."""
        status = {
            "services": {},
            "total_instances": 0,
            "healthy_instances": 0
        }
        
        for service_name, instances in self.registry.get_all_services().items():
            healthy = [i for i in instances if i.is_healthy]
            status["services"][service_name] = {
                "total": len(instances),
                "healthy": len(healthy),
                "instances": [
                    {
                        "id": i.instance_id,
                        "host": i.host,
                        "port": i.port,
                        "version": i.version,
                        "healthy": i.is_healthy,
                        "uptime_seconds": (datetime.utcnow() - i.started_at).total_seconds()
                    }
                    for i in instances
                ]
            }
            status["total_instances"] += len(instances)
            status["healthy_instances"] += len(healthy)
        
        if self.scaler:
            status["auto_scaler"] = self.scaler.get_status()
        
        return status


# =============================================================================
# Factory Functions
# =============================================================================

_service_registry: Optional[ServiceRegistry] = None
_cluster_coordinator: Optional[ClusterCoordinator] = None


def get_service_registry() -> ServiceRegistry:
    """Get singleton service registry."""
    global _service_registry
    if _service_registry is None:
        _service_registry = ServiceRegistry()
    return _service_registry


def get_cluster_coordinator() -> ClusterCoordinator:
    """Get singleton cluster coordinator."""
    global _cluster_coordinator
    if _cluster_coordinator is None:
        policy = ScalingPolicy(
            min_replicas=2,
            max_replicas=10,
            target_cpu_percent=70,
            target_memory_percent=80,
            target_latency_ms=500
        )
        scaler = AutoScaler(policy)
        _cluster_coordinator = ClusterCoordinator(
            service_registry=get_service_registry(),
            auto_scaler=scaler
        )
    return _cluster_coordinator
