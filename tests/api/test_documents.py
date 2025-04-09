import pytest
from unittest.mock import patch, AsyncMock
from httpx import AsyncClient
from fastapi import status

from graph_rag.api.main import app # Import app for client
from graph_rag.domain.models import Document # Needed for mock return
from datetime import datetime

# Test data
DOC_ID_TO_DELETE = "doc-to-delete"
DOC_ID_NOT_FOUND = "doc-not-found"
DOC_ID_TO_UPDATE = "doc-to-update"
DOC_ID_UPDATE_NOT_FOUND = "doc-update-not-found"
BASE_METADATA = {"source": "original", "topic": "initial"}
UPDATED_METADATA = {"source": "patched", "status": "complete"}

@pytest.fixture
def mock_graph_repository_for_delete():
    """Mock the GraphRepository specifically for delete tests."""
    # We patch the dependency injection function
    with patch("graph_rag.api.dependencies.get_graph_repository") as mock_get_repo:
        mock_repo_instance = AsyncMock()
        
        # Configure the behavior of the mocked instance's delete_document
        async def mock_delete(doc_id):
            if doc_id == DOC_ID_TO_DELETE:
                return True # Simulate successful deletion
            elif doc_id == DOC_ID_NOT_FOUND:
                return False # Simulate document not found
            else:
                raise Exception("Unexpected ID in mock delete")
                
        mock_repo_instance.delete_document.side_effect = mock_delete
        
        # The dependency function should return our mocked instance
        mock_get_repo.return_value = mock_repo_instance
        yield mock_repo_instance

@pytest.fixture
def mock_graph_repository_for_patch():
    """Mock the GraphRepository specifically for patch tests."""
    with patch("graph_rag.api.dependencies.get_graph_repository") as mock_get_repo:
        mock_repo_instance = AsyncMock()
        
        # Configure update_document_properties
        async def mock_update(document_id, properties_to_update):
            if document_id == DOC_ID_TO_UPDATE:
                # Simulate successful update, return updated Document
                return Document(
                    id=DOC_ID_TO_UPDATE,
                    content="Original content", # Content shouldn't change
                    metadata=properties_to_update.get("metadata", BASE_METADATA),
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow()
                )
            elif document_id == DOC_ID_UPDATE_NOT_FOUND:
                return None # Simulate document not found
            else:
                raise Exception("Unexpected ID in mock update")
                
        mock_repo_instance.update_document_properties.side_effect = mock_update
        
        mock_get_repo.return_value = mock_repo_instance
        yield mock_repo_instance

@pytest.mark.asyncio
async def test_delete_document_endpoint_success(mock_graph_repository_for_delete):
    """Test successful deletion via the DELETE endpoint."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.delete(f"/api/v1/documents/{DOC_ID_TO_DELETE}")
        
    assert response.status_code == status.HTTP_204_NO_CONTENT
    # Verify the repository method was called correctly
    mock_graph_repository_for_delete.delete_document.assert_called_once_with(DOC_ID_TO_DELETE)

@pytest.mark.asyncio
async def test_delete_document_endpoint_not_found(mock_graph_repository_for_delete):
    """Test deleting a non-existent document via the DELETE endpoint."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.delete(f"/api/v1/documents/{DOC_ID_NOT_FOUND}")
        
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json()["detail"] == f"Document with id {DOC_ID_NOT_FOUND} not found or could not be deleted."
    # Verify the repository method was called correctly
    mock_graph_repository_for_delete.delete_document.assert_called_once_with(DOC_ID_NOT_FOUND)

@pytest.mark.asyncio
async def test_delete_document_endpoint_repository_error(mock_graph_repository_for_delete):
    """Test error handling when the repository fails during deletion."""
    # Configure the mock to raise an exception
    mock_graph_repository_for_delete.delete_document.side_effect = Exception("DB error")
    
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.delete(f"/api/v1/documents/some-other-id")
        
    assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
    assert "detail" in response.json()
    assert "Failed to delete document" in response.json()["detail"]

@pytest.mark.asyncio
async def test_patch_document_metadata_success(mock_graph_repository_for_patch):
    """Test successful metadata update via PATCH endpoint."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.patch(
            f"/api/v1/documents/{DOC_ID_TO_UPDATE}",
            json={"metadata": UPDATED_METADATA}
        )
        
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["id"] == DOC_ID_TO_UPDATE
    assert data["metadata"] == UPDATED_METADATA
    assert "content" in data # Ensure other fields are returned
    assert "created_at" in data
    assert "updated_at" in data
    
    # Verify the repository method was called correctly
    mock_graph_repository_for_patch.update_document_properties.assert_called_once_with(
        document_id=DOC_ID_TO_UPDATE, 
        properties_to_update={"metadata": UPDATED_METADATA}
    )

@pytest.mark.asyncio
async def test_patch_document_no_body(mock_graph_repository_for_patch):
    """Test PATCH with an empty request body (should ideally do nothing or validate)."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.patch(
            f"/api/v1/documents/{DOC_ID_TO_UPDATE}",
            json={}
        )
    
    # Expecting success, possibly returning unchanged data or just updated_at change
    assert response.status_code == status.HTTP_200_OK 
    mock_graph_repository_for_patch.update_document_properties.assert_called_once_with(
        document_id=DOC_ID_TO_UPDATE, 
        properties_to_update={} # Service receives empty dict
    )

@pytest.mark.asyncio
async def test_patch_document_invalid_field(mock_graph_repository_for_patch):
    """Test PATCH with fields not allowed for update (only metadata allowed)."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.patch(
            f"/api/v1/documents/{DOC_ID_TO_UPDATE}",
            json={"content": "new content"} # Attempting to change content
        )
        
    # Expect validation error as only metadata is patchable currently
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    mock_graph_repository_for_patch.update_document_properties.assert_not_called()

@pytest.mark.asyncio
async def test_patch_document_not_found(mock_graph_repository_for_patch):
    """Test PATCH on a non-existent document."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.patch(
            f"/api/v1/documents/{DOC_ID_UPDATE_NOT_FOUND}",
            json={"metadata": UPDATED_METADATA}
        )
        
    assert response.status_code == status.HTTP_404_NOT_FOUND
    mock_graph_repository_for_patch.update_document_properties.assert_called_once()

@pytest.mark.asyncio
async def test_patch_document_repository_error(mock_graph_repository_for_patch):
    """Test PATCH when the repository update fails."""
    mock_graph_repository_for_patch.update_document_properties.side_effect = Exception("DB error")
    
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.patch(
            f"/api/v1/documents/some-other-id-patch",
            json={"metadata": UPDATED_METADATA}
        )
        
    assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR 