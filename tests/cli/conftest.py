"""CLI test fixtures."""

import pytest
from typer.testing import CliRunner


@pytest.fixture
def cli_runner():
    """Create a CLI runner for testing."""
    return CliRunner(mix_stderr=False)
