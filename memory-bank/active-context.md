# Active Context

## Current Focus / Blockers
- **Integration Tests:** Fix remaining failures:
    - API/CLI (503/404 errors, CLI structure).
    - NLP model errors (NLTK/Spacy setup/downloads).
    - `GraphStore` interface methods & related tests.
- **`pymgclient` SSL Test:** Skipped (requires native Memgraph or complex Docker SSL setup). Consider resolving post-MVP if needed.

## Recent Changes
- `pymgclient` integrated; tests passing (except skipped SSL).
- `MemgraphGraphRepository` refactored to `GraphStore` interface.
- Core domain models added (`Node`, `Entity`, `Relationship`).
- Repository methods updated to align with `GraphStore`.

## Next Steps
1. Resolve all integration test failures (see Blockers).
2. Implement ingestion pipeline (chunking, embedding, storage).
3. Develop query engine (vector search + graph context retrieval). 