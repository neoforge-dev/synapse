"""PostHog analytics service for Synapse Graph-RAG."""

import logging
from typing import Any

try:
    import posthog

    HAS_POSTHOG = True
except ImportError:
    HAS_POSTHOG = False

from graph_rag.config import get_settings

logger = logging.getLogger(__name__)


class PostHogAnalytics:
    """PostHog analytics client for Synapse Graph-RAG events."""

    _initialized = False

    @classmethod
    def initialize(cls) -> None:
        """Initialize PostHog client."""
        if cls._initialized:
            return

        if not HAS_POSTHOG:
            logger.warning("PostHog package not installed - analytics disabled")
            return

        settings = get_settings()
        api_key = getattr(settings, "posthog_api_key", None)
        host = getattr(settings, "posthog_host", "https://eu.posthog.com")

        if not api_key:
            logger.warning("PostHog API key not configured - analytics disabled")
            return

        posthog.project_api_key = api_key
        posthog.host = host
        posthog.debug = getattr(settings, "api_log_level", "INFO").upper() == "DEBUG"
        cls._initialized = True
        logger.info("PostHog analytics initialized")

    @classmethod
    def capture(
        cls,
        user_id: str,
        event: str,
        properties: dict[str, Any] | None = None,
    ) -> None:
        """Capture an analytics event."""
        if not cls._initialized:
            cls.initialize()

        if not cls._initialized or not HAS_POSTHOG:
            return

        try:
            posthog.capture(
                distinct_id=user_id,
                event=event,
                properties={
                    "product": "synapse-graph-rag",
                    **(properties or {}),
                },
            )
        except Exception as e:
            logger.error(f"PostHog capture failed: {e}")

    @classmethod
    def identify(
        cls,
        user_id: str,
        properties: dict[str, Any] | None = None,
    ) -> None:
        """Identify a user with properties."""
        if not cls._initialized:
            cls.initialize()

        if not cls._initialized or not HAS_POSTHOG:
            return

        try:
            posthog.identify(user_id, properties or {})
        except Exception as e:
            logger.error(f"PostHog identify failed: {e}")

    # Synapse-specific events
    @classmethod
    def document_ingested(
        cls,
        user_id: str,
        document_id: str,
        source_type: str,
        chunk_count: int,
    ) -> None:
        """Track document ingestion."""
        cls.capture(
            user_id=user_id,
            event="synapse_document_ingested",
            properties={
                "document_id": document_id,
                "source_type": source_type,
                "chunk_count": chunk_count,
            },
        )

    @classmethod
    def search_performed(
        cls,
        user_id: str,
        query_length: int,
        result_count: int,
        search_type: str = "hybrid",
    ) -> None:
        """Track search operation."""
        cls.capture(
            user_id=user_id,
            event="synapse_search_performed",
            properties={
                "query_length": query_length,
                "result_count": result_count,
                "search_type": search_type,
            },
        )

    @classmethod
    def query_answered(
        cls,
        user_id: str,
        query_length: int,
        context_chunks: int,
        response_length: int,
        llm_provider: str,
    ) -> None:
        """Track RAG query answered."""
        cls.capture(
            user_id=user_id,
            event="synapse_query_answered",
            properties={
                "query_length": query_length,
                "context_chunks": context_chunks,
                "response_length": response_length,
                "llm_provider": llm_provider,
            },
        )

    @classmethod
    def graph_operation(
        cls,
        user_id: str,
        operation: str,
        node_count: int = 0,
        edge_count: int = 0,
    ) -> None:
        """Track graph operations."""
        cls.capture(
            user_id=user_id,
            event="synapse_graph_operation",
            properties={
                "operation": operation,
                "node_count": node_count,
                "edge_count": edge_count,
            },
        )

    @classmethod
    def mcp_action(
        cls,
        user_id: str,
        action: str,
        ide: str = "unknown",
    ) -> None:
        """Track MCP IDE integration actions."""
        cls.capture(
            user_id=user_id,
            event="synapse_mcp_action",
            properties={
                "action": action,
                "ide": ide,
            },
        )

    @classmethod
    def subscription_started(
        cls,
        user_id: str,
        plan: str,
        price: float,
    ) -> None:
        """Track subscription start."""
        cls.capture(
            user_id=user_id,
            event="synapse_subscription_started",
            properties={
                "plan": plan,
                "price": price,
            },
        )

    @classmethod
    def api_key_created(
        cls,
        user_id: str,
        key_name: str,
    ) -> None:
        """Track API key creation."""
        cls.capture(
            user_id=user_id,
            event="synapse_api_key_created",
            properties={
                "key_name": key_name,
            },
        )
