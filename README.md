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
# Option A: composable Unix-style pipeline (recommended)
synapse discover ~/Notes --include "**/*.md" \
  | synapse parse --meta source=vault --meta tags:='["notes","kb"]' \
  | synapse store --embeddings --json --emit-chunks

# Option B: legacy one-shot wrapper (backward compatible)
synapse ingest ~/Notes --embeddings  # parses YAML front matter / Notion property tables

# Control verbosity globally
synapse --quiet ingest ~/Notes        # warnings and above
synapse --verbose ingest ~/Notes      # debug logs

# Optional: add/override metadata (ergonomic flags)
synapse ingest ~/Notes --meta source=vault --meta owner=me \
  --meta-file meta.yaml --embeddings

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
- FAISS store now persists raw embeddings in `meta.json` to support precise deletions and index rebuilds.
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