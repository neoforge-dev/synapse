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

# Project variables
VENV_DIR ?= .venv
# TODO: Decide if package name should be synapse or synapse_rag or graph_rag
PACKAGE_NAME = graph_rag # Keep as graph_rag for now until package is renamed
CLI_COMMAND = graph-rag # Keep as graph-rag for now until CLI entry point is renamed
TEST_MARKER_INTEGRATION = integration
# Read config values - use the current PACKAGE_NAME
API_HOST := $(shell $(PYTHON) -c "from $(PACKAGE_NAME).config import settings; print(settings.api_host)")
API_PORT := $(shell $(PYTHON) -c "from $(PACKAGE_NAME).config import settings; print(settings.api_port)")

# Phony targets (prevents conflicts with files of the same name)
.PHONY: help install-dev lint format test test-memgraph test-all run-api run-memgraph stop-memgraph logs-memgraph clean

help: ## Display this help screen
	@awk 'BEGIN {FS = ":.*##"; printf "\nUsage:\n  make \033[36m<target>\033[0m\n\nTargets:\n"} /^[a-zA-Z_0-9-]+:.*?##/ { printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2 }' $(MAKEFILE_LIST)

install-dev: ## Install dependencies for development using uv
	$(UV) pip install --system -e .[dev]

lint: ## Run linters (ruff check)
	$(UV) run ruff check .

format: ## Run formatters (ruff format)
	$(UV) run ruff format .

test: ## Run unit tests (excluding integration tests)
	$(UV) run pytest -v tests/ -m "not $(TEST_MARKER_INTEGRATION)"

test-memgraph: ## Run Memgraph integration tests (requires Memgraph running)
	@echo "INFO: Ensure Memgraph container is running via 'make run-memgraph' before executing this target."
	RUN_MEMGRAPH_TESTS=true $(UV) run pytest -v tests/stores/ -m "$(TEST_MARKER_INTEGRATION)"

test-all: test test-memgraph ## Run all tests (unit + integration, requires Memgraph running)
	@echo "INFO: All tests passed (assuming Memgraph was running for integration tests)."

run-api: ## Run the FastAPI development server (uvicorn)
	$(UV) run uvicorn $(PACKAGE_NAME).api.main:app --reload --host $(API_HOST) --port $(API_PORT)

run-memgraph: ## Start Memgraph service using Docker Compose (detached mode)
	docker-compose up -d memgraph

stop-memgraph: ## Stop and remove Memgraph service container
	docker-compose down

logs-memgraph: ## Tail logs for the Memgraph service
	docker-compose logs -f memgraph

clean: ## Remove cache files and build artifacts
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	rm -rf build dist *.egg-info .pytest_cache .ruff_cache $(VENV_DIR) 