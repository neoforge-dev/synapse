# Progress and Status

## Overall Summary
- **Current State:** Streaming implemented (vector) and gated (keyword via flag). DI guardrails in place for vector store and search; contract tests added for vector store. CI pipeline added with validate job and label-gated Memgraph job; hot-path coverage reporting enabled. Core and API unit tests are green.
- **Key Achievement:** End-to-end vector streaming through engine and API; keyword streaming feature-flagged with tests. CI now provides quick, non-blocking hot-path coverage feedback.
- **Critical Concern:** Some DI guard tests depend on fixture overrides; added plan to temporarily clear overrides per-test when validating true DI getters.

## What Works Well
- **Setup & Core:** Poetry, Config, Pydantic Models.
- **Infrastructure:** `MemgraphGraphRepository` (CRUD tested, SSL mode attribute error fixed, basic empty label handling for nodes and relationships added), `SimpleVectorStore`, `Spacy/MockEntityExtractor`, `Mock/OpenAILLMService` placeholders.
- **Services/Engine:** `IngestionService` (basic flow), `SimpleGraphRAGEngine` (good test coverage for helpers & key scenarios), `PersistentKnowledgeGraphBuilder` (refactored tests for its direct API).
- **API:** FastAPI app, routers, DI via `api/dependencies.py`. Document management (`/api/v1/documents`) endpoint tests are now passing with mocks.
- **Testing:** `pytest` setup; foundational API/Memgraph tests pass. `SimpleGraphRAGEngine` and orchestrator have strong test coverage.

## High-Priority Plan (Next Steps)
- **Streaming**
  - Implement true incremental keyword streaming when backend supports paging (keep `enable_keyword_streaming` flag).
  - Add engine contract tests for ordering and shape across vector/keyword.
- **DI + Health**
  - Add DI guard tests for graph repo, entity extractor, doc processor, KG builder, ingestion service (clear fixture overrides per-test to hit real getters).
  - Health/readiness probes: vector store size probe; guarded Memgraph ping.
- **Contracts**
  - GraphRepository contract tests (skipped unless Memgraph available): add/get doc/chunk, link entities, delete.
  - GraphRAGEngine contract tests: query, retrieve_context, stream_context, error paths.
- **CI Guardrails**
  - Hot-path coverage reporting (non-blocking) in Makefile and CI. Done.
  - OpenAPI spec drift check (warn-only) in CI.
  - Flaky detector scaffold (collect failures, report/quarantine).
- **Dev Ergonomics**
  - Pre-commit with ruff format/check + commit-msg lint hooks.
  - Test templates for unit/api/contract; update contributing docs.

## Latest progress
- Added advanced integration recipes to `README.md` (jq/xargs for discover→parse→store, multi-root stdin, metadata augmentation, filtering, parallel batching, per-chunk outputs).
- Documented vector store considerations in `README.md` (idempotent re-ingestion and rebuild notes).
- Expanded `docs/ARCHITECTURE.md` with CLI decomposition and typed metadata support.

## Other Important Tasks (Post-Critical Path)
- Robust error mapping in API (uniform problem details)
- Performance tuning of vector/graph joins (as real backends are used)
- Deployment/observability (non-MVP)

## Immediate Sprint Backlog
- [x] Implement `SimpleGraphRAGEngine.stream_context` (vector) and API NDJSON; add tests
- [x] Feature-flag keyword streaming; add tests when enabled
- [x] Add DI guard tests (vector store; search API) and vector store contract test
- [x] CI validate job + label-gated Memgraph + hot-path coverage reporting
- [ ] Add per-test utility to temporarily clear dependency overrides and validate true DI getters (graph repo, etc.)
- [ ] Add GraphRAGEngine and GraphRepository contract tests (skip Memgraph when unavailable)

## Notes
- YAGNI: Implement streaming for vector first; keyword later if needed
- TDD non-negotiable: define behavior in tests before code
- Keep vertical slices small and shippable

## 2025-08-12 — Repo consolidation and docs unification
- Added `docs/HANDBOOK.md` as single source-of-truth; updated `README.md`, `docs/ARCHITECTURE.md`, `docs/PLAN.md`, `docs/BACKLOG.md`, `docs/PROMPT.md`, `docs/MCP.md`.
- Generated/updated navigation: `docs/INDEX.md`, `docs/index.json`; added `docs/DELETION_CANDIDATES.md`.
- Deleted legacy/empty items: `graphrag/`, `handlers/`, `middleware/`, root `services/`, `database/`, root `utils/`, `models/user.go`, `CLAUDE.md`.
- Tech debt: replaced stdout prints in `graph_rag/services/ingestion.py` with debug logs; made CLI admin/search respect `SYNAPSE_API_BASE_URL`.
- CI: deduplicated `.github/workflows/ci.yml` and added hot-path coverage job.
- Tests: unit suite passes (221 passed, 42 skipped). Deprecation warnings noted for later.
