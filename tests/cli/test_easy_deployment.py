"""Test easy deployment commands for onboarding."""

from typer.testing import CliRunner
from graph_rag.cli.main import app

runner = CliRunner()


def test_synapse_up_command_exists():
    """Test that synapse up command exists and shows help."""
    result = runner.invoke(app, ["up", "--help"])
    assert result.exit_code == 0
    assert "Bring up required services via docker-compose" in result.output
    assert "--compose" in result.output
    assert "--detached" in result.output
    assert "--start-docker" in result.output
    assert "--wait-bolt" in result.output


def test_synapse_admin_up_command_exists():
    """Test that synapse admin up command exists and shows help."""
    result = runner.invoke(app, ["admin", "up", "--help"])
    assert result.exit_code == 0
    assert "Bring up Memgraph/API via docker compose" in result.output


def test_synapse_config_command_helps_onboarding():
    """Test that synapse config show command exists for onboarding."""
    result = runner.invoke(app, ["config", "show", "--help"])
    assert result.exit_code == 0
    assert "Show effective settings" in result.output