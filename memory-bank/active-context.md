# Active Context

## Current Focus
- Consolidating duplicate implementations and fixing dependency issues.
- Resolving confusion between `SimpleKnowledgeGraphBuilder` and `PersistentKnowledgeGraphBuilder` by standardizing on `SimpleKnowledgeGraphBuilder`.

## Recent Changes

- Fixed core domain models and interfaces for cleaner abstractions
- Fixed MemgraphGraphRepository implementation for proper CRUD operations
- Made all MemgraphGraphRepository integration tests pass
- Implemented SimpleVectorStore for vector embeddings storage and similarity search
- Created __init__.py for vector_stores package to expose SimpleVectorStore
- Consolidated duplicate SimpleVectorStore implementations:
  - Kept the one in graph_rag/infrastructure/vector_stores/simple_vector_store.py
  - Added a re-export from graph_rag/stores/__init__.py with a deprecation warning 
  - Updated imports across codebase
- Fixed dependency issues in dependencies.py:
  - Fixed the IngestionService initialization parameter mismatch by properly aligning parameter names (document_processor, graph_store, etc.) 
  - Added error handling for missing LLM_TYPE in settings to prevent API crashes
  - Corrected incorrect reference to a non-existent embedding module
  - Fixed a missing embedding service implementation
  - Simplified SimpleVectorStore construction to use a direct model name
- Standardized KnowledgeGraphBuilder implementation:
  - Consolidated the two KnowledgeGraphBuilder implementations by standardizing on `SimpleKnowledgeGraphBuilder`
  - Renamed `get_kg_builder` to `get_knowledge_graph_builder` in main.py for consistency
  - Updated the `KnowledgeGraphBuilderDep` to use `get_knowledge_graph_builder` instead of `get_kg_builder`
  - Updated test dependency overrides to match the new function name
- All MemgraphGraphRepository CRUD tests now pass after fixing chunk property persistence (id/document_id always set).

## Blockers
- Memgraph database query execution issue: "'mgclient.Column' object is not subscriptable" 
- Remaining integration tests for API/CLI and NLP processing components still fail
- Need to fix these for complete functionality

## Next Steps
1. Resolve the Memgraph client library compatibility issue (possibly update library or add a wrapper) 
2. Run and fix API/CLI integration tests
3. Run and fix NLP integration tests
4. Implement and test the complete Ingestion Pipeline
5. Implement the Query Engine 