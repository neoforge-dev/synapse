# System Patterns

## Architecture & Components
- **Clean Architecture:** domain → core → infrastructure → API/CLI
- **API:** FastAPI exposes GraphRAGEngine
- **CLI:** Typer interface
- **Core:** GraphRAGEngine orchestrates ingestion/retrieval
- **Infrastructure:** GraphStore interface → MemgraphGraphRepository

## Patterns
- Dependency Injection (FastAPI)
- Repository Pattern (GraphStore)
- Async I/O
- Pydantic models/settings

## Testing
- pytest (unit, integration markers)
- AsyncMock for async methods
- Makefile targets: test, test-memgraph

## Graph Storage
- Idempotent writes (MERGE)
- Async operations, retries (tenacity)
- Interface: add/get nodes/relationships, search, neighbors

## Search
- (Planned: Memgraph MAGE for Keyword/Vector).

## Debugging Protocols (Summary)
- **Systematic Approach:** Analyze -> Investigate -> Hypothesize -> Fix -> Verify.
- **First Principles:** Focus on information flow, state transitions, error types.
- **Tools:** Graph visualization, state logging, `GraphDebugger`.
- *See `debugging-examples.md` & `core/debug_tools.py` for details.* 