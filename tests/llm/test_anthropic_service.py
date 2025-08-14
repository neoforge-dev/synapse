"""Tests for Anthropic LLM service implementation."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import json
from graph_rag.llm.anthropic_service import AnthropicService


class TestAnthropicService:
    """Test suite for AnthropicService."""

    @pytest.fixture
    def mock_anthropic_client(self):
        """Mock Anthropic async client."""
        with patch('anthropic.AsyncAnthropic') as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value = mock_client
            yield mock_client

    @pytest.fixture
    def anthropic_service(self):
        """Create Anthropic service with test API key."""
        with patch.dict('os.environ', {'ANTHROPIC_API_KEY': 'test-api-key'}):
            return AnthropicService(api_key="test-key")

    def test_initialization_with_api_key(self):
        """Test service initialization with provided API key."""
        service = AnthropicService(api_key="test-key")
        assert service.api_key == "test-key"
        assert service.model == "claude-3-5-haiku-20241022"
        assert service.max_tokens == 2000
        assert service.temperature == 0.3

    def test_initialization_with_env_var(self):
        """Test service initialization with environment variable."""
        with patch.dict('os.environ', {'ANTHROPIC_API_KEY': 'env-key'}):
            service = AnthropicService()
            assert service.api_key == "env-key"

    def test_initialization_without_api_key_raises_error(self):
        """Test that initialization without API key raises ValueError."""
        with patch.dict('os.environ', {}, clear=True):
            with pytest.raises(ValueError, match="Anthropic API key is required"):
                AnthropicService()

    def test_custom_parameters(self):
        """Test service initialization with custom parameters."""
        service = AnthropicService(
            api_key="test-key",
            model="claude-3-5-sonnet-20241022",
            max_tokens=1000,
            temperature=0.7,
            timeout=60.0
        )
        assert service.model == "claude-3-5-sonnet-20241022"
        assert service.max_tokens == 1000
        assert service.temperature == 0.7
        assert service.timeout == 60.0

    def test_format_messages_basic(self, anthropic_service):
        """Test basic message formatting."""
        system_msg, messages = anthropic_service._format_messages("Hello world")
        
        assert system_msg == "You are a helpful assistant."
        assert len(messages) == 1
        assert messages[0]["role"] == "user"
        assert messages[0]["content"] == "Hello world"

    def test_format_messages_with_context(self, anthropic_service):
        """Test message formatting with context."""
        system_msg, messages = anthropic_service._format_messages(
            "What is AI?", 
            context="AI is artificial intelligence"
        )
        
        assert "AI is artificial intelligence" in system_msg
        assert len(messages) == 1
        assert messages[0]["role"] == "user"
        assert messages[0]["content"] == "What is AI?"

    def test_format_messages_with_history(self, anthropic_service):
        """Test message formatting with conversation history."""
        history = [
            {"role": "user", "content": "Hi"},
            {"role": "assistant", "content": "Hello!"},
            {"role": "user", "content": "How are you?"}
        ]
        
        system_msg, messages = anthropic_service._format_messages("Fine, thanks", history=history)
        
        assert len(messages) == 4  # 3 history + 1 current
        assert messages[0]["role"] == "user"
        assert messages[0]["content"] == "Hi"
        assert messages[1]["role"] == "assistant"
        assert messages[1]["content"] == "Hello!"
        assert messages[2]["role"] == "user"
        assert messages[2]["content"] == "How are you?"
        assert messages[3]["role"] == "user"
        assert messages[3]["content"] == "Fine, thanks"

    def test_format_messages_filters_invalid_roles(self, anthropic_service):
        """Test that invalid roles are filtered out from history."""
        history = [
            {"role": "system", "content": "System message"},  # Should be filtered
            {"role": "user", "content": "Valid user message"},
            {"role": "invalid", "content": "Invalid role"},  # Should be filtered
            {"role": "assistant", "content": "Valid assistant message"}
        ]
        
        system_msg, messages = anthropic_service._format_messages("Test", history=history)
        
        # Should only include user and assistant messages
        assert len(messages) == 3  # 2 valid history + 1 current
        assert messages[0]["role"] == "user"
        assert messages[0]["content"] == "Valid user message"
        assert messages[1]["role"] == "assistant"
        assert messages[1]["content"] == "Valid assistant message"

    @pytest.mark.asyncio
    async def test_generate_response_success(self, anthropic_service, mock_anthropic_client):
        """Test successful response generation."""
        # Mock response
        mock_response = MagicMock()
        mock_content_block = MagicMock()
        mock_content_block.text = "This is a test response"
        mock_response.content = [mock_content_block]
        mock_response.usage = MagicMock()
        mock_response.usage.input_tokens = 10
        mock_response.usage.output_tokens = 5
        
        mock_anthropic_client.messages.create.return_value = mock_response
        
        # Test
        result = await anthropic_service.generate_response("Test prompt")
        
        assert result == "This is a test response"
        mock_anthropic_client.messages.create.assert_called_once()
        
        # Check token usage was updated
        usage = await anthropic_service.get_token_usage()
        assert usage["prompt_tokens"] == 10
        assert usage["completion_tokens"] == 5
        assert usage["total_tokens"] == 15

    @pytest.mark.asyncio
    async def test_generate_response_multiple_content_blocks(self, anthropic_service, mock_anthropic_client):
        """Test response with multiple content blocks."""
        mock_response = MagicMock()
        mock_block1 = MagicMock()
        mock_block1.text = "First part "
        mock_block2 = MagicMock()
        mock_block2.text = "second part"
        mock_response.content = [mock_block1, mock_block2]
        mock_response.usage = None
        
        mock_anthropic_client.messages.create.return_value = mock_response
        
        result = await anthropic_service.generate_response("Test prompt")
        
        assert result == "First part second part"

    @pytest.mark.asyncio
    async def test_generate_response_empty_content(self, anthropic_service, mock_anthropic_client):
        """Test handling of empty response content."""
        mock_response = MagicMock()
        mock_response.content = []
        mock_response.usage = None
        
        mock_anthropic_client.messages.create.return_value = mock_response
        
        result = await anthropic_service.generate_response("Test prompt")
        
        assert "I apologize, but I couldn't generate a response" in result

    @pytest.mark.asyncio
    async def test_generate_response_api_error(self, anthropic_service, mock_anthropic_client):
        """Test handling of API errors."""
        mock_anthropic_client.messages.create.side_effect = Exception("API Error")
        
        result = await anthropic_service.generate_response("Test prompt")
        
        assert "Error generating response: API Error" in result

    @pytest.mark.asyncio
    async def test_generate_response_stream(self, anthropic_service, mock_anthropic_client):
        """Test streaming response generation."""
        # Mock streaming response
        mock_chunk1 = MagicMock()
        mock_chunk1.type = "content_block_delta"
        mock_chunk1.delta = MagicMock()
        mock_chunk1.delta.text = "Hello "
        
        mock_chunk2 = MagicMock()
        mock_chunk2.type = "content_block_delta"
        mock_chunk2.delta = MagicMock()
        mock_chunk2.delta.text = "world!"
        
        mock_chunk3 = MagicMock()
        mock_chunk3.type = "other_type"  # Should be ignored
        
        mock_chunks = [mock_chunk1, mock_chunk2, mock_chunk3]
        
        async def mock_stream():
            for chunk in mock_chunks:
                yield chunk
        
        # Mock the streaming context manager
        mock_stream_manager = AsyncMock()
        mock_stream_manager.__aenter__.return_value = mock_stream()
        mock_stream_manager.__aexit__.return_value = None
        mock_anthropic_client.messages.stream.return_value = mock_stream_manager
        
        # Test streaming
        result_parts = []
        async for part in anthropic_service.generate_response_stream("Test prompt"):
            result_parts.append(part)
        
        assert result_parts == ["Hello ", "world!"]

    @pytest.mark.asyncio
    async def test_generate_response_stream_error(self, anthropic_service, mock_anthropic_client):
        """Test streaming response with error."""
        mock_anthropic_client.messages.stream.side_effect = Exception("Stream Error")
        
        result_parts = []
        async for part in anthropic_service.generate_response_stream("Test prompt"):
            result_parts.append(part)
        
        assert len(result_parts) == 1
        assert "Error: Stream Error" in result_parts[0]

    @pytest.mark.asyncio
    async def test_extract_entities_relationships(self, anthropic_service, mock_anthropic_client):
        """Test entity and relationship extraction."""
        # Mock response with JSON
        mock_response = MagicMock()
        mock_content_block = MagicMock()
        json_response = {
            "entities": [
                {"id": "e1", "label": "Person", "name": "John", "properties": {}},
                {"id": "e2", "label": "Company", "name": "Acme", "properties": {}}
            ],
            "relationships": [
                {"source": "e1", "target": "e2", "type": "WORKS_AT", "properties": {}}
            ]
        }
        mock_content_block.text = json.dumps(json_response)
        mock_response.content = [mock_content_block]
        mock_response.usage = None
        
        mock_anthropic_client.messages.create.return_value = mock_response
        
        # Test
        entities, relationships = await anthropic_service.extract_entities_relationships("John works at Acme")
        
        assert len(entities) == 2
        assert entities[0]["name"] == "John"
        assert entities[1]["name"] == "Acme"
        
        assert len(relationships) == 1
        assert relationships[0]["type"] == "WORKS_AT"

    @pytest.mark.asyncio
    async def test_extract_entities_relationships_invalid_json(self, anthropic_service, mock_anthropic_client):
        """Test entity extraction with invalid JSON response."""
        mock_response = MagicMock()
        mock_content_block = MagicMock()
        mock_content_block.text = "Invalid JSON response"
        mock_response.content = [mock_content_block]
        mock_response.usage = None
        
        mock_anthropic_client.messages.create.return_value = mock_response
        
        entities, relationships = await anthropic_service.extract_entities_relationships("Test text")
        
        assert entities == []
        assert relationships == []

    @pytest.mark.asyncio
    async def test_embed_text_fallback(self, anthropic_service):
        """Test text embedding fallback (Anthropic doesn't provide embeddings)."""
        result = await anthropic_service.embed_text("Test text")
        
        # Should return hash-based fallback
        assert len(result) == 768
        assert all(isinstance(x, float) for x in result)
        assert all(0.0 <= x <= 1.0 for x in result)

    @pytest.mark.asyncio
    async def test_embed_text_consistency(self, anthropic_service):
        """Test that same text produces same embedding."""
        result1 = await anthropic_service.embed_text("Same text")
        result2 = await anthropic_service.embed_text("Same text")
        
        assert result1 == result2

    @pytest.mark.asyncio
    async def test_embed_text_different_for_different_text(self, anthropic_service):
        """Test that different text produces different embeddings."""
        result1 = await anthropic_service.embed_text("Text one")
        result2 = await anthropic_service.embed_text("Text two")
        
        assert result1 != result2

    @pytest.mark.asyncio
    async def test_get_token_usage(self, anthropic_service):
        """Test token usage retrieval."""
        # Initially zero
        usage = await anthropic_service.get_token_usage()
        assert usage == {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
        
        # Modify internal counters
        anthropic_service._token_usage["prompt_tokens"] = 100
        anthropic_service._token_usage["completion_tokens"] = 50
        anthropic_service._token_usage["total_tokens"] = 150
        
        usage = await anthropic_service.get_token_usage()
        assert usage["prompt_tokens"] == 100
        assert usage["completion_tokens"] == 50
        assert usage["total_tokens"] == 150

    def test_reset_token_usage(self, anthropic_service):
        """Test token usage reset."""
        # Set some usage
        anthropic_service._token_usage["prompt_tokens"] = 100
        anthropic_service._token_usage["completion_tokens"] = 50
        anthropic_service._token_usage["total_tokens"] = 150
        
        # Reset
        anthropic_service.reset_token_usage()
        
        # Should be zero
        assert anthropic_service._token_usage["prompt_tokens"] == 0
        assert anthropic_service._token_usage["completion_tokens"] == 0
        assert anthropic_service._token_usage["total_tokens"] == 0

    def test_import_error_handling(self):
        """Test handling of missing Anthropic package."""
        with patch('anthropic.AsyncAnthropic', side_effect=ImportError("No module named 'anthropic'")):
            service = AnthropicService(api_key="test-key")
            
            with pytest.raises(ImportError, match="Anthropic package not installed"):
                service._get_client()

    @pytest.mark.asyncio
    async def test_client_initialization_lazy(self, anthropic_service):
        """Test that client is initialized lazily."""
        # Client should be None initially
        assert anthropic_service._client is None
        
        # After calling _get_client, it should be set
        with patch('anthropic.AsyncAnthropic') as mock_client_class:
            mock_client = MagicMock()
            mock_client_class.return_value = mock_client
            
            client = anthropic_service._get_client()
            assert client == mock_client
            assert anthropic_service._client == mock_client
            
            # Second call should return cached client
            client2 = anthropic_service._get_client()
            assert client2 == mock_client
            mock_client_class.assert_called_once()  # Should only be called once