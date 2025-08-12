# MCP Integration (Planned)

Expose tools for MCP-enabled IDE/chat clients (backed by local FastAPI/services):

- `ingest_files(paths[], metadata?, replace=true, embeddings=false)`
- `search(query, type, limit, stream?)`
- `query_answer(text, k?, include_graph=false)`

Implementation plan:
- Thin Python MCP server that calls local FastAPI or services directly
- Unit tests with mocked services
- Usage: configure in IDE per MCP spec; provide example configs here

Example configuration (pseudocode):

```json
{
  "tools": [
    {"name": "ingest_files", "args": {"replace": true, "embeddings": false}},
    {"name": "search", "args": {"type": "semantic", "limit": 5}},
    {"name": "query_answer", "args": {"k": 5, "include_graph": false}}
  ],
  "endpoint": "http://localhost:8000/api/v1"
}
```
