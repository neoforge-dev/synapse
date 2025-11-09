# Makefile for Synapse Project
# Prerequisites: Python 3.10+, uv, Docker, Docker Compose (v2 recommended)

# Define shell and flags
SHELL := /bin/bash
.ONESHELL:
.SHELLFLAGS := -eu -o pipefail -c
.DEFAULT_GOAL := help

# Define Python interpreter command
PYTHON := python3
UV := uv
# Explicitly define python executable within the virtual environment
VENV_PYTHON := $(VENV_DIR)/bin/python 

# Add commands for NLTK and spaCy data
# Use uv to install spaCy model wheel since pip may not be present in uv venv
DOWNLOAD_NLTK = $(VENV_PYTHON) -m nltk.downloader punkt
SPACY_MODEL_WHEEL := https://github.com/explosion/spacy-models/releases/download/en_core_web_sm-3.8.0/en_core_web_sm-3.8.0-py3-none-any.whl

# Project variables
VENV_DIR ?= .venv
# TODO: Decide if package name should be synapse or synapse_rag or graph_rag
PACKAGE_NAME = graph_rag # Keep as graph_rag for now until package is renamed
CLI_COMMAND = graph-rag # Keep as graph-rag for now until CLI entry point is renamed
TEST_MARKER_INTEGRATION = integration

# Use environment variables or defaults for API host/port in Makefile
# Avoids issues with importing/running Python code during make execution
API_HOST ?= 0.0.0.0
API_PORT ?= 8000
# API_HOST := $(shell $(PYTHON) -c "from $(PACKAGE_NAME).config import settings; print(settings.api_host)" 2>/dev/null || echo 0.0.0.0)
# API_PORT := $(shell $(PYTHON) -c "from $(PACKAGE_NAME).config import settings; print(settings.api_port)" 2>/dev/null || echo 8000)

# Phony targets (prevents conflicts with files of the same name)
.PHONY: help install-dev download-nlp-data lint format test test-memgraph test-all run-api run-memgraph stop-memgraph logs-memgraph clean test-integration up down check-links

help: ## Display this help screen
	@awk 'BEGIN {FS = ":.*##"; printf "\nUsage:\n  make \033[36m<target>\033[0m\n\nTargets:\n"} /^[a-zA-Z_0-9-]+:.*?##/ { printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2 }' $(MAKEFILE_LIST)

# Renamed target to make intent clear
install-deps: ## Install Python dependencies for development using uv
	$(UV) pip install -e .[dev]

install-mcp-deps: ## Install development dependencies including MCP extras
	$(UV) pip install -e '.[dev,mcp]'

download-nlp-data: install-deps ## Download necessary NLTK and spaCy data models (Requires dependencies installed)
	@echo "INFO: Downloading NLTK 'punkt'..."
	$(VENV_DIR)/bin/python -m nltk.downloader punkt
	@echo "INFO: Installing spaCy 'en_core_web_sm' model via wheel..."
	$(UV) pip install -q $(SPACY_MODEL_WHEEL)

install-dev: install-deps download-nlp-data ## Install dependencies and download NLP data for development
	@echo "INFO: Development environment setup complete."

lint: ## Run linters (ruff check)
	$(UV) run ruff check .
	$(UV) run mypy graph_rag/core graph_rag/services || true

format: ## Run formatters (ruff format)
	$(UV) run ruff format .

check-links: ## Validate all markdown links (requires lychee installed)
	@command -v lychee >/dev/null 2>&1 || { echo "ERROR: lychee is not installed. Install with: brew install lychee (macOS) or cargo install lychee"; exit 1; }
	@echo "INFO: Checking all markdown links..."
	lychee --verbose --cache --max-cache-age 1d --exclude-file .lycheeignore --timeout 30 --max-retries 3 '**/*.md'

test: ## Run unit tests (excluding integration tests)
	@echo "Running unit tests..."
	$(UV) run pytest -v -m "not integration" --tb=long -rA --maxfail=5

coverage-hot: ## Enforce >=85% coverage on critical API routers
	@echo "Reporting coverage for hot paths (gated at 85%)..."
	SKIP_SPACY_IMPORT=1 GRAPH_RAG_EMBEDDING_PROVIDER=mock GRAPH_RAG_LLM_TYPE=mock $(UV) run pytest -q -m "not integration" \
		--cov=graph_rag.api.routers.documents \
		--cov=graph_rag.api.routers.ingestion \
		--cov=graph_rag.api.routers.query \
		--cov-report=term-missing \
		--cov-fail-under=85 tests/api/test_query_ask_router.py

