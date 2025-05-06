# Progress and Status

## Overall Status
- Core infrastructure (DB connection, vector store basics, API structure, DI) is functional.
- Basic ingestion and query pipelines exist but require thorough testing and refinement.
- All previously failing tests are now passing (after fixes to Memgraph driver usage, API responses, dependency injection/mocking in tests).
- **Critical Issue: Test coverage is very low (~33%).**

## What Works
- **Core:** Poetry setup, Config, Pydantic Models.
- **Infrastructure:** `MemgraphGraphRepository` (CRUD tested), `SimpleVectorStore` (basics work, locking implemented), `Spacy/MockEntityExtractor`, `Mock/OpenAILLMService` placeholders.
- **Services/Engine:** `IngestionService` basic flow, `GraphRAGEngine` structure exists.
- **API:** FastAPI app, routers (documents, ingestion, search, query), lifespan management, singleton dependencies via `api/dependencies.py`.
- **Testing:** `pytest` setup, basic API tests passing (often with mocks), Memgraph integration tests passing.

## What's Left / Needs Doing (High Priority First)
1.  **Increase Test Coverage:** Add comprehensive unit/integration tests for API, services, engine, storage, etc. (Currently ~33%).
2.  **Refactor KG Builder Tests:** Rewrite `tests/core/test_persistent_kg_builder.py` to use `add_*` methods.
3.  **Review/Fix Skipped Tests:** Address the 45 skipped tests.
4.  **Implement Core Engine Logic:** Build out query planning, graph traversal, context building, LLM interaction in `GraphRAGEngine`.
5.  **End-to-End Testing:** Add tests covering full ingestion-retrieval flow.
6.  **Refine Error Handling:** Improve robustness across layers.
7.  **Implement Real LLMService:** Flesh out `OpenAILLMService` or add alternatives.
8.  **Scalability/Performance:** Evaluate indexing, query optimization.
9.  **Deployment:** Define strategy.
10. **Monitoring/Logging:** Implement.

## Known Issues / Bugs
*   **Low Test Coverage (~33%):** High risk for regressions.
*   `PersistentKnowledgeGraphBuilder` tests are not verifying logic (core calls commented out).
*   Potential inconsistencies if services are created bypassing singleton getters (unlikely with current DI).
*   Duplicate dependency getter definitions (`main.py` vs. `dependencies.py`) identified as confusing.

## Next Steps (Priority Order)
1.  **Fix `ModuleNotFoundError` in `graph_rag/core/graph_rag_engine.py`.**
2.  Verify status of other test suites (CLI, Memgraph store, Entity Extractor).
3.  Increase Test Coverage significantly.
4.  Implement and fix NLP integration tests.
5.  Implement Ingestion Pipeline core logic.
6.  Implement Query Engine core logic.
7.  (Post-MVP) Begin Web UI implementation.

All MemgraphGraphRepository CRUD tests now pass after fixing chunk property persistence (id/document_id always set). 