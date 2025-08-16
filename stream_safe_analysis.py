#!/usr/bin/env python3
"""
Stream-safe knowledge base analysis to prevent CLI buffer overflow.
Outputs results in chunks and provides summary-only modes.
"""

import asyncio
import json
import sys
from typing import Dict, Any, List

from graph_rag.infrastructure.graph_stores.memgraph_store import MemgraphGraphRepository
from graph_rag.config import get_settings


class StreamSafeAnalyzer:
    """Knowledge base analyzer with output streaming protection."""
    
    def __init__(self, port: int = 7687):
        self.settings = get_settings()
        self.settings.memgraph_port = port
        self.graph_repo = MemgraphGraphRepository(settings_obj=self.settings)
    
    async def get_basic_stats(self) -> Dict[str, Any]:
        """Get basic statistics without overwhelming output."""
        
        # Document count
        doc_query = "MATCH (d:Document) RETURN count(d) as total_documents"
        doc_result = await self.graph_repo.execute_query(doc_query)
        total_documents = doc_result[0]["total_documents"] if doc_result else 0
        
        # Chunk count
        chunk_query = "MATCH (c:Chunk) RETURN count(c) as total_chunks"
        chunk_result = await self.graph_repo.execute_query(chunk_query)
        total_chunks = chunk_result[0]["total_chunks"] if chunk_result else 0
        
        # Entity count by type
        entity_query = """
        MATCH (e)
        WHERE NOT e:Document AND NOT e:Chunk AND NOT e:Topic
        RETURN labels(e)[0] as entity_type, count(*) as count
        ORDER BY count DESC
        """
        entity_result = await self.graph_repo.execute_query(entity_query)
        entity_stats = {row["entity_type"]: row["count"] for row in entity_result}
        total_entities = sum(entity_stats.values())
        
        # Relationship counts
        rel_query = """
        MATCH ()-[r]->()
        RETURN type(r) as rel_type, count(*) as count
        ORDER BY count DESC
        """
        rel_result = await self.graph_repo.execute_query(rel_query)
        relationship_stats = {row["rel_type"]: row["count"] for row in rel_result}
        
        return {
            "documents": total_documents,
            "chunks": total_chunks,
            "entities": total_entities,
            "entity_types": entity_stats,
            "relationships": relationship_stats
        }
    
    async def get_top_entities(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get most mentioned entities with controlled output size."""
        query = """
        MATCH (e)-[r:MENTIONS]-(c:Chunk)
        WHERE NOT e:Document AND NOT e:Chunk AND NOT e:Topic
        RETURN e.name as entity, labels(e)[0] as type, count(r) as mentions
        ORDER BY mentions DESC
        LIMIT $limit
        """
        result = await self.graph_repo.execute_query(query, {"limit": limit})
        return [{"entity": row["entity"], "type": row["type"], "mentions": row["mentions"]} 
                for row in result]
    
    async def get_document_summary(self) -> List[Dict[str, Any]]:
        """Get document summary with controlled output."""
        query = """
        MATCH (d:Document)
        OPTIONAL MATCH (d)-[:CONTAINS]->(c:Chunk)
        RETURN d.id as doc_id, d.title as title, count(c) as chunk_count
        ORDER BY chunk_count DESC
        """
        result = await self.graph_repo.execute_query(query)
        return [{"id": row["doc_id"], "title": row["title"], "chunks": row["chunk_count"]} 
                for row in result]
    
    def print_compact_summary(self, stats: Dict[str, Any], 
                            top_entities: List[Dict[str, Any]], 
                            documents: List[Dict[str, Any]]):
        """Print a compact summary that won't overflow CLI buffers."""
        
        print("📊 KNOWLEDGE BASE SUMMARY")
        print("=" * 40)
        print(f"📚 Documents: {stats['documents']}")
        print(f"📝 Chunks: {stats['chunks']}")
        print(f"🏷️  Entities: {stats['entities']}")
        print()
        
        print("📊 Entity Types:")
        for etype, count in list(stats['entity_types'].items())[:5]:  # Top 5 only
            print(f"   {etype}: {count}")
        print()
        
        print("🔗 Relationships:")
        for rtype, count in list(stats['relationships'].items())[:3]:  # Top 3 only
            print(f"   {rtype}: {count}")
        print()
        
        print("⭐ Top Entities:")
        for entity in top_entities[:5]:  # Top 5 only
            name = entity['entity'][:50]  # Truncate long names
            print(f"   {name} ({entity['type']}): {entity['mentions']} mentions")
        print()
        
        print("📚 Document Overview:")
        for doc in documents[:5]:  # Top 5 only
            title = doc['title'][:60] if doc['title'] else doc['id'][:60]
            print(f"   {title}: {doc['chunks']} chunks")


async def main():
    """Main analysis function with streaming protection."""
    
    # Use compact mode by default to prevent overflow
    compact_mode = True
    
    try:
        analyzer = StreamSafeAnalyzer()
        
        print("🔍 Starting Safe Knowledge Base Analysis...")
        print()
        
        # Get basic stats
        stats = await analyzer.get_basic_stats()
        
        # Get top entities (limited)
        top_entities = await analyzer.get_top_entities(limit=10)
        
        # Get document summary
        documents = await analyzer.get_document_summary()
        
        if compact_mode:
            analyzer.print_compact_summary(stats, top_entities, documents)
        else:
            # Full output mode (could cause overflow)
            print(json.dumps({
                "stats": stats,
                "top_entities": top_entities,
                "documents": documents
            }, indent=2))
        
        print("✅ Analysis completed safely")
        
    except Exception as e:
        print(f"❌ Analysis failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())