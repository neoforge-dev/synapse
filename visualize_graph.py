#!/usr/bin/env python3
"""
Knowledge Graph Visualization Script
Generates interactive network visualizations of the knowledge graph.
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
    """Main visualization function"""
    print("🎨 Starting Knowledge Graph Visualization...")
    print(f"📅 Started at: {datetime.now()}")
    
    # Initialize settings and connections
    settings = get_settings()
    settings.memgraph_port = 7687  # Use default port
    
    try:
        # Initialize graph repository
        graph_repo = MemgraphGraphRepository(settings_obj=settings)
        
        print("\n🔍 Extracting graph data...")
        
        # Extract graph structure
        nodes, edges = await extract_graph_structure(graph_repo)
        
        print(f"📊 Extracted {len(nodes)} nodes and {len(edges)} edges")
        
        # Generate visualizations
        await generate_network_visualizations(nodes, edges)
        
        print(f"\n✅ Visualization completed at: {datetime.now()}")
        
    except Exception as e:
        print(f"❌ Error during visualization: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # Close connections
        if 'graph_repo' in locals():
            await graph_repo.close()

async def extract_graph_structure(graph_repo: MemgraphGraphRepository) -> Tuple[List[Dict], List[Dict]]:
    """Extract nodes and edges for visualization"""
    
    # Get sample of most connected entities and documents
    nodes_query = """
    MATCH (n)
    WHERE n:Entity OR n:Document
    OPTIONAL MATCH (n)-[r]->()
    WITH n, count(r) as out_connections
    OPTIONAL MATCH ()-[r2]->(n)
    WITH n, out_connections, count(r2) as in_connections
    WITH n, (out_connections + in_connections) as connections
    ORDER BY connections DESC
    LIMIT 500
    RETURN 
        id(n) as node_id,
        labels(n) as labels,
        n.name as name,
        n.title as title,
        n.entity_type as entity_type,
        n.category as category,
        connections
    """
    
    nodes_result = await graph_repo.execute_query(nodes_query)
    
    nodes = []
    node_ids = set()
    
    for row in nodes_result:
        node_id = row['node_id']
        node_ids.add(node_id)
        
        label = row['labels'][0] if row['labels'] else 'Unknown'
        name = row.get('name') or row.get('title') or f"{label}_{node_id}"
        
        # Ensure name is a string and truncate long names
        name = str(name) if name is not None else f"{label}_{node_id}"
        if len(name) > 50:
            name = name[:47] + "..."
        
        node = {
            'id': str(node_id),
            'label': name,
            'type': label,
            'entity_type': row.get('entity_type'),
            'category': row.get('category'),
            'connections': row['connections'],
            'size': min(max(row['connections'] * 2, 10), 50)  # Size based on connections
        }
        
        # Color coding
        if label == 'Entity':
            entity_type = row.get('entity_type', 'UNKNOWN')
            node['color'] = get_entity_color(entity_type)
            node['group'] = f"Entity_{entity_type}"
        elif label == 'Document':
            category = row.get('category', 'Unknown')
            node['color'] = get_document_color(category)
            node['group'] = f"Document_{category}"
        else:
            node['color'] = '#999999'
            node['group'] = label
        
        nodes.append(node)
    
    # Get edges between the selected nodes
    edges_query = f"""
    MATCH (a)-[r]->(b)
    WHERE id(a) IN {list(node_ids)} AND id(b) IN {list(node_ids)}
    RETURN 
        id(a) as source_id,
        id(b) as target_id,
        type(r) as relationship_type
    LIMIT 2000
    """
    
    edges_result = await graph_repo.execute_query(edges_query)
    
    edges = []
    for row in edges_result:
        edge = {
            'source': str(row['source_id']),
            'target': str(row['target_id']),
            'type': row['relationship_type'],
            'color': get_edge_color(row['relationship_type'])
        }
        edges.append(edge)
    
    return nodes, edges

def get_entity_color(entity_type: str) -> str:
    """Get color for entity type"""
    colors = {
        'PERSON': '#FF6B6B',      # Red
        'ORG': '#4ECDC4',         # Teal
        'PRODUCT': '#45B7D1',     # Blue
        'TECHNOLOGY': '#96CEB4',  # Green
        'GPE': '#FECA57',         # Yellow
        'MONEY': '#FF9FF3',       # Pink
        'DATE': '#FFA726',        # Orange
        'EVENT': '#AB47BC',       # Purple
    }
    return colors.get(entity_type, '#B0BEC5')  # Default gray

def get_document_color(category: str) -> str:
    """Get color for document category"""
    colors = {
        'CodeSwiftr': '#2196F3',      # Blue
        'LinkedIn': '#0077B5',        # LinkedIn Blue
        'case_studies': '#4CAF50',    # Green
        'content': '#FF9800',         # Orange
        'strategy': '#9C27B0',        # Purple
        'technical': '#607D8B',       # Blue Gray
    }
    # Default based on hash of category
    if category not in colors:
        hash_val = hash(category) % 7
        default_colors = ['#F44336', '#E91E63', '#9C27B0', '#673AB7', '#3F51B5', '#2196F3', '#03A9F4']
        return default_colors[hash_val]
    return colors[category]

def get_edge_color(relationship_type: str) -> str:
    """Get color for relationship type"""
    colors = {
        'MENTIONS': '#90A4AE',      # Gray
        'CONTAINS': '#66BB6A',      # Green
        'BELONGS_TO': '#42A5F5',    # Blue
        'RELATED_TO': '#FFA726',    # Orange
    }
    return colors.get(relationship_type, '#BDBDBD')

async def generate_network_visualizations(nodes: List[Dict], edges: List[Dict]):
    """Generate network visualization files"""
    
    # Create visualizations directory
    viz_dir = Path("visualizations")
    viz_dir.mkdir(exist_ok=True)
    
    # Generate network data
    network_data = {
        'nodes': nodes,
        'edges': edges,
        'generated_at': datetime.now().isoformat(),
        'stats': {
            'total_nodes': len(nodes),
            'total_edges': len(edges),
            'node_types': list(set(node['type'] for node in nodes)),
            'edge_types': list(set(edge['type'] for edge in edges))
        }
    }
    
    # Save network data as JSON
    with open(viz_dir / "network_data.json", "w") as f:
        json.dump(network_data, f, indent=2, default=str)
    
    print(f"📊 Generated network data: {viz_dir}/network_data.json")
    
    # Generate interactive network visualization
    html_content = generate_network_html(network_data)
    with open(viz_dir / "network_visualization.html", "w") as f:
        f.write(html_content)
    
    print(f"🌐 Generated network visualization: {viz_dir}/network_visualization.html")
    
    # Generate Cytoscape.js visualization
    cytoscape_html = generate_cytoscape_html(network_data)
    with open(viz_dir / "cytoscape_network.html", "w") as f:
        f.write(cytoscape_html)
    
    print(f"🎯 Generated Cytoscape network: {viz_dir}/cytoscape_network.html")

def generate_network_html(data: Dict) -> str:
    """Generate HTML with vis.js network visualization"""
    
    # Convert data for vis.js format
    vis_nodes = []
    for node in data['nodes']:
        vis_node = {
            'id': node['id'],
            'label': node['label'],
            'color': node['color'],
            'size': node['size'],
            'title': f"Type: {node['type']}<br/>Connections: {node['connections']}"
        }
        if node.get('entity_type'):
            vis_node['title'] += f"<br/>Entity Type: {node['entity_type']}"
        if node.get('category'):
            vis_node['title'] += f"<br/>Category: {node['category']}"
        vis_nodes.append(vis_node)
    
    vis_edges = []
    for edge in data['edges']:
        vis_edges.append({
            'from': edge['source'],
            'to': edge['target'],
            'color': edge['color'],
            'title': f"Relationship: {edge['type']}"
        })
    
    return f"""
