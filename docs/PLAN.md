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
- Guardrails/logging:
  - [x] Log the number of existing chunks and include `doc_id` and `id_source`
  - [x] Handle vector store delete exceptions without failing ingestion (warn and continue)
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
  - Non-dry-run `--json` success payload including `document_id`, `num_chunks`, `id_source`, `path`, flags, and optional `topics` [DONE]

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
- Non-dry-run `synapse ingest --json` supports single file, directory, and `--stdin` payloads [DONE].
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
   - `--json` success summary after ingestion (doc id, chunks) [DONE]
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

## New initiatives based on external evaluation/feedback

The recent assessment highlights that while the architectural foundations are sound, reliability and an answer-synthesis layer are essential to deliver a one-command insight experience. The items below extend this plan.

### A) Quality and reliability hardening (short-term)
- Raise code coverage gates in CI to >= 85% lines/branches for hot paths; full-repo target will follow after infra tests are expanded.
- Expand integration tests:
  - Graph repository (Memgraph) CRUD/links smoke tests behind label/skips
  - Vector store: delete/rebuild persistence scenarios across restarts
  - End-to-end: ingest → query → ask (once implemented) happy paths
- Property-based tests for identity derivation and chunking invariants.
- Static analysis: enable mypy in strict mode on `core/` and `services/`.
- Error contracts: normalize API error responses (problem+json) and add tests.

### B) Synthesis layer (LLM) and one-command answers (short-term)
- Implement `LLMService` providers: OpenAI, Anthropic, Ollama (local) with retry, timeouts, and token budgeting; selectable via settings.
- Prompting strategy:
  - Deterministic format for retrieved chunks + graph context
  - Answer, cite, and summarize modes with safety rails
- New API: `POST /api/v1/ask` with options `{ text, k, include_graph, provider, model, streaming }`.
- New CLI: `synapse ask "question" [--k 5] [--graph] [--provider openai] [--model gpt-4o] [--stream] [--json]`.
- Tests: golden prompt assembly unit tests; mocked LLM responses; CLI/API contracts.

### C) Vector store robustness and maintenance (short/mid-term)
- Persist raw embeddings alongside metadata to support precise deletions and index rebuilds (FAISS path).
- Maintenance commands: `synapse store stats|rebuild|clear` (CLI) and matching admin API endpoints.
- Config defaults to a safer persistent store in API mode; document trade-offs.

### D) BrandFocus-oriented capabilities (mid-term)
- Style profiling: compute a style fingerprint from user corpus; expose as `StyleProfile` stored per user; add prompt adapters to reflect tone and structure.
- Content ideation: `synapse suggest --topic X` to produce outlines/snippets using the knowledge base with guardrails.
- Relationship intelligence: first-class `Person`/`Company` entities with recency/frequency scores and a simple "follow-up" signal; queries and views for interactions.

### E) Observability and ops (short/mid-term)
- Structured logging (JSON); request correlation IDs end-to-end.
- `/metrics` (Prometheus) for ingestion rates, vector counts, latency buckets.
- Health/readiness split; dependency pings (Memgraph, vector store) with backoff.

### F) Developer experience and packaging (short-term)
- `pipx` and Homebrew formula for CLI; prebuilt binaries via PyInstaller for macOS/Linux.
- `synapse up`: Docker Compose to start API + Memgraph + optional FAISS sidecar.
- Example recipes: richer jq/xargs, `ask` pipelines, and MCP usage.

### Phasing
- Phase 1 (2-3 weeks): A, B (OpenAI provider + ask), part of C (embedding persistence), E basics, F packaging.
- Phase 2 (3-4 weeks): Remaining C (maintenance cmds), D (style profile v1, relationship scores), E metrics.
- Phase 3: Additional providers (Anthropic/Ollama), advanced prompting, BrandFocus-specific UX polish.

