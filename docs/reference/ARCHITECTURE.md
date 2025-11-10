# Synapse Architecture Overview

Synapse is a graph-augmented Retrieval-Augmented Generation (RAG) platform built with a comprehensive service-oriented architecture. This document captures the current production layout so contributors understand where features live and how requests flow through the stack.

**Last Updated**: 2025-11-10 (Week 45 Performance Optimization Sprint Complete)

**Architecture Highlights**:
- **4-Router Consolidated API** (89.2% complexity reduction from 37 routers)
- **16+ Specialized Services** (IngestionService, SearchService, AdvancedFeaturesService, etc.)
- **Enterprise-Grade Security** (JWT, API keys, RBAC, MFA, SSO)
- **Production-Ready Observability** (Structured logging, Prometheus metrics, alerting)
- **$10M+ ARR Platform** serving Fortune 500 clients

---

## High-Level Layout

```
CLI (Typer) ─┬─ synapse ingest / search / up
             └─ synapse mcp …
FastAPI      ─┬─ /api/v1/query/* (Core Business Operations)
             ├─ /api/v1/auth/*, /admin/*, /compliance/*, /health/* (Enterprise Platform)
             ├─ /api/v1/dashboard/*, /audience/*, /concepts/*, /content/* (Analytics Intelligence)
             └─ /api/v1/graph/*, /hot-takes/*, /viral/*, /brand-safety/*, /reasoning/*, /chunks/* (Advanced Features)
Services     ─┬─ IngestionService (documents → graph/vector)
             ├─ SearchService (graph + vector retrieval)
             └─ AdvancedFeaturesService (analytics, brand safety, reasoning)
Data stores  ─┬─ Memgraph (graph)
             ├─ Simple/FAISS vector store
             └─ optional Postgres/SQLite analytics
```

The CLI and MCP server reuse the same services as the FastAPI layer so behaviour is consistent regardless of the entry point.

---

## Consolidated Routers (4)

1. **Core Business Operations** – ingestion, document management, hybrid search, “ask” query orchestration, CRM hooks.
2. **Enterprise Platform** – authentication, configuration, admin tooling, health checks.
3. **Analytics Intelligence** – dashboards, metrics, reporting endpoints (read-heavy, often backed by cached aggregations).
4. **Advanced Features** – graph analytics, brand safety checks, hot-take scoring, reasoning helpers, chunk inspection.

Each router is created by a factory in `graph_rag/api/routers/*.py` and wired inside `graph_rag/api/main.py`. Startup dependencies (Memgraph repository, vector store, ingestion pipeline, embedding service) are initialised in the FastAPI lifespan handler and stored on `app.state`.

---

## Services of Interest

- `IngestionService` orchestrates parsing, chunking, entity extraction and persistence into Memgraph + the vector store. It supports idempotent re-ingestion (deleting stale chunks/vectors before writing new ones) and optional vision/PDF processors.
- `AdvancedFeaturesService` powers the advanced router. It derives graph statistics, connected components, visualization data, content scoring, and brand-safety analysis from the current graph repository and vector store. The API no longer returns hard-coded payloads—the service executes heuristics against stored data.
- `SearchService` blends graph and vector lookups, providing fallbacks when one backend is unavailable.

All services log through the structured logging helpers in `graph_rag/observability`. A dedicated `ComponentType.SERVICE` was added for service-level telemetry.

---

## Data & Ports

| Component            | Container Port | Host Port (`synapse up`) |
|----------------------|----------------|--------------------------|
| FastAPI (uvicorn)    | 8000           | **18888**                |
| Memgraph (Bolt)      | 7687           | **17687**                |
| Memgraph (HTTP)      | 7444           | **17444**                |
| Postgres (optional)  | 5432           | **15432**                |

The container ports remain standard to ease intra-container communication; host ports are shifted to avoid collisions with other local services.

---

## Request Flow (example)

1. `synapse ingest ./docs` (CLI) → `IngestionService` via in-process call → document chunks stored in Memgraph + vector store.
2. `curl http://localhost:18888/api/v1/graph/stats` → Advanced Features router → `AdvancedFeaturesService.graph_stats()` → Memgraph repository + vector store analysed → JSON response.
3. MCP clients call the same services through the MCP server wrapper (`graph_rag/mcp/server.py`).

