import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import HTMLResponse, PlainTextResponse

from graph_rag.api.dependencies import get_graph_repository
from graph_rag.core.interfaces import GraphRepository

logger = logging.getLogger(__name__)


def create_graph_router() -> APIRouter:
    # No internal prefix; main app mounts with /graph
    router = APIRouter(tags=["Graph"])

    @router.get("/neighbors")
    async def neighbors(
        id: str = Query(..., description="Start node id"),
        depth: int = Query(1, ge=1, le=3, description="Traversal depth (1..3)"),
        types: str | None = Query(None, description="Comma-separated relationship types"),
        repo: Annotated[GraphRepository, Depends(get_graph_repository)] = None,
    ) -> dict:
        try:
            rel_types = [t.strip() for t in types.split(",") if t.strip()] if types else None
            nodes: list[dict] = []
            edges: list[dict] = []
            if depth == 1:
                neighs, rels = await repo.get_neighbors(id, relationship_types=rel_types)
                for n in neighs:
                    nodes.append({"id": n.id, "type": n.type, "properties": n.properties})
                nodes.append({"id": id, "type": "Node", "properties": {}})
                for r in rels:
                    edges.append(
                        {
                            "id": r.id,
                            "type": r.type,
                            "source": r.source_id,
                            "target": r.target_id,
                            "properties": r.properties,
                        }
                    )
            else:
                sub_nodes, sub_edges = await repo.query_subgraph(id, max_depth=depth, relationship_types=rel_types)
                nodes = sub_nodes
                edges = sub_edges
            unique_nodes = {n["id"]: n for n in nodes}.values()
            return {"nodes": list(unique_nodes), "edges": edges}
        except Exception as e:
            logger.error(f"neighbors failed: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail=str(e))

    @router.post("/subgraph")
    async def subgraph(
        payload: dict,
        repo: Annotated[GraphRepository, Depends(get_graph_repository)] = None,
    ) -> dict:
        try:
            seeds = payload.get("seeds") or []
            depth = int(payload.get("depth", 1))
            rel_types = payload.get("rel_types")
            if not seeds:
                raise HTTPException(status_code=400, detail="'seeds' is required")
            all_nodes: dict[str, dict] = {}
            all_edges: dict[str, dict] = {}
            for sid in seeds:
                nodes, edges = await repo.query_subgraph(sid, max_depth=depth, relationship_types=rel_types)
                for n in nodes:
                    all_nodes[n["id"]] = n
                for e in edges:
                    all_edges[str(e.get("id"))] = e
            return {"nodes": list(all_nodes.values()), "edges": list(all_edges.values())}
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"subgraph failed: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail=str(e))

    @router.get("/export")
    async def export_graph(
        format: str = Query("json", pattern="^(json|graphml)$"),
        seed: str | None = Query(None, description="Optional seed id to scope export"),
        depth: int = Query(1, ge=1, le=3),
        limit_nodes: int | None = Query(None, ge=1, description="Optional max nodes in export"),
        limit_edges: int | None = Query(None, ge=1, description="Optional max edges in export"),
        repo: Annotated[GraphRepository, Depends(get_graph_repository)] = None,
    ):
        try:
            if seed:
                nodes, edges = await repo.query_subgraph(seed, max_depth=depth)
            else:
                nodes, edges = [], []
            if isinstance(limit_nodes, int):
                nodes = nodes[: max(0, limit_nodes)]
            if isinstance(limit_edges, int):
                edges = edges[: max(0, limit_edges)]
            if format == "json":
                elements = {
                    "elements": {
                        "nodes": [{"data": {"id": n["id"], **n}} for n in nodes],
                        "edges": [
                            {
                                "data": {
                                    "id": e.get("id"),
                                    "source": e.get("source"),
                                    "target": e.get("target"),
                                    "label": e.get("type"),
                                    **e,
                                }
                            }
                            for e in edges
                        ],
                    }
                }
                # Return dict so FastAPI serializes to JSON object (not quoted string)
                return elements
            from xml.sax.saxutils import escape

            def node_xml(n: dict) -> str:
                return f"<node id=\"{escape(str(n['id']))}\" />"

            def edge_xml(e: dict) -> str:
                sid = escape(str(e.get("source")))
                tid = escape(str(e.get("target")))
                rid = escape(str(e.get("id")))
                label = escape(str(e.get("type", "RELATED_TO")))
                return f"<edge id=\"{rid}\" source=\"{sid}\" target=\"{tid}\"><data key=\"label\">{label}</data></edge>"

            body_nodes = "".join(node_xml(n) for n in nodes)
            body_edges = "".join(edge_xml(e) for e in edges)
            graphml = (
                "<?xml version=\"1.0\" encoding=\"UTF-8\"?>"
                "<graphml xmlns=\"http://graphml.graphdrawing.org/xmlns\" xmlns:xsi=\"http://www.w3.org/2001/XMLSchema-instance\" xsi:schemaLocation=\"http://graphml.graphdrawing.org/xmlns http://graphml.graphdrawing.org/xmlns/1.0/graphml.xsd\">"
                "<graph edgedefault=\"directed\">"
                f"{body_nodes}{body_edges}"
                "</graph>"
                "</graphml>"
            )
            # Return plain text/XML so body is not JSON-quoted
            return PlainTextResponse(graphml, media_type="application/xml")
        except Exception as e:
            logger.error(f"export failed: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail=str(e))

    @router.get("/viz", response_class=HTMLResponse)
    async def graph_visualization(
        seed: str | None = Query(None, description="Starting node for visualization"),
        depth: int = Query(1, ge=1, le=3, description="Graph traversal depth"),
        repo: Annotated[GraphRepository, Depends(get_graph_repository)] = None,
    ):
        """Interactive graph visualization interface."""
        try:
            html_content = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Business Intelligence Graph - Synapse</title>
    <script src="https://unpkg.com/cytoscape@3.26.0/dist/cytoscape.min.js"></script>
    <script src="https://unpkg.com/cytoscape-fcose@2.2.0/cytoscape-fcose.js"></script>
    <style>
        body {{ margin: 0; padding: 0; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); }}
        .header {{ background: rgba(255,255,255,0.95); padding: 20px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
        .title {{ color: #2c3e50; margin: 0; font-size: 24px; font-weight: 600; }}
        .subtitle {{ color: #7f8c8d; margin: 5px 0 0 0; font-size: 14px; }}
        .main-container {{ display: flex; height: calc(100vh - 80px); }}
        .sidebar {{ width: 300px; background: rgba(255,255,255,0.95); padding: 20px; overflow-y: auto; }}
        .graph-container {{ flex: 1; position: relative; }}
        #cy {{ width: 100%; height: 100%; background: linear-gradient(45deg, #f8f9fa 0%, #e9ecef 100%); }}
        
        .control-group {{ margin-bottom: 20px; }}
        .control-group h3 {{ color: #2c3e50; margin: 0 0 10px 0; font-size: 16px; }}
        .control-group input, .control-group select, .control-group button {{ 
            width: 100%; padding: 10px; margin: 5px 0; border: 1px solid #ddd; border-radius: 5px; font-size: 14px; 
        }}
        .control-group button {{ 
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; border: none; cursor: pointer; 
            transition: all 0.3s ease; font-weight: 500;
        }}
        .control-group button:hover {{ transform: translateY(-2px); box-shadow: 0 5px 15px rgba(0,0,0,0.2); }}
        
        .filter-checkbox {{ display: flex; align-items: center; margin: 5px 0; }}
        .filter-checkbox input {{ width: auto; margin-right: 8px; }}
        .filter-checkbox label {{ color: #2c3e50; font-size: 13px; }}
        
        .legend {{ background: white; border-radius: 8px; padding: 15px; margin-top: 20px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
        .legend h4 {{ margin: 0 0 10px 0; color: #2c3e50; }}
        .legend-item {{ display: flex; align-items: center; margin: 8px 0; }}
        .legend-color {{ width: 20px; height: 20px; border-radius: 50%; margin-right: 10px; }}
        .legend-label {{ font-size: 12px; color: #555; }}
        
        .stats {{ background: white; border-radius: 8px; padding: 15px; margin-top: 20px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
        .stats h4 {{ margin: 0 0 10px 0; color: #2c3e50; }}
        .stat-item {{ display: flex; justify-content: space-between; margin: 5px 0; font-size: 13px; }}
        .stat-label {{ color: #7f8c8d; }}
        .stat-value {{ font-weight: 600; color: #2c3e50; }}
        
        .node-info {{ 
            position: absolute; top: 20px; right: 20px; background: rgba(255,255,255,0.95); 
            padding: 15px; border-radius: 8px; box-shadow: 0 5px 20px rgba(0,0,0,0.2); 
            max-width: 300px; display: none; 
        }}
        .node-info h4 {{ margin: 0 0 10px 0; color: #2c3e50; }}
        .node-info .detail {{ margin: 5px 0; font-size: 13px; color: #555; }}
    </style>
</head>
<body>
    <div class="header">
        <h1 class="title">🔍 Business Intelligence Knowledge Graph</h1>
        <p class="subtitle">Interactive visualization of business entities, documents, and relationships</p>
    </div>
    
    <div class="main-container">
        <div class="sidebar">
            <div class="control-group">
                <h3>🎯 Graph Navigation</h3>
                <input type="text" id="seedInput" placeholder="Enter entity or document ID" value="{seed or ''}">
                <select id="depthSelect">
                    <option value="1">1 Level</option>
                    <option value="2" selected>2 Levels</option>
                    <option value="3">3 Levels</option>
                </select>
                <button onclick="loadGraph()">🔄 Load Graph</button>
                <button onclick="resetView()">🎯 Reset View</button>
                <button onclick="fitToView()">📐 Fit to View</button>
            </div>
            
            <div class="control-group">
                <h3>🔧 Layout Options</h3>
                <select id="layoutSelect" onchange="changeLayout()">
                    <option value="fcose">Force-Directed (Business)</option>
                    <option value="cose">Compound Spring</option>
                    <option value="circle">Circular</option>
                    <option value="grid">Grid</option>
                    <option value="breadthfirst">Hierarchical</option>
                </select>
            </div>
            
            <div class="control-group">
                <h3>🎨 Node Filters</h3>
                <div class="filter-checkbox">
                    <input type="checkbox" id="showDocuments" checked onchange="updateFilters()">
                    <label for="showDocuments">📄 Documents</label>
                </div>
                <div class="filter-checkbox">
                    <input type="checkbox" id="showEntities" checked onchange="updateFilters()">
                    <label for="showEntities">🏷️ Entities</label>
                </div>
                <div class="filter-checkbox">
                    <input type="checkbox" id="showChunks" checked onchange="updateFilters()">
                    <label for="showChunks">📝 Chunks</label>
                </div>
            </div>
            
            <div class="control-group">
                <h3>🔗 Relationship Filters</h3>
                <div class="filter-checkbox">
                    <input type="checkbox" id="showMentions" checked onchange="updateFilters()">
                    <label for="showMentions">MENTIONS</label>
                </div>
                <div class="filter-checkbox">
                    <input type="checkbox" id="showContains" checked onchange="updateFilters()">
                    <label for="showContains">CONTAINS</label>
                </div>
                <div class="filter-checkbox">
                    <input type="checkbox" id="showRelated" checked onchange="updateFilters()">
                    <label for="showRelated">RELATED_TO</label>
                </div>
            </div>
            
            <div class="legend">
                <h4>🎨 Node Types</h4>
                <div class="legend-item">
                    <div class="legend-color" style="background: #3498db;"></div>
                    <span class="legend-label">Documents</span>
                </div>
                <div class="legend-item">
                    <div class="legend-color" style="background: #e74c3c;"></div>
                    <span class="legend-label">Entities</span>
                </div>
                <div class="legend-item">
                    <div class="legend-color" style="background: #2ecc71;"></div>
                    <span class="legend-label">Chunks</span>
                </div>
                <div class="legend-item">
                    <div class="legend-color" style="background: #f39c12;"></div>
                    <span class="legend-label">Topics</span>
                </div>
            </div>
            
            <div class="stats">
                <h4>📊 Graph Statistics</h4>
                <div class="stat-item">
                    <span class="stat-label">Nodes:</span>
                    <span class="stat-value" id="nodeCount">0</span>
                </div>
                <div class="stat-item">
                    <span class="stat-label">Relationships:</span>
                    <span class="stat-value" id="edgeCount">0</span>
                </div>
                <div class="stat-item">
                    <span class="stat-label">Visible:</span>
                    <span class="stat-value" id="visibleCount">0</span>
                </div>
            </div>
        </div>
        
        <div class="graph-container">
            <div id="cy"></div>
            <div class="node-info" id="nodeInfo">
                <h4 id="nodeTitle">Node Details</h4>
                <div id="nodeDetails"></div>
            </div>
        </div>
    </div>
    
    <script>
        // Business-focused color scheme
        const nodeColors = {{
            'Document': '#3498db',
            'Entity': '#e74c3c', 
            'Chunk': '#2ecc71',
            'Topic': '#f39c12',
            'default': '#95a5a6'
        }};
        
        const edgeColors = {{
            'MENTIONS': '#8e44ad',
            'CONTAINS': '#27ae60',
            'RELATED_TO': '#2980b9',
            'default': '#bdc3c7'
        }};
        
        cytoscape.use(cytoscapeFcose);
        
        const cy = cytoscape({{
            container: document.getElementById('cy'),
            style: [
                {{
                    selector: 'node',
                    style: {{
                        'background-color': 'data(color)',
                        'label': 'data(name)',
                        'text-valign': 'center',
                        'text-halign': 'center',
                        'color': 'white',
                        'text-outline-width': 2,
                        'text-outline-color': 'data(color)',
                        'width': 'mapData(importance, 0, 1, 30, 60)',
                        'height': 'mapData(importance, 0, 1, 30, 60)',
                        'font-size': '12px',
                        'font-weight': 'bold',
                        'border-width': 2,
                        'border-color': '#fff',
                        'transition-property': 'background-color, border-color, width, height',
                        'transition-duration': '0.3s'
                    }}
                }},
                {{
                    selector: 'node:selected',
                    style: {{
                        'border-color': '#f1c40f',
                        'border-width': 4,
                        'background-color': '#f39c12'
                    }}
                }},
                {{
                    selector: 'node:hover',
                    style: {{
                        'background-color': '#34495e',
                        'width': 50,
                        'height': 50
                    }}
                }},
                {{
                    selector: 'edge',
                    style: {{
                        'width': 'mapData(weight, 0, 1, 2, 8)',
                        'line-color': 'data(color)',
                        'target-arrow-color': 'data(color)',
                        'target-arrow-shape': 'triangle',
                        'curve-style': 'bezier',
                        'label': 'data(type)',
                        'font-size': '10px',
                        'color': '#2c3e50',
                        'text-rotation': 'autorotate',
                        'text-background-color': 'white',
                        'text-background-opacity': 0.8,
                        'text-border-width': 1,
                        'text-border-color': '#bdc3c7',
                        'opacity': 0.8
                    }}
                }},
                {{
                    selector: 'edge:selected',
                    style: {{
                        'line-color': '#f1c40f',
                        'target-arrow-color': '#f1c40f',
                        'width': 6,
                        'opacity': 1
                    }}
                }},
                {{
                    selector: '.hidden',
                    style: {{
                        'display': 'none'
                    }}
                }}
            ],
            layout: {{ name: 'fcose', randomize: false, fit: true }}
        }});
        
        // Node click handler for details
        cy.on('tap', 'node', function(evt) {{
            const node = evt.target;
            const data = node.data();
            showNodeDetails(data);
        }});
        
        // Background click to hide details
        cy.on('tap', function(evt) {{
            if (evt.target === cy) {{
                hideNodeDetails();
            }}
        }});
        
        function showNodeDetails(data) {{
            const nodeInfo = document.getElementById('nodeInfo');
            const nodeTitle = document.getElementById('nodeTitle');
            const nodeDetails = document.getElementById('nodeDetails');
            
            nodeTitle.textContent = data.name || data.id;
            
            let details = `<div class="detail"><strong>Type:</strong> ${{data.type || 'Unknown'}}</div>`;
            details += `<div class="detail"><strong>ID:</strong> ${{data.id}}</div>`;
            
            if (data.properties) {{
                Object.entries(data.properties).forEach(([key, value]) => {{
                    if (key !== 'id' && key !== 'type' && key !== 'name') {{
                        details += `<div class="detail"><strong>${{key}}:</strong> ${{value}}</div>`;
                    }}
                }});
            }}
            
            nodeDetails.innerHTML = details;
            nodeInfo.style.display = 'block';
        }}
        
        function hideNodeDetails() {{
            document.getElementById('nodeInfo').style.display = 'none';
        }}
        
        async function loadGraph() {{
            const seed = document.getElementById('seedInput').value;
            const depth = document.getElementById('depthSelect').value;
            const url = seed ? `/api/v1/graph/viz/data?seed=${{seed}}&depth=${{depth}}` : '/api/v1/graph/viz/data';
            
            try {{
                const response = await fetch(url);
                const data = await response.json();
                
                const elements = [
                    ...data.nodes.map(n => ({{ 
                        data: {{ 
                            id: n.id, 
                            name: n.id.length > 20 ? n.id.substring(0, 17) + '...' : n.id,
                            type: n.type || 'Unknown',
                            color: nodeColors[n.type] || nodeColors.default,
                            importance: Math.random() * 0.5 + 0.5,
                            ...n 
                        }} 
                    }})),
                    ...data.edges.map(e => ({{ 
                        data: {{ 
                            id: e.id, 
                            source: e.source, 
                            target: e.target, 
                            type: e.type,
                            color: edgeColors[e.type] || edgeColors.default,
                            weight: Math.random() * 0.5 + 0.5,
                            ...e 
                        }} 
                    }}))
                ];
                
                cy.elements().remove();
                cy.add(elements);
                changeLayout();
                updateStats();
                updateFilters();
            }} catch (error) {{
                console.error('Error loading graph:', error);
                alert('Error loading graph data. Please check the console for details.');
            }}
        }}
        
        function changeLayout() {{
            const layout = document.getElementById('layoutSelect').value;
            const layoutOptions = {{
                'fcose': {{ name: 'fcose', randomize: false, fit: true, padding: 50 }},
                'cose': {{ name: 'cose', randomize: false, fit: true, padding: 50 }},
                'circle': {{ name: 'circle', fit: true, padding: 50 }},
                'grid': {{ name: 'grid', fit: true, padding: 50 }},
                'breadthfirst': {{ name: 'breadthfirst', directed: true, fit: true, padding: 50 }}
            }};
            cy.layout(layoutOptions[layout] || layoutOptions.fcose).run();
        }}
        
        function resetView() {{
            cy.fit();
            cy.center();
            hideNodeDetails();
        }}
        
        function fitToView() {{
            cy.fit(cy.elements(':visible'), 50);
        }}
        
        function updateFilters() {{
            const showDocs = document.getElementById('showDocuments').checked;
            const showEntities = document.getElementById('showEntities').checked;
            const showChunks = document.getElementById('showChunks').checked;
            const showMentions = document.getElementById('showMentions').checked;
            const showContains = document.getElementById('showContains').checked;
            const showRelated = document.getElementById('showRelated').checked;
            
            cy.nodes().forEach(node => {{
                const type = node.data('type');
                let show = true;
                
                if (type === 'Document' && !showDocs) show = false;
                if (type === 'Entity' && !showEntities) show = false;
                if (type === 'Chunk' && !showChunks) show = false;
                
                if (show) {{
                    node.removeClass('hidden');
                }} else {{
                    node.addClass('hidden');
                }}
            }});
            
            cy.edges().forEach(edge => {{
                const type = edge.data('type');
                let show = true;
                
                if (type === 'MENTIONS' && !showMentions) show = false;
                if (type === 'CONTAINS' && !showContains) show = false;
                if (type === 'RELATED_TO' && !showRelated) show = false;
                
                // Hide edge if either node is hidden
                const source = cy.getElementById(edge.data('source'));
                const target = cy.getElementById(edge.data('target'));
                if (source.hasClass('hidden') || target.hasClass('hidden')) show = false;
                
                if (show) {{
                    edge.removeClass('hidden');
                }} else {{
                    edge.addClass('hidden');
                }}
            }});
            
            updateStats();
        }}
        
        function updateStats() {{
            const totalNodes = cy.nodes().length;
            const totalEdges = cy.edges().length;
            const visibleNodes = cy.nodes(':visible').length;
            const visibleEdges = cy.edges(':visible').length;
            
            document.getElementById('nodeCount').textContent = totalNodes;
            document.getElementById('edgeCount').textContent = totalEdges;
            document.getElementById('visibleCount').textContent = `${{visibleNodes}}N + ${{visibleEdges}}E`;
        }}
        
        // Load initial graph if seed provided
        if ('{seed or ''}') {{
            loadGraph();
        }}
        
        // Keyboard shortcuts
        document.addEventListener('keydown', function(e) {{
            if (e.key === 'f' || e.key === 'F') {{
                fitToView();
            }} else if (e.key === 'r' || e.key === 'R') {{
                resetView();
            }} else if (e.key === 'Escape') {{
                hideNodeDetails();
            }}
        }});
    </script>
</body>
</html>
            """
            return HTMLResponse(content=html_content)
        except Exception as e:
            logger.error(f"graph visualization failed: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail=str(e))

    @router.get("/viz/data")
    async def graph_visualization_data(
        seed: str | None = Query(None, description="Starting node"),
        depth: int = Query(1, ge=1, le=3, description="Traversal depth"),
        node_types: str | None = Query(None, description="Comma-separated node types"),
        edge_types: str | None = Query(None, description="Comma-separated edge types"),
        repo: Annotated[GraphRepository, Depends(get_graph_repository)] = None,
    ):
        """Graph data endpoint for visualization."""
        try:
            if seed:
                nodes, edges = await repo.query_subgraph(seed, max_depth=depth)
            else:
                # Return empty graph for now - in production might want sample data
                nodes, edges = [], []

            # Apply filtering if specified
            if node_types:
                allowed_node_types = {t.strip() for t in node_types.split(",")}
                nodes = [n for n in nodes if n.get("type") in allowed_node_types]

            if edge_types:
                allowed_edge_types = {t.strip() for t in edge_types.split(",")}
                edges = [e for e in edges if e.get("type") in allowed_edge_types]

            return {"nodes": nodes, "edges": edges}
        except Exception as e:
            logger.error(f"graph visualization data failed: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail=str(e))

    return router
