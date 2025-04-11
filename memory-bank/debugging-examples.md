# Debugging Examples: GraphRAG MCP

## Debugging Pattern Summary
1.  **Observe:** Identify symptom (e.g., test failure, error log).
2.  **Gather Info:** Check inputs, outputs, state (logs, DB queries, state capture).
3.  **Hypothesize:** Formulate potential causes based on info and system knowledge.
4.  **Verify:** Test hypotheses using targeted checks (specific queries, code inspection, debuggers).
5.  **Resolve:** Implement the fix based on verified cause.
6.  **Document:** Update memory bank if needed.

---

## Example 1: Ingestion - Missing Relationships

- **Symptom:** Document nodes exist, but `CONTAINS` relationships to chunks are missing after ingestion.
- **Potential Causes:**
    - Transaction commits before relationship creation.
    - Entity/Chunk ID mismatch during linking.
    - Graph constraint violation.
    - Error in `GraphStore.create_relationship` implementation.
- **Verification:**
    - `MATCH (d:Document)-[r:CONTAINS]->(c:Chunk) RETURN d,r,c;` (Check if *any* exist).
    - Check transaction logs/order of operations in `IngestionService`.
    - Inspect IDs passed to `graph_repo.create_relationship`.
    - Review `MemgraphGraphRepository.add_relationship` logic.
- **Resolution Type:** Fix transaction scope, relationship creation logic, or ID handling.

---

## Example 2: Query - Incorrect Context

- **Symptom:** Query returns irrelevant or incomplete context chunks.
- **Potential Causes:**
    - Incorrect graph traversal path in query engine.
    - Flawed context assembly logic (ordering, filtering).
    - Poor vector search results (embedding quality, search query).
    - Query preprocessing alters meaning.
- **Verification:**
    - `EXPLAIN` graph query used for context retrieval.
    - Log/Inspect intermediate results (vector search hits, graph neighbors).
    - Compare raw vs. processed query text.
    - Analyze `QueryEngine` context assembly steps.
- **Resolution Type:** Optimize graph query, fix context assembly, improve embedding/search strategy.

---

## Example 3: E2E - Slow Performance

- **Symptom:** API endpoints or CLI commands respond slowly during integration tests.
- **Potential Causes:**
    - Missing/inefficient database indexes.
    - Large graph size impacting traversal.
    - Complex/unoptimized Cypher queries.
    - Bottleneck in API logic (e.g., synchronous operations).
- **Verification:**
    - `PROFILE` slow queries in Memgraph.
    - `SHOW INDEX INFO;`
    - Check node/relationship counts (`MATCH (n) RETURN count(n);`).
    - Profile Python code execution (e.g., using `cProfile`).
- **Resolution Type:** Add DB indexes, optimize queries, refactor slow code sections.

---
*(Refer to `core/debug_tools.py` for specific tooling)* 