import asyncio
import logging
from collections.abc import AsyncGenerator
from typing import Any

from .protocols import LLMService  # Import the protocol

logger = logging.getLogger(__name__)


class MockLLMService(LLMService):
    """A mock implementation of the LLMService for testing and development."""

    async def generate_response(
        self,
        prompt: str,
        context: str | None = None,
        history: list[dict[str, str]] | None = None,
    ) -> str:
        logger.info(
            f"MockLLMService: Generating response for prompt: {prompt[:50]}..."
            f"Context: {context[:50] if context else 'None'}"
        )
        # Simulate a simple response
        response = f"Mock response to: {prompt[:100]}"
        if context:
            response += f" | Based on context: {context[:50]}"
        if history:
            response += f" | History length: {len(history)}"
        return response

    async def generate_response_stream(
        self,
        prompt: str,
        context: str | None = None,
        history: list[dict[str, str]] | None = None,
    ) -> AsyncGenerator[str, None]:
        logger.info(
            f"MockLLMService: Generating stream for prompt: {prompt[:50]}..."
            f"Context: {context[:50] if context else 'None'}"
        )
        response = f"Mock stream response to: {prompt[:100]}"
        if context:
            response += f" | Based on context: {context[:50]}"
        if history:
            response += f" | History length: {len(history)}"

        # Simulate streaming
        words = response.split()
        for i, word in enumerate(words):
            yield word + (" " if i < len(words) - 1 else "")
            await asyncio.sleep(0.05)  # Simulate network delay

    async def extract_entities_relationships(
        self, text: str
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        logger.info(
            f"MockLLMService: Extracting entities/relationships from: {text[:50]}..."
        )
        # Simulate extraction based on simple keywords
        entities = []
        relationships = []
        if "Alice" in text:
            entities.append(
                {"id": "p1", "label": "Person", "properties": {"name": "Alice"}}
            )
        if "Bob" in text:
            entities.append(
                {"id": "p2", "label": "Person", "properties": {"name": "Bob"}}
            )
        if "works at" in text and "Alice" in text and "CompanyX" in text:
            entities.append(
                {"id": "c1", "label": "Company", "properties": {"name": "CompanyX"}}
            )
            relationships.append(
                {"source": "p1", "target": "c1", "type": "WORKS_AT", "properties": {}}
            )

        logger.debug(
            f"Mock extracted: {len(entities)} entities, {len(relationships)} relationships"
        )
        return entities, relationships

    async def embed_text(self, text: str) -> list[float]:
        logger.info(f"MockLLMService: Generating embedding for: {text[:50]}...")
        # Simulate a fixed-size embedding vector (e.g., 10 dimensions)
        # Use hash for pseudo-randomness based on text
        import hashlib

        hash_val = int(hashlib.sha256(text.encode("utf-8")).hexdigest(), 16)
        embedding = [(hash_val + i) % 100 / 100.0 for i in range(10)]
        return embedding

    async def get_token_usage(self) -> dict[str, int]:
        logger.info("MockLLMService: Getting token usage.")
        # Simulate some token usage
        return {"prompt_tokens": 100, "completion_tokens": 50, "total_tokens": 150}
