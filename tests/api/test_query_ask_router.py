import json
from unittest.mock import AsyncMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from graph_rag.api.main import create_app
from graph_rag.api import dependencies as deps


@pytest.mark.unit
def test_query_ask_happy_path(monkeypatch):
    app: FastAPI = create_app()

    class DummyEngine:
        async def query(self, text: str, config: dict):  # noqa: ARG002
            class R:
                answer = "test answer"
                # simulate domain chunk object minimal interface
                class Chunk:
                    def __init__(self, id: str, text: str, doc_id: str, score: float):
                        self.id = id
                        self.text = text
                        self.document_id = doc_id
                        self.properties = {"score": score}

                relevant_chunks = [Chunk("c1", "t", "d1", 0.9)]
            
            # include_graph False => just a tuple of empty entities/relationships
            R.graph_context = ([], [])
            R.metadata = {"k": config.get("k")}
            return R()

    with TestClient(app) as client:
        app.dependency_overrides[deps.get_graph_rag_engine] = lambda: DummyEngine()
        payload = {"text": "hello", "k": 3, "include_graph": False}
        res = client.post("/api/v1/query/ask", json=payload)
        assert res.status_code == 200, res.text
        data = res.json()
        assert data["answer"] == "test answer"
        assert isinstance(data["relevant_chunks"], list)
        assert data["relevant_chunks"][0]["id"] == "c1"
        assert data["metadata"]["k"] == 3
