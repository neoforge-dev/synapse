# Project Brief: GraphRAG MCP

## Core Goal
- Build a GraphRAG system using Memgraph & Python 3.11+.
- Implement Clean Architecture principles.

## MVP Scope
- **Ingestion:** Process documents, extract entities/relationships, store in Memgraph.
- **Retrieval:** Query graph for context relevant to user query.
- **Interfaces:** FastAPI backend, Typer CLI frontend.

## Key Technologies
- Memgraph + MAGE (for graph storage & search)
- Python 3.11+

## Out of Scope (MVP)
- Advanced graph algorithms (beyond basic search)
- UI frontend
- Authentication/Authorization 