# Context Preservation Strategy

This document outlines the strategy for maintaining critical system state and preventing context rot during multi-agent execution of Synapse Graph-RAG fixes.

## 🎯 Context Management Objectives

**Primary Goal:** Maintain system coherence across multiple specialized agents  
**Key Challenge:** Prevent context rot while enabling deep technical focus  
**Strategy:** Structured handoffs with preserved state and validation checkpoints

## 📊 Critical State Information

### Environment State (Preserve Across All Phases)
```json
{
  "working_directory": "/Users/bogdan/til/graph-rag-mcp",
  "database_port": 7777,
  "api_port": 8888,
  "environment_prefix": "SYNAPSE_MEMGRAPH_PORT=7777",
  "custom_configuration": "Custom ports for isolation"
}
```

### Data State (Baseline to Preserve)
```json
{
  "documents_processed": 154,
  "total_documents": 1450,
  "chunks_created": 3314,
  "basic_relationships": {
    "MENTIONS": 4222,
    "CONTAINS": 3314,
    "MENTIONS_TOPIC": 3284,
    "HAS_TOPIC": 148
  },
  "entities_current": 0,
  "entities_expected": 500
}
```

### Analysis Tools (Available for Validation)
```json
{
  "primary_analysis": "analyze_knowledge_base.py",
  "visualization": "visualize_graph.py", 
  "interactive_query": "query_knowledge_base.py",
  "dashboard": "visualizations/dashboard.html",
  "validation_command": "SYNAPSE_MEMGRAPH_PORT=7777 uv run python analyze_knowledge_base.py"
}
```

### Configuration State (Maintain Consistency)
```json
{
  "ports": {
    "memgraph": 7777,
    "api": 8888
  },
  "models": {
    "spacy": "en_core_web_sm",
    "embeddings": "all-MiniLM-L6-v2"
  },
  "services": {
    "entity_extractor_type": "spacy",
    "embedding_provider": "sentence-transformers",
    "vector_store_type": "simple"
  }
}
```

## 🔄 Context Handoff Protocol

### Phase 1 → Phase 2 Handoff
**What Phase 1 Delivers:**
- Entity extraction integration implemented
- 500+ entities extracted from existing data
- Entity-chunk MENTIONS relationships created
- All existing functionality preserved

**What Phase 2 Receives:**
```json
{
  "phase_1_status": "complete",
  "entities_extracted": 500+,
  "entity_types": ["PERSON", "ORG", "GPE", "PRODUCT"],
  "new_relationships": "MENTIONS",
  "data_integrity": "preserved",
  "working_functionality": ["document_processing", "chunking", "entity_extraction"],
  "validation_passed": true
}
```

### Phase 2 → Phase 3 Handoff  
**What Phase 2 Delivers:**
- Real 384-dimensional embeddings
- Working semantic search
- Query tool functional (circular imports fixed)
- All Phase 1 achievements preserved

**What Phase 3 Receives:**
```json
{
  "phase_2_status": "complete",
  "embedding_dimension": 384,
  "semantic_search": "functional",
  "query_tool": "working",
  "phase_1_preserved": true,
  "entities_count": 500+,
  "validation_passed": true
}
```

## 📋 State Validation Commands

### Universal Health Check (All Phases)
```bash
# System overview - use after any phase
SYNAPSE_MEMGRAPH_PORT=7777 uv run python analyze_knowledge_base.py

# Expected output progression:
# Phase 0 (broken): Total Entities: 0
# Phase 1: Total Entities: 500+
# Phase 2: Total Entities: 500+, Real embeddings working
# Phase 3: All functionality + comprehensive tests
```

### Environment Verification
```bash
# Verify working directory
pwd
# Expected: /Users/bogdan/til/graph-rag-mcp

# Verify ports available
netstat -an | grep 7777  # Memgraph
netstat -an | grep 8888  # API (if running)

# Verify Python environment
uv run python --version
uv run python -c "import graph_rag; print('Package available')"
```

### Data Integrity Check
```bash
# Document count should remain stable
SYNAPSE_MEMGRAPH_PORT=7777 uv run python -c "
import asyncio
from graph_rag.infrastructure.graph_stores.memgraph_store import MemgraphGraphRepository
from graph_rag.config import get_settings

async def check_data():
    settings = get_settings()
    settings.memgraph_port = 7777
    repo = MemgraphGraphRepository(settings_obj=settings)
    
    docs_query = 'MATCH (d:Document) RETURN count(d) as count'
    chunks_query = 'MATCH (c:Chunk) RETURN count(c) as count'
    
    docs_result = await repo.execute_query(docs_query)
    chunks_result = await repo.execute_query(chunks_query)
    
    print(f'Documents: {docs_result[0][\"count\"]}')
    print(f'Chunks: {chunks_result[0][\"count\"]}')
    
    await repo.close()

asyncio.run(check_data())
"
# Expected: Documents: 154, Chunks: 3314 (stable across phases)
```

