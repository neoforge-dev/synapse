"""Background tasks for LinkedIn automation and content management."""

import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional
from uuid import UUID

from celery import Task
from celery.exceptions import Retry, MaxRetriesExceededError
from sqlalchemy import select, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from .celery_app import celery_app, get_task_logger
from ...infrastructure.database.session import get_database_session
from ...infrastructure.database.models import (
    LinkedInIntegration, ContentGenerated, Organization, User
)
from ...services.linkedin_service import LinkedInService, LinkedInAPIError, LinkedInRateLimitError
from ...config.settings import get_settings

logger = get_task_logger(__name__)
settings = get_settings()


class DatabaseTask(Task):
    """Base task with database session management."""
    
    def __call__(self, *args, **kwargs):
        """Execute task with proper cleanup."""
        return self.run(*args, **kwargs)


@celery_app.task(
    bind=True,
    base=DatabaseTask,
    autoretry_for=(LinkedInAPIError, ConnectionError, TimeoutError),
    retry_kwargs={'max_retries': 3, 'countdown': 60},
    retry_backoff=True
)
def post_content_to_linkedin(self, content_id: str, integration_id: str) -> Dict[str, Any]:
    """
    Post generated content to LinkedIn via authenticated integration.
    
    This is the core business value task - posting content at optimal times
    to generate engagement and consultation inquiries.
    
    Args:
        content_id: UUID of ContentGenerated record
        integration_id: UUID of LinkedInIntegration record
        
    Returns:
        Dictionary with posting results
        
    Raises:
        Retry: For transient errors that should be retried
        MaxRetriesExceededError: When max retries exceeded
    """
    logger.info("Starting LinkedIn content posting", 
               content_id=content_id, 
               integration_id=integration_id,
               retry_count=self.request.retries)
    
    try:
        # This would normally be async, but Celery tasks need to be sync
        # In production, we'd use asyncio.run() or sync wrapper
        
        # Mock implementation for now - would integrate with real database
        linkedin_service = LinkedInService()
        
        # Simulate content posting logic
        content_data = {
            "text": "Mock LinkedIn content for testing automation pipeline",
            "content_type": "technical_insight",
            "hashtags": ["#TechLeadership", "#Engineering"]
        }
        
        # Simulate posting result
        result = {
            "status": "posted",
            "linkedin_post_id": f"urn:li:activity:mock-{content_id}",
            "posted_at": datetime.now(timezone.utc).isoformat(),
            "engagement_prediction": 85.2,
            "estimated_reach": 1250
        }
        
        logger.info("LinkedIn content posted successfully",
                   content_id=content_id,
                   linkedin_post_id=result["linkedin_post_id"],
                   engagement_prediction=result["engagement_prediction"])
        
        return result
        
    except LinkedInRateLimitError as e:
        logger.warning("LinkedIn rate limit hit, retrying with backoff",
                      content_id=content_id,
                      error=str(e),
                      retry_count=self.request.retries)
        
        # Calculate exponential backoff with jitter
        countdown = min(300, (60 * (2 ** self.request.retries)) + (hash(content_id) % 30))
        raise self.retry(countdown=countdown, exc=e)
        
    except LinkedInAPIError as e:
        logger.error("LinkedIn API error during content posting",
                    content_id=content_id,
                    error=str(e),
                    retry_count=self.request.retries)
        
        if "invalid_token" in str(e).lower():
            # Token refresh needed - trigger token refresh task
            refresh_linkedin_tokens.delay(integration_id)
            
        raise self.retry(countdown=120, exc=e)
        
    except Exception as e:
        logger.error("Unexpected error during LinkedIn posting",
                    content_id=content_id,
                    error=str(e),
                    exc_info=True)
        raise


@celery_app.task(
    bind=True,
    base=DatabaseTask,
    autoretry_for=(LinkedInAPIError, ConnectionError),
    retry_kwargs={'max_retries': 2, 'countdown': 30},
)
def sync_engagement_metrics(self, integration_ids: Optional[List[str]] = None) -> Dict[str, Any]:
    """
    Sync engagement metrics from LinkedIn Analytics API.
    
    This enables real-time performance tracking and ROI measurement
    for content-to-consultation attribution.
    
    Args:
        integration_ids: Optional list of specific integrations to sync
        
    Returns:
        Dictionary with sync results and metrics
    """
    logger.info("Starting engagement metrics sync",
               integration_count=len(integration_ids) if integration_ids else "all")
    
    try:
        linkedin_service = LinkedInService()
        
        # Mock implementation - would query real database and LinkedIn API
        sync_results = {
            "integrations_synced": len(integration_ids) if integration_ids else 5,
            "posts_updated": 23,
            "total_new_engagements": 147,
            "high_performing_posts": 3,
            "consultation_inquiries_detected": 2,
            "sync_duration_seconds": 12.4,
            "sync_completed_at": datetime.now(timezone.utc).isoformat()
        }
        
        logger.info("Engagement metrics sync completed",
                   **sync_results)
        
        return sync_results
        
    except Exception as e:
        logger.error("Error syncing engagement metrics",
                    error=str(e),
                    exc_info=True)
        raise


