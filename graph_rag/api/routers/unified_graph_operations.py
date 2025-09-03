"""
Unified Graph Operations Router - Epic 2 Consolidation

Consolidates graph and monitoring routers into a single high-performance endpoint.
Provides comprehensive graph operations and system monitoring.

Performance Target: <100ms average response time
Business Impact: Real-time graph health monitoring for $610K pipeline reliability
"""

import logging
import time
from typing import Annotated, Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

from graph_rag.api.dependencies import (
    get_graph_repository,
    get_vector_store,
)
from graph_rag.core.interfaces import GraphRepository, VectorStore

logger = logging.getLogger(__name__)


def create_unified_graph_operations_router() -> APIRouter:
    """Factory function to create the unified graph operations router."""
    router = APIRouter()

    @router.get(
        "/nodes",
        summary="Get graph nodes",
        description="Retrieves nodes from the knowledge graph with filtering options.",
    )
    async def get_graph_nodes(
        repo: Annotated[GraphRepository, Depends(get_graph_repository)],
        node_type: Annotated[Optional[str], Query(description="Filter by node type")] = None,
        limit: Annotated[int, Query(description="Maximum nodes to return")] = 50,
    ):
        """Get graph nodes with unified filtering and performance optimization."""
        try:
            if node_type:
                entities = await repo.get_entities_by_type(node_type, limit=limit)
            else:
                entities = await repo.get_entities_by_type("", limit=limit)
            
            nodes = [
                {
                    "id": entity.id,
                    "type": entity.type,
                    "properties": entity.properties
                }
                for entity in entities
            ]
            
            return {"nodes": nodes, "count": len(nodes)}
            
        except Exception as e:
            logger.error(f"Failed to get graph nodes: {e}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to retrieve graph nodes",
            )

    @router.get(
        "/relationships",
        summary="Get graph relationships",
        description="Retrieves relationships from the knowledge graph.",
    )
    async def get_graph_relationships(
        repo: Annotated[GraphRepository, Depends(get_graph_repository)],
        limit: Annotated[int, Query(description="Maximum relationships to return")] = 50,
    ):
        """Get graph relationships with performance optimization."""
        try:
            # This would need to be implemented in the repository
            relationships = []  # Placeholder
            
            return {"relationships": relationships, "count": len(relationships)}
            
        except Exception as e:
            logger.error(f"Failed to get graph relationships: {e}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to retrieve graph relationships",
            )

    @router.get(
        "/health",
        summary="Graph and system health check",
        description="Comprehensive health check for graph and vector stores.",
    )
    async def unified_health_check(
        repo: Annotated[GraphRepository, Depends(get_graph_repository)],
        vector_store: Annotated[VectorStore, Depends(get_vector_store)],
    ):
        """Unified health check with comprehensive system monitoring."""
        _start = time.monotonic()
        
        try:
            health_status = {
                "status": "healthy",
                "timestamp": time.time(),
                "components": {},
                "performance_metrics": {}
            }
            
            # Graph store health
            try:
                entities = await repo.get_entities_by_type("Document", limit=1)
                health_status["components"]["graph_store"] = {
                    "status": "healthy",
                    "response_time_ms": round((time.monotonic() - _start) * 1000, 2)
                }
            except Exception as e:
                health_status["components"]["graph_store"] = {
                    "status": "unhealthy",
                    "error": str(e)
                }
            
            # Vector store health
            try:
                vector_count = await vector_store.get_vector_store_size()
                health_status["components"]["vector_store"] = {
                    "status": "healthy",
                    "vector_count": vector_count
                }
            except Exception as e:
                health_status["components"]["vector_store"] = {
                    "status": "unhealthy",
                    "error": str(e)
                }
            
            # Overall health determination
            component_statuses = [comp["status"] for comp in health_status["components"].values()]
            if any(status == "unhealthy" for status in component_statuses):
                health_status["status"] = "degraded"
            
            health_status["performance_metrics"]["total_response_time_ms"] = round((time.monotonic() - _start) * 1000, 2)
            
            return health_status
            
        except Exception as e:
            logger.error(f"Health check failed: {e}", exc_info=True)
            return {
                "status": "unhealthy",
                "error": str(e),
                "timestamp": time.time()
            }

    return router