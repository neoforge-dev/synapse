from typer.testing import CliRunner

from graph_rag.cli.main import app


def test_top_level_up_delegates(monkeypatch, tmp_path):
    called = {"args": None}

    def fake_admin_up(**kwargs):  # type: ignore[no-redef]
        called["args"] = kwargs

    # Monkeypatch the imported function in main module namespace
    import graph_rag.cli.main as main_mod

    monkeypatch.setattr(main_mod, "admin_up", fake_admin_up)

    compose_file = tmp_path / "docker-compose.yml"
    compose_file.write_text("version: '3'\nservices: {}\n")

    runner = CliRunner(mix_stderr=False)
    result = runner.invoke(
        app,
        [
            "up",
            "--compose",
            str(compose_file),
            "--detached",
            "--no-start-docker",
            "--no-wait-bolt",
            "--wait-timeout",
            "5",
        ],
    )
    assert result.exit_code == 0, result.output
    assert called["args"] is not None
    assert called["args"]["compose_file"] == str(compose_file)
    assert called["args"]["detached"] is True
    assert called["args"]["start_docker"] is False
    assert called["args"]["wait_bolt"] is False
    assert called["args"]["wait_timeout"] == 5
