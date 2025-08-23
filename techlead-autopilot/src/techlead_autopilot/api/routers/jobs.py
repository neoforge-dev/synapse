"""Job monitoring and management API endpoints."""

import logging
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from ...api.auth.dependencies import get_current_user
from ...infrastructure.database.models import User
from ...infrastructure.jobs.monitoring import get_job_metrics, get_system_health
from ...infrastructure.jobs.tasks import (
    get_task_status,
    enqueue_content_posting,
    sync_engagement_metrics,
    health_check_job
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/jobs", tags=["Job Management"])


# Request/Response models
class TaskStatusResponse(BaseModel):
    """Response model for task status."""
    
    task_id: str
    status: str
    ready: bool
    successful: Optional[bool] = None
    failed: Optional[bool] = None
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class EnqueuePostingRequest(BaseModel):
    """Request model for enqueuing content posting."""
    
    content_id: str = Field(..., description="Content ID to post")
    integration_id: str = Field(..., description="LinkedIn integration ID to use")
    schedule_time: Optional[datetime] = Field(None, description="Optional scheduled posting time")


class EnqueuePostingResponse(BaseModel):
    """Response model for enqueuing content posting."""
    
    task_id: str
    content_id: str
    integration_id: str
    scheduled_for: Optional[datetime] = None
    enqueued_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    estimated_execution: Optional[datetime] = None


class JobMetricsResponse(BaseModel):
    """Response model for job metrics."""
    
    active_tasks: int
    pending_tasks: int
    failed_tasks: int
    successful_tasks: int
    retry_tasks: int
    total_tasks: int
    
    average_task_duration: float
    success_rate: float
    failure_rate: float
    
    linkedin_posts_today: int
    engagement_syncs_today: int
    token_refreshes_today: int
    
    last_updated: str


class SystemHealthResponse(BaseModel):
    """Response model for system health."""
    
    celery_workers: int
    redis_status: str
    database_status: str
    linkedin_api_status: str
    
    queue_lengths: Dict[str, int]
    worker_status: Dict[str, str]
    
    uptime_seconds: int
    memory_usage_mb: int
    cpu_usage_percent: float
    
    overall_status: str
    health_score: int
    
    last_health_check: str


@router.get("/metrics", response_model=JobMetricsResponse)
async def get_job_processing_metrics(
    hours: int = 24,
    current_user: User = Depends(get_current_user)
) -> JobMetricsResponse:
    """
    Get job processing metrics for monitoring dashboard.
    
    This endpoint provides comprehensive statistics about background job
    processing including success rates, task counts, and performance metrics.
    
    Args:
        hours: Time period to analyze (default: 24 hours)
        current_user: Authenticated user
        
    Returns:
        JobMetricsResponse with current metrics
    """
    logger.info("Fetching job metrics",
               user_id=str(current_user.id),
               time_period_hours=hours)
    
    try:
        metrics = get_job_metrics(hours)
        
        response = JobMetricsResponse(**metrics.to_dict())
        
        logger.info("Job metrics retrieved successfully",
                   user_id=str(current_user.id),
                   total_tasks=metrics.total_tasks,
                   success_rate=metrics.success_rate)
        
        return response
        
    except Exception as e:
        logger.error("Failed to retrieve job metrics",
                    user_id=str(current_user.id),
                    error=str(e),
                    exc_info=True)
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve job processing metrics"
        )


@router.get("/health", response_model=SystemHealthResponse)
async def get_system_health_status(
    current_user: User = Depends(get_current_user)
) -> SystemHealthResponse:
    """
    Get comprehensive system health status.
    
    This endpoint provides real-time health monitoring for all system
    components including Celery workers, Redis, database, and external APIs.
    
    Args:
        current_user: Authenticated user
        
    Returns:
        SystemHealthResponse with current health status
    """
    logger.info("Fetching system health status", user_id=str(current_user.id))
    
    try:
        health = get_system_health()
        
        response = SystemHealthResponse(**health.to_dict())
        
        logger.info("System health status retrieved",
                   user_id=str(current_user.id),
                   overall_status=health.overall_status,
                   health_score=health.health_score)
        
        return response
        
    except Exception as e:
        logger.error("Failed to retrieve system health",
                    user_id=str(current_user.id),
                    error=str(e),
                    exc_info=True)
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve system health status"
        )


