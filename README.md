# Synapse: Graph-Enhanced RAG

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT) <!-- TODO: Confirm license -->

A system demonstrating Retrieval-Augmented Generation (RAG) enhanced with a Knowledge Graph, leveraging Memgraph. Hosted on [neoforge.dev](https://neoforge.dev).

## Features

*   **Document Ingestion:** Process text documents, extract entities and relationships.
*   **Knowledge Graph:** Build and store extracted information in a Memgraph knowledge graph.
*   **Vector Embeddings:** (Planned) Generate embeddings for text chunks.
*   **Hybrid Retrieval:** (Planned) Combine graph traversal and vector similarity for enhanced context retrieval.
*   **FastAPI Backend:** Exposes REST API endpoints for ingestion and querying.
*   **Typer CLI:** Provides command-line interface for interacting with the API.
*   **Dockerized Memgraph:** Easy setup for the graph database using Docker Compose.

## Prerequisites

*   **Python:** 3.10 or higher
*   **uv:** Fast Python package installer (`pip install uv`)
*   **Docker:** Latest version
*   **Docker Compose:** Version 2.x recommended (often included with Docker Desktop)
*   **NLTK Data:** The `punkt` tokenizer is needed for sentence splitting. It should download automatically on first run if missing, but you can manually download it:
    ```bash
    python -c "import nltk; nltk.download('punkt')"
    ```

## Setup Instructions

1.  **Clone the Repository:**
    ```bash
    # TODO: Update with correct repository URL on neoforge.dev
    git clone <repository-url>
    cd synapse # Assuming the repo folder name might change
    ```

2.  **Install Dependencies:**
    Uses `uv` for fast dependency management.
    ```bash
    make install-dev
    ```
    This installs the project in editable mode along with development dependencies (like `pytest`, `httpx`, `ruff`).

## Configuration

The application uses Pydantic's `BaseSettings` for configuration, loaded from:

1.  Environment Variables (prefixed with `SYNAPSE_` - TODO: Update prefix)
2.  A `.env` file in the project root.

Create a `.env` file in the project root for local development overrides. Example:

```dotenv
# .env file
# SYNAPSE_MEMGRAPH_HOST=localhost # Default
# SYNAPSE_MEMGRAPH_PORT=7687      # Default
# SYNAPSE_API_HOST=127.0.0.1      # Default
# SYNAPSE_API_PORT=8000         # Default
# SYNAPSE_API_LOG_LEVEL=DEBUG     # Example override
```

See `graph_rag/config.py` (TODO: Rename package?) for all available settings and their default values.

## Running the Application

1.  **Start Memgraph:**
    This starts Memgraph using Docker Compose in detached mode. Data is persisted in a Docker volume (`memgraph_data`).
    ```bash
    make run-memgraph
    ```
    *   To view Memgraph logs: `make logs-memgraph`
    *   To stop Memgraph: `make stop-memgraph`

2.  **Start the API Server:**
    This runs the FastAPI application using Uvicorn with live reloading.
    ```bash
    make run-api
    ```
    The API will be available at `http://<API_HOST>:<API_PORT>` (default: `http://127.0.0.1:8000`).
    *   View interactive API documentation (Swagger UI) at `http://127.0.0.1:8000/docs`.
    *   View alternative API documentation (ReDoc) at `http://127.0.0.1:8000/redoc`.

## Running Tests

*   **Run Unit Tests:** (Excludes tests requiring external services)
    ```bash
    make test
    ```
*   **Run Memgraph Integration Tests:** (Requires Memgraph to be running via `make run-memgraph`)
    ```bash
    make test-memgraph
    ```
    *(These tests are marked with `@pytest.mark.integration` and require the `RUN_MEMGRAPH_TESTS=true` environment variable, which the Makefile target sets automatically)*.
*   **Run All Tests:** (Requires Memgraph to be running)
    ```bash
    make test-all 
    ```

## Using the CLI

The CLI interacts with the running API server. (TODO: Rename CLI command?)

*   **Show Help:**
    ```bash
    graph-rag --help
    graph-rag ingest --help
    graph-rag query --help
    ```

*   **Ingest a Document (from text):**
    ```bash
    graph-rag ingest ingest --content "Alice lives in Wonderland." --metadata '{"source":"cli-example"}'
    ```

*   **Ingest a Document (from file):**
    ```bash
    graph-rag ingest ingest --file ./path/to/your/document.txt --metadata '{"source":"file-example"}' --doc-id "my-doc-01"
    ```

*   **Query the System:**
    ```bash
    graph-rag query ask "Who lives in Wonderland?"
    ```

*   **Query with Options:**
    ```bash
    graph-rag query ask "Tell me about Alice" --k 5 --show-chunks --show-graph
    ```

*   **Specify API URL:** (If not running on default `http://127.0.0.1:8000`)
    ```bash
    graph-rag ingest ingest --content "..." --url http://other-host:8080/api/v1/ingestion/documents
    graph-rag query ask "..." --url http://other-host:8080/api/v1/query/
    ```

## Project Structure

(TODO: Update package name `graph_rag` to `synapse`?)
```
├── graph_rag/
│   ├── api/          # FastAPI application (main.py, routers, models)
│   ├── cli/          # Typer CLI application (main.py, commands)
│   ├── core/         # Core logic (processor, extractor, builder, engine, stores interfaces)
│   ├── models.py     # Core data models (Document, Chunk, Entity, etc.)
│   ├── stores/       # Concrete store implementations (MemgraphStore, vector stores)
│   ├── config.py     # Pydantic settings configuration
│   └── __init__.py   # Package definition (__version__)
├── tests/
│   ├── api/          # API endpoint tests
│   ├── cli/          # CLI command tests
│   ├── core/         # Core component unit tests
│   └── stores/       # Store implementation integration tests
├── .env.example      # Example environment variables file
├── docker-compose.yml # Docker Compose configuration for services (Memgraph)
├── Makefile          # Development commands (install, test, lint, run, etc.)
├── pyproject.toml    # Project metadata and dependencies (for uv/pip)
└── README.md         # This file
```

## Contributing

Contributions are welcome! Please follow standard fork-and-pull-request workflow. Ensure tests pass (`make test-all`) and code is formatted (`make format`) before submitting a pull request.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details. <!-- TODO: Create LICENSE file --> 