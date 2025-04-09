import pytest
from httpx import AsyncClient
from fastapi import status

# Assuming your FastAPI app instance is accessible for testing
# If main.app isn't directly importable, adjust how you get the app
# Might need a fixture in conftest.py to provide the app instance
from graph_rag.api.main import app 

# Mark all tests in this module as async
pytestmark = pytest.mark.asyncio 

@pytest.fixture(scope="module")
async def async_client() -> AsyncClient:
    """Provides an async test client for the FastAPI app."""
    async with AsyncClient(app=app, base_url="http://testserver") as client:
        yield client

# --- Test Cases --- 

async def test_ingest_document_success(async_client: AsyncClient):
    """Test successful ingestion of a document via the API."""
    payload = {
        "content": "This is a test document about Alice and Bob.",
        "metadata": {"source": "api-test", "category": "testing"},
        "document_id": "test-doc-api-01"
    }
    
    response = await async_client.post("/api/v1/ingestion/documents", json=payload)
    
    assert response.status_code == status.HTTP_202_ACCEPTED
    response_data = response.json()
    assert response_data["message"] == "Ingestion task accepted."
    assert response_data["document_id"] == "test-doc-api-01"
    # TODO: Verify side effects (e.g., check mock graph/vector stores if possible 
    #       or use dependency overrides during testing)

async def test_ingest_document_generate_id(async_client: AsyncClient):
    """Test ingestion when document_id is not provided (should be generated)."""
    payload = {
        "content": "Another test document.",
        "metadata": {"source": "api-test-genid"}
    }
    
    response = await async_client.post("/api/v1/ingestion/documents", json=payload)
    
    assert response.status_code == status.HTTP_202_ACCEPTED
    response_data = response.json()
    assert response_data["message"] == "Ingestion task accepted."
    assert "document_id" in response_data
    assert response_data["document_id"].startswith("doc-") # Check generated format

async def test_ingest_document_empty_content(async_client: AsyncClient):
    """Test ingestion attempt with empty content string."""
    payload = {
        "content": "", # Empty content
        "metadata": {"source": "api-test-empty"}
    }
    
    # The API endpoint itself doesn't currently validate empty content, 
    # the core Document model might. Let's assume the current behavior 
    # accepts it but might log warnings or result in no chunks/entities.
    # If validation IS added to the API model (e.g. min_length=1), 
    # this test should expect a 422 Unprocessable Entity.
    
    response = await async_client.post("/api/v1/ingestion/documents", json=payload)
    
    # Assuming it's currently accepted (change if API validation added)
    assert response.status_code == status.HTTP_202_ACCEPTED 
    # assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    
async def test_ingest_document_missing_content(async_client: AsyncClient):
    """Test ingestion request missing the required 'content' field."""
    payload = { 
        # Missing "content"
        "metadata": {"source": "api-test-missing"}
    }
    
    response = await async_client.post("/api/v1/ingestion/documents", json=payload)
    
    # FastAPI/Pydantic handles validation of required fields
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    response_data = response.json()
    assert "detail" in response_data
    # Check that the error message indicates 'content' is missing
    assert any("content" in err.get("loc", []) and "missing" in err.get("type", "") for err in response_data.get("detail", []))

async def test_ingest_document_invalid_metadata_type(async_client: AsyncClient):
    """Test ingestion with metadata that is not a dictionary."""
    payload = { 
        "content": "Valid content.",
        "metadata": ["not", "a", "dictionary"] # Invalid type
    }
    
    response = await async_client.post("/api/v1/ingestion/documents", json=payload)
    
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    response_data = response.json()
    assert "detail" in response_data
    assert any("metadata" in err.get("loc", []) and "dict_type" in err.get("type", "") for err in response_data.get("detail", []))

# TODO: Add tests that mock dependencies (doc_processor, extractor, builder) 
#       to verify they are called correctly and handle their potential errors.
#       This requires using FastAPI's dependency overrides feature. 