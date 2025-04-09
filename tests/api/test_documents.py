import pytest
from unittest.mock import patch, AsyncMock
from httpx import AsyncClient
from fastapi import status

# from graph_rag.api.main import app # Import app for client -- No longer needed
from graph_rag.domain.models import Document # Needed for mock return
from datetime import datetime, timezone

# Test data
DOC_ID_TO_DELETE = "doc-to-delete"
DOC_ID_NOT_FOUND = "doc-not-found"
DOC_ID_TO_UPDATE = "doc-to-update"
DOC_ID_UPDATE_NOT_FOUND = "doc-update-not-found"
DOC_ID_REPO_ERROR = "doc-repo-error"
BASE_METADATA = {"source": "original", "topic": "initial"}
UPDATED_METADATA = {"source": "patched", "status": "complete"}
# Dummy node data for get_node mock
DUMMY_NODE_DATA = {
    "_label": "Document", 
    "id": DOC_ID_TO_UPDATE, 
    "content": "Original content",
    "metadata": BASE_METADATA,
    "created_at": datetime.now(timezone.utc).isoformat(),
    "updated_at": datetime.now(timezone.utc).isoformat()
}
DUMMY_NODE_DATA_REPO_ERROR = { # For the repo error test case
    "_label": "Document", 
    "id": DOC_ID_REPO_ERROR, 
    "content": "Content",
    "metadata": {},
    "created_at": datetime.now(timezone.utc).isoformat(),
    "updated_at": datetime.now(timezone.utc).isoformat()
}

@pytest.mark.asyncio
async def test_delete_document_endpoint_success(test_client: AsyncClient, mock_graph_repo: AsyncMock):
    """Test successful deletion via the DELETE endpoint."""
    # Configure mock for this test
    async def mock_delete(doc_id):
        if doc_id == DOC_ID_TO_DELETE:
            return True
        return False
    mock_graph_repo.delete_document.side_effect = mock_delete
    mock_graph_repo.reset_mock() # Reset mock state before the call

    response = await test_client.delete(f"/api/v1/documents/{DOC_ID_TO_DELETE}")
        
    assert response.status_code == status.HTTP_204_NO_CONTENT
    # Verify the repository method was called correctly
    mock_graph_repo.delete_document.assert_awaited_once_with(DOC_ID_TO_DELETE)

@pytest.mark.asyncio
async def test_delete_document_endpoint_not_found(test_client: AsyncClient, mock_graph_repo: AsyncMock):
    """Test deleting a non-existent document via the DELETE endpoint."""
    # Configure mock for this test
    async def mock_delete(doc_id):
        if doc_id == DOC_ID_NOT_FOUND:
            return False
        return True # Or raise an error for unexpected IDs if preferred
    mock_graph_repo.delete_document.side_effect = mock_delete
    mock_graph_repo.reset_mock()

    response = await test_client.delete(f"/api/v1/documents/{DOC_ID_NOT_FOUND}")
        
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json()["detail"] == f"Document with id {DOC_ID_NOT_FOUND} not found or could not be deleted."
    # Verify the repository method was called correctly
    mock_graph_repo.delete_document.assert_awaited_once_with(DOC_ID_NOT_FOUND)

@pytest.mark.asyncio
async def test_delete_document_endpoint_repository_error(test_client: AsyncClient, mock_graph_repo: AsyncMock):
    """Test error handling when the repository fails during deletion."""
    # Configure the mock to raise an exception
    mock_graph_repo.delete_document.side_effect = Exception("DB error")
    mock_graph_repo.reset_mock()
    
    response = await test_client.delete(f"/api/v1/documents/{DOC_ID_REPO_ERROR}") # Use specific ID for clarity
        
    assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
    assert "detail" in response.json()
    assert "Failed to delete document" in response.json()["detail"]
    mock_graph_repo.delete_document.assert_awaited_once_with(DOC_ID_REPO_ERROR)

