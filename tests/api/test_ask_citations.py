import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from graph_rag.api.main import create_app
from graph_rag.api import dependencies as deps


@pytest.mark.unit
def test_ask_includes_citations_in_metadata():
    app: FastAPI = create_app()

    class DummyEngine:
        async def query(self, text: str, config: dict):  # noqa: ARG002
            class R:
                answer = "x"
                class Chunk:
                    def __init__(self, id: str, text: str, doc_id: str):
                        self.id = id
                        self.text = text
                        self.document_id = doc_id
                        self.properties = {"score": 0.5}
                relevant_chunks = [Chunk("c1", "t1", "d1"), Chunk("c2", "t2", "d2")]
            R.graph_context = ([], [])
            R.metadata = {}
            return R()

    with TestClient(app) as client:
        app.dependency_overrides[deps.get_graph_rag_engine] = lambda: DummyEngine()
        payload = {"text": "hello", "k": 2, "include_graph": False}
        res = client.post("/api/v1/query/ask", json=payload)
        assert res.status_code == 200, res.text
        data = res.json()
        cites = data.get("metadata", {}).get("citations", [])
        assert cites and {"chunk_id": "c1", "document_id": "d1"} in cites
