import json
from unittest.mock import AsyncMock

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


async def test_graph_neighbors_endpoint(test_client: AsyncClient, mock_graph_repo: AsyncMock):
    # Mock neighbors for depth=1
    class Node:
        def __init__(self, id, type, properties=None):
            self.id = id
            self.type = type
            self.properties = properties or {}

    class Rel:
        def __init__(self, id, type, source_id, target_id, properties=None):
            self.id = id
            self.type = type
            self.source_id = source_id
            self.target_id = target_id
            self.properties = properties or {}

    mock_graph_repo.get_neighbors.return_value = (
        [Node("n2", "Person", {"name": "Bob"})],
        [Rel("r1", "FRIENDS", "n1", "n2", {"since": 2020})],
    )

    resp = await test_client.get("/api/v1/graph/neighbors", params={"id": "n1", "depth": 1})
    assert resp.status_code == 200
    data = resp.json()
    assert "nodes" in data and "edges" in data
    # Expect seed and neighbor
    ids = {n["id"] for n in data["nodes"]}
    assert {"n1", "n2"}.issubset(ids)
    assert any(e["type"] == "FRIENDS" and e["source"] == "n1" and e["target"] == "n2" for e in data["edges"])


async def test_graph_subgraph_endpoint(test_client: AsyncClient, mock_graph_repo: AsyncMock):
    # Mock subgraph query_subgraph response
    nodes = [
        {"id": "a", "type": "Person", "properties": {"name": "Alice"}},
        {"id": "b", "type": "Person", "properties": {"name": "Bob"}},
    ]
    edges = [
        {"id": "e1", "type": "KNOWS", "source": "a", "target": "b", "properties": {}}
    ]
    mock_graph_repo.query_subgraph.return_value = (nodes, edges)

    payload = {"seeds": ["a"], "depth": 2}
    resp = await test_client.post("/api/v1/graph/subgraph", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["nodes"][0]["id"] == "a"
    assert any(e["id"] == "e1" for e in data["edges"])


async def test_graph_export_cytoscape_json(test_client: AsyncClient, mock_graph_repo: AsyncMock):
    nodes = [
        {"id": "x", "type": "Topic", "properties": {"name": "ML"}},
        {"id": "y", "type": "Doc", "properties": {"title": "Paper"}},
    ]
    edges = [
        {"id": "e2", "type": "HAS_TOPIC", "source": "y", "target": "x", "properties": {}}
    ]
    mock_graph_repo.query_subgraph.return_value = (nodes, edges)

    resp = await test_client.get("/api/v1/graph/export", params={"format": "json", "seed": "y", "depth": 1})
    assert resp.status_code == 200
    body = resp.text
    data = json.loads(body)
    assert "elements" in data and "nodes" in data["elements"] and "edges" in data["elements"]
    node_ids = {n["data"]["id"] for n in data["elements"]["nodes"]}
    assert {"x", "y"}.issubset(node_ids)
    edge_ids = {e["data"]["id"] for e in data["elements"]["edges"]}
    assert "e2" in edge_ids


async def test_graph_export_graphml(test_client: AsyncClient, mock_graph_repo: AsyncMock):
    nodes = [
        {"id": "x", "type": "Topic", "properties": {"name": "ML"}},
        {"id": "y", "type": "Doc", "properties": {"title": "Paper"}},
    ]
    edges = [
        {"id": "e2", "type": "HAS_TOPIC", "source": "y", "target": "x", "properties": {}}
    ]
    mock_graph_repo.query_subgraph.return_value = (nodes, edges)

    resp = await test_client.get("/api/v1/graph/export", params={"format": "graphml", "seed": "y", "depth": 1})
    assert resp.status_code == 200
    body = resp.text
    assert body.startswith("<?xml") and "<graphml" in body and "<edge" in body and "<node" in body
