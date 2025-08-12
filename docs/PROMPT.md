## Graph RAG MCP — Continuation Prompt for New Agent

You are taking over an actively developed Graph RAG project focused on stable document identity and idempotent ingestion. Continue the work with high autonomy. Follow repository conventions, keep the test suite green, and prefer minimal, safe, incremental changes with strong tests.

### Context
- Project type: Graph-based RAG with Memgraph + vector store (SimpleVectorStore and FAISS option), FastAPI, CLI tools, and services layer.
- Current focus: Stable `document_id` derivation, idempotent re-ingestion (deleting old chunks/vectors before re-adding), and correct FAISS deletion behavior.
- Test runner and tooling:
  - Install: `make install-dev`
  - Lint: `make lint`
  - Format: `make format`
  - Unit tests: `make test` (or `make test -j1`)
  - Integration: `make test-integration` (Memgraph required)
  - Memgraph tests: `make test-memgraph`
  - Run API: `make run-api`
  - Run Memgraph: `make run-memgraph`

### Architecture and Code Style (follow strictly)
- Clean architecture: API → Services → Core → Infrastructure → LLM
- Repositories for data access (GraphRepository, VectorStore)
- Strategy pattern for components (EntityExtractor, LLMService)
- DI via FastAPI `Depends` and factories in `api/dependencies.py`
- Protocol interfaces in `core/interfaces.py`
- Style:
  - Line length: 88 (Ruff)
  - Double quotes
  - Typing: use type hints; Protocol for interfaces
  - Imports grouped: stdlib, third-party, local
  - Naming: snake_case (functions/vars), PascalCase (classes)
  - Async: consistent in services and repositories
  - Error handling: specific exceptions + contextual logs
  - Docstrings: Google style for public methods
  - Tests: unit tests for core logic, mock external deps

### Current State
- Identity: `graph_rag/utils/identity.py` implements multi-priority ID derivation (metadata > Notion UUID in filename/parents > content hash > path hash). Tests added and passing (`tests/utils/test_identity.py`).
- Ingestion: Idempotent re-ingest implemented in `graph_rag/services/ingestion.py` (with `replace_existing=True`) deleting old chunks from graph and vector store before adding new ones. Service tests cover this.
- FAISS vector store: `FaissVectorStore` now persists embeddings alongside metadata and correctly rebuilds the index on deletions. Infra tests added and passing.
- Suite status at last run: 194 passed, 42 skipped; all green.

### Priorities (continue from here)
1) Observability and Metadata
   - Ensure `id_source` (from identity derivation) is consistently persisted and visible via API responses (`/documents` endpoints) and in logs.
   - Tighten logs in ingestion to include `document_id`, `id_source`, counts of chunks deleted/added, and vector store actions.
2) CLI/Service wiring improvements
   - Add a CLI flag `--no-replace` (or `--replace/--no-replace`) to control idempotent behavior and plumb into `IngestionService.ingest_document`.
   - Consider a dry-run mode for ingestion to preview derived IDs and actions.
3) Notion export walker nuances
   - Confirm directory walker ignores hidden and Obsidian folders (present), and expand ignore for Notion export attachment subfolders (assets). Only Markdown-like files should be ingested.
   - Keep Notion property table parsing robust (present) and add small tests for corner cases.
4) FAISS persistence hardening
   - Metadata version field `version: 2` implemented; rows include `embedding`. On load, legacy rows are detected and warned.
   - Maintenance helpers exist: `stats()`, `rebuild_index()` on the FAISS store.
5) Tests and docs
   - Add unit/integration tests around CLI re-ingestion toggles and id_source propagation.
   - Document the identity strategy and idempotent ingestion behavior in README/ARCH. Keep `docs/PLAN.md` up to date with changes.

### Concrete Tasks
- Observability
  - Verify `id_source` is attached to `Document.metadata` on ingest and exposed in API schemas/responses where appropriate.
  - Add structured logs in `IngestionService` around pre-delete (count of chunks to delete), post-delete, and post-add.
- CLI ingestion flag
  - In `graph_rag/cli/commands/ingest.py`, add Typer flag to control `replace_existing` and thread it through to `IngestionService.ingest_document`.
  - Update help text and usage examples.
- Notion walker
  - Extend file selection filter to hard-ignore typical Notion asset dirs (e.g., folder matching `*assets*` next to the page file). Keep logic simple and safe.
  - Add tests that a Notion export directory with an assets subfolder only ingests `.md` content pages.
- FAISS meta versioning
  - Update `FaissVectorStore` meta serialization to include a `version` key and set to `2` (rows include `embedding`).
  - On load, detect missing version or missing `embedding` keys and keep existing warning/behavior; consider auto-setting `version=1` for legacy.
  - Add a small unit test to ensure version is persisted and read.
- Docs
  - Update `README.md` or a dedicated section to document identity derivation and re-ingestion semantics.
  - Amend `docs/PLAN.md` as items complete.

### Acceptance Criteria
- API responses for documents include persisted `id_source` in metadata where available.
- CLI supports `--replace/--no-replace` and correctly toggles pre-delete behavior in service.
- Notion export ingestion ignores asset folders and only ingests relevant content files; tests cover this.
- FAISS meta includes version info; delete/rebuild remains correct; persistence round-trip behaves as expected.
- All tests stay green: `make test` passes locally; integration tests remain as-is (skipped unless Memgraph available).

### How to Work
- Use TDD where reasonable. Add or update tests for any change in behavior.
- Keep changes small and incremental; run `make test` frequently.
- Follow commit style conventions (conventional commits), and do not push unless explicitly instructed by the user.
- Prefer adding tests near existing files: API tests in `tests/api`, CLI in `tests/cli`, services in `tests/services`, infra in `tests/infrastructure`, utils in `tests/utils`.
- For FAISS behavior, prefer deterministic vectors in tests; use explicit embeddings or mocks as needed.

### Useful Paths
- Identity: `graph_rag/utils/identity.py`
- Ingestion service: `graph_rag/services/ingestion.py`
- CLI ingest: `graph_rag/cli/commands/ingest.py`
- FAISS store: `graph_rag/infrastructure/vector_stores/faiss_vector_store.py`
- Simple vector store: `graph_rag/infrastructure/vector_stores/simple_vector_store.py`
- API routers: `graph_rag/api/routers/*.py`
- Settings: `graph_rag/config.py`

### Gotchas
- Do not run long-lived background processes in this environment.
- Keep test isolation: avoid writing to global OS paths; tests use tmp dirs for FAISS.
- When changing schemas or interfaces, ensure all call sites and tests are updated.
- If you modify `faiss_vector_store` persistence, ensure backward compatibility and add clear warnings.

### Ready-to-Run Commands
- Run all unit tests: `make test -j1`
- Run a single test: `python -m pytest tests/infrastructure/vector_stores/test_simple_vector_store_contract.py::test_faiss_vector_store_delete_and_rebuild -v`
- Lint/format: `make lint && make format`

Continue the work by implementing priorities above, starting with observability (`id_source` exposure/logging) and the CLI replace toggle. Maintain green tests at each step.