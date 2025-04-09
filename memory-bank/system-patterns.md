# System Patterns: GraphRAG MCP

## Architecture
- **Pattern:** Clean Architecture (`domain`, `core`, `infrastructure`, `api`, `cli`).
- **API Layer:** FastAPI (uses `GraphRAGEngine`, defines `schemas`).
- **Core Layer:** Orchestrates use cases (`GraphRAGEngine`). Uses interfaces.
- **Infrastructure Layer:** Implements interfaces (`MemgraphStore`, `PersistentKnowledgeGraphBuilder`). Uses `neo4j` driver.
- **Domain Layer:** Core Pydantic models/interfaces (`core/interfaces.py`). Independent.

## Key Patterns & Decisions
- **DI:** FastAPI manages dependencies (`api/dependencies.py`, `app.state`). Lifespan for setup/teardown.
- **Persistence:** `MemgraphStore` uses `neo4j` driver (async).
- **Config:** Pydantic Settings from `.env` (`config/settings.py`).
- **Async:** Core operations are async.
- **Search:** Implemented in `MemgraphStore` (Keyword, Vector via MAGE).
- **Streaming:** API search supports JSONL streaming.
- **CLI:** Typer app interacts with FastAPI backend via HTTP.

## Key Tech & Patterns
- **Stack:** Python 3.11+, uv, Docker, FastAPI, Pydantic v2.
- **Core Patterns:** Repository, Dependency Injection (FastAPI), Async.
- **QA:** Ruff, Black, MyPy (Strict), Pytest (Unit/Integration). 