## 🛡️ Context Rot Prevention

### 1. Atomic Task Design
**Principle:** Each agent gets single, focused technical challenge  
**Benefit:** Deep focus without cognitive overload  
**Implementation:** Separate prompts for entity extraction, vector store, testing

### 2. Clear Success Criteria  
**Principle:** Measurable outcomes for each phase  
**Benefit:** Objective validation before proceeding  
**Implementation:** Specific metrics (entity count, embedding dimension, test coverage)

### 3. Progressive Validation
**Principle:** Test each phase before moving to next  
**Benefit:** Catch issues early, prevent cascading failures  
**Implementation:** Validation checkpoints with specific commands

### 4. State Documentation
**Principle:** Critical information preserved in documents  
**Benefit:** Context survives agent transitions  
**Implementation:** JSON state objects, validation commands, config preservation

## 📊 Context Loss Prevention

### Information That Must Survive Agent Transitions
1. **Working Directory:** `/Users/bogdan/til/graph-rag-mcp`
2. **Port Configuration:** API 8888, Memgraph 7777
3. **Data Baseline:** 154 docs, 3,314 chunks (preserve)
4. **Analysis Tools:** Available for validation
5. **Phase Progress:** What's been completed successfully

### Information Agents Don't Need
1. **Implementation History:** How previous phases were implemented
2. **Code Archaeology:** Understanding all existing code
3. **Future Phases:** Agents focus only on their current phase
4. **Alternative Approaches:** Stick to proven solutions

### Critical Commands for Every Agent
```bash
# 1. Navigate to working directory
cd /Users/bogdan/til/graph-rag-mcp

# 2. Check system health
SYNAPSE_MEMGRAPH_PORT=7777 uv run python analyze_knowledge_base.py

# 3. Verify data integrity (if needed)
# Document and chunk counts should remain stable

# 4. Test basic functionality
echo "stats" | SYNAPSE_MEMGRAPH_PORT=7777 uv run python query_knowledge_base.py
```

## 🎯 Success Handoff Protocol

### Final Context State (All Phases Complete)
```json
{
  "system_status": "production_ready",
  "critical_fixes": {
    "entity_extraction": {
      "status": "implemented",
      "entities_count": 500+,
      "types": ["PERSON", "ORG", "GPE", "PRODUCT", "DATE"],
      "relationships": "MENTIONS created"
    },
    "vector_store": {
      "status": "implemented", 
      "embedding_dimension": 384,
      "semantic_search": "functional",
      "performance": "<2s response"
    },
    "testing": {
      "status": "complete",
      "coverage": "95%+",
      "regression_prevention": "implemented"
    }
  },
  "preserved_functionality": {
    "document_processing": "working",
    "chunking": "working", 
    "basic_relationships": "working",
    "analysis_tools": "working",
    "configuration": "preserved"
  },
  "validation_commands": {
    "health_check": "SYNAPSE_MEMGRAPH_PORT=7777 uv run python analyze_knowledge_base.py",
    "search_test": "echo 'search test' | SYNAPSE_MEMGRAPH_PORT=7777 uv run python query_knowledge_base.py",
    "test_suite": "MEMGRAPH_HOST=localhost uv run pytest tests/ -v"
  },
  "next_steps": [
    "Complete remaining 1,296 document ingestion",
    "Explore knowledge graph with analysis tools", 
    "Use semantic search for content discovery",
    "Consider advanced features"
  ]
}
```

### User Handoff Message Template
```
🎯 CONTEXT PRESERVED SUCCESSFULLY

Your Synapse Graph-RAG system has been systematically upgraded:

PHASE 1 ✅: Entity extraction implemented
- 500+ entities extracted from your knowledge base
- Rich entity-chunk relationships created

PHASE 2 ✅: Real semantic search enabled  
- 384-dimensional embeddings replace mock vectors
- Meaningful semantic similarity search working

PHASE 3 ✅: Comprehensive testing completed
- 95%+ test coverage prevents regressions
- All critical workflows validated

PRESERVED THROUGHOUT:
- All 154 documents and 3,314 chunks
- Custom port configuration (API: 8888, Memgraph: 7777) 
- Analysis tools and visualizations
- Existing working functionality

YOUR SYSTEM IS NOW PRODUCTION-READY! 🚀

Validate with: SYNAPSE_MEMGRAPH_PORT=7777 uv run python analyze_knowledge_base.py
```

This context preservation strategy ensures that critical system state survives agent transitions while enabling each agent to focus deeply on their specialized technical domain.