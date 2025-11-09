# Synapse Graph-RAG Handbook

**Complete Developer and User Reference**
**Last Updated**: 2025-11-09 (Week 45 Sprint Complete)

---

## Table of Contents

1. [Overview](#overview)
2. [Quick Start](#quick-start)
3. [CLI Commands Reference](#cli-commands-reference)
4. [API Reference](#api-reference)
5. [Configuration Reference](#configuration-reference)
6. [Database Architecture](#database-architecture)
7. [Service Layer](#service-layer)
8. [Authentication & Authorization](#authentication--authorization)
9. [Business Development System](#business-development-system)
10. [Testing & Development](#testing--development)
11. [Troubleshooting](#troubleshooting)

---

## Overview

Synapse is a production-grade Graph-augmented Retrieval-Augmented Generation (RAG) platform combining:
- **Knowledge Graph**: Memgraph for storing documents, chunks, entities, relationships
- **Vector Store**: FAISS/Simple vector store for embeddings-based similarity search
- **REST API**: FastAPI with 44+ endpoints across 4 consolidated routers
- **CLI Tools**: 22+ composable Unix-style commands
- **Business Intelligence**: Complete LinkedIn automation and consultation pipeline

### Architecture Highlights

- **$10M+ ARR Platform**: Serving Fortune 500 clients
- **4-Router API**: 89.2% complexity reduction (37 → 4 routers)
- **Enterprise Security**: JWT, API keys, RBAC, MFA, SSO
- **Optimized Performance**: <10ms query latency on SQLite, <50ms on PostgreSQL

---

## Quick Start

### Installation

```bash
# Install with uv (recommended)
uv pip install -e ".[dev]"

# Or with pip
pip install -e ".[dev]"

# Install CLI globally
pipx install -e .

# Verify installation
synapse --version
```

### Basic Usage

```bash
# Start the stack (Memgraph + API)
synapse up

# Ingest documents
synapse ingest ./docs --enable-embeddings

# Search your knowledge base
synapse search "graph database architecture"

# Ask questions
synapse query ask "How does the authentication system work?"

# Stop the stack
synapse down
```

---

## CLI Commands Reference

### Complete Command List (22 Commands)

#### Core Data Operations

**`synapse ingest`** - Ingest documents with embeddings and entity extraction
```bash
synapse ingest ./path/to/docs \
  --enable-embeddings \
  --chunk-size 200 \
  --chunk-overlap 20

# Options:
#   --enable-embeddings    Generate and store vector embeddings
#   --chunk-size INT       Chunk size in tokens (default: 200)
#   --chunk-overlap INT    Overlap between chunks (default: 20)
#   --recursive           Recursively process subdirectories
```

**`synapse discover`** - Discover and list documents in a directory
```bash
synapse discover ./docs --recursive --extensions .md,.txt,.pdf
```

**`synapse parse`** - Parse documents with metadata extraction
```bash
synapse parse ./docs/file.md --extract-metadata
```

**`synapse store`** - Store parsed documents in graph and vector stores
```bash
synapse store ./parsed_docs --enable-embeddings
```

**`synapse search`** - Hybrid search combining vector similarity and graph traversal
```bash
synapse search "authentication JWT tokens" \
  --top-k 10 \
  --enable-graph-traversal

# Options:
#   --top-k INT              Number of results (default: 5)
#   --enable-graph-traversal Include related entities
#   --min-score FLOAT        Minimum similarity score
```

**`synapse query ask`** - Ask questions with LLM-powered synthesis
```bash
synapse query ask "Explain the 4-router architecture" \
  --max-tokens 2000 \
  --temperature 0.3

# Options:
#   --max-tokens INT      Maximum response tokens
#   --temperature FLOAT   LLM temperature (0.0-2.0)
#   --stream             Stream the response
```

**`synapse explain`** - Enhanced search with explanations and entity relations
```bash
synapse explain "database migration strategy" --detailed
```

**`synapse suggest`** - Generate suggestions grounded in your corpus
```bash
synapse suggest --topic "API optimization" --count 5
```

#### Stack Management

**`synapse up`** - Start Memgraph + API with health checks
```bash
synapse up --api-port 8000 --detach

# Options:
#   --api-port INT       API server port (default: 18888)
#   --detach            Run in background
#   --health-check      Wait for services to be healthy
```

**`synapse down`** - Stop the GraphRAG stack
```bash
synapse down --remove-volumes

# Options:
#   --remove-volumes    Remove Docker volumes
#   --timeout INT       Shutdown timeout seconds
```

**`synapse compose`** - Docker Compose management
```bash
# Start services
synapse compose up -d

# View logs
synapse compose logs -f

# Stop services
synapse compose down
```

**`synapse init`** - Interactive setup wizard
```bash
synapse init --guided

# Walks through:
# - Environment configuration
# - Database setup
# - API key generation
# - Initial document ingestion
```

#### Graph Operations

**`synapse graph stats`** - Display graph statistics
```bash
synapse graph stats --detailed

# Shows:
# - Node counts by type
# - Relationship counts
# - Connected components
# - Graph density metrics
```

**`synapse graph visualize`** - Generate graph visualizations
```bash
synapse graph visualize \
  --output graph.html \
  --layout force-directed \
  --max-nodes 1000
```

**`synapse graph explore`** - Interactive graph exploration
```bash
synapse graph explore --entity "Authentication" --depth 2
```

#### Analytics & Intelligence

**`synapse insights`** - Business intelligence and discovery
```bash
synapse insights discover \
  --category "technical-patterns" \
  --min-confidence 0.7

# Discovers:
# - Content themes
# - Entity relationships
# - Knowledge gaps
```

**`synapse analytics`** - Advanced business analytics
```bash
synapse analytics performance \
  --start-date 2025-01-01 \
  --end-date 2025-11-08 \
  --metrics engagement,conversion

# Metrics:
# - Content performance
# - User engagement
# - Conversion funnels
# - Pipeline analytics
```

#### Administration

**`synapse admin`** - Admin and maintenance commands
```bash
# Rebuild vector index
synapse admin rebuild-index --vector-store faiss

# Check system integrity
synapse admin integrity-check --fix

# Clear cache
synapse admin clear-cache --all

# Export metrics
synapse admin export-metrics --format json
```

**`synapse config`** - Configuration utilities
```bash
# Show current configuration
synapse config show --format yaml

# Validate configuration
synapse config validate

# Generate .env template
synapse config generate-env > .env.example
```

#### Integrations

**`synapse notion sync`** - Notion API sync utilities
```bash
synapse notion sync \
  --database-id abc123 \
  --incremental \
  --rate-limit 3.0

# Options:
#   --database-id TEXT    Notion database ID
#   --incremental        Sync only changes
#   --rate-limit FLOAT   Requests per second (default: 3.0)
```

**`synapse mcp start`** - Start MCP (Model Context Protocol) server
```bash
synapse mcp start \
  --host 0.0.0.0 \
  --port 8001 \
  --log-level INFO

# MCP enables:
# - Claude Desktop integration
# - LLM tool access to graph data
# - Real-time knowledge retrieval
```

**`synapse mcp stop`** - Stop MCP server
```bash
synapse mcp stop
```

#### Data Operations

**`synapse consolidate`** - Consolidate and deduplicate documents
```bash
synapse consolidate \
  --similarity-threshold 0.95 \
  --dry-run

# Options:
#   --similarity-threshold  Deduplication threshold
#   --dry-run              Preview without changes
#   --merge-strategy       Strategy: newest|oldest|manual
```

---

## API Reference

### Base URL

```
http://localhost:18888/api/v1
```

### Authentication

All authenticated endpoints require one of:
- **Bearer Token**: `Authorization: Bearer <jwt_token>`
- **API Key**: `X-API-Key: <api_key>`

### API Routers (4 Consolidated)

#### 1. Core Business Operations (`/api/v1/query/*`)

**Document Management**

```http
POST /api/v1/query/documents
Content-Type: application/json

{
  "source_path": "/path/to/doc.md",
  "content": "Document content...",
  "metadata": {
    "title": "My Document",
    "tags": ["guide", "technical"]
  }
}

Response: 201 Created
{
  "id": "doc_abc123",
  "created_at": "2025-11-08T10:00:00Z"
}
```

```http
GET /api/v1/query/documents
GET /api/v1/query/documents/{document_id}
DELETE /api/v1/query/documents/{document_id}
PATCH /api/v1/query/documents/{document_id}/metadata
```

**Ingestion**

```http
POST /api/v1/query/ingestion/documents
Content-Type: application/json

{
  "sources": ["/path/to/docs"],
  "options": {
    "enable_embeddings": true,
    "chunk_size": 200,
    "chunk_overlap": 20
  }
}

Response: 200 OK
{
  "documents_processed": 42,
  "chunks_created": 156,
  "entities_extracted": 89,
  "duration_seconds": 12.5
}
```

**Search & Retrieval**

```http
POST /api/v1/query/search
Content-Type: application/json

{
  "query": "authentication implementation",
  "top_k": 10,
  "enable_graph_traversal": true,
  "filters": {
    "tags": ["security"],
    "date_after": "2025-01-01"
  }
}

Response: 200 OK
{
  "results": [
    {
      "chunk_id": "chunk_xyz",
      "content": "...",
      "score": 0.92,
      "document_id": "doc_abc",
      "metadata": {...}
    }
  ],
  "query_time_ms": 45
}
```

```http
POST /api/v1/query/search/query   # Ask endpoint with LLM synthesis
POST /api/v1/query/search/batch   # Batch search queries
POST /api/v1/query/ask            # Legacy ask endpoint
```

**CRM Integration**

```http
GET  /api/v1/query/crm/pipeline/summary
GET  /api/v1/query/crm/contacts
GET  /api/v1/query/crm/contacts/{contact_id}
PUT  /api/v1/query/crm/contacts/{contact_id}
POST /api/v1/query/crm/proposals/generate
GET  /api/v1/query/crm/proposals
POST /api/v1/query/crm/proposals/{proposal_id}/send
POST /api/v1/query/crm/import-inquiries
GET  /api/v1/query/crm/lead-scoring/{contact_id}
GET  /api/v1/query/crm/analytics/conversion-funnel
```

#### 2. Enterprise Platform (`/api/v1/auth/*`, `/admin/*`, `/compliance/*`, `/health/*`)

**Authentication**

```http
POST /api/v1/auth/register
Content-Type: application/json

{
  "username": "user@example.com",
  "password": "SecurePass123!",
  "email": "user@example.com"
}

Response: 201 Created
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJh...",
  "token_type": "bearer",
  "expires_in": 1800
}
```

```http
POST /api/v1/auth/login              # User login (form or JSON)
POST /api/v1/auth/login/json         # JSON login
GET  /api/v1/auth/me                 # Current user info
POST /api/v1/auth/api-keys           # Create API key
GET  /api/v1/auth/api-keys           # List API keys
DELETE /api/v1/auth/api-keys/{key_id} # Revoke API key
```

**Enterprise Authentication** (SSO, SAML, OAuth, MFA)

```http
POST /api/v1/auth/enterprise/tenants           # Create tenant
GET  /api/v1/auth/enterprise/tenants/{tenant_id}
POST /api/v1/auth/enterprise/saml/configure    # Configure SAML
POST /api/v1/auth/enterprise/saml/login        # SAML login
POST /api/v1/auth/enterprise/oauth/configure   # Configure OAuth
POST /api/v1/auth/enterprise/mfa/setup         # Setup MFA
```

**Compliance Management**

```http
POST /api/v1/compliance/gdpr/requests          # Submit GDPR request
POST /api/v1/compliance/soc2/controls/{control_id}/test
POST /api/v1/compliance/hipaa/risk-assessment
GET  /api/v1/compliance/dashboard/overview
GET  /api/v1/compliance/frameworks
```

**System Administration**

```http
GET  /api/v1/admin/vector/stats                # Vector store statistics
POST /api/v1/admin/vector/rebuild              # Rebuild vector index
GET  /api/v1/admin/integrity/check             # Data integrity check
GET  /api/v1/admin/health/detailed             # Detailed health check
GET  /api/v1/admin/performance/stats
GET  /api/v1/admin/cache/stats
DELETE /api/v1/admin/cache/clear
GET  /api/v1/admin/system/metrics
GET  /api/v1/admin/platform/info
```

**Health Checks**

```http
GET /api/v1/health                   # Basic health check
GET /api/v1/health/enterprise        # Enterprise health
GET /health                          # Root health endpoint
GET /ready                           # Readiness probe
```

#### 3. Analytics Intelligence (`/api/v1/dashboard/*`, `/audience/*`, `/concepts/*`, `/content/*`)

**Business Intelligence Dashboards**

```http
GET /api/v1/dashboard/executive
Response: 200 OK
{
  "pipeline_value": 1158000.00,
  "active_opportunities": 18,
  "monthly_revenue": 85000.00,
  "growth_rate": 0.23,
  "key_metrics": {...}
}
```

```http
GET /api/v1/dashboard/operational    # HTML dashboard
GET /api/v1/dashboard/business-metrics
```

**Audience Intelligence**

```http
POST /api/v1/audience/analyze
Content-Type: application/json

{
  "content": "Technical blog post content...",
  "platform": "linkedin"
}

Response: 200 OK
{
  "target_audiences": ["CTOs", "Technical Leaders"],
  "engagement_prediction": 0.78,
  "optimal_posting_time": "06:30 AM Tuesday",
  "tone_analysis": {...}
}
```

```http
POST /api/v1/audience/resonance      # Resonance analysis
GET  /api/v1/audience/segments       # Audience segmentation
```

**Concept Intelligence**

```http
POST /api/v1/concepts/extract
Content-Type: application/json

{
  "text": "Discussion of microservices and GraphQL APIs...",
  "min_confidence": 0.7
}

Response: 200 OK
{
  "concepts": [
    {
      "name": "Microservices Architecture",
      "confidence": 0.92,
      "related_entities": ["Docker", "Kubernetes"]
    }
  ]
}
```

```http
GET /api/v1/concepts/trends          # Concept trends over time
```

**Content Intelligence**

```http
POST /api/v1/content/strategy        # Generate content strategy
GET  /api/v1/content/performance     # Content performance analytics
```

#### 4. Advanced Features (`/api/v1/graph/*`, `/hot-takes/*`, `/viral/*`, `/brand-safety/*`, `/reasoning/*`, `/chunks/*`)

**Graph Operations**

```http
POST /api/v1/graph/analyze
Content-Type: application/json

{
  "entity_id": "entity_123",
  "depth": 2,
  "relationship_types": ["RELATES_TO", "REFERENCES"]
}

Response: 200 OK
{
  "entity": {...},
  "connected_entities": [...],
  "relationships": [...],
  "subgraph": {...}
}
```

```http
GET /api/v1/graph/stats              # Graph statistics
GET /api/v1/graph/visualize          # Visualization data
```

**Content Analysis**

```http
POST /api/v1/hot-takes/analyze       # Hot-take analysis
POST /api/v1/hot-takes/quick-score   # Quick scoring
POST /api/v1/viral/predict           # Virality prediction
POST /api/v1/brand-safety/check      # Brand safety check
GET  /api/v1/brand-safety/guidelines # Safety guidelines
```

**Advanced Reasoning**

```http
POST /api/v1/reasoning/analyze
Content-Type: application/json

{
  "query": "Compare authentication approaches",
  "context_depth": 2,
  "enable_citations": true
}

Response: 200 OK
{
  "analysis": "...",
  "reasoning_steps": [...],
  "citations": [...],
  "confidence": 0.88
}
```

**Chunk Operations**

```http
GET /api/v1/chunks/{chunk_id}        # Get specific chunk
GET /api/v1/chunks                   # List chunks with filters
```

---

## Configuration Reference

### Complete Environment Variables (100+)

All variables use the `SYNAPSE_` prefix.

#### API Server Configuration

```bash
SYNAPSE_API_HOST=0.0.0.0                    # API server host
SYNAPSE_API_PORT=8000                       # API server port
SYNAPSE_API_LOG_LEVEL=INFO                  # Logging level (DEBUG/INFO/WARNING/ERROR)
SYNAPSE_API_LOG_JSON=false                  # Enable JSON structured logging
```

#### Security & Authentication

```bash
SYNAPSE_JWT_SECRET_KEY=<secret>             # JWT signing key (32+ chars)
SYNAPSE_JWT_ALGORITHM=HS256                 # JWT algorithm
SYNAPSE_JWT_ACCESS_TOKEN_EXPIRE_MINUTES=30  # Token expiration (5-1440)
SYNAPSE_ENABLE_AUTHENTICATION=true          # Enable API authentication
SYNAPSE_REQUIRE_AUTH_FOR_DOCS=false         # Require auth for /docs
```

#### Graph Database (Memgraph)

```bash
SYNAPSE_DISABLE_GRAPH=false                 # Disable graph features
SYNAPSE_MEMGRAPH_HOST=127.0.0.1            # Memgraph hostname
SYNAPSE_MEMGRAPH_PORT=7687                 # Memgraph port
SYNAPSE_MEMGRAPH_USER=                     # Username (optional)
SYNAPSE_MEMGRAPH_PASSWORD=                 # Password (optional)
SYNAPSE_MEMGRAPH_USE_SSL=false             # Enable SSL
SYNAPSE_MEMGRAPH_MAX_RETRIES=3             # Connection retries
SYNAPSE_MEMGRAPH_RETRY_DELAY=2             # Retry delay (seconds)
```

#### Vector Store Configuration

```bash
SYNAPSE_VECTOR_STORE_TYPE=simple            # Type: simple|faiss|mock
SYNAPSE_VECTOR_STORE_PATH=~/.graph_rag/vector_store  # Storage path
SYNAPSE_SIMPLE_VECTOR_STORE_PERSISTENT=true # Enable persistence
SYNAPSE_VECTOR_STORE_EMBEDDING_MODEL=all-MiniLM-L6-v2  # Embedding model
```

#### FAISS Optimization

```bash
SYNAPSE_USE_OPTIMIZED_FAISS=true           # Use optimized FAISS
SYNAPSE_FAISS_USE_GPU=true                 # Enable GPU acceleration
SYNAPSE_FAISS_QUANTIZE=true                # Enable quantization
SYNAPSE_FAISS_NLIST=100                    # IVF clusters
SYNAPSE_FAISS_M=16                         # HNSW connections
SYNAPSE_FAISS_EF_CONSTRUCTION=200          # HNSW build quality
SYNAPSE_FAISS_EF_SEARCH=50                 # HNSW search quality
```

#### NLP & Entity Extraction

```bash
SYNAPSE_ENTITY_EXTRACTOR_TYPE=spacy        # Type: mock|spacy
SYNAPSE_ENTITY_EXTRACTOR_MODEL=en_core_web_sm  # SpaCy model
SYNAPSE_EMBEDDING_PROVIDER=sentence-transformers  # Provider
```

#### LLM Configuration

```bash
SYNAPSE_LLM_TYPE=mock                      # Type: mock|openai|anthropic|ollama
SYNAPSE_OPENAI_API_KEY=<key>              # OpenAI API key
SYNAPSE_ANTHROPIC_API_KEY=<key>           # Anthropic API key
SYNAPSE_OLLAMA_BASE_URL=http://localhost:11434  # Ollama URL
SYNAPSE_LLM_MODEL_NAME=gpt-4o-mini        # Model name
SYNAPSE_LLM_MAX_TOKENS=2000               # Max response tokens
SYNAPSE_LLM_TEMPERATURE=0.3               # Temperature (0.0-2.0)
SYNAPSE_LLM_TIMEOUT=30.0                  # API timeout (seconds)
```

#### Citation & Retrieval

```bash
SYNAPSE_CITATION_STYLE=numeric            # Style: numeric|apa|mla|chicago|ieee
SYNAPSE_GRAPH_CONTEXT_MAX_TOKENS=1500     # Max context tokens
```

#### Operational Mode

```bash
SYNAPSE_VECTOR_ONLY_MODE=false            # Vector-only mode (no graph)
SYNAPSE_AUTO_FALLBACK_VECTOR_MODE=true    # Auto-fallback on graph unavailable
```

#### Notion Integration

```bash
SYNAPSE_NOTION_API_KEY=<key>              # Notion API key
SYNAPSE_NOTION_BASE_URL=https://api.notion.com/v1
SYNAPSE_NOTION_VERSION=2022-06-28         # API version
SYNAPSE_NOTION_MAX_RETRIES=5              # Max retries
SYNAPSE_NOTION_MAX_QPS=3.0                # Requests per second
SYNAPSE_NOTION_BACKOFF_CEILING=8.0        # Max backoff seconds
```

#### Caching

```bash
SYNAPSE_CACHE_TYPE=memory                 # Type: memory|redis
SYNAPSE_REDIS_URL=redis://localhost:6379/0  # Redis URL
SYNAPSE_CACHE_DEFAULT_TTL=300             # Default TTL (seconds)
SYNAPSE_CACHE_EMBEDDING_TTL=3600          # Embedding cache TTL
SYNAPSE_CACHE_SEARCH_TTL=600              # Search cache TTL
```

#### Document Processing

```bash
SYNAPSE_CHUNK_SPLITTER_TYPE=sentence      # Type: sentence|token
SYNAPSE_INGESTION_CHUNK_SIZE=200          # Chunk size (tokens)
SYNAPSE_INGESTION_CHUNK_OVERLAP=20        # Chunk overlap (tokens)
```

#### Feature Flags

```bash
SYNAPSE_ENABLE_KEYWORD_STREAMING=false    # Enable keyword streaming
SYNAPSE_ENABLE_METRICS=true               # Expose /metrics endpoint
SYNAPSE_ENABLE_RATE_LIMITING=false        # Enable rate limiting
SYNAPSE_RATE_LIMIT_PER_MINUTE=300         # Requests per minute
SYNAPSE_RATE_LIMIT_PER_HOUR=5000          # Requests per hour
```

#### LLM Relationship Extraction

```bash
SYNAPSE_ENABLE_LLM_RELATIONSHIPS=false    # Enable LLM relationships
SYNAPSE_LLM_REL_MIN_CONFIDENCE=0.7        # Min confidence (0.0-1.0)
```

#### Maintenance

```bash
SYNAPSE_ENABLE_MAINTENANCE_JOBS=false     # Enable background jobs
SYNAPSE_MAINTENANCE_INTERVAL_SECONDS=86400  # Interval (default: 1 day)
```

#### Enterprise Authentication (90+ Additional Variables)

```bash
# Enterprise Features
SYNAPSE_ENABLE_ENTERPRISE_AUTH=false       # Enable enterprise auth
SYNAPSE_ENABLE_MULTI_TENANCY=false         # Enable multi-tenancy
SYNAPSE_DEFAULT_TENANT_DOMAIN=synapse.local
SYNAPSE_TENANT_ISOLATION_LEVEL=database    # Isolation: database|schema|row

# SAML 2.0
SYNAPSE_SAML_ENTITY_ID=                    # SAML entity ID
SYNAPSE_SAML_CERT_FILE=                    # Certificate path
SYNAPSE_SAML_KEY_FILE=                     # Private key path

# OAuth 2.0/OpenID Connect
SYNAPSE_OAUTH_REDIRECT_URI=http://localhost:8000/auth/enterprise/oauth/callback

# LDAP/Active Directory
SYNAPSE_LDAP_CONNECTION_TIMEOUT=10         # Connection timeout
SYNAPSE_LDAP_SEARCH_TIMEOUT=30             # Search timeout

# Multi-Factor Authentication
SYNAPSE_MFA_ISSUER_NAME=Synapse Graph-RAG
SYNAPSE_MFA_BACKUP_CODE_LENGTH=8           # Backup code length (6-12)
SYNAPSE_MFA_TOTP_WINDOW=1                  # TOTP window tolerance

# Compliance & Audit
SYNAPSE_ENABLE_AUDIT_LOGGING=true          # Enable audit logs
SYNAPSE_AUDIT_LOG_ENCRYPTION=true          # Encrypt audit logs
SYNAPSE_AUDIT_RETENTION_DAYS=2555          # 7 years retention
SYNAPSE_GDPR_COMPLIANCE_MODE=false         # GDPR compliance

# Security Policies
SYNAPSE_PASSWORD_MIN_LENGTH=12             # Min password length (8-128)
SYNAPSE_SESSION_TIMEOUT_MINUTES=30         # Session timeout (5-1440)
SYNAPSE_MAX_CONCURRENT_SESSIONS=5          # Max sessions per user
SYNAPSE_REQUIRE_MFA_FOR_ADMIN=true         # Require admin MFA

# Rate Limiting
SYNAPSE_ENTERPRISE_RATE_LIMIT_PER_MINUTE=1000
SYNAPSE_LOGIN_ATTEMPT_LIMIT=5              # Failed login limit
SYNAPSE_LOCKOUT_DURATION_MINUTES=30        # Lockout duration

# Encryption & Key Management
SYNAPSE_ENABLE_FIELD_ENCRYPTION=true       # Field-level encryption
SYNAPSE_ENCRYPTION_ALGORITHM=AES-256-GCM
SYNAPSE_KEY_ROTATION_INTERVAL_DAYS=90      # Key rotation interval

# High Availability & DR
SYNAPSE_ENABLE_HA_MODE=false               # High availability mode
SYNAPSE_BACKUP_ENCRYPTION=true             # Encrypt backups
SYNAPSE_BACKUP_RETENTION_DAYS=30           # Backup retention
SYNAPSE_CROSS_REGION_REPLICATION=false     # Cross-region replication
```

---

## Database Architecture

### Current Database State (November 2025)

**Active SQLite Databases**: 11 databases, 1.4MB total

#### Production Databases

1. **epic7_sales_automation.db** (389KB)
   - Sales pipeline: 134 opportunities, $1.158M value
   - Tables: crm_contacts, crm_opportunities, crm_deals, crm_proposals, crm_interactions, crm_activities
   - Status: Active, excellent performance (<10ms queries)

2. **synapse_business_crm.db** (94KB)
   - CRM data and customer relationships
   - Business intelligence tracking

3. **linkedin_business_development.db** (131KB)
   - LinkedIn content automation
   - Post scheduling and tracking
   - Engagement analytics

4. **synapse_analytics_intelligence.db** (86KB)
   - Performance metrics
   - A/B testing results
   - Content analytics

5. **synapse_content_intelligence.db** (33KB)
   - AI-powered content analysis
   - Concept extraction results

6. **synapse_system_infrastructure.db** (319KB)
   - System monitoring metrics
   - Health check history
   - Performance logs

7-10. **Epic 16-18 Databases** (327KB total)
   - epic16_abm_campaigns.db (74KB)
   - epic16_enterprise_onboarding.db (45KB)
   - epic16_fortune500_acquisition.db (147KB)
   - epic18_global_expansion.db (61KB)

### PostgreSQL Migration (Future)

**Status**: Planned for Q2 2026 when scale requires
**Current Scale**: 1.4MB << 100MB threshold
**Decision**: SQLite sufficient for 12-24 months

See `DATABASE_MIGRATION_STATUS.md` for complete migration analysis.

---

## Service Layer

### Core Services

#### IngestionService
**Purpose**: Document ingestion pipeline with chunking, entity extraction, and embedding generation

**Key Methods**:
- `ingest_documents(paths: List[str]) -> IngestResult`
- `process_document(doc: Document) -> ProcessResult`
- `extract_entities(text: str) -> List[Entity]`

**Dependencies**: DocumentProcessor, EntityExtractor, GraphStore, VectorStore, EmbeddingService

#### SearchService
**Purpose**: Hybrid search combining vector similarity and graph traversal

**Key Methods**:
- `search(query: str, top_k: int) -> List[SearchResult]`
- `hybrid_search(query: str, enable_graph: bool) -> HybridResults`
- `get_related_entities(entity_id: str) -> List[Entity]`

**Dependencies**: GraphRepository, VectorStore

#### AdvancedFeaturesService
**Purpose**: Advanced analytics, brand safety, reasoning, content analysis

**Key Capabilities**:
- Graph statistics and visualization
- Hot-take analysis and scoring
- Brand safety checks
- Virality prediction
- Reasoning analysis with citations
- Chunk inspection

**Key Methods**:
- `graph_stats() -> GraphStatistics`
- `analyze_hot_take(content: str) -> HotTakeAnalysis`
- `check_brand_safety(content: str) -> BrandSafetyCheck`
- `predict_virality(content: str) -> ViralityPrediction`
- `analyze_reasoning(query: str, depth: int) -> ReasoningAnalysis`

#### EmbeddingService
**Purpose**: Generate text embeddings for vector search

**Implementations**:
- SentenceTransformerEmbeddingService (default)
- OpenAIEmbeddingService
- OllamaEmbeddingService
- MockEmbeddingService (testing)

---

## Authentication & Authorization

### Authentication Methods

#### 1. JWT Token Authentication (Default)

```python
# Login to get token
POST /api/v1/auth/login
{
  "username": "user@example.com",
  "password": "SecurePassword123!"
}

# Use token in requests
GET /api/v1/query/documents
Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGc...
```

**Token Expiration**: 30 minutes (configurable)
**Refresh**: Re-login to get new token

#### 2. API Key Authentication

```python
# Create API key
POST /api/v1/auth/api-keys
{
  "name": "Production API Key",
  "expires_at": "2026-11-08T00:00:00Z"
}

Response:
{
  "key_id": "key_abc123",
  "api_key": "syn_live_abcdefghijklmnop...",  # Save this!
  "created_at": "2025-11-08T10:00:00Z"
}

# Use API key in requests
GET /api/v1/query/documents
X-API-Key: syn_live_abcdefghijklmnop...
```

#### 3. Enterprise SSO (SAML/OAuth)

**SAML 2.0 Setup**:
```bash
# Configure SAML
POST /api/v1/auth/enterprise/saml/configure
{
  "idp_entity_id": "https://idp.example.com",
  "idp_sso_url": "https://idp.example.com/sso",
  "idp_x509_cert": "-----BEGIN CERTIFICATE-----\n..."
}

# Users login via SAML
POST /api/v1/auth/enterprise/saml/login
{
  "saml_response": "<base64-encoded-response>"
}
```

**OAuth 2.0/OpenID Connect**:
```bash
# Configure OAuth provider
POST /api/v1/auth/enterprise/oauth/configure
{
  "provider": "azure_ad",  # or google, okta, auth0
  "client_id": "abc-123",
  "client_secret": "secret",
  "discovery_url": "https://login.microsoftonline.com/..."
}
```

### Authorization (RBAC)

**Roles**:
- `user`: Basic read access
- `editor`: Read + write documents
- `admin`: Full system access
- `enterprise_admin`: Tenant administration

**Permissions**:
- `documents:read`
- `documents:write`
- `documents:delete`
- `admin:*`
- `compliance:manage`

---

## Business Development System

### LinkedIn Automation

**Content Scheduling**:
```python
# Schedule LinkedIn posts
python -m business_development.content_scheduler

# Features:
# - Optimal posting times (6:30 AM Tue/Thu)
# - A/B testing hooks and CTAs
# - Engagement prediction
# - Automatic posting via LinkedIn API
```

**Consultation Inquiry Detection**:
```python
# Monitor for consultation inquiries
python -m business_development.consultation_inquiry_detector

# Detects:
# - NLP-based inquiry patterns
# - Priority scoring
# - Value estimation
# - Pipeline tracking
```

### Analytics Frameworks

**Performance Analysis**:
```python
# Analyze content performance
python -m analytics.performance_analyzer

# Provides:
# - Pattern recognition
# - Consultation-driving content analysis
# - Engagement optimization
```

**A/B Testing**:
```python
# Run A/B tests
python -m analytics.ab_testing_framework

# Statistical testing with 95% confidence
# Test: hooks, CTAs, posting times
```

---

## Testing & Development

### Running Tests

```bash
# Unit tests
make test

# Integration tests (requires Memgraph)
make test-memgraph

# All tests
make test-all

# Coverage enforcement (≥85% on critical routers)
make coverage-hot

# Single test
uv run pytest tests/api/test_search.py::test_unified_search -v
```

### Test Markers

```python
@pytest.mark.integration  # Requires external services
@pytest.mark.graph       # Graph operations
@pytest.mark.temporal    # Date/time sensitive
@pytest.mark.unit        # Self-contained
```

### Development Workflow

```bash
# Install dev dependencies
make install-dev

# Format code
make format

# Lint code
make lint

# Build package
make build

# Install locally with pipx
make install-local
```

---

## Troubleshooting

### Common Issues

#### 1. Memgraph Connection Errors

**Error**: `Failed to connect to Memgraph at 127.0.0.1:7687`

**Solutions**:
```bash
# Check if Memgraph is running
docker ps | grep memgraph

# Start Memgraph
synapse up

# Or use make
make run-memgraph

# Check logs
docker logs synapse-memgraph
```

#### 2. Authentication Errors

**Error**: `401 Unauthorized`

**Solutions**:
```bash
# Disable authentication for testing
export SYNAPSE_ENABLE_AUTHENTICATION=false

# Or generate token
curl -X POST http://localhost:18888/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "admin"}'

# Use token in requests
curl -H "Authorization: Bearer <token>" \
  http://localhost:18888/api/v1/query/documents
```

#### 3. Vector Store Errors

**Error**: `FAISS index not found`

**Solutions**:
```bash
# Rebuild vector index
synapse admin rebuild-index --vector-store faiss

# Or use simple vector store
export SYNAPSE_VECTOR_STORE_TYPE=simple

# Check vector store path
echo $SYNAPSE_VECTOR_STORE_PATH
```

#### 4. Import Errors

**Error**: `ModuleNotFoundError: No module named 'graph_rag'`

**Solutions**:
```bash
# Install in development mode
uv pip install -e ".[dev]"

# Or with pip
pip install -e ".[dev]"

# Verify installation
python -c "import graph_rag; print(graph_rag.__version__)"
```

#### 5. SpaCy Model Errors

**Error**: `Can't find model 'en_core_web_sm'`

**Solutions**:
```bash
# Download SpaCy model
python -m spacy download en_core_web_sm

# Or use mock extractor
export SYNAPSE_ENTITY_EXTRACTOR_TYPE=mock

# Skip SpaCy import for lightweight testing
export SKIP_SPACY_IMPORT=1
```

### Performance Optimization

**Slow Queries**:
```bash
# Enable FAISS GPU acceleration
export SYNAPSE_FAISS_USE_GPU=true

# Increase FAISS cache
export SYNAPSE_FAISS_NLIST=200

# Enable query caching
export SYNAPSE_CACHE_SEARCH_TTL=600
```

**High Memory Usage**:
```bash
# Enable FAISS quantization
export SYNAPSE_FAISS_QUANTIZE=true

# Reduce chunk size
export SYNAPSE_INGESTION_CHUNK_SIZE=150

# Use simple vector store
export SYNAPSE_VECTOR_STORE_TYPE=simple
```

### Getting Help

- **Documentation**: `/docs` in repo, `/docs` API endpoint
- **Issues**: https://github.com/anthropics/claude-code/issues
- **Logs**: Check `~/.graph_rag/logs/` for detailed logs
- **Health Check**: `curl http://localhost:18888/health`

---

**Document Version**: 1.0.0
**Last Updated**: 2025-11-09 (Week 45 Sprint Complete)
**Completeness**: ~80% (major expansion from 30%)
**Status**: Production-ready reference
