"""Production-ready structured logging with correlation IDs and performance tracking."""

import json
import logging
import time
import traceback
import uuid
from contextvars import ContextVar
from dataclasses import asdict, dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

# Context variables for correlation tracking
correlation_id: ContextVar[str | None] = ContextVar('correlation_id', default=None)
user_id: ContextVar[str | None] = ContextVar('user_id', default=None)
request_id: ContextVar[str | None] = ContextVar('request_id', default=None)


class LogLevel(Enum):
    """Log levels with corresponding logging levels."""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class ComponentType(Enum):
    """System component types for structured logging."""
    API = "api"
    ENGINE = "engine"
    SEARCH = "search"
    CITATION = "citation"
    VALIDATION = "validation"
    LLM = "llm"
    VECTOR_STORE = "vector_store"
    GRAPH_STORE = "graph_store"
    INGESTION = "ingestion"
    AUTHENTICATION = "authentication"
    MONITORING = "monitoring"


@dataclass
class LogContext:
    """Structured log context with correlation tracking."""

    # Core identification
    correlation_id: str | None = None
    request_id: str | None = None
    user_id: str | None = None
    session_id: str | None = None

    # Component context
    component: ComponentType | None = None
    operation: str | None = None

    # Performance tracking
    start_time: float | None = None
    duration_ms: float | None = None

    # Business context
    query_id: str | None = None
    document_id: str | None = None
    chunk_id: str | None = None

    # Technical context
    model_name: str | None = None
    tokens_used: int | None = None
    chunk_count: int | None = None

    # Additional metadata
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary, excluding None values."""
        result = {}
        for key, value in asdict(self).items():
            if value is not None:
                result[key] = value
        return result


@dataclass
class StructuredLogRecord:
    """Structured log record for JSON serialization."""

    # Standard fields
    timestamp: str
    level: str
    message: str
    logger: str

    # Correlation fields
    correlation_id: str | None = None
    request_id: str | None = None
    user_id: str | None = None

    # Context fields
    component: str | None = None
    operation: str | None = None

    # Performance fields
    duration_ms: float | None = None

    # Error fields
    error_type: str | None = None
    error_message: str | None = None
    stack_trace: str | None = None

    # Additional metadata
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_json(self) -> str:
        """Serialize to JSON string."""
        data = asdict(self)
        # Remove None values
        data = {k: v for k, v in data.items() if v is not None}
        return json.dumps(data, default=str)


class StructuredLogger:
    """Production-ready structured logger with correlation tracking."""

    def __init__(self, name: str, component: ComponentType | None = None):
        self.name = name
        self.component = component
        self.logger = logging.getLogger(name)
        self._setup_json_formatter()

    def _setup_json_formatter(self):
        """Setup JSON formatter for structured logging."""
        # Create custom formatter that outputs JSON
        formatter = JsonFormatter()

        # Apply to all handlers
        for handler in self.logger.handlers:
            handler.setFormatter(formatter)

        # If no handlers, add a console handler
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)

    def _create_log_record(
        self,
        level: LogLevel,
        message: str,
        context: LogContext | None = None,
        error: Exception | None = None,
        **kwargs
    ) -> StructuredLogRecord:
        """Create a structured log record."""

        # Get correlation info from context vars
        correlation_id_val = correlation_id.get()
        request_id_val = request_id.get()
        user_id_val = user_id.get()

        # Override with context if provided
        if context:
            correlation_id_val = context.correlation_id or correlation_id_val
            request_id_val = context.request_id or request_id_val
            user_id_val = context.user_id or user_id_val

        record = StructuredLogRecord(
            timestamp=datetime.utcnow().isoformat() + "Z",
            level=level.value,
            message=message,
            logger=self.name,
            correlation_id=correlation_id_val,
            request_id=request_id_val,
            user_id=user_id_val,
            component=self.component.value if self.component else context.component.value if context and context.component else None,
            operation=context.operation if context else None,
            duration_ms=context.duration_ms if context else None,
            metadata=dict(kwargs)
        )

        # Add error information if present
        if error:
            record.error_type = type(error).__name__
            record.error_message = str(error)
            record.stack_trace = traceback.format_exc()

        # Add context metadata
        if context and context.metadata:
            record.metadata.update(context.metadata)

        return record

    def debug(self, message: str, context: LogContext | None = None, **kwargs):
        """Log debug message with structured context."""
        if self.logger.isEnabledFor(logging.DEBUG):
            record = self._create_log_record(LogLevel.DEBUG, message, context, **kwargs)
            self.logger.debug(record.to_json())

    def info(self, message: str, context: LogContext | None = None, **kwargs):
        """Log info message with structured context."""
        if self.logger.isEnabledFor(logging.INFO):
            record = self._create_log_record(LogLevel.INFO, message, context, **kwargs)
            self.logger.info(record.to_json())

    def warning(self, message: str, context: LogContext | None = None, **kwargs):
        """Log warning message with structured context."""
        if self.logger.isEnabledFor(logging.WARNING):
            record = self._create_log_record(LogLevel.WARNING, message, context, **kwargs)
            self.logger.warning(record.to_json())

    def error(self, message: str, context: LogContext | None = None, error: Exception | None = None, **kwargs):
        """Log error message with structured context."""
        if self.logger.isEnabledFor(logging.ERROR):
            record = self._create_log_record(LogLevel.ERROR, message, context, error, **kwargs)
            self.logger.error(record.to_json())

    def critical(self, message: str, context: LogContext | None = None, error: Exception | None = None, **kwargs):
        """Log critical message with structured context."""
        if self.logger.isEnabledFor(logging.CRITICAL):
            record = self._create_log_record(LogLevel.CRITICAL, message, context, error, **kwargs)
            self.logger.critical(record.to_json())


class JsonFormatter(logging.Formatter):
    """Custom JSON formatter for structured logging."""

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON."""
        # If the message is already a JSON string from StructuredLogger, return as-is
        if hasattr(record, 'msg') and isinstance(record.msg, str):
            try:
                json.loads(record.msg)  # Validate it's valid JSON
                return record.msg
            except (json.JSONDecodeError, TypeError):
                pass

        # Otherwise, create a basic structured record
        log_record = StructuredLogRecord(
            timestamp=datetime.utcnow().isoformat() + "Z",
            level=record.levelname,
            message=str(record.getMessage()),
            logger=record.name,
            correlation_id=correlation_id.get(),
            request_id=request_id.get(),
            user_id=user_id.get()
        )

        # Add exception info if present
        if record.exc_info:
            log_record.stack_trace = self.formatException(record.exc_info)

        return log_record.to_json()


