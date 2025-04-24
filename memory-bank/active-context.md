# Active Context - [Current Date]

## Focus
- Resolved multiple test failures in `tests/core/test_graph_rag_engine.py` and `tests/core/test_graph_rag_engine_orchestrator.py`.

## Recent Changes
- **`SimpleGraphRAGEngine` (`graph_rag/core/graph_rag_engine.py`):**
    - `_find_entities_in_graph_by_properties`: Corrected logic to use `entity.text` instead of `entity.name` for property lookups, as `ExtractedEntity` might not have `name` populated.
    - `query`: Ensured `graph_context_tuple` is initialized to `([], [])` when graph context is enabled but no entities are extracted or found, instead of `None`.
- **`MemgraphGraphRepository` (`graph_rag/infrastructure/graph_stores/memgraph_store.py`):**
    - Refactored `delete_document` method for multi-step deletion (find chunks, delete doc, delete chunks) with improved logging.
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
- **Memgraph Query Error:** `mgclient.Column object is not subscriptable`. Investigation needed (library update/wrapper). - *This might be resolved by recent refactoring, needs confirmation.*
- **Failing Integration Tests:** API/CLI and NLP processing tests need fixing. - *Previous failures were during collection, need to check runtime failures now.*

## Next Steps
1.  **Run Tests:** Verify test collection passes.
2.  **Resolve Memgraph Client Issue (if still present):** Update library or add wrapper.
3.  **Fix Runtime Test Failures:** Address any tests failing during execution.
4.  **Implement/Test:** Complete Ingestion Pipeline.
5.  **Implement:** Query Engine. 