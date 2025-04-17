# Technical Context

## Core Stack
- **Language:** Python 3.12+
- **Frameworks:** FastAPI (API), Typer (CLI)
- **Database:** Memgraph (via `pymgclient`)
- **Data/Config:** Pydantic v2+ (Models, Settings via env vars)
- **NLP:** `spacy`, `nltk`
- **Testing:** `pytest` (`pytest-asyncio`, `unittest.mock`)

## Development Environment
- **Package/Venv:** `uv`
- **Orchestration:** `Makefile` (`install-dev`, `test`, `test-memgraph`, `download-nlp-data`)
- **DB Instance:** Docker (Memgraph on ports 7687, 7444, 3000)

## Key Technical Constraints/Requirements
- Async I/O for DB and API interactions.
- Strict type hinting enforced.

## Dependencies
- Managed via `pyproject.toml`. 