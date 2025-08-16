# Claude Code Prompt Engineering System

This directory contains an optimal prompt engineering strategy for implementing critical Synapse Graph-RAG fixes using Claude Code's sub-agent system.

## 🎯 System Overview

**Problem:** Single massive prompt causes context rot and incomplete implementation  
**Solution:** Coordinated multi-agent approach with progressive validation  
**Result:** Systematic fixes with deep technical focus and maintained context

## 📂 Prompt Structure

### Core Coordination
- **`MASTER_COORDINATOR.md`** - Main orchestration prompt for Claude Code
- **`COORDINATOR.md`** - Phase coordination and state management
- **`VALIDATION_PROTOCOL.md`** - Success criteria and handoff procedures
- **`CONTEXT_PRESERVATION.md`** - State preservation across agent transitions

### Specialized Agent Prompts
- **`PHASE1_ENTITY_EXTRACTION.md`** - Backend engineer: Fix entity extraction
- **`PHASE2_VECTOR_STORE.md`** - Backend engineer: Implement real embeddings  
- **`PHASE3_TESTING.md`** - QA test guardian: Comprehensive validation

## 🚀 Usage Instructions

### Quick Start (Copy-Paste Ready)
```
Use the MASTER_COORDINATOR.md prompt directly in Claude Code to begin systematic fixes:

1. Copy content from MASTER_COORDINATOR.md
2. Paste into Claude Code
3. System will automatically coordinate Phase 1 → 2 → 3
4. Each phase uses specialized sub-agents
5. Progressive validation ensures success
```

### Manual Phase Execution
If you prefer manual control, execute phases individually:

#### Phase 1: Entity Extraction (CRITICAL)
```
Use: PHASE1_ENTITY_EXTRACTION.md with backend-engineer agent
Goal: Fix IngestionService to extract entities
Success: 500+ entities from 154 documents
```

#### Phase 2: Vector Store (HIGH PRIORITY)  
```
Use: PHASE2_VECTOR_STORE.md with backend-engineer agent
Goal: Replace mock embeddings with real semantic search
Success: 384-dim embeddings, working search
```

#### Phase 3: Testing (VALIDATION)
```
Use: PHASE3_TESTING.md with qa-test-guardian agent  
Goal: Comprehensive testing and validation
Success: 95%+ coverage, production ready
```

## 🔧 Technical Context

### Current System State
- **Documents:** 154/1,450 processed, 3,314 chunks created
- **Entities:** 0 extracted (CRITICAL FAILURE)
- **Embeddings:** Mock 10-dimensional (no semantic search)
- **Infrastructure:** Working (Memgraph 7777, FastAPI 8888)

### Root Causes Identified
1. **Entity Extraction:** IngestionService never calls entity_extractor
2. **Vector Store:** MockEmbeddingService used instead of real embeddings
3. **Query Tool:** Circular import preventing usage

### Expected Results
- **Phase 1:** 500+ entities extracted, knowledge graph functional
- **Phase 2:** Real semantic search with 384-dim embeddings
- **Phase 3:** Production-ready system with comprehensive tests

## 📋 Validation Commands

### System Health Check (Use After Any Phase)
```bash
cd /Users/bogdan/til/graph-rag-mcp
SYNAPSE_MEMGRAPH_PORT=7777 uv run python analyze_knowledge_base.py
```

### Phase 1 Success Validation
```bash
# Should show >500 entities (not 0)
SYNAPSE_MEMGRAPH_PORT=7777 uv run python analyze_knowledge_base.py | grep "Total Entities"
```

### Phase 2 Success Validation
```bash
# Should work without circular import errors
echo "search artificial intelligence" | SYNAPSE_MEMGRAPH_PORT=7777 uv run python query_knowledge_base.py
```

### Phase 3 Success Validation  
```bash
# Should have high test coverage
MEMGRAPH_HOST=localhost uv run pytest tests/ -v --tb=short
```

## 🎯 Sub-Agent Selection Guide

### Backend-Engineer Agent (Phases 1 & 2)
**Use For:**
- Server-side implementation (IngestionService, dependencies)
- Database integration (entity storage, relationships)
- Infrastructure configuration (embedding services, vector stores)
- Performance optimization

**Perfect For:**
- Entity extraction integration in ingestion pipeline
- Vector store configuration and embedding setup
- API and service layer modifications

### QA-Test-Guardian Agent (Phase 3)
**Use For:** 
- Comprehensive testing implementation
- Quality assurance and validation
- Regression prevention
- Performance benchmarking

**Perfect For:**
- Creating test suites for new functionality
- Integration testing across components
- Performance validation and benchmarking

### General-Purpose Agent (Coordination)
**Use For:**
- Analysis and coordination tasks
- File exploration and understanding
- System monitoring and validation
- Documentation and reporting

## 🔄 Context Management Strategy

### State Preservation
Each agent receives:
- **Working Environment:** Directory, ports, configuration
- **Data Baseline:** Current document/chunk counts to preserve
- **Analysis Tools:** Available for validation
- **Success Criteria:** Clear metrics for completion

### Handoff Protocol
1. **Phase Completion:** Validate success criteria before handoff
2. **State Documentation:** Pass critical information to next phase
3. **Validation Commands:** Verify functionality before proceeding
4. **Rollback Plan:** Emergency procedures if phase fails

### Context Rot Prevention
- **Atomic Tasks:** Each agent gets single, focused challenge
- **Progressive Validation:** Test each phase before next
- **State Documentation:** Critical info preserved in documents
- **Clear Boundaries:** Agents focus only on their specialization

## ⚠️ Important Usage Notes

### DO use this system when:
- Complex multi-step technical implementation needed
- Risk of context rot with single massive prompt
- Need for specialized technical expertise
- Systematic validation and testing required

### DO NOT use this system for:
- Simple single-file edits or bug fixes
- Quick diagnostic tasks
- Exploratory analysis or research
- Documentation-only changes

### Critical Success Factors
1. **Sequential Execution:** Complete phases in order (1 → 2 → 3)
2. **Validation Checkpoints:** Verify success before proceeding
3. **State Preservation:** Maintain environment and data integrity
4. **Specialized Focus:** Let each agent excel in their domain

## 📊 Expected Timeline

### Optimal Execution
- **Phase 1:** 1-2 hours (entity extraction fix)
- **Phase 2:** 1-2 hours (vector store implementation)  
- **Phase 3:** 2-3 hours (comprehensive testing)
- **Total:** 4-7 hours to production-ready system

### Benefits Over Single Prompt
- **Higher Success Rate:** Specialized agents excel in their domains
- **Better Quality:** Deep focus without context overload
- **Systematic Validation:** Progressive testing prevents failures
- **Maintainable:** Clear separation of concerns and responsibilities

## 🚀 Getting Started

### Immediate Usage (Recommended)
1. **Copy `MASTER_COORDINATOR.md` content**
2. **Paste into Claude Code session**
3. **System automatically coordinates all phases**
4. **Monitor progress and validate each phase**
5. **Enjoy production-ready Graph-RAG system!**

### Manual Execution (Advanced)
1. Start with Phase 1 using `PHASE1_ENTITY_EXTRACTION.md`
2. Validate entity extraction success
3. Proceed to Phase 2 using `PHASE2_VECTOR_STORE.md`
4. Validate semantic search functionality
5. Complete with Phase 3 using `PHASE3_TESTING.md`
6. Final system validation

This prompt engineering system provides the optimal approach for implementing complex technical fixes while maintaining context and ensuring systematic success.