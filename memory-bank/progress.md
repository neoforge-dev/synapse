# Progress and Status

## Overall Summary
- **Current State:** Config stability improved. Env aliasing added; API import collision resolved. New tests verify settings aliasing and `MemgraphConnectionConfig` defaults. Core engine remains green; `/documents` API tests pass; some API/integration tests still pending fixes.
- **Key Achievement:** Unified settings behavior across app/tests; removed ambiguous settings imports; added guardrail tests.
- **Critical Concern:** Previously blocking Pydantic validation for Memgraph connection is mitigated by alias handling; need to confirm via full test run.

## What Works Well
- **Setup & Core:** Poetry, Config, Pydantic Models.
- **Infrastructure:** `MemgraphGraphRepository` (CRUD tested, SSL mode attribute error fixed, basic empty label handling for nodes and relationships added), `SimpleVectorStore`, `Spacy/MockEntityExtractor`, `Mock/OpenAILLMService` placeholders.
- **Services/Engine:** `IngestionService` (basic flow), `SimpleGraphRAGEngine` (good test coverage for helpers & key scenarios), `PersistentKnowledgeGraphBuilder` (refactored tests for its direct API).
- **API:** FastAPI app, routers, DI via `api/dependencies.py`. Document management (`/api/v1/documents`) endpoint tests are now passing with mocks.
- **Testing:** `pytest` setup; foundational API/Memgraph tests pass. `SimpleGraphRAGEngine` and orchestrator have strong test coverage.

## High-Priority Plan (Next Steps)
Guided by Pareto and core user journey (ingest → retrieve → answer), we will deliver highest-value improvements first.

1) Streamed context retrieval from core engine (must-have for API parity)
   - Reduces divergence between orchestrator and simple engine
   - Enables consistent streaming in `/search/query?stream=true`
   - TDD: add failing test for `SimpleGraphRAGEngine.stream_context`, then implement minimal functionality (vector search only; keyword later if needed)

2) DI hardening and guard tests (stability, fast failure)
   - Add unit tests for DI getters to return 503 when state is missing (`get_vector_store`, `get_ingestion_service`, `get_graph_rag_engine`)
   - Ensure factories are consistently used across app/state

3) Consolidate Memgraph client usage in DI (eliminate drift)
   - Verify no vestigial neo4j driver paths remain
   - Confirm mgclient-backed repo is the only concrete implementation wired at runtime

4) Coverage on ingest/query vertical slice (lock behavior)
   - Add tests around ingestion → vector store → query mapping for metadata/score propagation
   - Keep YAGNI: test only the critical paths actually used by API/CLI

5) Refactors while green (only after tests)
   - Clarify naming and dependency seams in `api/dependencies.py`
   - Remove dead code paths and comments that can mislead future work

## Other Important Tasks (Post-Critical Path)
- Robust error mapping in API (uniform problem details)
- Performance tuning of vector/graph joins (as real backends are used)
- Deployment/observability (non-MVP)

## Immediate Sprint Backlog
- [ ] Add failing test: `tests/core/test_graph_rag_engine_stream.py::test_stream_context_vector`
- [ ] Implement `SimpleGraphRAGEngine.stream_context` (vector only)
- [ ] Run tests, keep green
- [ ] Commit changes with descriptive message
- [ ] Add DI guard tests for 503 behavior

## Notes
- YAGNI: Implement streaming for vector first; keyword later if needed
- TDD non-negotiable: define behavior in tests before code
- Keep vertical slices small and shippable
