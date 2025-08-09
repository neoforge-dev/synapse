# Backlog (Curated)

## CRITICAL NOW
- Document identity and dedup (canonical `document_id`):
  - Derive ID priority: explicit metadata `id` → Notion page UUID (from filename/folder/property table) → Obsidian front matter `id` → normalized content hash → path-hash fallback with stat info
  - Implement `derive_document_id(path, content, metadata)` returning `(id, id_source, confidence)`
  - Idempotent re-ingestion: if `document_id` exists, update metadata/content; replace chunks and re-index vectors atomically
  - Tests: Notion nested tree stability, rename/move resilience, duplicate content across files, mixed Notion/Obsidian cases
  - Docs: identity scheme in README + ARCH; migration/rename guidance

## Must-have
- Notion export walker with stable IDs + tests (covered by identity work)
- Enable embeddings default ON after footprint validation; keep `--no-embeddings`
- `make up`/`make down` (done) and sample launchd plist (done)
- README Quickstart for Mac (done)
- Architecture/PRD docs (done)

## Next
- MCP server exposing ingest/search/query + docs
- Search CLI topic filter examples; topic-based query path
- FAISS persistence defaults and config polish
- Health probes: vector store stats, Memgraph ping; troubleshooting docs

## Later
- Autotagging improvements (lightweight keyphrase)
- UI explorer (optional)
