#!/bin/bash
# Demo Environment Setup Script
# Sets up a demo environment for Synapse Graph-RAG with sample data and use cases

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Project root
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

echo "🚀 SYNAPSE GRAPH-RAG - DEMO ENVIRONMENT SETUP"
echo "============================================================"
echo ""

# Step 1: Check prerequisites
echo "📋 Step 1: Checking Prerequisites"
echo "----------------------------------------"

check_command() {
    if command -v "$1" &> /dev/null; then
        echo -e "  ${GREEN}✅${NC} $1: $(command -v $1)"
        return 0
    else
        echo -e "  ${RED}❌${NC} $1: Not found"
        return 1
    fi
}

MISSING_DEPS=0
check_command python3 || MISSING_DEPS=1
check_command docker || MISSING_DEPS=1
check_command uv || MISSING_DEPS=1

if [ $MISSING_DEPS -eq 1 ]; then
    echo ""
    echo -e "${RED}Error: Missing required dependencies${NC}"
    exit 1
fi

echo ""

# Step 2: Start Memgraph
echo "📋 Step 2: Starting Memgraph"
echo "----------------------------------------"

if docker ps | grep -q memgraph; then
    echo -e "  ${GREEN}✅${NC} Memgraph is already running"
else
    echo "  Starting Memgraph via Docker Compose..."
    if docker-compose -f tools/docker/docker-compose.yml up -d memgraph 2>/dev/null || \
       docker compose -f tools/docker/docker-compose.yml up -d memgraph 2>/dev/null; then
        echo "  Waiting for Memgraph to be ready..."
        sleep 5
        echo -e "  ${GREEN}✅${NC} Memgraph started"
    else
        echo -e "  ${YELLOW}⚠️${NC}  Could not start Memgraph automatically"
        echo "  Please start Memgraph manually: make run-memgraph"
    fi
fi

echo ""

# Step 3: Install dependencies
echo "📋 Step 3: Installing Dependencies"
echo "----------------------------------------"

if [ -d ".venv" ] || [ -f "uv.lock" ]; then
    echo "  Installing dependencies with uv..."
    if uv pip install -e .[dev] 2>/dev/null || uv sync 2>/dev/null; then
        echo -e "  ${GREEN}✅${NC} Dependencies installed"
    else
        echo -e "  ${YELLOW}⚠️${NC}  Dependency installation had issues (may already be installed)"
    fi
else
    echo -e "  ${YELLOW}⚠️${NC}  Virtual environment not found, skipping dependency install"
fi

echo ""

# Step 4: Download NLP models
echo "📋 Step 4: Downloading NLP Models"
echo "----------------------------------------"

if command -v python3 &> /dev/null; then
    echo "  Downloading spaCy model..."
    python3 -m spacy download en_core_web_sm 2>/dev/null || echo -e "  ${YELLOW}⚠️${NC}  spaCy model download skipped (may already be installed)"
    
    echo "  Downloading NLTK data..."
    python3 -m nltk.downloader punkt 2>/dev/null || echo -e "  ${YELLOW}⚠️${NC}  NLTK data download skipped (may already be installed)"
    
    echo -e "  ${GREEN}✅${NC} NLP models ready"
else
    echo -e "  ${YELLOW}⚠️${NC}  Python3 not found, skipping NLP model download"
fi

echo ""

# Step 5: Create demo data directory
echo "📋 Step 5: Setting Up Demo Data"
echo "----------------------------------------"

DEMO_DATA_DIR="$PROJECT_ROOT/data/demo"
mkdir -p "$DEMO_DATA_DIR"

# Create sample demo documents
cat > "$DEMO_DATA_DIR/demo_document_1.md" << 'EOF'
# Enterprise Graph-RAG System

## Overview

Synapse Graph-RAG is a production-ready Graph-augmented Retrieval-Augmented Generation system designed for Fortune 500 enterprises.

## Key Features

- **Advanced Graph-RAG**: Combines knowledge graphs (Memgraph) with vector search (FAISS)
- **Enterprise Business Intelligence**: Complete consultation pipeline tracking and ROI optimization
- **MCP Integration**: Model Context Protocol server for seamless IDE integration
- **Enterprise API**: Consolidated 4-router architecture with zero technical debt

## Use Cases

1. **Document Q&A**: Ask questions about ingested documents with graph-enhanced context
2. **Knowledge Discovery**: Discover relationships between entities across documents
3. **Enterprise Search**: Hybrid search combining vector similarity and graph traversal
EOF

cat > "$DEMO_DATA_DIR/demo_document_2.md" << 'EOF'
# Graph-RAG Architecture

## Components

### Graph Database (Memgraph)
- Stores entities and relationships
- Enables multi-hop traversal
- Provides graph context for RAG

### Vector Store (FAISS)
- Stores document embeddings
- Enables semantic search
- Provides similarity matching