@pytest.mark.asyncio
async def test_patch_document_metadata_success(test_client: AsyncClient, mock_graph_repo: AsyncMock):
    """Test successful metadata update via PATCH endpoint."""
    # Mock get_node to return the existing node
    async def mock_get(node_id):
        if node_id == DOC_ID_TO_UPDATE:
            return DUMMY_NODE_DATA
        return None
    mock_graph_repo.get_node.side_effect = mock_get

    # Mock update_node_properties to return updated data
    async def mock_update(node_id, properties):
        if node_id == DOC_ID_TO_UPDATE:
            updated_node = DUMMY_NODE_DATA.copy()
            updated_node["metadata"] = properties # Apply the update
            updated_node["updated_at"] = datetime.now(timezone.utc).isoformat()
            return updated_node
        return None
    mock_graph_repo.update_node_properties.side_effect = mock_update
    mock_graph_repo.reset_mock() # Reset calls, not side effects
    # Re-apply side effects after reset_mock if needed per test logic, or reset specific mocks
    mock_graph_repo.get_node.reset_mock() 
    mock_graph_repo.update_node_properties.reset_mock()
    mock_graph_repo.get_node.side_effect = mock_get
    mock_graph_repo.update_node_properties.side_effect = mock_update


    response = await test_client.patch(
        f"/api/v1/documents/{DOC_ID_TO_UPDATE}",
        json={"metadata": UPDATED_METADATA} # Ensure request schema is met
    )
        
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["id"] == DOC_ID_TO_UPDATE
    assert data["metadata"] == UPDATED_METADATA
    assert "content" in data 
    assert "created_at" in data
    assert "updated_at" in data
    
    # Verify the repository methods were called correctly
    mock_graph_repo.get_node.assert_awaited_once_with(DOC_ID_TO_UPDATE)
    mock_graph_repo.update_node_properties.assert_awaited_once_with(
        DOC_ID_TO_UPDATE, 
        UPDATED_METADATA # Endpoint extracts metadata from request
    )

@pytest.mark.asyncio
async def test_patch_document_no_body(test_client: AsyncClient, mock_graph_repo: AsyncMock):
    """Test PATCH with an empty request body (expects 422)."""
    # No need to mock repo methods as validation should fail first
    mock_graph_repo.reset_mock()

    response = await test_client.patch(
        f"/api/v1/documents/{DOC_ID_TO_UPDATE}",
        json={}
    )
    
    # Expecting 422 because the request body is invalid per the schema
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY 
    mock_graph_repo.get_node.assert_not_awaited()
    mock_graph_repo.update_node_properties.assert_not_awaited()

@pytest.mark.asyncio
async def test_patch_document_invalid_field(test_client: AsyncClient, mock_graph_repo: AsyncMock):
    """Test PATCH with fields not allowed for update (expects 422)."""
    # No need to mock repo methods as validation should fail first
    mock_graph_repo.reset_mock() # Reset mock, it shouldn't be called

    response = await test_client.patch(
        f"/api/v1/documents/{DOC_ID_TO_UPDATE}",
        json={"content": "new content"} # Attempting to change content, invalid schema
    )
        
    # Expect validation error as DocumentUpdateMetadataRequest only accepts metadata
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    mock_graph_repo.get_node.assert_not_awaited()
    mock_graph_repo.update_node_properties.assert_not_awaited()

@pytest.mark.asyncio
async def test_patch_document_not_found(test_client: AsyncClient, mock_graph_repo: AsyncMock):
    """Test PATCH on a non-existent document."""
    # Configure get_node mock to return None
    async def mock_get(node_id):
        if node_id == DOC_ID_UPDATE_NOT_FOUND:
            return None
        return DUMMY_NODE_DATA # Return dummy for other potential calls
    mock_graph_repo.get_node.side_effect = mock_get
    mock_graph_repo.reset_mock() # Reset calls
    mock_graph_repo.get_node.reset_mock()
    mock_graph_repo.update_node_properties.reset_mock()
    mock_graph_repo.get_node.side_effect = mock_get

    response = await test_client.patch(
        f"/api/v1/documents/{DOC_ID_UPDATE_NOT_FOUND}",
        json={"metadata": UPDATED_METADATA}
    )
        
    assert response.status_code == status.HTTP_404_NOT_FOUND
    mock_graph_repo.get_node.assert_awaited_once_with(DOC_ID_UPDATE_NOT_FOUND)
    mock_graph_repo.update_node_properties.assert_not_awaited() # Should not be called if get_node returns None

@pytest.mark.asyncio
async def test_patch_document_repository_error(test_client: AsyncClient, mock_graph_repo: AsyncMock):
    """Test PATCH when the repository update fails."""
    # Mock get_node to return the existing node
    async def mock_get(node_id):
        if node_id == DOC_ID_REPO_ERROR:
            return DUMMY_NODE_DATA_REPO_ERROR
        return None
    mock_graph_repo.get_node.side_effect = mock_get
    
    # Mock update_node_properties to raise an error
    mock_graph_repo.update_node_properties.side_effect = Exception("DB error on update")
    mock_graph_repo.reset_mock()
    mock_graph_repo.get_node.reset_mock() 
    mock_graph_repo.update_node_properties.reset_mock()
    mock_graph_repo.get_node.side_effect = mock_get
    mock_graph_repo.update_node_properties.side_effect = Exception("DB error on update")

    response = await test_client.patch(
        f"/api/v1/documents/{DOC_ID_REPO_ERROR}",
        json={"metadata": UPDATED_METADATA}
    )
        
    assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
    mock_graph_repo.get_node.assert_awaited_once_with(DOC_ID_REPO_ERROR)
    mock_graph_repo.update_node_properties.assert_awaited_once_with(
        DOC_ID_REPO_ERROR, 
        UPDATED_METADATA
    ) 