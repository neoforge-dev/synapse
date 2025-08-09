# Backlog (Prioritized for Compounding Impact)

- CRITICAL: FAISS correctness and persistence
  - Store embeddings alongside metadata to enable index rebuilds
  - Rebuild index on deletions; skip legacy rows without embeddings
  - Add infra tests for delete/rebuild/persistence round-trip

- Idempotent ingestion hardening
  - Pre-delete logs: report counts, doc_id, id_source
  - Best-effort vector deletion; do not fail ingestion on delete errors

- CLI observability and UX
  - Non-dry-run --json implemented (single, directory, stdin)
  - Next: --quiet/--verbose consistency; error codes and structured errors

- Stability & Developer Experience
  - Reduce spaCy/transformers cold-start via lazy import paths
  - Makefile targets: smoke, unit-fast, e2e (documented already)

- Docs & Examples
  - Architecture overview (docs/ARCHITECTURE.md)
  - MCP integration plan (docs/MCP.md)
  - More CLI scripting examples (jq, xargs)
