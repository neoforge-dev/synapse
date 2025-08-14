import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status

from graph_rag.api.dependencies import (
    get_graph_repository,
    get_llm,
    get_vector_store,
)
from graph_rag.api.health import (
    HealthChecker,
    SystemHealth,
    check_embedding_service,
    check_graph_repository,
    check_llm_service,
    check_vector_store,
)
from graph_rag.core.interfaces import GraphRepository, VectorStore
from graph_rag.llm.protocols import LLMService
from graph_rag.services.maintenance import IntegrityCheckJob

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

    @router.get("/health/detailed", response_model=SystemHealth)
    async def detailed_health_check(
        request: Request,
        graph_repo: Annotated[GraphRepository, Depends(get_graph_repository)],
        vector_store: Annotated[VectorStore, Depends(get_vector_store)],
        llm_service: Annotated[LLMService, Depends(get_llm)],
    ) -> SystemHealth:
        """Comprehensive health check with detailed component status."""

        health_checker = HealthChecker(timeout_seconds=10.0)

        # Get embedding service from vector store
        embedding_service = getattr(vector_store, 'embedding_service', None)

        # Define health checkers
        checkers = {
            "graph_repository": lambda: check_graph_repository(graph_repo),
            "vector_store": lambda: check_vector_store(vector_store),
            "llm_service": lambda: check_llm_service(llm_service),
        }

        if embedding_service:
            checkers["embedding_service"] = lambda: check_embedding_service(embedding_service)

        # Add system-level checks
        if hasattr(request.app.state, 'maintenance_scheduler'):
            async def check_maintenance_scheduler():
                scheduler = request.app.state.maintenance_scheduler
                if scheduler and hasattr(scheduler, 'is_running'):
                    return {
                        "status": "healthy" if scheduler.is_running() else "unhealthy",
                        "message": "Maintenance scheduler running" if scheduler.is_running() else "Maintenance scheduler stopped",
                        "details": {
                            "job_count": len(getattr(scheduler, 'jobs', [])),
                            "last_run": getattr(scheduler, 'last_run_time', None)
                        }
                    }
                else:
                    return {"status": "degraded", "message": "Maintenance scheduler not configured"}

            checkers["maintenance_scheduler"] = check_maintenance_scheduler

        return await health_checker.check_all(checkers)

    @router.get("/performance/stats")
    async def performance_stats() -> dict:
        """Get performance statistics for monitored functions."""
        from graph_rag.api.performance import get_performance_stats
        return get_performance_stats()

    @router.get("/cache/stats")
    async def cache_stats() -> dict:
        """Get cache statistics and hit rates."""
        from graph_rag.api.performance import get_cache_stats
        return get_cache_stats()

    @router.delete("/cache/clear")
    async def clear_cache() -> dict:
        """Clear all cached data."""
        from graph_rag.api.performance import clear_cache
        clear_cache()
        return {"status": "ok", "message": "Cache cleared"}

    # New maintenance endpoints
    @router.post("/maintenance/rebuild-faiss", status_code=status.HTTP_202_ACCEPTED)
    async def trigger_faiss_rebuild(
        request: Request,
        vector_store: Annotated[VectorStore, Depends(get_vector_store)]
    ) -> dict:
        """Manually trigger FAISS index rebuild."""
        try:
            # Get maintenance scheduler from app state if available
            scheduler = getattr(request.app.state, 'maintenance_scheduler', None)
            if scheduler:
                result = await scheduler.trigger_job("faiss_maintenance")
                if result:
                    return {"status": "triggered", "result": result}
                else:
                    # Fallback: trigger rebuild directly
                    if hasattr(vector_store, "rebuild_index"):
                        await vector_store.rebuild_index()
                        return {"status": "ok", "message": "FAISS rebuild completed directly"}
                    else:
                        raise HTTPException(status_code=400, detail="FAISS rebuild not supported")
            else:
                # Fallback: trigger rebuild directly
                if hasattr(vector_store, "rebuild_index"):
                    await vector_store.rebuild_index()
                    return {"status": "ok", "message": "FAISS rebuild completed directly"}
                else:
                    raise HTTPException(status_code=400, detail="FAISS rebuild not supported")
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"faiss_rebuild failed: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail=str(e))

    @router.get("/maintenance/status")
    async def maintenance_status(request: Request) -> dict:
        """Get maintenance job and scheduler status."""
        try:
            scheduler = getattr(request.app.state, 'maintenance_scheduler', None)
            if scheduler:
                return {
                    "scheduler": scheduler.get_scheduler_status(),
                    "jobs": scheduler.get_job_status()
                }
            else:
                return {
                    "scheduler": {"running": False, "message": "Maintenance jobs not enabled"},
                    "jobs": {}
                }
        except Exception as e:
            logger.error(f"maintenance_status failed: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail=str(e))

    @router.post("/integrity/check")
    async def manual_integrity_check(
        request: Request,
        graph_repo: Annotated[GraphRepository, Depends(get_graph_repository)],
        vector_store: Annotated[VectorStore, Depends(get_vector_store)],
        sample_size: int = 10
    ) -> dict:
        """Run comprehensive integrity checks manually."""
        try:
            # Get settings for JSON logging
            settings = getattr(request.app.state, 'settings', None)
            log_json = settings.api_log_json if settings else False

            # Create and run integrity check job
            integrity_job = IntegrityCheckJob(
                graph_repository=graph_repo,
                vector_store=vector_store,
                sample_size=sample_size,
                log_json=log_json
            )

            result = await integrity_job.run()

            # Return result with appropriate status code
            if result.get("result", {}).get("status") == "failed":
                return {
                    "status": "completed_with_errors",
                    "result": result,
                    "message": "Integrity check found issues"
                }
            else:
                return {
                    "status": "ok",
                    "result": result,
                    "message": "Integrity check completed successfully"
                }

        except Exception as e:
            logger.error(f"manual_integrity_check failed: {e}", exc_info=True)
            raise HTTPException(
                status_code=500,
                detail={
                    "error": str(e),
                    "type": "application/problem+json"
                }
            )

    return router
