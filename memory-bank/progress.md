# Progress

## Completed
- FastAPI app structure.
- `GraphStore` interface defined & `MemgraphGraphRepository` implemented.
- Core domain models created (`Document`, `Chunk`, `Node`, etc.).
- Test framework (`pytest`, async support) configured.
- `pymgclient` integrated & core tests passing (SSL test skipped).

## Blocked By
- Integration test failures (API/CLI, NLP, `GraphStore`). See `active-context.md`.

## Next Steps
1. Fix integration tests.
2. Implement Ingestion Pipeline.
3. Implement Query Engine. 