import json
from unittest.mock import MagicMock, patch

from typer.testing import CliRunner

from graph_rag.cli.main import app


def test_cli_suggest_happy_path_prints_answer():
    runner = CliRunner()
    fake_resp = MagicMock()
    fake_resp.json.return_value = {"answer": "Idea 1\nIdea 2"}
    fake_resp.raise_for_status.return_value = None

    with patch("httpx.Client") as client_cls:
        client = MagicMock()
        client.post.return_value = fake_resp
        client_cls.return_value.__enter__.return_value = client

        res = runner.invoke(app, ["suggest", "AI research roadmap", "--k", "3"])
        assert res.exit_code == 0, res.output
        assert "Idea 1" in res.stdout


def test_cli_suggest_json_output():
    runner = CliRunner()
    fake_resp = MagicMock()
    fake_resp.json.return_value = {"answer": "- idea A\n- idea B"}
    fake_resp.raise_for_status.return_value = None

    with patch("httpx.Client") as client_cls:
        client = MagicMock()
        client.post.return_value = fake_resp
        client_cls.return_value.__enter__.return_value = client

        res = runner.invoke(app, ["suggest", "marketing plan", "--json"])
        assert res.exit_code == 0, res.output
        data = json.loads(res.stdout.strip())
        assert data["topic"] == "marketing plan"
        assert "idea" in data["ideas"].lower()


def test_cli_suggest_http_error_returns_exit_code():
    # Avoid Click's stdout capture edge case by calling the function directly
    fake_resp = MagicMock()
    fake_resp.raise_for_status.side_effect = Exception("boom")

    with patch("httpx.Client") as client_cls:
        client = MagicMock()
        client.post.return_value = fake_resp
        client_cls.return_value.__enter__.return_value = client

        import typer

        from graph_rag.cli.commands.suggest import run_suggest

        try:
            run_suggest(topic="anything", json_out=False)
            assert False, "Expected typer.Exit to be raised"
        except typer.Exit as e:
            assert e.exit_code == 1
