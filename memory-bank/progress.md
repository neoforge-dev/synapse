# Progress: GraphRAG MCP

## Key Milestones Achieved
- Project Setup & Clean Architecture structure.
- Basic FastAPI app with health check.
- Memgraph connection via `GraphRepository`.
- Typer CLI (`synapse`) structure with `ingest` command prototype.
- Initial `spacy` integration for entity extraction.
- Core service refactoring.
- Basic integration tests for `GraphRepository`.
- CLI command renamed to `synapse`.
- Python 3.13 build issues resolved (switched to 3.11/3.12).

## Immediate Next Steps (Priority Order)
1. Implement core graph storage logic in `ingest` command (Nodes: Document, Chunk, Entity; Relationships: HAS_CHUNK, MENTIONED_IN).
2. Define and implement basic `/api/v1/query` endpoint (accept query text).
3. Implement basic query logic: Find entities in query -> Retrieve related Chunks/Documents from Memgraph.
4. Add integration tests for ingest storing data correctly.
5. Add integration tests for query retrieving basic context.

## Known Issues / Blockers
- None currently critical. 