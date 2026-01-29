"""
Sentry integration for production error tracking and monitoring.
"""

from __future__ import annotations

import logging
import os
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Callable

logger = logging.getLogger(__name__)


def init_sentry() -> None:
    """Initialize Sentry for error tracking in production."""
    sentry_dsn = os.getenv("SENTRY_DSN")
    environment = os.getenv("SYNAPSE_ENVIRONMENT", "development")
    release = os.getenv("SYNAPSE_VERSION", "unknown")

    if not sentry_dsn:
        logger.info("Sentry DSN not configured, skipping Sentry initialization")
        return

    try:
        import sentry_sdk
        from sentry_sdk.integrations.fastapi import FastApiIntegration
        from sentry_sdk.integrations.logging import LoggingIntegration
        from sentry_sdk.integrations.redis import RedisIntegration
        from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration

        # Configure logging integration
        sentry_logging = LoggingIntegration(
            level=logging.INFO,  # Capture info and above as breadcrumbs
            event_level=logging.ERROR,  # Send errors as events
        )

        sentry_sdk.init(
            dsn=sentry_dsn,
            environment=environment,
            release=release,
            integrations=[
                FastApiIntegration(
                    transaction_style="endpoint",
                ),
                sentry_logging,
                SqlalchemyIntegration(),
                RedisIntegration(),
            ],
            # Performance monitoring
            traces_sample_rate=float(os.getenv("SENTRY_TRACES_SAMPLE_RATE", "0.1")),
            # Profiling
            profiles_sample_rate=float(os.getenv("SENTRY_PROFILES_SAMPLE_RATE", "0.1")),
            # Filter out health check requests
            before_send=before_send_filter,
            # Additional configuration
            attach_stacktrace=True,
            send_default_pii=False,  # Don't send personally identifiable information
            max_breadcrumbs=50,
            debug=environment == "development",
        )

        logger.info(
            f"Sentry initialized for environment: {environment}, release: {release}"
        )
    except ImportError:
        logger.warning("sentry-sdk not installed, skipping Sentry initialization")
    except Exception as e:
        logger.error(f"Failed to initialize Sentry: {e}")


def before_send_filter(event: dict[str, Any], hint: dict[str, Any]) -> dict[str, Any] | None:
    """Filter Sentry events before sending."""
    # Don't send events for health check endpoints
    if "request" in event:
        url = event["request"].get("url", "")
        if "/health" in url or "/metrics" in url:
            return None

    # Don't send events for expected errors
    if "exception" in event:
        exception_values = event["exception"].get("values", [])
        for exc in exception_values:
            exc_type = exc.get("type", "")
            # Filter out HTTP 404s and other client errors
            if exc_type in ["HTTPException", "NotFound", "ValidationError"]:
                return None

    return event


def capture_exception(error: Exception, context: dict[str, Any] | None = None) -> None:
    """Capture an exception with additional context."""
    try:
        import sentry_sdk

        with sentry_sdk.push_scope() as scope:
            if context:
                for key, value in context.items():
                    scope.set_extra(key, value)
            sentry_sdk.capture_exception(error)
    except ImportError:
        logger.error(f"Exception occurred: {error}", exc_info=True)
    except Exception as e:
        logger.error(f"Failed to capture exception in Sentry: {e}", exc_info=True)


def capture_message(message: str, level: str = "info", context: dict[str, Any] | None = None) -> None:
    """Capture a message with additional context."""
    try:
        import sentry_sdk

        with sentry_sdk.push_scope() as scope:
            if context:
                for key, value in context.items():
                    scope.set_extra(key, value)
            sentry_sdk.capture_message(message, level=level)
    except ImportError:
        logger.log(getattr(logging, level.upper(), logging.INFO), message)
    except Exception as e:
        logger.error(f"Failed to capture message in Sentry: {e}", exc_info=True)


def set_user_context(user_id: str, email: str | None = None, username: str | None = None) -> None:
    """Set user context for Sentry events."""
    try:
        import sentry_sdk

        sentry_sdk.set_user({
            "id": user_id,
            "email": email,
            "username": username,
        })
    except ImportError:
        pass
    except Exception as e:
        logger.error(f"Failed to set user context in Sentry: {e}")


def set_tag(key: str, value: str) -> None:
    """Set a tag for Sentry events."""
    try:
        import sentry_sdk

        sentry_sdk.set_tag(key, value)
    except ImportError:
        pass
    except Exception as e:
        logger.error(f"Failed to set tag in Sentry: {e}")


def configure_sentry_context(
    user_id: str | None = None,
    tags: dict[str, str] | None = None,
    extras: dict[str, Any] | None = None,
) -> None:
    """Configure Sentry context with user, tags, and extras."""
    try:
        import sentry_sdk

        with sentry_sdk.configure_scope() as scope:
            if user_id:
                scope.set_user({"id": user_id})
            if tags:
                for key, value in tags.items():
                    scope.set_tag(key, value)
            if extras:
                for key, value in extras.items():
                    scope.set_extra(key, value)
    except ImportError:
        pass
    except Exception as e:
        logger.error(f"Failed to configure Sentry context: {e}")
