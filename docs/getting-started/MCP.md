# MCP Integration

```json
{
  "tools": [
    {"name": "ingest_files", "args": {"replace": true, "embeddings": false}},
    {"name": "search", "args": {"type": "semantic", "limit": 5}},
    {"name": "query_answer", "args": {"k": 5, "include_graph": false}}
  ],
  "endpoint": "http://localhost:18888/api/v1"
}
```

## Available Tools

The server implementation lives in `graph_rag/mcp/server.py` and exposes the following tools:

- `ingest_files(paths, metadata?, replace?, embeddings?)`
- `search(query, limit?, search_type?, threshold?)`
- `query_answer(question, k?, include_graph?, stream?)`
- `list_documents(limit?, offset?)`
- `get_document(document_id)`
- `delete_document(document_id)`
- `system_status()`

Each tool delegates to the corresponding Synapse service (`IngestionService`, `SearchService`, `AdvancedFeaturesService`, etc.), so responses mirror the FastAPI endpoints.

## Running the MCP Server

```bash
# Install Synapse with MCP extras (if you haven't already)
uv pip install synapse-graph-rag[mcp]

# Start the server
synapse mcp start --host 127.0.0.1 --port 8765 --check-health
```

The CLI command relies on the same configuration as the API. If you override `SYNAPSE_API_BASE_URL` or other environment variables, the MCP server will pick them up.

## IDE Configuration

### VS Code (OpenAI MCP extension)

Add the following snippet to your `settings.json`:

```json
"openai.mcpServers": [
  {
    "name": "synapse",
    "url": "http://127.0.0.1:8765",
    "description": "Synapse Graph-RAG MCP server"
  }
]
```

### Claude Desktop

Place the config in `~/Library/Application Support/Claude/claude_desktop_config.json` (macOS) or the equivalent directory on Linux/Windows:

```json
{
  "mcpServers": {
    "synapse": {
      "url": "http://127.0.0.1:8765",
      "description": "Synapse Graph-RAG MCP server"
    }
  }
}
```

Restart the IDE after editing the configuration.

## Troubleshooting

- **Health check fails** – ensure `synapse up` (or your own FastAPI deployment) is running and reachable at `http://localhost:18888`.
- **Authentication issues** – if you enable API auth, provide matching credentials to the MCP server via environment variables.
- **Tool not found** – confirm you are on a recent Synapse version (`synapse --version`) and restart the MCP server after upgrades.