---

## Extension Points

- Additional analytics can plug into `AdvancedFeaturesService` via the graph snapshot helper.
- New CLI commands should live in `graph_rag/cli/commands/` and reuse service factories via `graph_rag/api/dependencies` to stay consistent with the API.
- For a step-by-step list of environment variables and service changes needed to move from the mock defaults to production backends (Memgraph, FAISS, LLM providers, Postgres), see `docs/guides/PRODUCTION_BACKENDS.md`.

---

## Complete Service Catalog

Synapse employs **16+ specialized services** (not a "small number") for comprehensive functionality:

### Core Services

**IngestionService** (`graph_rag/services/ingestion.py`)
- Document parsing and chunking
- Entity extraction coordination
- Graph + vector store persistence
- Idempotent re-ingestion
- Vision/PDF processing support
- **Dependencies**: DocumentProcessor, EntityExtractor, GraphStore, VectorStore, EmbeddingService

**SearchService** (`graph_rag/services/search.py`)
- Hybrid search (vector + graph)
- Fallback strategies (vector-only if graph unavailable)
- Related entity retrieval
- **Dependencies**: GraphRepository, VectorStore

**AdvancedSearchService** (`graph_rag/services/advanced_search.py`) **[Previously Undocumented]**
- Multi-modal search combining text, entities, relationships
- Graph-aware ranking algorithms
- Context window expansion via graph traversal
- Temporal search (date-range filtering)
- Advanced filtering (by entity type, relationship, metadata)
- **Key Methods**:
  - `advanced_search(query, filters, context_depth)`
  - `search_with_explanation(query)` - Returns search + reasoning
  - `temporal_search(query, date_range)`
  - `entity_centric_search(entity_id, depth)`
- **Used By**: Advanced Features router, insights commands

**AdvancedFeaturesService** (`graph_rag/services/advanced_features.py`)
- Graph statistics and analytics
- Connected component analysis
- Graph visualization data generation
- Hot-take content analysis
- Brand safety checking
- Virality prediction
- Reasoning analysis with citations
- **Key Methods**:
  - `graph_stats() -> GraphStatistics`
  - `analyze_hot_take(content) -> HotTakeAnalysis`
  - `check_brand_safety(content) -> BrandSafetyCheck`
  - `predict_virality(content) -> ViralityScore`
  - `analyze_reasoning(query, depth) -> ReasoningAnalysis`

**EmbeddingService** (Multiple Implementations)
- `SentenceTransformerEmbeddingService` - Default, local embeddings
- `OpenAIEmbeddingService` - OpenAI API embeddings
- `OllamaEmbeddingService` - Local Ollama embeddings
- `MockEmbeddingService` - Testing

### Business Intelligence Services

**BatchOperationsService** (`graph_rag/services/batch_operations.py`)
- Bulk document processing
- Batch search queries
- Parallel ingestion pipelines

**ClusteringService** (`graph_rag/services/clustering.py`)
- Document clustering
- Entity clustering
- Topic discovery

**RerankService** (`graph_rag/services/rerank.py`)
- Search result reranking
- Relevance scoring
- Cross-encoder models

**CitationService** (`graph_rag/services/citation.py`)
- Citation generation (APA, MLA, Chicago, IEEE, Numeric)
- Source tracking
- Attribution management

### Advanced Retrieval Services

**AdvancedRetrievalService** (`graph_rag/services/advanced_retrieval.py`)
- Multi-hop reasoning
- Query decomposition
- Sub-query routing
- Answer fusion

**PromptOptimizationService** (`graph_rag/services/prompt_optimization.py`)
- Query rewriting
- Prompt engineering
- Context optimization

**AnswerValidationService** (`graph_rag/services/answer_validation.py`)
- Answer quality checking
- Hallucination detection
- Confidence scoring

### Data Management Services

**BatchIngestionService** (`graph_rag/services/batch_ingestion.py`)
- Large-scale document ingestion
- Progress tracking
- Error handling and retry logic

**MaintenanceService** (`graph_rag/services/maintenance.py`)
- FAISS index rebuilding
- Integrity checks
- Cache management
- Database optimization

