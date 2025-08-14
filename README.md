# Synapse MCP

**Ask intelligent questions about your personal knowledge base** - Graph-augmented retrieval for Notion/Obsidian with AI-powered answers.

## 🚀 Quick Start (2 minutes to AI answers!)

### Option 1: Full Power (Graph + Vector)
**Prereqs**: Docker Desktop, Python 3.10+

```bash
# Install
pip install synapse-graph-rag

# Start services (auto-detects Docker, starts containers)
synapse up

# Ingest your notes and ask questions!
synapse ingest ~/Notes --embeddings
synapse query ask "What are the main themes in my notes?"
```

### Option 2: Vector-Only Mode (No Docker required)
**Perfect for trying out the system without Docker/Memgraph**

```bash
# Install
pip install synapse-graph-rag

# Start in vector-only mode
SYNAPSE_DISABLE_GRAPH=true synapse ingest ~/Notes --embeddings
SYNAPSE_DISABLE_GRAPH=true synapse query ask "What did I write about AI?"
```

---

## 📚 Detailed Setup

### Prerequisites
- Python 3.10+ (3.12 recommended)
- Docker Desktop (optional - only for full graph features)
- `uv` package manager (recommended) or `pip`

```bash
# 1) Install dev deps
make install-dev

# Optional: type checks and lint
make lint

# 2) Start services (Memgraph + API)
make up  # leaves API in foreground; Ctrl+C to stop API

# Alternatively run in two terminals
# Packaging (pipx)
make build
pipx install dist/*.whl
make run-memgraph
make run-api

# 3) Ingest your notes (directory or single file)
# Option A: composable Unix-style pipeline (recommended)
synapse discover ~/Notes --include "**/*.md" \
  | synapse parse --meta source=vault --meta tags:='["notes","kb"]' \
  | synapse store --embeddings --json --emit-chunks

# Option B: one-shot wrapper (convenience)
synapse ingest ~/Notes --embeddings  # parses YAML front matter / Notion property tables

# Notion API sync (direct): requires SYNAPSE_NOTION_API_KEY in env
synapse notion sync --db <DATABASE_ID> --limit 50 --embeddings --replace
# Or export JSON of pages
synapse notion sync --query "project" --json | jq .

# Notion enhancements
# - Dry-run plan
synapse notion sync --db <DATABASE_ID> --dry-run | jq .
# - Attachment handling
synapse notion sync --db <DATABASE_ID> --attachments download --download-path ./assets

# Control verbosity globally
synapse --quiet ingest ~/Notes        # warnings and above
synapse --verbose ingest ~/Notes      # debug logs

# Observability
curl http://localhost:8000/ready        # readiness
curl http://localhost:8000/metrics      # Prometheus metrics (enabled by default)

# Ask (synthesis) with streaming
synapse query ask "What did I write about embeddings trade-offs?" --k 5 --stream
# Graph exploration
synapse graph neighbors --id <NODE_ID> --depth 2 --types HAS_TOPIC,MENTIONS
synapse graph export --seed <NODE_ID> --format graphml --out sub.graphml

# Admin ops
synapse admin vector-stats
synapse admin vector-rebuild
synapse admin integrity-check

# MCP server (optional)
synapse mcp run --host 127.0.0.1 --port 8765

# Point CLI search/admin to a custom API base
export SYNAPSE_API_BASE_URL="http://localhost:8000/api/v1"

# Optional: add/override metadata; control replacement
synapse ingest ~/Notes --meta source=vault --meta owner=me \
  --meta-file meta.yaml --embeddings --replace/--no-replace

# Preview what would be ingested (no changes)
synapse ingest ~/Notes --dry-run --json \
  --include "**/*.md" --exclude "archive/**"

# Use jq to filter before storing (topics contains "AI")
synapse discover ~/Notes --include "**/*.md" \
  | synapse parse \
  | jq 'select(.metadata.topics[]? == "AI")' \
  | synapse store --embeddings --json

# Pipe content from stdin (single doc)
# Non-dry-run with --json now emits a structured summary
echo "Hello from stdin" | synapse ingest ignored.md --stdin --json
```

Notes:
- Directory ingest skips hidden files, `.obsidian/` folders, and `*assets*` subfolders from Notion exports; accepts `.md`, `.markdown`, `.txt`.
- `--include`/`--exclude` let you filter files using glob patterns relative to the input path.
- `--embeddings` enables vector embeddings during ingestion (defaults off). When off, only graph+topics are stored; when on, semantic search is enabled.
- Re-ingestion mode defaults to replace; use `--no-replace` to append-only (not recommended).

### Composable CLI commands

- `synapse discover DIRECTORY [--include PATTERN ...] [--exclude PATTERN ...] [--json] [--stdin]`
  - Outputs absolute file paths, one per line; with `--json`, emits `{ "path": "..." }` per line
  - Respects ignore rules for hidden files, `.obsidian/`, and Notion `assets` folders
  - With `--stdin`, accepts a JSON array of directories from stdin and discovers across all roots

- `synapse parse [--meta key=value ... | --meta key:=jsonValue ...] [--meta-file path]`
  - Reads file paths from stdin
  - For each file, parses YAML front matter and Notion property tables, merges metadata, and emits one JSON line: `{ path, content, metadata }`
  - `--meta key:=jsonValue` parses the value as JSON (e.g. `--meta tags:='["a","b"]'`, `--meta count:=123`, `--meta flag:=true`)

