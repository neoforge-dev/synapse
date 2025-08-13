import json
from pathlib import Path
from unittest.mock import patch, MagicMock

from typer.testing import CliRunner

from graph_rag.cli.main import app

runner = CliRunner()


def test_notion_dry_run_add_update_delete(tmp_path: Path):
    state_file = tmp_path / "state.json"

    # Initial state: page a exists
    state_file.write_text(json.dumps({"db:db1": {"last_edited_time": "2024-01-01T00:00:00Z", "pages": {"a": "2024-01-01T00:00:00Z"}}}))

    # Mock NotionClient methods
    with patch("graph_rag.cli.commands.notion.NotionClient") as MockClient:
        client = MockClient.return_value
        # Return two pages: a (updated) and b (new)
        client.query_database.return_value = {
            "results": [
                {"id": "a", "properties": {}, "last_edited_time": "2024-02-01T00:00:00Z"},
                {"id": "b", "properties": {}, "last_edited_time": "2024-01-15T00:00:00Z"},
            ],
            "has_more": False,
        }
        # Run dry-run
        result = runner.invoke(
            app,
            [
                "notion",
                "sync",
                "--db",
                "db1",
                "--dry-run",
                "--state-file",
                str(state_file),
            ],
        )
        assert result.exit_code == 0, result.output
        lines = [json.loads(l) for l in result.output.splitlines() if l.strip()]
        # Expect update for a, add for b, and delete for missing page c (not present in this run but existed in state)
        actions = {d["page_id"]: d["action"] for d in lines}
        assert actions.get("a") == "update"
        assert actions.get("b") == "add"
        # No delete expected because we didn't have c in state; ensure only 2 actions
        assert len(lines) == 2
