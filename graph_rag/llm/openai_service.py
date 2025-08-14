"""OpenAI LLM service implementation."""

import json
import logging
import os
import time
from collections.abc import AsyncGenerator
from typing import Any

from .protocols import LLMService
from .response_models import ConfidenceCalculator, ConfidenceMetrics, EnhancedLLMResponse

logger = logging.getLogger(__name__)


class OpenAIService(LLMService):
    """Production OpenAI LLM service implementation."""

    def __init__(
        self,
        api_key: str | None = None,
        model: str = "gpt-4o-mini",
        base_url: str | None = None,
        max_tokens: int = 2000,
        temperature: float = 0.3,
        timeout: float = 30.0
    ):
        """Initialize OpenAI service.
        
        Args:
            api_key: OpenAI API key (defaults to OPENAI_API_KEY env var)
            model: Model to use (gpt-4o-mini, gpt-4o, gpt-3.5-turbo, etc.)
            base_url: Custom base URL for API
            max_tokens: Maximum tokens in response
            temperature: Sampling temperature (0.0 to 2.0)
            timeout: Request timeout in seconds
        """
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OpenAI API key is required. Set OPENAI_API_KEY environment variable.")

        self.model = model
        self.base_url = base_url or "https://api.openai.com/v1"
        self.max_tokens = max_tokens
        self.temperature = temperature
        self.timeout = timeout

        # Track token usage
        self._token_usage = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}

        # Initialize client
        self._client = None
        self._async_client = None

        logger.info(f"OpenAI service initialized with model {model}")

    def _get_client(self):
        """Get synchronous OpenAI client."""
        if self._client is None:
            try:
                import openai
                self._client = openai.OpenAI(
                    api_key=self.api_key,
                    base_url=self.base_url,
                    timeout=self.timeout
                )
            except ImportError:
                raise ImportError(
                    "OpenAI package not installed. Install with: pip install openai"
                )
        return self._client

    def _get_async_client(self):
        """Get asynchronous OpenAI client."""
        if self._async_client is None:
            try:
                import openai
                self._async_client = openai.AsyncOpenAI(
                    api_key=self.api_key,
                    base_url=self.base_url,
                    timeout=self.timeout
                )
            except ImportError:
                raise ImportError(
                    "OpenAI package not installed. Install with: pip install openai"
                )
        return self._async_client

    def _format_messages(
        self,
        prompt: str,
        context: str | None = None,
        history: list[dict[str, str]] | None = None
    ) -> list[dict[str, str]]:
        """Format messages for OpenAI chat completion."""
        messages = []

        # Add system message with context if provided
        if context:
            system_content = f"You are a helpful assistant. Use the following context to answer questions accurately and concisely.\n\nContext:\n{context}"
            messages.append({"role": "system", "content": system_content})
        else:
            messages.append({"role": "system", "content": "You are a helpful assistant."})

        # Add conversation history
        if history:
            for msg in history:
                role = msg.get("role", "user")
                content = msg.get("content", "")
                if role in ["user", "assistant"] and content:
                    messages.append({"role": role, "content": content})

        # Add current prompt
        messages.append({"role": "user", "content": prompt})

        return messages

    async def generate_response(
        self,
        prompt: str,
        context: str | None = None,
        history: list[dict[str, str]] | None = None,
    ) -> str:
        """Generate a response using OpenAI's chat completion API."""
        try:
            client = self._get_async_client()
            messages = self._format_messages(prompt, context, history)

            logger.debug(f"Sending request to OpenAI model {self.model}")

            response = await client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_tokens=self.max_tokens,
                temperature=self.temperature,
                stream=False
            )

            # Update token usage
            if response.usage:
                self._token_usage["prompt_tokens"] += response.usage.prompt_tokens
                self._token_usage["completion_tokens"] += response.usage.completion_tokens
                self._token_usage["total_tokens"] += response.usage.total_tokens

            content = response.choices[0].message.content
            if not content:
                logger.warning("OpenAI returned empty response")
                return "I apologize, but I couldn't generate a response. Please try again."

            logger.debug(f"OpenAI response generated successfully ({len(content)} chars)")
            return content.strip()

        except Exception as e:
            logger.error(f"Error generating OpenAI response: {e}")
            return f"Error generating response: {str(e)}"

    async def generate_response_stream(
        self,
        prompt: str,
        context: str | None = None,
        history: list[dict[str, str]] | None = None,
    ) -> AsyncGenerator[str, None]:
        """Generate a streaming response using OpenAI's chat completion API."""
        try:
            client = self._get_async_client()
            messages = self._format_messages(prompt, context, history)

            logger.debug(f"Starting streaming request to OpenAI model {self.model}")

            response = await client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_tokens=self.max_tokens,
                temperature=self.temperature,
                stream=True
            )

            async for chunk in response:
                if chunk.choices and chunk.choices[0].delta.content:
                    content = chunk.choices[0].delta.content
                    yield content

            logger.debug("OpenAI streaming response completed")

        except Exception as e:
            logger.error(f"Error streaming OpenAI response: {e}")
            yield f"\n[Error: {str(e)}]"

    async def extract_entities_relationships(
        self, text: str
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        """Extract entities and relationships from text using OpenAI."""
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

JSON Response:"""

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
                    logger.warning("No JSON found in OpenAI extraction response")
                    return [], []

            except json.JSONDecodeError as e:
                logger.warning(f"Failed to parse JSON from OpenAI extraction: {e}")
                return [], []

        except Exception as e:
            logger.error(f"Error extracting entities/relationships with OpenAI: {e}")
            return [], []

    async def embed_text(self, text: str) -> list[float]:
        """Generate text embeddings using OpenAI's embedding API."""
        try:
            client = self._get_async_client()

            # Use text-embedding-3-small for cost efficiency
            response = await client.embeddings.create(
                model="text-embedding-3-small",
                input=text,
                encoding_format="float"
            )

            if response.data:
                embedding = response.data[0].embedding
                logger.debug(f"Generated OpenAI embedding with {len(embedding)} dimensions")
                return embedding
            else:
                logger.warning("OpenAI returned empty embedding response")
                return []

        except Exception as e:
            logger.error(f"Error generating OpenAI embedding: {e}")
            # Return zero vector as fallback
            return [0.0] * 1536  # text-embedding-3-small dimension

    async def get_token_usage(self) -> dict[str, int]:
        """Get current token usage statistics."""
        return self._token_usage.copy()

    def reset_token_usage(self):
        """Reset token usage counters."""
        self._token_usage = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}

    async def generate_enhanced_response(
        self,
        prompt: str,
        context: str | None = None,
        history: list[dict[str, str]] | None = None,
        context_chunks: list[Any] | None = None,
        query: str | None = None,
        context_texts: list[str] | None = None,
    ) -> EnhancedLLMResponse:
        """Generate an enhanced response with confidence scoring."""
        start_time = time.time()

        try:
            # Generate the standard response
            response_text = await self.generate_response(prompt, context, history)
            processing_time = time.time() - start_time

            # Calculate confidence metrics
            confidence = ConfidenceCalculator.calculate_confidence(
                answer_text=response_text,
                context_chunks=context_chunks or [],
                query=query or "",
                context_texts=context_texts
            )

            # Get token usage for this response
            current_usage = await self.get_token_usage()

            # Assess hallucination risk and verification needs
            has_hallucination_risk = confidence.overall_score < 0.5
            requires_verification = (
                confidence.level.value in ["low", "very_low"] or
                len(confidence.uncertainty_indicators) > 2
            )

            return EnhancedLLMResponse(
                text=response_text,
                confidence=confidence,
                input_tokens=current_usage.get("prompt_tokens"),
                output_tokens=current_usage.get("completion_tokens"),
                processing_time=processing_time,
                model_name=self.model,
                temperature=self.temperature,
                has_hallucination_risk=has_hallucination_risk,
                requires_verification=requires_verification
            )

        except Exception as e:
            logger.error(f"Error generating enhanced OpenAI response: {e}")
            # Return a low-confidence fallback response
            fallback_confidence = ConfidenceMetrics(
                overall_score=0.1,
                level=ConfidenceCalculator._score_to_level(0.1),
                context_coverage=0.0,
                context_relevance=0.0,
                uncertainty_indicators=["error_occurred"],
                reasoning="Error occurred during response generation"
            )

            return EnhancedLLMResponse(
                text=f"Error generating response: {e}",
                confidence=fallback_confidence,
                processing_time=time.time() - start_time,
                model_name=self.model,
                temperature=self.temperature,
                has_hallucination_risk=True,
                requires_verification=True
            )