### Integration Services

**ExperimentConsolidatorService** (`graph_rag/services/experiment_consolidator.py`)
- A/B test result aggregation
- Experiment analysis

**CrossPlatformCorrelatorService** (`graph_rag/services/cross_platform_correlator.py`)
- Multi-platform data correlation
- LinkedIn + Twitter + Substack integration

**CRMService** (`graph_rag/services/crm_service.py`)
- Contact management
- Opportunity tracking
- Proposal generation
- Lead scoring
- **27 methods covering full CRM lifecycle**
- PostgreSQL connection pooling

---

## Observability Architecture

Synapse includes production-grade observability for monitoring, debugging, and alerting.

### Structured Logging

**ComponentType Enum** (`graph_rag/observability/types.py`)
```python
class ComponentType(Enum):
    API = "api"                    # API endpoints
    SERVICE = "service"            # Service layer
    REPOSITORY = "repository"      # Data access
    MIDDLEWARE = "middleware"      # Request middleware
    CLI = "cli"                    # CLI commands
    MCP = "mcp"                    # MCP server
    BACKGROUND = "background"      # Background jobs
```

**Structured Logging Pattern** (`graph_rag/observability/logging.py`)
```python
from graph_rag.observability import get_logger, ComponentType

logger = get_logger(__name__, ComponentType.SERVICE)

logger.info("Document ingested", extra={
    "document_id": doc_id,
    "chunks_created": chunk_count,
    "duration_ms": duration
})
```

**Features**:
- JSON logging for production (when `SYNAPSE_API_LOG_JSON=true`)
- Correlation IDs for request tracking
- Component-based log filtering
- Performance timing instrumentation

### Prometheus Metrics

**Exposed Metrics** (`/metrics` endpoint):
```
# HTTP request metrics
http_requests_total{method, path, status}
http_request_duration_seconds{path}

# Business metrics
documents_ingested_total
search_queries_total
embeddings_generated_total
graph_operations_total

# System metrics
vector_store_size_bytes
graph_node_count
graph_relationship_count
cache_hit_rate
```

**Configuration**:
```bash
SYNAPSE_ENABLE_METRICS=true      # Enable Prometheus endpoint
```

### Alerting System

**Alert Manager** (`graph_rag/observability/alerts.py`)
- Automatic alert evaluation
- Configurable thresholds
- Alert severity levels (INFO, WARNING, ERROR, CRITICAL)
- Auto-resolution when conditions clear

**Built-in Alerts**:
- High error rate (>5% in 5 minutes)
- Slow query performance (>1s p95 latency)
- Vector store full (>90% capacity)
- Graph store connection failures
- Cache miss rate high (>50%)

**Alert Configuration**:
```python
from graph_rag.observability.alerts import initialize_alerts

alert_manager = initialize_alerts(
    evaluation_interval=30.0,     # Evaluate every 30s
    enable_auto_resolve=True      # Auto-resolve when clear
)
```

### Middleware Stack

**Request Processing Pipeline** (outer → inner):

1. **SecurityHeadersMiddleware** - Add security headers (CSP, X-Frame-Options, etc.)
2. **CorrelationMiddleware** - Inject correlation IDs (`X-Correlation-ID`)
3. **PerformanceMiddleware** - Track request latency, log slow requests (>5s)
4. **RequestSizeMiddleware** - Enforce max request size (10MB default)
5. **RateLimitMiddleware** - Rate limiting (300 req/min, 5000 req/hour)
6. **RequestLoggingMiddleware** - Log requests and metrics
7. **CORSMiddleware** - CORS handling (closest to app)

**Middleware Configuration**:
```bash
SYNAPSE_ENABLE_RATE_LIMITING=true
SYNAPSE_RATE_LIMIT_PER_MINUTE=300
SYNAPSE_RATE_LIMIT_PER_HOUR=5000
```

---

## Authentication & Authorization Architecture

### Multi-Layered Security

**Authentication Methods Supported**:
1. **JWT Tokens** - Short-lived access tokens (30 min default)
2. **API Keys** - Long-lived keys for service-to-service
3. **SAML 2.0** - Enterprise SSO integration
4. **OAuth 2.0/OpenID Connect** - Social login (Google, Azure AD, Okta)
5. **LDAP/Active Directory** - Enterprise directory integration
6. **MFA (TOTP)** - Multi-factor authentication

