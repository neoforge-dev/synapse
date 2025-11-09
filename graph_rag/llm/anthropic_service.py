"""Anthropic Claude LLM service implementation."""

import json
import logging
import os
from collections.abc import AsyncGenerator
from typing import Any

from .protocols import LLMService

logger = logging.getLogger(__name__)


class AnthropicService(LLMService):
    """Production Anthropic Claude LLM service implementation."""

    def __init__(
        self,
        api_key: str | None = None,
        model: str = "claude-3-5-haiku-20241022",
        max_tokens: int = 2000,
        temperature: float = 0.3,
        timeout: float = 60.0
    ):
        """Initialize Anthropic service.

        Args:
            api_key: Anthropic API key (defaults to ANTHROPIC_API_KEY env var)
            model: Model to use (claude-3-5-sonnet-20241022, claude-3-5-haiku-20241022, etc.)
            max_tokens: Maximum tokens in response
            temperature: Sampling temperature (0.0 to 1.0)
            timeout: Request timeout in seconds
        """
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise ValueError("Anthropic API key is required. Set ANTHROPIC_API_KEY environment variable.")

        self.model = model
        self.max_tokens = max_tokens
        self.temperature = temperature
        self.timeout = timeout

        # Track token usage
        self._token_usage = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}

        # Initialize client
        self._client = None

        logger.info(f"Anthropic service initialized with model {model}")

    def _get_client(self):
        """Get Anthropic client."""
        if self._client is None:
            try:
                import anthropic
                self._client = anthropic.AsyncAnthropic(
                    api_key=self.api_key,
                    timeout=self.timeout
                )
            except ImportError as e:
                raise ImportError(
                    "Anthropic package not installed. Install with: uv pip install anthropic"
                ) from e
        return self._client

    def _format_messages(
        self,
        prompt: str,
        context: str | None = None,
        history: list[dict[str, str]] | None = None
    ) -> tuple[str, list[dict[str, str]]]:
        """Format messages for Anthropic Claude."""
        # Anthropic uses system message separately
        system_message = "You are a helpful assistant."
        if context:
            system_message = f"You are a helpful assistant. Use the following context to answer questions accurately and concisely.\n\nContext:\n{context}"

        messages = []

        # Add conversation history
        if history:
            for msg in history:
                role = msg.get("role", "user")
                content = msg.get("content", "")
                if role in ["user", "assistant"] and content:
                    messages.append({"role": role, "content": content})

        # Add current prompt
        messages.append({"role": "user", "content": prompt})

        return system_message, messages

    async def generate_response(
        self,
        prompt: str,
        context: str | None = None,
        history: list[dict[str, str]] | None = None,
    ) -> str:
        """Generate a response using Anthropic's messages API."""
        try:
            client = self._get_client()
            system_message, messages = self._format_messages(prompt, context, history)

            logger.debug(f"Sending request to Anthropic model {self.model}")

            response = await client.messages.create(
                model=self.model,
                max_tokens=self.max_tokens,
                temperature=self.temperature,
                system=system_message,
                messages=messages
            )

            # Update token usage
            if response.usage:
                self._token_usage["prompt_tokens"] += response.usage.input_tokens
                self._token_usage["completion_tokens"] += response.usage.output_tokens
                self._token_usage["total_tokens"] += response.usage.input_tokens + response.usage.output_tokens

            # Extract content from response
            content = ""
            for block in response.content:
                if hasattr(block, 'text'):
                    content += block.text

            if not content:
                logger.warning("Anthropic returned empty response")
                return "I apologize, but I couldn't generate a response. Please try again."

            logger.debug(f"Anthropic response generated successfully ({len(content)} chars)")
            return content.strip()

        except Exception as e:
            logger.error(f"Error generating Anthropic response: {e}")
            return f"Error generating response: {str(e)}"

    async def generate_response_stream(
        self,
        prompt: str,
        context: str | None = None,
        history: list[dict[str, str]] | None = None,
    ) -> AsyncGenerator[str, None]:
        """Generate a streaming response using Anthropic's messages API."""
        try:
            client = self._get_client()
            system_message, messages = self._format_messages(prompt, context, history)

            logger.debug(f"Starting streaming request to Anthropic model {self.model}")

            async with client.messages.stream(
                model=self.model,
                max_tokens=self.max_tokens,
                temperature=self.temperature,
                system=system_message,
                messages=messages
            ) as stream:
                async for chunk in stream:
                    if chunk.type == "content_block_delta" and hasattr(chunk.delta, 'text'):
                        yield chunk.delta.text

            logger.debug("Anthropic streaming response completed")

        except Exception as e:
            logger.error(f"Error streaming Anthropic response: {e}")
            yield f"\n[Error: {str(e)}]"

    async def extract_entities_relationships(
        self, text: str
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        """Extract entities and relationships from text using Anthropic Claude."""
        try:
            prompt = f"""Extract entities and relationships from the following text.
Return your response as valid JSON with two arrays: "entities" and "relationships".

For entities, include: id (unique), label (type), name, and properties (dict).
For relationships, include: source (entity id), target (entity id), type, and properties (dict).

Text: {text}

Response format:
{{
  "entities": [
    {{"id": "ent1", "label": "Person", "name": "John Doe", "properties": {{}}}},
    ...
  ],
  "relationships": [
    {{"source": "ent1", "target": "ent2", "type": "WORKS_AT", "properties": {{}}}},
    ...
  ]
}}

Respond with only the JSON, no additional text:"""

            response = await self.generate_response(prompt)

            # Try to parse JSON response
            try:
                # Find JSON in response (handle cases where model adds explanation)
                start_idx = response.find('{')
                end_idx = response.rfind('}') + 1
                if start_idx >= 0 and end_idx > start_idx:
                    json_str = response[start_idx:end_idx]
                    data = json.loads(json_str)

                    entities = data.get("entities", [])
                    relationships = data.get("relationships", [])

                    logger.debug(f"Extracted {len(entities)} entities and {len(relationships)} relationships")
                    return entities, relationships
                else:
                    logger.warning("No JSON found in Anthropic extraction response")
                    return [], []

            except json.JSONDecodeError as e:
                logger.warning(f"Failed to parse JSON from Anthropic extraction: {e}")
                return [], []

        except Exception as e:
            logger.error(f"Error extracting entities/relationships with Anthropic: {e}")
            return [], []

    async def embed_text(self, text: str) -> list[float]:
        """Generate text embeddings (Anthropic doesn't provide embeddings API, use fallback)."""
        logger.warning("Anthropic doesn't provide embeddings API, using text hash fallback")

        # Simple hash-based embedding for compatibility
        import hashlib
        hash_val = int(hashlib.sha256(text.encode("utf-8")).hexdigest(), 16)

        # Generate 768-dimensional embedding (common size)
        embedding = [(hash_val + i) % 1000 / 1000.0 for i in range(768)]

        logger.debug(f"Generated fallback embedding with {len(embedding)} dimensions")
        return embedding

    async def get_token_usage(self) -> dict[str, int]:
        """Get current token usage statistics."""
        return self._token_usage.copy()

    def reset_token_usage(self):
        """Reset token usage counters."""
        self._token_usage = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
