"""
Load Balancer & Scaling Infrastructure
======================================
Implements load balancing, health checks, and horizontal scaling support.

System Design Concepts:
- Round-robin load balancing
- Weighted load balancing
- Health check endpoints
- Circuit breaker pattern
- Connection pooling
- Rate limiting per server

Author: Loan Analytics Team
Version: 1.0.0
"""

import asyncio
import time
import random
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Any, Callable
from collections import deque
import threading
import hashlib

logger = logging.getLogger(__name__)


# =============================================================================
# Enums and Types
# =============================================================================

class ServerStatus(str, Enum):
    """Server health status."""
    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"
    DEGRADED = "degraded"
    STARTING = "starting"
    DRAINING = "draining"  # Graceful shutdown


class LoadBalancingStrategy(str, Enum):
    """Load balancing algorithms."""
    ROUND_ROBIN = "round_robin"
    WEIGHTED_ROUND_ROBIN = "weighted_round_robin"
    LEAST_CONNECTIONS = "least_connections"
    IP_HASH = "ip_hash"
    RANDOM = "random"
    LEAST_RESPONSE_TIME = "least_response_time"


class CircuitState(str, Enum):
    """Circuit breaker states."""
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Failing, reject requests
    HALF_OPEN = "half_open"  # Testing recovery


# =============================================================================
# Data Classes
# =============================================================================

@dataclass
class ServerInstance:
    """Represents a backend server instance."""
    id: str
    host: str
    port: int
    weight: int = 1
    max_connections: int = 100
    status: ServerStatus = ServerStatus.STARTING
    current_connections: int = 0
    total_requests: int = 0
    failed_requests: int = 0
    avg_response_time_ms: float = 0.0
    last_health_check: Optional[datetime] = None
    last_failure: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def url(self) -> str:
        return f"http://{self.host}:{self.port}"
    
    @property
    def is_available(self) -> bool:
        return (
            self.status == ServerStatus.HEALTHY and
            self.current_connections < self.max_connections
        )
    
    @property
    def failure_rate(self) -> float:
        if self.total_requests == 0:
            return 0.0
        return self.failed_requests / self.total_requests
    
    def record_request(self, success: bool, response_time_ms: float):
        """Record a request result."""
        self.total_requests += 1
        if not success:
            self.failed_requests += 1
            self.last_failure = datetime.utcnow()
        
        # Update rolling average response time
        alpha = 0.1  # Smoothing factor
        self.avg_response_time_ms = (
            alpha * response_time_ms + (1 - alpha) * self.avg_response_time_ms
        )


@dataclass
class HealthCheckConfig:
    """Health check configuration."""
    endpoint: str = "/health"
    interval_seconds: int = 10
    timeout_seconds: int = 5
    healthy_threshold: int = 2
    unhealthy_threshold: int = 3


@dataclass
class CircuitBreakerConfig:
    """Circuit breaker configuration."""
    failure_threshold: int = 5
    recovery_timeout_seconds: int = 30
    half_open_max_requests: int = 3


# =============================================================================
# Circuit Breaker Pattern
# =============================================================================

class CircuitBreaker:
    """
    Circuit Breaker Pattern Implementation.
    
    Prevents cascading failures by:
    - Tracking failure counts
    - Opening circuit when threshold exceeded
    - Periodically testing recovery
    """
    
    def __init__(self, config: CircuitBreakerConfig):
        self.config = config
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time: Optional[datetime] = None
        self.half_open_requests = 0
        self._lock = threading.Lock()
    
    def can_execute(self) -> bool:
        """Check if request can proceed."""
        with self._lock:
            if self.state == CircuitState.CLOSED:
                return True
            
            if self.state == CircuitState.OPEN:
                # Check if recovery timeout passed
                if self.last_failure_time:
                    elapsed = (datetime.utcnow() - self.last_failure_time).total_seconds()
                    if elapsed >= self.config.recovery_timeout_seconds:
                        self._transition_to_half_open()
                        return True
                return False
            
            if self.state == CircuitState.HALF_OPEN:
                return self.half_open_requests < self.config.half_open_max_requests
            
            return False
    
    def record_success(self):
        """Record successful request."""
        with self._lock:
            if self.state == CircuitState.HALF_OPEN:
                self.success_count += 1
                if self.success_count >= self.config.half_open_max_requests:
                    self._transition_to_closed()
            elif self.state == CircuitState.CLOSED:
                self.failure_count = 0
    
    def record_failure(self):
        """Record failed request."""
        with self._lock:
            self.failure_count += 1
            self.last_failure_time = datetime.utcnow()
            
            if self.state == CircuitState.HALF_OPEN:
                self._transition_to_open()
            elif self.state == CircuitState.CLOSED:
                if self.failure_count >= self.config.failure_threshold:
                    self._transition_to_open()
    
    def _transition_to_open(self):
        """Transition to open state."""
        self.state = CircuitState.OPEN
        logger.warning(f"Circuit breaker opened after {self.failure_count} failures")
    
    def _transition_to_half_open(self):
        """Transition to half-open state."""
        self.state = CircuitState.HALF_OPEN
        self.half_open_requests = 0
        self.success_count = 0
        logger.info("Circuit breaker half-open, testing recovery")
    
    def _transition_to_closed(self):
        """Transition to closed state."""
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        logger.info("Circuit breaker closed, service recovered")


