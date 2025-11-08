# Synapse Architecture Overview

Synapse is a graph-augmented Retrieval-Augmented Generation (RAG) platform built around a small number of composable services. This document captures the current production layout so contributors understand where features live and how requests flow through the stack.

---

## High-Level Layout

```
CLI (Typer) ─┬─ synapse ingest / search / up
             └─ synapse mcp …
FastAPI      ─┬─ /api/v1/core-business-operations
             ├─ /api/v1/enterprise-platform
             ├─ /api/v1/analytics-intelligence
             └─ /api/v1/advanced-features
Services     ─┬─ IngestionService (documents → graph/vector)
             ├─ SearchService (graph + vector retrieval)
             └─ AdvancedFeaturesService (analytics, brand safety, reasoning)
Data stores  ─┬─ Memgraph (graph)
             ├─ Simple/FAISS vector store
             └─ optional Postgres/SQLite analytics
```

The CLI and MCP server reuse the same services as the FastAPI layer so behaviour is consistent regardless of the entry point.

---

## Consolidated Routers (4)

1. **Core Business Operations** – ingestion, document management, hybrid search, “ask” query orchestration, CRM hooks.
2. **Enterprise Platform** – authentication, configuration, admin tooling, health checks.
3. **Analytics Intelligence** – dashboards, metrics, reporting endpoints (read-heavy, often backed by cached aggregations).
4. **Advanced Features** – graph analytics, brand safety checks, hot-take scoring, reasoning helpers, chunk inspection.

Each router is created by a factory in `graph_rag/api/routers/*.py` and wired inside `graph_rag/api/main.py`. Startup dependencies (Memgraph repository, vector store, ingestion pipeline, embedding service) are initialised in the FastAPI lifespan handler and stored on `app.state`.

---

## Services of Interest

- `IngestionService` orchestrates parsing, chunking, entity extraction and persistence into Memgraph + the vector store. It supports idempotent re-ingestion (deleting stale chunks/vectors before writing new ones) and optional vision/PDF processors.
- `AdvancedFeaturesService` powers the advanced router. It derives graph statistics, connected components, visualization data, content scoring, and brand-safety analysis from the current graph repository and vector store. The API no longer returns hard-coded payloads—the service executes heuristics against stored data.
- `SearchService` blends graph and vector lookups, providing fallbacks when one backend is unavailable.

All services log through the structured logging helpers in `graph_rag/observability`. A dedicated `ComponentType.SERVICE` was added for service-level telemetry.

---

## Data & Ports

| Component            | Container Port | Host Port (`synapse up`) |
|----------------------|----------------|--------------------------|
| FastAPI (uvicorn)    | 8000           | **18888**                |
| Memgraph (Bolt)      | 7687           | **17687**                |
| Memgraph (HTTP)      | 7444           | **17444**                |
| Postgres (optional)  | 5432           | **15432**                |

The container ports remain standard to ease intra-container communication; host ports are shifted to avoid collisions with other local services.

---

## Request Flow (example)

1. `synapse ingest ./docs` (CLI) → `IngestionService` via in-process call → document chunks stored in Memgraph + vector store.
2. `curl http://localhost:18888/api/v1/advanced/graph/stats` → Advanced router → `AdvancedFeaturesService.graph_stats()` → Memgraph repository + vector store analysed → JSON response.
3. MCP clients call the same services through the MCP server wrapper (`graph_rag/mcp/server.py`).

---

## Extension Points

- Additional analytics can plug into `AdvancedFeaturesService` via the graph snapshot helper.
- New CLI commands should live in `graph_rag/cli/commands/` and reuse service factories via `graph_rag/api/dependencies` to stay consistent with the API.
- For a step-by-step list of environment variables and service changes needed to move from the mock defaults to production backends (Memgraph, FAISS, LLM providers, Postgres), see `docs/guides/PRODUCTION_BACKENDS.md`.

---

For installation and packaging details see `docs/guides/INSTALLATION_GUIDE.md` and `docs/HOMEBREW.md`.
