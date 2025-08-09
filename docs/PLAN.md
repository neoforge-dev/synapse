# Graph RAG MCP: Identity, Idempotence, Vector Store, and CLI UX Plan

This plan captures the remaining details and concrete tasks to fully deliver stable document identity, idempotent ingestion, robust vector store operations, and good observability.

## Objectives
- Stable, canonical `document_id` across imports and renames
- Idempotent re-ingestion that atomically replaces chunks and vectors
- Correct FAISS deletion (no ghost vectors; index remains consistent)
- Notion export nuances handled reliably (IDs, property tables)
- End-to-end wiring in CLI/API with observability of identity provenance
- Comprehensive tests (unit, service, infrastructure, integration)

- CLI is easy to install and immediately useful without deep setup
- Ergonomic CLI UX for ingestion, filtering, metadata, and scripting outputs

## Current State
- Implemented `graph_rag/utils/identity.py` with multi-priority ID derivation.
- Ingestion service supports `replace_existing=True` to delete existing chunks and vectors before re-ingest.
- CLI derives canonical `document_id` and attaches `id_source` to metadata; parses YAML front matter and Notion property tables.
- Added tests for identity derivation and idempotent re-ingestion.
- FAISS store supports persistence and search; deletion currently drops metadata rows but cannot truly rebuild index (no stored embeddings).

## Gaps and Risks
- FAISS deletion correctness: without stored embeddings, "delete" cannot rebuild the index; vectors can go stale or require full reset.
- Observability: ensure `id_source` and `topics` are consistently persisted and queryable; make logs actionable.
- Notion export walker: ignore attachment subfolders where appropriate; robust parsing of property tables; edge cases in names.
- Test coverage: add infrastructure tests for FAISS deletions; service-level tests covering replace_existing + FAISS behavior.

- CLI ergonomics: JSON metadata string is unfriendly; no dry-run; limited output formats; no include/exclude glob filters; no stdin ingestion.
- Installation friction: dependency on Memgraph for first run is heavy (future improvement via easy startup tooling).

## Detailed Plan

### 1) FAISS Vector Store Robustness (CRITICAL)
- Persist embeddings alongside metadata so we can rebuild indexes upon deletions.
- Update `FaissVectorStore.add_chunks` to store `embedding` per row (raw, not normalized).
- Update `delete_chunks` to filter rows, then rebuild a fresh index from stored embeddings of remaining rows (normalize on add to index).
- Backward compatibility: if rows loaded without `embedding`, log a warning and skip those rows during rebuild; in that case, encourage full re-ingestion.
- Add tests:
  - Add chunk A and B → search returns both as appropriate
  - Delete A → ensure A is absent in results and store remains consistent
  - Persistence round-trip: delete, save, reload, and verify state is preserved

### 2) Idempotent Re-ingestion Hardening
- Current service deletes graph chunks and calls `vector_store.delete_chunks` before re-adding.
- Add small guardrails/logging:
  - Log the number of chunks found and deleted by doc id
  - Handle vector store delete exceptions without failing ingestion
- Extend tests if needed to validate vector store delete is invoked for old chunk IDs.

### 3) Notion Export Walker & Identity Nuances
- Ensure walker ignores Notion asset subfolders (e.g., exported attachments like `.../Page Name .../assets`); currently non-md files are skipped, which is sufficient but document in README/ARCH.
- Identity derivation already considers UUIDs in parent directories and filenames (dashed/compact). Add doc examples.
- Keep table parsing robust (already in CLI).

### 4) Observability & Metadata
- Persist `id_source` into `Document.metadata` and keep through pipeline.
- Ensure topics normalization already implemented (done). Consider a flag to disable topic projection when not desired (optional).
- Logging: start/end and key milestones in ingestion; include `document_id` and `id_source`.

### 5) CLI & Service Integration
- CLI already derives canonical `document_id` and passes `id_source`. Re-ingestion behavior relies on service flag; defaults to replace existing.
- Add high-value CLI UX features focused on first-run success and scripting:
  - `--meta key=value` (repeatable) and `--meta-file` (YAML/JSON) for ergonomic metadata input
  - `--dry-run` to preview actions (derived `document_id`, `id_source`, topics, file list)
  - Output controls: `--json`, `--quiet`, `--verbose/--debug`
  - Directory filters: `--include`/`--exclude` glob patterns
  - Stdin support (`--stdin`) for piping content

### 6) Testing
- Unit tests: identity derivation (done), FAISS delete/rebuild (to add).
- Service tests: re-ingestion deletes vectors (present), can expand assertions after FAISS fix.
- CLI tests: metadata flags, meta-file, dry-run JSON summary, include/exclude filters, stdin flag path.

### 7) Documentation
- Keep `ARCHITECTURE.md` and `README.md` consistent with identity strategy and idempotence.
- Add notes on FAISS persistence and deletion trade-offs.

## Acceptance Criteria
- Re-ingesting a doc with same `document_id` replaces chunks in graph and vectors; no duplicate chunks or stale vectors remain.
- FAISS `delete_chunks` removes vectors accurately and persists state; after reload, searches reflect deletions.
- Identity derivation passes tests for metadata, Notion UUIDs, content and path hash fallbacks.
- CLI processes Notion markdown exports, derives IDs consistently, and attaches `id_source`.
- All tests pass locally (unit + infra). Integration tests remain green.

## CLI UX Overhaul: Task Breakdown and Phasing

Guiding principles: first-run success, safety by default, scriptability, minimal dependencies.

### Phase A (Must-have, 80/20 value)
1) Metadata ergonomics
   - Add `--meta key=value` (repeatable) to `ingest`
   - Add `--meta-file path.(yaml|yml|json)`; merge order: front matter < meta-file < `--meta` < `--metadata` JSON
   - Tests: key=value merge, YAML file load

2) Safe previews and outputs
   - Add `--dry-run` to show per-file plan: `{path, document_id, id_source, topics}`
   - Add `--json` output format for dry-run (machine-readable)
   - Tests: dry-run JSON for single file

3) Directory selection control
   - Add `--include`/`--exclude` glob patterns (repeatable); apply in rglob walk
   - Default ignores retained: hidden files, `.obsidian`, `*assets*`
   - Tests: include-only `*.md`, exclude subfolder pattern

4) Stdin (basic)
   - Add `--stdin` flag to read content from STDIN and ingest as a single document (path is ignored)
   - Tests: minimal happy-path (optional in Phase A if flaky on CI)

Deliverables: updated CLI command, tests added under `tests/cli/`, README snippets updated in a follow-up.

### Phase B (Nice-to-have, next iteration)
5) Output controls for non-dry-run
   - `--json` success summary after ingestion (doc id, chunks)
   - `--quiet`/`--verbose` unified across commands

6) Safer defaults
   - Revisit defaulting to `--no-replace` and TTY prompts with `--yes`

7) Store/graph management commands
   - `synapse store stats|rebuild|clear`, `synapse config show|init`

8) Zero-dependency/no-graph first run
   - Add `--no-graph` or internal fallback to a null repo for purely local vector mode
   - Provide `synapse up` (Docker Compose) to start API + Memgraph

### Risks & Mitigations
- Glob matching inconsistencies across OS
  - Use `fnmatch` on POSIX-style paths, add tests
- Backwards-compat with existing CLI tests
  - New flags are additive; default behavior unchanged
- YAML parsing errors
  - Handle exceptions, surface helpful errors

