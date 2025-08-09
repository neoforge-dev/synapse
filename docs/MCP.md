# MCP Integration (Planned)

Expose tools for MCP-enabled IDE/chat clients:

- `ingest_files(paths[], metadata?)`
- `search(query, type, limit, stream?)`
- `query_answer(text, k?)`

Implementation plan:
- Thin Python MCP server that calls local FastAPI or services directly
- Unit tests with mocked services
- Usage: configure in IDE per MCP spec; provide example configs here
