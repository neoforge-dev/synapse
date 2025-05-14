# System Patterns

## Core Architecture
- **Layered Structure:** API (FastAPI) -> Services -> Core (Interfaces, Domain Models, Engine) -> Infrastructure (DB/Model Impls) -> LLM Abstraction.
    - Corresponding Dirs: `api/`, `services/`, `core/`, `infrastructure/`, `llm/`.
- **Dependency Injection (DI):** FastAPI `Depends` with factories/singletons via `api/dependencies.py`.
- **Interfaces:** Defined as Protocols in `core/interfaces.py`.

## Key Design Patterns Used
- Repository (e.g., `GraphRepository`).
- Strategy (for configurable components like VectorStore, EntityExtractor, LLMService).
- Singleton & Factory (primarily in `api/dependencies.py` for shared resources).

## Data Modeling & Graph Operations
- **Domain Models:** Pydantic models in `domain/models.py` (e.g., Document, Chunk, Entity).
- **Graph Schema Highlights:**
    - Labels: `:Document`, `:Chunk`, `:Entity`.
    - Required Properties: `id` (string UUID), `created_at`, `updated_at`.
    - Relationships: `CONTAINS`, `MENTIONS`.
- **Pydantic Model Reconstruction (from `mgclient`):
    - Driver's `node.properties` are mapped to Pydantic model fields.
    - Core fields are direct attributes; other properties stored in a `properties` dict field.
    - Utilizes `_convert_neo4j_temporal_types` helper. (Refer to codebase for exact logic).

## High-Level Component Interactions
- API Routers delegate to Services/Engines.
- Services use Repositories & Core Components.
- Engine uses Repositories, Core Components & LLMService.
- Repositories interact with Databases.
- Extractors/Embedders interact with external models.

## Error Handling Approach
- Detailed logging and custom Exception handlers.
- Fallback mock implementations (e.g., `MockLLMService`).
- Standard HTTP error responses from API.

## Testing Strategy
- **Framework:** `pytest` (with `pytest-asyncio`, `httpx`, `unittest.mock`).
- **Database Testing:** Dockerized Memgraph for integration tests; `pymgclient` for direct checks.
- **Execution:** Via `Makefile` (e.g., `make test`).
- **Mocking:** Extensive use of mocks in `conftest.py` and per-test setup, especially for API tests.

## Debugging
## New Decisions & Patterns (Config/DI)
- Configuration aliasing: `Settings` now maps `GRAPH_DB_URI`, `NEO4J_USERNAME`, `NEO4J_PASSWORD` to Memgraph settings when corresponding `SYNAPSE_` variables are not set. `SYNAPSE_*` takes precedence.
- Single settings source: Use `graph_rag.config.get_settings` throughout; avoid duplicate settings getters to prevent ambiguity.
- Graph store selection: Prefer mgclient-based `MemgraphGraphRepository` in DI for MVP; avoid mixing with the Neo4j async repository in default paths.
- FastAPI DI: Prefer app.state initialized via lifespan for core singletons (repo, vector store, extractors, engine), with lightweight getters accessing state.
- Follows structured protocol (see `debugging-protocol.md`).
- Key Tools: Logging, `GraphDebugger` utility, direct database queries. 