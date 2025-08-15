#!/usr/bin/env python3
"""
Comprehensive Knowledge Base Analysis Script
Analyzes the ingested documents and generates insights and visualizations.
"""

import asyncio
import json
import os
import sys
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple, Any

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from graph_rag.infrastructure.graph_stores.memgraph_graph_store import MemgraphGraphStore
from graph_rag.infrastructure.repositories.graph_repository import GraphRepository
from graph_rag.config import get_settings

async def main():
    """Main analysis function"""
    print("🔍 Starting Knowledge Base Analysis...")
    print(f"📅 Analysis started at: {datetime.now()}")
    
    # Initialize settings and connections
    settings = get_settings()
    settings.memgraph_port = 7777  # Use custom port
    
    try:
        # Initialize graph store and repository
        graph_store = MemgraphGraphStore(settings)
        graph_repo = GraphRepository(graph_store)
        
        print("\n📊 DOCUMENT STATISTICS")
        print("=" * 50)
        
        # Get document statistics
        doc_stats = await get_document_statistics(graph_repo)
        print_document_stats(doc_stats)
        
        print("\n🏷️  ENTITY ANALYSIS")
        print("=" * 50)
        
        # Get entity statistics
        entity_stats = await get_entity_statistics(graph_repo)
        print_entity_stats(entity_stats)
        
        print("\n🔗 RELATIONSHIP ANALYSIS")
        print("=" * 50)
        
        # Get relationship statistics
        rel_stats = await get_relationship_statistics(graph_repo)
        print_relationship_stats(rel_stats)
        
        print("\n📈 CONTENT INSIGHTS")
        print("=" * 50)
        
        # Get content insights
        content_insights = await get_content_insights(graph_repo)
        print_content_insights(content_insights)
        
        # Generate visualizations
        print("\n🎨 GENERATING VISUALIZATIONS")
        print("=" * 50)
        
        await generate_visualizations(graph_repo, doc_stats, entity_stats, rel_stats)
        
        print(f"\n✅ Analysis completed at: {datetime.now()}")
        
    except Exception as e:
        print(f"❌ Error during analysis: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # Close connections
        if 'graph_store' in locals():
            await graph_store.close()

async def get_document_statistics(graph_repo: GraphRepository) -> Dict[str, Any]:
    """Get comprehensive document statistics"""
    
    # Get total document count
    total_docs_query = "MATCH (d:Document) RETURN count(d) as total"
    total_docs_result = await graph_repo.graph_store.execute_query(total_docs_query)
    total_docs = total_docs_result[0]['total'] if total_docs_result else 0
    
    # Get documents by category
    category_query = """
    MATCH (d:Document) 
    WHERE d.category IS NOT NULL 
    RETURN d.category as category, count(d) as count 
    ORDER BY count DESC
    """
    category_result = await graph_repo.graph_store.execute_query(category_query)
    categories = {row['category']: row['count'] for row in category_result}
    
    # Get documents by data type
    type_query = """
    MATCH (d:Document) 
    WHERE d.data_type IS NOT NULL 
    RETURN d.data_type as data_type, count(d) as count
    """
    type_result = await graph_repo.graph_store.execute_query(type_query)
    data_types = {row['data_type']: row['count'] for row in type_result}
    
    # Get chunk statistics
    chunk_query = """
    MATCH (c:Chunk) 
    RETURN count(c) as total_chunks, 
           avg(size(c.content)) as avg_chunk_size,
           min(size(c.content)) as min_chunk_size,
           max(size(c.content)) as max_chunk_size
    """
    chunk_result = await graph_repo.graph_store.execute_query(chunk_query)
    chunk_stats = chunk_result[0] if chunk_result else {}
    
    return {
        'total_documents': total_docs,
        'categories': categories,
        'data_types': data_types,
        'chunk_stats': chunk_stats
    }

async def get_entity_statistics(graph_repo: GraphRepository) -> Dict[str, Any]:
    """Get entity extraction statistics"""
    
    # Get total entity count
    total_entities_query = "MATCH (e:Entity) RETURN count(e) as total"
    total_entities_result = await graph_repo.graph_store.execute_query(total_entities_query)
    total_entities = total_entities_result[0]['total'] if total_entities_result else 0
    
    # Get entities by type
    entity_type_query = """
    MATCH (e:Entity) 
    WHERE e.entity_type IS NOT NULL 
    RETURN e.entity_type as entity_type, count(e) as count 
    ORDER BY count DESC LIMIT 20
    """
    entity_type_result = await graph_repo.graph_store.execute_query(entity_type_query)
    entity_types = {row['entity_type']: row['count'] for row in entity_type_result}
    
    # Get most mentioned entities
    popular_entities_query = """
    MATCH (e:Entity)-[r:MENTIONS]-(c:Chunk)
    RETURN e.name as entity_name, e.entity_type as entity_type, count(r) as mention_count
    ORDER BY mention_count DESC LIMIT 20
    """
    popular_entities_result = await graph_repo.graph_store.execute_query(popular_entities_query)
    popular_entities = [
        {'name': row['entity_name'], 'type': row['entity_type'], 'mentions': row['mention_count']}
        for row in popular_entities_result
    ]
    
    return {
        'total_entities': total_entities,
        'entity_types': entity_types,
        'popular_entities': popular_entities
    }

async def get_relationship_statistics(graph_repo: GraphRepository) -> Dict[str, Any]:
    """Get relationship statistics"""
    
    # Get relationship type counts
    rel_type_query = """
    MATCH ()-[r]->() 
    RETURN type(r) as relationship_type, count(r) as count 
    ORDER BY count DESC
    """
    rel_type_result = await graph_repo.graph_store.execute_query(rel_type_query)
    relationship_types = {row['relationship_type']: row['count'] for row in rel_type_result}
    
    # Get documents with most entities
    doc_entity_query = """
    MATCH (d:Document)-[:CONTAINS]->(c:Chunk)-[:MENTIONS]->(e:Entity)
    RETURN d.title as document_title, count(DISTINCT e) as entity_count
    ORDER BY entity_count DESC LIMIT 10
    """
    doc_entity_result = await graph_repo.graph_store.execute_query(doc_entity_query)
    docs_with_entities = [
        {'title': row['document_title'], 'entity_count': row['entity_count']}
        for row in doc_entity_result
    ]
    
    return {
        'relationship_types': relationship_types,
        'docs_with_most_entities': docs_with_entities
    }

async def get_content_insights(graph_repo: GraphRepository) -> Dict[str, Any]:
    """Get content-based insights"""
    
    # Get technology mentions
    tech_query = """
    MATCH (e:Entity)-[:MENTIONS]-(c:Chunk)
    WHERE e.entity_type IN ['ORG', 'PRODUCT', 'TECHNOLOGY'] 
       OR e.name =~ '(?i).*(react|python|javascript|typescript|docker|kubernetes|aws|azure|api|database|sql|nosql|microservice|blockchain|ai|ml|machine learning|fastapi|django|flask).*'
    RETURN e.name as technology, count(*) as mentions
    ORDER BY mentions DESC LIMIT 15
    """
    tech_result = await graph_repo.graph_store.execute_query(tech_query)
    technologies = [{'name': row['technology'], 'mentions': row['mentions']} for row in tech_result]
    
    # Get business concepts
    business_query = """
    MATCH (e:Entity)-[:MENTIONS]-(c:Chunk)
    WHERE e.name =~ '(?i).*(strategy|business|client|customer|revenue|growth|marketing|sales|product|service|solution|development|consulting|freelancing|startup|mvp|prototype).*'
    RETURN e.name as concept, count(*) as mentions
    ORDER BY mentions DESC LIMIT 15
    """
    business_result = await graph_repo.graph_store.execute_query(business_query)
    business_concepts = [{'name': row['concept'], 'mentions': row['mentions']} for row in business_result]
    
    return {
        'technologies': technologies,
        'business_concepts': business_concepts
    }

def print_document_stats(stats: Dict[str, Any]):
    """Print document statistics"""
    print(f"📚 Total Documents: {stats['total_documents']}")
    
    if stats['categories']:
        print("\n📂 Documents by Category:")
        for category, count in list(stats['categories'].items())[:10]:
            print(f"   {category}: {count}")
    
    if stats['data_types']:
        print(f"\n📄 Data Types: {stats['data_types']}")
    
    if stats['chunk_stats']:
        chunk_stats = stats['chunk_stats']
        print(f"\n📝 Chunk Statistics:")
        print(f"   Total Chunks: {chunk_stats.get('total_chunks', 'N/A')}")
        print(f"   Average Chunk Size: {chunk_stats.get('avg_chunk_size', 'N/A'):.0f} chars")
        print(f"   Min Chunk Size: {chunk_stats.get('min_chunk_size', 'N/A')} chars")
        print(f"   Max Chunk Size: {chunk_stats.get('max_chunk_size', 'N/A')} chars")

def print_entity_stats(stats: Dict[str, Any]):
    """Print entity statistics"""
    print(f"🏷️  Total Entities: {stats['total_entities']}")
    
    if stats['entity_types']:
        print(f"\n📊 Entity Types:")
        for entity_type, count in list(stats['entity_types'].items())[:10]:
            print(f"   {entity_type}: {count}")
    
    if stats['popular_entities']:
        print(f"\n⭐ Most Mentioned Entities:")
        for entity in stats['popular_entities'][:10]:
            print(f"   {entity['name']} ({entity['type']}): {entity['mentions']} mentions")

def print_relationship_stats(stats: Dict[str, Any]):
    """Print relationship statistics"""
    if stats['relationship_types']:
        print(f"🔗 Relationship Types:")
        for rel_type, count in stats['relationship_types'].items():
            print(f"   {rel_type}: {count}")
    
    if stats['docs_with_most_entities']:
        print(f"\n📈 Documents with Most Entities:")
        for doc in stats['docs_with_most_entities']:
            title = doc['title'][:60] + "..." if len(doc['title']) > 60 else doc['title']
            print(f"   {title}: {doc['entity_count']} entities")

def print_content_insights(insights: Dict[str, Any]):
    """Print content insights"""
    if insights['technologies']:
        print(f"💻 Technology Mentions:")
        for tech in insights['technologies']:
            print(f"   {tech['name']}: {tech['mentions']} mentions")
    
    if insights['business_concepts']:
        print(f"\n💼 Business Concepts:")
        for concept in insights['business_concepts']:
            print(f"   {concept['name']}: {concept['mentions']} mentions")

async def generate_visualizations(graph_repo: GraphRepository, doc_stats: Dict, entity_stats: Dict, rel_stats: Dict):
    """Generate visualization files"""
    
    # Create visualizations directory
    viz_dir = Path("visualizations")
    viz_dir.mkdir(exist_ok=True)
    
    # Generate JSON data for web visualizations
    viz_data = {
        'document_stats': doc_stats,
        'entity_stats': entity_stats,
        'relationship_stats': rel_stats,
        'generated_at': datetime.now().isoformat()
    }
    
    with open(viz_dir / "knowledge_base_data.json", "w") as f:
        json.dump(viz_data, f, indent=2, default=str)
    
    print(f"📊 Generated visualization data: {viz_dir}/knowledge_base_data.json")
    
    # Generate simple HTML dashboard
    html_content = generate_html_dashboard(viz_data)
    with open(viz_dir / "dashboard.html", "w") as f:
        f.write(html_content)
    
    print(f"🌐 Generated HTML dashboard: {viz_dir}/dashboard.html")

def generate_html_dashboard(data: Dict) -> str:
    """Generate a simple HTML dashboard"""
    return f"""
<!DOCTYPE html>
<html>
<head>
    <title>Knowledge Base Dashboard</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        .container {{ max-width: 1200px; margin: 0 auto; }}
        .chart-container {{ width: 45%; display: inline-block; margin: 20px; }}
        .stats {{ background: #f5f5f5; padding: 20px; border-radius: 8px; margin: 20px 0; }}
        .stats h3 {{ margin-top: 0; }}
        .stat-item {{ margin: 10px 0; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>📊 Knowledge Base Dashboard</h1>
        <p>Generated at: {data.get('generated_at', 'Unknown')}</p>
        
        <div class="stats">
            <h3>📚 Document Overview</h3>
            <div class="stat-item">Total Documents: <strong>{data['document_stats']['total_documents']}</strong></div>
            <div class="stat-item">Total Entities: <strong>{data['entity_stats']['total_entities']}</strong></div>
            <div class="stat-item">Total Chunks: <strong>{data['document_stats']['chunk_stats'].get('total_chunks', 'N/A')}</strong></div>
        </div>
        
        <div class="chart-container">
            <canvas id="categoriesChart"></canvas>
        </div>
        
        <div class="chart-container">
            <canvas id="entityTypesChart"></canvas>
        </div>
        
        <script>
            // Categories Chart
            const categoriesData = {json.dumps(list(data['document_stats']['categories'].items())[:10])};
            const categoriesChart = new Chart(document.getElementById('categoriesChart'), {{
                type: 'pie',
                data: {{
                    labels: categoriesData.map(item => item[0]),
                    datasets: [{{
                        data: categoriesData.map(item => item[1]),
                        backgroundColor: ['#FF6384', '#36A2EB', '#FFCE56', '#4BC0C0', '#9966FF', '#FF9F40', '#FF6384', '#C9CBCF', '#4BC0C0', '#FF6384']
                    }}]
                }},
                options: {{
                    responsive: true,
                    plugins: {{
                        title: {{ display: true, text: 'Documents by Category' }}
                    }}
                }}
            }});
            
            // Entity Types Chart
            const entityTypesData = {json.dumps(list(data['entity_stats']['entity_types'].items())[:8])};
            const entityTypesChart = new Chart(document.getElementById('entityTypesChart'), {{
                type: 'bar',
                data: {{
                    labels: entityTypesData.map(item => item[0]),
                    datasets: [{{
                        label: 'Count',
                        data: entityTypesData.map(item => item[1]),
                        backgroundColor: '#36A2EB'
                    }}]
                }},
                options: {{
                    responsive: true,
                    plugins: {{
                        title: {{ display: true, text: 'Entity Types Distribution' }}
                    }}
                }}
            }});
        </script>
    </div>
</body>
</html>
"""

if __name__ == "__main__":
    asyncio.run(main())