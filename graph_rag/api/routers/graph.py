import logging
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import PlainTextResponse

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

    return router
