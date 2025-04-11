# System Patterns

## Architecture
- **Style:** Clean Architecture (Domain → Core → Infra → API/CLI).
- **Flow:** FastAPI/Typer → GraphRAGEngine → Core Services → GraphStore.
- **Database:** Dockerized Memgraph instance via `GraphStore` interface (`MemgraphGraphRepository` impl).

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

## Search (Planned)
- Keyword/Vector: Memgraph MAGE library.
- Optimization: Native Memgraph query tuning (indexes, `PROFILE`).

## Debugging Pattern
- **Approach:** Observe -> Gather Info -> Hypothesize -> Verify -> Resolve -> Document.
- **Focus:** Information flow, state transitions, error types.
- **Tools:** Logging, `GraphDebugger`, visualization, direct DB queries.
- *(See `debugging-examples.md` for specific scenarios).* 