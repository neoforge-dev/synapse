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
