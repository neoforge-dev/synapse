import os

import pytest

from graph_rag.config import Settings
from graph_rag.infrastructure.graph_stores.memgraph_store import (
    MemgraphConnectionConfig,
)


def test_memgraph_connection_config_uses_settings_defaults(monkeypatch):
    # Ensure no MEMGRAPH_ envs are set, to force default-from-Settings path
    monkeypatch.delenv("MEMGRAPH_HOST", raising=False)
    monkeypatch.delenv("MEMGRAPH_PORT", raising=False)
    monkeypatch.delenv("MEMGRAPH_USE_SSL", raising=False)

    settings = Settings(_env_file=None)
    cfg = MemgraphConnectionConfig(settings_obj=settings)

    assert cfg.host == settings.memgraph_host
    assert cfg.port == settings.memgraph_port
    assert cfg.use_ssl == settings.memgraph_use_ssl


def test_memgraph_connection_config_overrides_from_env(monkeypatch):
    # When MEMGRAPH_ envs are set, those should override
    monkeypatch.setenv("MEMGRAPH_HOST", "envhost")
    monkeypatch.setenv("MEMGRAPH_PORT", "7777")
    monkeypatch.setenv("MEMGRAPH_USE_SSL", "true")

    cfg = MemgraphConnectionConfig()
    assert cfg.host == "envhost"
    assert cfg.port == 7777
    assert cfg.use_ssl is True
