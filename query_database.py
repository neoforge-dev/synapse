#!/usr/bin/env python3
"""
Direct database query script to examine what's in the Memgraph database.
"""

import asyncio

from graph_rag.config import Settings
from graph_rag.infrastructure.graph_stores.memgraph_store import MemgraphGraphRepository


async def query_database():
    """Query the database to see what's there."""
    settings = Settings()
    graph_repo = MemgraphGraphRepository(settings)

    try:
        # Check documents
        docs_query = "MATCH (d:Document) RETURN d.document_id, d.title, d.source LIMIT 10"
        docs = await graph_repo.execute_query(docs_query)
        print(f"📄 Documents found: {len(docs)}")
        for doc in docs:
            print(f"  - ID: {doc.get('d.document_id')}, Title: {doc.get('d.title')}, Source: {doc.get('d.source')}")

        # Check chunks
        chunks_query = "MATCH (c:Chunk) RETURN count(c) as chunk_count"
        chunks = await graph_repo.execute_query(chunks_query)
        print(f"📝 Total chunks: {chunks[0]['chunk_count'] if chunks else 0}")

        # Check entities
        entities_query = "MATCH (e:Entity) RETURN e.name, e.entity_type LIMIT 20"
        entities = await graph_repo.execute_query(entities_query)
        print(f"🏷️ Sample entities found: {len(entities)}")
        for entity in entities[:10]:
            print(f"  - {entity.get('e.name')} ({entity.get('e.entity_type')})")

        # Search for Notion specifically
        notion_query = """
        MATCH (d:Document)-[:HAS_CHUNK]->(c:Chunk)-[:MENTIONS]->(e:Entity)
        WHERE toLower(e.name) CONTAINS 'notion'
           OR toLower(c.text) CONTAINS 'notion'
           OR toLower(d.title) CONTAINS 'notion'
        RETURN d.document_id, d.title, c.text, e.name
        LIMIT 10
        """
        notion_results = await graph_repo.execute_query(notion_query)
        print(f"🔍 Notion-related content: {len(notion_results)}")
        for result in notion_results:
            print(f"  - Doc: {result.get('d.title')}")
            print(f"    Entity: {result.get('e.name')}")
            print(f"    Text snippet: {result.get('c.text')[:100]}...")

        # Search for LinkedIn
        linkedin_query = """
        MATCH (d:Document)-[:HAS_CHUNK]->(c:Chunk)-[:MENTIONS]->(e:Entity)
        WHERE toLower(e.name) CONTAINS 'linkedin'
           OR toLower(c.text) CONTAINS 'linkedin'
           OR toLower(d.title) CONTAINS 'linkedin'
        RETURN d.document_id, d.title, c.text, e.name
        LIMIT 10
        """
        linkedin_results = await graph_repo.execute_query(linkedin_query)
        print(f"🔗 LinkedIn-related content: {len(linkedin_results)}")
        for result in linkedin_results:
            print(f"  - Doc: {result.get('d.title')}")
            print(f"    Entity: {result.get('e.name')}")
            print(f"    Text snippet: {result.get('c.text')[:100]}...")

        # Search for content strategy
        strategy_query = """
        MATCH (d:Document)-[:HAS_CHUNK]->(c:Chunk)
        WHERE toLower(c.text) CONTAINS 'content strategy'
           OR toLower(c.text) CONTAINS 'content creation'
           OR toLower(c.text) CONTAINS 'content optimization'
        RETURN d.document_id, d.title, c.text
        LIMIT 10
        """
        strategy_results = await graph_repo.execute_query(strategy_query)
        print(f"📈 Content strategy related: {len(strategy_results)}")
        for result in strategy_results:
            print(f"  - Doc: {result.get('d.title')}")
            print(f"    Text snippet: {result.get('c.text')[:100]}...")

    except Exception as e:
        print(f"Error querying database: {e}")

if __name__ == "__main__":
    asyncio.run(query_database())
