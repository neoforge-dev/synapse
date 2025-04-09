# Technical Context: GraphRAG MCP

## Core Stack
- **Language:** Python 3.11+
- **API Framework:** FastAPI
- **CLI Framework:** Typer
- **Graph Database:** Memgraph (via `neo4j` driver)
- **Data Validation:** Pydantic v2
- **Embeddings (Planned):** `sentence-transformers`
- **Web Server:** Uvicorn

## Development Tools
- **Package Manager:** `uv`
- **Linting/Formatting:** Ruff, Black
- **Type Checking:** MyPy
- **Testing:** Pytest, pytest-asyncio

## Environment & Deployment
- **Containerization:** Docker & Docker Compose (`python:3.11-slim` base)
- **Configuration:** `.env` file
- **CI/CD:** GitHub Actions (basic lint/test pipeline)

## Setup Commands (Root Dir)
- **Install:** `uv pip install -e .`
- **Build Containers:** `docker-compose build`
- **Run Services:** `docker-compose up`
- **Run Tests:** `docker-compose exec app pytest tests/` 