<!DOCTYPE html>
<html>
<head>
    <title>Knowledge Graph Network</title>
    <script src="https://unpkg.com/vis-network/standalone/umd/vis-network.min.js"></script>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 0; padding: 20px; }}
        #network {{ width: 100%; height: 80vh; border: 1px solid #ccc; }}
        .controls {{ margin: 20px 0; }}
        .stats {{ background: #f5f5f5; padding: 15px; border-radius: 8px; margin: 20px 0; }}
        button {{ margin: 5px; padding: 8px 16px; cursor: pointer; }}
    </style>
</head>
<body>
    <h1>🔗 Knowledge Graph Network Visualization</h1>
    <p>Generated at: {data.get('generated_at', 'Unknown')}</p>
    
    <div class="stats">
        <h3>📊 Network Statistics</h3>
        <p><strong>Nodes:</strong> {data['stats']['total_nodes']} | <strong>Edges:</strong> {data['stats']['total_edges']}</p>
        <p><strong>Node Types:</strong> {', '.join(data['stats']['node_types'])}</p>
        <p><strong>Relationship Types:</strong> {', '.join(data['stats']['edge_types'])}</p>
    </div>
    
    <div class="controls">
        <button onclick="network.fit()">Fit to Screen</button>
        <button onclick="stabilize()">Stabilize</button>
        <button onclick="filterEntities()">Show Only Entities</button>
        <button onclick="filterDocuments()">Show Only Documents</button>
        <button onclick="showAll()">Show All</button>
    </div>
    
    <div id="network"></div>
    
    <script>
        const nodes = new vis.DataSet({json.dumps(vis_nodes)});
        const edges = new vis.DataSet({json.dumps(vis_edges)});
        
        const allNodes = nodes.get();
        const allEdges = edges.get();
        
        const container = document.getElementById('network');
        const data = {{ nodes: nodes, edges: edges }};
        
        const options = {{
            physics: {{
                enabled: true,
                stabilization: {{iterations: 100}},
                barnesHut: {{
                    gravitationalConstant: -8000,
                    centralGravity: 0.3,
                    springLength: 95,
                    springConstant: 0.04,
                    damping: 0.09
                }}
            }},
            nodes: {{
                shape: 'dot',
                scaling: {{
                    min: 10,
                    max: 50
                }},
                font: {{
                    size: 12,
                    face: 'Arial'
                }}
            }},
            edges: {{
                width: 2,
                smooth: {{
                    type: 'continuous'
                }}
            }},
            interaction: {{
                hover: true,
                tooltipDelay: 200
            }}
        }};
        
        const network = new vis.Network(container, data, options);
        
        // Control functions
        function stabilize() {{
            network.stabilize();
        }}
        
        function filterEntities() {{
            const entityNodes = allNodes.filter(node => node.title.includes('Type: Entity'));
            const entityNodeIds = new Set(entityNodes.map(n => n.id));
            const entityEdges = allEdges.filter(edge => 
                entityNodeIds.has(edge.from) && entityNodeIds.has(edge.to)
            );
            
            nodes.update(entityNodes);
            edges.update(entityEdges);
            network.fit();
        }}
        
        function filterDocuments() {{
            const docNodes = allNodes.filter(node => node.title.includes('Type: Document'));
            const docNodeIds = new Set(docNodes.map(n => n.id));
            const docEdges = allEdges.filter(edge => 
                docNodeIds.has(edge.from) && docNodeIds.has(edge.to)
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
        
        // Event handlers
        network.on("selectNode", function(params) {{
            const nodeId = params.nodes[0];
            const node = nodes.get(nodeId);
            console.log('Selected node:', node);
        }});
        
        network.on("selectEdge", function(params) {{
            const edgeId = params.edges[0];
            const edge = edges.get(edgeId);
            console.log('Selected edge:', edge);
        }});
    </script>
</body>
</html>
"""

def generate_cytoscape_html(data: Dict) -> str:
    """Generate HTML with Cytoscape.js visualization"""
    
    # Convert data for Cytoscape format
    cy_elements = []
    
    # Add nodes
    for node in data['nodes']:
        cy_elements.append({
            'data': {
                'id': node['id'],
                'label': node['label'],
                'type': node['type'],
                'entity_type': node.get('entity_type', ''),
                'category': node.get('category', ''),
                'connections': node['connections']
            },
            'style': {
                'background-color': node['color'],
                'width': node['size'],
                'height': node['size']
            }
        })
    
    # Add edges
    for edge in data['edges']:
        cy_elements.append({
            'data': {
                'id': f"{edge['source']}-{edge['target']}",
                'source': edge['source'],
                'target': edge['target'],
                'relationship': edge['type']
            },
            'style': {
                'line-color': edge['color']
            }
        })
    
    return f"""
<!DOCTYPE html>
<html>
<head>
    <title>Knowledge Graph - Cytoscape</title>
    <script src="https://unpkg.com/cytoscape@3.21.0/dist/cytoscape.min.js"></script>
    <script src="https://unpkg.com/cytoscape-cose-bilkent@4.1.0/cytoscape-cose-bilkent.js"></script>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 0; padding: 20px; }}
        #cy {{ width: 100%; height: 80vh; border: 1px solid #ccc; }}
        .controls {{ margin: 20px 0; }}
        .stats {{ background: #f5f5f5; padding: 15px; border-radius: 8px; margin: 20px 0; }}
        button {{ margin: 5px; padding: 8px 16px; cursor: pointer; }}
        .legend {{ margin: 20px 0; }}
        .legend-item {{ display: inline-block; margin: 5px 10px; }}
        .legend-color {{ width: 20px; height: 20px; display: inline-block; margin-right: 5px; vertical-align: middle; }}
    </style>
</head>
<body>
    <h1>🎯 Knowledge Graph - Advanced Network</h1>
    <p>Generated at: {data.get('generated_at', 'Unknown')}</p>
    
    <div class="stats">
        <h3>📊 Network Statistics</h3>
        <p><strong>Nodes:</strong> {data['stats']['total_nodes']} | <strong>Edges:</strong> {data['stats']['total_edges']}</p>
    </div>
    
    <div class="legend">
        <h4>🎨 Legend</h4>
        <div class="legend-item">
            <span class="legend-color" style="background-color: #FF6B6B;"></span>
            <span>Person</span>
        </div>
        <div class="legend-item">
            <span class="legend-color" style="background-color: #4ECDC4;"></span>
            <span>Organization</span>
        </div>
        <div class="legend-item">
            <span class="legend-color" style="background-color: #45B7D1;"></span>
            <span>Product</span>
        </div>
        <div class="legend-item">
            <span class="legend-color" style="background-color: #2196F3;"></span>
            <span>Document</span>
        </div>
    </div>
    
    <div class="controls">
        <button onclick="cy.fit()">Fit to Screen</button>
        <button onclick="runLayout('cose-bilkent')">Hierarchical Layout</button>
        <button onclick="runLayout('circle')">Circle Layout</button>
        <button onclick="runLayout('grid')">Grid Layout</button>
        <button onclick="showCentralNodes()">Show Central Nodes</button>
    </div>
    
    <div id="cy"></div>
    
    <script>
        const cy = cytoscape({{
            container: document.getElementById('cy'),
            
            elements: {json.dumps(cy_elements)},
            
            style: [
                {{
                    selector: 'node',
                    style: {{
                        'label': 'data(label)',
                        'font-size': '10px',
                        'text-valign': 'center',
                        'text-halign': 'center',
                        'color': '#333',
                        'text-outline-width': 2,
                        'text-outline-color': '#fff'
                    }}
                }},
                {{
                    selector: 'edge',
                    style: {{
                        'width': 2,
                        'curve-style': 'bezier',
                        'target-arrow-shape': 'triangle',
                        'target-arrow-color': '#999',
                        'line-color': '#999'
                    }}
                }},
                {{
                    selector: 'node:selected',
                    style: {{
                        'border-width': 3,
                        'border-color': '#000'
                    }}
                }}
            ],
            
            layout: {{
                name: 'cose-bilkent',
                animate: true,
                animationDuration: 1000,
                fit: true,
                padding: 30
            }}
        }});
        
        // Layout functions
        function runLayout(layoutName) {{
            const layout = cy.layout({{
                name: layoutName,
                animate: true,
                animationDuration: 1000,
                fit: true,
                padding: 30
            }});
            layout.run();
        }}
        
        function showCentralNodes() {{
            // Highlight nodes with many connections
            cy.nodes().forEach(node => {{
                const connections = node.data('connections');
                if (connections > 5) {{
                    node.style('border-width', '4px');
                    node.style('border-color', '#ff0000');
                }}
            }});
        }}
        
        // Event handlers
        cy.on('tap', 'node', function(evt) {{
            const node = evt.target;
            console.log('Node clicked:', node.data());
            
            // Highlight neighborhood
            const neighborhood = node.neighborhood().add(node);
            cy.elements().removeClass('highlighted').addClass('faded');
            neighborhood.removeClass('faded').addClass('highlighted');
        }});
        
        cy.on('tap', function(evt) {{
            if (evt.target === cy) {{
                // Clicked on background, remove highlighting
                cy.elements().removeClass('highlighted faded');
            }}
        }});
        
        // Add CSS for highlighting
        cy.style()
            .selector('.highlighted')
            .style({{
                'opacity': 1,
                'z-index': 999
            }})
            .selector('.faded')
            .style({{
                'opacity': 0.3
            }})
            .update();
    </script>
</body>
</html>
"""

if __name__ == "__main__":
    asyncio.run(main())