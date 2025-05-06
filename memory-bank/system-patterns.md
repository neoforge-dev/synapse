# System Patterns

## Core Architecture
*   **Layers:** API (FastAPI) -> Services -> Core (Interfaces, Domain Models, Engine) -> Infrastructure (DB/Model Implementations) -> LLM Abstraction.
    *   Dirs: `api/`, `services/`, `core/`, `infrastructure/`, `llm/`
*   **DI:** FastAPI `Depends` + Factories/Singletons (`api/dependencies.py`).
*   **Interfaces:** Core components use Protocols (`core/interfaces.py`).

## Key Design Patterns
*   Repository (`GraphRepository`)
*   Strategy (Configurable components: VectorStore, EntityExtractor, LLMService)
*   Singleton (`api/dependencies.py` for DB connections, LLMs, embedding models)
*   Factory Functions (`api/dependencies.py` for component creation)

## Data Modeling & Graph Ops
*   **Domain Models:** Pydantic (`domain/models.py`: Document, Chunk, Entity, etc.).
*   **Graph Schema:**
    *   Labels: `:Document`, `:Chunk`, `:Entity`, etc.
    *   Required Props: Custom `id` (string UUID).
    *   Other data stored in node properties dict.
    *   Timestamps: `created_at`, `updated_at` properties.
    *   Relationships: `CONTAINS`, `MENTIONS`, etc.
*   **Reconstructing Pydantic Models from `mgclient` Driver:**
    1.  Get `node_obj` from driver.
    2.  Copy `node_obj.properties` dict.
    3.  Extract core fields (`id`, `type`, `name`, etc.) using `.get()` on the copy.
    4.  Extract/parse standard fields (`created_at`, etc.) from the copy.
    5.  Create `all_properties` dict excluding standard fields already handled.
    6.  Instantiate Pydantic model, passing core fields as args and `all_properties` to model's `properties` field.
    *   Ensures direct access to core fields + full metadata preservation in `.properties`.
    *   Uses `_convert_neo4j_temporal_types` helper.

## Component Relationships (High-Level)
*   API Routers -> Services/Engines
*   Services -> Repositories + Core Components
*   Engine -> Repositories + Core Components + LLMService
*   Repositories -> Databases
*   Extractors/Embedders -> External Models

## Error Handling
*   Detailed logging + Exception handlers.
*   Fallback mocks (e.g., `MockLLMService`).
*   Standard HTTP errors in API.

## Testing
*   **Framework:** `pytest` (`pytest-asyncio`, `httpx`, `unittest.mock`).
*   **DB:** Dockerized Memgraph (integration), `pymgclient` (direct checks).
*   **Execution:** `Makefile` (`test`).
*   **Mocking:** `conftest.py` `test_client` fixture mocks dependencies heavily for API tests.

## Debugging
*   Protocol: Structured approach (Observe -> Analyze -> Hypothesize -> Verify -> Fix -> Document). See `debugging-protocol.md`.
*   Tools: Logging, `GraphDebugger`, DB queries. 