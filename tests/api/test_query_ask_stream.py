import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from graph_rag.api import dependencies as deps
from graph_rag.api.main import create_app


@pytest.mark.unit
def test_query_ask_stream_happy_path():
    app: FastAPI = create_app()

    class DummyEngine:
        async def stream_answer(self, text: str, config: dict):  # noqa: ARG002
            for token in ["hello", " ", "world"]:
                yield token

    with TestClient(app) as client:
        app.dependency_overrides[deps.get_graph_rag_engine] = lambda: DummyEngine()
        payload = {"text": "hello", "k": 2, "include_graph": False}
        resp = client.post("/api/v1/query/ask/stream", json=payload)
        assert resp.status_code == 200
        # Full body is available for StreamingResponse after request completes in TestClient
        assert resp.text == "hello world"
