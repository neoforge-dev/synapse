import os

import pytest

from graph_rag.config import Settings


def test_graph_db_uri_alias_overrides_when_synapse_missing(monkeypatch):
    # Clear SYNAPSE_ vars to test alias behavior
    monkeypatch.delenv("SYNAPSE_MEMGRAPH_HOST", raising=False)
    monkeypatch.delenv("SYNAPSE_MEMGRAPH_PORT", raising=False)
    monkeypatch.delenv("SYNAPSE_MEMGRAPH_USE_SSL", raising=False)

    # Set GRAPH_DB_URI alias
    monkeypatch.setenv("GRAPH_DB_URI", "bolt://alias-host:7777")

    settings = Settings(_env_file=None)
    assert settings.memgraph_host == "alias-host"
    assert settings.memgraph_port == 7777
    assert settings.memgraph_use_ssl is False


def test_graph_db_uri_with_ssl_scheme(monkeypatch):
    monkeypatch.delenv("SYNAPSE_MEMGRAPH_USE_SSL", raising=False)
    monkeypatch.setenv("GRAPH_DB_URI", "bolt+s://secure-host:7687")

    settings = Settings(_env_file=None)
    assert settings.memgraph_host == "secure-host"
    assert settings.memgraph_use_ssl is True


def test_neo4j_username_password_aliases(monkeypatch):
    monkeypatch.delenv("SYNAPSE_MEMGRAPH_USER", raising=False)
    monkeypatch.delenv("SYNAPSE_MEMGRAPH_PASSWORD", raising=False)

    monkeypatch.setenv("NEO4J_USERNAME", "neo_user")
    monkeypatch.setenv("NEO4J_PASSWORD", "neo_pass")

    settings = Settings(_env_file=None)
    assert settings.memgraph_user == "neo_user"
    assert settings.memgraph_password.get_secret_value() == "neo_pass"


def test_synapse_vars_take_precedence_over_aliases(monkeypatch):
    monkeypatch.setenv("SYNAPSE_MEMGRAPH_HOST", "synapse-host")
    monkeypatch.setenv("SYNAPSE_MEMGRAPH_PORT", "9999")
    monkeypatch.setenv("GRAPH_DB_URI", "bolt://ignored-host:1234")

    settings = Settings(_env_file=None)
    assert settings.memgraph_host == "synapse-host"
    assert settings.memgraph_port == 9999
