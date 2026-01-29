# Demo Setup Guide - Synapse Graph-RAG

**Generated:** January 21, 2026
**Project:** Synapse Graph-RAG
**Location:** `neoforge-dev/synapse-graph-rag/`

---

## Overview

This guide helps you set up a demo environment for Synapse Graph-RAG to showcase enterprise capabilities to potential customers.

**Demo Duration:** ~20 minutes  
**Target Audience:** Enterprise decision-makers, technical evaluators

---

## Prerequisites

### Required
- Python 3.10+
- Docker & Docker Compose
- uv (Astral Python package manager)
- Internet access (for NLP model downloads)

### Optional
- Memgraph already running (if not, script will start it)

---

## Quick Setup (5 minutes)

### Automated Setup

```bash
cd neoforge-dev/synapse-graph-rag

# Run automated setup script
./scripts/setup_demo_environment.sh
```

This script will:
1. ✅ Check prerequisites
2. ✅ Start Memgraph (if not running)
3. ✅ Install dependencies
4. ✅ Download NLP models
5. ✅ Create demo documents
6. ✅ Create demo ingestion script
7. ✅ Create demo use cases

---

## Manual Setup (if needed)

### Step 1: Start Infrastructure

```bash
# Start Memgraph
make run-memgraph
# Or: docker-compose -f tools/docker/docker-compose.yml up -d memgraph

# Verify Memgraph is running
docker ps | grep memgraph
```

### Step 2: Install Dependencies

```bash
# Install dependencies
make install-dev
# Or: uv pip install -e .[dev]

# Download NLP models
make download-nlp-data
```

### Step 3: Configure Environment

```bash
# Copy demo configuration
cp data/demo/demo.env .env

# Or create your own .env with:
# SYNAPSE_MEMGRAPH_HOST=localhost
# SYNAPSE_MEMGRAPH_PORT=7687
# SYNAPSE_API_HOST=0.0.0.0
# SYNAPSE_API_PORT=8000
# SYNAPSE_LLM_TYPE=mock
```

---

## Demo Data

### Demo Documents

Demo documents are created in `data/demo/`:
- `demo_document_1.md` - Overview of Synapse Graph-RAG
- `demo_document_2.md` - Architecture details
- `demo_document_3.md` - Deployment guide

### Ingest Demo Documents

```bash
# Run ingestion script
./data/demo/ingest_demo.sh

# Or manually:
synapse ingest data/demo/demo_document_1.md
synapse ingest data/demo/demo_document_2.md
synapse ingest data/demo/demo_document_3.md
```

---

## Demo Use Cases

See `data/demo/demo_use_cases.md` for complete use cases. Here are the highlights:

### Use Case 1: Document Question Answering

**Query:** "What is Synapse Graph-RAG?"

**API Call:**
```bash
curl -X POST http://localhost:8000/api/v1/query \
  -H "Content-Type: application/json" \
  -d '{"query": "What is Synapse Graph-RAG?", "max_results": 5}'
```

**Expected:** Response with citations referencing overview document

---

### Use Case 2: Knowledge Discovery

**Query:** "What are the components of the Graph-RAG architecture?"

**API Call:**
```bash
curl -X POST http://localhost:8000/api/v1/query \
  -H "Content-Type: application/json" \
  -d '{"query": "What are the components of the Graph-RAG architecture?", "max_results": 5}'
```

**Expected:** Response listing Memgraph, FAISS, LLM Service with relationships

---

### Use Case 3: Deployment Information

**Query:** "How do I deploy Synapse Graph-RAG?"

**API Call:**
```bash
curl -X POST http://localhost:8000/api/v1/query \
  -H "Content-Type: application/json" \
  -d '{"query": "How do I deploy Synapse Graph-RAG?", "max_results": 5}'
```

**Expected:** Response with deployment steps and prerequisites

---

### Use Case 4: Entity Relationship Discovery

**Query:** "What entities are related to Memgraph?"

**API Call:**
```bash
curl -X POST http://localhost:8000/api/v1/search \
  -H "Content-Type: application/json" \
  -d '{"query": "Memgraph", "search_type": "graph"}'
```

**Expected:** Graph traversal showing related entities and relationships

---

### Use Case 5: Hybrid Search

**Query:** "Enterprise features and capabilities"

