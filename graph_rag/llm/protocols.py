from collections.abc import AsyncGenerator
from typing import Any, Protocol

from .response_models import EnhancedLLMResponse


class LLMService(Protocol):
    """Protocol defining the interface for LLM services."""

    async def generate_response(
        self,
        prompt: str,
        context: str | None = None,
        history: list[dict[str, str]] | None = None,
    ) -> str:
        """Generate a response to the given prompt.

        Args:
            prompt: The input prompt to generate a response for.
            context: Optional context to consider when generating the response.
            history: Optional conversation history.

        Returns:
            The generated response as a string.
        """
        ...

    async def generate_response_stream(
        self,
        prompt: str,
        context: str | None = None,
        history: list[dict[str, str]] | None = None,
    ) -> AsyncGenerator[str, None]:
        """Generate a streaming response to the given prompt.

        Args:
            prompt: The input prompt to generate a response for.
            context: Optional context to consider when generating the response.
            history: Optional conversation history.

        Yields:
            Chunks of the generated response as strings.
        """
        ...

    async def extract_entities_relationships(
        self, text: str
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        """Extract entities and relationships from the given text.

        Args:
            text: The text to extract entities and relationships from.

        Returns:
            A tuple containing:
            - List of extracted entities, each represented as a dictionary
            - List of extracted relationships, each represented as a dictionary
        """
        ...

    async def embed_text(self, text: str) -> list[float]:
        """Generate an embedding vector for the given text.

        Args:
            text: The text to generate an embedding for.

        Returns:
            A list of floats representing the embedding vector.
        """
        ...

    async def get_token_usage(self) -> dict[str, int]:
        """Get the current token usage statistics.

        Returns:
            A dictionary containing token usage statistics.
        """
        ...

    async def generate_enhanced_response(
        self,
        prompt: str,
        context: str | None = None,
        history: list[dict[str, str]] | None = None,
        context_chunks: list[Any] | None = None,
        query: str | None = None,
        context_texts: list[str] | None = None,
    ) -> EnhancedLLMResponse:
        """Generate an enhanced response with confidence scoring.

        Args:
            prompt: The input prompt to generate a response for.
            context: Optional context to consider when generating the response.
            history: Optional conversation history.
            context_chunks: Optional chunks used for context (for confidence scoring).
            query: Optional original query (for confidence scoring).
            context_texts: Optional context texts (for confidence scoring).

        Returns:
            EnhancedLLMResponse with confidence metrics and metadata.
        """
        ...
