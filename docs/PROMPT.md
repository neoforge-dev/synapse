# Cursor Agent Handoff Prompt

You are taking over an active Graph RAG project. Your mandate is to work autonomously, using a TDD-first, XP-inspired workflow to maximize the amount of time you can progress without human intervention. Deliver small, reversible changes with high signal tests and pragmatic CI guardrails.

## Project snapshot
- Stack: Python 3.12, FastAPI, Pydantic v2, pytest, ruff, uv.
- Architecture: API → Services → Core → Infrastructure → LLM.
- Key layers and protocols live in `graph_rag/core/interfaces.py` and are used across services and infrastructure.
- Data stores: Memgraph repository (infrastructure), Simple vector store with embeddings.

## Current state (important)
- Vector streaming is implemented end-to-end (engine + router) and serialized as NDJSON.
- Keyword streaming exists behind a feature flag and is enabled only when `SYNAPSE_ENABLE_KEYWORD_STREAMING=true`.
- Engine streaming now supports both vector and keyword search types and yields `SearchResultData` sequentially for deterministic behavior.
- Search router returns 501 for keyword streaming unless the flag is enabled and propagates HTTP exceptions.
- DI guard tests exist (vector store search path; some for documents), vector-store contract test added.
- CI: GitHub Actions workflow with a validate job (lint, format, unit tests + hot-path coverage reporting) and a label-gated Memgraph integration job.

## Commands
- Install dev deps: `make install-dev`
- Lint: `make lint`
- Format: `make format`
- Unit tests: `make test`
- Integration tests (Memgraph): `make test-integration` (requires Memgraph up)
- Start API (dev): `make run-api`
- Start Memgraph: `make run-memgraph`
- Hot-path coverage (non-blocking): `make coverage-hot`

## Endpoints (relevant)
- Streaming search (NDJSON): `POST /api/v1/search/query?stream=true`
  - Body: `{ "query": str, "search_type": "vector"|"keyword", "limit": int }`
  - Keyword streaming requires `SYNAPSE_ENABLE_KEYWORD_STREAMING=true`.
- Documents: `/api/v1/documents` (POST/GET/GET by id/DELETE/PATCH metadata)
- Ingestion: `POST /api/v1/ingestion/documents` (async; returns 202)
- Health: `GET /health`

## Feature flags
- `SYNAPSE_ENABLE_KEYWORD_STREAMING` (bool) → enables keyword streaming in API/engine.

## CI/CD
- `.github/workflows/ci.yml`:
  - Validate: ruff check, ruff format --check, unit tests, hot-path coverage.
  - Memgraph Integration (only when PR has label `memgraph`): spins Memgraph service and runs `make test-integration`.

## Code style and conventions
- Line length 88, double quotes, type hints, Protocols for interfaces.
- Tests first; small commits; conventional commit messages.
- NDJSON streaming emits each `SearchResultSchema` as a JSON line.

## Where to look
- Engine: `graph_rag/core/graph_rag_engine.py`
- Routers: `graph_rag/api/routers/*.py` (notably `search.py`, `documents.py`, `ingestion.py`)
- Config: `graph_rag/config/__init__.py`
- Vector store: `graph_rag/infrastructure/vector_stores/simple_vector_store.py`
- App factory and DI getters: `graph_rag/api/main.py`
- Tests: `tests/api`, `tests/core`, `tests/infrastructure`, `tests/services`
- Project context: `memory-bank/*.md` (especially `progress.md` and `development-workflow.md`)

## Streaming: spec recap
- Engine `stream_context(query, search_type, limit)` yields `SearchResultData` sequentially.
- Router converts `SearchResultData`/`ChunkData` to `SearchResultSchema` and yields NDJSON.
- Keyword streaming returns 501 unless `SYNAPSE_ENABLE_KEYWORD_STREAMING=true`.

## Known test behaviors (DI overrides)
- The API test fixture overrides dependencies with mocks (see `tests/conftest.py`).
- Some DI guard tests won’t hit the real state-based getters unless you temporarily clear specific overrides.
- Plan: write a small per-test utility/fixture to clear `app.dependency_overrides` for the targeted getter to exercise real DI guards in `api/main.py`.

## Immediate backlog (prioritized)
1) DI + Health
   - Implement a per-test override-clearing utility and complete DI guard tests for:
     - Graph repository
     - Entity extractor
     - Document processor
     - Knowledge graph builder
     - Ingestion service
   - Add basic readiness checks (vector store size probe; gated Memgraph ping).

2) Contracts
   - GraphRAGEngine contract tests for `query`, `retrieve_context`, `stream_context`, error cases.
   - GraphRepository contract tests (skip when Memgraph unavailable): add/get doc/chunk, link entities, delete.

3) Streaming
   - Plan true incremental keyword streaming (paging/cursor) when backend supports it; keep API guarded by flag. Add engine contract tests for ordering and shape.

4) CI Guardrails
   - Add OpenAPI spec drift check (generate OpenAPI JSON and compare with committed baseline; warn-only on PR).
   - Add flaky test detector scaffold (collect failures, mark flaky or report).

5) Dev ergonomics
   - Add `.pre-commit-config.yaml` (ruff format/check + commit-msg lint) and wiring.
   - Provide test templates (unit/api/contract) + a short contributing section.

## Deliverable guidance
- Work in small vertical slices: add or update a failing test, implement code, keep green, commit with a conventional message.
- Keep streaming deterministic until true incremental streaming is implemented.
- Prefer Protocol-based contract tests at boundaries (VectorStore, GraphRepository, Engine).
- For DI tests that must reach the real getter:
  - Clear the specific dependency override: `if getter in app.dependency_overrides: del app.dependency_overrides[getter]`
  - Ensure `app.state.<dep>` is `None` to trigger a 503 from `api/main.py` getter.

## Examples to start with (step-by-step)
- Implement a test utility in `tests/utils/overrides.py`:
  - `clear_override(app: FastAPI, getter)`
  - `restore_overrides(app: FastAPI, saved: dict)`
- Use it in DI guard tests for documents and ingestion so you can assert 503 from real getters.
- Add Engine contract tests under `tests/core/engine_contract/` for `stream_context` vector/keyword shape/order.
- Add OpenAPI drift job step in CI (validate job):
  - Run `uv run python -c "import json; from graph_rag.api.main import create_app; import json; from fastapi.encoders import jsonable_encoder; print(json.dumps(jsonable_encoder(create_app().openapi())))" > openapi.json`
  - Compare against `docs/openapi.json`; warn on diff (don’t fail build yet).

## Acceptance check for each PR
- New tests green locally (`make test`).
- CI validate job green (lint, format, unit tests, hot-path coverage report).
- If touching Memgraph behavior, include label `memgraph` to run integration job.

## References
- Progress and plan: `memory-bank/progress.md`
- Workflow: `memory-bank/development-workflow.md`

Good luck. Deliver autonomously and keep the loop green. Use TDD; change one thing at a time; ship reversible increments.
