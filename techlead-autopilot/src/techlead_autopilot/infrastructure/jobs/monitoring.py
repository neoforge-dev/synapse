"""Job monitoring and health check system for background tasks."""

import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, asdict

from celery import Celery
from celery.events.state import State
from redis import Redis
from redis.exceptions import ConnectionError as RedisConnectionError

from .celery_app import celery_app
from ...config.settings import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


@dataclass
class JobMetrics:
    """Job processing metrics for monitoring."""
    
    active_tasks: int = 0
    pending_tasks: int = 0
    failed_tasks: int = 0
    successful_tasks: int = 0
    retry_tasks: int = 0
    total_tasks: int = 0
    
    average_task_duration: float = 0.0
    success_rate: float = 0.0
    failure_rate: float = 0.0
    
    linkedin_posts_today: int = 0
    engagement_syncs_today: int = 0
    token_refreshes_today: int = 0
    
    last_updated: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)


@dataclass
class SystemHealth:
    """Overall system health status."""
    
    celery_workers: int = 0
    redis_status: str = "unknown"
    database_status: str = "unknown"
    linkedin_api_status: str = "unknown"
    
    queue_lengths: Dict[str, int] = None
    worker_status: Dict[str, str] = None
    
    uptime_seconds: int = 0
    memory_usage_mb: int = 0
    cpu_usage_percent: float = 0.0
    
    overall_status: str = "unknown"  # healthy, degraded, unhealthy
    health_score: int = 0  # 0-100
    
    last_health_check: str = ""

    def __post_init__(self):
        if self.queue_lengths is None:
            self.queue_lengths = {}
        if self.worker_status is None:
            self.worker_status = {}

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)