# =============================================================================
# Rate Limiter
# =============================================================================

class RateLimiter:
    """
    Token Bucket Rate Limiter.
    
    Controls request rate per client/server to prevent overload.
    """
    
    def __init__(
        self,
        requests_per_second: float = 100,
        burst_size: int = 200
    ):
        self.rate = requests_per_second
        self.burst_size = burst_size
        self.tokens = burst_size
        self.last_update = time.time()
        self._lock = threading.Lock()
    
    def acquire(self, tokens: int = 1) -> bool:
        """
        Attempt to acquire tokens.
        
        Returns True if tokens acquired, False if rate limited.
        """
        with self._lock:
            now = time.time()
            elapsed = now - self.last_update
            self.last_update = now
            
            # Add tokens based on elapsed time
            self.tokens = min(
                self.burst_size,
                self.tokens + elapsed * self.rate
            )
            
            if self.tokens >= tokens:
                self.tokens -= tokens
                return True
            
            return False
    
    def get_wait_time(self, tokens: int = 1) -> float:
        """Get time to wait until tokens available."""
        with self._lock:
            if self.tokens >= tokens:
                return 0.0
            needed = tokens - self.tokens
            return needed / self.rate


class DistributedRateLimiter:
    """
    Per-client rate limiter with sliding window.
    
    Tracks rate limits for individual clients (by IP or API key).
    """
    
    def __init__(
        self,
        requests_per_window: int = 100,
        window_seconds: int = 60
    ):
        self.max_requests = requests_per_window
        self.window_seconds = window_seconds
        self.clients: Dict[str, deque] = {}
        self._lock = threading.Lock()
    
    def is_allowed(self, client_id: str) -> tuple[bool, dict]:
        """
        Check if client request is allowed.
        
        Returns (allowed, rate_limit_info)
        """
        with self._lock:
            now = time.time()
            cutoff = now - self.window_seconds
            
            if client_id not in self.clients:
                self.clients[client_id] = deque()
            
            # Remove old timestamps
            while self.clients[client_id] and self.clients[client_id][0] < cutoff:
                self.clients[client_id].popleft()
            
            current_count = len(self.clients[client_id])
            remaining = max(0, self.max_requests - current_count)
            
            info = {
                "limit": self.max_requests,
                "remaining": remaining,
                "reset": int(cutoff + self.window_seconds),
                "window": self.window_seconds
            }
            
            if current_count >= self.max_requests:
                return False, info
            
            self.clients[client_id].append(now)
            info["remaining"] = remaining - 1
            return True, info
    
    def cleanup(self):
        """Remove stale client entries."""
        with self._lock:
            now = time.time()
            cutoff = now - self.window_seconds * 2
            
            stale = [
                client_id for client_id, timestamps in self.clients.items()
                if not timestamps or timestamps[-1] < cutoff
            ]
            
            for client_id in stale:
                del self.clients[client_id]


# =============================================================================
# Load Balancer
# =============================================================================

