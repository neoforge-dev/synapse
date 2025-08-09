# Synapse MCP

Graph-augmented retrieval for your personal knowledge base (Notion/Obsidian) with a modern CLI, FastAPI backend, and upcoming MCP integration.

### Quickstart (macOS)

Prereqs: Docker Desktop, Python 3.10+, `uv` package manager.

```bash
# 1) Install dev deps
make install-dev

# 2) Start services (Memgraph + API)
make up  # leaves API in foreground; Ctrl+C to stop API

# Alternatively run in two terminals
make run-memgraph
make run-api

# 3) Ingest your notes (directory or single file)
synapse ingest ~/Notes --embeddings  # parses YAML front matter / Notion property tables

# Optional: add/override metadata
synapse ingest ~/Notes --embeddings --metadata '{"topics":["ml","graph"],"aliases":["RAG"]}'
```

Notes:
- Directory ingest skips hidden files and `.obsidian/` folders; accepts `.md`, `.markdown`, `.txt`.
- `--embeddings` enables vector embeddings during ingestion (defaults off). When off, only graph+topics are stored; when on, semantic search is enabled.

Identity and idempotence:
- The system will derive a stable `document_id` per file/page (priority: explicit metadata `id` → Notion page UUID → Obsidian `id` → normalized content hash → path-hash fallback).
- Re-ingesting the same content updates the existing document/chunks instead of duplicating.

### Configuration

Set environment variables or `.env` with `SYNAPSE_` prefix. Key options:

- `SYNAPSE_VECTOR_STORE_TYPE`: `simple` (default) or `faiss`
- `SYNAPSE_VECTOR_STORE_PATH`: path for FAISS persistence (default `~/.graph_rag/faiss_store`)
- `SYNAPSE_EMBEDDING_PROVIDER`: `sentence-transformers` (default) or `mock`
- `SYNAPSE_MEMGRAPH_HOST`/`SYNAPSE_MEMGRAPH_PORT`: Memgraph connection (defaults to `127.0.0.1:7687`)
- `SYNAPSE_API_HOST`/`SYNAPSE_API_PORT`: API network settings

### Status

- Robust CLI ingestion for Markdown/Notion, topic extraction, and topic graph projection are implemented.
- API is available via FastAPI; MCP integration is planned.
- See `docs/PLAN.md` for milestones and priorities.

### Next Docs

- `docs/ARCHITECTURE.md`: system overview and layering
- `docs/PRD.md`: goals, scope, personas
- `docs/BACKLOG.md`: curated prioritized backlog
- `docs/MCP.md`: Model Context Protocol usage and setup

License: MIT