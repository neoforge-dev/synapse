# Progress and Status

This document tracks project progress, identifies what works, what remains to be built, the overall status, and known issues.

## What Works

*   **Dependency Management:** Poetry setup is complete and managing dependencies.
*   **Configuration:** Centralized configuration (`graph_rag/config.py`) is in place.
*   **Core Models:** Pydantic models for documents, nodes, relationships, chunks are defined.
*   **Memgraph Integration:** `MemgraphGraphRepository` can connect, perform CRUD operations (add, get, delete nodes/relationships), and reconstruct Pydantic models from query results.
*   **Vector Store:** `SimpleVectorStore` provides basic add/search functionality with locking.
*   **Dependency Injection:** Centralized factories and cache in `graph_rag/api/dependencies.py` handle component instantiation.
*   **API Structure:** FastAPI application (`main.py`) with routers for ingestion, query, debug is set up.
*   **Lifespan Management:** Basic startup/shutdown logic for initializing/closing resources (like graph store connection) is implemented.
*   **Basic Ingestion:** `IngestionService` orchestrates chunking and adding to graph/vector stores.
*   **Basic Query:** `GraphRAGEngine` structure exists, though end-to-end query flow needs validation.
*   **Debugging Tools:** `GraphDebugger` can execute Cypher queries and return raw results.

## What's Left to Build / Fix

*   **End-to-End Testing:** Comprehensive integration tests covering the full ingestion and query pipelines.
*   **Query Pipeline Logic:** Thoroughly test and potentially refine the logic within `GraphRAGEngine`, including vector search, graph retrieval, and LLM interaction.
*   **LLM Integration:** Ensure the LLM component (`LlamaCppLLMService` or alternatives) integrates correctly for response synthesis.
*   **Error Handling:** Robust error handling throughout the API and core components.
*   **Scalability & Performance:** Optimize queries, potentially add indexing in Memgraph, evaluate vector store performance.
*   **Deployment:** Define deployment strategy (e.g., Docker, K8s).
*   **Monitoring & Logging:** Implement proper logging and potentially monitoring.
*   **Test Coverage:** Increase unit and integration test coverage significantly.

## Current Status

*   **Overall:** Major refactoring complete. Core components (graph store, vector store, basic API structure, dependency injection) are implemented. Import errors and major inconsistencies (like GraphStore vs GraphRepository) have been resolved across the codebase and tests.
*   **Testing:** Test collection should now pass. The next step is to run `poetry run pytest` to identify and address any *runtime* test failures.

## Known Issues / Bugs

*   **Runtime Test Failures:** Specific failures need to be identified by running `poetry run pytest`.
*   **Memgraph Client Issue:** Potential `mgclient.Column object is not subscriptable` error needs verification after recent changes.
*   Potential race conditions or concurrency issues, especially around shared resources like the vector store (mitigated partially by locking in `SimpleVectorStore`).
*   LLM interaction and response synthesis logic is likely incomplete or untested.

## Completed & Working
- **Core:** Domain models, graph/vector store interfaces, Memgraph DB connection framework.
- **Infrastructure:**
    - `MemgraphGraphRepository`: Implemented and passing integration tests.
    - `SimpleVectorStore`: Implemented (in-memory, sentence-transformers `all-MiniLM-L6-v2`, cosine similarity). *Consolidated duplicate implementations*.
- **API/App:** FastAPI structure setup, initial endpoints defined.
- **Fixes:** 
    - Resolved `IngestionService` init params, LLM_TYPE handling, Memgraph chunk property persistence issues.
    - Fixed CLI ingest command tests in `tests/integration/test_ingest_command.py` by updating the repository type to use `MemgraphGraphRepository` instead of `MemgraphRepository`.
- **Tests:** 
    - Query pipeline integration tests (`tests/integration/test_query_pipeline.py`) are now passing (using mocked engine).
    - CLI ingest command tests (`tests/integration/test_ingest_command.py`) are now passing.

## What's Left / Outstanding
- **Core:** Implement ingestion pipeline, RAG query mechanism (actual logic, beyond mocks).
- **Integrations:** Verify status of other test suites (CLI, Memgraph store, Entity Extractor, etc.).
- **Test Coverage:** Significantly increase unit and integration test coverage.
- **Features:** Expand CLI tools, add alternative vector stores, implement Web UI (post-MVP).

## Known Issues & Blockers
- **Low Test Coverage:** Current coverage (~27%) is significantly below target (e.g., 80%).
- **Operational:** Memgraph Docker setup sometimes requires manual restart.
- **Enhancements:** Embedding model needs production optimization, finalize Query Engine API, define entity/relationship extraction edge cases.

## Next Steps (Priority Order)
1.  Verify status of other test suites (CLI, Memgraph store, Entity Extractor).
2.  Increase Test Coverage significantly.
3.  Implement and fix NLP integration tests.
4.  Implement Ingestion Pipeline core logic.
5.  Implement Query Engine core logic.
6.  (Post-MVP) Begin Web UI implementation.

All MemgraphGraphRepository CRUD tests now pass after fixing chunk property persistence (id/document_id always set). 