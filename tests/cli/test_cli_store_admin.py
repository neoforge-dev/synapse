import asyncio
import json
from unittest.mock import patch

import typer

from graph_rag.cli.commands import store as store_mod


def _capture_echo():
    outputs: list[str] = []

    def fake_echo(msg, *args, **kwargs):  # noqa: ARG001
        outputs.append(str(msg))

    return outputs, fake_echo


def test_store_stats_simple_store(monkeypatch):
    class DummyVS:
        async def get_vector_store_size(self):
            return 5

    monkeypatch.setattr(store_mod, "_get_vector_store", lambda *_args, **_kwargs: DummyVS())
    outputs, fake_echo = _capture_echo()
    with patch.object(typer, "echo", side_effect=fake_echo):
        store_mod.store_stats()
    assert outputs, "Expected output from store_stats"
    data = json.loads(outputs[0])
    assert data["vectors"] == 5
    assert "type" in data


def test_store_rebuild_simple_store(monkeypatch):
    class DummyVS:
        # No rebuild_index attribute to trigger fallback path
        pass

    monkeypatch.setattr(store_mod, "_get_vector_store", lambda *_args, **_kwargs: DummyVS())
    outputs, fake_echo = _capture_echo()
    with patch.object(typer, "echo", side_effect=fake_echo):
        store_mod.store_rebuild()
    assert outputs and "Rebuild not supported" in outputs[0]


def test_store_clear_requires_yes(monkeypatch):
    outputs, fake_echo = _capture_echo()
    with patch.object(typer, "echo", side_effect=fake_echo):
        try:
            store_mod.store_clear(confirm=False)
            assert False, "Expected typer.Exit"
        except typer.Exit as e:
            assert e.exit_code == 1
    assert outputs and "Refusing to clear without --yes" in outputs[0]


def test_store_clear_yes(monkeypatch):
    class DummyVS:
        async def delete_store(self):
            # simulate async deletion
            await asyncio.sleep(0)

    monkeypatch.setattr(store_mod, "_get_vector_store", lambda *_args, **_kwargs: DummyVS())
    outputs, fake_echo = _capture_echo()
    with patch.object(typer, "echo", side_effect=fake_echo):
        store_mod.store_clear(confirm=True)
    assert outputs and outputs[-1] == "Vector store cleared."
