# Synapse Graph-RAG - Deployment Guide

**Generated:** 2026-01-21T03:10:45.785219
**Project:** Synapse Graph-RAG
**Location:** `neoforge-dev/synapse-graph-rag/`

---

## Prerequisites

### Required
- **Python 3.10+** - Check with `python3 --version`
- **Docker & Docker Compose** - For Memgraph
- **uv** - Python dependency management (Astral)
- **Internet access** - For NLP model downloads

### Recommended
- **Memgraph** - Via Docker Compose (included)
- **PostgreSQL** - For production (optional, can use Memgraph)

---

## Quick Start

### Step 1: Install Dependencies
```bash
cd neoforge-dev/synapse-graph-rag

# Install using uv (recommended)
make install-dev
# Or: uv pip install -e .[dev]

# Download NLP models
make download-nlp-data
```

### Step 2: Start Infrastructure
```bash
# Start Memgraph via Docker Compose
make run-memgraph
# Or: docker-compose -f tools/docker/docker-compose.yml up -d memgraph

# Verify Memgraph is running
docker ps | grep memgraph
```

### Step 3: Configure Environment
```bash
# Copy example environment file
cp .env.example .env

# Edit .env with your settings
# Key variables:
# - SYNAPSE_MEMGRAPH_HOST=localhost
# - SYNAPSE_MEMGRAPH_PORT=7687
# - SYNAPSE_API_HOST=0.0.0.0
# - SYNAPSE_API_PORT=8000
```

### Step 4: Start API Server
```bash
# Start FastAPI server
make run-api
# Or: uv run python -m graph_rag.api.main

# Verify API is running
curl http://localhost:8000/health
```

---

## Production Deployment

### Option 1: Docker Compose (Recommended for Staging)

```bash
# Start all services
make up
# Or: docker-compose -f tools/docker/docker-compose.yml up -d

# Check logs
make logs-memgraph
docker-compose logs -f api
```

### Option 2: Kubernetes (Production)

```bash
# Apply Kubernetes manifests
kubectl apply -f k8s/

# Verify pods
kubectl get pods -n synapse

# Check services
kubectl get svc -n synapse
```

### Option 3: Railway/Cloudflare (Managed)

See infrastructure-specific guides in `infrastructure/` directory.

---

## Environment Variables

### Required Variables

```bash
# Memgraph Connection
SYNAPSE_MEMGRAPH_HOST=localhost
SYNAPSE_MEMGRAPH_PORT=7687
SYNAPSE_MEMGRAPH_USER=memgraph
SYNAPSE_MEMGRAPH_PASSWORD=memgraph

# API Configuration
SYNAPSE_API_HOST=0.0.0.0
SYNAPSE_API_PORT=8000

# LLM Provider (choose one)
SYNAPSE_LLM_TYPE=openai  # or mock, anthropic
SYNAPSE_OPENAI_API_KEY=sk-...  # if using OpenAI
```

### Optional Variables

```bash
# Authentication (Enterprise)
SYNAPSE_ENABLE_AUTHENTICATION=true
SYNAPSE_JWT_SECRET_KEY=your-secret-key

# Vector Store
SYNAPSE_VECTOR_STORE_TYPE=simple  # or faiss, pinecone

# Entity Extraction
SYNAPSE_ENTITY_EXTRACTOR_TYPE=spacy  # or mock

# Embedding Provider
SYNAPSE_EMBEDDING_PROVIDER=sentencetransformers  # or openai
```

---

## Post-Deployment Verification

### Health Checks

```bash
# API Health
curl http://localhost:8000/health

# API Docs
open http://localhost:8000/docs

# Memgraph Connection (via API)
curl http://localhost:8000/api/v1/health
```

### Functional Tests

```bash
# Run test suite
make test

# Run integration tests (requires Memgraph)
make test-memgraph

# Run all tests
make test-all
```

### Performance Checks

```bash
# Check API response time
time curl http://localhost:8000/health

# Monitor resource usage
docker stats
```

---

## Troubleshooting

### Memgraph Connection Failed

```bash
# Check if Memgraph is running
docker ps | grep memgraph

# Check Memgraph logs
docker logs <memgraph-container-id>

# Verify connection string
echo $SYNAPSE_MEMGRAPH_HOST
echo $SYNAPSE_MEMGRAPH_PORT
```

### API Not Starting

```bash
# Check Python version
python3 --version  # Should be 3.10+

# Check dependencies
uv pip list

# Check logs
tail -f logs/api.log  # if logging to file
```

### Dependencies Missing

```bash
# Reinstall dependencies
make install-dev

# Download NLP models
make download-nlp-data

# Verify installation
python3 -c "import graph_rag; print('OK')"
```

---

## Monitoring

### Health Endpoints

- **API Health:** `GET /health`
- **API Docs:** `GET /docs`
- **OpenAPI Spec:** `GET /openapi.json`

### Metrics (if Prometheus enabled)

- **Metrics:** `GET /metrics`

---

## Rollback Procedures

If deployment fails:

1. **Stop services:**
   ```bash
   make down
   # Or: docker-compose down
   ```

2. **Restore previous version:**
   ```bash
   git checkout <previous-tag>
   ```

3. **Rebuild and redeploy:**
   ```bash
   make install-dev
   make up
   ```

---

## Security Considerations

- ✅ **Secrets:** Use environment variables, never hardcode
- ✅ **Authentication:** Enable JWT auth for production
- ✅ **Network:** Use HTTPS in production
- ✅ **Dependencies:** Regularly audit with `uv pip-audit`

---

**Last Updated:** 2026-01-21T03:10:45.785222
