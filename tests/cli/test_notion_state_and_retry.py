from pathlib import Path
from unittest.mock import MagicMock, patch

from typer.testing import CliRunner

from graph_rag.cli.main import app

runner = CliRunner()


def test_notion_state_corruption_recovery(tmp_path: Path):
    state_file = tmp_path / "state.json"
    # Write corrupted JSON
    state_file.write_text("{this is not: json}")

    with patch("graph_rag.cli.commands.notion.NotionClient") as MockClient:
        client = MockClient.return_value
        client.list_pages.return_value = {"results": [], "has_more": False}
        # Run dry-run; should not crash and should treat state as empty
        result = runner.invoke(
            app,
            [
                "notion",
                "sync",
                "--query",
                "abc",
                "--dry-run",
                "--state-file",
                str(state_file),
            ],
        )
        assert result.exit_code == 0, result.output


def test_notion_retry_budget_enforced(monkeypatch, tmp_path: Path):
    # Simulate repeated 429 responses and ensure client stops after configured retries
    class Resp:
        def __init__(self, code=429):
            self.status_code = code
            self.request = MagicMock()
            self.text = "rate limited"
            self.headers = {}

        def raise_for_status(self):  # pragma: no cover - not used directly
            raise RuntimeError("should not be called")

    calls = {"n": 0}

    def fake_request(method, url, json=None):  # noqa: ARG001
        calls["n"] += 1
        return Resp(429)

    # Patch httpx.Client to return our fake response
    class FakeClient:
        def __init__(self, *args, **kwargs):  # noqa: ARG002
            pass

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):  # noqa: ARG001
            return False

        def request(self, method, url, json=None):  # noqa: ARG001
            return fake_request(method, url, json)

    with patch("graph_rag.infrastructure.notion_client.httpx.Client", FakeClient):
        from graph_rag.config import Settings
        from graph_rag.infrastructure.notion_client import NotionClient

        # Configure small retry budget
        s = Settings(_env_file=None)
        # Hack: set secret to bypass key check
        object.__setattr__(s, "notion_api_key", type("S", (), {"get_secret_value": lambda self: "x"})())
        object.__setattr__(s, "notion_max_retries", 3)

        client = NotionClient(s)
        try:
            client.list_pages(query="x")
        except Exception:
            pass
        # Expect attempts == retries (loop counts attempts; request called each time)
        assert calls["n"] == 3
