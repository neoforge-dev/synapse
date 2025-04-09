# Technical Context

## Core Technologies
- **Language:** Python 3.13+
- **API:** FastAPI
- **Database:** Memgraph (+ MAGE)
- **Graph Client:** `pymgclient`, `neo4j` driver (via `gqalchmey` for schema? Check `infra`)
- **NLP/Embeddings:** `sentence-transformers`, `nltk` (check usage)
- **Data Validation:** Pydantic (v2+)
- **Testing:** `pytest`, `pytest-asyncio`, `pytest-cov`
- **Build/Tasks:** `uv`, Makefile

## Development Setup
- Python venv managed via `uv`.
- `Makefile` for common commands (`lint`, `test`, `run`, etc.).

## Key Technical Constraints
- Python 3.13+ features/compatibility.
- Memgraph capabilities and query language.
- Strict type safety (Pydantic models, FastAPI responses).
- Async operations for I/O (database, potentially LLMs).

## Configuration
- Managed via Pydantic Settings (env var support).

## Testing Strategy
- `pytest` framework with async support.
- Mocking for unit tests, integration tests use fixtures.

*(Core/Dev dependencies managed in `pyproject.toml`)* 