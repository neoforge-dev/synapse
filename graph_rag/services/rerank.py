from __future__ import annotations

from typing import List

from graph_rag.core.interfaces import SearchResultData


class CrossEncoderReranker:
    """Lightweight reranker wrapper.

    If cross-encoder model is unavailable, acts as a no-op returning the top-k input.
    """

    def __init__(self, model_name: str | None = None):
        self.model_name = model_name or "cross-encoder/ms-marco-MiniLM-L-6-v2"
        self._available = False
        try:  # optional dependency
            from sentence_transformers import CrossEncoder  # noqa: F401

            self._available = True
        except Exception:
            self._available = False

    async def rerank(
        self, query: str, items: List[SearchResultData], k: int
    ) -> List[SearchResultData]:
        if not items:
            return []
        if not self._available:
            # Best effort: return as-is
            return items[:k]
        try:
            from sentence_transformers import CrossEncoder

            model = CrossEncoder(self.model_name)
            pairs = [(query, it.chunk.text) for it in items]
            scores = model.predict(pairs)
            # Attach scores and sort
            rescored: List[SearchResultData] = []
            for it, s in zip(items, scores):
                try:
                    it.score = float(s)  # type: ignore[attr-defined]
                    if hasattr(it, "chunk") and hasattr(it.chunk, "metadata"):
                        meta = it.chunk.metadata or {}
                        meta["score_rerank"] = float(s)
                        it.chunk.metadata = meta
                except Exception:
                    pass
                rescored.append(it)
            rescored.sort(key=lambda x: getattr(x, "score", 0.0), reverse=True)
            return rescored[:k]
        except Exception:
            # Fallback
            return items[:k]
