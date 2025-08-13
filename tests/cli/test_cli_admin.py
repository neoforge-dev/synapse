from unittest.mock import patch

import pytest
import typer
from typer.testing import CliRunner

from graph_rag.cli.commands.admin import up as admin_up


def test_admin_up_fails_when_compose_missing():
    with pytest.raises(typer.Exit) as exc:
        admin_up(
            compose_file="./nope.yml",
            detached=True,
            start_docker=False,
            wait_bolt=False,
            wait_timeout=1,
        )
    assert exc.value.exit_code == 1


@patch("graph_rag.cli.commands.admin.subprocess.run")
@patch("graph_rag.cli.commands.admin._ensure_docker_running")
def test_admin_up_runs_docker_compose(mock_preflight, mock_run, tmp_path):
    compose_file = tmp_path / "docker-compose.yml"
    compose_file.write_text("version: '3'\nservices: {}\n")
    mock_run.return_value.returncode = 0

    admin_up(
        compose_file=str(compose_file),
        detached=True,
        start_docker=False,
        wait_bolt=False,
        wait_timeout=1,
    )
    mock_preflight.assert_called_once()
    # Ensure docker compose was invoked with provided file
    called = any(
        "docker" in str(args[0][0][0]) and "compose" in args[0][0] and str(compose_file) in args[0][0]
        for args in mock_run.call_args_list
    )
    assert called, f"docker compose not called with {compose_file}: {mock_run.call_args_list}"
