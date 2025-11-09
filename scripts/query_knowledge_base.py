#!/usr/bin/env python3
"""
Knowledge Base Query and Search Script
Interactive tool for exploring the ingested knowledge base.
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from graph_rag.config import get_settings
from graph_rag.infrastructure.graph_stores.memgraph_store import MemgraphGraphRepository


async def main():
    """Main interactive query function"""
    print("🔍 Knowledge Base Query Tool")
    print("=" * 50)
    print("Available commands:")
    print("1. search <query>     - Vector search for documents")
    print("2. entity <name>      - Find entity and related documents")
    print("3. doc <title>        - Find document by title")
    print("4. stats             - Show knowledge base statistics")
    print("5. categories        - List all document categories")
    print("6. technologies      - Find technology mentions")
    print("7. business          - Find business concepts")
    print("8. exit              - Exit the tool")
    print("=" * 50)

    # Initialize settings and services
    settings = get_settings()
    settings.memgraph_port = 7777  # Use custom port

    try:
        # Initialize services
        graph_repo = MemgraphGraphRepository(settings_obj=settings)

        print("✅ Connected to knowledge base")

        # Interactive loop
        while True:
            try:
                user_input = input("\n> ").strip()

                if not user_input:
                    continue

                if user_input.lower() == 'exit':
                    break

                # Parse command
                parts = user_input.split(' ', 1)
                command = parts[0].lower()
                query = parts[1] if len(parts) > 1 else ""

                if command == 'search':
                    if not query:
                        print("❌ Please provide a search query")
                        continue
                    await handle_search(graph_repo, query)

                elif command == 'entity':
                    if not query:
                        print("❌ Please provide an entity name")
                        continue
                    await handle_entity_search(graph_repo, query)

                elif command == 'doc':
                    if not query:
                        print("❌ Please provide a document title")
                        continue
                    await handle_document_search(graph_repo, query)

                elif command == 'stats':
                    await handle_stats(graph_repo)

                elif command == 'categories':
                    await handle_categories(graph_repo)

                elif command == 'technologies':
                    await handle_technologies(graph_repo)

                elif command == 'business':
                    await handle_business_concepts(graph_repo)

                else:
                    print(f"❌ Unknown command: {command}")
                    print("Type 'exit' to quit or use one of the available commands.")

            except KeyboardInterrupt:
                print("\n👋 Goodbye!")
                break
            except Exception as e:
                print(f"❌ Error: {e}")

    except Exception as e:
        print(f"❌ Connection error: {e}")
    finally:
        # Close connections
        if 'graph_repo' in locals():
            await graph_repo.close()

async def handle_search(graph_repo: MemgraphGraphRepository, query: str):
    """Handle content search query"""
    print(f"🔍 Searching for: '{query}'")

    try:
        # Search in chunks for content
        search_query = """
        MATCH (c:Chunk)
        WHERE toLower(c.content) CONTAINS toLower($query)
        OPTIONAL MATCH (c)-[:BELONGS_TO]->(d:Document)
        RETURN c.content as content, d.title as document_title, d.category as category
        LIMIT 10
        """

        results = await graph_repo.execute_query(search_query, {"query": query})

        if not results:
            print("📭 No results found")
            return

        print(f"📚 Found {len(results)} relevant chunks:")
        print("-" * 60)

        for i, result in enumerate(results, 1):
            print(f"\n{i}. Document: {result.get('document_title', 'Unknown')}")
            if result.get('category'):
                print(f"   Category: {result['category']}")
            content = result['content'][:200] + "..." if len(result['content']) > 200 else result['content']
            print(f"   Content: {content}")

    except Exception as e:
        print(f"❌ Search error: {e}")

async def handle_entity_search(graph_repo: MemgraphGraphRepository, entity_name: str):
    """Handle entity search"""
    print(f"🏷️  Searching for entity: '{entity_name}'")

    try:
        # Search for entity (case-insensitive partial match)
        entity_query = """
        MATCH (e:Entity)
        WHERE toLower(e.name) CONTAINS toLower($entity_name)
        RETURN e.name as name, e.entity_type as entity_type, id(e) as entity_id
        LIMIT 10
        """

        entities = await graph_repo.execute_query(
            entity_query,
            {"entity_name": entity_name}
        )

        if not entities:
            print("📭 No entities found")
            return

        print(f"🏷️  Found {len(entities)} matching entities:")

        for entity in entities:
            print(f"\n• {entity['name']} ({entity['entity_type']})")

            # Get related documents
            related_docs_query = """
            MATCH (e:Entity)-[:MENTIONS]-(c:Chunk)-[:BELONGS_TO]->(d:Document)
            WHERE id(e) = $entity_id
            RETURN DISTINCT d.title as title, d.category as category
            LIMIT 5
            """

            related_docs = await graph_repo.execute_query(
                related_docs_query,
                {"entity_id": entity['entity_id']}
            )

            if related_docs:
                print("  📄 Related documents:")
                for doc in related_docs:
                    category = f" ({doc['category']})" if doc['category'] else ""
                    print(f"    - {doc['title']}{category}")

    except Exception as e:
        print(f"❌ Entity search error: {e}")

async def handle_document_search(graph_repo: MemgraphGraphRepository, title_query: str):
    """Handle document search by title"""
    print(f"📄 Searching for document: '{title_query}'")

    try:
        doc_query = """
        MATCH (d:Document)
        WHERE toLower(d.title) CONTAINS toLower($title_query)
        RETURN d.title as title, d.category as category, d.source as source,
               d.data_type as data_type, id(d) as doc_id
        LIMIT 10
        """

        documents = await graph_repo.execute_query(
            doc_query,
            {"title_query": title_query}
        )

        if not documents:
            print("📭 No documents found")
            return

        print(f"📚 Found {len(documents)} matching documents:")

        for doc in documents:
            print(f"\n• {doc['title']}")
            if doc['category']:
                print(f"  Category: {doc['category']}")
            if doc['source']:
                print(f"  Source: {doc['source']}")
            if doc['data_type']:
                print(f"  Type: {doc['data_type']}")

            # Get entities in this document
            entities_query = """
            MATCH (d:Document)-[:CONTAINS]->(c:Chunk)-[:MENTIONS]->(e:Entity)
            WHERE id(d) = $doc_id
            RETURN DISTINCT e.name as name, e.entity_type as entity_type
            LIMIT 10
            """

            entities = await graph_repo.execute_query(
                entities_query,
                {"doc_id": doc['doc_id']}
            )

            if entities:
                entity_list = [f"{e['name']} ({e['entity_type']})" for e in entities]
                print(f"  🏷️  Entities: {', '.join(entity_list)}")

    except Exception as e:
        print(f"❌ Document search error: {e}")

async def handle_stats(graph_repo: MemgraphGraphRepository):
    """Show knowledge base statistics"""
    print("📊 Knowledge Base Statistics")
    print("-" * 40)

    try:
        # Get basic counts
        stats_queries = [
            ("Documents", "MATCH (d:Document) RETURN count(d) as count"),
            ("Chunks", "MATCH (c:Chunk) RETURN count(c) as count"),
            ("Entities", "MATCH (e:Entity) RETURN count(e) as count"),
            ("Relationships", "MATCH ()-[r]->() RETURN count(r) as count")
        ]

        for label, query in stats_queries:
            result = await graph_repo.execute_query(query)
            count = result[0]['count'] if result else 0
            print(f"{label}: {count:,}")

    except Exception as e:
        print(f"❌ Stats error: {e}")

async def handle_categories(graph_repo: MemgraphGraphRepository):
    """List all document categories"""
    print("📂 Document Categories")
    print("-" * 30)

    try:
        categories_query = """
        MATCH (d:Document)
        WHERE d.category IS NOT NULL
        RETURN d.category as category, count(d) as count
        ORDER BY count DESC
        """

        categories = await graph_repo.execute_query(categories_query)

        if not categories:
            print("📭 No categories found")
            return

        for cat in categories:
            print(f"• {cat['category']}: {cat['count']} documents")

    except Exception as e:
        print(f"❌ Categories error: {e}")

async def handle_technologies(graph_repo: MemgraphGraphRepository):
    """Find technology mentions"""
    print("💻 Technology Mentions")
    print("-" * 30)

    try:
        tech_query = """
        MATCH (e:Entity)-[:MENTIONS]-(c:Chunk)
        WHERE e.name =~ '(?i).*(react|python|javascript|typescript|docker|kubernetes|aws|azure|api|database|sql|nosql|microservice|blockchain|ai|ml|machine learning|fastapi|django|flask|node|angular|vue|redis|postgresql|mongodb|mysql|graphql|rest|devops|ci/cd|git|github|gitlab|jenkins|terraform|ansible).*'
        RETURN e.name as technology, count(*) as mentions
        ORDER BY mentions DESC
        LIMIT 20
        """

        technologies = await graph_repo.execute_query(tech_query)

        if not technologies:
            print("📭 No technology mentions found")
            return

        for tech in technologies:
            print(f"• {tech['technology']}: {tech['mentions']} mentions")

    except Exception as e:
        print(f"❌ Technologies error: {e}")

async def handle_business_concepts(graph_repo: MemgraphGraphRepository):
    """Find business concept mentions"""
    print("💼 Business Concepts")
    print("-" * 30)

    try:
        business_query = """
        MATCH (e:Entity)-[:MENTIONS]-(c:Chunk)
        WHERE e.name =~ '(?i).*(strategy|business|client|customer|revenue|growth|marketing|sales|product|service|solution|development|consulting|freelancing|startup|mvp|prototype|roadmap|planning|execution|leadership|team|project|agile|scrum|kanban|workflow|process|optimization|efficiency|innovation|scalability|performance).*'
        RETURN e.name as concept, count(*) as mentions
        ORDER BY mentions DESC
        LIMIT 20
        """

        concepts = await graph_repo.execute_query(business_query)

        if not concepts:
            print("📭 No business concepts found")
            return

        for concept in concepts:
            print(f"• {concept['concept']}: {concept['mentions']} mentions")

    except Exception as e:
        print(f"❌ Business concepts error: {e}")

if __name__ == "__main__":
    asyncio.run(main())
