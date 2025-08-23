"""Production-grade logging system with structured logs and rotation."""

import json
import logging
import logging.config
import logging.handlers
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional, Union

import structlog
from pythonjsonlogger.json import JsonFormatter

from ..config.settings import get_settings


class CustomJSONFormatter(JsonFormatter):
    """Custom JSON formatter with additional fields."""
    
    def add_fields(self, log_record: Dict[str, Any], record: logging.LogRecord, message_dict: Dict[str, Any]) -> None:
        """Add custom fields to log record."""
        super().add_fields(log_record, record, message_dict)
        
        # Add timestamp in ISO format
        if not log_record.get('timestamp'):
            log_record['timestamp'] = datetime.utcnow().isoformat() + 'Z'
        
        # Add service information
        log_record['service'] = 'techlead-autopilot'
        log_record['version'] = get_settings().version
        log_record['environment'] = get_settings().environment
        
        # Add request ID if available
        if hasattr(record, 'request_id'):
            log_record['request_id'] = record.request_id
        
        # Add user ID if available
        if hasattr(record, 'user_id'):
            log_record['user_id'] = record.user_id
        
        # Add organization ID if available
        if hasattr(record, 'organization_id'):
            log_record['organization_id'] = record.organization_id


class StructuredLogProcessor:
    """Processor for structlog to add consistent fields."""
    
    def __call__(self, logger: Any, method_name: str, event_dict: Dict[str, Any]) -> Dict[str, Any]:
        """Process log event dictionary."""
        settings = get_settings()
        
        # Add standard fields
        event_dict.setdefault('timestamp', datetime.utcnow().isoformat() + 'Z')
        event_dict.setdefault('service', 'techlead-autopilot')
        event_dict.setdefault('version', settings.version)
        event_dict.setdefault('environment', settings.environment)
        
        return event_dict


def setup_logging() -> None:
    """Set up production-grade logging configuration."""
    settings = get_settings()
    
    # Create logs directory if it doesn't exist
    log_dir = Path('logs')
    log_dir.mkdir(exist_ok=True)
    
    # Base logging configuration
    logging_config: Dict[str, Any] = {
        'version': 1,
        'disable_existing_loggers': False,
        'formatters': {
            'json': {
                '()': CustomJSONFormatter,
                'format': '%(timestamp)s %(level)s %(name)s %(message)s'
            },
            'console': {
                'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                'datefmt': '%Y-%m-%d %H:%M:%S'
            }
        },
        'handlers': {
            'console': {
                'class': 'logging.StreamHandler',
                'formatter': 'console' if settings.is_development else 'json',
                'stream': sys.stdout,
                'level': settings.log_level
            }
        },
        'root': {
            'level': settings.log_level,
            'handlers': ['console']
        },
        'loggers': {
            'techlead_autopilot': {
                'level': settings.log_level,
                'handlers': ['console'],
                'propagate': False
            },
            'uvicorn': {
                'level': 'INFO',
                'handlers': ['console'],
                'propagate': False
            },
            'fastapi': {
                'level': 'INFO',
                'handlers': ['console'],
                'propagate': False
            }
        }
    }
    
    # Add file logging for production and staging
    if not settings.is_development:
        # Main application log with rotation
        logging_config['handlers']['file_app'] = {
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': log_dir / 'app.log',
            'maxBytes': 50 * 1024 * 1024,  # 50MB
            'backupCount': 10,
            'formatter': 'json',
            'level': settings.log_level
        }
        
        # Error log with rotation
        logging_config['handlers']['file_error'] = {
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': log_dir / 'error.log',
            'maxBytes': 50 * 1024 * 1024,  # 50MB
            'backupCount': 10,
            'formatter': 'json',
            'level': 'ERROR'
        }
        
        # Access log for API requests
        logging_config['handlers']['file_access'] = {
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': log_dir / 'access.log',
            'maxBytes': 50 * 1024 * 1024,  # 50MB
            'backupCount': 10,
            'formatter': 'json',
            'level': 'INFO'
        }
        
        # Audit log for security events
        logging_config['handlers']['file_audit'] = {
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': log_dir / 'audit.log',
            'maxBytes': 50 * 1024 * 1024,  # 50MB
            'backupCount': 20,  # Keep more audit logs
            'formatter': 'json',
            'level': 'INFO'
        }
        
        # Update root and logger handlers
        logging_config['root']['handlers'].extend(['file_app', 'file_error'])
        logging_config['loggers']['techlead_autopilot']['handlers'].extend(['file_app', 'file_error'])
        
        # Add access logger
        logging_config['loggers']['access'] = {
            'level': 'INFO',
            'handlers': ['file_access'],
            'propagate': False
        }
        
        # Add audit logger
        logging_config['loggers']['audit'] = {
            'level': 'INFO',
            'handlers': ['file_audit'],
            'propagate': False
        }
    
    # Apply logging configuration
    logging.config.dictConfig(logging_config)
    
    # Configure structlog
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            StructuredLogProcessor(),
            structlog.processors.JSONRenderer()
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    """Get a structured logger instance."""
    return structlog.get_logger(name)


