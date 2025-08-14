"""Tests for Ollama LLM service implementation."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import json
import aiohttp
from graph_rag.llm.ollama_service import OllamaService


class TestOllamaService:
    """Test suite for OllamaService."""

    @pytest.fixture
    def ollama_service(self):
        """Create Ollama service with default settings."""
        return OllamaService()

    @pytest.fixture
    def custom_ollama_service(self):
        """Create Ollama service with custom settings."""
        return OllamaService(
            base_url="http://custom:11434",
            model="llama3.2:7b",
            timeout=60.0,
            temperature=0.5,
            max_tokens=1000
        )

    def test_initialization_defaults(self, ollama_service):
        """Test service initialization with default parameters."""
        assert ollama_service.base_url == "http://localhost:11434"
        assert ollama_service.model == "llama3.2:3b"
        assert ollama_service.timeout == 120.0
        assert ollama_service.temperature == 0.3
        assert ollama_service.max_tokens is None

    def test_initialization_custom_parameters(self, custom_ollama_service):
        """Test service initialization with custom parameters."""
        assert custom_ollama_service.base_url == "http://custom:11434"
        assert custom_ollama_service.model == "llama3.2:7b"
        assert custom_ollama_service.timeout == 60.0
        assert custom_ollama_service.temperature == 0.5
        assert custom_ollama_service.max_tokens == 1000

    def test_base_url_trailing_slash_removed(self):
        """Test that trailing slash is removed from base_url."""
        service = OllamaService(base_url="http://localhost:11434/")
        assert service.base_url == "http://localhost:11434"

    def test_estimate_tokens(self, ollama_service):
        """Test token estimation."""
        # Rough estimation: 1 token ≈ 4 characters
        text = "Hello world!"  # 12 characters
        estimated = ollama_service._estimate_tokens(text)
        assert estimated == 3  # 12 // 4

    def test_format_prompt_basic(self, ollama_service):
        """Test basic prompt formatting."""
        prompt = ollama_service._format_prompt("What is AI?")
        
        assert "Human: What is AI?" in prompt
        assert "Assistant:" in prompt

    def test_format_prompt_with_context(self, ollama_service):
        """Test prompt formatting with context."""
        prompt = ollama_service._format_prompt(
            "What is AI?",
            context="AI stands for Artificial Intelligence"
        )
        
        assert "Context:" in prompt
        assert "AI stands for Artificial Intelligence" in prompt
        assert "Human: What is AI?" in prompt
        assert "Assistant:" in prompt

    def test_format_prompt_with_history(self, ollama_service):
        """Test prompt formatting with conversation history."""
        history = [
            {"role": "user", "content": "Hi"},
            {"role": "assistant", "content": "Hello!"},
            {"role": "user", "content": "How are you?"}
        ]
        
        prompt = ollama_service._format_prompt("Fine, thanks", history=history)
        
        assert "Conversation History:" in prompt
        assert "User: Hi" in prompt
        assert "Assistant: Hello!" in prompt
        assert "User: How are you?" in prompt
        assert "Human: Fine, thanks" in prompt

    def test_format_prompt_with_empty_history_content(self, ollama_service):
        """Test prompt formatting filters empty history content."""
        history = [
            {"role": "user", "content": "Valid message"},
            {"role": "assistant", "content": ""},  # Empty content
            {"role": "user", "content": None}  # None content
        ]
        
        prompt = ollama_service._format_prompt("Test", history=history)
        
        assert "User: Valid message" in prompt
        # Empty/None content should not appear
        assert "Assistant:" not in prompt or "Assistant: \n" not in prompt

    @pytest.mark.asyncio
    async def test_generate_response_success(self, ollama_service):
        """Test successful response generation."""
        mock_response_data = {
            "response": "This is a test response from Ollama",
            "done": True
        }
        
        with patch('aiohttp.ClientSession') as mock_session_class:
            mock_session = AsyncMock()
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.json.return_value = mock_response_data
            
            mock_session.post.return_value.__aenter__.return_value = mock_response
            mock_session_class.return_value.__aenter__.return_value = mock_session
            mock_session_class.return_value.__aexit__.return_value = None
            
            result = await ollama_service.generate_response("Test prompt")
            
            assert result == "This is a test response from Ollama"
            mock_session.post.assert_called_once()

    @pytest.mark.asyncio
    async def test_generate_response_empty_content(self, ollama_service):
        """Test handling of empty response content."""
        mock_response_data = {
            "response": "",
            "done": True
        }
        
        with patch('aiohttp.ClientSession') as mock_session_class:
            mock_session = AsyncMock()
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.json.return_value = mock_response_data
            
            mock_session.post.return_value.__aenter__.return_value = mock_response
            mock_session_class.return_value.__aenter__.return_value = mock_session
            mock_session_class.return_value.__aexit__.return_value = None
            
            result = await ollama_service.generate_response("Test prompt")
            
            assert "I apologize, but I couldn't generate a response" in result

    @pytest.mark.asyncio
    async def test_generate_response_api_error(self, ollama_service):
        """Test handling of API errors."""
        with patch('aiohttp.ClientSession') as mock_session_class:
            mock_session = AsyncMock()
            mock_response = AsyncMock()
            mock_response.status = 500
            mock_response.text.return_value = "Internal Server Error"
            
            mock_session.post.return_value.__aenter__.return_value = mock_response
            mock_session_class.return_value.__aenter__.return_value = mock_session
            mock_session_class.return_value.__aexit__.return_value = None
            
            result = await ollama_service.generate_response("Test prompt")
            
            assert "Ollama API error 500: Internal Server Error" in result

    @pytest.mark.asyncio
    async def test_generate_response_with_max_tokens(self, custom_ollama_service):
        """Test response generation with max tokens setting."""
        mock_response_data = {
            "response": "Response with token limit",
            "done": True
        }
        
        with patch('aiohttp.ClientSession') as mock_session_class:
            mock_session = AsyncMock()
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.json.return_value = mock_response_data
            
            mock_session.post.return_value.__aenter__.return_value = mock_response
            mock_session_class.return_value.__aenter__.return_value = mock_session
            mock_session_class.return_value.__aexit__.return_value = None
            
            await custom_ollama_service.generate_response("Test prompt")
            
            # Check that max_tokens was included in payload
            call_args = mock_session.post.call_args
            payload = call_args[1]['json']
            assert payload['options']['num_predict'] == 1000

    @pytest.mark.asyncio
    async def test_generate_response_stream_success(self, ollama_service):
        """Test successful streaming response generation."""
        mock_chunks = [
            b'{"response": "Hello ", "done": false}\n',
            b'{"response": "world!", "done": false}\n',
            b'{"response": "", "done": true}\n',
        ]
        
        with patch('aiohttp.ClientSession') as mock_session_class:
            mock_session = AsyncMock()
            mock_response = AsyncMock()
            mock_response.status = 200
            
            async def mock_content():
                for chunk in mock_chunks:
                    yield chunk
            
            mock_response.content = mock_content()
            mock_session.post.return_value.__aenter__.return_value = mock_response
            mock_session_class.return_value.__aenter__.return_value = mock_session
            mock_session_class.return_value.__aexit__.return_value = None
            
            result_parts = []
            async for part in ollama_service.generate_response_stream("Test prompt"):
                result_parts.append(part)
            
            assert result_parts == ["Hello ", "world!"]

    @pytest.mark.asyncio
    async def test_generate_response_stream_api_error(self, ollama_service):
        """Test streaming response with API error."""
        with patch('aiohttp.ClientSession') as mock_session_class:
            mock_session = AsyncMock()
            mock_response = AsyncMock()
            mock_response.status = 404
            mock_response.text.return_value = "Model not found"
            
            mock_session.post.return_value.__aenter__.return_value = mock_response
            mock_session_class.return_value.__aenter__.return_value = mock_session
            mock_session_class.return_value.__aexit__.return_value = None
            
            result_parts = []
            async for part in ollama_service.generate_response_stream("Test prompt"):
                result_parts.append(part)
            
            assert len(result_parts) == 1
            assert "Ollama API error 404: Model not found" in result_parts[0]

    @pytest.mark.asyncio
    async def test_generate_response_stream_malformed_json(self, ollama_service):
        """Test streaming response with malformed JSON chunks."""
        mock_chunks = [
            b'{"response": "Hello", "done": false}\n',
            b'invalid json\n',  # Should be skipped
            b'{"response": " world!", "done": true}\n',
        ]
        
        with patch('aiohttp.ClientSession') as mock_session_class:
            mock_session = AsyncMock()
            mock_response = AsyncMock()
            mock_response.status = 200
            
            async def mock_content():
                for chunk in mock_chunks:
                    yield chunk
            
            mock_response.content = mock_content()
            mock_session.post.return_value.__aenter__.return_value = mock_response
            mock_session_class.return_value.__aenter__.return_value = mock_session
            mock_session_class.return_value.__aexit__.return_value = None
            
            result_parts = []
            async for part in ollama_service.generate_response_stream("Test prompt"):
                result_parts.append(part)
            
            # Should skip malformed JSON and continue
            assert result_parts == ["Hello", " world!"]

    @pytest.mark.asyncio
    async def test_extract_entities_relationships(self, ollama_service):
        """Test entity and relationship extraction."""
        json_response = {
            "entities": [
                {"id": "e1", "label": "Person", "name": "John", "properties": {}},
                {"id": "e2", "label": "Company", "name": "Acme", "properties": {}}
            ],
            "relationships": [
                {"source": "e1", "target": "e2", "type": "WORKS_AT", "properties": {}}
            ]
        }
        
        mock_response_data = {
            "response": json.dumps(json_response),
            "done": True
        }
        
        with patch('aiohttp.ClientSession') as mock_session_class:
            mock_session = AsyncMock()
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.json.return_value = mock_response_data
            
            mock_session.post.return_value.__aenter__.return_value = mock_response
            mock_session_class.return_value.__aenter__.return_value = mock_session
            mock_session_class.return_value.__aexit__.return_value = None
            
            entities, relationships = await ollama_service.extract_entities_relationships("John works at Acme")
            
            assert len(entities) == 2
            assert entities[0]["name"] == "John"
            assert entities[1]["name"] == "Acme"
            
            assert len(relationships) == 1
            assert relationships[0]["type"] == "WORKS_AT"

    @pytest.mark.asyncio
    async def test_extract_entities_relationships_invalid_json(self, ollama_service):
        """Test entity extraction with invalid JSON response."""
        mock_response_data = {
            "response": "Invalid JSON response from model",
            "done": True
        }
        
        with patch('aiohttp.ClientSession') as mock_session_class:
            mock_session = AsyncMock()
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.json.return_value = mock_response_data
            
            mock_session.post.return_value.__aenter__.return_value = mock_response
            mock_session_class.return_value.__aenter__.return_value = mock_session
            mock_session_class.return_value.__aexit__.return_value = None
            
            entities, relationships = await ollama_service.extract_entities_relationships("Test text")
            
            assert entities == []
            assert relationships == []

    @pytest.mark.asyncio
    async def test_embed_text_success(self, ollama_service):
        """Test successful text embedding."""
        mock_response_data = {
            "embedding": [0.1, 0.2, 0.3, 0.4]
        }
        
        with patch('aiohttp.ClientSession') as mock_session_class:
            mock_session = AsyncMock()
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.json.return_value = mock_response_data
            
            mock_session.post.return_value.__aenter__.return_value = mock_response
            mock_session_class.return_value.__aenter__.return_value = mock_session
            mock_session_class.return_value.__aexit__.return_value = None
            
            result = await ollama_service.embed_text("Test text")
            
            assert result == [0.1, 0.2, 0.3, 0.4]

    @pytest.mark.asyncio
    async def test_embed_text_fallback_on_api_error(self, ollama_service):
        """Test text embedding fallback when API returns error."""
        with patch('aiohttp.ClientSession') as mock_session_class:
            mock_session = AsyncMock()
            mock_response = AsyncMock()
            mock_response.status = 404  # Embeddings not supported
            
            mock_session.post.return_value.__aenter__.return_value = mock_response
            mock_session_class.return_value.__aenter__.return_value = mock_session
            mock_session_class.return_value.__aexit__.return_value = None
            
            result = await ollama_service.embed_text("Test text")
            
            # Should return hash-based fallback
            assert len(result) == 768
            assert all(isinstance(x, float) for x in result)

    @pytest.mark.asyncio
    async def test_embed_text_fallback_on_exception(self, ollama_service):
        """Test text embedding fallback when exception occurs."""
        with patch('aiohttp.ClientSession', side_effect=Exception("Network error")):
            result = await ollama_service.embed_text("Test text")
            
            # Should return hash-based fallback
            assert len(result) == 768
            assert all(isinstance(x, float) for x in result)

    @pytest.mark.asyncio
    async def test_get_token_usage(self, ollama_service):
        """Test token usage retrieval."""
        # Initially zero
        usage = await ollama_service.get_token_usage()
        assert usage == {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
        
        # Simulate some usage
        ollama_service._token_usage["prompt_tokens"] = 100
        ollama_service._token_usage["completion_tokens"] = 50
        ollama_service._token_usage["total_tokens"] = 150
        
        usage = await ollama_service.get_token_usage()
        assert usage["prompt_tokens"] == 100
        assert usage["completion_tokens"] == 50
        assert usage["total_tokens"] == 150

    def test_reset_token_usage(self, ollama_service):
        """Test token usage reset."""
        # Set some usage
        ollama_service._token_usage["prompt_tokens"] = 100
        ollama_service._token_usage["completion_tokens"] = 50
        ollama_service._token_usage["total_tokens"] = 150
        
        # Reset
        ollama_service.reset_token_usage()
        
        # Should be zero
        assert ollama_service._token_usage["prompt_tokens"] == 0
        assert ollama_service._token_usage["completion_tokens"] == 0
        assert ollama_service._token_usage["total_tokens"] == 0

    @pytest.mark.asyncio
    async def test_health_check_success(self, ollama_service):
        """Test successful health check."""
        with patch('aiohttp.ClientSession') as mock_session_class:
            mock_session = AsyncMock()
            mock_response = AsyncMock()
            mock_response.status = 200
            
            # Mock the context manager for both session and response
            mock_session.get.return_value.__aenter__.return_value = mock_response
            mock_session.get.return_value.__aexit__.return_value = None
            mock_session_class.return_value.__aenter__.return_value = mock_session
            mock_session_class.return_value.__aexit__.return_value = None
            
            result = await ollama_service.health_check()
            
            assert result is True
            mock_session.get.assert_called_once_with("http://localhost:11434/api/tags")

    @pytest.mark.asyncio
    async def test_health_check_failure(self, ollama_service):
        """Test health check failure."""
        with patch('aiohttp.ClientSession') as mock_session_class:
            mock_session = AsyncMock()
            mock_response = AsyncMock()
            mock_response.status = 503
            
            mock_session.get.return_value.__aenter__.return_value = mock_response
            mock_session_class.return_value.__aenter__.return_value = mock_session
            mock_session_class.return_value.__aexit__.return_value = None
            
            result = await ollama_service.health_check()
            
            assert result is False

    @pytest.mark.asyncio
    async def test_health_check_exception(self, ollama_service):
        """Test health check with exception."""
        with patch('aiohttp.ClientSession', side_effect=Exception("Connection error")):
            result = await ollama_service.health_check()
            
            assert result is False

    @pytest.mark.asyncio
    async def test_list_models_success(self, ollama_service):
        """Test successful model listing."""
        mock_response_data = {
            "models": [
                {"name": "llama3.2:3b"},
                {"name": "llama3.2:7b"},
                {"name": "codellama:13b"}
            ]
        }
        
        with patch('aiohttp.ClientSession') as mock_session_class:
            mock_session = AsyncMock()
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.json.return_value = mock_response_data
            
            # Mock the context manager for both session and response
            mock_session.get.return_value.__aenter__.return_value = mock_response
            mock_session.get.return_value.__aexit__.return_value = None
            mock_session_class.return_value.__aenter__.return_value = mock_session
            mock_session_class.return_value.__aexit__.return_value = None
            
            models = await ollama_service.list_models()
            
            assert models == ["llama3.2:3b", "llama3.2:7b", "codellama:13b"]

    @pytest.mark.asyncio
    async def test_list_models_api_error(self, ollama_service):
        """Test model listing with API error."""
        with patch('aiohttp.ClientSession') as mock_session_class:
            mock_session = AsyncMock()
            mock_response = AsyncMock()
            mock_response.status = 500
            
            # Mock the context manager for both session and response
            mock_session.get.return_value.__aenter__.return_value = mock_response
            mock_session.get.return_value.__aexit__.return_value = None
            mock_session_class.return_value.__aenter__.return_value = mock_session
            mock_session_class.return_value.__aexit__.return_value = None
            
            models = await ollama_service.list_models()
            
            assert models == []

    @pytest.mark.asyncio
    async def test_list_models_exception(self, ollama_service):
        """Test model listing with exception."""
        with patch('aiohttp.ClientSession', side_effect=Exception("Network error")):
            models = await ollama_service.list_models()
            
            assert models == []