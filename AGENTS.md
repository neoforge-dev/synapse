# Agent Instructions for Synapse Codebase

## Build/Lint/Test Commands

```bash
# Setup
make install-dev                    # Install dependencies and NLP data
uv pip install -e .[dev]           # Alternative dependency installation

# Linting and formatting
make lint                          # Run ruff check + mypy
make format                        # Run ruff format
uv run ruff check .                # Check code style
uv run ruff format .               # Format code

# Testing
make test                          # Run unit tests
make test-integration             # Run integration tests
make test-all                     # Run all tests
make coverage-hot                # Check critical API coverage (85%+)

# Run a single test
uv run pytest tests/path/to/test_file.py::test_function_name -v

# Run tests with specific markers
uv run pytest -m "not integration" # Run only unit tests
uv run pytest -m integration       # Run only integration tests

# Run Memgraph integration tests (requires Memgraph running)
make run-memgraph                  # Start Memgraph service
make test-memgraph                # Run Memgraph tests
```

## Code Style Guidelines

### Imports
- Use absolute imports when possible
- Group imports in standard order: standard library, third-party, local
- Use ruff (isort rules) for import organization

### Formatting
- Line length: 100 characters (ruff configuration)
- Use ruff format (equivalent to black) for code formatting
- Follow PEP 8 style guidelines

### Types
- Use type hints extensively (mypy enforced)
- Prefer explicit types over implicit ones
- Use pydantic models for data validation

### Naming Conventions
- snake_case for variables and functions
- PascalCase for classes
- UPPER_CASE for constants
- Descriptive names over abbreviations

### Error Handling
- Use appropriate exception types
- Handle errors gracefully with tenacity retry decorators where needed
- Log errors with context for debugging

### General
- Use uv for all Python dependency management
- Follow existing code patterns in the repository
- Write tests for new functionality
- Keep functions focused and modular