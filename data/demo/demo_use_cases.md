# Demo Use Cases - Synapse Graph-RAG

## Use Case 1: Document Question Answering

**Query:** "What is Synapse Graph-RAG?"

**Expected Response:**
- Should reference the overview document
- Should mention key features (Graph-RAG, Enterprise BI, MCP Integration)
- Should include citations

**API Call:**
```bash
curl -X POST http://localhost:8000/api/v1/query \
  -H "Content-Type: application/json" \
  -d '{"query": "What is Synapse Graph-RAG?", "max_results": 5}'
```

---

## Use Case 2: Knowledge Discovery

**Query:** "What are the components of the Graph-RAG architecture?"

**Expected Response:**
- Should reference the architecture document
- Should list components (Memgraph, FAISS, LLM Service)
- Should explain integration between components

**API Call:**
```bash
curl -X POST http://localhost:8000/api/v1/query \
  -H "Content-Type: application/json" \
  -d '{"query": "What are the components of the Graph-RAG architecture?", "max_results": 5}'
```

---

## Use Case 3: Deployment Information

**Query:** "How do I deploy Synapse Graph-RAG?"

**Expected Response:**
- Should reference the deployment guide
- Should list prerequisites
- Should provide quick start steps

**API Call:**
```bash
curl -X POST http://localhost:8000/api/v1/query \
  -H "Content-Type: application/json" \
  -d '{"query": "How do I deploy Synapse Graph-RAG?", "max_results": 5}'
```

---

## Use Case 4: Entity Relationship Discovery

**Query:** "What entities are related to Memgraph?"

**Expected Response:**
- Should use graph traversal to find related entities
- Should show relationships
- Should provide context

**API Call:**
```bash
curl -X POST http://localhost:8000/api/v1/search \
  -H "Content-Type: application/json" \
  -d '{"query": "Memgraph", "search_type": "graph"}'
```

---

## Use Case 5: Hybrid Search

**Query:** "Enterprise features and capabilities"

**Expected Response:**
- Should combine vector similarity and graph context
- Should rank results by relevance
- Should provide comprehensive answers

**API Call:**
```bash
curl -X POST http://localhost:8000/api/v1/search \
  -H "Content-Type: application/json" \
  -d '{"query": "Enterprise features and capabilities", "search_type": "hybrid"}'
```

---

## Verification Steps

After ingesting demo documents, verify:

1. **Documents ingested:**
   ```bash
   curl http://localhost:8000/api/v1/documents
   ```

2. **Graph entities:**
   ```bash
   curl http://localhost:8000/api/v1/entities
   ```

3. **Health check:**
   ```bash
   curl http://localhost:8000/health
   ```

---

## Expected Demo Flow

1. **Setup** (5 minutes)
   - Run `./scripts/setup_demo_environment.sh`
   - Start API: `make run-api`

2. **Ingest** (2 minutes)
   - Run `./data/demo/ingest_demo.sh`
   - Verify documents ingested

3. **Query** (5 minutes)
   - Try Use Case 1-5 queries
   - Verify responses include citations
   - Check graph traversal works

4. **Showcase** (10 minutes)
   - Demonstrate hybrid search
   - Show entity relationships
   - Highlight enterprise features

**Total Demo Time:** ~20 minutes
