# Project Progress

## Completed & Working
- **Core:** Domain models, graph/vector store interfaces, Memgraph DB connection framework.
- **Infrastructure:**
    - `MemgraphGraphRepository`: Implemented and passing integration tests.
    - `SimpleVectorStore`: Implemented (in-memory, sentence-transformers `all-MiniLM-L6-v2`, cosine similarity). *Needs consolidation from duplicate locations*.
- **API/App:** FastAPI structure setup, initial endpoints defined.
- **Fixes:** Resolved `IngestionService` init params, LLM_TYPE handling, Memgraph chunk property persistence issues.

## What's Left / Outstanding
- **Core:** Implement ingestion pipeline, RAG query mechanism.
- **Integrations:** Fix failing API integration tests, implement/fix NLP component tests.
- **Features:** Expand CLI tools, add alternative vector stores, implement Web UI (post-MVP).

## Known Issues & Blockers
- **Critical:** API integration tests are failing.
- **Refactoring:** Duplicate `SimpleVectorStore` implementation exists in `graph_rag/stores/` and `graph_rag/infrastructure/vector_stores/` -> Needs consolidation.
- **Operational:** Memgraph Docker setup sometimes requires manual restart.
- **Enhancements:** Embedding model needs production optimization, finalize Query Engine API, define entity/relationship extraction edge cases.

## Next Steps (Priority Order)
1.  Consolidate duplicate `SimpleVectorStore`.
2.  Fix failing API integration tests.
3.  Implement and fix NLP integration tests.
4.  Implement Ingestion Pipeline.
5.  Implement Query Engine.
6.  (Post-MVP) Begin Web UI implementation.

All MemgraphGraphRepository CRUD tests now pass after fixing chunk property persistence (id/document_id always set). 