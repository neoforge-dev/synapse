# Backend-Engineer: Vector Store & Semantic Search Implementation

You are a backend engineer tasked with implementing **REAL VECTOR EMBEDDINGS** to enable semantic search in a Graph-RAG system. This is the second critical priority after entity extraction.

## 🎯 TECHNICAL MISSION

**Problem:** Using mock 10-dimensional embeddings (no real semantic search)  
**Goal:** Implement real 384-dimensional sentence transformer embeddings  
**Impact:** Enable production-ready semantic search capabilities  
**Expected Result:** Sub-second semantic search with real embeddings

## 📊 Current State (Post Phase 1)

### What Should Be Working ✅
- **Entity Extraction:** 500+ entities extracted from 154 documents (Phase 1 success)
- **Infrastructure:** Memgraph (7777), FastAPI (8888), document processing
- **Data:** 154 documents, 3,314 chunks, entity-chunk relationships

### Current Limitations ❌
- **Mock Embeddings:** 10-dimensional dummy vectors (no semantic meaning)
- **No Semantic Search:** Vector similarity meaningless with mock data
- **Query Tool Broken:** Circular import preventing usage
- **Limited RAG:** Cannot perform real retrieval-augmented generation

## 🛠️ TECHNICAL REQUIREMENTS

### 1. Replace Mock Embedding Service

**Current Implementation:**
- **File:** `graph_rag/api/dependencies.py`
- **Class:** `MockEmbeddingService` with 10-dimensional dummy vectors
- **Issue:** No real semantic meaning in vector space

**Target Implementation:**
- **Service:** Real sentence-transformers embedding service
- **Model:** `all-MiniLM-L6-v2` (384 dimensions)
- **Performance:** Production-ready with proper caching

### 2. Configure Real Vector Store

**Current Vector Store:**
- **Type:** SimpleVectorStore with mock embeddings
- **Dimensions:** 10 (meaningless)
- **Performance:** Fast but no semantic value

**Target Vector Store:**
- **Type:** SimpleVectorStore with real embeddings  
- **Dimensions:** 384 (semantic meaning)
- **Performance:** Real semantic similarity search

### 3. Fix Query Tool Circular Imports

**Current Issue:**
- **File:** `query_knowledge_base.py`
- **Problem:** Circular import with GraphRAG engine
- **Impact:** Interactive querying non-functional

**Target Solution:**
- **Approach:** Resolve import dependencies or simplify interface
- **Result:** Working semantic search in query tool

## 📂 Key Files to Modify

### Primary Configuration
- **`graph_rag/api/dependencies.py`** - Embedding service factory
- **`graph_rag/config/__init__.py`** - Embedding provider settings

### Query Interface
- **`query_knowledge_base.py`** - Fix circular imports
- **`graph_rag/core/graph_rag_engine.py`** - Engine dependencies

### Vector Store  
- **`graph_rag/infrastructure/vector_stores/simple_vector_store.py`** - Configuration

## 🔧 IMPLEMENTATION APPROACH

### Step 1: Configure Sentence Transformers

**Check Current Configuration:**
```bash
grep -r "embedding_provider" graph_rag/config/__init__.py
grep -r "MockEmbeddingService" graph_rag/api/dependencies.py
```

**Expected Configuration:**
```python
# In settings
embedding_provider: str = Field(
    "sentence-transformers",  # Change from "mock"
    description="Provider for embedding models"
)
```

### Step 2: Update Dependency Factory

**Current Factory in `dependencies.py`:**
```python
def create_embedding_service(settings: Settings) -> EmbeddingService:
    # Currently returns MockEmbeddingService
```

**Target Factory:**
```python
def create_embedding_service(settings: Settings) -> EmbeddingService:
    if settings.embedding_provider == "sentence-transformers":
        from graph_rag.services.embedding_service import SentenceTransformerEmbeddingService
        return SentenceTransformerEmbeddingService(
            model_name=settings.vector_store_embedding_model
        )
    # Fallback to mock for testing
    return MockEmbeddingService(dimension=384)
```

### Step 3: Regenerate Embeddings for Existing Data

**Approach:**
1. **Identify Existing Chunks:** Find all 3,314 chunks with mock embeddings
2. **Generate Real Embeddings:** Process each chunk with sentence transformers  
3. **Update Vector Store:** Replace mock vectors with real embeddings
4. **Preserve Metadata:** Keep all chunk metadata and relationships

**Implementation Strategy:**
```python
# Migration script or service method
async def migrate_to_real_embeddings():
    # Get all existing chunks
    chunks = await graph_store.get_all_chunks()
    
    # Process in batches for performance
    for batch in chunks.batch(100):
        embeddings = []
        for chunk in batch:
            # Generate real embedding
            embedding = await embedding_service.embed(chunk.content)
            embeddings.append((chunk.id, embedding))
        
        # Update vector store
        await vector_store.update_embeddings(embeddings)
```

### Step 4: Fix Query Tool Circular Imports

**Analyze Import Cycle:**
```bash
python -c "import query_knowledge_base" 2>&1 | head -20
```

**Common Solutions:**
1. **Lazy Imports:** Move imports inside functions
2. **Interface Abstraction:** Create simplified query interface  
3. **Dependency Injection:** Pass services rather than importing