test-memgraph: ## Run Memgraph integration tests (requires Memgraph running)
	@echo "INFO: Ensure Memgraph container is running via 'make run-memgraph' before executing this target."
	@echo "INFO: Waiting for Memgraph to be ready..."
	@max_attempts=10; \
	attempt=0; \
	while ! nc -z localhost 7687 && [ $$attempt -lt $$max_attempts ]; do \
	  echo "Attempt $$((attempt+1))/$$max_attempts: Memgraph not yet available, waiting 2 seconds..."; \
	  sleep 2; \
	  attempt=$$((attempt+1)); \
	done; \
	if [ $$attempt -eq $$max_attempts ]; then \
	  echo "ERROR: Memgraph failed to start within $$((max_attempts * 2)) seconds."; \
	  exit 1; \
	fi
	@echo "INFO: Memgraph is ready. Running tests..."
	# Add --cov-fail-under=0 to prevent failure but still report coverage. Explicitly add cov flags.
	RUN_MEMGRAPH_TESTS=true $(UV) run pytest -v tests/infrastructure/graph_stores/ -m "$(TEST_MARKER_INTEGRATION)" --cov=$(PACKAGE_NAME) --cov-report=term-missing --cov-fail-under=0

test-integration:
	@echo "Running integration tests..."
	# Set the env var to allow memgraph_connection fixture to run
	RUNNING_INTEGRATION_TESTS=true $(UV) run pytest -m integration -vv

test-all: test test-memgraph ## Run all tests (unit + integration, requires Memgraph running)
	@echo "INFO: All tests passed (assuming Memgraph was running for integration tests)."

run-api: ## Run the FastAPI development server (uvicorn)
	@echo "INFO: Running API server on http://$(API_HOST):$(API_PORT)"
	# Use the create_app factory and pass host/port directly to uvicorn
	$(UV) run uvicorn graph_rag.api.main:create_app --factory --host $(API_HOST) --port $(API_PORT) --reload

run-memgraph: ## Start Memgraph service using Docker Compose (detached mode)
	docker-compose up -d memgraph

stop-memgraph: ## Stop and remove Memgraph service container
	docker-compose down

logs-memgraph: ## Tail logs for the Memgraph service
	docker-compose logs -f memgraph

up: ## Start Memgraph and API (detached Memgraph, foreground API)
	$(MAKE) run-memgraph
	$(MAKE) run-api

down: ## Stop Memgraph service and any foreground API process (Ctrl+C API)
	$(MAKE) stop-memgraph

clean: ## Remove cache files and build artifacts
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	rm -rf build dist *.egg-info .pytest_cache .ruff_cache $(VENV_DIR) 

.PHONY: build wheel install-local
build: ## Build source and wheel distributions
	$(UV) run python -m build

wheel: build ## Alias for build

install-local: ## Install the package locally via pipx
	pipx install --force dist/*.whl || true

# --- Remove Duplicated Targets Below ---
# .PHONY: install test lint format clean run-deps stop-deps

# # Development
# install:
# 	$(UV) pip install -e ".[dev]"

# # Testing
# test:
# 	$(UV) run pytest -v tests/ -m "not $(TEST_MARKER_INTEGRATION)"

# test-integration:
# 	$(UV) run pytest -v tests/infrastructure/ -m "$(TEST_MARKER_INTEGRATION)"

# # Code Quality
# lint:
# 	$(UV) run ruff check .
# 	$(UV) run ruff format --check .

# format:
# 	$(UV) run ruff format .

# # Dependencies
# run-deps:
# 	docker-compose up -d memgraph

# stop-deps:
# 	docker-compose down

# # Cleanup
# clean:
# 	find . -type d -name "__pycache__" -exec rm -rf {} +
# 	find . -type f -name "*.pyc" -delete
# 	find . -type f -name "*.pyo" -delete
# 	find . -type f -name "*.pyd" -delete
# 	find . -type f -name ".coverage" -delete
# 	find . -type d -name ".pytest_cache" -exec rm -rf {} +
# 	find . -type d -name ".ruff_cache" -exec rm -rf {} +
# 	find . -type d -name "*.egg-info" -exec rm -rf {} +
# 	find . -type d -name "dist" -exec rm -rf {} +
# 	find . -type d -name "build" -exec rm -rf {} +

# # Development Workflow
# dev: install run-deps
# 	$(UV) pip install -e ".[dev]"

# # CI/CD
# ci: lint test 