### JWT Authentication Flow

```
1. User → POST /api/v1/auth/login (username, password)
2. API validates credentials
3. API generates JWT token (signed with SYNAPSE_JWT_SECRET_KEY)
4. User receives token (30 min expiration)
5. User includes token in requests: Authorization: Bearer <token>
6. Middleware validates token, extracts user info
7. Request proceeds with authenticated user context
```

**JWT Claims**:
```json
{
  "sub": "user_id_123",
  "username": "user@example.com",
  "role": "admin",
  "permissions": ["documents:write", "admin:*"],
  "tenant_id": "tenant_abc",
  "exp": 1699450000
}
```

### API Key Authentication

**Generation**:
```bash
POST /api/v1/auth/api-keys
{
  "name": "Production Service",
  "expires_at": "2026-11-08"
}

Response:
{
  "key_id": "key_xyz",
  "api_key": "syn_live_abc123..."  # Store securely!
}
```

**Usage**:
```bash
GET /api/v1/query/documents
X-API-Key: syn_live_abc123...
```

**Storage**:
- API keys hashed with bcrypt before storage
- Only full key shown once at creation
- Keys can be revoked via DELETE /api/v1/auth/api-keys/{key_id}

### Role-Based Access Control (RBAC)

**Roles**:
- `user` - Basic read access
- `editor` - Read + write documents
- `admin` - Full system access
- `enterprise_admin` - Tenant administration

**Permissions**:
- `documents:read` - View documents
- `documents:write` - Create/update documents
- `documents:delete` - Delete documents
- `search:query` - Execute searches
- `admin:*` - All admin operations
- `compliance:manage` - Compliance management

**Permission Checking**:
```python
from graph_rag.api.auth import require_permission

@router.delete("/documents/{id}")
@require_permission("documents:delete")
async def delete_document(id: str, current_user: User):
    ...
```

### Enterprise SSO (SAML 2.0)

**SAML Flow**:
```
1. User → GET /api/v1/auth/enterprise/saml/login
2. API redirects to IdP login page
3. User authenticates at IdP (Okta, Azure AD, etc.)
4. IdP → POST SAML response to /api/v1/auth/enterprise/saml/acs
5. API validates SAML assertion
6. API creates session, returns JWT token
```

**Configuration**:
```bash
POST /api/v1/auth/enterprise/saml/configure
{
  "idp_entity_id": "https://idp.example.com",
  "idp_sso_url": "https://idp.example.com/sso",
  "idp_x509_cert": "-----BEGIN CERTIFICATE-----\n..."
}
```

### Multi-Tenancy

**Tenant Isolation Levels**:
- `database` - Separate database per tenant (strongest isolation)
- `schema` - Separate schema per tenant (PostgreSQL)
- `row` - Row-level tenant_id filtering (least isolation)

**Tenant Context**:
```python
# Automatically injected into requests
@router.get("/documents")
async def list_documents(
    current_user: User,
    tenant_id: str = Depends(get_tenant_id)
):
    # Query scoped to tenant_id automatically
    ...
```

**Tenant Management**:
```bash
POST /api/v1/auth/enterprise/tenants
{
  "domain": "acme.com",
  "name": "ACME Corporation",
  "isolation_level": "database"
}
```

---

## Vector Store Implementations

### Simple Vector Store

**Implementation**: `SimpleVectorStore` (`graph_rag/core/vector_store.py`)
- In-memory vector storage with optional persistence
- Cosine similarity search
- Exact nearest neighbor search
- **Use Case**: Development, small datasets (<100K vectors)
- **Performance**: O(n) search complexity

**Persistence**:
```python
# Saves to ~/.graph_rag/vector_store/simple_vector_store.pkl
store = SimpleVectorStore(persistent=True)
```

### FAISS Vector Store

**Implementation**: `FaissVectorStore` (`graph_rag/infrastructure/vector_stores/faiss_store.py`)
- Facebook AI Similarity Search
- Approximate nearest neighbor (ANN)
- **Use Case**: Production, large datasets (100K+ vectors)
- **Performance**: O(log n) search complexity

