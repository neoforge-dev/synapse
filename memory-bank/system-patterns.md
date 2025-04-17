# System Patterns

## Architecture & Layers
- **Style:** Clean Architecture (Domain → Core → Infra → API/CLI).
- **Layers:**
    1.  **Core Domain (`graph_rag/core/`):** Interfaces, domain models, service contracts.
    2.  **Infrastructure (`graph_rag/infrastructure/`):** Interface implementations (storage, external services like `MemgraphGraphRepository`, `SimpleVectorStore`).
    3.  **API (`graph_rag/api/`):** FastAPI endpoints, schemas, API-level Dependency Injection (DI).
    4.  **Services (`graph_rag/services/`):** Application logic coordinating API and Core (e.g., `IngestionService`).
- **Data Flow:** FastAPI/Typer → GraphRAGEngine → Core Services → GraphStore/VectorStore.

## Key Design Patterns
- **Dependency Injection:** FastAPI `Depends` (API), Manual/Factories (Core). Potential for simplification.
- **Repository Pattern:** `GraphStore` & `VectorStore` interfaces abstract persistence.
- **Factory Pattern:** Functions like `create_knowledge_graph_builder` create configured instances.
- **Async I/O:** Used for DB operations and API endpoints.
- **Pydantic:** Data validation (Models, Settings).

## Component Relationships
- **Knowledge Graph Builder:** Standardized on `SimpleKnowledgeGraphBuilder` (basic impl., sync `build`, uses `GraphStore`). Retrieved via `get_knowledge_graph_builder()`. `PersistentKnowledgeGraphBuilder` exists but unused.
- **Graph Storage:** `GraphStore` implemented by `MemgraphGraphRepository` (connects via `pymgclient`, async CRUD, idempotent writes with `MERGE`, retries via `tenacity`).
- **Vector Storage:** `VectorStore` implemented by `SimpleVectorStore` (in-memory SentenceTransformer "all-MiniLM-L6-v2", cosine similarity). Legacy imports handled via re-export.

## Error Handling
- Exception capturing with detailed logging.
- Fallback mechanisms (e.g., mock services).
- Standard HTTP error responses in API.

## Testing
- **Framework:** `pytest` (unit, integration).
- **Async:** `pytest-asyncio`, `unittest.mock.AsyncMock`.
- **DB:** `pymgclient` for direct Memgraph checks; Dockerized Memgraph for integration tests.
- **Execution:** `Makefile` commands (`test`, `test-memgraph`).

## Debugging Pattern
- **Approach:** Observe -> Gather Info -> Hypothesize -> Verify -> Resolve -> Document.
- **Tools:** Logging, `GraphDebugger`, visualization, direct DB queries.
- *(See `debugging-examples.md` for specific scenarios).* 