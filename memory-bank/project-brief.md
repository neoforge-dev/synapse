# Project Brief: GraphRAG MCP (Optimized)

## Goal
- Build a GraphRAG system using Memgraph & modern Python practices.

## Core Features (MVP)
- **Ingestion:** Store Docs/Chunks, Link Doc->Chunk.
- **Embeddings:** Generate & Store chunk embeddings (Sentence Transformers).
- **Retrieval:** Keyword & Vector search (MAGE) for chunks.
- **API:** FastAPI endpoints (Ingestion, Search, Health).
- **CLI:** Typer CLI for Ingestion, Search, Health.

## Key Requirements
- **Stack:** Python 3.11+, Memgraph+MAGE, FastAPI, Pydantic v2, Neo4j Driver, uv, Docker.
- **Architecture:** Clean Architecture (`domain`, `core`, `infrastructure`, `api`, `cli`).
- **QA:** Ruff, Black, MyPy, Pytest.

## Non-Goals (MVP)
- Advanced Graph algos, UI, Auth. 