class PerformanceTimer:
    """Context manager for timing operations with structured logging."""

    def __init__(
        self,
        logger: StructuredLogger,
        operation: str,
        context: LogContext | None = None,
        log_start: bool = True,
        log_end: bool = True,
        threshold_ms: float | None = None
    ):
        self.logger = logger
        self.operation = operation
        self.context = context or LogContext()
        self.log_start = log_start
        self.log_end = log_end
        self.threshold_ms = threshold_ms
        self.start_time = None
        self.end_time = None

    def __enter__(self):
        self.start_time = time.time()
        self.context.operation = self.operation
        self.context.start_time = self.start_time

        if self.log_start:
            self.logger.info(f"Starting {self.operation}", self.context)

        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.end_time = time.time()
        duration_ms = (self.end_time - self.start_time) * 1000
        self.context.duration_ms = duration_ms

        if exc_type:
            self.logger.error(
                f"Operation {self.operation} failed",
                self.context,
                error=exc_val
            )
        elif self.log_end:
            # Only log if above threshold (if set)
            if self.threshold_ms is None or duration_ms >= self.threshold_ms:
                self.logger.info(
                    f"Completed {self.operation}",
                    self.context,
                    duration_ms=duration_ms
                )


class CorrelationManager:
    """Manager for correlation ID tracking across requests."""

    @staticmethod
    def generate_correlation_id() -> str:
        """Generate a new correlation ID."""
        return str(uuid.uuid4())

    @staticmethod
    def set_correlation_id(corr_id: str) -> None:
        """Set correlation ID in context."""
        correlation_id.set(corr_id)

    @staticmethod
    def get_correlation_id() -> str | None:
        """Get current correlation ID."""
        return correlation_id.get()

    @staticmethod
    def set_request_id(req_id: str) -> None:
        """Set request ID in context."""
        request_id.set(req_id)

    @staticmethod
    def get_request_id() -> str | None:
        """Get current request ID."""
        return request_id.get()

    @staticmethod
    def set_user_id(usr_id: str) -> None:
        """Set user ID in context."""
        user_id.set(usr_id)

    @staticmethod
    def get_user_id() -> str | None:
        """Get current user ID."""
        return user_id.get()

    @classmethod
    def start_request(cls, req_id: str | None = None, corr_id: str | None = None) -> str:
        """Start a new request context."""
        if not req_id:
            req_id = str(uuid.uuid4())
        if not corr_id:
            corr_id = cls.generate_correlation_id()

        cls.set_request_id(req_id)
        cls.set_correlation_id(corr_id)

        return corr_id


def get_structured_logger(name: str, component: ComponentType | None = None) -> StructuredLogger:
    """Factory function to get a structured logger instance."""
    return StructuredLogger(name, component)


def configure_logging(
    level: str = "INFO",
    format_type: str = "json",
    enable_correlation: bool = True
) -> None:
    """Configure global logging settings for the application."""

    # Set global log level
    logging.basicConfig(level=getattr(logging, level.upper()))

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.handlers.clear()

    # Add console handler with appropriate formatter
    handler = logging.StreamHandler()

    if format_type == "json":
        handler.setFormatter(JsonFormatter())
    else:
        handler.setFormatter(logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        ))

    root_logger.addHandler(handler)
    root_logger.setLevel(getattr(logging, level.upper()))


# Convenience function for common graph RAG components
def get_component_logger(component: ComponentType, module: str = None) -> StructuredLogger:
    """Get a structured logger for a specific GraphRAG component."""
    name = f"graph_rag.{component.value}"
    if module:
        name += f".{module}"
    return StructuredLogger(name, component)


# Pre-configured loggers for common components
api_logger = get_component_logger(ComponentType.API, "router")
engine_logger = get_component_logger(ComponentType.ENGINE, "core")
search_logger = get_component_logger(ComponentType.SEARCH, "service")
citation_logger = get_component_logger(ComponentType.CITATION, "service")
validation_logger = get_component_logger(ComponentType.VALIDATION, "service")
llm_logger = get_component_logger(ComponentType.LLM, "service")
