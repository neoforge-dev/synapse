# System Patterns

This document outlines the key system architecture decisions, design patterns, and component relationships within the Graph RAG project.

## Core Architecture

*   **Layered Architecture**: The system generally follows a layered approach:
    *   **API Layer (FastAPI)**: Handles HTTP requests, routing, request/response validation (Pydantic schemas), and dependency injection. Located in `graph_rag/api/`.
    *   **Service Layer**: Contains business logic coordinating interactions between different components (e.g., `IngestionService`, `SearchService`). Located in `graph_rag/services/`.
    *   **Core Logic Layer**: Defines core interfaces (`graph_rag/core/interfaces.py`), domain models (`graph_rag/domain/models.py`), and core algorithms/engines (e.g., `GraphRAGEngine`, `EntityExtractor`, `DocumentProcessor`). Located in `graph_rag/core/`.
    *   **Infrastructure Layer**: Provides concrete implementations for interfaces, interacting with external systems like databases and models (e.g., `MemgraphGraphRepository`, `SimpleVectorStore`, `SpacyEntityExtractor`). Located in `graph_rag/infrastructure/`.
    *   **LLM Abstraction**: Handles interaction with different Large Language Models through a common protocol (`graph_rag/llm/protocols.py`) and loader (`graph_rag/llm/loader.py`). Implementations in `graph_rag/llm/`.
*   **Dependency Injection**: FastAPI's dependency injection (`Depends`) is used extensively to provide instances of repositories, services, and configurations to API endpoints and potentially other components. Factory functions and singleton patterns are used in `graph_rag/api/dependencies.py` to manage instance creation.
*   **Interface-Based Design**: Core components interact through interfaces (Protocols) defined in `graph_rag.core.interfaces`, allowing for interchangeable implementations (e.g., different graph stores, vector stores, entity extractors).

## Key Design Patterns

*   **Repository Pattern**: The `GraphRepository` (implemented by `MemgraphGraphRepository`) abstracts the data access logic for the graph database.
*   **Strategy Pattern (Implicit)**: Different implementations for `VectorStore`, `EntityExtractor`, `LLMService`, etc., can be configured via settings, acting like strategies chosen at runtime/startup.
*   **Singleton Pattern**: Used in `graph_rag/api/dependencies.py` to manage single instances of expensive resources like database connections (via repository), LLM clients, and embedding models.
*   **Factory Functions**: Used in `graph_rag/api/dependencies.py` to centralize the creation logic for various components based on application settings.

## Data Modeling and Reconstruction

*   **Domain Models (Pydantic)**: Core data structures like `Document`, `Chunk`, `Entity`, `Relationship`, and `Node` are defined as Pydantic models in `graph_rag/domain/models.py`. These models enforce structure and types.
*   **Graph Schema**:
    *   Nodes generally have labels corresponding to their type (e.g., `:Document`, `:Chunk`, `:Entity`, `:Person`).
    *   Nodes must have a custom `id` property (string).
    *   Key data fields (like `content`, `text`, `name`) are stored as properties.
    *   Metadata or other arbitrary data is stored within the node's properties dictionary.
    *   Timestamps (`created_at`, `updated_at`) are stored as properties.
    *   Relationships (`CONTAINS`, `MENTIONS`, `RELATED_TO`, etc.) link nodes.
*   **Reconstructing Models from Database**:
    *   When retrieving data (e.g., in `MemgraphGraphRepository.get_node_by_id`), the raw node object is obtained from the database driver (`mgclient`).
    *   The primary data source is the `node_obj.properties` dictionary.
    *   **Pattern**:
        1.  Copy the `node_obj.properties` dictionary.
        2.  Extract core fields needed as explicit arguments for the Pydantic model constructor (e.g., custom `id`, `type` from labels, `name`, `text`, `content`). Use `.get()` on the *original* properties dictionary copy for these.
        3.  Extract and parse standard fields like `created_at`, `updated_at` from the original properties dictionary copy.
        4.  Create a separate dictionary (`all_properties` in the code) containing all original properties *except* the standard fields (`id`, `created_at`, `updated_at`) that have dedicated attributes on the Pydantic model.
        5.  Instantiate the Pydantic model (e.g., `Entity(...)`), passing the extracted core fields to their corresponding arguments and the `all_properties` dictionary to the `properties` argument of the model.
    *   This ensures that specific fields are directly accessible (e.g., `entity.name`) while *all* other custom/metadata properties remain available in the `entity.properties` dictionary, preventing data loss during reconstruction.
    *   The `_convert_neo4j_temporal_types` helper is used to handle potential database-specific time formats.

## Component Relationships

*   **API Routers** depend on **Service** or **Engine** interfaces/implementations (via `Depends`).
*   **Services** (e.g., `IngestionService`) depend on **Repositories** (`GraphRepository`, `VectorStore`) and potentially **Core Logic** components (`EntityExtractor`, `DocumentProcessor`).
*   **GraphRAGEngine** depends on `GraphRepository`, `VectorStore`, `EntityExtractor`, and potentially `LLMService`.
*   **Repositories** interact directly with external **Databases** (`Memgraph`, Vector DB).
*   **Entity Extractors** may depend on external **NLP Models** (spaCy).
*   **Embedding Services** depend on external **Embedding Models** (SentenceTransformers).

*(This is a high-level overview and may evolve as the project progresses.)*

## Error Handling
- Exception capturing with detailed logging.
- Fallback mechanisms (e.g., mock services).
- Standard HTTP error responses in API.

## Testing
- **Framework:** `pytest` (unit, integration).
- **Async:** `pytest-asyncio`, `unittest.mock.AsyncMock`.
- **DB:** `pymgclient` for direct Memgraph checks; Dockerized Memgraph for integration tests.
- **Execution:** `Makefile` commands (`test`, `test-memgraph`).
- **Mocking Strategy:** Heavy use of mocks (`AsyncMock`) in `conftest.py`'s `test_client` fixture for isolating API layer tests. This requires careful configuration of mock return values (e.g., ensuring correct data types like `QueryResult`, `Entity`) and potentially test-specific overrides (as seen in `test_query_pipeline`). Assertions in tests using this fixture may need to focus on structure/types rather than specific content from mocked dependencies.

## Debugging Protocol
The project follows a structured debugging protocol documented in `debugging-protocol.md`. Key aspects include:

1. **Analysis Phase**
   - Observe errors without judgment
   - Analyze test cases thoroughly
   - Question assumptions about implementation

2. **Systematic Investigation**
   - Run related tests
   - Verify dependencies
   - Trace execution paths

3. **Implementation Phase**
   - Minimal fixes
   - Test verification
   - Refactoring when needed

4. **Persistent Error Protocol**
   - Multiple reasoning approaches
   - Architecture review
   - Edge case consideration

5. **Documentation**
   - Update Memory Bank files
   - Document fixes
   - Record learned patterns

This protocol ensures consistent, thorough debugging practices across the project.

## Debugging Pattern
- **Approach:** Observe -> Gather Info -> Hypothesize -> Verify -> Resolve -> Document.
- **Tools:** Logging, `GraphDebugger`, visualization, direct DB queries.
- *(See `debugging-examples.md` for specific scenarios).* 