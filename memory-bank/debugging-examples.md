# Debugging Examples: GraphRAG MCP

## Example 1: Document Ingestion Error

### Error Context
- Test: `test_ingest_command.py`
- Error Type: State Transition Error
- Symptom: Document nodes created but relationships missing

### Applying First Principles

#### 1. Information Gathering
```python
# State Capture
MATCH (d:Document) RETURN d;
MATCH (d:Document)-[r]->() RETURN d, r;

# Input Validation
- Document content: Valid
- Entity extraction: Successful
- Graph write transaction: Committed
```

#### 2. Hypothesis Formation
1. **Transaction Scope**
   - Hypothesis: Transaction commits before relationship creation
   - Verification: Check transaction logs
   - Impact: High (data integrity)

2. **Entity Mapping**
   - Hypothesis: Entity IDs mismatch between extraction and storage
   - Verification: Compare extracted vs stored entities
   - Impact: Medium (data consistency)

3. **Graph Constraints**
   - Hypothesis: Missing constraint prevents relationship creation
   - Verification: Check schema constraints
   - Impact: Low (configuration)

#### 3. Verification
```python
# Transaction Log Analysis
MATCH (n) RETURN n ORDER BY n.created_at;

# Entity Comparison
MATCH (e:Entity) RETURN e;
MATCH (d:Document)-[r:HAS_ENTITY]->(e:Entity) RETURN d, r, e;
```

#### 4. Resolution
- Implement transaction scope validation
- Add relationship creation verification
- Update graph constraints if needed
- Document fix in memory bank

## Example 2: Query Pipeline Error

### Error Context
- Test: `test_query_pipeline.py`
- Error Type: Integration Error
- Symptom: Query returns incorrect context

### Applying First Principles

#### 1. Information Gathering
```python
# State Capture
MATCH (q:Query) RETURN q;
MATCH (q:Query)-[r:RETRIEVED_FROM]->(d:Document) RETURN q, r, d;

# Input Validation
- Query text: Valid
- Graph traversal: Executed
- Context assembly: Completed
```

#### 2. Hypothesis Formation
1. **Graph Traversal**
   - Hypothesis: Incorrect path selection in graph query
   - Verification: Analyze query execution plan
   - Impact: High (result accuracy)

2. **Context Assembly**
   - Hypothesis: Document ordering incorrect
   - Verification: Check context assembly logic
   - Impact: Medium (result quality)

3. **Query Processing**
   - Hypothesis: Query preprocessing alters intent
   - Verification: Compare raw vs processed query
   - Impact: Low (user experience)

#### 3. Verification
```python
# Query Analysis
EXPLAIN MATCH (q:Query)-[r:RETRIEVED_FROM]->(d:Document) RETURN q, r, d;

# Context Validation
MATCH (q:Query) RETURN q.context;
```

#### 4. Resolution
- Optimize graph traversal
- Fix context assembly logic
- Improve query preprocessing
- Document solution in memory bank

## Example 3: E2E Integration Error

### Error Context
- Test: `test_e2e.py`
- Error Type: Performance Error
- Symptom: Slow response times

### Applying First Principles

#### 1. Information Gathering
```python
# Performance Metrics
PROFILE MATCH (n) RETURN n;
SHOW INDEX INFO;

# System State
MATCH (n) RETURN count(n);
MATCH ()-[r]->() RETURN count(r);
```

#### 2. Hypothesis Formation
1. **Index Usage**
   - Hypothesis: Missing or incorrect indexes
   - Verification: Analyze query plans
   - Impact: High (performance)

2. **Graph Size**
   - Hypothesis: Large graph affecting traversal
   - Verification: Check node/relationship counts
   - Impact: Medium (scalability)

3. **Query Complexity**
   - Hypothesis: Complex queries causing slowdown
   - Verification: Profile query execution
   - Impact: Low (optimization)

#### 3. Verification
```python
# Performance Analysis
PROFILE MATCH (n) WHERE n.property = value RETURN n;

# Index Validation
SHOW INDEX INFO;
```

#### 4. Resolution
- Add appropriate indexes
- Optimize graph structure
- Simplify complex queries
- Document optimizations in memory bank 