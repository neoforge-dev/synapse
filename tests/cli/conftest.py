"""CLI test fixtures."""
import pytest
from typer.testing import CliRunner
import asyncio

from graph_rag.cli.main import app

@pytest.fixture
def cli_runner():
    """Create a CLI runner for testing."""
    return CliRunner(mix_stderr=False) 