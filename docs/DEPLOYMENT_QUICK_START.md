# Synapse Graph-RAG - Deployment Quick Start

**5-Minute Production Deployment Guide**

---

## Prerequisites

- Docker and Docker Compose installed
- GitHub account with access to repository
- Railway account (or alternative platform)
- Sentry account for error tracking (optional but recommended)

---

## Quick Deployment Steps

### 1. Environment Setup (2 minutes)

```bash
# Clone repository
git clone https://github.com/neoforge-ai/synapse-graph-rag.git
cd synapse-graph-rag

# Copy production environment template
cp .env.production.example .env.production

# Generate secrets
python -c "import secrets; print('SYNAPSE_JWT_SECRET_KEY=' + secrets.token_urlsafe(32))" >> .env.production
python -c "import secrets; print('POSTGRES_PASSWORD=' + secrets.token_urlsafe(24))" >> .env.production

# Edit .env.production and add:
# - OPENAI_API_KEY=your-key
# - SENTRY_DSN=your-dsn (optional)
```

### 2. Test Locally (2 minutes)

```bash
# Build and start all services
docker-compose -f docker-compose.prod.yml up -d

# Wait for services to start
sleep 30

# Verify health
curl http://localhost:8000/health

# Check API docs
open http://localhost:8000/docs

# Clean up
docker-compose -f docker-compose.prod.yml down
```

### 3. Deploy to Production (1 minute)

**Option A: Railway (Recommended)**

```bash
# Install Railway CLI
npm install -g @railway/cli

# Login to Railway
railway login

# Link to your project
railway link

# Deploy
railway up --service synapse-prod --environment production

# Wait for deployment
sleep 45

# Verify
curl https://synapse.neoforge.dev/health
```

**Option B: GitHub Actions (Automated)**

```bash
# Set GitHub secrets:
# - RAILWAY_TOKEN
# - SENTRY_DSN
# - OPENAI_API_KEY
# - SYNAPSE_JWT_SECRET_KEY

# Push to main branch
git push origin main

# GitHub Actions will automatically:
# 1. Run tests
# 2. Build Docker image
# 3. Deploy to production
# 4. Run health checks
```

---

## Post-Deployment Verification

### Health Checks

```bash
# Comprehensive health
curl https://synapse.neoforge.dev/health | jq '.'

# Liveness probe
curl https://synapse.neoforge.dev/monitoring/health/liveness

# Readiness probe
curl https://synapse.neoforge.dev/monitoring/health/readiness

# System metrics
curl https://synapse.neoforge.dev/monitoring/metrics/system | jq '.'
```

### Smoke Tests

```bash
# API documentation
curl https://synapse.neoforge.dev/docs

# API health endpoint
curl https://synapse.neoforge.dev/api/v1/health

# Monitoring endpoints
curl https://synapse.neoforge.dev/monitoring/info | jq '.'
```

---

## Common Commands

```bash
# Deploy to staging
make -f Makefile.deployment deploy-staging

# Deploy to production
make -f Makefile.deployment deploy-production

# Check production status
make -f Makefile.deployment status-production

# View logs
make -f Makefile.deployment logs-production

# Rollback production
make -f Makefile.deployment rollback-production

# Database backup
make -f Makefile.deployment db-backup

# Security scan
make -f Makefile.deployment security-scan
```

---

## Monitoring Setup

### Sentry Error Tracking

```bash
# Set environment variable
export SENTRY_DSN=https://xxx@sentry.io/xxx

# Restart services to apply
railway restart --service synapse-prod
```

### Prometheus + Grafana (Optional)

```bash
# Start monitoring stack locally
docker-compose -f docker-compose.prod.yml --profile monitoring up -d

# Access dashboards
# Prometheus: http://localhost:9090
# Grafana: http://localhost:3000 (admin/admin)
```

---

## Troubleshooting

### Deployment Failed

```bash
# Check logs
railway logs --service synapse-prod --tail 100

# Check GitHub Actions
# Visit: https://github.com/your-repo/actions

# Manual rollback
railway deployments rollback --service synapse-prod
```

### Health Check Failed

```bash
# Check all services are running
railway status

# Check environment variables
railway variables --service synapse-prod

# Test Memgraph connection
railway run --service synapse-prod -- python -c "from graph_rag.infrastructure.graph_stores.memgraph_store import MemgraphGraphRepository; print('OK')"
```

### High Memory Usage

```bash
# Check resource usage
railway metrics --service synapse-prod

# Adjust resources in Railway dashboard
# Settings → Resources → Increase memory limit
```

---

## Security Checklist

Before going live:

- [ ] Changed default passwords
- [ ] Generated strong JWT secret
- [ ] Configured HTTPS/TLS
- [ ] Enabled authentication
- [ ] Set up Sentry error tracking
- [ ] Configured CORS properly
- [ ] Reviewed environment variables
- [ ] Set up database backups
- [ ] Configured rate limiting
- [ ] Reviewed security headers

---

## Next Steps

1. **Set up monitoring**: Configure Sentry and Prometheus
2. **Configure backups**: Automated database backups
3. **Set up alerts**: Configure alerting for critical issues
4. **Load testing**: Test application under load
5. **Documentation**: Update API documentation
6. **CI/CD**: Configure automated deployments

---

## Support

- Documentation: `/Users/bogdan/work/FORGE/neoforge-dev/synapse-graph-rag/docs/CICD_SETUP.md`
- Issues: https://github.com/neoforge-ai/synapse-graph-rag/issues
- Sentry: Check error reports at sentry.io

---

**Deployment Time: ~5 minutes**
**Production Ready: ✅**
