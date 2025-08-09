# Graph RAG MCP Development Guide

## Build/Test Commands
- Install deps: `make install-dev`
- Run lint: `make lint`
- Run format: `make format`
- Run tests: `make test` (unit tests)
- Run single test: `python -m pytest tests/path/to/test_file.py::test_function -v`
- Run integration tests: `make test-integration`
- Run memgraph tests: `make test-memgraph`
- Run API: `make run-api`
- Run Memgraph: `make run-memgraph`

## Code Style Guidelines
- Line length: 88 chars (Ruff config)
- Quote style: double quotes
- Typing: Use type hints consistently, leverage Protocol for interfaces
- Imports: Group by stdlib, third-party, local (with blank line separators)
- Naming: snake_case for functions/variables, PascalCase for classes
- Async: Use async/await consistently in service layer and repositories
- Error handling: Use specific exceptions, log errors with context
- DocStrings: Include for all public methods, use Google style
- Testing: Write unit tests for core logic, mock external dependencies

## Architecture
- Clean architecture: API → Services → Core → Infrastructure → LLM
- Repository pattern for data access (GraphRepository, VectorStore)
- Strategy pattern for configurable components (EntityExtractor, LLMService)
- Dependency injection via FastAPI's Depends and factories in `api/dependencies.py`
- Core interfaces defined as Protocols in `core/interfaces.py`

## Debugging Protocol
- Run all tests in the same file to identify related failures
- Use `GraphDebugger` for query inspection
- Always document fixes in `memory-bank/progress.md`
- Follow TDD principles: make it work → make it right → make it fast