from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

from typer.testing import CliRunner

from graph_rag.cli.main import app


def test_ingest_single_file_front_matter_parsed_and_merged(cli_runner: CliRunner, tmp_path: Path):
    file_path = tmp_path / "note.md"
    file_path.write_text(
        """---
inputs: example
aliases: alias1
created: 2024-01-02
updated_at: 2024-02-03
tags: ["ai", "notes"]
---
Body content here.
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
        # Return value doesn't matter; metadata is asserted via call args
        mock_process.return_value = MagicMock(document_id=str(file_path), num_chunks=1)

        result = cli_runner.invoke(app, ["ingest", str(file_path)])
        assert result.exit_code == 0

        assert mock_process.call_count == 1
        args, kwargs = mock_process.call_args
        assert args[0] == file_path
        meta = args[1]
        assert meta.get("inputs") == "example"
        assert meta.get("aliases") == ["alias1"]
        assert meta.get("created_at") == "2024-01-02"
        assert meta.get("updated_at") == "2024-02-03"
        assert meta.get("topics") == ["ai", "notes"]

        mock_echo.assert_any_call(
            f"Successfully processed and stored {file_path} including graph links."
        )


def test_ingest_directory_recursive_skips_obsidian_and_hidden_merges(cli_runner: CliRunner, tmp_path: Path):
    root = tmp_path / "vault"
    root.mkdir()

    file1 = root / "a.md"
    file1.write_text(
        """---
inputs: present
aliases: x
tags: "#tag1 #tag2"
---
file1 body
""",
        encoding="utf-8",
    )

    file2 = root / "b.txt"
    file2.write_text("file2 body", encoding="utf-8")

    hidden = root / ".hidden.md"
    hidden.write_text("should be skipped", encoding="utf-8")

    obsidian_dir = root / ".obsidian"
    obsidian_dir.mkdir()
    (obsidian_dir / "app.json").write_text("{}", encoding="utf-8")

    with (
        patch(
            "graph_rag.cli.commands.ingest.process_and_store_document",
            new_callable=AsyncMock,
        ) as mock_process,
        patch("graph_rag.cli.commands.ingest.typer.echo") as mock_echo,
    ):
        def side_effect(path: Path, metadata: dict):
            res = MagicMock()
            res.document_id = str(path)
            res.num_chunks = 1
            return res

        mock_process.side_effect = side_effect

        result = cli_runner.invoke(
            app,
            [
                "ingest",
                str(root),
                "--metadata",
                "{\"source\":\"vault\"}",
            ],
        )
        assert result.exit_code == 0

        # Only file1 and file2 should be processed
        called_paths = [call_args[0][0] for call_args in mock_process.call_args_list]
        assert set(called_paths) == {file1, file2}

        # Validate metadata merge/normalization for file1
        file1_call = next(c for c in mock_process.call_args_list if c[0][0] == file1)
        meta1 = file1_call[0][1]
        assert meta1.get("source") == "vault"
        assert meta1.get("aliases") == ["x"]
        assert meta1.get("topics") == ["tag1", "tag2"]

        # File2 should only have CLI metadata
        file2_call = next(c for c in mock_process.call_args_list if c[0][0] == file2)
        meta2 = file2_call[0][1]
        assert meta2 == {"source": "vault"}

        mock_echo.assert_any_call(
            f"Successfully processed and stored 2 files from {root}."
        )
