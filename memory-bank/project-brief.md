# Project Brief: GraphRAG MCP

## Core
- GraphRAG system using Memgraph & Python 3.11+
- Clean Architecture: domain, core, infra, api, cli

## MVP
- **Flow:** Ingest → Embed → Store → Retrieve
- **Search:** Vector & Keyword via MAGE
- **Stack:** FastAPI, Typer CLI, Memgraph+MAGE, Pydantic v2

## QA
- Ruff, Black, MyPy, Pytest

## Out of Scope
- Advanced Graph algos, UI, Auth 