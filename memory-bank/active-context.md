# Active Context

## Current Focus
- Resolve FastAPI response model type errors (esp. query router).
- Fix dependency/import issues (incl. tests).
- Ensure consistent type annotations for dependencies & interfaces.

## Recent Changes (High-Level)
- Added API settings (host, port).
- Introduced LLM protocols/types.
- Switched to `pymgclient`.
- Fixed various settings references.

## Active Decisions
- Using `pymgclient` for Memgraph.
- Standardizing on `GraphRepository` interface type hints.
- Maintaining consistent settings naming.

## Next Steps
1. Fix FastAPI response model type errors (query router).
2. Resolve remaining import issues (tests).
3. Ensure proper type annotations across dependencies.
4. Update test configurations for new settings.

## Open Questions
- Consolidate graph repository interfaces?
- Handle duplicate `test_memgraph_store.py` files?
- Best approach for FastAPI response model type errors? 