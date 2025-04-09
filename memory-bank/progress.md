# Progress: GraphRAG MCP

## Completed
- **Core RAG:** Ingest -> Embed -> Store (Memgraph/neo4j driver) -> Retrieve (Vector/Keyword).
- **Interfaces:**
    - FastAPI (Ingest, Search Batch/Stream, Health). Lifespan mgmt.
    - CLI (Ingest doc, Search Batch/Stream, Health) via HTTP to API.
- **Config:** Pydantic Settings (`config/settings.py`, `.env`).
- **Structure:** Clean Arch (`domain`, `core`, `infra`, `api`, `cli`), Tests (`config`, `api`, `cli`).
- **Repo Setup:** `.gitignore`, `LICENSE`, `README.md`, `CONTRIBUTING.md`, GitHub Actions CI (Lint, Test).
- **Refactoring:** `MemgraphStore` (neo4j driver), `EmbeddingService`, `PersistentKGBuilder`.

## Next Steps / TODOs
- **Ingestion ID:** Fix API/CLI inability to return generated `document_id` (needs Background Tasks or Engine change).
- **Error Handling:** Custom exceptions, API/CLI error refinement.
- **Admin:** Implement API/CLI admin features (stats, config view).
- **Testing:** API/CLI test coverage, CI integration tests (w/ DB service).
- **Docs:** OpenAPI refinement, docstrings.
- **Config:** Make CLI API URL configurable.
- **Secrets:** Evaluate production secrets management.
- **Future:** Graph Search impl, Advanced Ingestion/Search, Prod Hardening.

## Known Issues
- Ingestion endpoint returns placeholder `document_id`.
- CI tests lack DB integration. 