# Implementation Plan (Pragmatic, Pareto-first)

This plan targets the 20% of work that delivers 80% of value for a Mac-based power user with a large personal knowledge base (Notion/Obsidian), using CLI/API today and MCP tomorrow.

## Objectives
- Persistent, reliable local knowledge base: ingest Markdown/Notion export, persist vectors, build a graph, query via CLI/API.
- Zero-to-usable in minutes on macOS; optional auto-start.
- Thin MCP server to expose ingest/search/query tools to chat IDEs.

## Guiding Principles
- TDD for each vertical slice (tests first, minimal code to green, refactor).
- YAGNI: implement only what directly serves the core flow.
- Clean architecture: API → Services → Core → Infra, DI’d, test-friendly.

## Core User Journey
1) Install on Mac; run one command to bring up API (+ Memgraph if used).
2) Ingest a folder of Markdown (Obsidian/Notion export) with front matter metadata.
3) Persist vectors between runs (local FAISS index + sidecar metadata).
4) Query via CLI/API; stream results if desired.
5) (Next) Use same actions from MCP-enabled chat tools.

## Workstream A: Vector Store Persistence (FAISS)
- Why: Highest leverage for reliability; enables offline, resumable knowledge base.
- Deliverables:
  - New `FaissVectorStore` (async interface-compatible):
    - Persist index to disk via `faiss.write_index/read_index`.
    - Persist chunk metadata/id mappings via JSON sidecar in the same directory.
    - Generate embeddings via configured `EmbeddingService` when missing.
    - Cosine/IP search (IndexFlatIP) with normalized vectors.
  - Settings additions:
    - `vector_store_type = "faiss"` (default stays "simple").
    - `vector_store_path` (e.g., `~/.graph_rag/faiss`), created on first run.
  - Factory wiring in `api/dependencies.py` to construct FAISS store when selected.
  - Tests:
    - Ingest chunks without embeddings and search → results shape ok.
    - Restart store (new instance, same path) and search again → persistence verified.

## Workstream B: Markdown/Obsidian Ingestion
- Why: Directly serves local KB ingestion.
- Deliverables:
  - Front matter parser (YAML) in CLI ingest path; map tags/topic/date to metadata.
  - Ignore binary assets; handle UTF-8.
  - Directory ingestion support in CLI: process all Markdown files recursively, skip `.obsidian/`, images, and hidden files.
  - Tests:
    - Ingest sample markdown with front matter; metadata captured and merged with CLI `--metadata` overrides.
    - Directory ingestion invokes processing for all eligible files.
  - Notes:
    - Obsidian front matter keys to treat specially: `tags`/`Topics` → `topics` (list of strings), `aliases` → `aliases`, date fields if present → `created_at`/`updated_at`.
    - Keep parsing tolerant; warn on YAML errors, continue.
  - Acceptance:
    - CLI can ingest a directory path; logs per-file; exits non-zero only if no files processed.
    - Unit tests pass; no regression in existing CLI tests.

## Workstream C: Notion Export Ingestion (Phase 1)
- Why: Many users export Notion as Markdown ZIP.
- Deliverables:
  - Path walker for Notion-exported Markdown; normalize filenames; strip Notion artifacts.
  - Parse Notion front matter or property tables (if present) at top of file; map `Tags`/`Created`/`Last edited time`.
  - Tests: ingest a mini Notion export tree; metadata preserved and topics extracted.
  - Acceptance: files with Notion folder names ("Page Name xxxx") are ingested with stable `document_id` derivation.

## Workstream D: Topic Tagging (Pragmatic)
- Why: Sorting/organizing by topics provides immediate value.
- Deliverables:
  - Heuristic topic extraction (first heading / tag / simple keyphrase fallback) with deterministic behavior;
  - Stored in chunk/document metadata for graph queries.
  - Graph projection: optionally add `:Topic` nodes linked to documents/chunks when topics present.
  - Tests with deterministic inputs/outputs (no external LLM needed initially).
  - Acceptance: searching by topic keyword returns chunks tagged with the topic via keyword path.

## Workstream E: Autostart Ergonomics (Mac)
- Why: “It just runs” UX.
- Deliverables:
  - `make up` target to start Memgraph + API.
  - Sample `launchd` plist and script; doc steps to enable/disable.
  - Smoke test for `make up` (non-blocking).
  - Acceptance: `make up` runs API on default port and tails logs; `make down` stops.

## Workstream F: MCP Server (Thin Proxy)
- Why: Unblocks chat/IDE integration without reworking core.
- Deliverables:
  - Python MCP server exposing tools:
    - `graph_rag.ingest_files(paths[], metadata?)`
    - `graph_rag.search(query, type, limit, stream?)`
    - `graph_rag.query_answer(text, k?)`
  - Unit tests for tool handlers (mock API calls).
  - Docs: `docs/MCP.md` usage and configuration.
  - Acceptance: smoke script can call MCP server methods and receive valid responses using mocked API.

## Documentation Upgrades
- `README.md`: Quickstart (Mac), CLI/API, config table, FAQs.
- `docs/ARCHITECTURE.md`: one-pager mapping core → services → infra.
- `docs/PRD.md`: scope, personas, top jobs-to-be-done, non-goals.
- `docs/BACKLOG.md`: curated, prioritized list (sync with this plan).

## Risks / Considerations
- Embedding model load time (sentence-transformers) → allow `mock`/smaller model; cache model instance.
- FAISS index consistency → guard writes (temp + replace), validate dimension, normalize vectors.
- Notion export variability → start with Markdown path; document unsupported bits.

## Milestones (Incremental)
1) FAISS persistence (A) — tests + wiring — ship.
2) Obsidian front matter + directory ingestion (B) — tests + CLI support — ship.
3) Notion export path (C) — tests — ship.
4) Topics (D) — tests — ship.
5) Autostart (E) — docs + make target — ship.
6) MCP server (F) — tests + docs — ship.
7) README/ARCH/PRD/BACKLOG — ship.

## Acceptance per Milestone
- Green unit tests (`make test`), existing suite unaffected.
- New tests for the slice; CI validate passes.
- Backwards-compatible defaults; no breaking changes to existing API/CLI.

---

Next action: Implement Milestone 1 (FAISS persistence) with tests and wiring.
