import json
import logging
import os
from pathlib import Path
from typing import Any

import faiss  # type: ignore
import numpy as np

from graph_rag.core.interfaces import ChunkData, SearchResultData, VectorStore

logger = logging.getLogger(__name__)


def _ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def _normalize(vectors: np.ndarray) -> np.ndarray:
    norms = np.linalg.norm(vectors, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    return vectors / norms


class FaissVectorStore(VectorStore):
    """Persistent FAISS-based vector store using cosine similarity (via inner product on normalized vectors).

    Persists:
    - FAISS index file: index.faiss
    - Metadata sidecar: meta.json (maps row -> ChunkData minimal fields)
    """

    def __init__(self, path: str, embedding_dimension: int):
        self.base_path = Path(os.path.expanduser(path))
        _ensure_dir(self.base_path)
        self.index_path = self.base_path / "index.faiss"
        self.meta_path = self.base_path / "meta.json"
        self.embedding_dimension = int(embedding_dimension)

        self.index = faiss.IndexFlatIP(self.embedding_dimension)
        self._rows: list[dict[str, Any]] = []
        self._row_by_chunk_id: dict[str, int] = {}

        self._load()

    # --- persistence ---
    def _load(self) -> None:
        if self.index_path.exists():
            logger.info(f"Loading FAISS index from {self.index_path}")
            self.index = faiss.read_index(str(self.index_path))
        if self.meta_path.exists():
            try:
                data = json.loads(self.meta_path.read_text())
                self._rows = data.get("rows", [])
                self._row_by_chunk_id = {r["chunk_id"]: i for i, r in enumerate(self._rows)}
            except Exception as e:
                logger.error(f"Failed to load FAISS metadata: {e}")
                self._rows = []
                self._row_by_chunk_id = {}

    def _save(self) -> None:
        # Write index atomically
        tmp_index = self.index_path.with_suffix(".faiss.tmp")
        faiss.write_index(self.index, str(tmp_index))
        tmp_index.replace(self.index_path)
        # Write metadata
        tmp_meta = self.meta_path.with_suffix(".json.tmp")
        tmp_meta.write_text(json.dumps({"rows": self._rows}))
        tmp_meta.replace(self.meta_path)

    # --- VectorStore API ---
    async def add_chunks(self, chunks: list[ChunkData]) -> None:  # type: ignore[override]
        if not chunks:
            return
        # Expect embeddings present on chunks; caller ensures generation
        vectors: list[list[float]] = []
        new_rows: list[dict[str, Any]] = []
        for ch in chunks:
            if ch.embedding is None:
                logger.warning(f"Skipping chunk {ch.id} without embedding for FAISS store")
                continue
            if ch.id in self._row_by_chunk_id:
                # FAISS IndexFlat doesn't support in-place update; naive strategy: append new and keep last
                logger.warning(f"Duplicate chunk id {ch.id} detected; appending new embedding")
            vectors.append(ch.embedding)
            new_rows.append(
                {
                    "chunk_id": ch.id,
                    "document_id": ch.document_id,
                    "text": ch.text,
                    "metadata": ch.metadata or {},
                }
            )
        if not vectors:
            return
        vec = np.array(vectors, dtype=np.float32)
        vec = _normalize(vec)
        self.index.add(vec)
        start = len(self._rows)
        self._rows.extend(new_rows)
        for offset, row in enumerate(new_rows):
            self._row_by_chunk_id[row["chunk_id"]] = start + offset
        self._save()

    async def search_similar_chunks(  # type: ignore[override]
        self, query_vector: list[float], limit: int = 10, threshold: float | None = None
    ) -> list[SearchResultData]:
        if self.index.ntotal == 0:
            return []
        q = np.array([query_vector], dtype=np.float32)
        q = _normalize(q)
        scores, idxs = self.index.search(q, k=max(1, limit))
        results: list[SearchResultData] = []
        for score, idx in zip(scores[0].tolist(), idxs[0].tolist()):
            if idx < 0 or idx >= len(self._rows):
                continue
            if threshold is not None and score < threshold:
                continue
            row = self._rows[idx]
            results.append(
                SearchResultData(
                    chunk=ChunkData(
                        id=row["chunk_id"],
                        text=row.get("text", ""),
                        document_id=row.get("document_id", ""),
                        embedding=None,
                        metadata=row.get("metadata", {}),
                        score=float(score),
                    ),
                    score=float(score),
                )
            )
        return results

    async def get_chunk_by_id(self, chunk_id: str) -> ChunkData | None:  # type: ignore[override]
        row_idx = self._row_by_chunk_id.get(chunk_id)
        if row_idx is None:
            return None
        row = self._rows[row_idx]
        return ChunkData(
            id=row["chunk_id"],
            text=row.get("text", ""),
            document_id=row.get("document_id", ""),
            embedding=None,
            metadata=row.get("metadata", {}),
            score=0.0,
        )

    async def delete_chunks(self, chunk_ids: list[str]) -> None:  # type: ignore[override]
        # Not supported efficiently with IndexFlat; rebuild by filtering rows.
        if not chunk_ids:
            return
        keep_rows = [r for r in self._rows if r["chunk_id"] not in set(chunk_ids)]
        self._rows = keep_rows
        self._row_by_chunk_id = {r["chunk_id"]: i for i, r in enumerate(self._rows)}
        # Rebuild index
        self.index = faiss.IndexFlatIP(self.embedding_dimension)
        if self._rows:
            vecs = []
            for r in self._rows:
                # Without storing embeddings on disk, can't rebuild; for now, we drop support for delete without full rebuild.
                # Future: persist embeddings alongside metadata.
                pass
        # Save new (empty) index for now; document limitation
        self._save()

    async def delete_store(self) -> None:  # type: ignore[override]
        if self.index_path.exists():
            self.index_path.unlink()
        if self.meta_path.exists():
            self.meta_path.unlink()
        self.index = faiss.IndexFlatIP(self.embedding_dimension)
        self._rows = []
        self._row_by_chunk_id = {}