class LoadBalancer:
    """
    Production-grade Load Balancer.
    
    Features:
    - Multiple load balancing strategies
    - Health checking
    - Circuit breakers per server
    - Connection tracking
    - Graceful server draining
    """
    
    def __init__(
        self,
        strategy: LoadBalancingStrategy = LoadBalancingStrategy.ROUND_ROBIN,
        health_config: Optional[HealthCheckConfig] = None,
        circuit_config: Optional[CircuitBreakerConfig] = None
    ):
        self.strategy = strategy
        self.health_config = health_config or HealthCheckConfig()
        self.circuit_config = circuit_config or CircuitBreakerConfig()
        
        self.servers: Dict[str, ServerInstance] = {}
        self.circuit_breakers: Dict[str, CircuitBreaker] = {}
        self.rate_limiters: Dict[str, RateLimiter] = {}
        
        self._round_robin_index = 0
        self._lock = threading.Lock()
        self._health_check_task: Optional[asyncio.Task] = None
    
    def add_server(
        self,
        server_id: str,
        host: str,
        port: int,
        weight: int = 1,
        max_connections: int = 100
    ):
        """Add a backend server to the pool."""
        server = ServerInstance(
            id=server_id,
            host=host,
            port=port,
            weight=weight,
            max_connections=max_connections,
            status=ServerStatus.STARTING
        )
        
        with self._lock:
            self.servers[server_id] = server
            self.circuit_breakers[server_id] = CircuitBreaker(self.circuit_config)
            self.rate_limiters[server_id] = RateLimiter(
                requests_per_second=max_connections * 0.8
            )
        
        logger.info(f"Added server {server_id} at {host}:{port}")
    
    def remove_server(self, server_id: str, graceful: bool = True):
        """Remove a server from the pool."""
        with self._lock:
            if server_id not in self.servers:
                return
            
            if graceful:
                self.servers[server_id].status = ServerStatus.DRAINING
                logger.info(f"Server {server_id} marked for draining")
            else:
                del self.servers[server_id]
                del self.circuit_breakers[server_id]
                del self.rate_limiters[server_id]
                logger.info(f"Server {server_id} removed")
    
    def get_server(self, client_ip: Optional[str] = None) -> Optional[ServerInstance]:
        """
        Get next available server based on strategy.
        
        Args:
            client_ip: Client IP for IP-hash strategy
            
        Returns:
            Selected server or None if all unavailable
        """
        with self._lock:
            available = [
                s for s in self.servers.values()
                if s.is_available and self.circuit_breakers[s.id].can_execute()
            ]
            
            if not available:
                logger.warning("No healthy servers available")
                return None
            
            if self.strategy == LoadBalancingStrategy.ROUND_ROBIN:
                return self._round_robin(available)
            elif self.strategy == LoadBalancingStrategy.WEIGHTED_ROUND_ROBIN:
                return self._weighted_round_robin(available)
            elif self.strategy == LoadBalancingStrategy.LEAST_CONNECTIONS:
                return self._least_connections(available)
            elif self.strategy == LoadBalancingStrategy.IP_HASH:
                return self._ip_hash(available, client_ip)
            elif self.strategy == LoadBalancingStrategy.RANDOM:
                return self._random(available)
            elif self.strategy == LoadBalancingStrategy.LEAST_RESPONSE_TIME:
                return self._least_response_time(available)
            
            return available[0]
    
    def _round_robin(self, servers: List[ServerInstance]) -> ServerInstance:
        """Simple round-robin selection."""
        server = servers[self._round_robin_index % len(servers)]
        self._round_robin_index += 1
        return server
    
    def _weighted_round_robin(self, servers: List[ServerInstance]) -> ServerInstance:
        """Weighted round-robin based on server weights."""
        total_weight = sum(s.weight for s in servers)
        target = self._round_robin_index % total_weight
        self._round_robin_index += 1
        
        cumulative = 0
        for server in servers:
            cumulative += server.weight
            if cumulative > target:
                return server
        
        return servers[-1]
    
    def _least_connections(self, servers: List[ServerInstance]) -> ServerInstance:
        """Select server with fewest active connections."""
        return min(servers, key=lambda s: s.current_connections)
    
    def _ip_hash(
        self,
        servers: List[ServerInstance],
        client_ip: Optional[str]
    ) -> ServerInstance:
        """Consistent hashing based on client IP."""
        if not client_ip:
            return self._round_robin(servers)
        
        hash_value = int(hashlib.md5(client_ip.encode()).hexdigest(), 16)
        index = hash_value % len(servers)
        return servers[index]
    
    def _random(self, servers: List[ServerInstance]) -> ServerInstance:
        """Random server selection."""
        return random.choice(servers)
    
    def _least_response_time(self, servers: List[ServerInstance]) -> ServerInstance:
        """Select server with lowest average response time."""
        return min(servers, key=lambda s: s.avg_response_time_ms)
    
    def record_request_start(self, server_id: str):
        """Record start of a request to a server."""
        with self._lock:
            if server_id in self.servers:
                self.servers[server_id].current_connections += 1
    
    def record_request_end(
        self,
        server_id: str,
        success: bool,
        response_time_ms: float
    ):
        """Record end of a request with result."""
        with self._lock:
            if server_id in self.servers:
                server = self.servers[server_id]
                server.current_connections = max(0, server.current_connections - 1)
                server.record_request(success, response_time_ms)
            
            if server_id in self.circuit_breakers:
                if success:
                    self.circuit_breakers[server_id].record_success()
                else:
                    self.circuit_breakers[server_id].record_failure()
    
    def update_server_health(self, server_id: str, healthy: bool):
        """Update server health status."""
        with self._lock:
            if server_id in self.servers:
                server = self.servers[server_id]
                server.last_health_check = datetime.utcnow()
                
                if healthy:
                    if server.status != ServerStatus.DRAINING:
                        server.status = ServerStatus.HEALTHY
                else:
                    server.status = ServerStatus.UNHEALTHY
    
    def get_stats(self) -> Dict[str, Any]:
        """Get load balancer statistics."""
        with self._lock:
            healthy = sum(1 for s in self.servers.values() if s.status == ServerStatus.HEALTHY)
            total = len(self.servers)
            
            return {
                "strategy": self.strategy.value,
                "total_servers": total,
                "healthy_servers": healthy,
                "unhealthy_servers": total - healthy,
                "servers": {
                    s.id: {
                        "status": s.status.value,
                        "url": s.url,
                        "connections": s.current_connections,
                        "total_requests": s.total_requests,
                        "failure_rate": round(s.failure_rate * 100, 2),
                        "avg_response_ms": round(s.avg_response_time_ms, 2),
                        "circuit_state": self.circuit_breakers[s.id].state.value
                    }
                    for s in self.servers.values()
                }
            }


