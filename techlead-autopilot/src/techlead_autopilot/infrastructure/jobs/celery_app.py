"""Celery application configuration for background job processing."""

import os
import logging
from datetime import timedelta
from celery import Celery
from celery.signals import setup_logging

from ...config.settings import get_settings

# Get application settings
settings = get_settings()

# Create Celery application
celery_app = Celery(
    "techlead_autopilot",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=[
        "techlead_autopilot.infrastructure.jobs.tasks"
    ]
)

# Celery configuration
celery_app.conf.update(
    # Task settings
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    
    # Result backend settings
    result_expires=3600,  # Results expire after 1 hour
    result_backend_transport_options={
        "master_name": "mymaster",
        "visibility_timeout": 3600,
    },
    
    # Worker settings
    worker_prefetch_multiplier=1,
    task_acks_late=True,
    worker_max_tasks_per_child=1000,
    
    # Task routing and queues
    task_routes={
        "techlead_autopilot.infrastructure.jobs.tasks.post_content_to_linkedin": {
            "queue": "linkedin_posting",
            "priority": 8
        },
        "techlead_autopilot.infrastructure.jobs.tasks.sync_engagement_metrics": {
            "queue": "analytics", 
            "priority": 5
        },
        "techlead_autopilot.infrastructure.jobs.tasks.schedule_content_posting": {
            "queue": "scheduling",
            "priority": 7
        },
        "techlead_autopilot.infrastructure.jobs.tasks.refresh_linkedin_tokens": {
            "queue": "maintenance",
            "priority": 6
        },
        "techlead_autopilot.infrastructure.jobs.tasks.health_check_job": {
            "queue": "monitoring",
            "priority": 3
        }
    },
    
    # Task retry settings
    task_retry_jitter=True,
    task_retry_backoff=True,
    task_retry_backoff_max=300,  # 5 minutes max backoff
    
    # Beat scheduler settings for periodic tasks
    beat_schedule={
        # Sync engagement metrics every 30 minutes
        "sync-engagement-metrics": {
            "task": "techlead_autopilot.infrastructure.jobs.tasks.sync_engagement_metrics",
            "schedule": timedelta(minutes=30),
            "options": {"queue": "analytics", "priority": 5}
        },
        
        # Refresh LinkedIn tokens daily at 2 AM
        "refresh-linkedin-tokens": {
            "task": "techlead_autopilot.infrastructure.jobs.tasks.refresh_linkedin_tokens", 
            "schedule": timedelta(hours=24),
            "options": {"queue": "maintenance", "priority": 6}
        },
        
        # Health check every 5 minutes
        "health-check": {
            "task": "techlead_autopilot.infrastructure.jobs.tasks.health_check_job",
            "schedule": timedelta(minutes=5),
            "options": {"queue": "monitoring", "priority": 3}
        },
        
        # Process scheduled content posting every minute
        "process-scheduled-content": {
            "task": "techlead_autopilot.infrastructure.jobs.tasks.schedule_content_posting",
            "schedule": timedelta(minutes=1),
            "options": {"queue": "scheduling", "priority": 7}
        }
    },
    
    # Error handling
    task_reject_on_worker_lost=True,
    task_ignore_result=False,
    
    # Security settings
    worker_hijack_root_logger=False,
    worker_log_color=False if os.getenv("ENVIRONMENT") == "production" else True,
)


@setup_logging.connect
def config_loggers(*args, **kwargs):
    """Configure logging for Celery workers."""
    from logging.config import dictConfig
    
    logging_config = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "default": {
                "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            },
            "json": {
                "()": "pythonjsonlogger.jsonlogger.JsonFormatter",
                "format": "%(asctime)s %(name)s %(levelname)s %(message)s",
            },
        },
        "handlers": {
            "default": {
                "level": "INFO",
                "class": "logging.StreamHandler",
                "formatter": "json" if settings.log_format == "json" else "default",
            },
        },
        "loggers": {
            "celery": {
                "handlers": ["default"],
                "level": settings.log_level,
                "propagate": False,
            },
            "techlead_autopilot": {
                "handlers": ["default"],
                "level": settings.log_level,
                "propagate": False,
            },
        },
        "root": {
            "level": settings.log_level,
            "handlers": ["default"],
        },
    }
    
    dictConfig(logging_config)


# Task decorators and utilities
def get_task_logger(name: str):
    """Get a task logger with proper formatting."""
    logger = celery_app.log.get_default_logger()
    logger.name = name
    return logger