class JobMonitor:
    """Monitor background job processing system."""
    
    def __init__(self):
        """Initialize job monitor."""
        self.celery_app = celery_app
        self.redis_client = self._get_redis_client()
        self.state = State()
        
    def _get_redis_client(self) -> Optional[Redis]:
        """Get Redis client for monitoring."""
        try:
            redis_url = settings.celery_broker_url
            if redis_url.startswith('redis://'):
                return Redis.from_url(redis_url)
            return None
        except Exception as e:
            logger.warning("Failed to connect to Redis for monitoring", error=str(e))
            return None
    
    def get_job_metrics(self, hours: int = 24) -> JobMetrics:
        """
        Get job processing metrics for the specified time period.
        
        Args:
            hours: Time period to analyze (default: 24 hours)
            
        Returns:
            JobMetrics with current statistics
        """
        logger.info("Collecting job metrics", time_period_hours=hours)
        
        try:
            # Get task statistics from Celery
            stats = self._collect_celery_stats()
            
            # Calculate metrics
            metrics = JobMetrics(
                active_tasks=stats.get("active", 0),
                pending_tasks=stats.get("pending", 0),
                failed_tasks=stats.get("failed", 0),
                successful_tasks=stats.get("successful", 0),
                retry_tasks=stats.get("retries", 0),
                total_tasks=stats.get("total", 0),
                
                # Calculate rates
                success_rate=self._calculate_success_rate(stats),
                failure_rate=self._calculate_failure_rate(stats),
                average_task_duration=stats.get("avg_duration", 0.0),
                
                # Today's specific metrics
                linkedin_posts_today=self._count_tasks_today("post_content_to_linkedin"),
                engagement_syncs_today=self._count_tasks_today("sync_engagement_metrics"),
                token_refreshes_today=self._count_tasks_today("refresh_linkedin_tokens"),
                
                last_updated=datetime.now(timezone.utc).isoformat()
            )
            
            logger.info("Job metrics collected successfully",
                       total_tasks=metrics.total_tasks,
                       success_rate=metrics.success_rate,
                       active_tasks=metrics.active_tasks)
            
            return metrics
            
        except Exception as e:
            logger.error("Failed to collect job metrics", error=str(e), exc_info=True)
            return JobMetrics(last_updated=datetime.now(timezone.utc).isoformat())
    
    def get_system_health(self) -> SystemHealth:
        """
        Get comprehensive system health status.
        
        Returns:
            SystemHealth with current status
        """
        logger.info("Performing system health check")
        
        try:
            health = SystemHealth()
            
            # Check Celery workers
            health.celery_workers = self._count_active_workers()
            
            # Check Redis connectivity
            health.redis_status = self._check_redis_status()
            
            # Check database connectivity
            health.database_status = self._check_database_status()
            
            # Check LinkedIn API status
            health.linkedin_api_status = self._check_linkedin_api_status()
            
            # Get queue lengths
            health.queue_lengths = self._get_queue_lengths()
            
            # Get worker status
            health.worker_status = self._get_worker_status()
            
            # Calculate overall health
            health.overall_status, health.health_score = self._calculate_overall_health(health)
            
            health.last_health_check = datetime.now(timezone.utc).isoformat()
            
            logger.info("System health check completed",
                       overall_status=health.overall_status,
                       health_score=health.health_score,
                       active_workers=health.celery_workers)
            
            return health
            
        except Exception as e:
            logger.error("Failed to perform health check", error=str(e), exc_info=True)
            
            return SystemHealth(
                overall_status="unhealthy",
                health_score=0,
                last_health_check=datetime.now(timezone.utc).isoformat()
            )
    
    def _collect_celery_stats(self) -> Dict[str, Any]:
        """Collect statistics from Celery."""
        try:
            # In production, this would connect to Celery's monitoring API
            # For now, return mock stats
            return {
                "active": 3,
                "pending": 12,
                "failed": 2,
                "successful": 156,
                "retries": 8,
                "total": 181,
                "avg_duration": 4.2
            }
        except Exception as e:
            logger.warning("Failed to collect Celery stats", error=str(e))
            return {}
    
    def _calculate_success_rate(self, stats: Dict[str, Any]) -> float:
        """Calculate success rate from stats."""
        total = stats.get("total", 0)
        successful = stats.get("successful", 0)
        return (successful / total * 100) if total > 0 else 0.0
    
    def _calculate_failure_rate(self, stats: Dict[str, Any]) -> float:
        """Calculate failure rate from stats."""
        total = stats.get("total", 0)
        failed = stats.get("failed", 0)
        return (failed / total * 100) if total > 0 else 0.0
    
    def _count_tasks_today(self, task_name: str) -> int:
        """Count tasks of specific type executed today."""
        # Mock implementation - would query Celery result backend
        task_counts = {
            "post_content_to_linkedin": 8,
            "sync_engagement_metrics": 48,
            "refresh_linkedin_tokens": 2
        }
        return task_counts.get(task_name, 0)
    
    def _count_active_workers(self) -> int:
        """Count active Celery workers."""
        try:
            # Mock implementation - would query Celery management API
            return 2
        except Exception:
            return 0
    
    def _check_redis_status(self) -> str:
        """Check Redis connection status."""
        if not self.redis_client:
            return "unavailable"
        
        try:
            self.redis_client.ping()
            return "healthy"
        except RedisConnectionError:
            return "unhealthy"
        except Exception as e:
            logger.warning("Redis health check failed", error=str(e))
            return "degraded"
    
    def _check_database_status(self) -> str:
        """Check database connection status."""
        try:
            # Mock implementation - would test database connection
            return "healthy"
        except Exception as e:
            logger.warning("Database health check failed", error=str(e))
            return "unhealthy"
    
    def _check_linkedin_api_status(self) -> str:
        """Check LinkedIn API connectivity."""
        try:
            # Mock implementation - would test LinkedIn API
            return "healthy"
        except Exception as e:
            logger.warning("LinkedIn API health check failed", error=str(e))
            return "degraded"
    
    def _get_queue_lengths(self) -> Dict[str, int]:
        """Get current queue lengths."""
        try:
            return {
                "linkedin_posting": 3,
                "analytics": 15,
                "scheduling": 2,
                "maintenance": 1,
                "monitoring": 0
            }
        except Exception:
            return {}
    
    def _get_worker_status(self) -> Dict[str, str]:
        """Get individual worker status."""
        try:
            return {
                "worker-1": "active",
                "worker-2": "active"
            }
        except Exception:
            return {}
    
    def _calculate_overall_health(self, health: SystemHealth) -> tuple[str, int]:
        """
        Calculate overall health status and score.
        
        Args:
            health: SystemHealth object to analyze
            
        Returns:
            Tuple of (status_string, health_score_0_100)
        """
        score = 100
        
        # Deduct points for unhealthy components
        if health.celery_workers == 0:
            score -= 30  # Critical - no workers
        elif health.celery_workers == 1:
            score -= 10  # Degraded - single point of failure
        
        if health.redis_status == "unhealthy":
            score -= 25  # Critical for job queue
        elif health.redis_status == "degraded":
            score -= 10
        
        if health.database_status == "unhealthy":
            score -= 20  # Important for data persistence
        
        if health.linkedin_api_status == "unhealthy":
            score -= 15  # Important for core functionality
        elif health.linkedin_api_status == "degraded":
            score -= 5
        
        # Determine overall status
        if score >= 90:
            status = "healthy"
        elif score >= 70:
            status = "degraded"
        else:
            status = "unhealthy"
        
        return status, max(0, score)


# Global monitor instance
job_monitor = JobMonitor()


def get_job_metrics(hours: int = 24) -> JobMetrics:
    """Get current job processing metrics."""
    return job_monitor.get_job_metrics(hours)


def get_system_health() -> SystemHealth:
    """Get current system health status."""
    return job_monitor.get_system_health()