- `synapse store [--embeddings/--no-embeddings] [--replace/--no-replace] [--json] [--emit-chunks]`
  - Reads JSON lines from stdin (as produced by `parse`)
  - Derives `document_id`, chunks content, optionally generates embeddings, stores to graph/vector stores
  - With `--json`, emits `{ document_id, num_chunks }` per line
  - With `--emit-chunks` and `--json`, also emits one line per chunk: `{ chunk_id, document_id }`
  - Maintenance: `synapse store stats` (show vector stats), `synapse store rebuild` (FAISS), `synapse store clear --yes`

- `synapse ingest`
  - Backward-compatible wrapper that performs discover → parse → store in one command. Supports `--dry-run`, `--json`, and `--json-summary` for directory mode.

- `synapse suggest "<topic>" [--k 5] [--graph] [--style "concise, analytical"] [--count 5] [--json]`
  - Uses the new `/api/v1/query/ask` endpoint to generate ideas and content suggestions grounded in your corpus.

- `synapse config show|init`
  - `show` prints effective settings (use `--json` for JSON)
  - `init` writes a `.env` template (use `--path` and `--force` as needed)

JSON output (non-dry-run):
- Single file: `{ "document_id": "...", "num_chunks": N, "id_source": "...", "path": "...", "embeddings": bool, "replace_existing": bool, "topics": [..] }`
- Directory: `[{...}, {...}]` per file summary
- STDIN: same object as single file, with `path` pointing to a temp file

Logging controls:
- `--quiet` reduces logs to warnings/errors.
- `--verbose` or `--debug` enables debug logs.

Identity and idempotence:
- The system will derive a stable `document_id` per file/page (priority: explicit metadata `id` → Notion page UUID → Obsidian `id` → normalized content hash → path-hash fallback). The derivation `id_source` is recorded in `Document.metadata`.
- Re-ingesting the same `document_id` with `--replace` deletes old chunks/vectors atomically before adding new ones.

### Integration recipes (jq/xargs)

- Multi-root discovery via stdin JSON array, filter, parse, and store with embeddings:

  ```bash
  printf '["%s","%s"]\n' "$HOME/Notes" "$HOME/Work" \
    | synapse discover --stdin --json \
    | jq -r 'select(.path | contains("/Archive/") | not) | .path' \
    | synapse parse --meta source=vault \
    | synapse store --embeddings --json
  ```

- Augment metadata using jq between parse and store (derive `area` from path):

  ```bash
  synapse discover "$HOME/Notes" --include "**/*.md" \
    | synapse parse \
    | jq '. as $d | .metadata = ($d.metadata + {area: ($d.path | split("/") | .[-2])})' \
    | synapse store --json
  ```

- Filter by topics before storing (e.g., only keep docs tagged "AI"):

  ```bash
  synapse discover "$HOME/Notes" --include "**/*.md" \
    | synapse parse \
    | jq 'select(.metadata.topics[]? == "AI")' \
    | synapse store --embeddings --json
  ```

- Capture per-chunk outputs for downstream processing queues:

  ```bash
  synapse discover "$HOME/Notes" --include "**/*.md" \
    | synapse parse \
    | synapse store --embeddings --json --emit-chunks \
    | jq 'select(.chunk_id) | {chunk_id, document_id}'
  ```

- Parallel pipeline with xargs (split input into batches; adjust -P for concurrency):

  ```bash
  synapse discover "$HOME/Notes" --include "**/*.md" \
    | xargs -P 4 -n 200 sh -c '
        printf "%s\n" "$@" \
        | synapse parse --meta batch_id=$RANDOM \
        | synapse store --embeddings --json
      ' sh
  ```

- Multi-root + include/exclude patterns, dedupe paths, then ingest:

  ```bash
  jq -nc --arg a "$HOME/Notes" --arg b "$HOME/Projects" '[ $a, $b ]' \
    | synapse discover --stdin --include "**/*.md" --exclude "**/drafts/**" \
    | sort -u \
    | synapse parse \
    | synapse store --json
  ```

### Vector store considerations

- The default vector store is an in-process simple store optimized for tests and quick starts. For production, set `SYNAPSE_VECTOR_STORE_TYPE=faiss`.
- FAISS store persists raw embeddings in `meta.json` (version 2) to support precise deletions and index rebuilds.
- Use maintenance commands to manage the FAISS index:
  - `synapse store stats` shows vector count and index paths
  - `synapse store rebuild` reconstructs the index from persisted embeddings
  - `synapse store clear --yes` removes index and metadata

### Configuration

Set environment variables or `.env` with `SYNAPSE_` prefix. Key options:

- `SYNAPSE_VECTOR_STORE_TYPE`: `simple` (default) or `faiss`
- `SYNAPSE_VECTOR_STORE_PATH`: path for FAISS persistence (default `~/.graph_rag/faiss_store`)
- `SYNAPSE_EMBEDDING_PROVIDER`: `sentence-transformers` (default) or `mock`
- `SYNAPSE_MEMGRAPH_HOST`/`SYNAPSE_MEMGRAPH_PORT`: Memgraph connection (defaults to `127.0.0.1:7687`)
- `SYNAPSE_API_HOST`/`SYNAPSE_API_PORT`: API network settings
- `SYNAPSE_API_LOG_JSON=true`: emit structured JSON logs
- `SYNAPSE_ENABLE_METRICS=true|false`: toggle /metrics endpoint

### Status

- Robust CLI ingestion for Markdown/Notion, topic extraction, and topic graph projection are implemented.
- API is available via FastAPI; MCP integration is planned.
- See `docs/PLAN.md` for milestones and priorities.

### Next Docs

- `docs/HANDBOOK.md`: single source of truth (architecture, workflows, ops)
- `docs/ARCHITECTURE.md`: system overview and layering
- `docs/PRD.md`: goals, scope, personas
- `docs/BACKLOG.md`: curated prioritized backlog
- `docs/MCP.md`: Model Context Protocol usage and setup

License: MIT