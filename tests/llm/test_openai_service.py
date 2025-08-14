"""Tests for OpenAI LLM service implementation."""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from graph_rag.llm.openai_service import OpenAIService


class TestOpenAIService:
    """Test suite for OpenAIService."""

    @pytest.fixture
    def mock_openai_client(self):
        """Mock OpenAI async client."""
        with patch('openai.AsyncOpenAI') as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value = mock_client
            yield mock_client

    @pytest.fixture
    def openai_service(self):
        """Create OpenAI service with test API key."""
        with patch.dict('os.environ', {'OPENAI_API_KEY': 'test-api-key'}):
            return OpenAIService(api_key="test-key")

    def test_initialization_with_api_key(self):
        """Test service initialization with provided API key."""
        service = OpenAIService(api_key="test-key")
        assert service.api_key == "test-key"
        assert service.model == "gpt-4o-mini"
        assert service.max_tokens == 2000
        assert service.temperature == 0.3

    def test_initialization_with_env_var(self):
        """Test service initialization with environment variable."""
        with patch.dict('os.environ', {'OPENAI_API_KEY': 'env-key'}):
            service = OpenAIService()
            assert service.api_key == "env-key"

    def test_initialization_without_api_key_raises_error(self):
        """Test that initialization without API key raises ValueError."""
        with patch.dict('os.environ', {}, clear=True):
            with pytest.raises(ValueError, match="OpenAI API key is required"):
                OpenAIService()

    def test_custom_parameters(self):
        """Test service initialization with custom parameters."""
        service = OpenAIService(
            api_key="test-key",
            model="gpt-4o",
            max_tokens=1000,
            temperature=0.7,
            timeout=60.0
        )
        assert service.model == "gpt-4o"
        assert service.max_tokens == 1000
        assert service.temperature == 0.7
        assert service.timeout == 60.0

    def test_format_messages_basic(self, openai_service):
        """Test basic message formatting."""
        messages = openai_service._format_messages("Hello world")

        assert len(messages) == 2
        assert messages[0]["role"] == "system"
        assert messages[0]["content"] == "You are a helpful assistant."
        assert messages[1]["role"] == "user"
        assert messages[1]["content"] == "Hello world"

    def test_format_messages_with_context(self, openai_service):
        """Test message formatting with context."""
        messages = openai_service._format_messages(
            "What is AI?",
            context="AI is artificial intelligence"
        )

        assert len(messages) == 2
        assert messages[0]["role"] == "system"
        assert "AI is artificial intelligence" in messages[0]["content"]
        assert messages[1]["role"] == "user"
        assert messages[1]["content"] == "What is AI?"

    def test_format_messages_with_history(self, openai_service):
        """Test message formatting with conversation history."""
        history = [
            {"role": "user", "content": "Hi"},
            {"role": "assistant", "content": "Hello!"},
            {"role": "user", "content": "How are you?"}
        ]

        messages = openai_service._format_messages("Fine, thanks", history=history)

        assert len(messages) == 5  # system + 3 history + 1 current
        assert messages[0]["role"] == "system"
        assert messages[1]["role"] == "user"
        assert messages[1]["content"] == "Hi"
        assert messages[2]["role"] == "assistant"
        assert messages[2]["content"] == "Hello!"
        assert messages[3]["role"] == "user"
        assert messages[3]["content"] == "How are you?"
        assert messages[4]["role"] == "user"
        assert messages[4]["content"] == "Fine, thanks"

    @pytest.mark.asyncio
    async def test_generate_response_success(self, openai_service, mock_openai_client):
        """Test successful response generation."""
        # Mock response
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "This is a test response"
        mock_response.usage = MagicMock()
        mock_response.usage.prompt_tokens = 10
        mock_response.usage.completion_tokens = 5
        mock_response.usage.total_tokens = 15

        mock_openai_client.chat.completions.create.return_value = mock_response

        # Test
        result = await openai_service.generate_response("Test prompt")

        assert result == "This is a test response"
        mock_openai_client.chat.completions.create.assert_called_once()

        # Check token usage was updated
        usage = await openai_service.get_token_usage()
        assert usage["prompt_tokens"] == 10
        assert usage["completion_tokens"] == 5
        assert usage["total_tokens"] == 15

    @pytest.mark.asyncio
    async def test_generate_response_empty_content(self, openai_service, mock_openai_client):
        """Test handling of empty response content."""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = None
        mock_response.usage = None

        mock_openai_client.chat.completions.create.return_value = mock_response

        result = await openai_service.generate_response("Test prompt")

        assert "I apologize, but I couldn't generate a response" in result

    @pytest.mark.asyncio
    async def test_generate_response_api_error(self, openai_service, mock_openai_client):
        """Test handling of API errors."""
        mock_openai_client.chat.completions.create.side_effect = Exception("API Error")

        result = await openai_service.generate_response("Test prompt")

        assert "Error generating response: API Error" in result

    @pytest.mark.asyncio
    async def test_generate_response_stream(self, openai_service, mock_openai_client):
        """Test streaming response generation."""
        # Mock streaming response
        mock_chunks = [
            MagicMock(choices=[MagicMock(delta=MagicMock(content="Hello "))]),
            MagicMock(choices=[MagicMock(delta=MagicMock(content="world!"))]),
            MagicMock(choices=[MagicMock(delta=MagicMock(content=None))]),  # End
        ]

        async def mock_stream():
            for chunk in mock_chunks:
                yield chunk

        mock_openai_client.chat.completions.create.return_value = mock_stream()

        # Test streaming
        result_parts = []
        async for part in openai_service.generate_response_stream("Test prompt"):
            result_parts.append(part)

        assert result_parts == ["Hello ", "world!"]

    @pytest.mark.asyncio
    async def test_generate_response_stream_error(self, openai_service, mock_openai_client):
        """Test streaming response with error."""
        mock_openai_client.chat.completions.create.side_effect = Exception("Stream Error")

        result_parts = []
        async for part in openai_service.generate_response_stream("Test prompt"):
            result_parts.append(part)

        assert len(result_parts) == 1
        assert "Error: Stream Error" in result_parts[0]

    @pytest.mark.asyncio
    async def test_extract_entities_relationships(self, openai_service, mock_openai_client):
        """Test entity and relationship extraction."""
        # Mock response with JSON
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        json_response = {
            "entities": [
                {"id": "e1", "label": "Person", "name": "John", "properties": {}},
                {"id": "e2", "label": "Company", "name": "Acme", "properties": {}}
            ],
            "relationships": [
                {"source": "e1", "target": "e2", "type": "WORKS_AT", "properties": {}}
            ]
        }
        mock_response.choices[0].message.content = json.dumps(json_response)
        mock_response.usage = None

        mock_openai_client.chat.completions.create.return_value = mock_response

        # Test
        entities, relationships = await openai_service.extract_entities_relationships("John works at Acme")

        assert len(entities) == 2
        assert entities[0]["name"] == "John"
        assert entities[1]["name"] == "Acme"

        assert len(relationships) == 1
        assert relationships[0]["type"] == "WORKS_AT"

    @pytest.mark.asyncio
    async def test_extract_entities_relationships_invalid_json(self, openai_service, mock_openai_client):
        """Test entity extraction with invalid JSON response."""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Invalid JSON response"
        mock_response.usage = None

        mock_openai_client.chat.completions.create.return_value = mock_response

        entities, relationships = await openai_service.extract_entities_relationships("Test text")

        assert entities == []
        assert relationships == []

    @pytest.mark.asyncio
    async def test_embed_text_success(self, openai_service, mock_openai_client):
        """Test successful text embedding."""
        mock_response = MagicMock()
        mock_response.data = [MagicMock()]
        mock_response.data[0].embedding = [0.1, 0.2, 0.3, 0.4]

        mock_openai_client.embeddings.create.return_value = mock_response

        result = await openai_service.embed_text("Test text")

        assert result == [0.1, 0.2, 0.3, 0.4]
        mock_openai_client.embeddings.create.assert_called_once_with(
            model="text-embedding-3-small",
            input="Test text",
            encoding_format="float"
        )

    @pytest.mark.asyncio
    async def test_embed_text_empty_response(self, openai_service, mock_openai_client):
        """Test embedding with empty response."""
        mock_response = MagicMock()
        mock_response.data = []

        mock_openai_client.embeddings.create.return_value = mock_response

        result = await openai_service.embed_text("Test text")

        assert result == []

    @pytest.mark.asyncio
    async def test_embed_text_api_error(self, openai_service, mock_openai_client):
        """Test embedding with API error."""
        mock_openai_client.embeddings.create.side_effect = Exception("API Error")

        result = await openai_service.embed_text("Test text")

        # Should return zero vector fallback
        assert len(result) == 1536
        assert all(isinstance(x, float) and x == 0.0 for x in result)

    @pytest.mark.asyncio
    async def test_get_token_usage(self, openai_service):
        """Test token usage retrieval."""
        # Initially zero
        usage = await openai_service.get_token_usage()
        assert usage == {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}

        # Modify internal counters
        openai_service._token_usage["prompt_tokens"] = 100
        openai_service._token_usage["completion_tokens"] = 50
        openai_service._token_usage["total_tokens"] = 150

        usage = await openai_service.get_token_usage()
        assert usage["prompt_tokens"] == 100
        assert usage["completion_tokens"] == 50
        assert usage["total_tokens"] == 150

    def test_reset_token_usage(self, openai_service):
        """Test token usage reset."""
        # Set some usage
        openai_service._token_usage["prompt_tokens"] = 100
        openai_service._token_usage["completion_tokens"] = 50
        openai_service._token_usage["total_tokens"] = 150

        # Reset
        openai_service.reset_token_usage()

        # Should be zero
        assert openai_service._token_usage["prompt_tokens"] == 0
        assert openai_service._token_usage["completion_tokens"] == 0
        assert openai_service._token_usage["total_tokens"] == 0

    def test_import_error_handling(self):
        """Test handling of missing OpenAI package."""
        with patch('openai.AsyncOpenAI', side_effect=ImportError("No module named 'openai'")):
            service = OpenAIService(api_key="test-key")

            with pytest.raises(ImportError, match="OpenAI package not installed"):
                service._get_async_client()
