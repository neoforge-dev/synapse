# Active Context

## Current Focus
- Stabilize core components and integration tests.
- Standardize on `SimpleKnowledgeGraphBuilder`.

## Recent Changes
- **Core Models/Interfaces:** Fixed and cleaned.
- **`MemgraphGraphRepository`:** Implemented CRUD, all integration tests pass (fixed chunk property persistence).
- **Vector Store:**
    - Implemented `SimpleVectorStore`.
    - Consolidated duplicate implementations, using `graph_rag/infrastructure/vector_stores/simple_vector_store.py`.
    - Added re-export from `graph_rag/stores/__init__.py` (with deprecation warning).
    - Updated imports codebase-wide.
- **Dependencies (`dependencies.py`):**
    - Fixed `IngestionService` initialization parameter mismatch.
    - Added error handling for missing `LLM_TYPE`.
    - Corrected embedding module references and missing service implementation.
    - Simplified `SimpleVectorStore` construction.
- **Knowledge Graph Builder:**
    - Standardized on `SimpleKnowledgeGraphBuilder`.
    - Renamed `get_kg_builder` -> `get_knowledge_graph_builder` in `main.py`.
    - Updated `KnowledgeGraphBuilderDep` and test overrides.

## Blockers
- **Memgraph Query Error:** `mgclient.Column object is not subscriptable`. Investigation needed (library update/wrapper).
- **Failing Integration Tests:** API/CLI and NLP processing tests need fixing.

## Next Steps
1.  **Resolve Memgraph Client Issue:** Update library or add wrapper.
2.  **Fix Integration Tests:** Address API/CLI and NLP test failures.
3.  **Implement/Test:** Complete Ingestion Pipeline.
4.  **Implement:** Query Engine. 