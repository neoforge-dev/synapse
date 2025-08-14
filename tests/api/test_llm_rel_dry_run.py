import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from graph_rag.api import dependencies as deps
from graph_rag.api.main import create_app


@pytest.mark.unit
def test_ask_llm_rel_dry_run_plans_are_returned():
    app: FastAPI = create_app()

    class DummyEngine:
        async def query(self, text: str, config: dict):  # noqa: ARG002
            # Simulate the engine populating planned relationships in config
            config.setdefault("llm_relationships_planned", []).append(
                {"source_id": "s1", "target_id": "t1", "type": "KNOWS", "confidence": 0.9}
            )
            class R:
                answer = "x"
                class Chunk:
                    def __init__(self, id: str, text: str, doc_id: str):
                        self.id = id
                        self.text = text
                        self.document_id = doc_id
                        self.properties = {"score": 0.5}
                relevant_chunks = [Chunk("c1", "t1", "d1")]
            R.graph_context = ([], [])
            R.metadata = {"config": config}
            return R()

    with TestClient(app) as client:
        app.dependency_overrides[deps.get_graph_rag_engine] = lambda: DummyEngine()
        payload = {
            "text": "hello",
            "k": 2,
            "include_graph": True,
            "extract_relationships_persist": False,
            "extract_relationships_dry_run": True,
        }
        res = client.post("/api/v1/query/ask", json=payload)
        assert res.status_code == 200, res.text
        data = res.json()
        planned = data.get("metadata", {}).get("config", {}).get("llm_relationships_planned", [])
        assert planned and planned[0]["type"] == "KNOWS"
