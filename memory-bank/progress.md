# Progress

## Working
- FastAPI structure setup
- GraphStore interface defined, implemented by MemgraphRepository
- Core domain models (Document, Chunk, Entity, Relationship, Node)
- Test framework structure

## Blocked
- **CRITICAL:** Test failures preventing progress (see active-context.md)
- Async handling in repository and tests

## Next Development Phases
1. Fix test failures, especially async mocking
2. Implement ingestion pipeline
3. Develop query engine with graph context 