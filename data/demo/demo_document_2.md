# Graph-RAG Architecture

## Components

### Graph Database (Memgraph)
- Stores entities and relationships
- Enables multi-hop traversal
- Provides graph context for RAG

### Vector Store (FAISS)
- Stores document embeddings
- Enables semantic search
- Provides similarity matching

### LLM Service
- Generates responses
- Uses graph + vector context
- Provides citations

## Integration

The system integrates graph and vector search to provide accurate, context-aware responses with citation tracking.
