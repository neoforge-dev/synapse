import logging
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import PlainTextResponse, HTMLResponse

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
        types: Optional[str] = Query(None, description="Comma-separated relationship types"),
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
        seed: Optional[str] = Query(None, description="Optional seed id to scope export"),
        depth: int = Query(1, ge=1, le=3),
        limit_nodes: Optional[int] = Query(None, ge=1, description="Optional max nodes in export"),
        limit_edges: Optional[int] = Query(None, ge=1, description="Optional max edges in export"),
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
        seed: Optional[str] = Query(None, description="Starting node for visualization"),
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
    <title>Graph Visualization - Synapse</title>
    <script src="https://unpkg.com/cytoscape@3.26.0/dist/cytoscape.min.js"></script>
    <style>
        body {{ margin: 0; padding: 20px; font-family: Arial, sans-serif; }}
        #cy {{ width: 100%; height: 80vh; border: 1px solid #ccc; }}
        .controls {{ margin-bottom: 20px; }}
        .controls input, .controls button {{ margin: 5px; padding: 8px; }}
        h1 {{ color: #333; }}
    </style>
</head>
<body>
    <h1>Graph Visualization</h1>
    <div class="controls">
        <input type="text" id="seedInput" placeholder="Enter node ID" value="{seed or ''}">
        <button onclick="loadGraph()">Load Graph</button>
        <button onclick="resetView()">Reset View</button>
    </div>
    <div id="cy"></div>
    
    <script>
        const cy = cytoscape({{
            container: document.getElementById('cy'),
            style: [
                {{
                    selector: 'node',
                    style: {{
                        'background-color': '#666',
                        'label': 'data(id)',
                        'text-valign': 'center',
                        'color': 'white',
                        'text-outline-width': 2,
                        'text-outline-color': '#666',
                        'width': 30,
                        'height': 30
                    }}
                }},
                {{
                    selector: 'edge',
                    style: {{
                        'width': 2,
                        'line-color': '#ccc',
                        'target-arrow-color': '#ccc',
                        'target-arrow-shape': 'triangle',
                        'curve-style': 'bezier',
                        'label': 'data(type)',
                        'font-size': '10px'
                    }}
                }}
            ],
            layout: {{ name: 'cose' }}
        }});
        
        async function loadGraph() {{
            const seed = document.getElementById('seedInput').value;
            const url = seed ? `/graph/viz/data?seed=${{seed}}&depth={depth}` : '/graph/viz/data';
            
            try {{
                const response = await fetch(url);
                const data = await response.json();
                
                const elements = [
                    ...data.nodes.map(n => ({{ data: {{ id: n.id, ...n }} }})),
                    ...data.edges.map(e => ({{ data: {{ id: e.id, source: e.source, target: e.target, type: e.type, ...e }} }}))
                ];
                
                cy.elements().remove();
                cy.add(elements);
                cy.layout({{ name: 'cose' }}).run();
            }} catch (error) {{
                console.error('Error loading graph:', error);
                alert('Error loading graph data');
            }}
        }}
        
        function resetView() {{
            cy.fit();
            cy.center();
        }}
        
        // Load initial graph if seed provided
        if ('{seed or ''}') {{
            loadGraph();
        }}
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
        seed: Optional[str] = Query(None, description="Starting node"),
        depth: int = Query(1, ge=1, le=3, description="Traversal depth"),
        node_types: Optional[str] = Query(None, description="Comma-separated node types"),
        edge_types: Optional[str] = Query(None, description="Comma-separated edge types"),
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
