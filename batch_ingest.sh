#!/bin/bash

# Batch ingestion script for Bogdan's personal data
set -e

export SYNAPSE_MEMGRAPH_PORT=7777
COUNTER=0
TOTAL=$(uv run synapse discover /Users/bogdan/data --include "*.md" | wc -l)

echo "🚀 Starting batch ingestion of $TOTAL documents..."
echo "📅 Started at: $(date)"

uv run synapse discover /Users/bogdan/data --include "*.md" | while read file; do
    COUNTER=$((COUNTER + 1))
    filename=$(basename "$file")
    category=$(echo "$file" | cut -d'/' -f6 | sed 's/ab0e9208-4267-4cea-8b89-285af4905dbd_Export-ab3a0f1d-6be8-4b06-b1c8-543aa4018e8f/CodeSwiftr/')
    
    echo "[$COUNTER/$TOTAL] Processing: $filename"
    
    SYNAPSE_MEMGRAPH_PORT=7777 uv run synapse ingest "$file" \
        --meta source="Bogdan_Personal_Knowledge_Base" \
        --meta category="$category" \
        --meta data_type="markdown" \
        --meta ingestion_batch="$(date +%Y%m%d)" > /dev/null 2>&1 || echo "❌ Failed: $filename"
    
    # Progress update every 50 documents
    if [ $((COUNTER % 50)) -eq 0 ]; then
        echo "✅ Completed $COUNTER/$TOTAL documents ($(( COUNTER * 100 / TOTAL ))%)"
    fi
done

echo "✅ Batch ingestion completed at: $(date)"