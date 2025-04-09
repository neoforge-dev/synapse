# System Patterns: GraphRAG MCP

## Architecture Style
- Clean Architecture: `domain`, `core`, `infrastructure`, `api`, `cli` layers.

## Key Components & Flow
- **API (FastAPI):** Exposes endpoints (ingest, query), uses `GraphRAGEngine`.
- **CLI (Typer):** Interacts with API via HTTP requests.
- **Core (`GraphRAGEngine`):** Orchestrates use cases (ingestion, querying).
- **Infrastructure (`GraphRepository`):** Handles persistence logic via Memgraph driver. Implements `GraphStore` interface.
- **Domain:** Defines core models (`Document`, `Chunk`, `Entity`) and interfaces (`GraphStore`, `EntityExtractor`).

## Design Patterns
- Dependency Injection: Via FastAPI `Depends`.
- Repository Pattern: Abstracting data access (`GraphRepository`).
- Async Operations: For all I/O (API, DB interactions).
- Configuration: Pydantic `BaseSettings` loading from `.env`.

## Search Strategy (Planned)
- Leverage Memgraph MAGE: Keyword Search, Vector Search modules. 