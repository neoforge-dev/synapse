# Active Context

## Critical Issues
- **Test failures across all suites:**
  - `TypeError: object AsyncMock/AsyncBoltDriver can't be used in 'await' expression`
  - Fixture errors: missing 'mocker', RAG engine/KG builder TypeError
  - API/CLI failures (503/404 errors, CLI structure issues)
  - NLP model errors: missing NLTK punkt_tab, Spacy en_core_web_sm
  - AttributeError on repository methods (GraphStore refactor)

## Recent Changes
- Refactored `MemgraphGraphRepository` to implement `GraphStore`
- Added domain models: `Node`, `Entity`, `Relationship`
- Updated repository methods for new model usage
- Attempted fix for async handling

## Immediate Actions
1. Fix async handling in `_execute_write/read_query`, `_get_driver`
2. Ensure NLP models download correctly in test env
3. Fix fixture scopes and mock configurations
4. Correct API dependencies and CLI structure
5. Update tests to use new GraphStore interface methods 