# =============================================================================
# Health Check Service
# =============================================================================

class HealthCheckService:
    """
    Background service for checking server health.
    
    Runs periodic health checks and updates server status.
    """
    
    def __init__(
        self,
        load_balancer: LoadBalancer,
        config: HealthCheckConfig
    ):
        self.lb = load_balancer
        self.config = config
        self._running = False
        self._health_counts: Dict[str, int] = {}  # Track consecutive health results
    
    async def start(self):
        """Start health check loop."""
        self._running = True
        logger.info("Health check service started")
        
        while self._running:
            await self._check_all_servers()
            await asyncio.sleep(self.config.interval_seconds)
    
    def stop(self):
        """Stop health check loop."""
        self._running = False
        logger.info("Health check service stopped")
    
    async def _check_all_servers(self):
        """Check health of all servers."""
        import aiohttp
        
        tasks = []
        for server_id, server in self.lb.servers.items():
            if server.status != ServerStatus.DRAINING:
                tasks.append(self._check_server(server_id, server))
        
        await asyncio.gather(*tasks, return_exceptions=True)
    
    async def _check_server(self, server_id: str, server: ServerInstance):
        """Check health of a single server."""
        import aiohttp
        
        url = f"{server.url}{self.config.endpoint}"
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    url,
                    timeout=aiohttp.ClientTimeout(total=self.config.timeout_seconds)
                ) as response:
                    healthy = response.status == 200
        except Exception as e:
            healthy = False
            logger.debug(f"Health check failed for {server_id}: {e}")
        
        # Update health count
        if server_id not in self._health_counts:
            self._health_counts[server_id] = 0
        
        if healthy:
            self._health_counts[server_id] = min(
                self._health_counts[server_id] + 1,
                self.config.healthy_threshold
            )
        else:
            self._health_counts[server_id] = max(
                self._health_counts[server_id] - 1,
                -self.config.unhealthy_threshold
            )
        
        # Update server status based on threshold
        if self._health_counts[server_id] >= self.config.healthy_threshold:
            self.lb.update_server_health(server_id, True)
        elif self._health_counts[server_id] <= -self.config.unhealthy_threshold:
            self.lb.update_server_health(server_id, False)


# =============================================================================
# Factory Functions
# =============================================================================

_load_balancer: Optional[LoadBalancer] = None


def get_load_balancer() -> LoadBalancer:
    """Get singleton load balancer instance."""
    global _load_balancer
    if _load_balancer is None:
        _load_balancer = LoadBalancer(
            strategy=LoadBalancingStrategy.LEAST_CONNECTIONS,
            health_config=HealthCheckConfig(
                interval_seconds=10,
                healthy_threshold=2,
                unhealthy_threshold=3
            ),
            circuit_config=CircuitBreakerConfig(
                failure_threshold=5,
                recovery_timeout_seconds=30
            )
        )
    return _load_balancer


def create_load_balancer_from_config(config: dict) -> LoadBalancer:
    """Create load balancer from configuration dict."""
    strategy = LoadBalancingStrategy(config.get("strategy", "round_robin"))
    
    health_config = HealthCheckConfig(
        endpoint=config.get("health_endpoint", "/health"),
        interval_seconds=config.get("health_interval", 10),
        timeout_seconds=config.get("health_timeout", 5)
    )
    
    circuit_config = CircuitBreakerConfig(
        failure_threshold=config.get("circuit_failure_threshold", 5),
        recovery_timeout_seconds=config.get("circuit_recovery_seconds", 30)
    )
    
    lb = LoadBalancer(strategy, health_config, circuit_config)
    
    # Add servers from config
    for server in config.get("servers", []):
        lb.add_server(
            server_id=server["id"],
            host=server["host"],
            port=server["port"],
            weight=server.get("weight", 1),
            max_connections=server.get("max_connections", 100)
        )
    
    return lb
