# Troubleshooting Guide

**Last Updated**: 2025-11-09

Comprehensive troubleshooting guide for Synapse Graph-RAG. This guide covers common issues, diagnostic steps, and solutions for development and production environments.

## Table of Contents

- [Quick Diagnostics](#quick-diagnostics)
- [Common Installation Issues](#common-installation-issues)
- [Memgraph Connection Issues](#memgraph-connection-issues)
- [Vector Store Problems](#vector-store-problems)
- [Authentication Failures](#authentication-failures)
- [API Server Errors](#api-server-errors)
- [MCP Integration Issues](#mcp-integration-issues)
- [Development Issues](#development-issues)
- [Performance Issues](#performance-issues)
- [Debug Mode](#debug-mode)
- [Getting Help](#getting-help)

---

## Quick Diagnostics

### System Health Check

Run these commands to quickly diagnose system health:

```bash
# Check overall system status
synapse init check

# Verify service health
synapse compose status

# Test basic connectivity
synapse admin health

# View component versions
synapse --version
```

### Common Quick Fixes

**Services won't start?**
```bash
# Try vector-only mode (no Docker required)
synapse init wizard --vector-only
```

**Getting mock responses?**
```bash
# Check LLM configuration
export SYNAPSE_LLM_TYPE=openai
export SYNAPSE_OPENAI_API_KEY=your_key_here
```

**Import errors?**
```bash
# Reinstall dependencies
uv pip install --upgrade synapse-graph-rag
make install-dev
```

---

## Common Installation Issues

### Issue: `ModuleNotFoundError: No module named 'graph_rag'`

**Symptoms:**
- Import errors when running commands
- Python can't find the package

**Solution:**
```bash
# Install in development mode
uv pip install -e .[dev]

# Or reinstall from scratch
make clean
make install-dev
```

**Verify:**
```bash
python -c "import graph_rag; print(graph_rag.__file__)"
```

---

### Issue: SpaCy model not found

**Symptoms:**
```
OSError: [E050] Can't find model 'en_core_web_sm'
```

**Solution:**
```bash
# Download spaCy model
uv pip install https://github.com/explosion/spacy-models/releases/download/en_core_web_sm-3.8.0/en_core_web_sm-3.8.0-py3-none-any.whl

# Or use the Makefile
make download-nlp-data
```

**Alternative - Use mock extractor:**
```bash
export SYNAPSE_ENTITY_EXTRACTOR_TYPE=mock
```

---

### Issue: NLTK data not found

**Symptoms:**
```
LookupError: Resource punkt not found
```

**Solution:**
```bash
# Download NLTK data
python -m nltk.downloader punkt

# Or run full setup
make download-nlp-data
```

---

### Issue: `mgclient` installation fails

**Symptoms:**
- Errors during `pip install` related to `mgclient`
- Memgraph operations fail

**Solution:**

The system automatically falls back to vector-only mode if Memgraph is unavailable.

```bash
# Option 1: Enable vector-only mode explicitly
export SYNAPSE_VECTOR_ONLY_MODE=true

# Option 2: Enable auto-fallback (default)
export SYNAPSE_AUTO_FALLBACK_VECTOR_MODE=true

# Option 3: Skip graph features during development
export SYNAPSE_DISABLE_GRAPH=true
```

**Note:** `mgclient` is optional for CI/lightweight testing. The system gracefully handles its absence.

---

## Memgraph Connection Issues

### Issue: Cannot connect to Memgraph

**Symptoms:**
```
ConnectionRefusedError: [Errno 61] Connection refused
Could not connect to Memgraph at 127.0.0.1:7687
```

**Diagnosis:**
```bash
# Check if Memgraph is running
docker ps | grep memgraph

# Check port availability
nc -z localhost 7687

# View Memgraph logs
docker-compose logs memgraph
```

**Solutions:**

**1. Start Memgraph:**
```bash
make run-memgraph

# Wait for startup (10-30 seconds)
# Then verify
nc -z localhost 7687
```

**2. Check Docker Compose:**
```bash
# Ensure Docker is running
docker info

# Start all services
docker-compose up -d

# Check service health
docker-compose ps
```

**3. Verify connection settings:**
```bash
# Check environment variables
echo $SYNAPSE_MEMGRAPH_HOST  # Should be 127.0.0.1 or localhost
echo $SYNAPSE_MEMGRAPH_PORT  # Should be 7687

# Override if needed
export SYNAPSE_MEMGRAPH_HOST=localhost
export SYNAPSE_MEMGRAPH_PORT=7687
```

---

### Issue: Memgraph timeout errors

**Symptoms:**
```
TimeoutError: Connection to Memgraph timed out
mgclient.Error: Query execution timed out
```

**Solution:**
```bash
# Increase retry settings
export SYNAPSE_MEMGRAPH_MAX_RETRIES=5
export SYNAPSE_MEMGRAPH_RETRY_DELAY=3

# For integration tests
make test-memgraph
# This includes automatic retry logic with 10 attempts
```

**Check Memgraph resource usage:**
```bash
# View container stats
docker stats memgraph --no-stream

# Increase container resources if needed (docker-compose.yml)
```

---

### Issue: Memgraph test failures

**Symptoms:**
- Integration tests fail with connection errors
- `RUN_MEMGRAPH_TESTS=true` tests timeout

**Solution:**
```bash
# Ensure Memgraph is running first
make run-memgraph

# Wait for Memgraph to be ready
sleep 10

# Run tests with proper environment
MEMGRAPH_HOST=localhost make test-memgraph

# Or run integration tests
RUNNING_INTEGRATION_TESTS=true uv run pytest -m integration
```

---

## Vector Store Problems

### Issue: FAISS import errors

**Symptoms:**
```
ModuleNotFoundError: No module named 'faiss'
```

**Solution:**
```bash
# Install FAISS
uv pip install faiss-cpu>=1.12.0

# Or for GPU support
uv pip install faiss-gpu>=1.12.0

# Verify installation
python -c "import faiss; print(faiss.__version__)"
```

**Alternative - Use simple vector store:**
```bash
export SYNAPSE_VECTOR_STORE_TYPE=simple
```

---

### Issue: Vector store persistence errors

**Symptoms:**
- "Failed to load vector store from disk"
- Embeddings not persisting between sessions

**Diagnosis:**
```bash
# Check vector store path
echo $SYNAPSE_VECTOR_STORE_PATH

# Default is: ~/.graph_rag/vector_store
ls -la ~/.graph_rag/vector_store/
```

**Solutions:**

**1. Verify write permissions:**
```bash
# Check directory permissions
ls -ld ~/.graph_rag/

# Create if missing
mkdir -p ~/.graph_rag/vector_store
chmod 755 ~/.graph_rag/vector_store
```

**2. Enable persistence explicitly:**
```bash
export SYNAPSE_SIMPLE_VECTOR_STORE_PERSISTENT=true
export SYNAPSE_VECTOR_STORE_PATH=/path/to/writable/directory
```

**3. Rebuild vector index:**
```bash
synapse admin rebuild-index
```

---

### Issue: Embedding dimension mismatch

**Symptoms:**
```
ValueError: Embedding dimension mismatch
RuntimeError: FAISS index dimension does not match embeddings
```

**Solution:**
```bash
# Delete existing index and rebuild
rm -rf ~/.graph_rag/vector_store/

# Ensure consistent embedding model
export SYNAPSE_VECTOR_STORE_EMBEDDING_MODEL=all-MiniLM-L6-v2

# Re-ingest documents
synapse store --embeddings your-docs/
```

---

## Authentication Failures

### Issue: JWT token errors

**Symptoms:**
```
401 Unauthorized: Invalid token
422 Unprocessable Entity: Missing JWT secret key
```

**Solution:**
```bash
# Set JWT secret (minimum 32 characters)
export SYNAPSE_JWT_SECRET_KEY=$(python -c "import secrets; print(secrets.token_urlsafe(32))")

# Verify configuration
synapse init check
```

**For development - disable authentication:**
```bash
export SYNAPSE_ENABLE_AUTHENTICATION=false
```

---

### Issue: API key authentication fails

**Symptoms:**
- 403 Forbidden errors
- "Invalid API key" messages

**Solution:**
```bash
# Generate new API key via CLI
synapse admin create-api-key --user your-user

# Use in requests
curl -H "X-API-Key: your-key" http://localhost:8000/api/v1/health
```

---

### Issue: Double API prefix (404 on auth endpoints)

**Symptoms:**
```
404 Not Found: /api/v1/api/v1/auth/login
```

**Status:** FIXED in January 2025 (Epic 19)

**Verification:**
```bash
# All 40 authentication tests should pass
uv run pytest tests/api/test_auth*.py -v

# Check router mounting
curl http://localhost:8000/docs
# Should show /api/v1/auth/* endpoints (not /api/v1/api/v1/auth/*)
```

---

## API Server Errors

### Issue: Port already in use

**Symptoms:**
```
OSError: [Errno 48] Address already in use
```

**Solution:**
```bash
# Find process using port 8000
lsof -ti:8000

# Kill the process
kill -9 $(lsof -ti:8000)

# Or use different port
export SYNAPSE_API_PORT=8001
make run-api
```

---

### Issue: API server won't start

**Symptoms:**
- uvicorn crashes immediately
- Import errors in API modules

**Diagnosis:**
```bash
# Run with verbose logging
export SYNAPSE_API_LOG_LEVEL=DEBUG
make run-api

# Check for syntax errors
uv run ruff check graph_rag/api/
```

**Solution:**
```bash
# Reinstall dependencies
make clean
make install-dev

# Verify configuration
synapse init check
```

---

### Issue: 500 Internal Server Error

**Symptoms:**
- API requests return 500 errors
- No specific error message

**Diagnosis:**
```bash
# Enable debug mode
export DEBUG=true

# Check API logs
docker-compose logs graph-rag

# Or if running locally
tail -f /var/log/synapse/api.log
```

**Solutions:**

**1. Check dependency injection:**
```bash
# Verify all services initialized
curl http://localhost:8000/api/v1/admin/health
```

**2. Review database connections:**
```bash
# Memgraph health
docker-compose exec memgraph mgconsole
```

**3. Check environment variables:**
```bash
env | grep SYNAPSE_
```

---

## MCP Integration Issues

### Issue: MCP server won't start

**Symptoms:**
```
ModuleNotFoundError: No module named 'mcp'
MCP server failed to start
```

**Solution:**
```bash
# Install MCP dependencies
uv pip install -e '.[dev,mcp]'

# Or specifically
uv pip install mcp>=0.0.8

# Start MCP server
synapse mcp start --port 3001
```

---

### Issue: IDE can't connect to MCP server

**Symptoms:**
- VS Code/Claude Desktop shows "Connection refused"
- MCP tools not available

**Diagnosis:**
```bash
# Check if MCP server is running
curl http://localhost:3001/health

# View MCP server logs
synapse mcp logs
```

**Solution:**
```bash
# Restart MCP server with correct port
synapse mcp start --port 3001

# Verify in IDE settings:
# Claude Desktop: ~/.config/claude/config.json
# VS Code: .vscode/settings.json
```

---

## Development Issues

### Issue: Test failures

**Symptoms:**
- `pytest` fails with import errors
- Tests can't connect to services

**Solutions:**

**1. Run tests with correct markers:**
```bash
# Unit tests only (no external dependencies)
make test

# Integration tests (requires Memgraph)
make test-integration

# Memgraph tests
MEMGRAPH_HOST=localhost make test-memgraph

# All tests
make test-all
```

**2. Use test environment variables:**
```bash
# Skip heavy imports for faster tests
SKIP_SPACY_IMPORT=1 GRAPH_RAG_EMBEDDING_PROVIDER=mock uv run pytest tests/

# Mock services
SYNAPSE_LLM_TYPE=mock SYNAPSE_ENTITY_EXTRACTOR_TYPE=mock uv run pytest
```

**3. Run specific test:**
```bash
# Single test file
uv run pytest tests/api/test_search.py -v

# Specific test function
uv run pytest tests/api/test_search.py::test_unified_search_keyword -v
```

---

### Issue: Linting errors

**Symptoms:**
```
ruff check fails with multiple violations
mypy reports type errors
```

**Solution:**
```bash
# Auto-fix formatting issues
make format

# Run linters
make lint

# Fix specific issues manually based on ruff output
uv run ruff check . --fix
```

**Common violations:**
- B904: Exception handling without `from`
- E402: Import placement
- E722: Bare except clauses

See [BACKLOG.md](../BACKLOG.md) for known remaining issues.

---

### Issue: Coverage failures

**Symptoms:**
```
FAILED: Coverage below 85% threshold
```

**Solution:**
```bash
# Run coverage for critical paths
make coverage-hot

# View detailed coverage report
uv run pytest --cov=graph_rag --cov-report=html
open htmlcov/index.html
```

---

## Performance Issues

### Issue: Slow startup time

**Symptoms:**
- API takes >30 seconds to start
- CLI commands hang on import

**Solutions:**

**1. Use lazy imports:**
```bash
# Skip spaCy during lightweight operations
export SKIP_SPACY_IMPORT=1
```

**2. Optimize vector store:**
```bash
# Use optimized FAISS
export SYNAPSE_USE_OPTIMIZED_FAISS=true

# Enable GPU if available
export SYNAPSE_FAISS_USE_GPU=true
```

**3. Reduce model size:**
```bash
# Use smaller embedding model
export SYNAPSE_VECTOR_STORE_EMBEDDING_MODEL=all-MiniLM-L6-v2
```

---

### Issue: Slow queries

**Symptoms:**
- Search/query takes >5 seconds
- API response times >500ms

**Diagnosis:**
```bash
# Check metrics
curl http://localhost:8000/metrics

# Monitor performance
synapse admin metrics
```

**Solutions:**

**1. Enable caching:**
```bash
export SYNAPSE_CACHE_TYPE=memory
export SYNAPSE_CACHE_DEFAULT_TTL=300
```

**2. Optimize chunk size:**
```bash
export SYNAPSE_INGESTION_CHUNK_SIZE=200
export SYNAPSE_INGESTION_CHUNK_OVERLAP=20
```

**3. Tune FAISS parameters:**
```bash
export SYNAPSE_FAISS_NLIST=100
export SYNAPSE_FAISS_M=16
export SYNAPSE_FAISS_EF_SEARCH=50
```

---

### Issue: High memory usage

**Symptoms:**
- OOM (Out of Memory) errors
- System slowdown during ingestion

**Solutions:**

**1. Enable quantization:**
```bash
export SYNAPSE_FAISS_QUANTIZE=true
```

**2. Process documents in batches:**
```bash
# Instead of ingesting entire directory at once
find docs/ -name "*.md" | xargs -n 10 synapse ingest
```

**3. Monitor resource usage:**
```bash
synapse admin metrics
docker stats
```

---

## Cache-Related Issues (Week 45 Performance Optimizations)

### Issue: Low Cache Hit Rates

**Symptoms**:
- Cache statistics show <10% hit rate
- Expected performance improvements not realized
- API response times higher than expected

**Diagnosis**:
```bash
# Check cache statistics
curl http://localhost:18888/api/v1/cache/stats

# Monitor over time
watch -n 5 'curl -s http://localhost:18888/api/v1/search/cache/stats | jq ".hit_rate"'

# Check individual cache performance
curl http://localhost:18888/api/v1/cache/embeddings/stats
curl http://localhost:18888/api/v1/cache/entities/stats
```

**Solutions**:

**1. Increase cache sizes for your workload:**
```bash
export SYNAPSE_EMBEDDING_CACHE_SIZE=5000  # Increase from 1000
export SYNAPSE_ENTITY_CACHE_SIZE=2000     # Increase from 500
export SYNAPSE_SEARCH_CACHE_SIZE=500      # Increase from 100
```

**2. Check cache TTL settings:**
```bash
# If cache expires too quickly, increase TTL
export SYNAPSE_CACHE_SEARCH_TTL=1200      # 20 minutes (from 10)
export SYNAPSE_CACHE_EMBEDDING_TTL=7200   # 2 hours (from 1 hour)
```

**3. Verify caching is enabled:**
```bash
# Check cache configuration
env | grep SYNAPSE_CACHE

# Verify cache type
env | grep SYNAPSE_CACHE_TYPE  # Should be 'memory' or 'redis'
```

**4. Analyze query patterns:**
```bash
# Low hit rates are normal if:
# - Every query is unique (no repeated searches)
# - Content changes frequently (cache invalidation)
# - First-time ingestion (no duplicate embeddings yet)

# Expected hit rates:
# - Search: >50% for typical workloads
# - Embeddings: >60% for batch ingestion with duplicates
# - Entities: >40% for similar documents
```

---

### Issue: Redis Connection Errors

**Symptoms**:
```
ConnectionError: Error 111 connecting to redis.internal:6379
redis.exceptions.ConnectionRefusedError
```

**Diagnosis**:
```bash
# Verify Redis is running
redis-cli ping
# Should respond: PONG

# Check Redis connectivity
redis-cli -h localhost -p 6379 ping

# Check Redis URL configuration
echo $SYNAPSE_REDIS_URL
# Should be: redis://host:port/db
```

**Solutions**:

**1. Start Redis if not running:**
```bash
# Using Docker
docker run -d --name synapse-redis -p 6379:6379 redis:7-alpine

# Or with docker-compose
docker-compose up -d redis
```

**2. Fix Redis URL configuration:**
```bash
# Correct format
export SYNAPSE_REDIS_URL=redis://localhost:6379/0

# For Redis with password
export SYNAPSE_REDIS_URL=redis://:password@localhost:6379/0

# For Redis Sentinel
export SYNAPSE_REDIS_URL=redis+sentinel://localhost:26379/mymaster/0
```

**3. Check network connectivity:**
```bash
# Test TCP connection
nc -zv localhost 6379

# Check Docker networking
docker network inspect bridge | grep synapse

# Restart API after fixing Redis
synapse down && synapse up
```

**4. Fallback to memory cache:**
```bash
# Temporarily use memory cache while fixing Redis
export SYNAPSE_CACHE_TYPE=memory
synapse down && synapse up
```

---

### Issue: Cache Memory Growing Too Large

**Symptoms**:
- API process memory usage increasing over time
- System running out of memory
- Cache not freeing memory with LRU eviction

**Diagnosis**:
```bash
# Monitor memory usage
curl http://localhost:18888/api/v1/admin/system/metrics | jq '.memory'

# Check cache sizes
curl http://localhost:18888/api/v1/cache/stats | jq '.size'

# Monitor over time
watch -n 10 'curl -s http://localhost:18888/api/v1/cache/stats | jq "{embedding: .embeddings.size, entity: .entities.size, search: .search.size}"'
```

**Solutions**:

**1. Reduce cache sizes:**
```bash
export SYNAPSE_EMBEDDING_CACHE_SIZE=500   # Reduce from 1000
export SYNAPSE_ENTITY_CACHE_SIZE=200      # Reduce from 500
export SYNAPSE_SEARCH_CACHE_SIZE=50       # Reduce from 100
```

**2. Reduce TTLs for auto-expiration:**
```bash
export SYNAPSE_CACHE_DEFAULT_TTL=60       # 1 minute instead of 5
export SYNAPSE_CACHE_SEARCH_TTL=120       # 2 minutes
export SYNAPSE_CACHE_EMBEDDING_TTL=600    # 10 minutes instead of 1 hour
```

**3. Manual cache clearing:**
```bash
# Clear all caches (admin endpoint)
curl -X DELETE http://localhost:18888/api/v1/admin/cache/clear

# Invalidate search cache specifically
curl -X POST http://localhost:18888/api/v1/search/cache/invalidate
```

**4. Switch to Redis for distributed memory:**
```bash
# Redis manages memory externally
export SYNAPSE_CACHE_TYPE=redis
export SYNAPSE_REDIS_URL=redis://localhost:6379/0

# Configure Redis maxmemory policy
redis-cli CONFIG SET maxmemory 256mb
redis-cli CONFIG SET maxmemory-policy allkeys-lru
```

---

### Issue: Cache Not Working (Always Cold Performance)

**Symptoms**:
- API response times consistently slow
- Cache statistics show 0 hits
- Performance not improving on repeated queries

**Diagnosis**:
```bash
# Verify caching is enabled
curl http://localhost:18888/api/v1/cache/stats

# Check cache configuration
env | grep SYNAPSE_CACHE

# Test cache with repeated query
curl http://localhost:18888/api/v1/search -d '{"query": "test", "limit": 5}'
curl http://localhost:18888/api/v1/search -d '{"query": "test", "limit": 5}'
# Second call should be faster

# Check logs for cache errors
docker logs synapse-api-1 | grep -i cache
```

**Solutions**:

**1. Verify cache is enabled:**
```bash
# Default should be 'memory'
export SYNAPSE_CACHE_TYPE=memory

# If disabled, enable it
unset SYNAPSE_DISABLE_CACHE  # Remove if set
```

**2. Check for cache invalidation:**
```bash
# Frequent document ingestion may invalidate caches
# Verify cache is not being cleared after each request

# Check ingestion logs
docker logs synapse-api-1 | grep "invalidate"
```

**3. Verify query normalization:**
```bash
# Queries must match exactly for cache hits
# Check if queries have different formatting:

# These are DIFFERENT cache keys:
curl ... -d '{"query": "Test"}'      # Capital T
curl ... -d '{"query": "test"}'      # Lowercase t
curl ... -d '{"query": "test ", ...}' # Trailing space
```

**4. Restart API to reinitialize caches:**
```bash
synapse down && synapse up
```

---

### Performance Optimization Verification

After Week 45 performance sprint, verify these optimizations are active:

**✅ Lazy Loading (Automatic)**:
```bash
# Startup time should be <5 seconds (was ~11s before)
time python -c "from graph_rag.api.main import create_app; create_app()"

# First API query loads libraries (slower)
# Subsequent queries use cached libraries (fast)
```

**✅ Search Caching**:
```bash
# Run same search twice
time curl http://localhost:18888/api/v1/search -d '{"query": "test"}'
# First: 200-400ms
time curl http://localhost:18888/api/v1/search -d '{"query": "test"}'
# Second (cached): <50ms

# Verify cache hits
curl http://localhost:18888/api/v1/search/cache/stats | jq '.hit_rate'
# Should be: >0.0%
```

**✅ Embedding Caching**:
```bash
# Ingest duplicate content
echo "test content" | synapse ingest test1 --stdin
echo "test content" | synapse ingest test2 --stdin

# Check embedding cache hits
curl http://localhost:18888/api/v1/cache/embeddings/stats | jq '.hits'
# Should be: >0 (second ingestion used cached embedding)
```

**✅ Entity Caching**:
```bash
# Process similar documents
curl http://localhost:18888/api/v1/cache/entities/stats | jq '.hit_rate'
# Should increase as similar documents are processed
```

**Target Performance Metrics**:
- Startup time: <5s (lazy loading)
- API response (cache hit): <100ms
- API response (cache miss): <200ms
- Search cache hit rate: >50%
- Embedding cache hit rate: >60% (batch ingestion)
- Entity cache hit rate: >40% (similar documents)

---

## Debug Mode

### Enable Verbose Logging

**API Server:**
```bash
export SYNAPSE_API_LOG_LEVEL=DEBUG
export DEBUG=true
make run-api
```

**CLI Commands:**
```bash
synapse --verbose search "query"
synapse --debug query ask "question"
```

**JSON Structured Logs:**
```bash
export SYNAPSE_API_LOG_JSON=true
# or
export SYNAPSE_JSON_LOGS=true
```

---

### Enable Component-Specific Debug

**Memgraph:**
```bash
# Increase log level in docker-compose.yml
docker-compose up -d memgraph --log-level=TRACE

# View detailed logs
docker-compose logs -f memgraph
```

**Vector Store:**
```bash
# Enable FAISS debug output
export FAISS_DEBUG=1
```

**Authentication:**
```bash
# Log all auth attempts
export SYNAPSE_AUTH_DEBUG=true
```

---

### Trace Request Flow

**Enable request tracing:**
```bash
# API requests
curl -H "X-Request-ID: trace-001" http://localhost:8000/api/v1/search

# CLI with trace
synapse --trace query ask "test question"
```

---

## Getting Help

### Before Reporting Issues

1. **Check existing documentation:**
   - [QUICKSTART.md](QUICKSTART.md) - Setup guide
   - [INSTALLATION.md](INSTALLATION.md) - Installation details
   - [HANDBOOK.md](../HANDBOOK.md) - System architecture
   - [BACKLOG.md](../BACKLOG.md) - Known issues

2. **Run diagnostics:**
   ```bash
   synapse init check
   synapse admin health
   synapse compose status
   ```

3. **Collect logs:**
   ```bash
   # API logs
   docker-compose logs graph-rag > api-logs.txt

   # Memgraph logs
   docker-compose logs memgraph > memgraph-logs.txt

   # System info
   synapse --version > system-info.txt
   env | grep SYNAPSE_ >> system-info.txt
   ```

---

### Reporting Bugs

**Include in bug reports:**
- Synapse version: `synapse --version`
- Python version: `python --version`
- Operating system: `uname -a`
- Steps to reproduce
- Full error message and stack trace
- Configuration (sanitize secrets!)
- Logs (see above)

**Report issues at:**
- GitHub Issues: https://github.com/neoforge-ai/synapse-graph-rag/issues
- Include label: `bug`, `documentation`, or `question`

---

### Community Resources

- **Documentation**: [docs/README.md](../README.md)
- **Architecture Guide**: [docs/reference/ARCHITECTURE.md](../reference/ARCHITECTURE.md)
- **Configuration Reference**: [docs/reference/CONFIGURATION.md](../reference/CONFIGURATION.md)
- **Contributing**: [CONTRIBUTING.md](../../CONTRIBUTING.md)
- **CLAUDE.md**: [CLAUDE.md](../../CLAUDE.md) - Development commands

---

### Emergency Workarounds

**If all else fails:**

**1. Vector-only mode (minimal dependencies):**
```bash
export SYNAPSE_VECTOR_ONLY_MODE=true
export SYNAPSE_DISABLE_GRAPH=true
export SYNAPSE_ENTITY_EXTRACTOR_TYPE=mock
export SYNAPSE_LLM_TYPE=mock
export SYNAPSE_EMBEDDING_PROVIDER=mock
synapse init wizard --vector-only
```

**2. Clean slate:**
```bash
make clean
rm -rf ~/.graph_rag/
docker-compose down -v
make install-dev
make up
```

**3. Minimal test:**
```bash
# Test core functionality
echo "test content" | synapse ingest dummy_path --stdin --meta title=test
synapse search "test"
```

---

## Success Indicators

You know Synapse is working correctly when:

- ✅ `synapse init check` shows all components green
- ✅ `synapse compose status` shows services running (full mode)
- ✅ Questions return intelligent answers (not "Mock response...")
- ✅ Search finds relevant content from ingested documents
- ✅ All authentication tests pass: `uv run pytest tests/api/test_auth*.py`
- ✅ API endpoints respond: `curl http://localhost:8000/api/v1/health`
- ✅ Memgraph is accessible: `nc -z localhost 7687`

---

**Need more help?** Check [docs/README.md](../README.md) for the complete documentation index or run `synapse --help` for CLI usage.
