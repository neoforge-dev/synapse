# Active Context - [Date: 2025-08-08]

## Current Focus
- Stabilize configuration and DI so all API/integration tests start cleanly. Lock behavior with tests. Prioritize core ingest/query path.

## Recent Changes
- Config: Added env alias support in `Settings` to accept `GRAPH_DB_URI`, `NEO4J_USERNAME`, `NEO4J_PASSWORD` and map to `memgraph_*`. Implemented via `@model_validator`.
- API: Removed duplicate/conflicting `get_settings` import usage in `graph_rag/api/main.py` to ensure a single source of settings.
- Tests: Added `tests/config/test_settings_aliases.py` and `tests/infrastructure/test_memgraph_connection_config.py` to verify alias behavior and that `MemgraphConnectionConfig` falls back to `Settings` defaults.
- Lint: Fixed state attribute type annotations that were triggering warnings in `api/main.py`.
- Safety: Existing guards for empty labels/types remain (fallback to `UnknownNode`/`UnknownRelationship`).

## Next Steps
1. Run the full test suite. If green for new tests, address remaining API/integration failures (streaming endpoint mock shape, DI/mocks where needed).
2. Standardize on the mgclient-based repository in DI; gate or remove legacy/neo4j-async repository to reduce drift.
3. Continue raising test coverage around ingest/query vertical slice.

## Active Decisions & Considerations
- Honor common env aliases for smoother dev/test; `SYNAPSE_*` vars take precedence.
- Use a single settings loader (`graph_rag.config.get_settings`) across the app.
- Prefer mgclient-backed repo as primary path for MVP; avoid multiple client stacks in DI.

## Blockers (Project Level)
- Streaming endpoint test fails due to mock data structure mismatch (`'dict' object has no attribute 'id'`).
- Some API tests depend on incomplete mocks/DI; resolve after config passes are green.