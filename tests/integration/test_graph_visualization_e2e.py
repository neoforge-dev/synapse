"""End-to-end integration test for graph visualization feature."""

import pytest
from fastapi.testclient import TestClient


def test_graph_visualization_complete_workflow():
    """Test complete graph visualization workflow from API to CLI."""
    from graph_rag.api.main import create_app
    
    app = create_app()
    client = TestClient(app)
    
    # Test 1: HTML visualization endpoint
    response = client.get("/api/v1/graph/viz")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    content = response.content.decode()
    
    # Verify HTML contains essential elements
    assert "<html" in content
    assert "cytoscape" in content  # Graph library
    assert "Graph Visualization" in content
    assert "loadGraph" in content  # JS function
    
    # Test 2: HTML with seed parameter
    response = client.get("/api/v1/graph/viz?seed=test123")
    assert response.status_code == 200
    content = response.content.decode()
    assert "test123" in content  # Seed should be embedded
    
    # Test 3: Data endpoint returns proper JSON structure
    response = client.get("/api/v1/graph/viz/data")
    assert response.status_code == 200
    assert "application/json" in response.headers["content-type"]
    
    data = response.json()
    assert "nodes" in data
    assert "edges" in data
    assert isinstance(data["nodes"], list)
    assert isinstance(data["edges"], list)
    
    # Test 4: Data endpoint with filtering
    response = client.get("/api/v1/graph/viz/data?node_types=Document&edge_types=MENTIONS")
    assert response.status_code == 200
    data = response.json()
    assert "nodes" in data
    assert "edges" in data


def test_graph_viz_cli_integration():
    """Test that CLI command generates correct URLs."""
    from typer.testing import CliRunner
    from graph_rag.cli.main import app
    
    runner = CliRunner()
    
    # Test basic command
    result = runner.invoke(app, ["graph", "viz", "--no-open"])
    assert result.exit_code == 0
    assert "http://localhost:8000/api/v1/graph/viz" in result.output
    
    # Test with seed parameter
    result = runner.invoke(app, ["graph", "viz", "--seed", "node456", "--no-open"])
    assert result.exit_code == 0
    assert "seed=node456" in result.output
    
    # Test with custom host/port
    result = runner.invoke(app, ["graph", "viz", "--host", "127.0.0.1", "--port", "9000", "--no-open"])
    assert result.exit_code == 0
    assert "127.0.0.1:9000" in result.output


def test_visualization_feature_completeness():
    """Test that visualization feature provides complete functionality."""
    from graph_rag.api.main import create_app
    
    app = create_app()
    client = TestClient(app)
    
    # Test HTML contains interactive features
    response = client.get("/api/v1/graph/viz")
    content = response.content.decode()
    
    # Verify interactive controls
    assert "seedInput" in content  # Input for node ID
    assert "loadGraph" in content  # Load button functionality  
    assert "resetView" in content  # Reset view button
    
    # Verify styling and layout
    assert "cytoscape" in content  # Graph rendering library
    assert "cose" in content  # Layout algorithm
    assert "background-color" in content  # Node styling
    
    # Verify error handling
    assert "Error loading graph" in content  # Error handling in JS
    
    # Test data endpoint error handling (should gracefully handle empty data)
    response = client.get("/api/v1/graph/viz/data?seed=nonexistent")
    assert response.status_code == 200  # Should not crash
    data = response.json()
    assert "nodes" in data
    assert "edges" in data