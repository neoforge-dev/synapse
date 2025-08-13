import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from graph_rag.api.dependencies import get_graph_repository, get_vector_store
from graph_rag.core.interfaces import GraphRepository, VectorStore

logger = logging.getLogger(__name__)


def create_admin_router() -> APIRouter:
    # No internal prefix; main app mounts under /admin
    router = APIRouter(tags=["Admin"])

    @router.get("/vector/stats")
    async def vector_stats(
        vector_store: Annotated[VectorStore, Depends(get_vector_store)]
    ) -> dict:
        try:
            # Prefer stats() if available (FAISS)
            if hasattr(vector_store, "stats"):
                return await vector_store.stats()  # type: ignore[attr-defined]
            # Fallback: return vector count if available
            if hasattr(vector_store, "get_vector_store_size"):
                size = await vector_store.get_vector_store_size()  # type: ignore[attr-defined]
                return {"vectors": int(size)}
            return {"status": "unknown"}
        except Exception as e:
            logger.error(f"vector_stats failed: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail=str(e))

    @router.post("/vector/rebuild", status_code=status.HTTP_202_ACCEPTED)
    async def vector_rebuild(
        vector_store: Annotated[VectorStore, Depends(get_vector_store)]
    ) -> dict:
        try:
            if hasattr(vector_store, "rebuild_index"):
                await vector_store.rebuild_index()  # type: ignore[attr-defined]
                return {"status": "ok", "message": "vector index rebuild started"}
            raise HTTPException(status_code=400, detail="Rebuild not supported")
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"vector_rebuild failed: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail=str(e))

    @router.get("/integrity/check")
    async def integrity_check(
        graph_repo: Annotated[GraphRepository, Depends(get_graph_repository)],
        vector_store: Annotated[VectorStore, Depends(get_vector_store)],
    ) -> dict:
        try:
            # Count chunks in graph
            try:
                q = "MATCH (c:Chunk) RETURN count(c) AS n"
                rows = await graph_repo.execute_query(q)
                graph_chunks = 0
                if rows:
                    row = rows[0]
                    graph_chunks = int(row.get("n", 0) if isinstance(row, dict) else list(row.values())[0])
            except Exception:
                graph_chunks = 0
            # Count vectors in store
            vectors = 0
            if hasattr(vector_store, "stats"):
                stats = await vector_store.stats()  # type: ignore[attr-defined]
                vectors = int(stats.get("vectors", 0))
            elif hasattr(vector_store, "get_vector_store_size"):
                vectors = int(await vector_store.get_vector_store_size())  # type: ignore[attr-defined]
            ok = vectors >= 0 and graph_chunks >= 0
            warnings: list[str] = []
            if vectors < graph_chunks:
                warnings.append(
                    f"Vector count ({vectors}) is less than graph chunks ({graph_chunks}); some chunks may be missing embeddings."
                )
            return {"graph_chunks": graph_chunks, "vectors": vectors, "ok": ok, "warnings": warnings}
        except Exception as e:
            logger.error(f"integrity_check failed: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail=str(e))

    return router
