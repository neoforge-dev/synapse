# System Patterns

## System Architecture

This application follows a **modular, layered architecture** that separates core domain logic from infrastructure and API concerns:

1. **Core Domain Layer** (`graph_rag/core/`)
   - Contains core interfaces and domain models
   - Defines contract for all services
   - Includes base implementations for key components

2. **Infrastructure Layer** (`graph_rag/infrastructure/`)
   - Implements interfaces defined in core
   - Includes persistent storage and external services
   - Examples: MemgraphRepository, SimpleVectorStore

3. **API Layer** (`graph_rag/api/`)
   - FastAPI endpoints and routers
   - API schemas and dependency injection
   - Request handling and validation

4. **Services Layer** (`graph_rag/services/`)
   - Application services that coordinate operations
   - Glue between API and core domain
   - Example: IngestionService

## Key Design Patterns

### Dependency Injection

Dependencies are managed in two ways:

1. **FastAPI Depends**: The API uses FastAPI dependency injection:
   ```python
   @router.post("/documents")
   async def ingest_document(
       payload: IngestRequest = Body(...),
       ingestion_service: IngestionService = Depends(get_ingestion_service)
   ):
   ```

2. **Application State**: Core components are stored in app.state:
   ```python
   app.state.graph_repository = MemgraphRepository(driver=app.state.neo4j_driver)
   app.state.kg_builder = SimpleKnowledgeGraphBuilder(graph_store=app.state.graph_repository)
   ```

Both approaches are used in the system, which creates some confusion with duplicated functionality.

### Factory Pattern

Factory functions generate configured instances:

```python
def create_knowledge_graph_builder(graph_repo) -> KnowledgeGraphBuilder:
    return SimpleKnowledgeGraphBuilder(graph_store=graph_repo)
```

### Repository Pattern

The GraphRepository provides persistence abstraction:

```python
class MemgraphGraphRepository(GraphRepository):
    async def add_node(self, label: str, properties: dict) -> str:
        # Implementation details for Memgraph
    
    async def get_node_by_id(self, node_id: str) -> Optional[dict]:
        # Implementation details
```

### Singleton Pattern

The API uses singletons for expensive services:

```python
if "graph_repository" not in _singletons:
    _singletons["graph_repository"] = create_graph_repository()
```

## Component Relationships

### KnowledgeGraphBuilder Implementations

The system now standardizes on a single implementation of the KnowledgeGraphBuilder interface:

**SimpleKnowledgeGraphBuilder**:
- Basic implementation that adds entities and relationships to a GraphStore
- Only requires a GraphStore in constructor
- Implements a synchronous `build` method
- Used consistently throughout the application
- Retrieved via `get_knowledge_graph_builder()` in both main.py and dependencies.py

We've consolidated the previous dual implementation approach to improve consistency:
- Renamed `get_kg_builder` to `get_knowledge_graph_builder` in main.py
- Updated `KnowledgeGraphBuilderDep` to use `get_knowledge_graph_builder` instead of `get_kg_builder`
- Standardized all router implementations to use the same implementation

Note: The `PersistentKnowledgeGraphBuilder` still exists in the codebase but is not currently used in the dependency injection system.

### Graph Storage

1. **GraphStore Interface**:
   - Abstract contract for graph operations
   
2. **MemgraphRepository**:
   - Implements GraphRepository interface
   - Connects to Memgraph database
   - Provides CRUD operations for nodes/edges

### Vector Storage

1. **VectorStore Interface**:
   - Defines operations for semantic embeddings

2. **SimpleVectorStore**:
   - Implementation using SentenceTransformers
   - Provides cosine similarity search

## Error Handling Strategy

The system uses a combination of:

1. **Exception capturing** with detailed logging
2. **Fallback mechanisms** (e.g., using mock implementations when real ones fail)
3. **HTTP error responses** with appropriate status codes

## Architecture
- **Style:** Clean Architecture (Domain → Core → Infra → API/CLI).
- **Flow:** FastAPI/Typer → GraphRAGEngine → Core Services → GraphStore.
- **Database:** Dockerized Memgraph instance via `GraphStore` interface (`MemgraphGraphRepository` impl).
- **Vector Storage:** In-memory vector storage via `VectorStore` interface (`SimpleVectorStore` impl).

## Key Patterns
- Dependency Injection (FastAPI `Depends`).
- Repository Pattern (`GraphStore` abstraction).
- Async I/O (DB operations, API endpoints).
- Pydantic (Models, Settings validation).
- Docker Containerization (Memgraph, potentially app).

## Testing
- **Framework:** `pytest` (unit, integration).
- **Async:** `pytest-asyncio`, `unittest.mock.AsyncMock`.
- **DB:** `pymgclient` for direct Memgraph access in specific tests.
- **Environment:** Docker-based Memgraph for integration tests.
- **Execution:** `Makefile` (`test`, `test-memgraph`).

## Graph Storage (`MemgraphGraphRepository`)
- **Writes:** Idempotent (`MERGE`).
- **Operations:** Async methods with `tenacity` retries.
- **Interface:** CRUD for nodes/relationships, search, neighbors.
- **Driver:** `pymgclient` (native Bolt protocol).

## Vector Storage (`SimpleVectorStore`)
- **Storage:** In-memory storage of text chunks and their vector embeddings.
- **Operations:** Add/remove chunks, similarity search using cosine similarity.
- **Model:** Uses SentenceTransformer with "all-MiniLM-L6-v2" by default
- **Location:** Implemented in `infrastructure/vector_stores/` following Clean Architecture
- **Compatibility:** Legacy imports maintained via re-export with deprecation warnings
- **Note:** Previous duplicate implementation marked for future removal

## Search (Planned)
- Keyword/Vector: Memgraph MAGE library and `SimpleVectorStore`.
- Optimization: Native Memgraph query tuning (indexes, `PROFILE`).

## Debugging Pattern
- **Approach:** Observe -> Gather Info -> Hypothesize -> Verify -> Resolve -> Document.
- **Focus:** Information flow, state transitions, error types.
- **Tools:** Logging, `GraphDebugger`, visualization, direct DB queries.
- *(See `debugging-examples.md` for specific scenarios).* 