### LLM Service
- Generates responses
- Uses graph + vector context
- Provides citations

## Integration

The system integrates graph and vector search to provide accurate, context-aware responses with citation tracking.
EOF

cat > "$DEMO_DATA_DIR/demo_document_3.md" << 'EOF'
# Deployment Guide

## Prerequisites

- Python 3.10+
- Docker (for Memgraph)
- uv (for dependency management)

## Quick Start

1. Install dependencies: `make install-dev`
2. Start Memgraph: `make run-memgraph`
3. Start API: `make run-api`
4. Verify: `curl http://localhost:8000/health`

## Production Deployment

For production deployments, use Docker Compose or Kubernetes manifests provided in the infrastructure directory.
EOF

echo -e "  ${GREEN}✅${NC} Demo documents created in $DEMO_DATA_DIR"

echo ""

# Step 6: Create demo ingestion script
echo "📋 Step 6: Creating Demo Ingestion Script"
echo "----------------------------------------"

cat > "$DEMO_DATA_DIR/ingest_demo.sh" << 'EOF'
#!/bin/bash
# Demo ingestion script for Synapse Graph-RAG

set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$PROJECT_ROOT"

echo "📥 Ingesting demo documents..."

# Use CLI to ingest documents
if command -v synapse &> /dev/null; then
    synapse ingest "$PROJECT_ROOT/data/demo/demo_document_1.md"
    synapse ingest "$PROJECT_ROOT/data/demo/demo_document_2.md"
    synapse ingest "$PROJECT_ROOT/data/demo/demo_document_3.md"
    echo "✅ Demo documents ingested"
else
    echo "⚠️  Synapse CLI not found, using Python API..."
    python3 -c "
from graph_rag.services.ingestion import IngestionService
from graph_rag.api.dependencies import create_graph_repository, create_vector_store
import asyncio

async def ingest():
    repo = create_graph_repository()
    vector_store = create_vector_store()
    service = IngestionService(repo, vector_store)
    
    docs = [
        '$PROJECT_ROOT/data/demo/demo_document_1.md',
        '$PROJECT_ROOT/data/demo/demo_document_2.md',
        '$PROJECT_ROOT/data/demo/demo_document_3.md'
    ]
    
    for doc_path in docs:
        with open(doc_path) as f:
            content = f.read()
            await service.ingest_document(content, doc_path)
    
    print('✅ Demo documents ingested')

asyncio.run(ingest())
"
fi
EOF

chmod +x "$DEMO_DATA_DIR/ingest_demo.sh"
echo -e "  ${GREEN}✅${NC} Demo ingestion script created"

echo ""

# Step 7: Create demo use cases file
echo "📋 Step 7: Creating Demo Use Cases"
echo "----------------------------------------"

cat > "$DEMO_DATA_DIR/demo_use_cases.md" << 'EOF'
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
EOF

echo -e "  ${GREEN}✅${NC} Demo use cases created"

echo ""

# Step 8: Create demo configuration
echo "📋 Step 8: Creating Demo Configuration"
echo "----------------------------------------"

cat > "$DEMO_DATA_DIR/demo.env" << 'EOF'
# Demo Environment Configuration
# Copy to .env for demo setup

# Memgraph Connection
SYNAPSE_MEMGRAPH_HOST=localhost
SYNAPSE_MEMGRAPH_PORT=7687
SYNAPSE_MEMGRAPH_USER=memgraph
SYNAPSE_MEMGRAPH_PASSWORD=memgraph

# API Configuration
SYNAPSE_API_HOST=0.0.0.0
SYNAPSE_API_PORT=8000

# LLM Provider (use mock for demo)
SYNAPSE_LLM_TYPE=mock

# Vector Store
SYNAPSE_VECTOR_STORE_TYPE=simple

# Entity Extraction
SYNAPSE_ENTITY_EXTRACTOR_TYPE=spacy

# Embedding Provider
SYNAPSE_EMBEDDING_PROVIDER=sentencetransformers

# Debug Mode (for demo)
DEBUG=True
EOF

echo -e "  ${GREEN}✅${NC} Demo configuration created"

echo ""

# Step 9: Summary
echo "============================================================"
echo "🎉 DEMO ENVIRONMENT SETUP COMPLETE"
echo "============================================================"
echo ""
echo "📁 Demo files created in: $DEMO_DATA_DIR"
echo ""
echo "📋 Next Steps:"
echo "  1. Start API server: make run-api"
echo "  2. Ingest demo documents: ./data/demo/ingest_demo.sh"
echo "  3. Try demo queries: See data/demo/demo_use_cases.md"
echo ""
echo "📖 Documentation:"
echo "  - Demo Use Cases: data/demo/demo_use_cases.md"
echo "  - Deployment Guide: docs/DEPLOYMENT_GUIDE.md"
echo ""
echo "✅ Ready for demo!"
