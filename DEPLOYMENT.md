# =============================================================================
# Deployment Guide: Load Balancing & Scaling
# =============================================================================

[![GitHub](https://img.shields.io/badge/GitHub-Repository-blue?logo=github)](https://github.com/amannjoshi/Loan-approval-disapproval)

**🔗 Repository:** [https://github.com/amannjoshi/Loan-approval-disapproval](https://github.com/amannjoshi/Loan-approval-disapproval)

## 🏗️ Architecture Overview

```
                    ┌─────────────────────────────────────────────────┐
                    │                 CLIENTS                          │
                    └────────────────────┬────────────────────────────┘
                                         │
                                         ▼
                    ┌─────────────────────────────────────────────────┐
                    │              NGINX LOAD BALANCER                 │
                    │  (Rate Limiting, SSL Termination, Compression)   │
                    └────────────────────┬────────────────────────────┘
                                         │
              ┌──────────────────────────┼──────────────────────────┐
              │                          │                          │
              ▼                          ▼                          ▼
    ┌─────────────────┐      ┌─────────────────┐      ┌─────────────────┐
    │   API Server 1  │      │   API Server 2  │      │   API Server 3  │
    │  (Gunicorn +    │      │  (Gunicorn +    │      │  (Gunicorn +    │
    │   Uvicorn)      │      │   Uvicorn)      │      │   Uvicorn)      │
    └────────┬────────┘      └────────┬────────┘      └────────┬────────┘
              │                        │                        │
              └────────────────────────┼────────────────────────┘
                                       │
              ┌────────────────────────┼────────────────────────┐
              │                        │                        │
              ▼                        ▼                        ▼
    ┌─────────────────┐      ┌─────────────────┐      ┌─────────────────┐
    │   PostgreSQL    │      │     Redis       │      │   Prometheus    │
    │   (Primary DB)  │      │    (Cache)      │      │  (Monitoring)   │
    └─────────────────┘      └─────────────────┘      └─────────────────┘
```

## 🚀 Quick Start

### 1. Build and Start Services

```bash
# Build the Docker images
docker-compose build

# Start all services (3 API replicas by default)
docker-compose up -d

# Scale API to 5 instances
docker-compose up -d --scale api=5
```

### 2. Verify Deployment

```bash
# Check health
curl http://localhost/health

# Check detailed health
curl http://localhost/health/detailed

# Check metrics
curl http://localhost/metrics
```

### 3. Monitor Services

- **Grafana Dashboard**: http://localhost:3000 (admin/admin)
- **Prometheus**: http://localhost:9090
- **API Docs**: http://localhost/docs

---

## 📁 Project Structure (Infrastructure)

```
Loan Approval/
├── infrastructure/
│   ├── __init__.py          # Package exports
│   ├── load_balancer.py     # Software load balancer implementation
│   └── scaling.py           # Auto-scaling & service discovery
├── middleware/
│   ├── __init__.py          # Package exports
│   └── rate_limiting.py     # Token bucket rate limiter
├── nginx/
│   ├── nginx.conf           # Main Nginx configuration
│   └── conf.d/
│       └── proxy_params.conf # Proxy settings
├── monitoring/
│   ├── prometheus/
│   │   ├── prometheus.yml   # Scrape configuration
│   │   └── rules/
│   │       └── alerts.yml   # Alerting rules
│   └── grafana/
│       └── provisioning/
│           ├── datasources/ # Auto-configure Prometheus
│           └── dashboards/  # Pre-built dashboards
├── Dockerfile               # Multi-stage production build
├── docker-compose.yml       # Full stack definition
└── DEPLOYMENT.md            # This file
```

---

## ⚙️ Configuration

### Load Balancing Strategies

The Nginx load balancer supports multiple strategies:

| Strategy | Description | Use Case |
|----------|-------------|----------|
| `round_robin` | Distributes requests evenly | Default, equal server capacity |
| `least_conn` | Routes to server with fewest connections | Variable request duration |
| `ip_hash` | Routes based on client IP | Session affinity needed |
| `weighted` | Weighted distribution | Different server capacities |

**Configure in `nginx/nginx.conf`:**
```nginx
upstream api_servers {
    least_conn;  # Change strategy here
    server api:8000;
}
```

### Rate Limiting

**Nginx Level (nginx.conf):**
```nginx
limit_req_zone $binary_remote_addr zone=api_limit:10m rate=100r/s;
limit_req_zone $binary_remote_addr zone=auth_limit:10m rate=10r/s;
```

**Application Level (middleware/rate_limiting.py):**
```python
RateLimitConfig(
    requests_per_second=50,
    burst_size=100,
    max_requests_per_window=1000
)
```

### Auto-Scaling

**Configuration in docker-compose.yml:**
```yaml
services:
  api:
    deploy:
      replicas: 3          # Initial replicas
      resources:
        limits:
          cpus: '0.5'
          memory: 1G
```

**Scale manually:**
```bash
docker-compose up -d --scale api=5
```

---

## 📊 Monitoring

### Key Metrics

| Metric | Description | Alert Threshold |
|--------|-------------|-----------------|
| `loan_api_requests_total` | Total request count | - |
| `loan_api_request_duration_seconds` | Response time | p99 > 5s |
| `loan_api_cpu_percent` | CPU usage | > 90% |
| `loan_api_memory_percent` | Memory usage | > 90% |

### Prometheus Queries

```promql
# Request rate
sum(rate(loan_api_requests_total[5m]))

# Error rate
sum(rate(loan_api_requests_by_status{status=~"5.."}[5m])) / sum(rate(loan_api_requests_total[5m]))

# P95 latency
histogram_quantile(0.95, sum(rate(loan_api_request_duration_seconds_bucket[5m])) by (le))
```

### Grafana Dashboards

Pre-configured dashboards:
1. **API Overview** - Request rate, latency, error rate
2. **System Resources** - CPU, memory, disk usage
3. **Database** - Connection pool, query latency

---

## 🔧 Operations

### Health Checks

| Endpoint | Purpose | Used By |
|----------|---------|---------|
| `/health` | Basic health | Load balancers |
| `/health/live` | Liveness probe | Kubernetes |
| `/health/ready` | Readiness probe | Kubernetes |
| `/health/detailed` | Full diagnostics | Monitoring |
| `/metrics` | Prometheus metrics | Prometheus |

### Common Commands

```bash
# View logs
docker-compose logs -f api

# Restart a service
docker-compose restart api

# Scale up
docker-compose up -d --scale api=5

# Scale down
docker-compose up -d --scale api=2

# Stop all services
docker-compose down

# Remove volumes (CAUTION: deletes data)
docker-compose down -v
```

### Troubleshooting

**API not responding:**
```bash
# Check container status
docker-compose ps

# Check logs
docker-compose logs api

# Check health
curl http://localhost/health/detailed
```

**High latency:**
```bash
# Check database
curl http://localhost/health/detailed | jq .checks.database

# Check CPU/memory
curl http://localhost/health/detailed | jq .checks.system
```

**Rate limit errors (429):**
- Check `Retry-After` header
- Review rate limit configuration
- Consider scaling up

---

## 🔒 Security

### Production Checklist

- [ ] Change default passwords in `.env`
- [ ] Enable HTTPS (configure SSL in Nginx)
- [ ] Restrict CORS origins
- [ ] Enable rate limiting
- [ ] Configure firewall rules
- [ ] Set up monitoring alerts
- [ ] Regular security updates

### SSL Configuration

Add to `nginx/nginx.conf`:
```nginx
server {
    listen 443 ssl;
    ssl_certificate /etc/nginx/ssl/cert.pem;
    ssl_certificate_key /etc/nginx/ssl/key.pem;
    # ... rest of config
}
```

---

## 📈 Performance Tuning

### Nginx

```nginx
worker_processes auto;
worker_connections 4096;
keepalive_timeout 65;
```

### Gunicorn

```bash
gunicorn app:app \
    --workers 4 \
    --worker-class uvicorn.workers.UvicornWorker \
    --bind 0.0.0.0:8000 \
    --timeout 30 \
    --keep-alive 5
```

### Database Connection Pool

```python
# In database/connection.py
engine = create_engine(
    url,
    pool_size=20,
    max_overflow=30,
    pool_pre_ping=True
)
```

---

## 🎯 Next Steps

1. **Kubernetes Migration**: Migrate from Docker Compose to K8s for production
2. **Service Mesh**: Add Istio/Linkerd for advanced traffic management
3. **CDN**: Add CloudFlare/AWS CloudFront for static assets
4. **Database Replication**: Set up read replicas for scaling reads
5. **Distributed Tracing**: Add Jaeger/Zipkin for request tracing
