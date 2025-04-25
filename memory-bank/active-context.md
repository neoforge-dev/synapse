# Active Context - [Current Date]

## Focus
- Debugging and fixing the failing integration test `test_search_then_ingest_interaction` in `tests/api/test_search_ingestion.py`.

## Recent Changes
- **Previous:** Resolved multiple `ModuleNotFoundError` and `ImportError` issues in `tests/api/test_search_ingestion.py`.
- **`test_search_then_ingest_interaction`:**
    - Identified the root cause of the failure: The test was verifying against the `VectorStore` instance stored in `app.state` (created during lifespan startup), while the background ingestion task populated a *different*, cached singleton instance managed by the dependency injection system (`_singletons` cache in `dependencies.py`).
    - **Fix:** Introduced a new fixture `singleton_vector_store` in `tests/conftest.py` to resolve and provide the actual cached `VectorStore` instance used by the application routes.
    - **Fix:** Modified `test_search_then_ingest_interaction` to use the `singleton_vector_store` fixture instead of `app.state.vector_store` for verification.
    - Added missing import for `MockEmbeddingService` in `tests/api/test_search_ingestion.py`.
    - Updated assertions in the final search step of the test to correctly match the expected response schema (`results` list containing scored chunks).

## Next Steps
1.  **Run All API Tests:** Execute `pytest tests/api/` to ensure no regressions were introduced and all API tests now pass.
2.  **Address Coverage:** The test run revealed very low coverage (33%). Need to prioritize adding more tests, especially for API routers and core engine logic.
3.  **Review Other Test Suites:** Check the status of other test suites (CLI, Memgraph store, Entity Extractor, etc.).
4.  **Fix `SimpleVectorStore.ingest_chunks` Bug:** Although the test passes, the redundant embedding generation in `SimpleVectorStore.ingest_chunks` should be fixed to use the pre-computed embeddings if available in `ChunkData`.
5.  **Update Memory Bank:** Reflect the successful fix and low coverage in `progress.md`.

## Active Decisions/Considerations
- The discrepancy between `app.state` initialization and dependency injection caching was the key issue for the integration test failure. Using fixtures that accurately reflect how the application resolves dependencies is crucial for reliable integration testing.
- The low test coverage (33%) is a significant risk and needs immediate attention.

## Blockers
- Low test coverage.

## Active Decisions/Considerations
- The mocking strategy for graph context retrieval (`get_neighbors`) in `test_simple_engine_query_with_graph_context` needed careful adjustment to match how the implementation calls the repository (individual IDs) and aggregates results.
- Asserting calls on mocks involving complex Pydantic objects requires careful inspection of passed arguments rather than direct object comparison, especially when IDs are dynamically generated. Using `call_count` and inspecting `await_args` or `call_args` is more robust.

## Blockers
- **ModuleNotFoundError:** `graph_rag/core/graph_rag_engine.py` imports a non-existent module `graph_rag.llm.mock_llm`. Needs fixing.
- **Failing Integration Tests:** API/CLI and NLP processing tests may still have runtime failures.

## Next Steps
1.  **Fix `ModuleNotFoundError` in `graph_rag/core/graph_rag_engine.py`.**
2.  **Run Integration Tests:** Specifically target API/CLI and NLP suites to identify and fix runtime failures.
3.  Verify status of other test suites (CLI, Memgraph store, Entity Extractor).
4.  Increase Test Coverage significantly.
5.  Implement and fix NLP integration tests (if different from step 2).
6.  Implement Ingestion Pipeline core logic.
7.  Implement Query Engine core logic.

## Current Focus

The immediate focus was reviewing and correcting property access issues in `graph_rag/infrastructure/graph_stores/memgraph_store.py` due to the `mgclient` driver returning `Node` objects. This review is now complete.

## Recent Changes & Decisions

- Confirmed that `MemgraphGraphRepository` methods (`get_chunks_by_document_id`, `get_chunk_by_id`, `get_document_by_id`) now correctly access node properties using `.properties`.
- Updated `progress.md` to reflect the successful refactoring and testing of `MemgraphGraphRepository`.
- Identified remaining issues: `ModuleNotFoundError` in tests and low test coverage.

## Next Steps

1.  **Fix `ModuleNotFoundError`**: Investigate and resolve the import error related to `graph_rag.llm.mock_llm` appearing in tests.
2.  **Verify Test Suites**: Check the status of all test suites to ensure no other failures were missed.
3.  **Increase Test Coverage**: Prioritize writing additional tests to improve the overall coverage, currently around 27%.

## Active Considerations / Blockers

- Low test coverage poses a risk for future refactoring and stability. 