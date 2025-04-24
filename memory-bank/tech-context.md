# Tech Context

This file documents the technologies, development setup, technical constraints, and dependencies for the Graph RAG project.

## Core Technologies

*   **Language:** Python 3.10+
*   **Framework:** FastAPI (for API), Typer (for CLI)
*   **Graph Database:** Memgraph (accessed via Bolt protocol)
*   **Database Driver:** `mgclient` (Memgraph native Python driver).
    *   **Data Handling:** Relies on node properties (`.properties`) and labels (`.labels`). See `system-patterns.md` for the reconstruction pattern used to create Pydantic models from `mgclient` objects.
    *   **Custom ID:** Nodes use a custom `id` property (string UUID) stored within `.properties`.
    *   **Temporal Types:** Handled via standard Python `datetime` (potentially with timezone info).
*   **Vector Storage:** Configurable via settings (`vector_store_type`), currently supports:
    *   `simple`: In-memory `SimpleVectorStore` using Sentence Transformers (via `EmbeddingService`).
    *   `mock`: Placeholder/testing.
*   **NLP Models:**
    *   **Embeddings:** Abstracted via `EmbeddingService`. Configurable via `embedding_provider` setting. Supports `sentencetransformers`, `mock`. Accessed via `SentenceTransformerEmbeddingService` or `MockEmbeddingService`.
    *   **Entity Extraction:** Abstracted via `EntityExtractor`. Configurable via settings (`entity_extractor_type`). Supports `spacy` (using configurable model like `en_core_web_sm`) and `mock`.
*   **LLM Integration:** Abstracted via `LLMService` protocol. Configurable via `LLM_TYPE` setting. Current support:
    *   `mock`: `MockLLMService` for testing/development.
    *   `openai`: Minimal `OpenAILLMService` exists in `dependencies.py` (likely requires full implementation).
*   **Caching:** Abstracted via `CacheService` protocol. Supports `memory` (`MemoryCache`).
*   **Dependency Injection:** FastAPI's `Depends` coupled with custom factory functions and a module-level singleton cache in `graph_rag/api/dependencies.py`.

## Development Setup

*   **Dependency Management:** **Poetry** (`pyproject.toml`, `poetry.lock`)
*   **Environment Management:** Recommended: `pyenv` for Python version management, `poetry` for virtual environments (`poetry install`).
*   **Linters/Formatters:** Ruff (configured in `pyproject.toml`) (`poetry run ruff check .`, `poetry run ruff format .`)
*   **Testing:** Pytest (with `pytest-asyncio`, `httpx`) (`poetry run pytest`)
*   **Configuration:** Pydantic Settings (`graph_rag/config/settings.py`), loaded from `.env` file (including `.env.test`) and environment variables.
*   **Task Runner:** `Makefile` provides convenience targets (`install-dev`, `test`, `format`, etc.).

## Technical Constraints

*   Requires access to a running Memgraph instance (Docker recommended).
*   Requires internet access to download NLP models (spaCy, Sentence Transformers) on first run/setup (`poetry run python -m spacy download en_core_web_sm`).
*   Async programming (`asyncio`) is used extensively for I/O operations (DB, API).

## Key Dependencies

*   `fastapi`, `uvicorn`, `typer`
*   `mgclient`
*   `pydantic`, `pydantic-settings`
*   `sentence-transformers`
*   `spacy` (and language models like `en_core_web_sm`)
*   `nltk` (specifically `punkt` tokenizer)
*   `ruff` (development dependency)
*   `pytest`, `pytest-asyncio`, `httpx`, `unittest.mock` (development dependency)
*   `tenacity` (for retries)
*   `python-dotenv`
*   `aiofiles` (for async file operations)

(See `pyproject.toml` for specific versions and full list). 