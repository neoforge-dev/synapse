# Active Context (Optimized)

## Current Focus & Blockers
- **CRITICAL:** Resolve widespread test failures (`make test && make test-memgraph`).
  - **Error Types Observed:**
    - `TypeError: object AsyncMock can't be used in 'await' expression` (Unit Tests, e.g., `test_add_document`, `test_add_chunk` in `test_graph_store.py`)
    - `TypeError: object AsyncBoltDriver can't be used in 'await' expression` (Integration Tests, e.g., `test_delete_document` in `test_graph_repository.py`, `test_capture_system_state` in `test_debug_tools.py`)
    - Fixture errors (`fixture 'mocker' not found`, `TypeError` in RAG engine/KG builder fixtures).
    - Mocking/Patching errors (`AttributeError` patching services/dependencies in API/Service tests).
    - API/CLI Test Failures (`503 Service Unavailable`, `404 Not Found`, `AssertionError` on status codes, CLI command structure/options issues).
    - `pydantic.ValidationError` in debugging scenario tests.
    - NLTK `LookupError: Resource punkt_tab not found`.
    - Spacy `OSError: [E050] Can't find model 'en_core_web_sm'`.
    - Settings load errors (`AssertionError` in `test_settings.py`).
    - Abstract class instantiation errors (`InMemoryKnowledgeGraphBuilder`).
    - `AttributeError` on expected methods (`save_document`, `get_document`, etc. likely due to GraphStore interface refactor).
- Fix underlying issues causing these errors (async handling, mock setup, fixture scope, dependency injection, CLI structure, environment setup for NLP models).

## Recent Changes
- Refactored `MemgraphGraphRepository` to implement `GraphStore` interface.
- Added `Node`, `Entity`, `Relationship` models to domain.
- Updated `MemgraphGraphRepository` methods (`get_neighbors`, `search_entities_by_properties`, `get_entity_by_id`, `add_node`, `add_nodes`, `add_relationship`) to use new models.
- Added unit and integration tests for `Entity`/`Relationship` usage.
- Attempted fix for `async with` in `_execute_write/read_query`.

## Next Steps (Immediate)
1. **Troubleshoot `TypeError: object AsyncMock/AsyncBoltDriver can't be used in 'await' expression`:** Re-examine `_execute_write_query`, `_execute_read_query`, `_get_driver` and how mocks/drivers are awaited/used in tests.
2. **Fix NLTK/spaCy Model Errors:** Ensure `punkt_tab` and `en_core_web_sm` are downloaded correctly in the test environment (check `Makefile` `download-nlp-data` target and test setup).
3. **Address Fixture/Mocking Errors:** Review `pytest` fixtures (scope, dependencies like `mocker`), patch targets, and mock configurations (`AsyncMock`, `MagicMock`) in failing tests.
4. **Investigate API/CLI Failures:** Check API dependencies (if services are correctly initialized/mocked), test client usage (`AsyncClient` vs `TestClient`), and review Typer CLI command definitions/options.
5. **Correct `AttributeError`s on repository methods:** Ensure tests use the correct `GraphStore` interface methods (`add_node`, `get_node_by_id`, etc.) instead of older/removed ones (`save_document`, etc.).

## Open Questions
- Best way to handle async driver/mock interactions in tests? 