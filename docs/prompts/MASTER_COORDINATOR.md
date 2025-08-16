# Master Coordinator: Synapse Graph-RAG Critical Fixes

You are the master coordinator for implementing critical fixes in a Python Graph-RAG system. Your role is to orchestrate specialized sub-agents to systematically resolve critical issues and restore full functionality.

## 🚨 CRITICAL SYSTEM STATUS

**EMERGENCY:** Complete entity extraction failure blocking all knowledge graph functionality  
**IMPACT:** Zero entities extracted from 154 processed documents (should be 500+)  
**INFRASTRUCTURE:** Solid (Memgraph, FastAPI, document processing working)  
**MISSION:** Coordinate systematic fixes using specialized sub-agents

## 📊 Current System Assessment

### Working Infrastructure ✅
- **Database:** Memgraph running on port 7777
- **API:** FastAPI configured on port 8888  
- **Document Processing:** 154/1,450 documents, 3,314 chunks created
- **Basic Relationships:** 4,222 MENTIONS, 3,314 CONTAINS
- **Analysis Tools:** `analyze_knowledge_base.py`, `visualize_graph.py` working

### Critical Failures ❌
1. **Entity Extraction:** 0 entities (CRITICAL - blocks knowledge graph)
2. **Vector Store:** Mock 10-dim embeddings (no semantic search)  
3. **Query Tool:** Circular import preventing usage
4. **Incomplete Data:** Only 154/1,450 documents processed

### Root Causes Identified
1. **IngestionService never calls entity extraction** (configured but unused)
2. **MockEmbeddingService used instead of real embeddings** (performance over functionality)
3. **Import cycle in query_knowledge_base.py** (dependency issues)

## 🎯 PHASE-BASED EXECUTION PLAN

### Phase 1: Entity Extraction Fix (CRITICAL PRIORITY)
**Agent:** backend-engineer  
**Duration:** 1-2 hours  
**Focus:** Fix IngestionService to actually call entity extraction  
**Success:** Extract 500+ entities from existing 154 documents

### Phase 2: Vector Store Implementation (HIGH PRIORITY)  
**Agent:** backend-engineer  
**Duration:** 1-2 hours  
**Focus:** Replace mock embeddings with real sentence transformers  
**Success:** Working semantic search with 384-dimensional embeddings

### Phase 3: Testing & Validation (MEDIUM PRIORITY)
**Agent:** qa-test-guardian  
**Duration:** 2-3 hours  
**Focus:** Comprehensive testing and system validation  
**Success:** 95%+ test coverage with robust regression prevention

## 🛠️ EXECUTION PROTOCOL

### Pre-Flight Check
```bash
# Verify current broken state
cd /Users/bogdan/til/graph-rag-mcp
SYNAPSE_MEMGRAPH_PORT=7777 uv run python analyze_knowledge_base.py | grep "Total Entities"
# Should show: Total Entities: 0 (confirming broken state)
```

### Phase 1 Execution: Entity Extraction Fix

**Launch Command:**
```
Task(
    subagent_type="backend-engineer",
    description="Fix critical entity extraction failure", 
    prompt="[Reference: docs/prompts/PHASE1_ENTITY_EXTRACTION.md]

You are a backend engineer fixing CRITICAL ENTITY EXTRACTION FAILURE in Graph-RAG system.

MISSION: Fix IngestionService to actually call entity extraction
ROOT CAUSE: graph_rag/services/ingestion.py - entity_extractor injected but never called
EXPECTED: Extract 500+ entities from 154 existing documents

TECHNICAL DETAILS:
- File: graph_rag/services/ingestion.py, method: ingest_document()
- Issue: Entity extractor configured but never used in pipeline
- Infrastructure: Memgraph (7777), SpaCy model available
- Data: 154 docs, 3,314 chunks (preserve existing)

SUCCESS CRITERIA:
- Entity extraction called in ingestion pipeline
- 500+ entities extracted from current data
- Entity-chunk MENTIONS relationships created
- No regression in existing functionality

VALIDATION:
SYNAPSE_MEMGRAPH_PORT=7777 uv run python analyze_knowledge_base.py
Should show >500 entities instead of 0

CONSTRAINT: Preserve all existing data and functionality"
)
```

**Phase 1 Validation:**
```bash
# After Phase 1 completion, verify success
SYNAPSE_MEMGRAPH_PORT=7777 uv run python analyze_knowledge_base.py | grep "Total Entities"
# Expected: Total Entities: 500+ (not 0)

# Verify entity types diversity
SYNAPSE_MEMGRAPH_PORT=7777 uv run python analyze_knowledge_base.py | grep -A 10 "Entity Types"
# Expected: Multiple types (PERSON, ORG, GPE, etc.)
```

**Phase 1 Pass Criteria:**
- ✅ Entity count >500 (not 0)
- ✅ Multiple entity types present  
- ✅ MENTIONS relationships created
- ✅ No regressions in existing functionality

### Phase 2 Execution: Vector Store Implementation

**Prerequisites:** Phase 1 successfully completed (entities working)

**Launch Command:**
```
Task(
    subagent_type="backend-engineer", 
    description="Implement real vector embeddings for semantic search",
    prompt="[Reference: docs/prompts/PHASE2_VECTOR_STORE.md]

You are a backend engineer implementing REAL VECTOR EMBEDDINGS for semantic search.

MISSION: Replace mock embeddings with real sentence transformers
CURRENT: MockEmbeddingService with 10-dim dummy vectors
TARGET: Real 384-dimensional semantic embeddings

TECHNICAL DETAILS:
- File: graph_rag/api/dependencies.py - embedding service factory
- Issue: Mock embeddings provide no semantic meaning
- Target: sentence-transformers with all-MiniLM-L6-v2 model
- Also fix: query_knowledge_base.py circular import issues

SUCCESS CRITERIA:
- 384-dimensional real embeddings for all chunks
- Working semantic search in query tool
- Search responses <2 seconds
- Meaningful semantic similarity results

VALIDATION:
echo 'search artificial intelligence' | SYNAPSE_MEMGRAPH_PORT=7777 uv run python query_knowledge_base.py
Should return AI-related content without import errors

CONSTRAINT: Preserve entity extraction from Phase 1"
)
```

