"""Test graph visualization endpoints using TDD approach."""

from fastapi.testclient import TestClient


def test_graph_viz_endpoint_returns_html():
    """Test that graph visualization endpoint returns interactive HTML."""
    from graph_rag.api.main import create_app

    app = create_app()
    client = TestClient(app)

    # Should return HTML page with graph visualization
    response = client.get("/api/v1/graph/viz")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    assert b"<html" in response.content
    assert b"graph" in response.content.lower()


def test_graph_viz_with_seed_node():
    """Test graph visualization with a specific seed node."""
    from graph_rag.api.main import create_app

    app = create_app()
    client = TestClient(app)

    # Should accept seed node parameter
    response = client.get("/api/v1/graph/viz?seed=node123")
    assert response.status_code == 200
    assert b"node123" in response.content


def test_graph_viz_data_endpoint():
    """Test that visualization can fetch graph data via API."""
    from graph_rag.api.main import create_app

    app = create_app()
    client = TestClient(app)

    # Should provide graph data in format suitable for visualization
    response = client.get("/api/v1/graph/viz/data?seed=test_node&depth=1")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/json")

    data = response.json()
    assert "nodes" in data
    assert "edges" in data
    assert isinstance(data["nodes"], list)
    assert isinstance(data["edges"], list)


def test_graph_viz_supports_filtering():
    """Test that visualization supports filtering by node/edge types."""
    from graph_rag.api.main import create_app

    app = create_app()
    client = TestClient(app)

    # Should accept filtering parameters
    response = client.get("/api/v1/graph/viz/data?node_types=Document,Entity&edge_types=MENTIONS")
    assert response.status_code == 200

    data = response.json()
    # Should return filtered results based on types
    assert "nodes" in data
    assert "edges" in data
