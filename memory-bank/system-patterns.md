# System Patterns: GraphRAG MCP (Optimized)

## Architecture
- Clean Architecture: `domain`, `core`, `infra`, `api`, `cli`.

## Key Components
- **API (`FastAPI`):** Exposes `GraphRAGEngine`.
- **CLI (`Typer`):** Command-line interface.
- **Core (`GraphRAGEngine`):** Orchestrates ingestion/retrieval.
- **Infrastructure (`GraphStore`/`MemgraphGraphRepository`):** Interacts with Memgraph (`neo4j` driver).
- **Domain (`Pydantic`):** Data models (`Node`, `Entity`, etc.), interfaces (`GraphStore`).

## Core Patterns
- Dependency Injection (`FastAPI Depends`).
- Repository Pattern (`GraphStore`).
- Async I/O.
- Settings Management (`Pydantic`).

## Testing Patterns
- Unit, Integration markers (`pytest`).
- Fixtures, Mocking (`unittest.mock`, `pytest-mock`).
- Config: `pytest.ini`, `Makefile` targets (`test`, `test-memgraph`).

## Graph Storage (Memgraph via `MemgraphGraphRepository`)
- **Writes:** `MERGE` (idempotency), timestamps, async, retries (`tenacity`).
- **Queries:** Node/Rel operations via `GraphStore` interface (`add_node`, `get_node_by_id`, `add_relationship`, `get_neighbors`).

## Search
- (Planned: Memgraph MAGE for Keyword/Vector).

## Debugging Protocols (Summary)
- **Systematic Approach:** Analyze -> Investigate -> Hypothesize -> Fix -> Verify.
- **First Principles:** Focus on information flow, state transitions, error types.
- **Tools:** Graph visualization, state logging, `GraphDebugger`.
- *See `debugging-examples.md` & `core/debug_tools.py` for details.* 