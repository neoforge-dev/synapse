# Active Context

This document tracks the current focus of work, recent changes, next steps, and active decisions or considerations.

## Current Focus

*   **Status:** Fixed CLI ingest command tests in `tests/integration/test_ingest_command.py` by updating the repository type to use `MemgraphGraphRepository` instead of `MemgraphRepository`. All tests in this file are now passing.
*   **Task:** Continue running tests to identify any remaining test failures.
*   **Recent Activity:**
    *   Fixed the CLI ingest command compatibility by updating the `process_and_store_document` function to use `MemgraphGraphRepository` instead of `MemgraphRepository`. 
    *   Updated the `memgraph_repo` fixture in conftest.py to return a `MemgraphGraphRepository` instance.
    *   Fixed `mock_document_processor` fixture to properly mock the `chunk_document` method.
    *   Corrected imports in the test files.
    *   Added previously missing `ChunkData` import in test_ingest_command.py.
    *   Corrected import paths for `Settings`, `EmbeddingModel`, `VectorStore`, `ProcessedDocument`, and various API schemas.
    *   Commented out unused imports (`NodeFactory`, `prompts`).
    *   Added missing dependency `faiss-cpu`.
    *   Standardized usage of the `GraphRepository` protocol from `interfaces.py` instead of `GraphStore` across core components, services, API routers, and tests.
    *   Fixed `NameError: name 'MockerFixture' is not defined` in tests.
    *   Refactored `graph_rag/api/dependencies.py` to centralize dependency creation using factory functions and a singleton cache pattern.
    *   Corrected numerous import errors across the API layer, core components, and tests.
    *   Refactored Memgraph data handling in `MemgraphGraphRepository` to correctly reconstruct Pydantic models from `mgclient` results (using node properties and labels).
    *   Fixed `SimpleVectorStore` to use `EmbeddingService` dependency and added locking.
    *   Updated test configurations (`conftest.py`) and individual test suites (`tests/`) to align with refactored dependencies and Memgraph data handling.
    *   Fixed logic in API routers (e.g., search query, document deletion).
    *   Fixed `GraphDebugger` queries and result parsing.
    *   Fixed `IngestionService` to add chunks to the vector store.
    *   Consolidated duplicate `SimpleVectorStore` implementations by removing the deprecated version in `graph_rag/stores/` and keeping the newer implementation in `graph_rag/infrastructure/vector_stores/`.

## Next Steps

1.  **Run Tests:** Execute `poetry run pytest` to identify any remaining failing tests.
2.  **Debug Failures:** Analyze the pytest output for any failing tests.
3.  **Iterative Fixing:** Address runtime errors in component logic, dependency injection, or test assertions.
4.  **Increase Test Coverage:** Work on improving the test coverage to reach the 80% target.
5.  **Update Memory Bank:** Reflect fixes and new status in `progress.md` and `active-context.md`.
6.  **Repeat:** Continue until all tests pass.

## Active Decisions / Considerations

*   **Debugging Protocol:** A new structured debugging protocol has been implemented to ensure consistent, thorough debugging practices across the project. This includes analysis phases, systematic investigation, implementation guidelines, and documentation requirements. See `debugging-protocol.md` for details.
*   **Singleton Pattern:** The module-level cache in `dependencies.py` acts as a singleton store. Ensure this is thread-safe if concurrent requests modify shared state (though current dependencies seem mostly read-only after initialization). For now, it simplifies dependency management across API requests and lifespan events.
*   **Memgraph Data Mapping:** The pattern of reconstructing Pydantic models from `mgclient` node properties and labels (see `system-patterns.md`) is critical. Ensure all necessary properties are captured and types are correctly handled.
*   **Test Coverage:** Still needs to be addressed after core functionality is stable.

## Blockers
- **Memgraph Query Error:** `mgclient.Column object is not subscriptable`. Investigation needed (library update/wrapper). - *This might be resolved by recent refactoring, needs confirmation.*
- **Failing Integration Tests:** API/CLI and NLP processing tests need fixing. - *Previous failures were during collection, need to check runtime failures now.*

## Next Steps
1.  **Run Tests:** Verify test collection passes.
2.  **Resolve Memgraph Client Issue (if still present):** Update library or add wrapper.
3.  **Fix Runtime Test Failures:** Address any tests failing during execution.
4.  **Implement/Test:** Complete Ingestion Pipeline.
5.  **Implement:** Query Engine. 