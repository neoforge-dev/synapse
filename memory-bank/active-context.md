# Active Context

## Current Focus
- Fixing dependency and import issues in the codebase
- Resolving FastAPI response model type errors
- Ensuring proper type annotations for dependencies

## Recent Changes
- Added missing API settings (api_host, api_port)
- Created LLM protocols and types modules
- Updated Memgraph client imports to use pymgclient
- Fixed settings references in embedding service

## Active Decisions
1. Using pymgclient instead of mgclient for Memgraph integration
2. Standardizing on GraphRepository interface for type annotations
3. Maintaining consistent settings naming across the codebase

## Next Steps
1. Fix FastAPI response model type errors in query router
2. Resolve remaining import issues in test files
3. Ensure proper type annotations for all dependencies
4. Update test configurations to match new settings

## Open Questions
- Should we consolidate the graph repository interfaces?
- How to handle the duplicate test_memgraph_store.py files?
- What's the best way to handle the FastAPI response model type errors?

## Current Challenges
1. FastAPI response model type errors in query router
2. Inconsistent type annotations between interfaces and implementations
3. Duplicate test files causing import conflicts
4. Missing or incorrect settings references in various modules 