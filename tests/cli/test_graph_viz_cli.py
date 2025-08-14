"""Test CLI command for graph visualization."""

from typer.testing import CliRunner

from graph_rag.cli.main import app

runner = CliRunner()


def test_graph_viz_command_exists():
    """Test that graph viz command exists and shows help."""
    result = runner.invoke(app, ["graph", "viz", "--help"])
    assert result.exit_code == 0
    assert "visualization" in result.output.lower()


def test_graph_viz_command_opens_url():
    """Test that graph viz command can construct proper URL."""
    result = runner.invoke(app, ["graph", "viz", "--seed", "test_node", "--port", "8000"])
    assert result.exit_code == 0
    assert "http://localhost:8000/api/v1/graph/viz" in result.output
    assert "seed=test_node" in result.output
