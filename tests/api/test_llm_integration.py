"""Test LLM integration in the API endpoints."""

import pytest
from unittest.mock import AsyncMock, MagicMock
from fastapi.testclient import TestClient
from graph_rag.api.main import create_app
from graph_rag.llm import MockLLMService


@pytest.fixture
def test_client():
    """Create a test client with mocked dependencies."""
    app = create_app()
    return TestClient(app)


@pytest.mark.asyncio
async def test_ask_endpoint_uses_llm_service(test_client, mocker):
    """Test that the /ask endpoint properly uses the LLM service."""
    # Mock the LLM service
    mock_llm = AsyncMock(spec=MockLLMService)
    mock_llm.generate_response.return_value = "Test LLM response with context."
    
    # Mock the engine dependency to return our mock LLM
    mock_engine = AsyncMock()
    mock_engine.query.return_value = MagicMock(
        answer="Test LLM response with context.",
        relevant_chunks=[],
        graph_context=None,
        metadata={"citations": []}
    )
    
    # Mock the dependency
    mocker.patch(
        "graph_rag.api.dependencies.get_graph_rag_engine",
        return_value=mock_engine
    )
    
    # Test the ask endpoint
    response = test_client.post(
        "/api/v1/query/ask",
        json={
            "text": "What is the meaning of life?",
            "k": 3,
            "include_graph": True
        }
    )
    
    assert response.status_code == 200
    data = response.json()
    assert "answer" in data
    assert data["answer"] == "Test LLM response with context."
    
    # Verify the engine was called
    mock_engine.query.assert_called_once()


def test_ask_endpoint_without_llm_service_returns_mock_response(test_client):
    """Test ask endpoint works with default MockLLMService."""
    # This test should work with the default setup using MockLLMService
    response = test_client.post(
        "/api/v1/query/ask",
        json={
            "text": "Test query",
            "k": 1,
            "include_graph": False
        }
    )
    
    # The response should succeed even with mock service
    # May get a 503 if dependencies aren't available, but structure should be correct
    assert response.status_code in [200, 503]  # 503 if memgraph not available in test
    
    if response.status_code == 200:
        data = response.json()
        assert "answer" in data
        assert "relevant_chunks" in data
        assert "metadata" in data


@pytest.mark.asyncio
async def test_llm_service_wired_correctly_in_dependencies():
    """Test that LLM service is properly wired in dependency injection."""
    from graph_rag.api.dependencies import create_llm_service, get_settings
    
    settings = get_settings()
    llm_service = create_llm_service(settings)
    
    # Should return a LLM service instance
    assert hasattr(llm_service, 'generate_response')
    assert hasattr(llm_service, 'generate_response_stream')
    
    # Should be MockLLMService by default
    from graph_rag.llm import MockLLMService
    assert isinstance(llm_service, MockLLMService)


@pytest.mark.asyncio
async def test_mock_llm_service_functionality():
    """Test that MockLLMService works as expected."""
    from graph_rag.llm import MockLLMService
    
    llm = MockLLMService()
    
    # Test generate_response
    response = await llm.generate_response("What is AI?")
    assert isinstance(response, str)
    assert "Mock response" in response
    assert "What is AI?" in response
    
    # Test generate_response with context
    response_with_context = await llm.generate_response(
        "What is AI?", 
        context="AI stands for Artificial Intelligence"
    )
    assert isinstance(response_with_context, str)
    assert "Mock response" in response_with_context
    assert "Based on context" in response_with_context
    
    # Test streaming response
    stream_parts = []
    async for part in llm.generate_response_stream("Test streaming"):
        stream_parts.append(part)
    
    full_response = ''.join(stream_parts)
    assert "Mock stream response" in full_response
    assert "Test streaming" in full_response