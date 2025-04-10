# Technical Context (Optimized)

## Core Tech
- **Language:** Python 3.13+
- **API:** FastAPI
- **Database:** Memgraph (+ MAGE planned)
- **Graph Client:** `neo4j` async driver
- **NLP/Embeddings:** `spacy`, `nltk` (needs setup/download)
- **Data Models:** Pydantic v2+
- **Testing:** `pytest`, `pytest-asyncio`, `pytest-cov`, `unittest.mock`
- **Build/Tasks:** `uv`, Makefile

## Development
- Venv via `uv`.
- `Makefile` for commands (`install-dev`, `lint`, `format`, `test`, `test-memgraph`, `run-api`, etc).
- NLP data download: `make download-nlp-data` (requires `nltk_data/tokenizers/punkt_tab`, `spacy download en_core_web_sm`).

## Constraints
- Python 3.13+.
- Memgraph Cypher.
- Async I/O (DB).
- Strict typing.

## Config
- Pydantic Settings (`.env` file support).

*(Dependencies: `pyproject.toml`)* 