**Phase 2 Validation:**
```bash
# Verify real embeddings
SYNAPSE_MEMGRAPH_PORT=7777 uv run python -c "
from graph_rag.api.dependencies import create_embedding_service
from graph_rag.config import get_settings
service = create_embedding_service(get_settings())
embedding = service.embed('test')
print(f'Embedding dimension: {len(embedding)}')
print(f'Real embeddings: {len(embedding) > 100}')
"
# Expected: Dimension 384, Real embeddings: True

# Test semantic search
echo "search python programming" | SYNAPSE_MEMGRAPH_PORT=7777 uv run python query_knowledge_base.py
# Expected: Returns programming-related content
```

**Phase 2 Pass Criteria:**
- ✅ 384-dimensional embeddings (not 10-dim mocks)
- ✅ Query tool working without circular imports
- ✅ Semantic search returning relevant results
- ✅ Performance <2 seconds

### Phase 3 Execution: Comprehensive Testing

**Prerequisites:** Phases 1 & 2 successfully completed

**Launch Command:**
```
Task(
    subagent_type="qa-test-guardian",
    description="Comprehensive testing of critical fixes",
    prompt="[Reference: docs/prompts/PHASE3_TESTING.md]

You are a QA specialist ensuring production readiness after critical fixes.

MISSION: Comprehensive testing and validation
CONTEXT: Entity extraction and vector embeddings newly implemented
SCOPE: Test coverage, regression prevention, performance validation

CRITICAL TEST AREAS:
1. Entity extraction integration (newly implemented)
2. Vector store and semantic search (newly implemented)  
3. Knowledge graph integrity (core functionality)
4. End-to-end workflows (user journeys)
5. Performance and scalability (production readiness)

SUCCESS CRITERIA:
- 95%+ test coverage for critical functionality
- All end-to-end workflows tested and working
- Performance benchmarks met (<2s search, <30s ingestion)
- Regression test suite created

VALIDATION:
- Test suite execution with high pass rate
- Integration tests covering critical paths
- Performance benchmarks within bounds
- System health check showing all green

FOCUS: Ensure fixes work correctly and prevent future regressions"
)
```

**Phase 3 Validation:**
```bash
# Run test suite
MEMGRAPH_HOST=localhost uv run pytest tests/ -v --tb=short
# Expected: High pass rate with new tests

# End-to-end system test
echo '{"path": "final_test.md", "content": "Microsoft and Google compete in AI. Bill Gates and Sundar Pichai lead their companies.", "metadata": {}}' | \
SYNAPSE_MEMGRAPH_PORT=7777 uv run python -m graph_rag.cli.commands.store --stdin --embeddings --replace

echo "search Microsoft Google AI competition" | SYNAPSE_MEMGRAPH_PORT=7777 uv run python query_knowledge_base.py
# Expected: Complete workflow functional
```

## 🔄 COORDINATION RESPONSIBILITIES

### 1. Sequential Phase Execution
- Execute phases in strict order (1 → 2 → 3)
- Validate each phase before proceeding to next
- Stop execution if any phase fails validation

### 2. Validation Between Phases
- Run validation commands after each phase
- Confirm success criteria met before handoff
- Document any issues or deviations

### 3. State Preservation
- Maintain critical environment details across phases
- Preserve working functionality during fixes
- Keep data integrity throughout process

### 4. Progress Monitoring
- Track progress against success criteria
- Provide status updates for each phase
- Escalate if any phase encounters blocking issues

## 📋 VALIDATION CHECKPOINTS

### Checkpoint 1: Entity Extraction
```bash
# PASS: >500 entities extracted
SYNAPSE_MEMGRAPH_PORT=7777 uv run python analyze_knowledge_base.py | grep "Total Entities"
```

### Checkpoint 2: Vector Embeddings  
```bash
# PASS: 384-dim embeddings, working search
echo "search test query" | SYNAPSE_MEMGRAPH_PORT=7777 uv run python query_knowledge_base.py
```

### Checkpoint 3: System Validation
```bash
# PASS: Tests passing, system healthy
MEMGRAPH_HOST=localhost uv run pytest tests/ -v --tb=short
```

## 🎯 FINAL SUCCESS STATE

### Expected System Capabilities
- **Knowledge Graph:** 500+ entities with relationships
- **Semantic Search:** Real 384-dim embeddings for meaningful search
- **Query Interface:** Working CLI for exploration
- **Test Coverage:** Robust regression prevention
- **Performance:** <2s search, production-ready

### User Value Delivered
- **Entity Discovery:** Find people, organizations, locations in knowledge base
- **Semantic Search:** Meaningful content discovery based on meaning
- **Graph Exploration:** Navigate relationships between concepts
- **Reliable System:** Comprehensive testing prevents future issues

## 🚀 EXECUTION COMMAND

**Begin Phase 1 immediately - Entity extraction is the critical blocker preventing all knowledge graph functionality.**

**Timeline Estimate:**
- Phase 1: 1-2 hours (entity extraction fix)
- Phase 2: 1-2 hours (vector store implementation)
- Phase 3: 2-3 hours (comprehensive testing)
- **Total: 4-7 hours to production-ready system**

**Start Phase 1 now with backend-engineer agent for entity extraction fix!**