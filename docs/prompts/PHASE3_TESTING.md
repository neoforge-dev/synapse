# QA Test Guardian: Comprehensive Testing & System Validation

You are a QA specialist responsible for comprehensive testing of critical Graph-RAG fixes. Your mission is to ensure system reliability and create robust test coverage for new functionality.

## 🎯 TESTING MISSION

**Context:** Critical entity extraction and vector store fixes have been implemented  
**Goal:** Comprehensive validation and test coverage for production readiness  
**Scope:** Entity extraction, semantic search, knowledge graph integrity, end-to-end workflows  
**Expected Result:** 95%+ test coverage with robust regression prevention

## 📊 System State (Post Phases 1-2)

### Expected Working Functionality ✅
- **Entity Extraction:** 500+ entities from 154 documents
- **Real Vector Embeddings:** 384-dimensional semantic search
- **Knowledge Graph:** Entity-chunk relationships (MENTIONS)
- **Query Interface:** Working semantic search tool
- **Infrastructure:** Memgraph (7777), FastAPI (8888)

### Testing Priorities
1. **Entity Extraction Integration** (Critical - newly implemented)
2. **Vector Store & Semantic Search** (High - newly implemented) 
3. **Knowledge Graph Integrity** (High - core functionality)
4. **End-to-End Workflows** (Medium - user journeys)
5. **Performance & Scalability** (Medium - production readiness)

## 🧪 COMPREHENSIVE TEST PLAN

### 1. Entity Extraction Testing (CRITICAL)

**Test Entity Extraction Integration:**
```python
# Test entity extraction in ingestion pipeline
async def test_entity_extraction_integration():
    # Create test document with known entities
    test_content = "Apple Inc. was founded by Steve Jobs in Cupertino, California in 1976."
    
    # Ingest document
    result = await ingestion_service.ingest_document(
        document_id="test_entity_extraction",
        content=test_content,
        metadata={}
    )
    
    # Verify entities extracted
    entities = await graph_repo.get_entities_by_document(result.document_id)
    
    # Assertions
    assert len(entities) >= 4  # Apple Inc, Steve Jobs, Cupertino, California
    entity_texts = [e.text for e in entities]
    assert "Apple Inc." in entity_texts or "Apple" in entity_texts
    assert "Steve Jobs" in entity_texts
    assert "Cupertino" in entity_texts
    assert "California" in entity_texts
```

**Test Entity-Chunk Relationships:**
```python
async def test_entity_chunk_relationships():
    # Use test document from previous test
    document_id = "test_entity_extraction"
    
    # Get chunks for document
    chunks = await graph_repo.get_chunks_by_document_id(document_id)
    
    # Get entities for document  
    entities = await graph_repo.get_entities_by_document(document_id)
    
    # Verify MENTIONS relationships exist
    for entity in entities:
        mentions = await graph_repo.get_entity_chunk_relationships(entity.id)
        assert len(mentions) > 0, f"Entity {entity.text} should have MENTIONS relationships"
```

**Test Entity Types Distribution:**
```python
async def test_entity_types_distribution():
    # Analyze entity types across all documents
    entity_stats = await analyze_entity_distribution()
    
    # Verify diverse entity types
    expected_types = ['PERSON', 'ORG', 'GPE', 'PRODUCT', 'DATE']
    for entity_type in expected_types:
        assert entity_type in entity_stats['entity_types'], f"Missing entity type: {entity_type}"
        assert entity_stats['entity_types'][entity_type] > 0, f"No entities of type: {entity_type}"
```

### 2. Vector Store & Semantic Search Testing

**Test Real Embeddings Generation:**
```python
async def test_real_embeddings():
    # Test embedding service
    embedding_service = create_embedding_service(get_settings())
    
    # Generate test embedding
    test_text = "artificial intelligence and machine learning"
    embedding = await embedding_service.embed(test_text)
    
    # Verify real embedding properties
    assert len(embedding) == 384, f"Expected 384-dim embedding, got {len(embedding)}"
    assert not all(x == embedding[0] for x in embedding), "Embedding appears to be constant/mock"
    assert abs(sum(embedding)) > 0.1, "Embedding appears to be zero vector"
```

**Test Semantic Search Quality:**
```python
async def test_semantic_search_quality():
    # Test semantic similarity
    queries_and_expected = [
        ("python programming", ["python", "code", "programming", "software"]),
        ("artificial intelligence", ["AI", "machine learning", "neural", "algorithm"]),
        ("business strategy", ["business", "strategy", "market", "revenue"])
    ]
    
    for query, expected_terms in queries_and_expected:
        results = await search_service.search(query, top_k=5)
        
        # Verify results contain semantically related content
        result_text = " ".join([r.content.lower() for r in results])
        relevant_found = any(term.lower() in result_text for term in expected_terms)
        assert relevant_found, f"Query '{query}' didn't return semantically relevant results"
```

