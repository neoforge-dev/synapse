You are taking over a Python project that implements Graph-augmented Retrieval (Graph RAG) for personal knowledge bases (Notion/Obsidian) with a CLI and FastAPI API. Your objectives are to complete the remaining epics and harden the system for practical daily use.

Context you must know (read these):
- README.md: quickstart and CLI/API overview
- docs/PLAN.md: current plan, epics, and remaining work
- docs/HANDBOOK.md and docs/ARCHITECTURE.md: architecture, layering, and DI patterns
- graph_rag/*: codebase (API routers, services, core engine, infrastructure, CLI)
- tests/*: contract and integration tests; keep them green

Current status (key capabilities already implemented):
- Ingestion pipeline from Markdown and Notion exports; YAML/Notion property parsing
- Stable document identity and idempotent re-ingestion
- Graph store (Memgraph) with documents/chunks/topics and linking helpers
- Vector store (Simple/FAISS); embeddings via sentence-transformers
- Ask endpoint and CLI with streaming; citations in metadata
- Hybrid retrieval (vector + keyword blending), optional cross-encoder rerank and MMR diversification
- Notion sync CLI with incremental checkpoints and rate-limit handling; asset include/skip
- Observability: request metrics; ask/ingestion counters

Your goals (remaining plan to implement):

1) Persist LLM-derived relationships with confidence gating
- Add `SYNAPSE_ENABLE_LLM_RELATIONSHIPS` (bool, default false) and `SYNAPSE_LLM_REL_MIN_CONFIDENCE` (float 0..1, default 0.7) to settings.
- In `SimpleGraphRAGEngine._retrieve_and_build_context`, when enabled:
  - Post-process `llm_service.extract_entities_relationships` output
  - Map by canonical entity names to known graph entities
  - If both ends exist and `confidence>=min_conf`, persist via `graph_store.add_relationship` with properties `{extractor:"llm", confidence, source_name, target_name}`
  - Dedupe: avoid inserting duplicates (same type/source/target); instead update `evidence_count` and `updated_at`
- Add a config toggle `extract_relationships_persist` in AskRequest and thread to engine
- Counters: increment `llm_relations_inferred_total` and `llm_relations_persisted_total`
- Tests: unit for gating/dedupe; integration with Memgraph fixture

2) Subgraph APIs and exports
- New router `graph_rag/api/routers/graph.py` with:
  - `GET /graph/neighbors?id=..&depth=1&types=HAS_TOPIC,MENTIONS` -> `{nodes, edges}`
  - `POST /graph/subgraph {seeds:[], depth, rel_types?}` -> `{nodes, edges}`
  - `GET /graph/export?format=graphml|json` -> string payload; implement simple GraphML and Cytoscape JSON formatters
- Wire router in `api/main.py`; add CLI wrappers `synapse graph neighbors|export`
- Tests: basic shape tests; export smoke tests

3) Notion sync dry-run diffs and attachment policy
- Extend `synapse notion sync` with:
  - `--dry-run` to print planned changes (add/update/delete) per `page_id`
  - `--attachments policy` where policy in `ignore|link|download`; implement download with `--download-path`
- State file: keep last cursor and last edited time per context key
- Rate limit budget: configurable QPS and backoff ceiling
- Tests: unit diff; CLI output checks

4) Background jobs and richer metrics
- FAISS maintenance job: periodic (disabled by default) and CLI-triggered
- Integrity checks: vector count vs graph chunks; log warnings and metrics
- Metrics: `ingestion_chunks_total`, `ingestion_vectors_total`, plus latency histograms for ingest/query
- Tests: counters increment and job invocation paths

5) MCP server and packaging
- Implement a small MCP server exposing `ingest_files`, `search`, `query_answer` that calls the local FastAPI or direct services
- Provide config examples for VS Code/Claude; add smoke tests for tool invocation
- Packaging: PyPI + Homebrew; `synapse up` (docker-compose) convenience

Guardrails and expectations:
- Maintain green tests. Add or adjust tests only when changing public contracts; prefer additive changes.
- Follow existing layering/DI patterns. Avoid tight coupling across layers.
- Keep code readable and match `code_style` conventions; add concise docstrings for new modules.
- Do not hard-fail on optional dependencies (e.g., CrossEncoder, Prometheus) — degrade gracefully.
- Ensure new API params have sane defaults and are backward compatible.

Getting started checklist:
- Read docs/PLAN.md (Remaining work section) and open related files
- Add new settings and feature flags
- Implement LLM relationship persistence with gating and counters
- Add graph router for subgraph/expor; wire it up and write small tests
- Extend Notion sync for dry-run/attachments; unit tests for diffing
- Add maintenance jobs and metrics; update README with new flags/endpoints
- Prepare MCP server skeleton and packaging scripts; add examples

When stuck:
- Prefer small, incremental PR-sized edits; run targeted pytest subsets often
- If a dependency is missing at runtime, fallback to no-op or mock and log a warning
- Document new flags/endpoints in README and HANDBOOK

---

Hand-off briefing for the next Cursor agent

Principles (non-negotiable)
- Pareto first; TDD always; YAGNI; vertical slices over horizontal layers

Primary user journey
1) Ingest notes (local/Notion)
2) Ask a question with citations; optionally stream
3) Explore/export subgraphs
4) Operate the system (health, metrics, vector maintenance)

Status overview
- LLM relation gating + optional persist; subgraph APIs/CLI; Notion `--dry-run` + `--attachments`; metrics/admin/maintenance; MCP skeleton; BM25; streaming ask; packaging and unit CI in place

Immediate execution plan (see `docs/PLAN.md` for acceptance criteria)
- P0
  - Retrieval toggles end-to-end: `search_type`, `blend_keyword_weight`, `no_answer_min_score` implemented and tested
  - API tests ensure toggles propagate to engine
- P1
  - Notion dry-run robustness; rate-limit tests with 429 mocks
  - Admin JSON logging toggle; minor integrity sampling
- P2
  - CLI `synapse up` (compose wrapper); graph API test expansion; prepare TestPyPI workflow

Concrete next tasks
1) Implement and test `no_answer_min_score` in engine; verify ask returns calibrated no-answer below threshold
2) Ensure API -> engine propagation for retrieval toggles; add unit+API tests
3) Extend Notion tests for multi-run dry-runs and 429 handling
4) Add `SYNAPSE_JSON_LOGS` setting; wire JSON logs in API/CLI
5) Implement `synapse up` command; update README examples
6) Optional Memgraph job (allowed to fail) in CI; keep unit job green

Working agreements
- Keep package code lint-clean; tests may be looser
- Degrade gracefully on optional deps; log warnings not crashes
- Commit small, descriptive changes; keep CI green
