# Progress: GraphRAG MCP

## Done
- Core RAG pipeline: Ingest → Embed → Store → Retrieve
- FastAPI endpoints: Ingest, Search, Health
- Typer CLI with HTTP backend
- Core service refactoring

## Next
- Fix document_id return in ingestion
- Improve error handling
- Add admin features
- Enhance test coverage
- Make CLI API URL configurable
- Add DB integration tests

## Issues
- Ingestion returns placeholder document_id
- CI tests need DB integration 