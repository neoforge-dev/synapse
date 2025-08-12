## Synapse MCP Handbook (Single Source of Truth)

This document is the canonical reference for contributors, CLI agents, and future developers. It consolidates the architecture, workflows, CLI/API contracts, vector-store persistence, identity/idempotence guarantees, testing strategy, CI, and maintenance tasks.

### Overview
- **What**: Graph-augmented retrieval for personal knowledge bases (Notion/Obsidian). 
- **Shape**: CLI (Typer), FastAPI backend, Memgraph graph store, pluggable vector store (Simple/FAISS), LLM synthesis layer.
- **Goals**: Stable document identity, idempotent ingestion, reliable vector maintenance, ergonomic CLI pipelines.

### Quickstart
See `README.md` for a step-by-step quickstart. Core commands:
- Install deps: `make install-dev`
- Run API: `make run-api`
- Run Memgraph: `make run-memgraph`
- Unit tests: `make test`
- Hot-path coverage gate: `make coverage-hot`

### Architecture
- Clean layering: API → Services → Core → Infrastructure → LLM
- DI factories: `graph_rag/api/dependencies.py`
- Protocols: `graph_rag/core/interfaces.py`
- CLI flow: `discover` → `parse` → `store` (composable) and `ingest` (wrapper)
- Core engine: `graph_rag/core/graph_rag_engine.py`
- Graph store: `graph_rag/infrastructure/graph_stores/memgraph_store.py`
- Vector stores: `graph_rag/infrastructure/vector_stores/{simple,faiss}_vector_store.py`

### Identity and Idempotence
- Canonical `document_id` derivation in `graph_rag/utils/identity.py` with priority:
  1) Explicit metadata `id`
  2) Notion page UUID (filename or parent dirs)
  3) Obsidian `id`
  4) Normalized content hash
  5) Path-hash fallback
- Re-ingestion (`--replace/--no-replace`):
  - When replacing, the system deletes old chunks and vectors for the same `document_id` before adding new ones.
  - `id_source` is attached to metadata for observability and surfaces in CLI outputs.

### Vector Store (FAISS) Persistence
- Index file: `index.faiss` (cosine via inner product on normalized vectors)
- Sidecar: `meta.json` with `version: 2` and `rows` (each row includes `embedding`).
- Deletions rebuild the FAISS index from persisted raw embeddings, skipping legacy rows missing `embedding` (warns).
- Maintenance helpers exposed on the store: `stats()`, `rebuild_index()`.

### CLI Commands (entry: `synapse`)
- `discover DIRECTORY [--include ...] [--exclude ...] [--json] [--stdin]`
- `parse [--meta key=value ... | --meta key:=json ...] [--meta-file PATH]`
- `store [--embeddings/--no-embeddings] [--replace/--no-replace] [--json] [--emit-chunks]`
- `ingest PATH` (wrapper; supports `--dry-run`, `--json`, `--json-summary`, `--stdin`, `--include/--exclude`, `--meta`, `--meta-file`, `--replace/--no-replace`, `--embeddings`)
- `suggest "<topic>" [--k 5] [--graph] [--count N] [--json]` (respects `SYNAPSE_API_BASE_URL`)

Key CLI guarantees and UX:
- Hidden files, `.obsidian/`, and Notion `assets` subfolders are ignored by default.
- Dry-run emits `{ path, document_id, id_source, topics }` (or JSON with `--json`).
- Non-dry-run JSON emits `{ document_id, num_chunks, id_source, path, embeddings, replace_existing, topics? }`.

### API (FastAPI)
- App factory: `graph_rag/api/main.py:create_app`
- Query router: `POST /api/v1/query` and `POST /api/v1/query/ask`
- `Ask` combines retrieval with LLM synthesis and can include graph context.
- Documents router: list/get now reflect `id_source` in `metadata` when present.

### Configuration (env / .env with `SYNAPSE_` prefix)
- `SYNAPSE_VECTOR_STORE_TYPE`: `simple` (default) or `faiss`
- `SYNAPSE_VECTOR_STORE_PATH`: FAISS persistence dir
- `SYNAPSE_EMBEDDING_PROVIDER`: `sentence-transformers` or `mock`
- `SYNAPSE_MEMGRAPH_HOST`/`SYNAPSE_MEMGRAPH_PORT`
- `SYNAPSE_API_HOST`/`SYNAPSE_API_PORT`
- `SYNAPSE_API_BASE_URL` (CLI admin/search commands): e.g., `http://localhost:8000/api/v1`
- `SYNAPSE_API_LOG_JSON`, `SYNAPSE_ENABLE_METRICS`

### Development Workflow
- Install: `make install-dev`
- Lint/Type: `make lint` (ruff + mypy on core/services)
- Format: `make format` (ruff format)
- Tests: `make test` (unit), `make test-integration`, `make test-memgraph`
- Debugging protocol: see `memory-bank/debugging-protocol.md` and `memory-bank/progress.md`

### Testing Strategy
- Unit tests dominate; mock external services.
- Contract tests for `GraphRepository`, `VectorStore`, `GraphRAGEngine`.
- API tests validate schemas and streaming; NDJSON when applicable.
- Coverage gate for hot paths at ≥85% via `make coverage-hot`.

### CI/CD
- Lint + mypy + unit tests on PR.
- Optional Memgraph integration stage behind a label.
- Merge queue and release automation recommended via conventional commits.

### MCP Integration (Planned)
- Tools: `ingest_files`, `search`, `query_answer` exposed via a thin Python MCP server that calls local FastAPI/services.
- See `docs/MCP.md` for details and IDE configuration examples.

### Cleanup Candidates and Deprecations
- Orphan/placeholder dirs: `handlers/`, `middleware/`, `services/` (root), `database/`, `utils/` (root), `models/` (contains only `user.go`).
  - Action: retain for now; propose deletion in a cleanup PR if not referenced by code/tests.
- Legacy namespace: `graphrag/ingestion/ingestion_router.py` (alternate/old path).
  - Action: mark as legacy; migrate or delete after verification.

Deleted (approved):
- `handlers/`, `middleware/`, root `services/`, `database/`, root `utils/`
- `models/user.go` (no Go code elsewhere)
- `graphrag/` namespace
- `CLAUDE.md` (legacy doc)
- Doc deprecations: `CLAUDE.md` contains guidance now captured here; treat as legacy and remove after this Handbook is fully adopted.

### Reference Index
- Human index: `docs/INDEX.md`
- Machine index: `docs/index.json`
- Code roots: `graph_rag/*`
- Tests: `tests/*`