**Target Approach:**
```python
# Instead of importing GraphRAGEngine directly
# Use dependency injection or simplified interface
async def handle_search(graph_repo, query: str):
    # Direct graph query instead of full engine
    search_query = """
    MATCH (c:Chunk)
    WHERE toLower(c.content) CONTAINS toLower($query)
    RETURN c.content as content, c.id as chunk_id
    LIMIT 10
    """
    results = await graph_repo.execute_query(search_query, {"query": query})
    return results
```

## 🧪 TESTING & VALIDATION

### Before Implementation
```bash
# Check current embedding service
python -c "
from graph_rag.api.dependencies import create_embedding_service
from graph_rag.config import get_settings
settings = get_settings()
service = create_embedding_service(settings)
print(f'Service type: {type(service).__name__}')
print(f'Embedding dimension: {service.dimension if hasattr(service, \"dimension\") else \"unknown\"}')
"
```

### Test Real Embeddings
```bash
# Test sentence transformer loading
python -c "
from sentence_transformers import SentenceTransformer
model = SentenceTransformer('all-MiniLM-L6-v2')
embedding = model.encode('test sentence')
print(f'Embedding dimension: {len(embedding)}')
print(f'Embedding type: {type(embedding)}')
"
```

### Validate Semantic Search
```bash
# Test semantic similarity
python -c "
from sentence_transformers import SentenceTransformer
import numpy as np

model = SentenceTransformer('all-MiniLM-L6-v2')
query = 'artificial intelligence'
doc1 = 'machine learning algorithms'
doc2 = 'cooking recipes'

query_emb = model.encode(query)
doc1_emb = model.encode(doc1)
doc2_emb = model.encode(doc2)

sim1 = np.dot(query_emb, doc1_emb) / (np.linalg.norm(query_emb) * np.linalg.norm(doc1_emb))
sim2 = np.dot(query_emb, doc2_emb) / (np.linalg.norm(query_emb) * np.linalg.norm(doc2_emb))

print(f'AI vs ML similarity: {sim1:.3f}')
print(f'AI vs cooking similarity: {sim2:.3f}')
print(f'Semantic search working: {sim1 > sim2}')
"
```

### After Implementation
```bash
# Test query tool functionality
echo "search artificial intelligence" | SYNAPSE_MEMGRAPH_PORT=7777 uv run python query_knowledge_base.py

# Should return semantically relevant chunks about AI/technology
```

## 🎯 SUCCESS CRITERIA

### Technical Success
- [ ] Real sentence transformer embeddings configured
- [ ] 384-dimensional vectors for all chunks
- [ ] Query tool working without circular import errors
- [ ] Vector similarity search functional
- [ ] Embedding service properly integrated

### Functional Success
- [ ] Semantic search returns relevant results
- [ ] Query tool interactive interface working
- [ ] Vector similarity meaningful (AI content ranks higher for AI queries)
- [ ] Search response times < 2 seconds
- [ ] All existing functionality preserved

### Performance Success
- [ ] Embedding generation < 1 second per chunk
- [ ] Vector search < 500ms for typical queries
- [ ] Memory usage reasonable (< 2GB for full dataset)
- [ ] Proper caching to avoid recomputation

## 🔄 MIGRATION STRATEGY

### Existing Data Handling
1. **Preserve All Data:** Don't lose any documents, chunks, or relationships
2. **Gradual Migration:** Process embeddings in batches
3. **Rollback Plan:** Keep ability to revert to mock if needed
4. **Validation:** Verify each batch before proceeding

### Performance Optimization
1. **Batch Processing:** Handle multiple chunks at once
2. **Caching:** Cache model loading and embeddings
3. **Async Processing:** Use async for I/O operations  
4. **Progress Tracking:** Monitor migration progress

## ⚠️ CRITICAL CONSTRAINTS

### DO NOT BREAK
- **Entity extraction functionality (Phase 1 success)**
- **Existing document and chunk data**
- **Graph relationships and structure**
- **Analysis tools (analyze_knowledge_base.py, etc.)**
- **API and CLI basic functionality**

### MAINTAIN COMPATIBILITY
- **Custom port configuration (7777, 8888)**
- **Environment variable settings**
- **Existing data integrity**
- **Docker and deployment configuration**

## 📊 COMPLETION VALIDATION

### Comprehensive Testing
```bash
# 1. Verify real embeddings active
SYNAPSE_MEMGRAPH_PORT=7777 uv run python -c "
from graph_rag.api.dependencies import create_embedding_service
from graph_rag.config import get_settings
service = create_embedding_service(get_settings())
embedding = service.embed('test')
print(f'Embedding dimension: {len(embedding)}')
print(f'Real embeddings: {len(embedding) > 100}')
"

# 2. Test semantic search functionality  
echo "search python programming" | SYNAPSE_MEMGRAPH_PORT=7777 uv run python query_knowledge_base.py

# 3. Verify vector similarity makes sense
# Should return programming/technology content for programming queries

# 4. Performance benchmark
time echo "search machine learning" | SYNAPSE_MEMGRAPH_PORT=7777 uv run python query_knowledge_base.py
```

### Quality Validation
- **Semantic Relevance:** AI queries return AI content
- **Performance:** Sub-second search responses
- **Accuracy:** Top results are semantically related
- **Coverage:** All chunks have real embeddings

**MISSION:** Transform the system from mock embeddings to production-ready semantic search. This enables the full RAG (Retrieval-Augmented Generation) value proposition.

**Ready to implement real vector embeddings and semantic search!** 🚀