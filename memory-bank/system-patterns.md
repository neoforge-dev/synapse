# System Patterns: GraphRAG MCP

## Architecture
- Clean Architecture: domain, core, infra, api, cli
- API: FastAPI with GraphRAGEngine
- Core: Orchestrates use cases
- Infra: MemgraphStore, KGBuilder
- Domain: Core models/interfaces

## Patterns
- DI via FastAPI dependencies
- Async persistence with neo4j driver
- Pydantic Settings for config
- MAGE for search (Keyword, Vector)
- JSONL streaming support
- CLI via HTTP to FastAPI

## Stack
- Python 3.11+, FastAPI, Pydantic v2
- Repository, DI, Async patterns
- QA: Ruff, Black, MyPy, Pytest 