**Test Vector Search Performance:**
```python
async def test_vector_search_performance():
    import time
    
    query = "machine learning algorithms"
    
    # Measure search time
    start_time = time.time()
    results = await search_service.search(query, top_k=10)
    search_time = time.time() - start_time
    
    # Performance assertions
    assert search_time < 2.0, f"Search took {search_time:.2f}s, expected < 2.0s"
    assert len(results) > 0, "Search returned no results"
    assert len(results) <= 10, "Search returned more results than requested"
```

### 3. Knowledge Graph Integrity Testing

**Test Graph Consistency:**
```python
async def test_graph_consistency():
    # Check document-chunk relationships
    documents = await graph_repo.get_all_documents()
    
    for doc in documents:
        chunks = await graph_repo.get_chunks_by_document_id(doc.id)
        
        # Verify every chunk belongs to a document
        for chunk in chunks:
            belongs_to = await graph_repo.get_chunk_document_relationship(chunk.id)
            assert belongs_to is not None, f"Chunk {chunk.id} not linked to document"
            assert belongs_to.document_id == doc.id, f"Chunk document relationship incorrect"
```

**Test Entity-Chunk Relationship Integrity:**
```python
async def test_entity_relationships_integrity():
    # Get all MENTIONS relationships
    mentions_relationships = await graph_repo.get_relationships_by_type("MENTIONS")
    
    for relationship in mentions_relationships:
        # Verify source entity exists
        entity = await graph_repo.get_entity(relationship.source_id)
        assert entity is not None, f"MENTIONS relationship points to non-existent entity"
        
        # Verify target chunk exists
        chunk = await graph_repo.get_chunk(relationship.target_id)
        assert chunk is not None, f"MENTIONS relationship points to non-existent chunk"
        
        # Verify entity text appears in chunk content
        assert entity.text.lower() in chunk.content.lower(), \
            f"Entity '{entity.text}' not found in chunk content"
```

### 4. End-to-End Workflow Testing

**Test Complete Ingestion Pipeline:**
```python
async def test_complete_ingestion_pipeline():
    test_doc = {
        "path": "test_e2e.md",
        "content": """
        # Apple Inc. Business Analysis
        
        Apple Inc. is a technology company founded by Steve Jobs and Steve Wozniak.
        The company is headquartered in Cupertino, California.
        
        Key products include:
        - iPhone (smartphone)
        - MacBook (laptop computer)  
        - iPad (tablet device)
        
        The company's revenue exceeded $365 billion in 2021.
        """,
        "metadata": {"category": "business_analysis", "author": "test"}
    }
    
    # Complete ingestion
    result = await ingestion_service.ingest_document(
        document_id="test_e2e_pipeline",
        content=test_doc["content"],
        metadata=test_doc["metadata"]
    )
    
    # Verify all components
    # 1. Document stored
    document = await graph_repo.get_document(result.document_id)
    assert document is not None
    
    # 2. Chunks created
    chunks = await graph_repo.get_chunks_by_document_id(result.document_id)
    assert len(chunks) > 0
    
    # 3. Entities extracted
    entities = await graph_repo.get_entities_by_document(result.document_id)
    assert len(entities) >= 5  # Apple, Steve Jobs, Steve Wozniak, Cupertino, California
    
    # 4. Vector embeddings generated
    for chunk in chunks:
        embedding = await vector_store.get_embedding(chunk.id)
        assert embedding is not None
        assert len(embedding) == 384
    
    # 5. Search functionality
    search_results = await search_service.search("Apple technology company", top_k=5)
    result_ids = [r.id for r in search_results]
    assert any(chunk.id in result_ids for chunk in chunks), "Ingested content not searchable"
```

**Test Query Interface:**
```python
async def test_query_interface():
    # Test different query types
    test_queries = [
        "stats",
        "search apple technology", 
        "entity Steve Jobs",
        "categories"
    ]
    
    for query in test_queries:
        # This should not raise exceptions
        try:
            # Simulate query interface
            result = await execute_query_command(query)
            assert result is not None, f"Query '{query}' returned None"
        except Exception as e:
            pytest.fail(f"Query '{query}' failed with error: {e}")
```

### 5. Performance & Scale Testing

**Test Large Document Processing:**
```python
async def test_large_document_processing():
    # Create large test document
    large_content = "Apple Inc. " * 1000  # Repeat to create large document
    
    # Measure processing time
    start_time = time.time()
    result = await ingestion_service.ingest_document(
        document_id="test_large_doc",
        content=large_content,
        metadata={}
    )
    processing_time = time.time() - start_time
    
    # Performance assertions
    assert processing_time < 30.0, f"Large document took {processing_time:.2f}s, expected < 30s"
    assert len(result.chunk_ids) > 0, "Large document produced no chunks"
```

