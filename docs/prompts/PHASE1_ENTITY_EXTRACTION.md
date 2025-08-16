# Backend-Engineer: Critical Entity Extraction Fix

You are a backend engineer tasked with fixing **CRITICAL ENTITY EXTRACTION FAILURE** in a Graph-RAG system. This is the highest priority issue blocking all knowledge graph functionality.

## 🚨 CRITICAL TECHNICAL ISSUE

**Problem:** ZERO entities extracted from 154 processed documents  
**Root Cause:** `IngestionService` has entity extractor injected but **NEVER CALLS IT**  
**Impact:** Complete knowledge graph functionality failure  
**Expected Fix Result:** Extract 500+ entities from existing data

## 📂 Technical Context

### Environment
- **Working Directory:** `/Users/bogdan/til/graph-rag-mcp`
- **Database:** Memgraph on port 7777  
- **API:** FastAPI on port 8888
- **Data Status:** 154 documents processed, 3,314 chunks created

### Core Issue Location
**File:** `graph_rag/services/ingestion.py`  
**Method:** `IngestionService.ingest_document()`  
**Problem:** Entity extractor is injected in `__init__()` but never used

### Current Working Flow
```
Document → Chunks → Basic Relationships → Storage
             ↓
    [MISSING: Entity Extraction Step]
             ↓
    [MISSING: Entity-Chunk MENTIONS Links]
```

### Expected Working Flow  
```
Document → Chunks → Entity Extraction → Entity-Chunk Links → Storage
             ↓              ↓                    ↓
     Vector Store     Entities Stored      MENTIONS Created
```

## 🛠️ YOUR SPECIFIC MISSION

### 1. Analyze Current Entity Integration
**Diagnostic Command:**
```bash
cd /Users/bogdan/til/graph-rag-mcp
grep -r "entity_extractor" graph_rag/services/ingestion.py
```

**Expected Findings:**
- Entity extractor parameter in `__init__()`
- Entity extractor stored as `self.entity_extractor`  
- NO calls to entity extraction in `ingest_document()` method

### 2. Identify Integration Point
**Examine:** `graph_rag/services/ingestion.py` method `ingest_document()`

**Current Flow Analysis:**
1. Document processing and chunking ✅
2. **MISSING:** Entity extraction from chunks
3. **MISSING:** Entity-chunk relationship creation
4. Vector embedding generation ✅
5. Storage in graph and vector stores ✅

### 3. Implement Entity Extraction Integration

**Technical Requirements:**
1. **Call Entity Extraction:** Add entity extraction step after chunk creation
2. **Process Per Chunk:** Extract entities from each chunk's content
3. **Store Entities:** Save entities to graph repository  
4. **Create Relationships:** Link entities to chunks via MENTIONS relationships
5. **Handle Errors:** Graceful failure without breaking existing flow

**Implementation Approach:**
```python
# After chunk creation in ingest_document(), add:
for chunk in chunks:
    # Extract entities from chunk content
    entities = await self.entity_extractor.extract(chunk.content)
    
    # Store entities and create relationships
    for entity in entities:
        # Store entity in graph
        entity_id = await self.graph_store.add_entity(entity)
        
        # Create MENTIONS relationship between entity and chunk
        relationship = Relationship(
            source_id=entity_id,
            target_id=chunk.id,
            type="MENTIONS"
        )
        await self.graph_store.add_relationship(relationship)
```

### 4. Verify SpaCy Configuration
**Check Model Availability:**
```bash
python -c "import spacy; nlp = spacy.load('en_core_web_sm'); print('SpaCy model loaded successfully')"
```

**If Model Missing:**
```bash
python -m spacy download en_core_web_sm
```

### 5. Test Entity Extraction Directly
**Verify Extractor Works:**
```bash
python -c "
from graph_rag.core.entity_extractor import SpacyEntityExtractor
extractor = SpacyEntityExtractor()
result = extractor.extract('Apple Inc. is located in Cupertino, California.')
print(f'Entities found: {len(result)}')
for entity in result:
    print(f'  {entity.text} ({entity.label})')
"
```

## 🧪 VALIDATION PROCESS

### Before Implementation
```bash
# Should show 0 entities (broken state)
SYNAPSE_MEMGRAPH_PORT=7777 uv run python analyze_knowledge_base.py
```

### After Implementation  
```bash
# Should show 500+ entities (fixed state)
SYNAPSE_MEMGRAPH_PORT=7777 uv run python analyze_knowledge_base.py
```

### Expected Results
- **Total Entities:** 500-1000+ (from 154 documents)
- **Entity Types:** PERSON, ORG, GPE, PRODUCT, DATE, MONEY, etc.
- **Relationships:** Thousands of MENTIONS between entities and chunks
- **Entity Distribution:** Varied across different documents and chunks

### Test New Document Ingestion
```bash
# Test entity extraction on new document
echo '{"path": "test.md", "content": "Apple Inc. is a technology company founded by Steve Jobs in Cupertino, California.", "metadata": {}}' | \
SYNAPSE_MEMGRAPH_PORT=7777 uv run python -m graph_rag.cli.commands.store --stdin --embeddings --replace
```

**Expected:** Should extract entities: Apple Inc. (ORG), Steve Jobs (PERSON), Cupertino (GPE), California (GPE)

## 🎯 SUCCESS CRITERIA

### Technical Success
- [ ] Entity extraction called in ingestion pipeline
- [ ] Entities stored in graph repository
- [ ] Entity-chunk MENTIONS relationships created
- [ ] No errors in existing document/chunk processing
- [ ] SpaCy model properly configured and working

### Functional Success  
- [ ] 500+ entities extracted from existing 154 documents
- [ ] Multiple entity types represented (PERSON, ORG, GPE, etc.)
- [ ] Entity-chunk relationships searchable in graph
- [ ] `analyze_knowledge_base.py` shows non-zero entity count
- [ ] New document ingestion includes entity extraction

### Performance Success
- [ ] No significant slowdown in ingestion speed
- [ ] Memory usage remains reasonable
- [ ] Error handling prevents failures from breaking ingestion

## ⚠️ CRITICAL CONSTRAINTS

### DO NOT BREAK
- **Existing document processing pipeline**
- **Chunk creation and storage**  
- **Vector embedding generation**
- **Basic relationship creation (CONTAINS, etc.)**
- **API and CLI functionality**

### MAINTAIN COMPATIBILITY
- **Custom port configuration (7777, 8888)**
- **Existing analysis tools**
- **Current data (154 docs, 3,314 chunks)**
- **Configuration and settings**

## 🔄 ERROR HANDLING

### Entity Extraction Failures
- Log warnings but continue processing
- Don't fail entire ingestion for entity extraction errors
- Provide meaningful error messages
- Graceful degradation when SpaCy model unavailable

### Relationship Creation Failures
- Log relationship creation errors
- Continue with remaining entities
- Don't block document storage for relationship failures

## 📊 COMPLETION VALIDATION

When complete, run comprehensive validation:
```bash
# 1. Check entity extraction success
SYNAPSE_MEMGRAPH_PORT=7777 uv run python analyze_knowledge_base.py

# 2. Verify entity types and counts
# Should show entity statistics with multiple types

# 3. Test query functionality (if working)
echo "stats" | SYNAPSE_MEMGRAPH_PORT=7777 uv run python query_knowledge_base.py

# 4. Test new ingestion with entities
# Should extract entities from new content
```

**MISSION CRITICAL:** This fix unlocks the entire knowledge graph value proposition. The system infrastructure is solid - you just need to connect the entity extraction that's already configured but not being used.

**Ready to implement entity extraction integration in IngestionService!** 🚀