@router.post("/posting/enqueue", response_model=EnqueuePostingResponse)
async def enqueue_content_posting_job(
    request: EnqueuePostingRequest,
    current_user: User = Depends(get_current_user)
) -> EnqueuePostingResponse:
    """
    Enqueue content for LinkedIn posting.
    
    This endpoint enables scheduling content for optimal posting times
    or immediate posting with the proven engagement templates.
    
    Args:
        request: Content posting request details
        current_user: Authenticated user
        
    Returns:
        EnqueuePostingResponse with task details
    """
    logger.info("Enqueuing content for LinkedIn posting",
               user_id=str(current_user.id),
               content_id=request.content_id,
               integration_id=request.integration_id,
               scheduled=request.schedule_time is not None)
    
    try:
        # TODO: Verify user has access to content and integration
        # This would check organization-level permissions
        
        # Enqueue the posting task
        task_id = enqueue_content_posting(
            content_id=request.content_id,
            integration_id=request.integration_id,
            schedule_time=request.schedule_time
        )
        
        response = EnqueuePostingResponse(
            task_id=task_id,
            content_id=request.content_id,
            integration_id=request.integration_id,
            scheduled_for=request.schedule_time,
            estimated_execution=request.schedule_time or datetime.now(timezone.utc)
        )
        
        logger.info("Content posting job enqueued successfully",
                   user_id=str(current_user.id),
                   task_id=task_id,
                   content_id=request.content_id)
        
        return response
        
    except Exception as e:
        logger.error("Failed to enqueue content posting job",
                    user_id=str(current_user.id),
                    content_id=request.content_id,
                    error=str(e),
                    exc_info=True)
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to enqueue content for posting"
        )


@router.get("/tasks/{task_id}/status", response_model=TaskStatusResponse)
async def get_task_status_by_id(
    task_id: str,
    current_user: User = Depends(get_current_user)
) -> TaskStatusResponse:
    """
    Get status of a specific background task.
    
    This enables tracking of content posting, analytics sync, and other
    background operations with real-time status updates.
    
    Args:
        task_id: Task ID to check
        current_user: Authenticated user
        
    Returns:
        TaskStatusResponse with task status
    """
    logger.info("Fetching task status",
               user_id=str(current_user.id),
               task_id=task_id)
    
    try:
        status_info = get_task_status(task_id)
        
        response = TaskStatusResponse(**status_info)
        
        logger.info("Task status retrieved",
                   user_id=str(current_user.id),
                   task_id=task_id,
                   status=status_info["status"])
        
        return response
        
    except Exception as e:
        logger.error("Failed to retrieve task status",
                    user_id=str(current_user.id),
                    task_id=task_id,
                    error=str(e),
                    exc_info=True)
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve task status"
        )


@router.post("/analytics/sync")
async def trigger_engagement_metrics_sync(
    integration_ids: Optional[List[str]] = None,
    background_tasks: BackgroundTasks = BackgroundTasks(),
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Trigger engagement metrics synchronization.
    
    This enables on-demand syncing of LinkedIn engagement data
    for real-time analytics and performance tracking.
    
    Args:
        integration_ids: Optional list of specific integrations to sync
        background_tasks: FastAPI background tasks
        current_user: Authenticated user
        
    Returns:
        Dictionary with sync initiation status
    """
    logger.info("Triggering engagement metrics sync",
               user_id=str(current_user.id),
               integration_count=len(integration_ids) if integration_ids else "all")
    
    try:
        # TODO: Verify user has access to specified integrations
        
        # Trigger sync task
        task = sync_engagement_metrics.delay(integration_ids)
        
        response = {
            "message": "Engagement metrics sync initiated",
            "task_id": task.id,
            "integration_ids": integration_ids,
            "initiated_at": datetime.now(timezone.utc).isoformat(),
            "estimated_duration_minutes": 2
        }
        
        logger.info("Engagement metrics sync initiated",
                   user_id=str(current_user.id),
                   task_id=task.id)
        
        return response
        
    except Exception as e:
        logger.error("Failed to trigger engagement sync",
                    user_id=str(current_user.id),
                    error=str(e),
                    exc_info=True)
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to initiate engagement metrics sync"
        )


@router.post("/health/check")
async def trigger_health_check(
    background_tasks: BackgroundTasks = BackgroundTasks(),
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Trigger manual health check of all system components.
    
    This enables on-demand system health verification for operational monitoring.
    
    Args:
        background_tasks: FastAPI background tasks
        current_user: Authenticated user
        
    Returns:
        Dictionary with health check initiation status
    """
    logger.info("Triggering manual health check",
               user_id=str(current_user.id))
    
    try:
        # Trigger health check task
        task = health_check_job.delay()
        
        response = {
            "message": "System health check initiated",
            "task_id": task.id,
            "initiated_at": datetime.now(timezone.utc).isoformat(),
            "check_duration_seconds": 30
        }
        
        logger.info("Health check initiated",
                   user_id=str(current_user.id),
                   task_id=task.id)
        
        return response
        
    except Exception as e:
        logger.error("Failed to trigger health check",
                    user_id=str(current_user.id),
                    error=str(e),
                    exc_info=True)
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to initiate system health check"
        )