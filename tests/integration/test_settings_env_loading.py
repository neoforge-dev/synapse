import importlib
from pathlib import Path

import pytest


@pytest.mark.integration
def test_settings_loads_from_synapse_env(tmp_path, monkeypatch):
    home_dir = tmp_path / "home"
    synapse_dir = home_dir / ".synapse"
    synapse_dir.mkdir(parents=True)
    env_file = synapse_dir / ".env"
    env_file.write_text(
        "SYNAPSE_LLM_TYPE=mock\n"
        "SYNAPSE_VECTOR_ONLY_MODE=true\n"
        "SYNAPSE_API_PORT=9123\n"
    )

    monkeypatch.setenv("HOME", str(home_dir))
    monkeypatch.delenv("SYNAPSE_API_PORT", raising=False)
    monkeypatch.delenv("SYNAPSE_VECTOR_ONLY_MODE", raising=False)
    monkeypatch.delenv("SYNAPSE_LLM_TYPE", raising=False)

    # Ensure no local .env interferes by moving to a clean temp dir
    monkeypatch.chdir(tmp_path)

    config_module = importlib.import_module("graph_rag.config")
    importlib.reload(config_module)

    settings = config_module.get_settings()

    assert settings.api_port == 9123
    assert settings.vector_only_mode is True
    assert settings.llm_type == "mock"