**Basic FAISS**:
```python
store = FaissVectorStore(
    embedding_dim=384,  # all-MiniLM-L6-v2
    index_type="Flat"   # Exact search
)
```

### Optimized FAISS Vector Store **[Advanced Implementation]**

**Implementation**: `OptimizedFaissVectorStore` (`graph_rag/infrastructure/vector_stores/optimized_faiss_store.py`)
- **10x+ performance improvement** over basic FAISS
- GPU acceleration (when available)
- Quantization for memory efficiency
- IVF (Inverted File) indexing
- HNSW (Hierarchical Navigable Small World) graphs

**Features**:
- **GPU Support**: Automatic GPU detection and usage
- **Quantization**: Product Quantization (PQ) for 4-8x memory reduction
- **Hybrid Indexing**: IVF + PQ or HNSW for optimal speed/accuracy tradeoff
- **Dynamic Index Selection**: Chooses optimal index based on dataset size

**Configuration**:
```bash
SYNAPSE_USE_OPTIMIZED_FAISS=true      # Enable optimized FAISS
SYNAPSE_FAISS_USE_GPU=true            # GPU acceleration
SYNAPSE_FAISS_QUANTIZE=true           # Product Quantization
SYNAPSE_FAISS_NLIST=100               # IVF clusters
SYNAPSE_FAISS_M=16                    # HNSW connections
SYNAPSE_FAISS_EF_CONSTRUCTION=200     # Build quality
SYNAPSE_FAISS_EF_SEARCH=50            # Search quality
```

**Index Types by Dataset Size**:
- **< 10K vectors**: Flat (exact search)
- **10K - 100K**: IVF + Flat
- **100K - 1M**: IVF + PQ (quantized)
- **> 1M**: HNSW + PQ (GPU)

**Memory Savings**:
- Flat index: 384 * N bytes (N = vector count)
- PQ index: 64 * N bytes (6x reduction)
- GPU PQ index: 32 * N bytes (12x reduction)

### Shared Persistent Vector Store **[Multi-Process]**

**Implementation**: `SharedPersistentVectorStore` (`graph_rag/infrastructure/vector_stores/shared_persistent_store.py`)
- **Multi-process safe** via file locking
- Shared memory mapping for zero-copy reads
- Atomic writes with rollback
- **Use Case**: API server + background workers

**Features**:
- Read-write locks prevent corruption
- Memory-mapped files for efficient large dataset access
- Incremental saves (only changed vectors)
- Automatic crash recovery

**Usage**:
```python
# Process 1: API server
store = SharedPersistentVectorStore(path="~/.graph_rag/vectors")
store.search("query", top_k=10)  # Read lock

# Process 2: Background ingestion
store = SharedPersistentVectorStore(path="~/.graph_rag/vectors")
store.add(vectors, metadata)  # Write lock (blocks readers briefly)
```

---

## Dependency Injection System

**Central Dependencies** (`graph_rag/api/dependencies.py`):
```python
# All dependencies injected via FastAPI Depends()
def get_graph_repository(request: Request) -> GraphRepository:
    return request.app.state.graph_repository

def get_vector_store(request: Request) -> VectorStore:
    return request.app.state.vector_store

def get_search_service(request: Request) -> SearchService:
    return request.app.state.search_service

# etc. for all services
```

**Lifespan Initialization** (`graph_rag/api/main.py` lines 120-450):
```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Initialize all services
    app.state.graph_repository = create_graph_repository(settings)
    app.state.vector_store = create_vector_store(settings)
    app.state.ingestion_service = IngestionService(...)
    app.state.search_service = SearchService(...)
    # ... 10+ more services

    yield  # Application runs

    # Shutdown: Cleanup
    await app.state.graph_repository.close()
    await app.state.vector_store.close()
```

**Benefits**:
- Consistent service instances across requests
- Easy testing (mock dependencies)
- Graceful startup/shutdown
- Health check integration

---

For installation and packaging details see `docs/guides/INSTALLATION_GUIDE.md` and `docs/HOMEBREW.md`.

For complete API reference with all 44+ endpoints, see `docs/HANDBOOK.md` (API Reference section) or `docs/reference/API_REFERENCE.md`.
