import time
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
from graph_rag.api.performance_optimization import (
    get_advanced_performance_stats,
    get_optimization_recommendations,
    get_performance_monitor,
    get_query_optimizer,
)
from graph_rag.api.system_metrics import (
    assess_system_health,
    get_application_metrics,
    get_platform_info,
    get_system_metrics,
)
from graph_rag.core.interfaces import GraphRepository, VectorStore
from graph_rag.llm.protocols import LLMService
from graph_rag.observability import (
    ComponentType,
    LogContext,
    get_component_logger,
)
from graph_rag.services.maintenance import IntegrityCheckJob

# Use structured logger for admin endpoints
logger = get_component_logger(ComponentType.API, "admin")


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

    # System Metrics and Monitoring Endpoints
    @router.get("/metrics/system", response_model=dict)
    async def system_metrics() -> dict:
        """Get comprehensive system resource metrics."""
        context = LogContext(
            component=ComponentType.API,
            operation="system_metrics",
            metadata={"endpoint": "/admin/metrics/system"}
        )

        try:
            logger.info("Collecting system metrics", context)
            metrics = get_system_metrics()

            # Convert dataclass to dict for JSON serialization
            result = {
                "cpu_percent": metrics.cpu_percent,
                "cpu_count": metrics.cpu_count,
                "load_average": metrics.load_average,
                "memory": {
                    "total": metrics.memory_total,
                    "available": metrics.memory_available,
                    "used": metrics.memory_used,
                    "percent": metrics.memory_percent,
                },
                "disk": {
                    "total": metrics.disk_total,
                    "used": metrics.disk_used,
                    "free": metrics.disk_free,
                    "percent": metrics.disk_percent,
                },
                "network": {
                    "sent": metrics.network_sent,
                    "recv": metrics.network_recv,
                },
                "process_count": metrics.process_count,
                "timestamp": metrics.timestamp,
            }

            logger.info("System metrics collected successfully", context, cpu_percent=metrics.cpu_percent)
            return result

        except Exception as e:
            logger.error("Failed to collect system metrics", context, error=e)
            raise HTTPException(status_code=500, detail=f"Failed to collect system metrics: {str(e)}")

    @router.get("/metrics/application", response_model=dict)
    async def application_metrics(
        request: Request,
        vector_store: Annotated[VectorStore, Depends(get_vector_store)],
        graph_repo: Annotated[GraphRepository, Depends(get_graph_repository)],
    ) -> dict:
        """Get comprehensive application-specific metrics."""
        context = LogContext(
            component=ComponentType.API,
            operation="application_metrics",
            metadata={"endpoint": "/admin/metrics/application"}
        )

        try:
            logger.info("Collecting application metrics", context)

            # Get cache and performance stats
            from graph_rag.api.performance import get_cache_stats, get_performance_stats
            cache_stats = get_cache_stats()
            performance_stats = get_performance_stats()

            metrics = get_application_metrics(
                vector_store=vector_store,
                graph_repository=graph_repo,
                cache_stats=cache_stats,
                performance_stats=performance_stats
            )

            # Convert dataclass to dict for JSON serialization
            result = {
                "process": {
                    "memory_mb": metrics.process_memory_mb,
                    "cpu_percent": metrics.process_cpu_percent,
                    "thread_count": metrics.thread_count,
                    "open_files": metrics.open_files,
                    "uptime_seconds": metrics.uptime_seconds,
                },
                "cache": {
                    "hit_rate": metrics.cache_hit_rate,
                    "stats": cache_stats,
                },
                "storage": {
                    "vector_store_size": metrics.vector_store_size,
                    "graph_node_count": metrics.graph_node_count,
                },
                "requests": {
                    "total_requests": metrics.total_requests,
                    "avg_response_time": metrics.avg_response_time,
                    "performance_stats": performance_stats,
                },
                "timestamp": metrics.timestamp,
            }

            logger.info(
                "Application metrics collected successfully",
                context,
                memory_mb=metrics.process_memory_mb,
                uptime_hours=metrics.uptime_seconds / 3600
            )
            return result

        except Exception as e:
            logger.error("Failed to collect application metrics", context, error=e)
            raise HTTPException(status_code=500, detail=f"Failed to collect application metrics: {str(e)}")

    @router.get("/metrics/health-assessment")
    async def health_assessment(
        vector_store: Annotated[VectorStore, Depends(get_vector_store)],
        graph_repo: Annotated[GraphRepository, Depends(get_graph_repository)],
    ) -> dict:
        """Get comprehensive health assessment based on system and application metrics."""
        context = LogContext(
            component=ComponentType.API,
            operation="health_assessment",
            metadata={"endpoint": "/admin/metrics/health-assessment"}
        )

        try:
            logger.info("Performing health assessment", context)

            # Collect both system and application metrics
            system_metrics = get_system_metrics()

            from graph_rag.api.performance import get_cache_stats, get_performance_stats
            cache_stats = get_cache_stats()
            performance_stats = get_performance_stats()

            app_metrics = get_application_metrics(
                vector_store=vector_store,
                graph_repository=graph_repo,
                cache_stats=cache_stats,
                performance_stats=performance_stats
            )

            # Assess health based on thresholds
            assessment = assess_system_health(system_metrics, app_metrics)

            # Include raw metrics in the response
            result = {
                "assessment": assessment,
                "system_metrics": {
                    "cpu_percent": system_metrics.cpu_percent,
                    "memory_percent": system_metrics.memory_percent,
                    "disk_percent": system_metrics.disk_percent,
                },
                "application_metrics": {
                    "process_memory_mb": app_metrics.process_memory_mb,
                    "process_cpu_percent": app_metrics.process_cpu_percent,
                    "avg_response_time": app_metrics.avg_response_time,
                    "uptime_seconds": app_metrics.uptime_seconds,
                },
                "timestamp": system_metrics.timestamp,
            }

            logger.info(
                f"Health assessment completed: {assessment['status']}",
                context,
                status=assessment["status"],
                issue_count=len(assessment["issues"]),
                warning_count=len(assessment["warnings"])
            )
            return result

        except Exception as e:
            logger.error("Failed to perform health assessment", context, error=e)
            raise HTTPException(status_code=500, detail=f"Failed to perform health assessment: {str(e)}")

    @router.get("/platform/info")
    async def platform_info() -> dict:
        """Get platform and environment information."""
        context = LogContext(
            component=ComponentType.API,
            operation="platform_info",
            metadata={"endpoint": "/admin/platform/info"}
        )

        try:
            logger.info("Collecting platform info", context)
            info = get_platform_info()

            logger.info("Platform info collected successfully", context, system=info.get("system"))
            return info

        except Exception as e:
            logger.error("Failed to collect platform info", context, error=e)
            raise HTTPException(status_code=500, detail=f"Failed to collect platform info: {str(e)}")

    @router.get("/monitoring/dashboard")
    async def monitoring_dashboard(
        request: Request,
        vector_store: Annotated[VectorStore, Depends(get_vector_store)],
        graph_repo: Annotated[GraphRepository, Depends(get_graph_repository)],
        llm_service: Annotated[LLMService, Depends(get_llm)],
    ) -> dict:
        """Comprehensive monitoring dashboard with all metrics and health data."""
        context = LogContext(
            component=ComponentType.API,
            operation="monitoring_dashboard",
            metadata={"endpoint": "/admin/monitoring/dashboard"}
        )

        try:
            logger.info("Generating monitoring dashboard", context)

            # Collect all metrics
            system_metrics = get_system_metrics()

            from graph_rag.api.performance import get_cache_stats, get_performance_stats
            cache_stats = get_cache_stats()
            performance_stats = get_performance_stats()

            app_metrics = get_application_metrics(
                vector_store=vector_store,
                graph_repository=graph_repo,
                cache_stats=cache_stats,
                performance_stats=performance_stats
            )

            # Health assessment
            health_assessment_result = assess_system_health(system_metrics, app_metrics)

            # Component health checks
            health_checker = HealthChecker(timeout_seconds=5.0)
            embedding_service = getattr(vector_store, 'embedding_service', None)

            component_checkers = {
                "graph_repository": lambda: check_graph_repository(graph_repo),
                "vector_store": lambda: check_vector_store(vector_store),
                "llm_service": lambda: check_llm_service(llm_service),
            }

            if embedding_service:
                component_checkers["embedding_service"] = lambda: check_embedding_service(embedding_service)

            component_health = await health_checker.check_all(component_checkers)

            # Platform info
            platform_data = get_platform_info()

            # Build comprehensive dashboard
            dashboard = {
                "overview": {
                    "status": health_assessment_result["status"],
                    "uptime_hours": app_metrics.uptime_seconds / 3600,
                    "total_requests": app_metrics.total_requests,
                    "avg_response_time": app_metrics.avg_response_time,
                    "timestamp": system_metrics.timestamp,
                },
                "system_resources": {
                    "cpu_percent": system_metrics.cpu_percent,
                    "memory_percent": system_metrics.memory_percent,
                    "disk_percent": system_metrics.disk_percent,
                    "process_memory_mb": app_metrics.process_memory_mb,
                    "thread_count": app_metrics.thread_count,
                },
                "components": {
                    "overall_status": component_health.status,
                    "component_details": [
                        {
                            "name": comp.name,
                            "status": comp.status,
                            "response_time_ms": comp.response_time_ms,
                            "message": comp.message
                        }
                        for comp in component_health.components
                    ]
                },
                "storage": {
                    "vector_store_size": app_metrics.vector_store_size,
                    "graph_node_count": app_metrics.graph_node_count,
                    "cache_size": cache_stats.get("size", 0),
                },
                "health_assessment": health_assessment_result,
                "platform": {
                    "system": platform_data.get("system"),
                    "python_version": platform_data.get("python_version"),
                    "hostname": platform_data.get("hostname"),
                },
            }

            logger.info(
                "Monitoring dashboard generated successfully",
                context,
                overall_status=health_assessment_result["status"],
                component_count=len(component_health.components)
            )
            return dashboard

        except Exception as e:
            logger.error("Failed to generate monitoring dashboard", context, error=e)
            raise HTTPException(status_code=500, detail=f"Failed to generate monitoring dashboard: {str(e)}")

    # Advanced Performance Optimization Endpoints
    @router.get("/performance/advanced")
    async def advanced_performance_stats() -> dict:
        """Get comprehensive advanced performance statistics."""
        context = LogContext(
            component=ComponentType.API,
            operation="advanced_performance_stats",
            metadata={"endpoint": "/admin/performance/advanced"}
        )

        try:
            logger.info("Collecting advanced performance statistics", context)

            stats = get_advanced_performance_stats()
            recommendations = get_optimization_recommendations()

            # Get slow queries
            monitor = get_performance_monitor()
            slow_queries = monitor.get_slow_queries(limit=10)

            result = {
                "performance_summary": stats,
                "optimization_recommendations": recommendations,
                "slow_queries": [
                    {
                        "query_id": q.query_id,
                        "query_type": q.query_type,
                        "total_duration_ms": q.total_duration_ms,
                        "retrieval_duration_ms": q.retrieval_duration_ms,
                        "llm_duration_ms": q.llm_duration_ms,
                        "memory_peak_mb": q.memory_peak_mb,
                        "chunks_retrieved": q.chunks_retrieved,
                        "cache_hit": q.cache_hit,
                        "timestamp": q.timestamp,
                    }
                    for q in slow_queries
                ],
                "query_optimizer_stats": {
                    "total_patterns": len(get_query_optimizer().query_patterns),
                    "optimal_k_mappings": len(get_query_optimizer().optimal_k_values),
                    "complexity_cache_size": len(get_query_optimizer().query_complexity_cache),
                }
            }

            logger.info(
                "Advanced performance statistics collected successfully",
                context,
                total_queries=stats.get("total_queries", 0),
                slow_query_count=len(slow_queries)
            )
            return result

        except Exception as e:
            logger.error("Failed to collect advanced performance statistics", context, error=e)
            raise HTTPException(status_code=500, detail=f"Failed to collect advanced performance statistics: {str(e)}")

    @router.get("/performance/profiles")
    async def performance_profiles() -> dict:
        """Get performance profiles for different operation types."""
        context = LogContext(
            component=ComponentType.API,
            operation="performance_profiles",
            metadata={"endpoint": "/admin/performance/profiles"}
        )

        try:
            logger.info("Collecting performance profiles", context)

            monitor = get_performance_monitor()
            operation_types = ["vector", "hybrid", "graph", "keyword"]

            profiles = {}
            for op_type in operation_types:
                profile = monitor.get_performance_profile(op_type)
                if profile:
                    profiles[op_type] = {
                        "avg_duration_ms": profile.avg_duration_ms,
                        "min_duration_ms": profile.min_duration_ms,
                        "max_duration_ms": profile.max_duration_ms,
                        "p50_duration_ms": profile.p50_duration_ms,
                        "p95_duration_ms": profile.p95_duration_ms,
                        "p99_duration_ms": profile.p99_duration_ms,
                        "operations_per_second": profile.operations_per_second,
                        "total_operations": profile.total_operations,
                        "avg_memory_usage_mb": profile.avg_memory_usage_mb,
                        "cache_hit_rate": profile.cache_hit_rate,
                        "success_rate": profile.success_rate,
                    }

            result = {
                "operation_profiles": profiles,
                "timestamp": time.time(),
            }

            logger.info(
                "Performance profiles collected successfully",
                context,
                profile_count=len(profiles)
            )
            return result

        except Exception as e:
            logger.error("Failed to collect performance profiles", context, error=e)
            raise HTTPException(status_code=500, detail=f"Failed to collect performance profiles: {str(e)}")

    @router.get("/performance/optimization")
    async def optimization_analysis() -> dict:
        """Get optimization analysis and recommendations."""
        context = LogContext(
            component=ComponentType.API,
            operation="optimization_analysis",
            metadata={"endpoint": "/admin/performance/optimization"}
        )

        try:
            logger.info("Performing optimization analysis", context)

            optimizer = get_query_optimizer()
            monitor = get_performance_monitor()

            # Get optimization recommendations
            recommendations = get_optimization_recommendations()

            # Analyze query patterns
            pattern_analysis = {
                "total_unique_queries": len(optimizer.query_patterns),
                "frequent_queries": [
                    {"query_hash": hash_val, "frequency": count}
                    for hash_val, count in optimizer.query_patterns.items()
                    if count >= 3
                ],
                "optimal_k_distribution": {
                    str(k): len([v for v in optimizer.optimal_k_values.values() if v == k])
                    for k in range(3, 21)
                    if any(v == k for v in optimizer.optimal_k_values.values())
                },
                "complexity_distribution": {
                    "low": len([c for c in optimizer.query_complexity_cache.values() if c < 0.3]),
                    "medium": len([c for c in optimizer.query_complexity_cache.values() if 0.3 <= c < 0.7]),
                    "high": len([c for c in optimizer.query_complexity_cache.values() if c >= 0.7]),
                }
            }

            # Memory analysis
            memory_stats = monitor.memory_tracker.get_stats()

            result = {
                "recommendations": recommendations,
                "pattern_analysis": pattern_analysis,
                "memory_analysis": memory_stats,
                "cache_efficiency": {
                    "should_cache_count": len([
                        q for q in optimizer.query_patterns.keys()
                        if optimizer.should_use_cache(f"query_{q}")  # Simplified check
                    ]),
                    "total_patterns": len(optimizer.query_patterns),
                },
                "timestamp": time.time(),
            }

            logger.info(
                "Optimization analysis completed successfully",
                context,
                recommendation_count=len(recommendations),
                pattern_count=len(optimizer.query_patterns)
            )
            return result

        except Exception as e:
            logger.error("Failed to perform optimization analysis", context, error=e)
            raise HTTPException(status_code=500, detail=f"Failed to perform optimization analysis: {str(e)}")

    @router.post("/performance/reset-stats")
    async def reset_performance_stats() -> dict:
        """Reset performance statistics and optimization data."""
        context = LogContext(
            component=ComponentType.API,
            operation="reset_performance_stats",
            metadata={"endpoint": "/admin/performance/reset-stats"}
        )

        try:
            logger.info("Resetting performance statistics", context)

            # Reset performance monitor
            monitor = get_performance_monitor()
            monitor.query_history.clear()
            monitor.operation_stats.clear()
            monitor.slow_queries.clear()

            # Reset query optimizer
            optimizer = get_query_optimizer()
            optimizer.query_patterns.clear()
            optimizer.optimal_k_values.clear()
            optimizer.query_complexity_cache.clear()

            # Clear performance cache
            from graph_rag.api.performance import clear_cache
            clear_cache()

            result = {
                "status": "success",
                "message": "Performance statistics and optimization data reset",
                "timestamp": time.time(),
            }

            logger.info("Performance statistics reset successfully", context)
            return result

        except Exception as e:
            logger.error("Failed to reset performance statistics", context, error=e)
            raise HTTPException(status_code=500, detail=f"Failed to reset performance statistics: {str(e)}")

    return router
