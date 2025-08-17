import json
import logging
import os
from pathlib import Path
from typing import Any

import faiss  # type: ignore
import numpy as np

from graph_rag.core.interfaces import ChunkData, EmbeddingService, SearchResultData, VectorStore

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

    def __init__(self, path: str, embedding_dimension: int, embedding_service: EmbeddingService | None = None):
        self.base_path = Path(os.path.expanduser(path))
        _ensure_dir(self.base_path)
        self.index_path = self.base_path / "index.faiss"
        self.meta_path = self.base_path / "meta.json"
        self.embedding_dimension = int(embedding_dimension)
        self.embedding_service = embedding_service

        self.index = faiss.IndexFlatIP(self.embedding_dimension)
        self._rows: list[dict[str, Any]] = []
        self._row_by_chunk_id: dict[str, int] = {}

        self._load()

    # --- persistence ---
    def _load(self) -> None:
        if self.index_path.exists():
            logger.info(f"Loading FAISS index from {self.index_path}")
            self.index = faiss.read_index(str(self.index_path))
            try:
                # Align embedding dimension with loaded index
                self.embedding_dimension = int(self.index.d)
            except Exception:
                pass
        if self.meta_path.exists():
            try:
                data = json.loads(self.meta_path.read_text())
                version = int(data.get("version", 1))
                if version < 2:
                    logger.warning(
                        "FAISS meta version %s detected; embeddings may be missing. "
                        "Consider re-ingesting or running maintenance to upgrade.",
                        version,
                    )
                self._rows = data.get("rows", [])
                self._row_by_chunk_id = {
                    r["chunk_id"]: i for i, r in enumerate(self._rows)
                }
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
        tmp_meta.write_text(json.dumps({"version": 2, "rows": self._rows}))
        tmp_meta.replace(self.meta_path)

    def _rebuild_from_rows(self) -> None:
        """Rebuild FAISS index from current rows using persisted embeddings.

        Skips legacy rows that do not include an embedding.
        """
        self.index = faiss.IndexFlatIP(self.embedding_dimension)
        if not self._rows:
            return
        reb_vectors: list[list[float]] = []
        for r in self._rows:
            emb = r.get("embedding")
            if isinstance(emb, list) and len(emb) == self.embedding_dimension:
                reb_vectors.append(emb)
            else:
                logger.warning(
                    "Row %s missing embedding for FAISS rebuild; skipping.",
                    r.get("chunk_id"),
                )
        if reb_vectors:
            vec = np.array(reb_vectors, dtype=np.float32)
            vec = _normalize(vec)
            self.index.add(vec)

    # --- VectorStore API ---
    async def add_chunks(self, chunks: list[ChunkData]) -> None:  # type: ignore[override]
        if not chunks:
            return
        # Expect embeddings present on chunks; caller ensures generation
        vectors: list[list[float]] = []
        new_rows: list[dict[str, Any]] = []
        for ch in chunks:
            if ch.embedding is None:
                logger.warning(
                    f"Skipping chunk {ch.id} without embedding for FAISS store"
                )
                continue
            if ch.id in self._row_by_chunk_id:
                # FAISS IndexFlat doesn't support in-place update; naive strategy: append new and keep last
                logger.warning(
                    f"Duplicate chunk id {ch.id} detected; appending new embedding"
                )
            vectors.append(ch.embedding)
            new_rows.append(
                {
                    "chunk_id": ch.id,
                    "document_id": ch.document_id,
                    "text": ch.text,
                    "metadata": ch.metadata or {},
                    # Persist original (unnormalized) embedding for rebuilds
                    "embedding": ch.embedding,
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
        for score, idx in zip(scores[0].tolist(), idxs[0].tolist(), strict=False):
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
        # Rebuild by filtering rows and re-adding remaining embeddings.
        if not chunk_ids:
            return
        to_delete = set(chunk_ids)
        keep_rows = [r for r in self._rows if r.get("chunk_id") not in to_delete]
        self._rows = keep_rows
        self._row_by_chunk_id = {r["chunk_id"]: i for i, r in enumerate(self._rows)}

        # Rebuild FAISS index from persisted embeddings
        self._rebuild_from_rows()
        self._save()

    async def delete_store(self) -> None:  # type: ignore[override]
        if self.index_path.exists():
            self.index_path.unlink()
        if self.meta_path.exists():
            self.meta_path.unlink()
        self.index = faiss.IndexFlatIP(self.embedding_dimension)
        self._rows = []
        self._row_by_chunk_id = {}

    # --- Convenience methods for API compatibility ---
    async def search(
        self, query_text: str, top_k: int = 5, search_type: str = "vector"
    ) -> list[SearchResultData]:
        """
        Convenience method that matches SimpleVectorStore's interface.
        
        Converts query text to embedding and performs vector search.
        
        Args:
            query_text: The search query text
            top_k: Number of results to return
            search_type: Search type (only "vector" is supported)
            
        Returns:
            List of SearchResultData objects
        """
        if search_type.lower() != "vector":
            logger.warning(f"FaissVectorStore only supports vector search, got: {search_type}")
            return []

        if not self.embedding_service:
            logger.error("No embedding service available for text-to-vector conversion")
            return []

        try:
            # Generate embedding for the query text
            query_embedding = await self.embedding_service.generate_embedding(query_text)
            if not query_embedding:
                logger.error(f"Failed to generate embedding for query: '{query_text}'")
                return []

            # Use the protocol method to perform the search
            return await self.search_similar_chunks(
                query_vector=query_embedding,
                limit=top_k,
                threshold=None
            )
        except Exception as e:
            logger.error(f"Error in search for query '{query_text}': {e}", exc_info=True)
            return []

    # --- Maintenance helpers ---
    async def stats(self) -> dict[str, Any]:
        """Return basic statistics about the FAISS store."""
        return {
            "vectors": int(self.index.ntotal),
            "rows": int(len(self._rows)),
            "dimension": int(self.embedding_dimension),
            "index_path": str(self.index_path),
            "meta_path": str(self.meta_path),
        }

    async def rebuild_index(self) -> None:
        """Force a rebuild of the FAISS index from persisted embeddings."""
        self._rebuild_from_rows()
        self._save()
