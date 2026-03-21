# Synapse Graph-RAG — Agent Instructions

## Project Context

- **Domain:** neoforge-dev
- **Status:** ~50% complete — Enterprise B2B positioning, no production deployment yet
- **Stack:** Python 3.10+ + FastAPI + Memgraph + FAISS + PostgreSQL + Sentence Transformers
- **Deploy:** Docker Compose (local / self-hosted) — no cloud deployment yet
- **Last Updated:** 2026-03-21

## Entry Points

| Purpose | Location |
|---------|----------|
| API Entry | `graph_rag/api/main.py` |
| CLI Entry | `graph-rag` (via pyproject.toml entry point) |
| Config | `.env` (copy from `.env.example`) |
| Docker Compose | `docker-compose.yml` |
| Makefile | `Makefile` |
| Package Config | `pyproject.toml` |

## Development Commands

```bash
# Setup
uv pip install -e .[dev]              # Install with dev dependencies
make download-nlp-data                # Download NLTK punkt + spaCy en_core_web_sm
make install-mcp-deps                 # Install MCP extras (for IDE integration)

# Start services
make up                               # Start Memgraph + API (Docker Compose)
make run-memgraph                     # Start Memgraph graph database only
make run-api                          # Start FastAPI server only (host :8000 → exposed :18888)

# Test
uv run pytest                         # All tests
uv run pytest -m "not integration"    # Unit tests only
uv run pytest -m integration          # Integration tests (requires Memgraph running)
uv run pytest --cov=graph_rag         # With coverage

# Quality
ruff check .
ruff format .
mypy graph_rag/

# Stop
make down                             # Stop all services
```

## Key Files

| File | Purpose |
|------|---------|
| `graph_rag/api/main.py` | FastAPI app factory — 4 consolidated routers (Epic 15 Phase 2) |
| `graph_rag/api/routers/core_business_operations.py` | Core graph RAG operations |
| `graph_rag/api/routers/analytics_intelligence.py` | Analytics + intelligence endpoints |
| `graph_rag/api/routers/enterprise_platform.py` | Enterprise auth, CRM, compliance |
| `graph_rag/api/routers/advanced_features.py` | MCP, A/B testing, autonomous AI |
| `graph_rag/api/routers/monitoring.py` | Prometheus metrics, health checks |
| `graph_rag/api/dependencies.py` | FastAPI DI — embedding service, LLM factory |
| `graph_rag/api/middleware.py` | Rate limiting, request logging, security headers |
| `graph_rag/services/ingestion.py` | Document ingestion pipeline |
| `graph_rag/config.py` | Pydantic settings (env-driven) |
| `.env.example` | Required env vars reference |
| `docker-compose.yml` | Memgraph + API service definitions |
| `Makefile` | All development commands |
| `pyproject.toml` | Package config, dependencies, test settings |

## Architecture

```
synapse-graph-rag/
├── graph_rag/
│   ├── api/
│   │   ├── main.py               # FastAPI app — 4 consolidated routers
│   │   ├── routers/
│   │   │   ├── core_business_operations.py
│   │   │   ├── analytics_intelligence.py
│   │   │   ├── enterprise_platform.py
│   │   │   ├── advanced_features.py
│   │   │   └── monitoring.py
│   │   ├── dependencies.py       # Embedding + LLM factory (lazy-loaded)
│   │   ├── errors.py             # GraphRAGError + handlers
│   │   ├── metrics.py            # Prometheus metrics
│   │   └── middleware.py         # Rate limit, logging, security headers
│   ├── services/
│   │   └── ingestion.py          # Document ingestion pipeline
│   └── config.py                 # Pydantic settings
├── tests/
│   ├── unit/
│   └── integration/              # Requires Memgraph running
├── docker-compose.yml            # Memgraph :7687 + API :18888
├── Makefile
└── pyproject.toml
```

**Graph backend:** Memgraph (bolt://memgraph:7687) — Cypher-compatible, in-memory graph database.

**Vector search:** FAISS (faiss-cpu) with Sentence Transformers (`all-MiniLM-L6-v2` default). Hybrid retrieval: graph traversal + vector similarity.

**Router consolidation:** 33 legacy routers consolidated to 4 in Epic 15 Phase 2. Legacy routers are deleted — do not re-add them.

**Performance optimizations applied:**
- Lazy loading: FAISS, SentenceTransformers, LLM services (reduces startup by ~6s, saves ~1.2GB RAM)
- Search result caching (TTL 300s, 100 slots)
- Embedding cache (batch ingestion ~30% faster)
- Entity extraction cache (reduces redundant spaCy processing)

**Auth:** JWT + RBAC, enterprise-grade (SOX/GDPR/HIPAA compliant patterns in codebase).

**MCP integration:** FastMCP for IDE (Claude/Cursor) connectivity — install with `.[mcp]` extras.

**Business model:** SaaS $99-299/mo + Enterprise $5K-50K/mo. Part of Graph-RAG ecosystem:
- Synapse (neoforge-dev) → Platform
- Graph RAG Mastery (codeswiftr-com) → Course
- Graph-RAG Blueprint (leanvibe-dev) → Vertical template

## Quality Gates

| Gate | Tool | Threshold |
|------|------|-----------|
| Unit Tests | pytest | Pass all unit tests |
| Integration Tests | pytest -m integration | Graph operations, vector search |
| Lint | Ruff | Zero errors |
| Type Check | mypy | Strict mode |
| Graph Query (simple) | — | <50ms target |
| Graph Query (complex) | — | <500ms target |
| Vector Search | — | <200ms target |
| API Response (p95) | — | <1s target |

## Human Gates

The following changes require human approval before implementation:

1. **Graph Schema** — Changes to Memgraph/Neo4j data model or Cypher queries
2. **Router Architecture** — Adding new routers or modifying the 4-router consolidated structure (Epic 15 locked)
3. **AI/LLM Prompts** — Changes to retrieval logic, reranking, or generation prompts
4. **MCP Tools** — New or modified MCP tool definitions or capabilities
5. **Auth/RBAC** — Changes to JWT, RBAC, or compliance-related code
6. **Embedding Strategy** — Changes to embedding model or FAISS index configuration
7. **Production Deployment** — Any cloud deployment (no production env currently configured)
8. **Enterprise Features** — CRM pipeline, LinkedIn automation, A/B testing framework changes

## Environment Variables

Required: `MEMGRAPH_HOST`, `MEMGRAPH_PORT`
Optional: `SYNAPSE_ENABLE_AUTHENTICATION`, `SYNAPSE_JWT_SECRET_KEY`, `EMBEDDING_MODEL_NAME`,
`SYNAPSE_ENABLE_SEARCH_CACHE`, `SYNAPSE_SEARCH_CACHE_SIZE`, `SYNAPSE_SEARCH_CACHE_TTL`,
`POSTHOG_API_KEY`, `SENTRY_DSN`, `STRIPE_SECRET_KEY`

See `.env.example` for full reference.