def get_access_logger() -> logging.Logger:
    """Get the access logger for API requests."""
    return logging.getLogger('access')


def get_audit_logger() -> logging.Logger:
    """Get the audit logger for security events."""
    return logging.getLogger('audit')


class LoggerMixin:
    """Mixin to add logging capabilities to classes."""
    
    @property
    def logger(self) -> structlog.stdlib.BoundLogger:
        """Get logger for this class."""
        return get_logger(self.__class__.__name__)


def log_api_request(
    method: str,
    path: str,
    status_code: int,
    duration_ms: float,
    user_id: Optional[str] = None,
    request_id: Optional[str] = None,
    user_agent: Optional[str] = None,
    ip_address: Optional[str] = None
) -> None:
    """Log API request with structured data."""
    access_logger = get_access_logger()
    
    log_data = {
        'event': 'api_request',
        'method': method,
        'path': path,
        'status_code': status_code,
        'duration_ms': duration_ms,
        'timestamp': datetime.utcnow().isoformat() + 'Z'
    }
    
    if user_id:
        log_data['user_id'] = user_id
    if request_id:
        log_data['request_id'] = request_id
    if user_agent:
        log_data['user_agent'] = user_agent
    if ip_address:
        log_data['ip_address'] = ip_address
    
    access_logger.info(json.dumps(log_data))


def log_security_event(
    event_type: str,
    description: str,
    user_id: Optional[str] = None,
    ip_address: Optional[str] = None,
    additional_data: Optional[Dict[str, Any]] = None
) -> None:
    """Log security event for audit trail."""
    audit_logger = get_audit_logger()
    
    log_data = {
        'event': 'security_event',
        'event_type': event_type,
        'description': description,
        'timestamp': datetime.utcnow().isoformat() + 'Z'
    }
    
    if user_id:
        log_data['user_id'] = user_id
    if ip_address:
        log_data['ip_address'] = ip_address
    if additional_data:
        log_data.update(additional_data)
    
    audit_logger.info(json.dumps(log_data))


def log_error(
    error: Exception,
    context: Optional[Dict[str, Any]] = None,
    user_id: Optional[str] = None,
    request_id: Optional[str] = None
) -> None:
    """Log error with context information."""
    logger = get_logger('error')
    
    error_data = {
        'event': 'error',
        'error_type': type(error).__name__,
        'error_message': str(error),
        'timestamp': datetime.utcnow().isoformat() + 'Z'
    }
    
    if context:
        error_data['context'] = context
    if user_id:
        error_data['user_id'] = user_id
    if request_id:
        error_data['request_id'] = request_id
    
    logger.error("Application error occurred", **error_data, exc_info=True)


def log_business_event(
    event_type: str,
    description: str,
    user_id: Optional[str] = None,
    organization_id: Optional[str] = None,
    additional_data: Optional[Dict[str, Any]] = None
) -> None:
    """Log business events for analytics and monitoring."""
    logger = get_logger('business')
    
    event_data = {
        'event': 'business_event',
        'event_type': event_type,
        'description': description,
        'timestamp': datetime.utcnow().isoformat() + 'Z'
    }
    
    if user_id:
        event_data['user_id'] = user_id
    if organization_id:
        event_data['organization_id'] = organization_id
    if additional_data:
        event_data.update(additional_data)
    
    logger.info("Business event occurred", **event_data)


# Initialize logging on module import
if not logging.getLogger().handlers:
    setup_logging()