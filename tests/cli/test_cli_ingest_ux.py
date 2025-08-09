from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import AsyncMock, patch

from typer.testing import CliRunner

from graph_rag.cli.main import app


def test_ingest_meta_flags_merge_order(tmp_path: Path):
    file_path = tmp_path / "note.md"
    file_path.write_text(
        """---
inputs: example
aliases: alias1
created: 2024-01-02
tags: ["ai"]
---
Body content.
""",
        encoding="utf-8",
    )

    meta_file = tmp_path / "meta.yaml"
    meta_file.write_text("source: filemeta\ntopics: [ml]\n", encoding="utf-8")

    runner = CliRunner()
    with patch(
        "graph_rag.cli.commands.ingest.process_and_store_document",
        new_callable=AsyncMock,
    ) as mock_process:
        mock_process.return_value = None
        result = runner.invoke(
            app,
            [
                "ingest",
                str(file_path),
                "--meta-file",
                str(meta_file),
                "--meta",
                "topics=nlp",
                "--metadata",
                '{"topics":["override"],"priority":"high"}',
                "--no-replace",
            ],
        )
        assert result.exit_code == 0
        # Validate merged metadata precedence: front matter < meta-file < --meta < --metadata
        call_args, call_kwargs = mock_process.call_args
        meta = call_args[1]
        assert meta.get("inputs") == "example"  # from front matter
        assert meta.get("source") == "filemeta"  # from meta-file
        assert meta.get("topics") == ["override"]  # JSON overrides others
        assert meta.get("priority") == "high"


def test_ingest_dry_run_json_single_file(tmp_path: Path):
    file_path = tmp_path / "a.md"
    file_path.write_text("# Title\nHello", encoding="utf-8")

    runner = CliRunner()
    result = runner.invoke(app, ["ingest", str(file_path), "--dry-run", "--json"])
    assert result.exit_code == 0
    # Should output a JSON array with one plan item
    data = json.loads(result.stdout or "[]")
    assert isinstance(data, list) and len(data) == 1
    item = data[0]
    assert item["path"].endswith("a.md")
    assert item["document_id"]
    assert item["id_source"]


def test_ingest_include_exclude_globs(tmp_path: Path):
    root = tmp_path / "vault"
    (root / "skip").mkdir(parents=True)
    (root / "keep").mkdir(parents=True)
    (root / "keep" / "k.md").write_text("keep", encoding="utf-8")
    (root / "skip" / "s.md").write_text("skip", encoding="utf-8")

    runner = CliRunner()
    with patch(
        "graph_rag.cli.commands.ingest.process_and_store_document",
        new_callable=AsyncMock,
    ) as mock_process:
        mock_process.return_value = None
        result = runner.invoke(
            app,
            [
                "ingest",
                str(root),
                "--include",
                "**/*.md",
                "--exclude",
                "skip/**",
                "--no-replace",
            ],
        )
        assert result.exit_code == 0
        called_paths = [str(ca[0][0]) for ca in mock_process.call_args_list]
        assert any(p.endswith("keep/k.md") for p in called_paths)
        assert not any(p.endswith("skip/s.md") for p in called_paths)


def test_ingest_from_stdin(tmp_path: Path):
    runner = CliRunner()
    with patch(
        "graph_rag.cli.commands.ingest.process_and_store_document",
        new_callable=AsyncMock,
    ) as mock_process:
        mock_process.return_value = None
        result = runner.invoke(
            app,
            [
                "ingest",
                str(tmp_path / "ignored.md"),
                "--stdin",
            ],
            input="Hello from stdin",
        )
        assert result.exit_code == 0
        # Ensure called exactly once with a synthetic path
        assert mock_process.call_count == 1
        call_args, _ = mock_process.call_args
        assert isinstance(call_args[0], Path)


def test_ingest_json_single_file_success(tmp_path: Path):
    file_path = tmp_path / "doc.md"
    file_path.write_text("content", encoding="utf-8")

    runner = CliRunner()
    with patch(
        "graph_rag.cli.commands.ingest.process_and_store_document",
        new_callable=AsyncMock,
    ) as mock_process:
        mock_process.return_value = {"document_id": "doc-1", "num_chunks": 2}
        result = runner.invoke(app, ["ingest", str(file_path), "--json"])
        assert result.exit_code == 0
        data = json.loads(result.stdout or "{}")
        assert data["document_id"] == "doc-1"
        assert data["num_chunks"] == 2


def test_ingest_json_directory_success(tmp_path: Path):
    (tmp_path / "a.md").write_text("A", encoding="utf-8")
    (tmp_path / "b.md").write_text("B", encoding="utf-8")

    runner = CliRunner()
    with patch(
        "graph_rag.cli.commands.ingest.process_and_store_document",
        new_callable=AsyncMock,
    ) as mock_process:
        # Return different ids per call
        async def side_effect(path: Path, *args, **kwargs):
            name = path.stem
            return {"document_id": f"{name}-id", "num_chunks": 1}

        mock_process.side_effect = side_effect
        result = runner.invoke(app, ["ingest", str(tmp_path), "--json"])
        assert result.exit_code == 0
        arr = json.loads(result.stdout or "[]")
        assert isinstance(arr, list) and len(arr) == 2
        ids = {item["document_id"] for item in arr}
        assert ids == {"a-id", "b-id"}
