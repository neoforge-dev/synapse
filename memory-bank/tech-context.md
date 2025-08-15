# Tech Context

## Core Stack
- **Language:** Python 3.10+
- **Frameworks:** FastAPI, Typer
- **Graph DB:** Memgraph (via `mgclient`)
- **Vector Store:** Default `simple` (in-memory `SimpleVectorStore`); Configurable via `vector_store_type`.
- **Embedding:** Default `sentencetransformers` (`all-MiniLM-L6-v2`); Configurable via `embedding_provider`.
- **Entity Extraction:** Default `spacy` (`en_core_web_sm`); Configurable via `entity_extractor_type`.
- **LLM:** Default `mock` (`MockLLMService`); `openai` available; Configurable via `LLM_TYPE`.
- **Cache:** Default `memory` (`MemoryCache`); Configurable via `cache_type`.
- **DI:** FastAPI `Depends`, factories in `graph_rag/api/dependencies.py`.

## Development Workflow
- **Dependency Management:** Astral `uv`
- **Environment:** `uv run` and `uv pip` (project-local `.venv`), optional `pyenv` for Python installs
- **Linting/Formatting:** Ruff
- **Testing:** Pytest (tools: `pytest-asyncio`, `httpx`, `unittest.mock`)
- **Configuration:** Pydantic Settings (`graph_rag/config/settings.py`), `.env` files
- **Task Runner:** `Makefile` (common tasks: `install-dev`, `test`, `format`)

## Key Operational Constraints
- Running Memgraph instance (Docker recommended).
- Internet access for initial NLP model downloads.
- `asyncio` for core operations.

## Critical Libraries (Non-Dev)
## Environment & Configuration Notes
- Primary env prefix: `SYNAPSE_` for app settings (e.g., `SYNAPSE_MEMGRAPH_HOST`).
- Supported aliases for tests/integration:
  - `GRAPH_DB_URI` → host/port/SSL detection for Memgraph (e.g., `bolt://host:7687`, `bolt+s://host:7687`).
  - `NEO4J_USERNAME` / `NEO4J_PASSWORD` → mapped to `memgraph_user` / `memgraph_password`.
- `SYNAPSE_*` values take precedence over aliases.
- FastAPI, Uvicorn, Typer, `mgclient`
- Pydantic, Pydantic-Settings
- Sentence-Transformers, SpaCy, NLTK (`punkt`)
- Tenacity, python-dotenv, aiofiles
- *(Refer to `pyproject.toml` for specific versions)*