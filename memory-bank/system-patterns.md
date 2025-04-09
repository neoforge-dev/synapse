# System Patterns: GraphRAG MCP

## Architecture
- Clean Architecture: `domain`, `core`, `infra`, `api`, `cli` layers.

## Key Components & Responsibilities
- **API (`FastAPI`):** Exposes `GraphRAGEngine` functionality.
- **CLI (`Typer`):** Provides command-line interface (uses HTTP client).
- **Core (`GraphRAGEngine`):** Orchestrates ingestion and retrieval.
- **Infrastructure (`GraphRepository`):** Interacts with Memgraph (via `neo4j` driver).
- **Domain (`Pydantic`):** Defines data models and core interfaces.

## Core Patterns
- Dependency Injection (`FastAPI Depends`).
- Repository Pattern for data access.
- Async I/O for non-blocking operations.
- Settings Management (`Pydantic`).

## Testing Patterns
- **Types:** Unit, Integration, E2E (marked via `pytest` markers).
- **Data:** Centralized fixtures, generators.
- **Utilities:** Common helpers, async support.
- **Config:** `pytest.ini`, coverage goals.

## Graph Storage (Memgraph)
- **Writes:** `MERGE` (idempotency), timestamps, transactions, retries.
- **Queries:** Entity/relationship traversal, property search, neighbor exploration.
- **Performance:** Connection pooling, batch ops (planned), error handling.

## Search
- Memgraph MAGE (Keyword/Vector planned).

## Debugging Protocols (Summary)
- **Systematic Approach:** Analyze -> Investigate -> Hypothesize -> Fix -> Verify.
- **First Principles:** Focus on information flow, state transitions, error types.
- **Tools:** Graph visualization, state logging, `GraphDebugger`.
- *See `debugging-examples.md` & `core/debug_tools.py` for details.* 