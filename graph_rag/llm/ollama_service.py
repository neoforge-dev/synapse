"""Ollama local LLM service implementation."""

import json
import logging
from collections.abc import AsyncGenerator
from typing import Any

import aiohttp

from .protocols import LLMService

logger = logging.getLogger(__name__)


class OllamaService(LLMService):
    """Production Ollama local LLM service implementation."""

    def __init__(
        self,
        base_url: str = "http://localhost:11434",
        model: str = "llama3.2:3b",
        timeout: float = 120.0,
        temperature: float = 0.3,
        max_tokens: int | None = None
    ):
        """Initialize Ollama service.

        Args:
            base_url: Ollama server URL
            model: Model to use (must be pulled in Ollama)
            timeout: Request timeout in seconds
            temperature: Sampling temperature (0.0 to 1.0)
            max_tokens: Maximum tokens in response (None for unlimited)
        """
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout = timeout
        self.temperature = temperature
        self.max_tokens = max_tokens

        # Track token usage (estimated)
        self._token_usage = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}

        logger.info(f"Ollama service initialized with model {model} at {base_url}")

    def _estimate_tokens(self, text: str) -> int:
        """Rough token estimation (1 token ≈ 4 characters)."""
        return len(text) // 4

    def _format_prompt(
        self,
        prompt: str,
        context: str | None = None,
        history: list[dict[str, str]] | None = None
    ) -> str:
        """Format prompt for Ollama (simple string format)."""
        full_prompt = ""

        # Add context if provided
        if context:
            full_prompt += f"Context:\n{context}\n\n"

        # Add conversation history
        if history:
            full_prompt += "Conversation History:\n"
            for msg in history:
                role = msg.get("role", "user")
                content = msg.get("content", "")
                if content:
                    full_prompt += f"{role.title()}: {content}\n"
            full_prompt += "\n"

        # Add current prompt
        full_prompt += f"Human: {prompt}\n\nAssistant:"

        return full_prompt

    async def generate_response(
        self,
        prompt: str,
        context: str | None = None,
        history: list[dict[str, str]] | None = None,
    ) -> str:
        """Generate a response using Ollama's generate API."""
        try:
            formatted_prompt = self._format_prompt(prompt, context, history)

            payload = {
                "model": self.model,
                "prompt": formatted_prompt,
                "stream": False,
                "options": {
                    "temperature": self.temperature,
                }
            }

            if self.max_tokens:
                payload["options"]["num_predict"] = self.max_tokens

            logger.debug(f"Sending request to Ollama model {self.model}")

            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=self.timeout)) as session:
                async with session.post(
                    f"{self.base_url}/api/generate",
                    json=payload,
                    headers={"Content-Type": "application/json"}
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        raise Exception(f"Ollama API error {response.status}: {error_text}")

                    result = await response.json()

                    content = result.get("response", "")
                    if not content:
                        logger.warning("Ollama returned empty response")
                        return "I apologize, but I couldn't generate a response. Please try again."

                    # Update token usage estimates
                    prompt_tokens = self._estimate_tokens(formatted_prompt)
                    completion_tokens = self._estimate_tokens(content)

                    self._token_usage["prompt_tokens"] += prompt_tokens
                    self._token_usage["completion_tokens"] += completion_tokens
                    self._token_usage["total_tokens"] += prompt_tokens + completion_tokens

                    logger.debug(f"Ollama response generated successfully ({len(content)} chars)")
                    return content.strip()

        except Exception as e:
            logger.error(f"Error generating Ollama response: {e}")
            return f"Error generating response: {str(e)}"

    async def generate_response_stream(
        self,
        prompt: str,
        context: str | None = None,
        history: list[dict[str, str]] | None = None,
    ) -> AsyncGenerator[str, None]:
        """Generate a streaming response using Ollama's generate API."""
        try:
            formatted_prompt = self._format_prompt(prompt, context, history)

            payload = {
                "model": self.model,
                "prompt": formatted_prompt,
                "stream": True,
                "options": {
                    "temperature": self.temperature,
                }
            }

            if self.max_tokens:
                payload["options"]["num_predict"] = self.max_tokens

            logger.debug(f"Starting streaming request to Ollama model {self.model}")

            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=self.timeout)) as session:
                async with session.post(
                    f"{self.base_url}/api/generate",
                    json=payload,
                    headers={"Content-Type": "application/json"}
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        yield f"\n[Error: Ollama API error {response.status}: {error_text}]"
                        return

                    async for line in response.content:
                        if line:
                            try:
                                chunk_data = json.loads(line.decode('utf-8'))
                                if "response" in chunk_data:
                                    text_chunk = chunk_data["response"]
                                    if text_chunk:
                                        yield text_chunk

                                # Check if this is the final chunk
                                if chunk_data.get("done", False):
                                    break

                            except json.JSONDecodeError:
                                continue  # Skip malformed lines

            logger.debug("Ollama streaming response completed")

        except Exception as e:
            logger.error(f"Error streaming Ollama response: {e}")
            yield f"\n[Error: {str(e)}]"

    async def extract_entities_relationships(
        self, text: str
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        """Extract entities and relationships from text using Ollama."""
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
                    logger.warning("No JSON found in Ollama extraction response")
                    return [], []

            except json.JSONDecodeError as e:
                logger.warning(f"Failed to parse JSON from Ollama extraction: {e}")
                return [], []

        except Exception as e:
            logger.error(f"Error extracting entities/relationships with Ollama: {e}")
            return [], []

    async def embed_text(self, text: str) -> list[float]:
        """Generate text embeddings using Ollama's embeddings API."""
        try:
            payload = {
                "model": self.model,
                "prompt": text
            }

            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=self.timeout)) as session:
                async with session.post(
                    f"{self.base_url}/api/embeddings",
                    json=payload,
                    headers={"Content-Type": "application/json"}
                ) as response:
                    if response.status != 200:
                        # Fallback to hash-based embedding if embeddings not supported
                        logger.warning("Ollama embeddings not available, using hash fallback")
                        import hashlib
                        hash_val = int(hashlib.sha256(text.encode("utf-8")).hexdigest(), 16)
                        embedding = [(hash_val + i) % 1000 / 1000.0 for i in range(768)]
                        return embedding

                    result = await response.json()
                    embedding = result.get("embedding", [])

                    if embedding:
                        logger.debug(f"Generated Ollama embedding with {len(embedding)} dimensions")
                        return embedding
                    else:
                        logger.warning("Ollama returned empty embedding")
                        return []

        except Exception as e:
            logger.error(f"Error generating Ollama embedding: {e}")
            # Return hash-based fallback
            import hashlib
            hash_val = int(hashlib.sha256(text.encode("utf-8")).hexdigest(), 16)
            return [(hash_val + i) % 1000 / 1000.0 for i in range(768)]

    async def get_token_usage(self) -> dict[str, int]:
        """Get current token usage statistics (estimated)."""
        return self._token_usage.copy()

    def reset_token_usage(self):
        """Reset token usage counters."""
        self._token_usage = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}

    async def health_check(self) -> bool:
        """Check if Ollama server is accessible."""
        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=5.0)) as session:
                async with session.get(f"{self.base_url}/api/tags") as response:
                    return response.status == 200
        except Exception:
            return False

    async def list_models(self) -> list[str]:
        """List available models in Ollama."""
        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10.0)) as session:
                async with session.get(f"{self.base_url}/api/tags") as response:
                    if response.status == 200:
                        result = await response.json()
                        models = [model["name"] for model in result.get("models", [])]
                        return models
                    else:
                        return []
        except Exception as e:
            logger.error(f"Error listing Ollama models: {e}")
            return []
