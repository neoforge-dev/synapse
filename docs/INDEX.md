## Repository Index (navigable)

- **Project**: Synapse MCP (Graph RAG with Memgraph)
- **Primary entry points**: `README.md`, `graph_rag/`, `docs/`, `tests/`

### Core Docs
- `README.md`: Quickstart, CLI usage, configuration
- `docs/ARCHITECTURE.md`: System overview and layering
- `docs/guides/CONTENT_STRATEGY_GUIDE.md`: **Strategic content intelligence and calendar system**
- `docs/PRD.md`: Product requirements (v0 scope)
- `docs/PLAN.md`: Execution plan and gaps
- `docs/MCP.md`: Planned MCP integration
- `docs/LAUNCHD.md`: macOS autostart guide
- `docs/PROMPT.md`: Continuation prompt for agents
- `docs/HANDBOOK.md`: Single source-of-truth for architecture, workflows, and ops
- `CONTRIBUTING.md`: Contributing guide
- `docs/DELETION_CANDIDATES.md`: Proposed removals and checklist

### Code (Python package `graph_rag`)
- `graph_rag/api/`
  - `main.py`, `dependencies.py`, `schemas.py`, `models.py`
  - Routers: `routers/` → `query.py`, `search.py`, `ingestion.py`, `documents.py`, `chunks.py`, `__init__.py`
- `graph_rag/cli/`
  - `main.py` (Typer entry `synapse`)
  - Commands: `commands/` → `ingest.py`, `discover.py`, `parse.py`, `store.py`, `search.py`, `suggest.py`, `config.py`, `query.py`, `admin.py`
  - Config: `cli/config.py`
- `graph_rag/core/`
  - Core engine and protocols: `graph_rag_engine.py`, `knowledge_graph_builder.py`, `persistent_kg_builder.py`, `entity_extractor.py`, `graph_store.py`, `vector_store.py`, `interfaces.py`, `senior_debug_protocol.py`, `debug_tools.py`, `__init__.py`
- `graph_rag/infrastructure/`
  - Graph: `graph_stores/memgraph_store.py`, `repositories/graph_repository.py`
  - Vectors: `vector_stores/simple_vector_store.py`, `vector_stores/faiss_vector_store.py`
  - Documents: `document_processor/simple_processor.py`
  - Cache: `cache/memory_cache.py`, `cache/protocols.py`
- `graph_rag/services/`
  - `ingestion.py`, `search.py`, `embedding.py`, `__init__.py`
- `graph_rag/llm/`
  - `llm_service.py`, `loader.py`, `mock_llm.py`, `protocols.py`, `types.py`, `__init__.py`
- Other modules
  - `graph_rag/models.py`, `graph_rag/domain/models.py`, `graph_rag/data_stores/graph_store.py`, `graph_rag/config/__init__.py`, `graph_rag/utils/identity.py`, `graph_rag/__init__.py`

### Legacy/Alternate
- None

### Tests
- `tests/` (unit + integration)
  - API: `tests/api/*.py`
  - CLI: `tests/cli/*.py`
  - Core: `tests/core/*.py`
  - Infrastructure: `tests/infrastructure/*.py`, `tests/infrastructure/vector_stores/*.py`, `tests/infrastructure/graph_stores/*.py`, `tests/infrastructure/repositories/*.py`
  - Services: `tests/services/*.py`
  - Config: `tests/config/*.py`
  - Utils: `tests/utils/*.py`
  - Integration/E2E: `tests/integration/*.py`, `tests/test_e2e_mvp.py`
  - Shared: `tests/conftest.py`, `tests/cli/conftest.py`, `tests/setup_test_db.py`

### Memory Bank (project context)
- `memory-bank/`
  - `active-context.md`, `debugging-examples.md`, `debugging-protocol.md`, `development-workflow.md`, `product-context.md`, `progress.md`, `project-brief.md`, `system-patterns.md`, `tech-context.md`

### Third-Party/Vendored
- `pymgclient/` (C/C++/Python bindings, compiled `.so`, tests, docs)
  - Treat as third-party; excluded from lint/format per config

### Config and Build
- Project: `pyproject.toml`, `VERSION`, `Makefile`, `uv.lock`
- Python tests: `pytest.ini`, `tests/pytest.ini`
- Docker: `Dockerfile`, `Dockerfile.dev`, `docker-compose.yml`, `docker-compose.dev.yml`
- CI: `.github/workflows/ci.yml`

### Data and Generated
- Sample data: `data/paul_graham_essay.txt`
- Coverage HTML (generated): `htmlcov/`
- Logs and last-run markers: `pytest_output.log`, `pytestdebug.log`, `last-*.txt`

### Empty/Placeholder dirs (removed)
- Removed: `graphrag/`, `handlers/`, `middleware/`, root `services/`, `database/`, root `utils/`, `models/user.go`

---

### Quick Navigation Map

- **Docs**: `README.md`, `docs/*`
- **CLI**: `graph_rag/cli/main.py`, `graph_rag/cli/commands/*`
- **API**: `graph_rag/api/main.py`, `graph_rag/api/routers/*`
- **Core**: `graph_rag/core/*`
- **Infra**: `graph_rag/infrastructure/*`
- **LLM**: `graph_rag/llm/*`
- **Tests**: `tests/*`

Refer to `docs/index.json` for a machine-readable index suitable for CLI agents.