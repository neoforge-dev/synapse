# System Patterns: GraphRAG MCP

## Architecture
- Clean Architecture: domain, core, infra, api, cli

## Key Components
- **API:** FastAPI, GraphRAGEngine
- **CLI:** Typer, HTTP client
- **Core:** Orchestration (GraphRAGEngine)
- **Infra:** GraphRepository (Memgraph, neo4j driver)
- **Domain:** Models (Pydantic), Interfaces

## Core Patterns
- DI (FastAPI Depends)
- Repository
- Async I/O
- Pydantic Settings

## Testing Patterns
- **Test Organization**
  - Unit tests: Fast, isolated, mock dependencies
  - Integration tests: Test component interactions
  - E2E tests: Full system testing
  - Clear test markers for different types

- **Test Data Management**
  - Centralized test data
  - Reusable test fixtures
  - Sample data generators
  - Test data validation

- **Test Utilities**
  - Common test helpers
  - Database state verification
  - Async test support
  - Error handling tests

- **Test Configuration**
  - pytest.ini for global settings
  - Coverage requirements
  - Test timeouts
  - Logging configuration

## Graph Storage Patterns
- **Write Operations**
  - MERGE for idempotent node/relationship creation
  - Timestamps for create/update tracking
  - Retry with exponential backoff for transient failures
  - Transaction support for atomic operations

- **Query Operations**
  - Entity-based traversal
  - Relationship-based filtering
  - Property-based search
  - Neighbor exploration

- **Performance**
  - Connection pooling
  - Batch operations (planned)
  - Error handling with logging
  - Retry strategies for resilience

## Search
- Memgraph MAGE (Keyword/Vector)

## Debugging Protocols

### Senior Developer Protocol
1. **Analysis Phase**
   - Observe without judgment
   - Analyze test case
   - Question assumptions

2. **Systematic Investigation**
   - Find related failures
   - Trace execution path
   - Identify implementation gaps

3. **Implementation Phase**
   - Generate hypotheses
   - Verify systematically
   - Implement minimal fix

4. **Persistent Error Protocol**
   - Component architecture review
   - Edge case analysis
   - Dependency analysis

### First Principles Protocol
1. **Info Flow:** Behavior = inputs + state; Error = info mismatch; Debug = info gathering.
2. **State:** Sum of vars/rels; Traceable transitions; Graph aids tracking.
3. **Error Types:** Input Validation, State Transition, Integration, Performance.

### Process Summary
1. **Gather Info:** Capture state, inputs, trace flow, map graph transitions.
2. **Hypothesize:** Form/prioritize multiple hypotheses (local/systemic).
3. **Verify:** Minimal tests, graph queries, pos/neg cases.
4. **Resolve:** Minimal fix, validate state, update graph/docs.

### Tools
- Env matching error; Graph viz; State logging; Graph queries.
- SeniorDebugProtocol (core/debug_tools.py)
- GraphDebugger (core/debug_tools.py)

*Detailed examples in `debugging-examples.md` & `debug_tools.py`* 