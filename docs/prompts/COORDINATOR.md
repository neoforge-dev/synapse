# Phase Coordinator Prompt - Synapse Graph-RAG Critical Fixes

You are coordinating critical fixes for a Python Graph-RAG system with **COMPLETE ENTITY EXTRACTION FAILURE**. Your role is to orchestrate sub-agents and maintain overall system state.

## 🚨 CRITICAL SITUATION

**ZERO entities extracted from 154 processed documents** - the entire knowledge graph value proposition is broken.

## 📊 Current System State (Baseline)

### Infrastructure Status ✅
- **Memgraph Database:** Running on port 7777
- **FastAPI Server:** Configured for port 8888  
- **Document Processing:** 154/1,450 documents processed
- **Chunk Creation:** 3,314 chunks successfully created
- **Basic Relationships:** 4,222 MENTIONS, 3,314 CONTAINS working

### Analysis Tools (Working) ✅
- `analyze_knowledge_base.py` - System statistics and validation
- `visualize_graph.py` - Network visualization generation
- `query_knowledge_base.py` - Interactive CLI queries (needs fix)

### Critical Failures ❌
- **Entity Extraction:** 0 entities (should be 500+)
- **Vector Store:** Mock 10-dim embeddings (no semantic search)
- **Query Tool:** Circular import preventing usage
- **Batch Ingestion:** Incomplete (154/1,450 documents)

## 🎯 PHASE-BASED COORDINATION PLAN

### Phase 1: Entity Extraction Fix (CRITICAL PRIORITY)
**Agent:** backend-engineer  
**Focus:** Fix IngestionService entity extraction integration  
**Root Cause:** `graph_rag/services/ingestion.py` - entity_extractor injected but never called  
**Success Criteria:** Extract 500+ entities from existing 154 documents

### Phase 2: Vector Store Implementation (HIGH PRIORITY)  
**Agent:** backend-engineer  
**Focus:** Replace mock embeddings with real sentence transformers  
**Success Criteria:** Working semantic search with real 384-dim embeddings

### Phase 3: System Completion (MEDIUM PRIORITY)
**Agent:** general-purpose + qa-test-guardian  
**Focus:** Complete batch ingestion + comprehensive testing  
**Success Criteria:** All 1,450 documents processed with robust test coverage

## 🛠️ YOUR COORDINATION RESPONSIBILITIES

### 1. Phase Execution
Execute phases sequentially using the Task tool with specialized agents:
```
Phase 1: Task(subagent_type="backend-engineer", description="Fix entity extraction", prompt="[Phase 1 Prompt]")
Phase 2: Task(subagent_type="backend-engineer", description="Vector store fix", prompt="[Phase 2 Prompt]") 
Phase 3: Task(subagent_type="qa-test-guardian", description="Testing", prompt="[Phase 3 Prompt]")
```

### 2. Validation Between Phases
After each phase, validate success before proceeding:
```bash
# Phase 1 Validation - Entity Extraction
SYNAPSE_MEMGRAPH_PORT=7777 uv run python analyze_knowledge_base.py
# Should show >0 entities, expect 500+

# Phase 2 Validation - Vector Search  
echo "search test query" | SYNAPSE_MEMGRAPH_PORT=7777 uv run python query_knowledge_base.py
# Should work without circular import errors

# Phase 3 Validation - Complete System
# Full 1,450 documents processed with comprehensive tests passing
```

### 3. State Preservation
Maintain these critical environment details across all phases:
- **Ports:** API 8888, Memgraph 7777
- **Data:** 154 documents, 3,314 chunks (preserve existing)
- **Working Tools:** analyze_knowledge_base.py, visualize_graph.py
- **Configuration:** SYNAPSE_MEMGRAPH_PORT=7777 for all commands

## 📋 PHASE 1 EXECUTION

**Immediate Action:** Launch backend-engineer agent for entity extraction fix.

**Context for Agent:**
- Root cause identified: IngestionService.ingest_document() never calls self.entity_extractor
- Entity extractor is properly configured and injected but unused
- SpaCy model (en_core_web_sm) should be available
- Expected outcome: Extract 500+ entities from existing 154 documents

**Success Validation:**
```bash
# Before fix: Shows 0 entities
SYNAPSE_MEMGRAPH_PORT=7777 uv run python analyze_knowledge_base.py

# After fix: Should show 500+ entities
# Entity types should include: PERSON, ORG, GPE, PRODUCT, etc.
# Entity-chunk MENTIONS relationships should be created
```

## 🔄 HANDOFF PROTOCOL

### Phase Completion Criteria
- **Phase 1 Complete:** >500 entities extracted, entity-chunk relationships created
- **Phase 2 Complete:** Real embeddings working, semantic search functional  
- **Phase 3 Complete:** All documents processed, comprehensive tests passing

### Context Handoff Information
Pass this to each agent:
1. **Working Environment:** `/Users/bogdan/til/graph-rag-mcp`
2. **Custom Ports:** API 8888, Memgraph 7777  
3. **Existing Data:** 154 docs, 3,314 chunks (preserve)
4. **Analysis Tools:** Available for validation
5. **Configuration:** Use SYNAPSE_MEMGRAPH_PORT=7777

### Emergency Fallback
If any phase fails critically:
1. Document the specific failure mode
2. Preserve existing working functionality 
3. Consider alternative implementation approaches
4. Escalate with detailed technical analysis

## 🚀 START PHASE 1

Begin immediately with backend-engineer agent for entity extraction fix. This is the highest priority issue blocking all knowledge graph functionality.

**Expected Timeline:**
- Phase 1: 1-2 hours (critical entity extraction fix)
- Phase 2: 1-2 hours (vector store implementation)  
- Phase 3: 2-3 hours (completion and testing)

**Success Indicator:** After Phase 1, `analyze_knowledge_base.py` should show hundreds of extracted entities instead of zero.