**Test Memory Usage:**
```python
async def test_memory_usage():
    import psutil
    import os
    
    # Measure memory before processing
    process = psutil.Process(os.getpid())
    memory_before = process.memory_info().rss / 1024 / 1024  # MB
    
    # Process multiple documents
    for i in range(10):
        await ingestion_service.ingest_document(
            document_id=f"memory_test_{i}",
            content=f"Test document {i} with various entities like Apple Inc. and Steve Jobs.",
            metadata={}
        )
    
    # Measure memory after
    memory_after = process.memory_info().rss / 1024 / 1024  # MB
    memory_increase = memory_after - memory_before
    
    # Memory assertions
    assert memory_increase < 500, f"Memory increased by {memory_increase:.2f}MB, expected < 500MB"
```

## 🎯 VALIDATION COMMANDS

### System Health Check
```bash
# 1. Entity extraction validation
SYNAPSE_MEMGRAPH_PORT=7777 uv run python analyze_knowledge_base.py
# Should show >500 entities with diverse types

# 2. Semantic search validation  
echo "search artificial intelligence" | SYNAPSE_MEMGRAPH_PORT=7777 uv run python query_knowledge_base.py
# Should return AI-related content

# 3. Graph integrity check
echo "stats" | SYNAPSE_MEMGRAPH_PORT=7777 uv run python query_knowledge_base.py
# Should show healthy relationship counts

# 4. Performance check
time echo "search machine learning" | SYNAPSE_MEMGRAPH_PORT=7777 uv run python query_knowledge_base.py
# Should complete in < 2 seconds
```

### Regression Testing
```bash
# Run existing test suite
MEMGRAPH_HOST=localhost uv run pytest -v --tb=short

# Run specific entity extraction tests
MEMGRAPH_HOST=localhost uv run pytest tests/core/test_entity_extractor.py -v

# Run integration tests
MEMGRAPH_HOST=localhost uv run pytest tests/integration/ -v
```

## 🎯 SUCCESS CRITERIA

### Test Coverage
- [ ] 95%+ coverage for entity extraction functionality
- [ ] 90%+ coverage for vector store operations
- [ ] 85%+ coverage for search and query interfaces
- [ ] 80%+ coverage for end-to-end workflows

### Functional Validation
- [ ] All critical user journeys working (ingest → search → query)
- [ ] Entity extraction producing diverse, accurate entities
- [ ] Semantic search returning relevant results
- [ ] Knowledge graph relationships correct and complete
- [ ] Performance within acceptable bounds (< 2s search, < 30s ingestion)

### Regression Prevention
- [ ] Comprehensive test suite for new functionality
- [ ] Integration tests covering critical paths
- [ ] Performance benchmarks established
- [ ] Error handling tested for edge cases

### Production Readiness
- [ ] System stable under load testing
- [ ] Memory usage within reasonable bounds
- [ ] Error recovery mechanisms tested
- [ ] Monitoring and logging validated

## ⚠️ CRITICAL TEST AREAS

### High-Risk Areas
1. **Entity Extraction Integration** - New code, critical functionality
2. **Vector Store Migration** - Data migration risks
3. **Import Dependencies** - Circular import fixes
4. **Performance Impact** - Real embeddings vs mock performance

### Edge Cases to Test
1. **Empty Documents** - How system handles documents with no entities
2. **Special Characters** - Entity extraction with unicode, symbols  
3. **Large Documents** - Performance with very long content
4. **Memory Limits** - Behavior under memory pressure
5. **Network Issues** - Resilience to database connection problems

## 📊 COMPLETION VALIDATION

### Final System Validation
```bash
# 1. Complete system health check
SYNAPSE_MEMGRAPH_PORT=7777 uv run python analyze_knowledge_base.py

# 2. End-to-end user journey test
echo '{"path": "final_test.md", "content": "Microsoft and Google are competing in AI. Bill Gates founded Microsoft in Seattle.", "metadata": {}}' | \
SYNAPSE_MEMGRAPH_PORT=7777 uv run python -m graph_rag.cli.commands.store --stdin --embeddings --replace

# 3. Search for the ingested content
echo "search Microsoft Google AI competition" | SYNAPSE_MEMGRAPH_PORT=7777 uv run python query_knowledge_base.py

# 4. Verify entities were extracted
echo "entity Microsoft" | SYNAPSE_MEMGRAPH_PORT=7777 uv run python query_knowledge_base.py

# 5. Performance benchmark
time echo "search artificial intelligence" | SYNAPSE_MEMGRAPH_PORT=7777 uv run python query_knowledge_base.py
```

**MISSION:** Ensure the Graph-RAG system is production-ready with comprehensive test coverage and validated performance. Your testing validates that critical fixes work correctly and prevents regressions.

**Ready to implement comprehensive testing suite!** 🧪