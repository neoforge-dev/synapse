# Project Progress

## What Works
- Core domain models and classes are implemented and tested with unit tests.
- Framework for connecting to Memgraph DB via Docker.
- Infrastructure components necessary for the initial workflows.
- Basic graph and vector store interfaces and implementations.
- FastAPI app structure is set up with initial API endpoints
- Base models defined (Document, Chunk, Entity, Relationship)
- Interface definitions are in place for GraphStore and VectorStore
- MemgraphGraphRepository implementation completed and passing tests
- SimpleVectorStore implementation completed with cosine similarity search for text chunks

## What's Left
- Integration tests for API endpoints are failing.
- Ingestion pipeline implementation.
- Implementation of query mechanism for RAG.
- Additional vector store implementations.
- Extended command line tools.
- Integration tests for API/CLI component
- Integration tests for NLP component
- Web UI implementation

## Current Status
- `SimpleVectorStore` implementation for vector storage and similarity search
- Integration tests passing for `MemgraphGraphRepository`
- Core domain models and business logic are functional
- API endpoints are defined but failing integration tests
- CLI commands needs to be expanded
- Completed basic implementation of core components
- Some integration tests passing
- Working on stabilizing interfaces between components

## Known Issues
- Running Memgraph within docker-compose setup sometimes requires manual restart
- Integration tests for API endpoints are not passing
- Embedding model needs to be optimized for production use
- SimpleVectorStore is currently duplicated in two locations:
  - `graph_rag/stores/simple_vector_store.py`
  - `graph_rag/infrastructure/vector_stores/simple_vector_store.py`
  - Code is nearly identical in both locations
  - Need to consolidate to a single implementation and update imports
- Need to finalize API design for Query Engine
- Need to determine remaining edge cases for Entity/Relationship extraction

## Completed
- Project structure and FastAPI app setup
- `GraphStore` interface definition
- `MemgraphGraphRepository` implementation
- Database connection management
- `SimpleVectorStore` implementation created with cosine similarity search for text chunks.
  - Uses sentence-transformers for embedding generation
  - Implements VectorStore interface with add_chunks and search methods
  - Provides in-memory storage of embeddings with numpy
  - Note: Currently exists in two locations (graph_rag/stores/ and graph_rag/infrastructure/vector_stores/) 
    with identical implementations - needs consolidation
- All integration tests for `MemgraphGraphRepository` are passing
- FastAPI app structure with initial endpoints
- Base model definitions for Document, Chunk, Entity, Relationship
- GraphStore interface definition
- MemgraphGraphRepository implementation (passes all integration tests)
- VectorStore interface definition
- SimpleVectorStore implementation:
  - Uses cosine similarity for text chunks
  - Uses sentence-transformers for embedding generation (all-MiniLM-L6-v2 by default)
  - Implements VectorStore interface with methods for adding chunks and searching
  - Includes robust error handling for embedding generation failures
  - In-memory storage of chunks and embeddings with chunk ID lookup
  - Currently duplicated in two locations (needs consolidation)
- ✅ Fixed IngestionService initialization parameter mismatch in dependencies.py
- ✅ Added error handling for undefined LLM_TYPE in settings in create_llm_service

## Blocked By
- Integration tests for other modules (API/CLI, NLP) are pending
- Integration tests for API/CLI component (needs implementation)
- Integration tests for NLP component (needs implementation)

## Next Steps
1. Consolidate the duplicate SimpleVectorStore implementations
2. Run and fix API/CLI integration tests
3. Run and fix NLP integration tests
4. Implement Ingestion Pipeline
5. Implement Query Engine
6. Start Web UI implementation 

All MemgraphGraphRepository CRUD tests now pass after fixing chunk property persistence (id/document_id always set). 