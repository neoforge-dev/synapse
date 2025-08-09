from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

from typer.testing import CliRunner

from graph_rag.cli.main import app


def test_ingest_notion_markdown_property_table_parsed(cli_runner: CliRunner, tmp_path: Path):
    file_path = tmp_path / "notion_page.md"
    file_path.write_text(
        """| Property | Value |
| --- | --- |
| Tags | #ml, #dl |
| Aliases | Deep Learning Overview |
| Created | 2023-05-06 |
| Last edited time | 2023-06-07 |

Content starts here.
""",
        encoding="utf-8",
    )

    with (
        patch(
            "graph_rag.cli.commands.ingest.process_and_store_document",
            new_callable=AsyncMock,
        ) as mock_process,
        patch("graph_rag.cli.commands.ingest.typer.echo") as mock_echo,
    ):
        mock_process.return_value = MagicMock(document_id=str(file_path), num_chunks=1)

        result = cli_runner.invoke(
            app,
            [
                "ingest",
                str(file_path),
                "--metadata",
                "{\"source\":\"notion\"}",
                "--replace",
            ],
        )
        assert result.exit_code == 0

        args, kwargs = mock_process.call_args
        assert args[0] == file_path
        meta = args[1]
        assert meta.get("source") == "notion"
        assert meta.get("topics") == ["ml", "dl"]
        assert meta.get("aliases") == ["Deep Learning Overview"]
        assert meta.get("created_at") == "2023-05-06"
        assert meta.get("updated_at") == "2023-06-07"

        mock_echo.assert_any_call(
            f"Successfully processed and stored {file_path} including graph links."
        )
