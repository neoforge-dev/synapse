# Synapse Graph-RAG - CI/CD Setup Guide

**Last Updated:** 2026-01-26
**Status:** Production Ready
**Author:** DevOps Team

---

## Overview

This document describes the complete CI/CD pipeline for Synapse Graph-RAG, including continuous integration, automated deployments, monitoring, and rollback procedures.

## Table of Contents

1. [CI/CD Architecture](#cicd-architecture)
2. [GitHub Actions Workflows](#github-actions-workflows)
3. [Docker Configuration](#docker-configuration)
4. [Deployment Environments](#deployment-environments)
5. [Monitoring and Observability](#monitoring-and-observability)
6. [Security and Secrets Management](#security-and-secrets-management)
7. [Rollback Procedures](#rollback-procedures)
8. [Troubleshooting](#troubleshooting)

---

## CI/CD Architecture

### Pipeline Overview

```
┌─────────────────────────────────────────────────────────────┐
│                     GitHub Actions Pipeline                  │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  Push/PR → CI Workflow                                       │
│    ├─ Lint (ruff, mypy)                                      │
│    ├─ Security Scan (safety, bandit)                         │
│    ├─ Unit Tests (pytest)                                    │
│    ├─ Integration Tests (Memgraph)                           │
│    └─ Build Validation                                       │
│                                                               │
│  Develop Branch → Deploy Workflow                            │
│    ├─ Run CI Tests                                           │
│    ├─ Build Docker Image                                     │
│    ├─ Push to Container Registry                             │
│    ├─ Deploy to Staging                                      │
│    ├─ Health Checks                                          │
│    └─ Smoke Tests                                            │
│                                                               │
│  Main Branch / Release → Deploy Workflow                     │
│    ├─ Run CI Tests                                           │
│    ├─ Build Docker Image                                     │
│    ├─ Push to Container Registry                             │
│    ├─ Deploy to Production                                   │
│    ├─ Health Checks                                          │
│    ├─ Smoke Tests                                            │
│    └─ Create GitHub Release                                  │
│                                                               │
│  Release Tag → Release Workflow                              │
│    ├─ Run Full Test Suite                                    │
│    ├─ Build Package                                          │
│    ├─ Publish to PyPI                                        │
│    └─ Create GitHub Release                                  │
│                                                               │
└─────────────────────────────────────────────────────────────┘
```

### Key Features

- **Automated Testing**: Unit, integration, and security tests on every push
- **Multi-Environment Deployment**: Staging and production environments
- **Container Registry**: GitHub Container Registry (GHCR) for Docker images
- **Health Checks**: Automated health verification after deployment
- **Rollback Support**: Automatic rollback on deployment failure
- **Security Scanning**: Dependency vulnerability scanning with safety and bandit

---

## GitHub Actions Workflows

### 1. CI Workflow (`.github/workflows/ci.yml`)

**Triggers:**
- Push to `main` or `develop` branches
- Pull requests to `main` or `develop`
- Weekly schedule (Mondays at 6am UTC)

**Jobs:**
1. **Lint** - Code quality checks with ruff and mypy
2. **Test** - Unit and integration tests across Python 3.10, 3.11, 3.12
3. **Security** - Safety and bandit security scans
4. **MCP Integration** - Model Context Protocol integration tests
5. **Build Test** - Package build validation

**Matrix Testing:**
- Operating Systems: Ubuntu, macOS, Windows
- Python Versions: 3.10, 3.11, 3.12

**Services:**
- Memgraph: For integration testing (Linux only)

### 2. Deploy Workflow (`.github/workflows/deploy.yml`)

**Triggers:**
- Push to `develop` (staging deployment)
- Push to `main` (production deployment)
- Release published
- Manual workflow dispatch

**Jobs:**
1. **Prepare** - Determine environment and version
2. **Test** - Run critical tests before deployment
3. **Build and Push** - Build Docker image and push to GHCR
4. **Deploy Staging** - Deploy to staging environment
5. **Deploy Production** - Deploy to production environment
6. **Rollback** - Automatic rollback on failure

**Deployment Targets:**
- **Staging:** `https://staging.synapse.neoforge.dev`
- **Production:** `https://synapse.neoforge.dev`

### 3. Release Workflow (`.github/workflows/release.yml`)

**Triggers:**
- Push tags matching `v*` (e.g., v0.1.0)
- Manual workflow dispatch

**Jobs:**
1. **Test** - Full test suite across all Python versions
2. **Security** - Security scanning
3. **Build** - Build Python package distributions
4. **Publish PyPI** - Publish to PyPI (production)
5. **Publish Test PyPI** - Publish to Test PyPI (testing)
6. **Create Release** - Create GitHub release with artifacts
7. **Update Homebrew** - Update Homebrew formula
8. **Notify** - Release notifications

---

## Docker Configuration

### Multi-Stage Dockerfile

The Dockerfile uses a multi-stage build for optimized production images:

**Stage 1: Base** - Python 3.11-slim with uv package manager
**Stage 2: Builder** - Install dependencies and build artifacts
**Stage 3: Production** - Minimal runtime image with security hardening

**Security Features:**
- Non-root user (`synapse`)
- Minimal attack surface (slim base image)
- Security updates installed
- No unnecessary build tools in final image

**Image Size:** ~500MB (optimized from 1.2GB)

### Docker Compose Configurations

**Development:** `docker-compose.yml`
- Memgraph + PostgreSQL + API
- Volume mounts for local development
- Hot reload enabled

**Production:** `docker-compose.prod.yml`
- Memgraph + PostgreSQL + API
- Prometheus + Grafana (optional monitoring profile)
- Health checks and restart policies
- Resource limits and reservations

---

## Deployment Environments

### Staging Environment

**URL:** `https://staging.synapse.neoforge.dev`
**Platform:** Railway
**Deployment Trigger:** Push to `develop` branch
**Purpose:** Pre-production testing and validation

**Configuration:**
```bash
SYNAPSE_ENVIRONMENT=staging
SYNAPSE_ENABLE_AUTHENTICATION=true
SYNAPSE_LLM_TYPE=openai
SENTRY_DSN=<staging-dsn>
```

**Health Checks:**
- `/health` - Comprehensive health check
- `/health/liveness` - Liveness probe
- `/health/readiness` - Readiness probe

**Smoke Tests:**
- API documentation accessible
- Health endpoints responding
- Basic query functionality

### Production Environment

**URL:** `https://synapse.neoforge.dev`
**Platform:** Railway
**Deployment Trigger:** Push to `main` branch or release tag
**Purpose:** Live production environment

**Configuration:**
```bash
SYNAPSE_ENVIRONMENT=production
SYNAPSE_ENABLE_AUTHENTICATION=true
SYNAPSE_LLM_TYPE=openai
SENTRY_DSN=<production-dsn>
SENTRY_TRACES_SAMPLE_RATE=0.1
```

**Health Checks:**
- Same as staging with stricter timeouts
- Additional resource utilization checks
- Database connectivity verification

**Smoke Tests:**
- Same as staging plus:
  - API v1 health endpoint
  - Query execution validation
  - Authentication verification

---

## Monitoring and Observability

### 1. Sentry Error Tracking

**Purpose:** Real-time error tracking and performance monitoring

**Configuration:**
```python
# graph_rag/observability/sentry_config.py
SENTRY_DSN=<your-dsn>
SENTRY_TRACES_SAMPLE_RATE=0.1  # 10% of transactions
SENTRY_PROFILES_SAMPLE_RATE=0.1  # 10% profiling
```

**Features:**
- Automatic error capture
- Performance monitoring
- Request tracing
- User context tracking
- Custom tags and context

**Integration:**
```python
from graph_rag.observability.sentry_config import (
    init_sentry,
    capture_exception,
    capture_message,
    set_user_context
)

# Initialize on startup
init_sentry()

# Capture exceptions
try:
    # ... code
except Exception as e:
    capture_exception(e, context={"user_id": user.id})
```

### 2. Prometheus Metrics

**Endpoint:** `/metrics`
**Format:** Prometheus exposition format

**Metrics Collected:**
- HTTP request duration
- Request count by endpoint
- Error rates
- Active connections
- System resources (CPU, memory, disk)

**Configuration:**
```yaml
# monitoring/prometheus.yml
scrape_configs:
  - job_name: 'synapse-api'
    metrics_path: '/metrics'
    static_configs:
      - targets: ['graph-rag:8000']
```

### 3. Health Check Endpoints

**Comprehensive Health Check:**
```bash
GET /monitoring/health
```
Response includes:
- Overall status
- Memgraph connectivity
- System resources
- Individual component checks

**Liveness Probe:**
```bash
GET /monitoring/health/liveness
```
Simple alive check for Kubernetes/Docker

**Readiness Probe:**
```bash
GET /monitoring/health/readiness
```
Checks if service is ready to accept traffic

**System Metrics:**
```bash
GET /monitoring/metrics/system
```
Returns:
- CPU usage
- Memory usage
- Disk usage
- Uptime

**Application Info:**
```bash
GET /monitoring/info
```
Returns:
- Version
- Python version
- Platform
- Environment
- Start time

### 4. Grafana Dashboards (Optional)

**URL:** `http://localhost:3000` (when monitoring profile is enabled)
**Default Credentials:** admin/admin (change in production)

**Dashboards:**
- API Performance Dashboard
- System Resources Dashboard
- Business Metrics Dashboard

**Enabling Monitoring Stack:**
```bash
docker-compose --profile monitoring up -d
```

---

## Security and Secrets Management

### GitHub Secrets Required

**For Deployment:**
- `RAILWAY_TOKEN` - Railway deployment token
- `SENTRY_DSN` - Sentry error tracking DSN
- `OPENAI_API_KEY` - OpenAI API key
- `SYNAPSE_JWT_SECRET_KEY` - JWT signing secret

**For Release:**
- `GITHUB_TOKEN` - Automatically provided by GitHub
- `HOMEBREW_TOKEN` - Homebrew formula update token (optional)

### Environment Variables

**Critical Secrets:**
```bash
# NEVER commit these to version control
SYNAPSE_JWT_SECRET_KEY=<strong-random-key>
OPENAI_API_KEY=sk-...
SENTRY_DSN=https://...
POSTGRES_PASSWORD=<strong-password>
```

**Generate Secrets:**
```bash
# Generate JWT secret
python -c "import secrets; print(secrets.token_urlsafe(32))"

# Generate PostgreSQL password
python -c "import secrets; print(secrets.token_urlsafe(24))"
```

### Security Best Practices

1. **Environment Variables:** Always use environment variables for secrets
2. **Least Privilege:** Grant minimal permissions to service accounts
3. **Rotation:** Rotate secrets regularly (every 90 days)
4. **Audit Logs:** Enable audit logging for all environments
5. **Network Security:** Use HTTPS/TLS for all external communication
6. **Container Security:** Run containers as non-root user
7. **Dependency Scanning:** Automated vulnerability scanning in CI

---

## Rollback Procedures

### Automatic Rollback

The deploy workflow includes automatic rollback on failure:
- Health check failures
- Smoke test failures
- Deployment errors

### Manual Rollback

**Railway Platform:**
```bash
# View deployment history
railway deployments list --service synapse-prod

# Rollback to previous deployment
railway deployments rollback <deployment-id>
```

**Docker Deployment:**
```bash
# Tag previous working version
docker pull ghcr.io/<org>/synapse-graph-rag:v0.0.9

# Retag as latest
docker tag ghcr.io/<org>/synapse-graph-rag:v0.0.9 synapse-graph-rag:latest

# Restart services
docker-compose -f docker-compose.prod.yml up -d
```

**Kubernetes Deployment:**
```bash
# Rollback to previous revision
kubectl rollout undo deployment/synapse-api -n synapse

# Rollback to specific revision
kubectl rollout undo deployment/synapse-api --to-revision=5 -n synapse

# Check rollout status
kubectl rollout status deployment/synapse-api -n synapse
```

### Rollback Verification

After rollback, verify:
1. Health check endpoints return 200 OK
2. API documentation is accessible
3. Query functionality works
4. No error spikes in Sentry
5. Metrics show normal operation

---

## Troubleshooting

### CI/CD Pipeline Issues

**Problem:** Tests failing in CI but passing locally

**Solution:**
```bash
# Run tests with CI environment variables
SKIP_SPACY_IMPORT=1 GRAPH_RAG_EMBEDDING_PROVIDER=mock pytest tests/

# Use exact Python version from CI
pyenv install 3.11.x
pyenv local 3.11.x
```

**Problem:** Docker build fails

**Solution:**
```bash
# Check Docker build locally
docker build -t synapse-test .

# Check build logs
docker build --progress=plain -t synapse-test .

# Clean Docker cache
docker builder prune -f
```

**Problem:** Deployment health checks failing

**Solution:**
```bash
# Check service logs
railway logs --service synapse-prod --tail 100

# Test health endpoint manually
curl -v https://synapse.neoforge.dev/health

# Check Memgraph connectivity
curl https://synapse.neoforge.dev/api/v1/health
```

### Deployment Issues

**Problem:** Services not starting

**Solution:**
```bash
# Check container logs
docker-compose logs graph-rag

# Check environment variables
docker-compose config

# Verify secrets are set
echo $SYNAPSE_JWT_SECRET_KEY | wc -c  # Should be > 30
```

**Problem:** Memgraph connection timeout

**Solution:**
```bash
# Check Memgraph is running
docker ps | grep memgraph

# Test Memgraph connection
docker exec -it synapse-memgraph mgconsole

# Check network connectivity
docker network inspect synapse_graph-network
```

**Problem:** High memory usage

**Solution:**
```bash
# Check resource usage
docker stats

# Adjust memory limits in docker-compose.prod.yml
deploy:
  resources:
    limits:
      memory: 4G  # Increase if needed
```

### Monitoring Issues

**Problem:** Sentry not capturing errors

**Solution:**
```bash
# Verify Sentry DSN is set
echo $SENTRY_DSN

# Check Sentry initialization in logs
grep "Sentry initialized" logs/api.log

# Test Sentry manually
python -c "from graph_rag.observability.sentry_config import capture_message; capture_message('test')"
```

**Problem:** Prometheus not scraping metrics

**Solution:**
```bash
# Check Prometheus targets
curl http://localhost:9090/api/v1/targets

# Test metrics endpoint
curl http://localhost:8000/metrics

# Check Prometheus configuration
docker exec synapse-prometheus cat /etc/prometheus/prometheus.yml
```

---

## Quick Reference

### Common Commands

```bash
# Start development environment
docker-compose up -d

# Start production environment
docker-compose -f docker-compose.prod.yml up -d

# Start with monitoring
docker-compose -f docker-compose.prod.yml --profile monitoring up -d

# View logs
docker-compose logs -f graph-rag

# Run tests
pytest tests/ -v

# Build Docker image
docker build -t synapse-graph-rag:latest .

# Deploy to staging
git push origin develop

# Deploy to production
git push origin main

# Create release
git tag v0.1.0
git push origin v0.1.0

# Manual deployment
railway up --service synapse-prod --environment production
```

### Health Check URLs

- **Local Development:** `http://localhost:8000/health`
- **Staging:** `https://staging.synapse.neoforge.dev/health`
- **Production:** `https://synapse.neoforge.dev/health`

### Support and Escalation

For deployment issues:
1. Check this documentation
2. Review GitHub Actions logs
3. Check Sentry for errors
4. Review service logs in Railway/Kubernetes
5. Escalate to DevOps team if issue persists

---

## Maintenance and Updates

### Regular Maintenance Tasks

**Weekly:**
- Review Sentry error reports
- Check CI/CD pipeline success rate
- Review security scan results

**Monthly:**
- Rotate secrets
- Update dependencies
- Review and optimize resource usage
- Update documentation

**Quarterly:**
- Disaster recovery drill
- Performance optimization review
- Security audit
- Infrastructure cost optimization

### Updating the Pipeline

When modifying CI/CD workflows:
1. Test changes in a feature branch
2. Review workflow syntax with `act` (local GitHub Actions runner)
3. Document changes in this file
4. Get approval from DevOps team
5. Merge to `develop` first for testing
6. Merge to `main` after validation

---

**Document Version:** 1.0
**Last Reviewed:** 2026-01-26
**Next Review:** 2026-04-26
