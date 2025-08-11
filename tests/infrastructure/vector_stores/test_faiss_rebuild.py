import json
from pathlib import Path

import numpy as np
import pytest

from graph_rag.infrastructure.vector_stores.faiss_vector_store import FaissVectorStore
from graph_rag.core.interfaces import ChunkData


@pytest.mark.parametrize("dim", [8])
def test_faiss_rebuild_after_delete(tmp_path: Path, dim: int):
    store_path = tmp_path / "faiss"
    vs = FaissVectorStore(path=str(store_path), embedding_dimension=dim)

    # add two chunks with simple embeddings
    chunks = [
        ChunkData(id="c1", text="a", document_id="d1", embedding=[1.0] * dim),
        ChunkData(id="c2", text="b", document_id="d1", embedding=[0.0] * (dim - 1) + [1.0]),
    ]
    # Normalize: handled by store; we just provide raw
    import asyncio

    asyncio.run(vs.add_chunks(chunks))

    # Ensure meta has embeddings persisted
    meta = json.loads((store_path / "meta.json").read_text())
    assert meta.get("version") == 2
    assert any(r.get("embedding") for r in meta.get("rows", []))

    # Delete one chunk and make sure rebuild happens without error
    asyncio.run(vs.delete_chunks(["c1"]))

    # Reload store and ensure only one row remains
    vs2 = FaissVectorStore(path=str(store_path), embedding_dimension=dim)
    assert len(vs2._rows) == 1
    assert vs2._rows[0]["chunk_id"] == "c2"
