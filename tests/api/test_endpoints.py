import pytest
from fastapi.testclient import TestClient
from graph_rag.api.main import app

@pytest.fixture
def test_client():
    return TestClient(app)

def test_health_check(test_client):
    """Test the health check endpoint."""
    response = test_client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}

@pytest.mark.asyncio
async def test_create_document(test_client, graph_repository):
    """Test creating a document through the API."""
    doc_data = {
        "document_id": "test_doc_api_1",
        "text": "This is a test document from the API"
    }
    
    response = test_client.post("/documents/", json=doc_data)
    assert response.status_code == 200
    
    # Verify the document was created in the database
    result = await graph_repository.get_document(doc_data["document_id"])
    assert result is not None
    assert result["document_id"] == doc_data["document_id"]
    assert result["text"] == doc_data["text"]

@pytest.mark.asyncio
async def test_get_document(test_client, graph_repository):
    """Test retrieving a document through the API."""
    # First create a document
    doc_id = "test_doc_api_2"
    doc_text = "This is another test document from the API"
    await graph_repository.create_document(doc_id, doc_text)
    
    # Then try to retrieve it
    response = test_client.get(f"/documents/{doc_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["document_id"] == doc_id
    assert data["text"] == doc_text

@pytest.mark.asyncio
async def test_create_chunk(test_client, graph_repository):
    """Test creating a chunk through the API."""
    # First create a document
    doc_id = "test_doc_api_3"
    doc_text = "Document for chunk test"
    await graph_repository.create_document(doc_id, doc_text)
    
    # Then create a chunk
    chunk_data = {
        "chunk_id": "test_chunk_api_1",
        "text": "This is a test chunk from the API",
        "embedding": [0.1, 0.2, 0.3],
        "document_id": doc_id
    }
    
    response = test_client.post("/chunks/", json=chunk_data)
    assert response.status_code == 200
    
    # Verify the chunk was created in the database
    result = await graph_repository.get_chunk(chunk_data["chunk_id"])
    assert result is not None
    assert result["chunk_id"] == chunk_data["chunk_id"]
    assert result["text"] == chunk_data["text"]
    assert result["embedding"] == chunk_data["embedding"]
    assert result["document"]["document_id"] == doc_id 