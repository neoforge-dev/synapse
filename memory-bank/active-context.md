# Active Context: GraphRAG MCP

## Current Focus
- **Refinement & Robustness:** Address TODOs from `progress.md`.
    - Priority: Fix Ingestion ID return, Improve Error Handling.
    - Enhance Tests (Coverage, Integration).
    - Implement Admin features (API/CLI).
    - Make CLI API URL configurable.

## Recent Major Changes
- Completed initial API/CLI interface implementation (FastAPI + Typer).
- Implemented batch & streaming search.
- Set up project repo files (`README`, `LICENSE`, CI etc.).
- Added Config, API, CLI tests (mocked where necessary).
- Refactored `MemgraphStore` (neo4j driver), `EmbeddingService`, `PersistentKGBuilder`.
- Refactored Config (`graph_rag/config/settings.py`).

## Key Blockers / Issues
- Ingestion endpoint returns placeholder `document_id`.
- CI tests lack DB integration.

## Open Questions (Deferred / Future)
- Strategy for document *content* updates?
- Need for explicit transaction management across service operations? 