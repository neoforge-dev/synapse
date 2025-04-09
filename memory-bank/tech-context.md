# Technical Context: GraphRAG MCP

## Core Runtime Stack
- **Python:** 3.11+
- **Graph DB:** Memgraph (`memgraph/memgraph-platform` image incl. MAGE)
- **Graph Driver:** `neo4j` (Async)
- **Web Framework:** FastAPI
- **Data Validation:** Pydantic (+ Pydantic-Settings)
- **Embeddings:** `sentence-transformers`
- **Async Runner:** Uvicorn

## Dev & QA Tooling
- **Package Manager:** uv
- **Lint/Format:** Ruff, Black
- **Type Check:** MyPy (Strict)
- **Testing:** Pytest, pytest-asyncio, httpx
- **CLI Framework:** Typer

## Environment & Deployment
- **Containerization:** Docker, Docker Compose (`docker-compose.yml`, `docker-compose.dev.yml`)
- **Base Image:** `python:3.11-slim`
- **Config:** `.env` via Pydantic Settings
- **CI:** GitHub Actions (`.github/workflows/ci.yml` - Lint, Test)

## Key Dependencies / Constraints
- Requires Docker & Docker Compose locally.
- Requires Memgraph+MAGE.
- Relies on Python 3.11+ async.
- Requires MAGE `node_similarity` module for vector search.
- Strict type checking enforced.

## Build & Run (Local - Docker Compose Recommended)
- **Build:** `docker-compose build`
- **Run:** `docker-compose up`
- **Test:** `docker-compose exec <app_service_name> pytest` 