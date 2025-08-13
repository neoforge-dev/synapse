import json
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from graph_rag.api.main import create_app
from graph_rag.api import dependencies as deps


@pytest.mark.unit
def test_neighbors_types_filter(monkeypatch):
    app: FastAPI = create_app()

    class Node:
        def __init__(self, id, type, props=None):
            self.id = id
            self.type = type
            self.properties = props or {}

    class Rel:
        def __init__(self, id, type, s, t, props=None):
            self.id = id
            self.type = type
            self.source_id = s
            self.target_id = t
            self.properties = props or {}

    class Repo:
        async def get_neighbors(self, entity_id: str, relationship_types=None, direction="both"):
            assert relationship_types == ["FRIENDS"], "types filter not passed through"
            return [Node("n2", "Person")], [Rel("r1", "FRIENDS", entity_id, "n2")]

    with TestClient(app) as client:
        app.dependency_overrides[deps.get_graph_repository] = lambda: Repo()
        resp = client.get("/api/v1/graph/neighbors", params={"id": "n1", "types": "FRIENDS"})
        assert resp.status_code == 200
        data = resp.json()
        assert any(e["type"] == "FRIENDS" for e in data["edges"])  # filtered


@pytest.mark.unit
def test_export_pagination_limits():
    app: FastAPI = create_app()

    class Repo:
        async def query_subgraph(self, seed, max_depth=1, relationship_types=None):  # noqa: ARG002
            nodes = [{"id": str(i), "type": "T", "properties": {}} for i in range(10)]
            edges = [
                {"id": f"e{i}", "type": "R", "source": str(i), "target": str(i + 1), "properties": {}}
                for i in range(9)
            ]
            return nodes, edges

    with TestClient(app) as client:
        from graph_rag.api import dependencies as deps

        app.dependency_overrides[deps.get_graph_repository] = lambda: Repo()
        resp = client.get("/api/v1/graph/export", params={"format": "json", "seed": "0", "limit_nodes": 3, "limit_edges": 2})
        assert resp.status_code == 200
        body = resp.text
        data = json.loads(body)
        assert len(data["elements"]["nodes"]) == 3
        assert len(data["elements"]["edges"]) == 2
