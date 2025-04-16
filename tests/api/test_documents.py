import pytest
from unittest.mock import patch, AsyncMock
from httpx import AsyncClient
from fastapi import status

# from graph_rag.api.main import app # Import app for client -- No longer needed
from graph_rag.domain.models import Entity # Import Entity for mocking
from datetime import datetime, timezone

# Test data
DOC_ID_TO_DELETE = "doc-to-delete"
DOC_ID_NOT_FOUND = "doc-not-found"
DOC_ID_TO_UPDATE = "doc-to-update"
DOC_ID_UPDATE_NOT_FOUND = "doc-update-not-found"
DOC_ID_REPO_ERROR = "doc-repo-error"
BASE_METADATA = {"source": "original", "topic": "initial"}
# Define UPDATED_METADATA before using it
UPDATED_METADATA = {"source": "patched", "status": "complete"}
# Combine base and update for expected result, as endpoint merges
# Properties in request only updates existing keys or adds new ones. Endpoint logic fetches, updates, then saves.
EXPECTED_MERGED_METADATA = BASE_METADATA.copy()
EXPECTED_MERGED_METADATA.update(UPDATED_METADATA) # {"source": "patched", "topic": "initial", "status": "complete"}

# Dummy node data for get_entity_by_id mock (as Entity)
DUMMY_ENTITY_DATA = Entity(
    id=DOC_ID_TO_UPDATE,
    type="Document",
    properties=BASE_METADATA
)

DUMMY_ENTITY_DATA_REPO_ERROR = Entity( # For the repo error test case
    id=DOC_ID_REPO_ERROR,
    type="Document",
    properties={"some_key": "some_value"} # Give it some initial properties
)

# Expected updated entity after successful patch (used for second get_entity_by_id mock)
EXPECTED_UPDATED_ENTITY_AFTER_PATCH = Entity(
    id=DOC_ID_TO_UPDATE,
    type="Document",
    properties=EXPECTED_MERGED_METADATA
)

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
    # Mock get_entity_by_id to return the existing entity initially.
    # The endpoint internally calls add_entity (which replaces props) and then fetches again.
    # We only need to mock the initial fetch.
    async def mock_get_entity(entity_id):
        if entity_id == DOC_ID_TO_UPDATE:
             # Always return the initial state for the first get call
             return DUMMY_ENTITY_DATA
        return None
    mock_graph_repo.get_entity_by_id.side_effect = mock_get_entity

    # Mock add_entity (which replaces properties) to signify success
    mock_graph_repo.add_entity.return_value = None # add_entity doesn't return anything significant

    mock_graph_repo.reset_mock() # Reset calls, not side effects
    # Re-apply side effects after reset_mock
    mock_graph_repo.get_entity_by_id.side_effect = mock_get_entity
    mock_graph_repo.add_entity.return_value = None


    response = await test_client.patch(
        f"/api/v1/documents/{DOC_ID_TO_UPDATE}/metadata",
        json={"properties": UPDATED_METADATA} # Schema expects {"properties": {...}}
    )

    # Debugging output
    print(f"Response Status: {response.status_code}")
    print(f"Response JSON: {response.text}")
    print(f"get_entity_by_id calls: {mock_graph_repo.get_entity_by_id.call_args_list}")
    print(f"add_entity calls: {mock_graph_repo.add_entity.call_args_list}")

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["id"] == DOC_ID_TO_UPDATE
    # Assert against the merged metadata, reflecting the update logic
    assert data["metadata"] == EXPECTED_MERGED_METADATA # Changed from "properties" to "metadata" to match schema
    # assert "content" not in data # Content is not part of DocumentResponse schema
    assert "type" in data and data["type"] == "Document" # Check type if included

    # Verify the repository methods were called correctly
    # Should be called once: only before update (project pattern)
    assert mock_graph_repo.get_entity_by_id.call_count == 1
    mock_graph_repo.get_entity_by_id.assert_any_call(DOC_ID_TO_UPDATE) # Check it was called with the ID

    # Check that add_entity was called once with the correct merged properties
    mock_graph_repo.add_entity.assert_awaited_once()
    call_args, _ = mock_graph_repo.add_entity.call_args
    added_entity = call_args[0]
    assert isinstance(added_entity, Entity)
    assert added_entity.id == DOC_ID_TO_UPDATE
    assert added_entity.type == "Document"
    assert added_entity.properties == EXPECTED_MERGED_METADATA

