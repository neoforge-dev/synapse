# Graph RAG MCP: Identity, Idempotence, and Vector Store Robustness Plan

This plan captures the remaining details and concrete tasks to fully deliver stable document identity, idempotent ingestion, robust vector store operations, and good observability.

## Objectives
- Stable, canonical `document_id` across imports and renames
- Idempotent re-ingestion that atomically replaces chunks and vectors
- Correct FAISS deletion (no ghost vectors; index remains consistent)
- Notion export nuances handled reliably (IDs, property tables)
- End-to-end wiring in CLI/API with observability of identity provenance
- Comprehensive tests (unit, service, infrastructure, integration)

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
- Consider a future CLI flag `--no-replace` if needed.

### 6) Testing
- Unit tests: identity derivation (done), FAISS delete/rebuild (to add).
- Service tests: re-ingestion deletes vectors (present), can expand assertions after FAISS fix.
- API/CLI smoke already cover ingestion flows.

### 7) Documentation
- Keep `ARCHITECTURE.md` and `README.md` consistent with identity strategy and idempotence.
- Add notes on FAISS persistence and deletion trade-offs.

## Acceptance Criteria
- Re-ingesting a doc with same `document_id` replaces chunks in graph and vectors; no duplicate chunks or stale vectors remain.
- FAISS `delete_chunks` removes vectors accurately and persists state; after reload, searches reflect deletions.
- Identity derivation passes tests for metadata, Notion UUIDs, content and path hash fallbacks.
- CLI processes Notion markdown exports, derives IDs consistently, and attaches `id_source`.
- All tests pass locally (unit + infra). Integration tests remain green.
