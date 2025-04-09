# Technical Context: GraphRAG MCP

## Runtime
- Python 3.11+, FastAPI, Pydantic
- Memgraph (with MAGE)
- neo4j driver (Async)
- sentence-transformers, Uvicorn

## Development
- uv package manager
- Ruff, Black, MyPy
- Pytest, pytest-asyncio
- Typer CLI

## Environment
- Docker & Docker Compose
- python:3.11-slim base
- .env config
- GitHub Actions CI

## Setup
- Build: docker-compose build
- Run: docker-compose up
- Test: docker-compose exec app pytest 