@pytest.mark.asyncio
async def test_patch_document_no_body(test_client: AsyncClient, mock_graph_repo: AsyncMock):
    """Test PATCH with an empty request body (expects 422)."""
    # No need to mock repo methods as validation should fail first
    mock_graph_repo.reset_mock()

    response = await test_client.patch(
        f"/api/v1/documents/{DOC_ID_TO_UPDATE}/metadata",
        json={} # Empty body - Should still fail 422, but for missing 'properties' field
    )
    
    # Expecting 422 because the request body is invalid per the schema
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY 
    mock_graph_repo.get_entity_by_id.assert_not_awaited()
    mock_graph_repo.add_entity.assert_not_awaited()

@pytest.mark.asyncio
async def test_patch_document_invalid_field(test_client: AsyncClient, mock_graph_repo: AsyncMock):
    """Test PATCH with fields not allowed for update (expects 422)."""
    # No need to mock repo methods as validation should fail first
    mock_graph_repo.reset_mock() # Reset mock, it shouldn't be called

    response = await test_client.patch(
        f"/api/v1/documents/{DOC_ID_TO_UPDATE}/metadata",
        json={"content": "new content"} # Invalid body - Should still fail 422
    )
        
    # Expect validation error as DocumentUpdateMetadataRequest only accepts metadata
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    mock_graph_repo.get_entity_by_id.assert_not_awaited()
    mock_graph_repo.add_entity.assert_not_awaited()

@pytest.mark.asyncio
async def test_patch_document_not_found(test_client: AsyncClient, mock_graph_repo: AsyncMock):
    """Test PATCH on a non-existent document."""
    # Configure get_entity_by_id mock to return None
    async def mock_get_entity(entity_id):
        if entity_id == DOC_ID_UPDATE_NOT_FOUND:
            return None
        # Return dummy data for other potential calls if necessary, though unlikely here
        return DUMMY_ENTITY_DATA
    mock_graph_repo.get_entity_by_id.side_effect = mock_get_entity
    mock_graph_repo.add_entity.return_value = None # Mock add_entity just in case

    mock_graph_repo.reset_mock() # Reset calls
    mock_graph_repo.get_entity_by_id.side_effect = mock_get_entity
    mock_graph_repo.add_entity.return_value = None


    response = await test_client.patch(
        f"/api/v1/documents/{DOC_ID_UPDATE_NOT_FOUND}/metadata",
        json={"properties": UPDATED_METADATA} # Request body schema
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND
    # Verify get_entity_by_id was called, but add_entity was not
    mock_graph_repo.get_entity_by_id.assert_awaited_once_with(DOC_ID_UPDATE_NOT_FOUND)
    mock_graph_repo.add_entity.assert_not_awaited()

@pytest.mark.asyncio
async def test_patch_document_repository_error(test_client: AsyncClient, mock_graph_repo: AsyncMock):
    """Test PATCH when the repository update (add_entity) fails."""
    # Mock get_entity_by_id to return the existing entity
    async def mock_get_entity(entity_id):
        if entity_id == DOC_ID_REPO_ERROR:
            return DUMMY_ENTITY_DATA_REPO_ERROR
        return None
    mock_graph_repo.get_entity_by_id.side_effect = mock_get_entity

    # Mock add_entity to raise an error
    mock_graph_repo.add_entity.side_effect = Exception("DB error on update")

    mock_graph_repo.reset_mock()
    mock_graph_repo.get_entity_by_id.side_effect = mock_get_entity
    mock_graph_repo.add_entity.side_effect = Exception("DB error on update")

    response = await test_client.patch(
        f"/api/v1/documents/{DOC_ID_REPO_ERROR}/metadata",
        json={"properties": UPDATED_METADATA} # Request body schema
    )

    assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR

    # Verify get_entity_by_id was called once
    mock_graph_repo.get_entity_by_id.assert_awaited_once_with(DOC_ID_REPO_ERROR)

    # Verify add_entity was called once with the expected updated entity data
    mock_graph_repo.add_entity.assert_awaited_once()
    call_args, _ = mock_graph_repo.add_entity.call_args
    added_entity = call_args[0]
    assert isinstance(added_entity, Entity)
    assert added_entity.id == DOC_ID_REPO_ERROR
    assert added_entity.type == "Document"
    # Check properties passed to add_entity are the merged ones
    expected_merged_props = DUMMY_ENTITY_DATA_REPO_ERROR.properties.copy()
    expected_merged_props.update(UPDATED_METADATA)
    assert added_entity.properties == expected_merged_props

    # Verify that the repository methods were called correctly
    mock_graph_repo.get_entity_by_id.assert_awaited_once_with(DOC_ID_REPO_ERROR)
    mock_graph_repo.add_entity.assert_awaited_once()
    call_args, _ = mock_graph_repo.add_entity.call_args
    added_entity = call_args[0]
    assert isinstance(added_entity, Entity)
    assert added_entity.id == DOC_ID_REPO_ERROR
    assert added_entity.type == "Document"
    assert added_entity.properties == expected_merged_props