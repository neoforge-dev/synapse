#!/usr/bin/env python3
"""
Business Intelligence Generator
Creates comprehensive business intelligence report from Graph-RAG knowledge base.
"""

import asyncio
import json
import sys
from pathlib import Path
from typing import Dict, List, Any, Set, Tuple
from datetime import datetime

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from graph_rag.infrastructure.graph_stores.memgraph_store import MemgraphGraphRepository
from graph_rag.config import get_settings

async def main():
    """Main business intelligence generation function"""
    print("🔍 Starting Business Intelligence Analysis...")
    print(f"📅 Started at: {datetime.now()}")
    
    # Initialize settings and connections
    settings = get_settings()
    
    try:
        # Initialize graph repository
        graph_repo = MemgraphGraphRepository(settings_obj=settings)
        
        print("\n📊 Extracting business intelligence data...")
        
        # Generate comprehensive business intelligence
        await generate_business_intelligence(graph_repo)
        
        print(f"\n✅ Analysis completed at: {datetime.now()}")
        
    except Exception as e:
        print(f"❌ Error during analysis: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # Close connections
        if 'graph_repo' in locals():
            await graph_repo.close()

async def generate_business_intelligence(graph_repo: MemgraphGraphRepository):
    """Generate comprehensive business intelligence report"""
    
    # Create visualizations directory
    viz_dir = Path("visualizations")
    viz_dir.mkdir(exist_ok=True)
    
    print("🔍 Analyzing entity distribution...")
    entities_data = await analyze_entities(graph_repo)
    
    print("🔗 Analyzing relationships...")
    relationships_data = await analyze_relationships(graph_repo)
    
    print("📚 Analyzing documents...")
    documents_data = await analyze_documents(graph_repo)
    
    print("💼 Analyzing business insights...")
    business_insights = await analyze_business_insights(graph_repo)
    
    print("🌐 Creating enhanced network visualization...")
    network_data = await create_enhanced_network(graph_repo)
    
    # Compile comprehensive report
    report_data = {
        'generated_at': datetime.now().isoformat(),
        'entities': entities_data,
        'relationships': relationships_data,
        'documents': documents_data,
        'business_insights': business_insights,
        'network': network_data
    }
    
    # Save comprehensive data
    with open(viz_dir / "comprehensive_intelligence.json", "w") as f:
        json.dump(report_data, f, indent=2, default=str)
    
    print(f"📊 Generated comprehensive intelligence: {viz_dir}/comprehensive_intelligence.json")
    
    # Generate enhanced HTML dashboard
    enhanced_dashboard = generate_enhanced_dashboard(report_data)
    with open(viz_dir / "enhanced_dashboard.html", "w") as f:
        f.write(enhanced_dashboard)
    
    print(f"🌐 Generated enhanced dashboard: {viz_dir}/enhanced_dashboard.html")
    
    # Update knowledge base data with business insights
    await update_knowledge_base_data(report_data, viz_dir)

async def analyze_entities(graph_repo: MemgraphGraphRepository) -> Dict:
    """Analyze entity distribution and patterns"""
    
    # Get entity statistics
    entity_stats_query = """
    MATCH (e:Entity)
    RETURN 
        e.entity_type as entity_type,
        e.name as entity_name,
        count(*) as frequency
    ORDER BY frequency DESC
    """
    
    entities_result = await graph_repo.execute_query(entity_stats_query)
    
    # Get top entities by type
    top_entities_query = """
    MATCH (e:Entity)
    WITH e.entity_type as type, e.name as name, count(*) as mentions
    RETURN type, collect({name: name, mentions: mentions})[0..10] as top_entities
    ORDER BY type
    """
    
    top_entities_result = await graph_repo.execute_query(top_entities_query)
    
    # Business-relevant entities
    business_entities_query = """
    MATCH (e:Entity)
    WHERE e.entity_type IN ['ORG', 'PERSON', 'PRODUCT', 'MONEY', 'GPE']
    OPTIONAL MATCH (e)-[r]-(d:Document)
    WITH e, count(r) as document_connections
    RETURN 
        e.name as name,
        e.entity_type as type,
        document_connections
    ORDER BY document_connections DESC
    LIMIT 50
    """
    
    business_entities_result = await graph_repo.execute_query(business_entities_query)
    
    return {
        'total_entities': len(entities_result),
        'entity_distribution': entities_result,
        'top_entities_by_type': top_entities_result,
        'business_entities': business_entities_result
    }

async def analyze_relationships(graph_repo: MemgraphGraphRepository) -> Dict:
    """Analyze relationship patterns"""
    
    # Relationship type distribution
    rel_types_query = """
    MATCH ()-[r]->()
    RETURN type(r) as relationship_type, count(r) as frequency
    ORDER BY frequency DESC
    """
    
    rel_types_result = await graph_repo.execute_query(rel_types_query)
    
    # Entity-to-entity relationships
    entity_relationships_query = """
    MATCH (e1:Entity)-[r]-(e2:Entity)
    RETURN 
        e1.name as entity1,
        e1.entity_type as type1,
        type(r) as relationship,
        e2.name as entity2,
        e2.entity_type as type2
    LIMIT 100
    """
    
    entity_rel_result = await graph_repo.execute_query(entity_relationships_query)
    
    return {
        'relationship_types': rel_types_result,
        'entity_relationships': entity_rel_result,
        'total_relationships': sum(row['frequency'] for row in rel_types_result)
    }

async def analyze_documents(graph_repo: MemgraphGraphRepository) -> Dict:
    """Analyze document patterns and metadata"""
    
    # Document metadata analysis
    doc_analysis_query = """
    MATCH (d:Document)
    OPTIONAL MATCH (d)-[r]-(e:Entity)
    WITH d, count(e) as entity_count
    RETURN 
        d.title as title,
        d.source as source,
        d.category as category,
        entity_count
    ORDER BY entity_count DESC
    """
    
    doc_result = await graph_repo.execute_query(doc_analysis_query)
    
    # Document sources
    source_analysis_query = """
    MATCH (d:Document)
    RETURN d.source as source, count(d) as document_count
    ORDER BY document_count DESC
    """
    
    source_result = await graph_repo.execute_query(source_analysis_query)
    
    return {
        'documents': doc_result,
        'sources': source_result,
        'total_documents': len(doc_result)
    }

async def analyze_business_insights(graph_repo: MemgraphGraphRepository) -> Dict:
    """Extract specific business insights from the knowledge graph"""
    
    # CodeSwiftr related entities
    codeswiftr_query = """
    MATCH (e:Entity)
    WHERE toLower(e.name) CONTAINS 'codeswiftr' OR toLower(e.name) CONTAINS 'codswiftr'
    OPTIONAL MATCH (e)-[r]-(related)
    RETURN e.name as entity, collect(DISTINCT related.name) as related_entities
    """
    
    codeswiftr_result = await graph_repo.execute_query(codeswiftr_query)
    
    # Technology entities
    tech_query = """
    MATCH (e:Entity)
    WHERE e.entity_type = 'ORG' AND (
        toLower(e.name) IN ['python', 'react', 'django', 'kubernetes', 'terraform', 'docker', 'aws'] OR
        toLower(e.name) CONTAINS 'api' OR
        toLower(e.name) CONTAINS 'cloud'
    )
    OPTIONAL MATCH (e)-[r]-(d:Document)
    WITH e, count(d) as document_mentions
    RETURN e.name as technology, document_mentions
    ORDER BY document_mentions DESC
    """
    
    tech_result = await graph_repo.execute_query(tech_query)
    
    # Person entities
    people_query = """
    MATCH (e:Entity)
    WHERE e.entity_type = 'PERSON'
    OPTIONAL MATCH (e)-[r]-(d:Document)
    WITH e, count(d) as document_mentions
    RETURN e.name as person, document_mentions
    ORDER BY document_mentions DESC
    LIMIT 20
    """
    
    people_result = await graph_repo.execute_query(people_query)
    
    # Client/Company entities
    companies_query = """
    MATCH (e:Entity)
    WHERE e.entity_type = 'ORG' AND e.name <> 'CodeSwiftr'
    OPTIONAL MATCH (e)-[r]-(d:Document)
    WITH e, count(d) as document_mentions
    RETURN e.name as company, document_mentions
    ORDER BY document_mentions DESC
    LIMIT 20
    """
    
    companies_result = await graph_repo.execute_query(companies_query)
    
    return {
        'codeswiftr_ecosystem': codeswiftr_result,
        'technology_stack': tech_result,
        'key_people': people_result,
        'client_companies': companies_result
    }

async def create_enhanced_network(graph_repo: MemgraphGraphRepository) -> Dict:
    """Create enhanced network data with entities and relationships"""
    
    # Get top entities
    entities_query = """
    MATCH (e:Entity)
    OPTIONAL MATCH (e)-[r]-(related)
    WITH e, count(r) as connections
    WHERE connections > 0
    RETURN 
        id(e) as node_id,
        e.name as name,
        e.entity_type as entity_type,
        connections
    ORDER BY connections DESC
    LIMIT 100
    """
    
    entities_result = await graph_repo.execute_query(entities_query)
    
    # Get documents with high entity connections
    docs_query = """
    MATCH (d:Document)
    OPTIONAL MATCH (d)-[r]-(e:Entity)
    WITH d, count(e) as entity_connections
    WHERE entity_connections > 3
    RETURN 
        id(d) as node_id,
        d.title as title,
        d.source as source,
        entity_connections
    ORDER BY entity_connections DESC
    LIMIT 20
    """
    
    docs_result = await graph_repo.execute_query(docs_query)
    
    # Get relationships between selected nodes
    all_node_ids = [str(row['node_id']) for row in entities_result + docs_result]
    
    if all_node_ids:
        relationships_query = f"""
        MATCH (a)-[r]->(b)
        WHERE id(a) IN {all_node_ids} AND id(b) IN {all_node_ids}
        RETURN 
            id(a) as source_id,
            id(b) as target_id,
            type(r) as relationship_type
        LIMIT 200
        """
        
        relationships_result = await graph_repo.execute_query(relationships_query)
    else:
        relationships_result = []
    
    # Format nodes
    nodes = []
    
    # Add entity nodes
    for row in entities_result:
        nodes.append({
            'id': str(row['node_id']),
            'label': row['name'] or f"Entity_{row['node_id']}",
            'type': 'Entity',
            'entity_type': row['entity_type'],
            'connections': row['connections'],
            'size': min(max(row['connections'] * 3, 15), 60),
            'color': get_entity_color(row['entity_type']),
            'group': f"Entity_{row['entity_type']}"
        })
    
    # Add document nodes
    for row in docs_result:
        title = row['title'] or f"Document_{row['node_id']}"
        if len(title) > 30:
            title = title[:27] + "..."
        
        nodes.append({
            'id': str(row['node_id']),
            'label': title,
            'type': 'Document',
            'source': row['source'],
            'connections': row['entity_connections'],
            'size': min(max(row['entity_connections'] * 2, 20), 50),
            'color': '#2196F3',
            'group': f"Document_{row['source'] or 'Unknown'}"
        })
    
    # Format edges
    edges = []
    for row in relationships_result:
        edges.append({
            'source': str(row['source_id']),
            'target': str(row['target_id']),
            'type': row['relationship_type'],
            'color': get_edge_color(row['relationship_type'])
        })
    
    return {
        'nodes': nodes,
        'edges': edges,
        'stats': {
            'total_nodes': len(nodes),
            'total_edges': len(edges),
            'entity_nodes': len(entities_result),
            'document_nodes': len(docs_result)
        }
    }

def get_entity_color(entity_type: str) -> str:
    """Get color for entity type"""
    colors = {
        'PERSON': '#FF6B6B',      # Red
        'ORG': '#4ECDC4',         # Teal
        'PRODUCT': '#45B7D1',     # Blue
        'GPE': '#FECA57',         # Yellow
        'MONEY': '#FF9FF3',       # Pink
        'DATE': '#FFA726',        # Orange
        'EVENT': '#AB47BC',       # Purple
        'CARDINAL': '#66BB6A',    # Green
        'ORDINAL': '#42A5F5',     # Light Blue
    }
    return colors.get(entity_type, '#B0BEC5')  # Default gray

def get_edge_color(relationship_type: str) -> str:
    """Get color for relationship type"""
    colors = {
        'MENTIONS': '#90A4AE',      # Gray
        'CONTAINS': '#66BB6A',      # Green
        'BELONGS_TO': '#42A5F5',    # Blue
        'RELATED_TO': '#FFA726',    # Orange
        'MENTIONS_TOPIC': '#AB47BC', # Purple
        'HAS_TOPIC': '#4CAF50',     # Green
    }
    return colors.get(relationship_type, '#BDBDBD')

def generate_enhanced_dashboard(data: Dict) -> str:
    """Generate enhanced HTML dashboard with business intelligence"""
    
    network_data = data['network']
    entities_data = data['entities']
    business_insights = data['business_insights']
    
    return f"""
<!DOCTYPE html>
<html>
<head>
    <title>📊 Business Intelligence Dashboard - Graph-RAG Analysis</title>
    <script src="https://unpkg.com/vis-network/standalone/umd/vis-network.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            margin: 0;
            padding: 0;
            background: #f8f9fa;
        }}
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            text-align: center;
        }}
        .container {{
            max-width: 1400px;
            margin: 0 auto;
            padding: 20px;
        }}
        .grid {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 20px;
            margin: 20px 0;
        }}
        .grid-3 {{
            display: grid;
            grid-template-columns: 1fr 1fr 1fr;
            gap: 20px;
            margin: 20px 0;
        }}
        .card {{
            background: white;
            border-radius: 12px;
            padding: 25px;
            box-shadow: 0 4px 20px rgba(0,0,0,0.1);
            border: 1px solid #e9ecef;
        }}
        .card h3 {{
            margin-top: 0;
            color: #495057;
            border-bottom: 2px solid #007bff;
            padding-bottom: 10px;
        }}
        .metric {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 15px 0;
            border-bottom: 1px solid #f1f3f4;
        }}
        .metric:last-child {{
            border-bottom: none;
        }}
        .metric-value {{
            font-weight: bold;
            color: #007bff;
            font-size: 1.2em;
        }}
        .tech-stack {{
            display: flex;
            flex-wrap: wrap;
            gap: 8px;
            margin: 15px 0;
        }}
        .tech-tag {{
            background: #e3f2fd;
            color: #1976d2;
            padding: 6px 12px;
            border-radius: 20px;
            font-size: 0.85em;
            font-weight: 500;
        }}
        .people-list {{
            max-height: 300px;
            overflow-y: auto;
        }}
        .person-item {{
            padding: 10px;
            border-left: 4px solid #28a745;
            margin: 8px 0;
            background: #f8fff9;
            border-radius: 4px;
        }}
        .company-item {{
            padding: 10px;
            border-left: 4px solid #fd7e14;
            margin: 8px 0;
            background: #fff8f0;
            border-radius: 4px;
        }}
        #network {{
            width: 100%;
            height: 600px;
            border: 1px solid #dee2e6;
            border-radius: 8px;
        }}
        .network-controls {{
            margin: 15px 0;
            text-align: center;
        }}
        .btn {{
            background: #007bff;
            color: white;
            border: none;
            padding: 10px 20px;
            border-radius: 6px;
            cursor: pointer;
            margin: 0 5px;
            font-size: 14px;
        }}
        .btn:hover {{
            background: #0056b3;
        }}
        .insight-box {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 20px;
            border-radius: 12px;
            margin: 20px 0;
        }}
        .insight-title {{
            font-size: 1.5em;
            margin-bottom: 15px;
        }}
        .chart-container {{
            height: 300px;
            position: relative;
        }}
        .full-width {{
            grid-column: 1 / -1;
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>📊 Business Intelligence Dashboard</h1>
        <p>Graph-RAG Knowledge Base Analysis</p>
        <p>Generated: {data['generated_at']}</p>
    </div>
    
    <div class="container">
        <div class="insight-box">
            <div class="insight-title">🎯 Executive Summary</div>
            <p>This dashboard presents a comprehensive analysis of {entities_data['total_entities']} entities across {data['documents']['total_documents']} documents, revealing business relationships, technology stack, and professional network insights.</p>
        </div>
        
        <div class="grid-3">
            <div class="card">
                <h3>📈 Knowledge Graph Metrics</h3>
                <div class="metric">
                    <span>Total Entities</span>
                    <span class="metric-value">{entities_data['total_entities']}</span>
                </div>
                <div class="metric">
                    <span>Documents</span>
                    <span class="metric-value">{data['documents']['total_documents']}</span>
                </div>
                <div class="metric">
                    <span>Relationships</span>
                    <span class="metric-value">{data['relationships']['total_relationships']}</span>
                </div>
                <div class="metric">
                    <span>Network Nodes</span>
                    <span class="metric-value">{network_data['stats']['total_nodes']}</span>
                </div>
            </div>
            
            <div class="card">
                <h3>💼 Business Ecosystem</h3>
                <div class="metric">
                    <span>CodeSwiftr Mentions</span>
                    <span class="metric-value">{len(business_insights['codeswiftr_ecosystem'])}</span>
                </div>
                <div class="metric">
                    <span>Technology Stack Items</span>
                    <span class="metric-value">{len(business_insights['technology_stack'])}</span>
                </div>
                <div class="metric">
                    <span>Key People</span>
                    <span class="metric-value">{len(business_insights['key_people'])}</span>
                </div>
                <div class="metric">
                    <span>Client Companies</span>
                    <span class="metric-value">{len(business_insights['client_companies'])}</span>
                </div>
            </div>
            
            <div class="card">
                <h3>🔗 Network Analysis</h3>
                <div class="metric">
                    <span>Entity Nodes</span>
                    <span class="metric-value">{network_data['stats']['entity_nodes']}</span>
                </div>
                <div class="metric">
                    <span>Document Nodes</span>
                    <span class="metric-value">{network_data['stats']['document_nodes']}</span>
                </div>
                <div class="metric">
                    <span>Network Edges</span>
                    <span class="metric-value">{network_data['stats']['total_edges']}</span>
                </div>
                <div class="metric">
                    <span>Avg Connections</span>
                    <span class="metric-value">{network_data['stats']['total_edges'] // max(network_data['stats']['total_nodes'], 1)}</span>
                </div>
            </div>
        </div>
        
        <div class="grid">
            <div class="card">
                <h3>🚀 Technology Stack</h3>
                <div class="tech-stack">
                    {generate_tech_tags(business_insights['technology_stack'])}
                </div>
                <div style="margin-top: 20px;">
                    <strong>Top Technologies by Mentions:</strong>
                    {generate_tech_list(business_insights['technology_stack'][:10])}
                </div>
            </div>
            
            <div class="card">
                <h3>👥 Key People Network</h3>
                <div class="people-list">
                    {generate_people_list(business_insights['key_people'][:15])}
                </div>
            </div>
        </div>
        
        <div class="grid">
            <div class="card">
                <h3>🏢 Client & Partner Companies</h3>
                <div>
                    {generate_companies_list(business_insights['client_companies'][:15])}
                </div>
            </div>
            
            <div class="card">
                <h3>📊 Entity Distribution</h3>
                <div class="chart-container">
                    <canvas id="entityChart"></canvas>
                </div>
            </div>
        </div>
        
        <div class="card full-width">
            <h3>🌐 Knowledge Network Visualization</h3>
            <div class="network-controls">
                <button class="btn" onclick="network.fit()">🔍 Fit View</button>
                <button class="btn" onclick="filterEntities()">👥 Show Entities Only</button>
                <button class="btn" onclick="filterDocuments()">📄 Show Documents Only</button>
                <button class="btn" onclick="showAll()">🌐 Show All</button>
                <button class="btn" onclick="highlightTech()">💻 Highlight Tech</button>
            </div>
            <div id="network"></div>
        </div>
    </div>
    
    <script>
        // Network Data
        const nodes = new vis.DataSet({json.dumps(network_data['nodes'])});
        const edges = new vis.DataSet({json.dumps(network_data['edges'])});
        
        const allNodes = nodes.get();
        const allEdges = edges.get();
        
        // Initialize Network
        const container = document.getElementById('network');
        const data = {{ nodes: nodes, edges: edges }};
        
        const options = {{
            physics: {{
                enabled: true,
                stabilization: {{iterations: 150}},
                barnesHut: {{
                    gravitationalConstant: -8000,
                    centralGravity: 0.3,
                    springLength: 120,
                    springConstant: 0.04,
                    damping: 0.09
                }}
            }},
            nodes: {{
                shape: 'dot',
                scaling: {{
                    min: 15,
                    max: 60
                }},
                font: {{
                    size: 11,
                    face: 'Arial',
                    color: '#333'
                }},
                borderWidth: 2,
                shadow: true
            }},
            edges: {{
                width: 2,
                smooth: {{
                    type: 'continuous'
                }},
                arrows: {{
                    to: {{ enabled: true, scaleFactor: 1 }}
                }}
            }},
            interaction: {{
                hover: true,
                tooltipDelay: 200,
                hideEdgesOnDrag: true
            }}
        }};
        
        const network = new vis.Network(container, data, options);
        
        // Network Control Functions
        function filterEntities() {{
            const entityNodes = allNodes.filter(node => node.type === 'Entity');
            const entityNodeIds = new Set(entityNodes.map(n => n.id));
            const entityEdges = allEdges.filter(edge => 
                entityNodeIds.has(edge.source) && entityNodeIds.has(edge.target)
            );
            
            nodes.update(entityNodes);
            edges.update(entityEdges);
            network.fit();
        }}
        
        function filterDocuments() {{
            const docNodes = allNodes.filter(node => node.type === 'Document');
            const docNodeIds = new Set(docNodes.map(n => n.id));
            const docEdges = allEdges.filter(edge => 
                docNodeIds.has(edge.source) && docNodeIds.has(edge.target)
            );
            
            nodes.update(docNodes);
            edges.update(docEdges);
            network.fit();
        }}
        
        function showAll() {{
            nodes.update(allNodes);
            edges.update(allEdges);
            network.fit();
        }}
        
        function highlightTech() {{
            const techNodes = allNodes.filter(node => 
                node.entity_type === 'ORG' && 
                ['Python', 'React', 'Django', 'Kubernetes', 'Terraform', 'Docker'].includes(node.label)
            );
            
            // Reset all nodes
            nodes.update(allNodes.map(node => ({{
                ...node,
                borderWidth: node.type === 'Entity' && techNodes.some(tech => tech.id === node.id) ? 5 : 2,
                color: node.color
            }})));
        }}
        
        // Event Handlers
        network.on("selectNode", function(params) {{
            const nodeId = params.nodes[0];
            const node = nodes.get(nodeId);
            console.log('Selected node:', node);
            
            // Highlight connected nodes
            const connectedNodes = network.getConnectedNodes(nodeId);
            const connectedEdges = network.getConnectedEdges(nodeId);
            
            // Visual feedback
            nodes.update(allNodes.map(n => ({{
                ...n,
                opacity: connectedNodes.includes(n.id) || n.id === nodeId ? 1.0 : 0.3
            }})));
        }});
        
        network.on("deselectNode", function() {{
            // Reset opacity
            nodes.update(allNodes.map(n => ({{
                ...n,
                opacity: 1.0
            }})));
        }});
        
        // Entity Distribution Chart
        const entityCtx = document.getElementById('entityChart').getContext('2d');
        const entityDistribution = {json.dumps([
            {'type': etype, 'count': sum(1 for e in entities_data['entity_distribution'] if e.get('entity_type') == etype)}
            for etype in ['ORG', 'PERSON', 'GPE', 'MONEY', 'DATE', 'CARDINAL', 'ORDINAL']
        ])};
        
        new Chart(entityCtx, {{
            type: 'doughnut',
            data: {{
                labels: entityDistribution.map(item => item.type),
                datasets: [{{
                    data: entityDistribution.map(item => item.count),
                    backgroundColor: [
                        '#4ECDC4', '#FF6B6B', '#FECA57', '#FF9FF3', 
                        '#FFA726', '#66BB6A', '#42A5F5'
                    ]
                }}]
            }},
            options: {{
                responsive: true,
                maintainAspectRatio: false,
                plugins: {{
                    title: {{ display: true, text: 'Entity Type Distribution' }}
                }}
            }}
        }});
    </script>
</body>
</html>
"""

def generate_tech_tags(tech_stack: List[Dict]) -> str:
    """Generate HTML for technology tags"""
    tags = []
    for tech in tech_stack[:20]:  # Top 20 technologies
        tags.append(f'<span class="tech-tag">{tech["technology"]}</span>')
    return ''.join(tags)

def generate_tech_list(tech_stack: List[Dict]) -> str:
    """Generate HTML list for technologies"""
    items = []
    for tech in tech_stack:
        items.append(f'<div class="metric"><span>{tech["technology"]}</span><span class="metric-value">{tech["document_mentions"]}</span></div>')
    return ''.join(items)

def generate_people_list(people: List[Dict]) -> str:
    """Generate HTML list for people"""
    items = []
    for person in people:
        items.append(f'<div class="person-item"><strong>{person["person"]}</strong><br><small>{person["document_mentions"]} document mentions</small></div>')
    return ''.join(items)

def generate_companies_list(companies: List[Dict]) -> str:
    """Generate HTML list for companies"""
    items = []
    for company in companies:
        items.append(f'<div class="company-item"><strong>{company["company"]}</strong><br><small>{company["document_mentions"]} document mentions</small></div>')
    return ''.join(items)

async def update_knowledge_base_data(report_data: Dict, viz_dir: Path):
    """Update the knowledge base data JSON with enhanced business intelligence"""
    
    # Read existing knowledge base data
    kb_data_file = viz_dir / "knowledge_base_data.json"
    if kb_data_file.exists():
        with open(kb_data_file, 'r') as f:
            kb_data = json.load(f)
    else:
        kb_data = {}
    
    # Enhance with business intelligence
    kb_data['business_intelligence'] = {
        'generated_at': report_data['generated_at'],
        'entity_analysis': report_data['entities'],
        'business_insights': report_data['business_insights'],
        'network_stats': report_data['network']['stats']
    }
    
    # Save enhanced data
    with open(kb_data_file, 'w') as f:
        json.dump(kb_data, f, indent=2, default=str)
    
    print(f"📊 Updated knowledge base data: {kb_data_file}")

if __name__ == "__main__":
    asyncio.run(main())