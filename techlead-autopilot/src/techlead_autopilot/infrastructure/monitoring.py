"""Comprehensive error tracking and monitoring with Sentry-style monitoring."""

import os
import traceback
from typing import Any, Dict, Optional, Union

import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration
from sentry_sdk.integrations.asyncio import AsyncioIntegration
from sentry_sdk.integrations.logging import LoggingIntegration
from sentry_sdk.integrations.redis import RedisIntegration

from ..config.settings import get_settings
from .logging import get_logger, log_error


class MonitoringService:
    """Service for application monitoring and error tracking."""
    
    def __init__(self):
        """Initialize monitoring service."""
        self.settings = get_settings()
        self.logger = get_logger('monitoring')
        self._sentry_initialized = False
        
        # Initialize Sentry if DSN is provided
        if self.settings.sentry_dsn:
            self._init_sentry()
    
    def _init_sentry(self) -> None:
        """Initialize Sentry SDK with proper configuration."""
        try:
            # Logging integration to capture log messages
            logging_integration = LoggingIntegration(
                level=None,  # Capture info and above as breadcrumbs
                event_level=None  # Send error logs as events
            )
            
            sentry_sdk.init(
                dsn=self.settings.sentry_dsn,
                environment=self.settings.environment,
                release=f"techlead-autopilot@{self.settings.version}",
                traces_sample_rate=self.settings.sentry_traces_sample_rate,
                profiles_sample_rate=0.1 if self.settings.environment == "production" else 0,
                integrations=[
                    FastApiIntegration(auto_enabling=True),
                    SqlalchemyIntegration(),
                    AsyncioIntegration(),
                    logging_integration,
                    RedisIntegration(),
                ],
                # Performance monitoring
                enable_tracing=True,
                # Data scrubbing
                send_default_pii=False,
                before_send=self._before_send_event,
                before_send_transaction=self._before_send_transaction,
            )
            
            self._sentry_initialized = True
            self.logger.info("Sentry monitoring initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize Sentry: {e}")
    
    def _before_send_event(self, event: Dict[str, Any], hint: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Filter and modify events before sending to Sentry."""
        # Skip health check errors
        if event.get('request', {}).get('url', '').endswith('/health'):
            return None
        
        # Add custom tags
        event.setdefault('tags', {})
        event['tags'].update({
            'service': 'techlead-autopilot',
            'version': self.settings.version,
            'environment': self.settings.environment
        })
        
        # Add custom context
        event.setdefault('contexts', {})
        event['contexts']['application'] = {
            'name': 'TechLead AutoPilot',
            'version': self.settings.version
        }
        
        return event
    
    def _before_send_transaction(self, event: Dict[str, Any], hint: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Filter and modify transactions before sending to Sentry."""
        # Skip health check transactions
        transaction_name = event.get('transaction', '')
        if 'health' in transaction_name.lower():
            return None
        
        return event
    
    def capture_exception(
        self,
        error: Exception,
        user_id: Optional[str] = None,
        organization_id: Optional[str] = None,
        request_id: Optional[str] = None,
        additional_context: Optional[Dict[str, Any]] = None
    ) -> Optional[str]:
        """Capture exception with context information."""
        context = {}
        
        if user_id:
            context['user_id'] = user_id
        if organization_id:
            context['organization_id'] = organization_id
        if request_id:
            context['request_id'] = request_id
        if additional_context:
            context.update(additional_context)
        
        # Log error locally first
        log_error(error, context, user_id, request_id)
        
        # Send to Sentry if available
        if self._sentry_initialized:
            with sentry_sdk.configure_scope() as scope:
                # Add user context
                if user_id:
                    scope.user = {"id": user_id}
                
                # Add custom context
                for key, value in context.items():
                    scope.set_context(key, value)
                
                # Capture exception
                event_id = sentry_sdk.capture_exception(error)
                self.logger.info(f"Exception captured with Sentry ID: {event_id}")
                return event_id
        
        return None
    
    def capture_message(
        self,
        message: str,
        level: str = "info",
        user_id: Optional[str] = None,
        additional_context: Optional[Dict[str, Any]] = None
    ) -> Optional[str]:
        """Capture custom message."""
        context = additional_context or {}
        
        if self._sentry_initialized:
            with sentry_sdk.configure_scope() as scope:
                if user_id:
                    scope.user = {"id": user_id}
                
                for key, value in context.items():
                    scope.set_context(key, value)
                
                event_id = sentry_sdk.capture_message(message, level)
                return event_id
        
        # Also log locally
        logger_method = getattr(self.logger, level.lower(), self.logger.info)
        logger_method(message, **context)
        
        return None
    
    def set_user_context(
        self,
        user_id: str,
        email: Optional[str] = None,
        username: Optional[str] = None,
        organization_id: Optional[str] = None
    ) -> None:
        """Set user context for error tracking."""
        if self._sentry_initialized:
            with sentry_sdk.configure_scope() as scope:
                scope.user = {
                    "id": user_id,
                    "email": email,
                    "username": username,
                }
                if organization_id:
                    scope.set_tag("organization_id", organization_id)
    
    def set_request_context(
        self,
        request_id: str,
        method: str,
        path: str,
        user_agent: Optional[str] = None
    ) -> None:
        """Set request context for error tracking."""
        if self._sentry_initialized:
            with sentry_sdk.configure_scope() as scope:
                scope.set_context("request", {
                    "id": request_id,
                    "method": method,
                    "path": path,
                    "user_agent": user_agent
                })
    
    def add_breadcrumb(
        self,
        message: str,
        category: str = "custom",
        level: str = "info",
        data: Optional[Dict[str, Any]] = None
    ) -> None:
        """Add breadcrumb for debugging context."""
        if self._sentry_initialized:
            sentry_sdk.add_breadcrumb(
                message=message,
                category=category,
                level=level,
                data=data or {}
            )
    
    def start_transaction(self, name: str, op: str = "http") -> Optional[Any]:
        """Start a performance transaction."""
        if self._sentry_initialized:
            return sentry_sdk.start_transaction(name=name, op=op)
        return None
    
    def is_enabled(self) -> bool:
        """Check if monitoring is enabled."""
        return self._sentry_initialized


# Global monitoring service instance
_monitoring_service: Optional[MonitoringService] = None


def get_monitoring_service() -> MonitoringService:
    """Get or create global monitoring service."""
    global _monitoring_service
    if _monitoring_service is None:
        _monitoring_service = MonitoringService()
    return _monitoring_service


def capture_exception(
    error: Exception,
    user_id: Optional[str] = None,
    organization_id: Optional[str] = None,
    request_id: Optional[str] = None,
    additional_context: Optional[Dict[str, Any]] = None
) -> Optional[str]:
    """Convenience function to capture exception."""
    return get_monitoring_service().capture_exception(
        error, user_id, organization_id, request_id, additional_context
    )


def capture_message(
    message: str,
    level: str = "info",
    user_id: Optional[str] = None,
    additional_context: Optional[Dict[str, Any]] = None
) -> Optional[str]:
    """Convenience function to capture message."""
    return get_monitoring_service().capture_message(message, level, user_id, additional_context)


def set_user_context(
    user_id: str,
    email: Optional[str] = None,
    username: Optional[str] = None,
    organization_id: Optional[str] = None
) -> None:
    """Convenience function to set user context."""
    get_monitoring_service().set_user_context(user_id, email, username, organization_id)


def set_request_context(
    request_id: str,
    method: str,
    path: str,
    user_agent: Optional[str] = None
) -> None:
    """Convenience function to set request context."""
    get_monitoring_service().set_request_context(request_id, method, path, user_agent)


def add_breadcrumb(
    message: str,
    category: str = "custom",
    level: str = "info",
    data: Optional[Dict[str, Any]] = None
) -> None:
    """Convenience function to add breadcrumb."""
    get_monitoring_service().add_breadcrumb(message, category, level, data)


class ErrorTracker:
    """Context manager for tracking errors in code blocks."""
    
    def __init__(
        self,
        operation_name: str,
        user_id: Optional[str] = None,
        additional_context: Optional[Dict[str, Any]] = None
    ):
        """Initialize error tracker."""
        self.operation_name = operation_name
        self.user_id = user_id
        self.context = additional_context or {}
        self.monitoring = get_monitoring_service()
    
    def __enter__(self):
        """Enter context."""
        add_breadcrumb(f"Starting operation: {self.operation_name}")
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit context and handle any exceptions."""
        if exc_type is not None:
            # Exception occurred
            self.monitoring.capture_exception(
                exc_val,
                user_id=self.user_id,
                additional_context={
                    **self.context,
                    "operation": self.operation_name,
                    "traceback": traceback.format_exc()
                }
            )
            add_breadcrumb(
                f"Operation failed: {self.operation_name}",
                category="error",
                level="error",
                data={"error_type": exc_type.__name__, "error_message": str(exc_val)}
            )
        else:
            # Success
            add_breadcrumb(f"Operation completed: {self.operation_name}")
        
        # Don't suppress exceptions
        return False


def track_operation(
    operation_name: str,
    user_id: Optional[str] = None,
    additional_context: Optional[Dict[str, Any]] = None
) -> ErrorTracker:
    """Create an error tracker for an operation."""
    return ErrorTracker(operation_name, user_id, additional_context)