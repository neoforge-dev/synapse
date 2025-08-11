import json
from pathlib import Path
from unittest.mock import AsyncMock, patch

from typer.testing import CliRunner

from graph_rag.cli.main import app
from graph_rag.cli.commands.store import _process_store_lines


def test_store_ingests_json_stream(tmp_path: Path):
    # Prepare a fake document JSON line from parse
    doc_path = tmp_path / "doc.md"
    doc_path.write_text("Hello store", encoding="utf-8")
    payload = {
        "path": str(doc_path.resolve()),
        "content": "Hello store",
        "metadata": {"foo": "bar"},
    }

    # Patch IngestionService used by store to avoid real IO
    with patch("graph_rag.cli.commands.store.IngestionService") as svc_cls:
        svc = AsyncMock()
        # Simulate an IngestionResult-like object
        ingestion_result = AsyncMock()
        ingestion_result.document_id = "doc-123"
        ingestion_result.chunk_ids = ["c1", "c2"]
        svc.ingest_document.return_value = ingestion_result  # type: ignore
        svc_cls.return_value = svc

        # Use pure function to avoid Click capture edge-case in CI
        outputs = _process_store_lines([json.dumps(payload)], embeddings=False, replace=True)
        line = outputs[0]
        obj = json.loads(line)
        assert obj["document_id"] == "doc-123"
        assert obj["num_chunks"] == 2


def test_store_emit_chunks_flag(tmp_path: Path):
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
        ingestion_result.chunk_ids = ["c10", "c11", "c12"]
        svc.ingest_document.return_value = ingestion_result  # type: ignore
        svc_cls.return_value = svc

        outputs = _process_store_lines([json.dumps(payload)], embeddings=False, replace=True)
        lines = outputs
        assert len(lines) == 1 + 3  # 1 summary + 3 chunks
        # First line summary
        summary = json.loads(lines[0])
        assert summary["document_id"] == "doc-xyz"
        # Following lines are chunk emissions
        chunk_ids = [json.loads(ln)["chunk_id"] for ln in lines[1:]]
        assert chunk_ids == ["c10", "c11", "c12"]
