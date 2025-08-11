import io
import json
from pathlib import Path
from unittest.mock import AsyncMock, patch

import typer
from graph_rag.cli.commands.store import store_command


def test_store_cli_json_summary_only(tmp_path: Path):
    # Prepare input line
    doc_path = tmp_path / "doc.md"
    doc_path.write_text("Hello store", encoding="utf-8")
    payload = {
        "path": str(doc_path.resolve()),
        "content": "Hello store",
        "metadata": {"foo": "bar"},
    }

    with patch("graph_rag.cli.commands.store.IngestionService") as svc_cls:
        svc = AsyncMock()
        ingestion_result = AsyncMock()
        ingestion_result.document_id = "doc-001"
        ingestion_result.chunk_ids = ["c1", "c2", "c3"]
        svc.ingest_document.return_value = ingestion_result  # type: ignore
        svc_cls.return_value = svc

        # Monkeypatch stdin and echo
        input_text = json.dumps(payload) + "\n"
        outputs: list[str] = []

        def fake_echo(msg, *args, **kwargs):
            outputs.append(str(msg))

        def fake_get_text_stream(name):  # noqa: ARG001
            return io.StringIO(input_text)

        with patch.object(typer, "echo", side_effect=fake_echo):
            with patch.object(typer, "get_text_stream", side_effect=fake_get_text_stream):
                store_command(embeddings=False, replace=True, as_json=True, emit_chunks=False)

        lines = [ln for ln in outputs if ln.strip()]
        # Only the summary line should be emitted in --json mode without --emit-chunks
        assert len(lines) == 1
        summary = json.loads(lines[0])
        assert summary["document_id"] == "doc-001"
        assert summary["num_chunks"] == 3


def test_store_cli_json_with_emit_chunks(tmp_path: Path):
    doc_path = tmp_path / "doc.md"
    doc_path.write_text("Hello store", encoding="utf-8")
    payload = {
        "path": str(doc_path.resolve()),
        "content": "Hello store",
        "metadata": {},
    }

    with patch("graph_rag.cli.commands.store.IngestionService") as svc_cls:
        svc = AsyncMock()
        ingestion_result = AsyncMock()
        ingestion_result.document_id = "doc-xyz"
        ingestion_result.chunk_ids = ["cx", "cy"]
        svc.ingest_document.return_value = ingestion_result  # type: ignore
        svc_cls.return_value = svc

        input_text = json.dumps(payload) + "\n"
        outputs: list[str] = []

        def fake_echo(msg, *args, **kwargs):
            outputs.append(str(msg))

        def fake_get_text_stream(name):  # noqa: ARG001
            return io.StringIO(input_text)

        with patch.object(typer, "echo", side_effect=fake_echo):
            with patch.object(typer, "get_text_stream", side_effect=fake_get_text_stream):
                store_command(embeddings=False, replace=True, as_json=True, emit_chunks=True)

        lines = [ln for ln in outputs if ln.strip()]
        # Expect summary + 2 chunk lines
        assert len(lines) == 3
        summary = json.loads(lines[0])
        assert summary["document_id"] == "doc-xyz"
        chunk_lines = [json.loads(ln) for ln in lines[1:]]
        assert [cl["chunk_id"] for cl in chunk_lines] == ["cx", "cy"]
        assert all(cl["document_id"] == "doc-xyz" for cl in chunk_lines)