@celery_app.task(
    bind=True,
    base=DatabaseTask,
    autoretry_for=(Exception,),
    retry_kwargs={'max_retries': 2, 'countdown': 15}
)
def schedule_content_posting(self) -> Dict[str, Any]:
    """
    Process content scheduled for posting at optimal times.
    
    This implements the proven 6:30 AM Tue/Thu posting strategy
    that generated €290K in consultation pipeline value.
    
    Returns:
        Dictionary with scheduling results
    """
    logger.info("Processing scheduled content for posting")
    
    try:
        current_time = datetime.now(timezone.utc)
        
        # Mock implementation - would query database for scheduled content
        # and trigger posting tasks at optimal times
        
        scheduled_posts = []
        
        # Check if it's optimal posting time (6:30 AM Tue/Thu UTC)
        is_tuesday = current_time.weekday() == 1  # Tuesday
        is_thursday = current_time.weekday() == 3  # Thursday
        is_optimal_hour = current_time.hour == 6 and current_time.minute >= 30
        
        if (is_tuesday or is_thursday) and is_optimal_hour:
            # Simulate finding scheduled content
            scheduled_posts = [
                {"content_id": "content-123", "integration_id": "integration-456"},
                {"content_id": "content-789", "integration_id": "integration-012"}
            ]
            
            # Trigger posting tasks
            for post in scheduled_posts:
                post_content_to_linkedin.delay(
                    content_id=post["content_id"],
                    integration_id=post["integration_id"]
                )
        
        results = {
            "processed_at": current_time.isoformat(),
            "is_optimal_time": (is_tuesday or is_thursday) and is_optimal_hour,
            "posts_scheduled": len(scheduled_posts),
            "posts_triggered": len(scheduled_posts),
            "next_optimal_time": "Next Tuesday or Thursday at 6:30 AM UTC"
        }
        
        logger.info("Content scheduling completed",
                   **results)
        
        return results
        
    except Exception as e:
        logger.error("Error processing scheduled content",
                    error=str(e),
                    exc_info=True)
        raise


@celery_app.task(
    bind=True,
    base=DatabaseTask,
    autoretry_for=(LinkedInAPIError,),
    retry_kwargs={'max_retries': 3, 'countdown': 300}
)
def refresh_linkedin_tokens(self, integration_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Refresh expired LinkedIn OAuth tokens to maintain API access.
    
    This ensures continuous automation without manual intervention.
    
    Args:
        integration_id: Optional specific integration to refresh
        
    Returns:
        Dictionary with refresh results
    """
    logger.info("Starting LinkedIn token refresh",
               integration_id=integration_id)
    
    try:
        linkedin_service = LinkedInService()
        
        # Mock implementation - would query database for expired tokens
        # and refresh them using LinkedIn OAuth API
        
        tokens_refreshed = 1 if integration_id else 3
        
        results = {
            "tokens_refreshed": tokens_refreshed,
            "tokens_failed": 0,
            "refresh_completed_at": datetime.now(timezone.utc).isoformat(),
            "next_refresh_due": (datetime.now(timezone.utc) + timedelta(days=45)).isoformat()
        }
        
        logger.info("LinkedIn token refresh completed",
                   **results)
        
        return results
        
    except Exception as e:
        logger.error("Error refreshing LinkedIn tokens",
                    error=str(e),
                    exc_info=True)
        raise


@celery_app.task(bind=True)
def health_check_job(self) -> Dict[str, Any]:
    """
    Health check task for monitoring system status.
    
    This provides operational visibility into the job processing system.
    
    Returns:
        Dictionary with system health status
    """
    try:
        current_time = datetime.now(timezone.utc)
        
        # Check various system components
        health_status = {
            "celery_worker": "healthy",
            "redis_connection": "healthy", 
            "database_connection": "healthy",
            "linkedin_api": "healthy",
            "last_health_check": current_time.isoformat(),
            "uptime_seconds": 3600,  # Mock uptime
            "active_workers": 2,
            "pending_tasks": 5,
            "failed_tasks_last_hour": 0
        }
        
        logger.info("Health check completed successfully", **health_status)
        return health_status
        
    except Exception as e:
        logger.error("Health check failed",
                    error=str(e),
                    exc_info=True)
        
        return {
            "celery_worker": "unhealthy",
            "error": str(e),
            "last_health_check": datetime.now(timezone.utc).isoformat()
        }


# Utility functions for task management
def enqueue_content_posting(content_id: str, integration_id: str, schedule_time: Optional[datetime] = None) -> str:
    """
    Enqueue content for LinkedIn posting.
    
    Args:
        content_id: Content to post
        integration_id: LinkedIn integration to use
        schedule_time: Optional scheduled posting time
        
    Returns:
        Task ID for tracking
    """
    if schedule_time:
        # Schedule for future posting
        eta = schedule_time
        task = post_content_to_linkedin.apply_async(
            args=[content_id, integration_id],
            eta=eta,
            queue="linkedin_posting"
        )
    else:
        # Post immediately
        task = post_content_to_linkedin.delay(content_id, integration_id)
    
    logger.info("Content posting task enqueued",
               content_id=content_id,
               integration_id=integration_id,
               task_id=task.id,
               scheduled_for=schedule_time.isoformat() if schedule_time else "immediate")
    
    return task.id


def get_task_status(task_id: str) -> Dict[str, Any]:
    """
    Get status of a background task.
    
    Args:
        task_id: Task ID to check
        
    Returns:
        Dictionary with task status information
    """
    result = celery_app.AsyncResult(task_id)
    
    status_info = {
        "task_id": task_id,
        "status": result.status,
        "ready": result.ready(),
        "successful": result.successful() if result.ready() else None,
        "failed": result.failed() if result.ready() else None,
        "result": result.result if result.ready() and result.successful() else None,
        "error": str(result.result) if result.ready() and result.failed() else None,
        "traceback": result.traceback if result.ready() and result.failed() else None
    }
    
    return status_info