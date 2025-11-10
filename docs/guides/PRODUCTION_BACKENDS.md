# Enabling Production Backends

Synapse defaults to lightweight mock services so the CLI, API, and tests run without external dependencies. Follow this guide when you are ready to enable the full stack (Memgraph graph store, real LLMs, optional Postgres analytics).

## 1. Memgraph Graph Store

1. Start Memgraph (included in `synapse up`):
   ```bash
   synapse up --wait
   ```

2. Ensure `mgclient` is installed (it ships with the project). If you disabled graph support earlier, unset the flag:
   ```bash
   export SYNAPSE_DISABLE_GRAPH=false
   ```

3. Optional tuning:
   ```bash
   export SYNAPSE_MEMGRAPH_HOST=127.0.0.1
   export SYNAPSE_MEMGRAPH_PORT=17687    # host port from docker-compose
   export SYNAPSE_MEMGRAPH_USER=memgraph
   export SYNAPSE_MEMGRAPH_PASSWORD=your-password
   ```

4. Restart the API/CLI session; `create_graph_repository` will now return `MemgraphGraphRepository` instead of the mock implementation.

## 2. Vector Store Persistence

By default the simple in-memory vector store is used. For persisted embeddings shared across processes, set:
```bash
export SYNAPSE_VECTOR_STORE_TYPE=faiss
export SYNAPSE_VECTOR_STORE_PATH=~/.synapse/faiss_store
```
Run `synapse admin vector-stats` to verify the FAISS index is active.

## 3. LLM Providers

1. Choose a provider via `SYNAPSE_LLM_TYPE` (`openai`, `anthropic`, `ollama`, etc.).
2. Provide credentials:
   ```bash
   export SYNAPSE_LLM_TYPE=openai
   export OPENAI_API_KEY=sk-...
   ```
3. Optional settings:
   ```bash
   export SYNAPSE_LLM_MODEL_NAME=gpt-4o-mini
   export SYNAPSE_LLM_TEMPERATURE=0.3
   ```
4. Restart the API; requests that use the LLM (e.g. `/advanced/` endpoints) now call the real provider.

## 4. Postgres Analytics (Optional)

1. Ensure the Docker service is running (`synapse up` starts Postgres on host port 15432).
2. Configure the URI:
   ```bash
   export SYNAPSE_POSTGRES_URL=postgresql://synapse:synapse_password@127.0.0.1:15432/synapse_business_core
   ```
3. Run any required migrations or analytics scripts before relying on the dashboards.

## 5. Caching & Performance Optimization (Week 45)

Synapse includes high-performance caching for production deployments. The caching system provides:
- **Search result caching**: -200-400ms for repeated queries
- **Embedding caching**: 30% faster ingestion for duplicate content
- **Entity extraction caching**: -20-48ms reduction per extraction

### Memory-Based Caching (Development)

Default configuration uses in-memory caching (suitable for single-instance deployments):

```bash
export SYNAPSE_CACHE_TYPE=memory
export SYNAPSE_CACHE_DEFAULT_TTL=300

# Cache size tuning (optional)
export SYNAPSE_EMBEDDING_CACHE_SIZE=1000    # Default: 1000 embeddings
export SYNAPSE_ENTITY_CACHE_SIZE=500        # Default: 500 extractions
export SYNAPSE_SEARCH_CACHE_SIZE=100        # Default: 100 search results
```

**Memory Impact**: ~1-2MB for default cache sizes

### Redis Caching (Production - Multi-Instance)

For distributed production deployments with multiple API instances, use Redis:

**1. Start Redis**:
```bash
# Using Docker
docker run -d --name synapse-redis \
  -p 6379:6379 \
  redis:7-alpine

# Or add to docker-compose.yml
```

**2. Configure Redis caching**:
```bash
export SYNAPSE_CACHE_TYPE=redis
export SYNAPSE_REDIS_URL=redis://localhost:6379/0

# Production tuning
export SYNAPSE_CACHE_DEFAULT_TTL=600        # 10 minutes
export SYNAPSE_EMBEDDING_CACHE_SIZE=5000    # Larger for production
export SYNAPSE_ENTITY_CACHE_SIZE=2000
export SYNAPSE_SEARCH_CACHE_SIZE=500

# Cache TTL tuning by type
export SYNAPSE_CACHE_EMBEDDING_TTL=3600     # 1 hour (embeddings are stable)
export SYNAPSE_CACHE_SEARCH_TTL=600         # 10 minutes (fresher results)
```

**3. Verify Redis connectivity**:
```bash
# Test Redis connection
redis-cli -h localhost -p 6379 ping
# Should respond: PONG

# Check cache statistics
curl http://localhost:18888/api/v1/cache/stats
```

### Cache Monitoring

Monitor cache performance using the built-in endpoints:

```bash
# Combined cache statistics
curl http://localhost:18888/api/v1/cache/stats
# Returns: {"hits": 1523, "misses": 478, "hit_rate": "76.1%", ...}

# Search cache performance
curl http://localhost:18888/api/v1/search/cache/stats

# Embedding cache performance
curl http://localhost:18888/api/v1/cache/embeddings/stats

# Entity extraction cache performance
curl http://localhost:18888/api/v1/cache/entities/stats
```

**Target Metrics**:
- **Hit rate**: >50% for typical workloads, >70% for repeated queries
- **Response time**: <100ms for cache hits, <200ms for cache misses
- **Memory usage**: Monitor with `/api/v1/admin/system/metrics`

### Cache Tuning Guidelines

**Embedding Cache**:
- **Increase size** for large document batches with duplicate content
- **Increase TTL** for static content collections (e.g., documentation)
- **Decrease size** if memory constrained (minimum: 100)

**Entity Cache**:
- **Increase size** for frequent similar text analysis
- **Decrease if using Mock entity extractor** (lightweight, less benefit)
- Persistent per session (no TTL)

**Search Cache**:
- **Increase size** for high query volume with repeated patterns
- **Decrease TTL** for frequently updated content (minimum: 60s)
- **Invalidate manually** after bulk ingestion: `curl -X POST http://localhost:18888/api/v1/search/cache/invalidate`

### Performance Impact Summary

| Optimization | Cold Performance | Warm Performance (Cache Hit) | Improvement |
|--------------|------------------|------------------------------|-------------|
| Search caching | 200-400ms | <50ms | **-200-400ms** |
| Embedding caching | 500ms per batch | <10ms | **30% faster ingestion** |
| Entity extraction | 50-100ms | 2-5ms | **-20-48ms** |
| **Combined** | Variable | <100ms | **60-80% faster** |

### Production Checklist

Before deploying with caching enabled:

- [ ] Redis running and accessible from all API instances
- [ ] `SYNAPSE_REDIS_URL` configured correctly
- [ ] Cache sizes tuned for workload (monitor memory usage)
- [ ] Cache statistics endpoint accessible
- [ ] Cache invalidation strategy defined (manual vs. TTL-based)
- [ ] Monitoring alerts for low hit rates (<30%)

## 6. Verifying the Setup

```bash
# API health
curl http://localhost:18888/health

# Graph connectivity check
synapse admin graph-stats

# LLM smoke test
synapse query ask "Summarise the current knowledge graph status"
```

If any component fails, review the logs (`synapse compose logs`) and adjust the environment variables accordingly.