**API Call:**
```bash
curl -X POST http://localhost:8000/api/v1/search \
  -H "Content-Type: application/json" \
  -d '{"query": "Enterprise features and capabilities", "search_type": "hybrid"}'
```

**Expected:** Combined vector similarity + graph context results

---

## Demo Flow (20 minutes)

### Part 1: Setup & Overview (5 min)
1. **Show infrastructure** - Memgraph running, API ready
2. **Explain architecture** - Graph + Vector hybrid approach
3. **Show API docs** - `http://localhost:8000/docs`

### Part 2: Ingestion (2 min)
1. **Ingest demo documents** - Run `./data/demo/ingest_demo.sh`
2. **Show ingestion process** - Documents → Entities → Graph
3. **Verify ingestion** - Check documents endpoint

### Part 3: Query Examples (10 min)
1. **Use Case 1** - Document Q&A (show citations)
2. **Use Case 2** - Knowledge discovery (show graph traversal)
3. **Use Case 3** - Deployment info (show accuracy)
4. **Use Case 4** - Entity relationships (show graph power)
5. **Use Case 5** - Hybrid search (show best of both)

### Part 4: Enterprise Features (3 min)
1. **Show API structure** - Consolidated routers
2. **Show monitoring** - Health endpoints, metrics
3. **Show compliance** - SOX, GDPR, HIPAA ready

---

## Verification Steps

After setup, verify everything works:

```bash
# 1. Check API health
curl http://localhost:8000/health

# 2. Check documents ingested
curl http://localhost:8000/api/v1/documents

# 3. Check entities
curl http://localhost:8000/api/v1/entities

# 4. Try a query
curl -X POST http://localhost:8000/api/v1/query \
  -H "Content-Type: application/json" \
  -d '{"query": "What is Synapse?", "max_results": 3}'
```

---

## Troubleshooting

### Memgraph Not Starting

```bash
# Check Docker
docker ps

# Check logs
docker logs <memgraph-container-id>

# Restart
make run-memgraph
```

### API Not Responding

```bash
# Check if API is running
ps aux | grep "graph_rag.api.main"

# Check logs
tail -f logs/api.log  # if logging to file

# Restart API
make run-api
```

### Documents Not Ingesting

```bash
# Check Memgraph connection
curl http://localhost:8000/api/v1/health

# Check environment variables
echo $SYNAPSE_MEMGRAPH_HOST
echo $SYNAPSE_MEMGRAPH_PORT

# Try manual ingestion
synapse ingest data/demo/demo_document_1.md --verbose
```

---

## Customizing Demo

### Add Your Own Documents

```bash
# Add documents to data/demo/
cp your_document.md data/demo/

# Ingest
synapse ingest data/demo/your_document.md
```

### Use Real LLM (instead of mock)

```bash
# Update .env
export SYNAPSE_LLM_TYPE=openai
export SYNAPSE_OPENAI_API_KEY=sk-...

# Restart API
make run-api
```

### Use Production Vector Store

```bash
# Update .env
export SYNAPSE_VECTOR_STORE_TYPE=faiss
# Or: export SYNAPSE_VECTOR_STORE_TYPE=pinecone

# Restart API
make run-api
```

---

## Demo Script Template

For sales presentations, use this script:

```
1. Introduction (1 min)
   - "Synapse Graph-RAG combines knowledge graphs with vector search"
   - "Designed for Fortune 500 enterprises"

2. Live Demo (15 min)
   - Setup (already done)
   - Show ingestion
   - Run Use Cases 1-5
   - Highlight enterprise features

3. Q&A (4 min)
   - Answer questions
   - Show API docs
   - Discuss deployment options
```

---

## Success Criteria

Demo is successful if:
- ✅ All 5 use cases return accurate responses
- ✅ Citations are included in responses
- ✅ Graph traversal works (Use Case 4)
- ✅ Hybrid search works (Use Case 5)
- ✅ API responds in <500ms
- ✅ No errors in logs

---

## Next Steps After Demo

1. **If Interested:**
   - Schedule technical deep dive
   - Provide deployment guide
   - Discuss enterprise requirements

2. **If Ready to Deploy:**
   - Review deployment guide
   - Set up production environment
   - Plan pilot program

---

**Last Updated:** January 21, 2026
