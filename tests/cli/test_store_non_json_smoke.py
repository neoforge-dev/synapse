import io
from typer.testing import CliRunner

from graph_rag.cli.main import app


def test_store_command_non_json_smoke(monkeypatch):
    runner = CliRunner()
    # minimal valid JSONL input for store
    input_text = '{"path": "./foo.txt", "content": "hello world", "metadata": {}}\n'
    # avoid hitting Memgraph by stubbing the processing function
    fake_outputs = [
        '{"document_id": "d1", "num_chunks": 1}',
        '{"chunk_id": "c1", "document_id": "d1"}',
    ]
    monkeypatch.setattr(
        "graph_rag.cli.commands.store._process_store_lines",
        lambda lines, embeddings, replace: fake_outputs,
        raising=True,
    )
    result = runner.invoke(app, ["store"], input=input_text)
    # non-json mode prints nothing and exits 0
    assert result.exit_code == 0
    assert result.stdout.strip() == ""
