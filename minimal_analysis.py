#!/usr/bin/env python3
"""Ultra-minimal analysis to prevent CLI buffer overflow."""

import asyncio
import os
from graph_rag.infrastructure.graph_stores.memgraph_store import MemgraphGraphRepository
from graph_rag.config import get_settings

async def minimal_stats():
    """Get absolute minimal stats with tiny output."""
    try:
        settings = get_settings()
        settings.memgraph_port = int(os.environ.get('SYNAPSE_MEMGRAPH_PORT', 7687))
        repo = MemgraphGraphRepository(settings_obj=settings)
        
        # Single query for counts
        query = """
        MATCH (d:Document)
        OPTIONAL MATCH (c:Chunk)
        OPTIONAL MATCH (e) WHERE NOT e:Document AND NOT e:Chunk AND NOT e:Topic
        RETURN count(DISTINCT d) as docs, count(DISTINCT c) as chunks, count(DISTINCT e) as entities
        """
        result = await repo.execute_query(query)
        
        if result:
            r = result[0]
            print(f"📚 {r['docs']} docs | 📝 {r['chunks']} chunks | 🏷️ {r['entities']} entities")
        else:
            print("📊 No data found")
            
    except Exception as e:
        print(f"❌ {str(e)[:50]}")

if __name__ == "__main__":
    asyncio.run(minimal_stats())