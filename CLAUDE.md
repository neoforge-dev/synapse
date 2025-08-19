# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Commands

### Setup and Installation
```bash
make install-dev                    # Install dependencies and download NLP data
make up                            # Start Memgraph + API (API in foreground)
make run-memgraph                  # Start only Memgraph (detached)
make run-api                       # Start only API server
```

### Testing
```bash
make test                          # Run unit tests (excludes integration tests)
make test-memgraph                 # Run Memgraph integration tests (requires Memgraph running)
make test-integration              # Run integration tests
make test-all                      # Run all tests (unit + integration)

# Single test examples
uv run pytest tests/api/test_search.py::test_unified_search_keyword -v
MEMGRAPH_HOST=localhost uv run pytest tests/infrastructure/graph_stores/test_memgraph_store.py::test_add_get_relationship -v
```

### Code Quality
```bash
make lint                          # Run ruff check + mypy (mypy continues on errors)
make format                        # Run ruff format
```

### Build and Package
```bash
make build                         # Build source and wheel distributions
make install-local                 # Install via pipx from dist/
```

### Business Development Automation
```bash
# Start automation dashboard and control center
python business_development/automation_dashboard.py

# Schedule and manage LinkedIn content posting
python business_development/content_scheduler.py

# Monitor consultation inquiries and business pipeline
python business_development/consultation_inquiry_detector.py

# Analytics and performance optimization
python analytics/performance_analyzer.py
python analytics/ab_testing_framework.py
python analytics/synapse_content_integration.py
```

## Project Architecture

This is a **Graph-augmented RAG (Retrieval-Augmented Generation)** system called "Synapse" that combines:
- **Knowledge Graph**: Uses Memgraph for storing documents, chunks, entities, and relationships
- **Vector Store**: FAISS or simple vector store for embeddings-based search
- **CLI Tools**: Composable Unix-style pipeline commands (`discover` → `parse` → `store`)
- **FastAPI Backend**: REST API with /api/v1 endpoints
- **MCP Integration**: Model Context Protocol server support
- **Business Development Automation**: Complete LinkedIn content strategy and consultation generation system

### Core Components

**API Layer** (`graph_rag/api/`):
- FastAPI application with dependency injection in `dependencies.py`
- Routers: documents, ingestion, search, query, admin, graph
- Authentication and metrics endpoints

**CLI Layer** (`graph_rag/cli/`):
- Typer-based CLI with composable commands
- Entry point: `synapse` command (mapped to `graph_rag.cli.main:main`)
- Commands: `ingest`, `discover`, `parse`, `store`, `search`, `query`, `graph`, `notion`, `mcp`

**Core Engine** (`graph_rag/core/`):
- `GraphRAGEngine`: Main orchestrator for search and synthesis
- `KnowledgeGraphBuilder`: Builds graph from documents/chunks
- `EntityExtractor`: SpaCy or mock entity extraction
- Interfaces defined in `interfaces.py`

**Infrastructure** (`graph_rag/infrastructure/`):
- `MemgraphGraphRepository`: Graph operations via mgclient
- Vector stores: `SimpleVectorStore`, `FaissVectorStore`
- Document processing, caching

**Services** (`graph_rag/services/`):
- `IngestionService`: Document ingestion pipeline
- `SearchService`: Vector + graph retrieval
- `EmbeddingService`: Sentence transformers or mock

**Business Development System** (`business_development/`):
- `LinkedInBusinessDevelopmentEngine`: Complete Week 3 content with engagement optimization
- `ConsultationInquiryDetector`: NLP-based consultation inquiry detection and tracking
- `LinkedInAPIClient`: Production LinkedIn API integration with automated posting
- `ContentAutomationPipeline`: Automated scheduling at optimal times (6:30 AM Tue/Thu)
- `AutomationDashboard`: Central monitoring and control system

**Analytics System** (`analytics/`):
- `ABTestingFramework`: A/B test hooks, CTAs, and timing for optimization
- `PerformanceAnalyzer`: Pattern recognition for consultation-driving content
- `SynapseContentIntelligence`: Intelligent content recommendations using RAG

### Data Flow

1. **Ingestion**: `discover` → `parse` (with metadata) → `store` (with optional embeddings)
2. **Document Identity**: Stable `document_id` derived from metadata ID → Notion UUID → Obsidian ID → content hash → path hash
3. **Storage**: Documents and chunks stored in Memgraph; embeddings in vector store
4. **Search**: Vector similarity + graph traversal for context-aware retrieval
5. **Synthesis**: LLM-based answer generation from retrieved chunks

## Configuration

Environment variables use `SYNAPSE_` prefix:
- `SYNAPSE_MEMGRAPH_HOST/PORT`: Memgraph connection (default: 127.0.0.1:7687)
- `SYNAPSE_VECTOR_STORE_TYPE`: `simple` or `faiss` (default: simple)
- `SYNAPSE_EMBEDDING_PROVIDER`: `sentence-transformers` or `mock` (default: sentence-transformers)
- `SYNAPSE_API_HOST/PORT`: API server settings (default: 0.0.0.0:8000)

## Testing Strategy

**Test Markers** (pytest.ini):
- `integration`: Requires external services (Memgraph)
- `graph`: Graph-related operations
- `temporal`: Date/time operations
- `unit`: Self-contained tests

**Key Test Patterns**:
- Memgraph tests use `MEMGRAPH_HOST=localhost` environment variable
- Integration tests check for `RUNNING_INTEGRATION_TESTS=true`
- Mock services available for lightweight testing
- Coverage enforcement on critical API routers (≥85%)

## Important Files

- `pyproject.toml`: Dependencies, build config, CLI entry point
- `Makefile`: Development workflow automation
- `docker-compose.yml`: Memgraph service definition
- `graph_rag/config/__init__.py`: Centralized settings management
- `graph_rag/api/dependencies.py`: Dependency injection for all services
- `graph_rag/api/main.py`: FastAPI application factory
- `graph_rag/cli/main.py`: CLI application entry point

## Development Notes

- Uses `uv` for dependency management and virtual environments
- Project name is `synapse-graph-rag` but package is `graph_rag`
- CLI command is `synapse` but imports use `graph_rag`
- Memgraph client (`mgclient`) is optional - graceful fallbacks for CI
- SpaCy imports are conditional (`SKIP_SPACY_IMPORT=1` for lightweight runs)
- Vector store persistence includes raw embeddings for precise deletions

## Business Development System Notes

- Complete automation system for LinkedIn content strategy and consultation generation
- SQLite databases for business metrics tracking (`*.db` files)
- LinkedIn API integration with OAuth authentication and fallback workflows
- A/B testing framework with statistical significance analysis (95% confidence)
- Performance analytics with pattern recognition for consultation-driving content
- Optimal posting times: 6:30 AM Tuesday/Thursday for maximum engagement
- Synapse RAG integration for intelligent content recommendations
- Real-time consultation inquiry detection with priority scoring and value estimation
- Comprehensive automation dashboard for monitoring all business development systems
- Production-ready for immediate LinkedIn posting and consultation pipeline generation