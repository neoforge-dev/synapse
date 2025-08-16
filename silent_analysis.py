#!/usr/bin/env python3
"""Silent analysis agent with complete output suppression."""

import asyncio
import logging
import os
import sys
from contextlib import contextmanager
from io import StringIO

# Suppress all logging to prevent output overflow
logging.getLogger().setLevel(logging.CRITICAL)
for logger_name in ['graph_rag', 'sentence_transformers', 'INFO']:
    logging.getLogger(logger_name).setLevel(logging.CRITICAL)

from graph_rag.infrastructure.graph_stores.memgraph_store import MemgraphGraphRepository
from graph_rag.config import get_settings

@contextmanager
def suppress_stdout():
    """Context manager to completely suppress stdout."""
    with open(os.devnull, 'w') as devnull:
        old_stdout = sys.stdout
        sys.stdout = devnull
        try:
            yield
        finally:
            sys.stdout = old_stdout

class SilentAnalysisAgent:
    """Analysis agent that runs completely silently to avoid CLI crashes."""
    
    def __init__(self):
        with suppress_stdout():
            self.settings = get_settings()
            self.settings.memgraph_port = int(os.environ.get('SYNAPSE_MEMGRAPH_PORT', 7687))
            self.repo = MemgraphGraphRepository(settings_obj=self.settings)
    
    async def analyze_knowledge_graph(self):
        """Perform comprehensive analysis and return structured insights."""
        
        insights = {}
        
        try:
            # Basic statistics
            stats_query = """
            MATCH (d:Document)
            OPTIONAL MATCH (c:Chunk)
            OPTIONAL MATCH (e) WHERE NOT e:Document AND NOT e:Chunk AND NOT e:Topic
            RETURN count(DISTINCT d) as docs, count(DISTINCT c) as chunks, count(DISTINCT e) as entities
            """
            with suppress_stdout():
                result = await self.repo.execute_query(stats_query)
            
            if result:
                insights['basic_stats'] = result[0]
            
            # Entity type distribution
            entity_types_query = """
            MATCH (e) WHERE NOT e:Document AND NOT e:Chunk AND NOT e:Topic
            RETURN labels(e)[0] as type, count(*) as count
            ORDER BY count DESC LIMIT 5
            """
            with suppress_stdout():
                result = await self.repo.execute_query(entity_types_query)
            
            insights['top_entity_types'] = [{'type': r['type'], 'count': r['count']} for r in result]
            
            # Most connected entities
            connected_entities_query = """
            MATCH (e)-[r:MENTIONS]-(c:Chunk)
            WHERE NOT e:Document AND NOT e:Chunk AND NOT e:Topic
            RETURN e.name as entity, count(r) as connections
            ORDER BY connections DESC LIMIT 5
            """
            with suppress_stdout():
                result = await self.repo.execute_query(connected_entities_query)
            
            insights['most_connected'] = [{'entity': r['entity'][:30], 'connections': r['connections']} for r in result]
            
            # Document coverage
            doc_coverage_query = """
            MATCH (d:Document)
            OPTIONAL MATCH (d)-[:CONTAINS]->(c:Chunk)
            RETURN d.title as title, count(c) as chunks
            ORDER BY chunks DESC LIMIT 5
            """
            with suppress_stdout():
                result = await self.repo.execute_query(doc_coverage_query)
            
            insights['document_coverage'] = [{'title': (r['title'] or 'Untitled')[:40], 'chunks': r['chunks']} for r in result]
            
        except Exception as e:
            insights['error'] = str(e)[:100]
        
        return insights
    
    def generate_business_insights(self, data):
        """Generate actionable business insights from the knowledge graph."""
        
        insights = []
        
        if 'basic_stats' in data:
            stats = data['basic_stats']
            insights.append(f"Knowledge base contains {stats['docs']} documents with {stats['chunks']} chunks and {stats['entities']} extracted entities")
        
        if 'top_entity_types' in data:
            entity_summary = ", ".join([f"{item['count']} {item['type']}" for item in data['top_entity_types'][:3]])
            insights.append(f"Primary entity types: {entity_summary}")
        
        if 'most_connected' in data:
            top_entities = [item['entity'] for item in data['most_connected'][:3]]
            insights.append(f"Key concepts: {', '.join(top_entities)}")
        
        if 'document_coverage' in data:
            largest_doc = data['document_coverage'][0] if data['document_coverage'] else None
            if largest_doc:
                insights.append(f"Largest document: '{largest_doc['title']}' with {largest_doc['chunks']} chunks")
        
        return insights

async def main():
    """Main analysis function."""
    print("🔍 ANALYSIS AGENT REPORT")
    print("=" * 30)
    
    try:
        agent = SilentAnalysisAgent()
        
        # Perform analysis completely silently
        data = await agent.analyze_knowledge_graph()
        
        # Generate business insights
        insights = agent.generate_business_insights(data)
        
        # Output only essential insights
        for i, insight in enumerate(insights, 1):
            print(f"{i}. {insight}")
        
        print("\n✅ Analysis complete")
        
    except Exception as e:
        print(f"❌ Analysis failed: {str(e)[:50]}")

if __name__ == "__main__":
    asyncio.run(main())