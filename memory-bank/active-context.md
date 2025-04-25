# Active Context - [Current Date]

## Focus
- Resolved multiple test failures in `tests/core/test_graph_rag_engine.py` and `tests/core/test_graph_rag_engine_orchestrator.py`.

## Recent Changes
- **`SimpleGraphRAGEngine` (`graph_rag/core/graph_rag_engine.py`):**
    - `_find_entities_in_graph_by_properties`: Corrected logic to use `entity.text` instead of `entity.name` for property lookups, as `ExtractedEntity` might not have `name` populated.
    - `query`: Ensured `graph_context_tuple` is initialized to `([], [])` when graph context is enabled but no entities are extracted or found, instead of `None`.
- **`MemgraphGraphRepository` (`graph_rag/infrastructure/graph_stores/memgraph_store.py`):**
    - **Review Complete:** Verified changes for `get_document_by_id`, `add_chunk`, `get_chunks_by_document_id`, and `get_chunk_by_id`. Changes correctly address `mgclient.Node.properties` access, use the correct relationship (`CONTAINS`), and improve error handling (e.g., `add_chunk` checks for document existence).
    - Removed the old `delete_document` multi-step logic as it's likely superseded or incorporated into other methods. *(Self-correction: Previous note about `delete_document` was from an earlier context, the relevant changes reviewed were the property access fixes.)*
- **Tests (`tests/core/test_graph_rag_engine.py`):**
    - Corrected `combined_text` calculation in assertions to use space (" ") as a separator, matching the engine's implementation.
    - Replaced incorrect `assert_awaited_once_with` with `assert_called_once_with` for `AsyncMock` calls (`vector_store.search`).
    - Fixed `search_entities_by_properties` assertions to check `call_count` and use `assert_any_call` for individual property lookups, reflecting the implementation's loop.
    - Fixed `get_neighbors` mock logic to handle individual entity ID calls and updated assertions for call count (3 due to expansion) and final aggregated context (`([], [])` based on mock behavior).
    - Fixed attribute access from `rag_engine.graph_store` to `rag_engine._graph_store`.
    - Removed incorrect assertions checking for non-existent `result.extracted_entities` attribute.
- **Tests (`tests/core/test_graph_rag_engine_orchestrator.py`):**
    - Added missing import for `ExtractedEntity`, `ExtractionResult`.
    - Corrected `mock_document_processor` fixture to return `ChunkData` objects (instead of `Chunk`) and dynamically use the `document_id` from the input `DocumentData`.
    - Fixed `kg_builder.add_document` assertion to expect `DocumentData` with `ANY` id and check content/metadata.
    - Corrected `kg_builder.add_chunk` assertion logic: Replaced `assert_has_awaits` with manual inspection of `await_args_list` to verify the passed `ChunkData` objects' attributes (id, text, document_id, embedding).
    - Corrected `kg_builder.add_relationship` assertion to expect 0 calls, matching the mock `ExtractionResult` which had no relationships.

## Next Steps
- Commit the recent fixes.
- Review remaining skipped tests in `tests/core/test_graph_rag_engine.py` and address necessary refactoring.
- Proceed with implementing further features or addressing other test failures based on project priorities.

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