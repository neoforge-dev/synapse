# Technical Stack

## Core
- Python 3.13+
- FastAPI, Typer CLI
- Memgraph DB + neo4j async driver
- NLP: spacy, nltk
- Pydantic v2+ models
- pytest + async support

## Development
- uv for venv/package management
- Makefile commands (install-dev, test, test-memgraph)
- NLP setup: `make download-nlp-data`

## Requirements
- Async I/O for DB operations
- Strict typing
- Environment config via Pydantic Settings

*(Dependencies: `pyproject.toml`)* 