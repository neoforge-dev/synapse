import pytest
from unittest.mock import patch, AsyncMock
from httpx import AsyncClient
from fastapi import status, FastAPI
import uuid # Import uuid

# from graph_rag.api.main import app # Import app for client -- No longer needed
from graph_rag.domain.models import Entity # Import Entity for mocking
from datetime import datetime, timezone
from graph_rag.api.dependencies import get_graph_repository, get_ingestion_service # Import getters

# Test data
# Use a dynamic UUID for the test to avoid conflicts between runs
# DOC_ID_TO_DELETE = "doc-to-delete" # Replaced with dynamic UUID
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
async def test_delete_document_endpoint_success(
    integration_test_client: AsyncClient, # Use the integration client
    app: FastAPI, # Use the app fixture for a real app instance
    # Remove mock_graph_repo fixture
):
    """Tests successful deletion of a document via the API endpoint using integration client."""
    
    # Generate a unique ID for this test run
    doc_id_to_delete = f"test-delete-{uuid.uuid4()}"
    doc_payload = {
        "id": doc_id_to_delete,
        "content": "This is a test document to be deleted.",
        "metadata": {"test_run_id": str(uuid.uuid4()), "purpose": "delete_test"}
    }

    # --- Step 1: Create the document ---
    # Use the POST endpoint to add the document first
    # Note: Adjust endpoint path and payload based on the actual add_document endpoint definition
    create_response = await integration_test_client.post(
        "/api/v1/documents", 
        json=doc_payload
    )
    # Basic check to ensure creation was likely successful before proceeding
    # Using >= 200 and < 300 to accommodate 200 OK or 201 Created etc.
    assert 200 <= create_response.status_code < 300, \
        f"Failed to create document for deletion test. Status: {create_response.status_code}, Response: {create_response.text}"

    # --- Step 2: Delete the document ---
    # Make the DELETE request using the integration client
    delete_response = await integration_test_client.delete(f"/api/v1/documents/{doc_id_to_delete}")

    # Assertions for successful deletion
    assert delete_response.status_code == status.HTTP_204_NO_CONTENT, \
        f"Expected 204, got {delete_response.status_code}, response: {delete_response.text}"

    # --- Step 3: Verify deletion (Optional but recommended) ---
    get_response = await integration_test_client.get(f"/api/v1/documents/{doc_id_to_delete}")
    assert get_response.status_code == status.HTTP_404_NOT_FOUND, \
        f"Document {doc_id_to_delete} should have been deleted, but GET returned {get_response.status_code}"

    # No mock assertions needed as we removed the mock

@pytest.mark.asyncio
async def test_delete_document_endpoint_not_found(
    integration_test_client: AsyncClient, # Changed from test_client
    app: FastAPI, # Added app fixture
    mock_graph_repo: AsyncMock # Keep mock repo fixture for this specific test (testing 404 logic directly)
):
    """Tests attempting to delete a non-existent document via the API endpoint."""
    
    # Configure mock to simulate document not found in the repository layer
    mock_graph_repo.delete_document.reset_mock()
    mock_graph_repo.delete_document.return_value = False # Simulate repo returning False

    # Apply override for this test ONLY
    original_override = app.dependency_overrides.get(get_graph_repository)
    app.dependency_overrides[get_graph_repository] = lambda: mock_graph_repo

    # --- Step 1: Attempt to delete a non-existent document ---
    # Use a unique ID guaranteed not to exist (or verify it doesn't exist)
    doc_id_not_found = f"test-non-existent-{uuid.uuid4()}"
    
    try:
        # Make the DELETE request
        response = await integration_test_client.delete(f"/api/v1/documents/{doc_id_not_found}")

        # Assertions
        # The endpoint logic should catch the `False` from the repo and return 404
        assert response.status_code == status.HTTP_404_NOT_FOUND, \
            f"Expected 404, got {response.status_code}"
        # Verify the mock was called as expected
        mock_graph_repo.delete_document.assert_awaited_once_with(doc_id_not_found)
        # Check response detail if available
        # assert response.json() == {"detail": f"Document with id {doc_id_not_found} not found"} # Adjust based on actual response
    
    finally:
        # Clean up override
        if original_override:
            app.dependency_overrides[get_graph_repository] = original_override
        elif get_graph_repository in app.dependency_overrides:
             del app.dependency_overrides[get_graph_repository]

@pytest.mark.asyncio
async def test_delete_document_endpoint_repository_error(
    integration_test_client: AsyncClient, # Use integration client
    app: FastAPI, # Use app fixture
    mock_graph_repo: AsyncMock # Use mock repo for simulating error
):
    """Test error handling when the repository fails during deletion."""
    
    # Generate a unique ID for this test run
    doc_id_repo_error = f"test-repo-error-{uuid.uuid4()}"

    # Configure the mock to raise an exception during deletion
    mock_graph_repo.delete_document.reset_mock()
    mock_graph_repo.delete_document.side_effect = Exception("Simulated DB error during delete")

    # Apply override for this test ONLY
    original_override = app.dependency_overrides.get(get_graph_repository)
    app.dependency_overrides[get_graph_repository] = lambda: mock_graph_repo

    try:
        # --- Step 1: Attempt to delete, expecting repository error ---
        response = await integration_test_client.delete(f"/api/v1/documents/{doc_id_repo_error}")
            
        # Assertions
        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR, \
            f"Expected 500, got {response.status_code}"
        assert "detail" in response.json()
        # Check if the detail message indicates the failure reason
        assert "Failed to delete document" in response.json()["detail"], \
            f"Unexpected error detail: {response.json()['detail']}"
        # Verify the mock was called
        mock_graph_repo.delete_document.assert_awaited_once_with(doc_id_repo_error)

    finally:
        # Clean up override
        if original_override:
            app.dependency_overrides[get_graph_repository] = original_override
        elif get_graph_repository in app.dependency_overrides:
             del app.dependency_overrides[get_graph_repository]

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

# --- Existing Test (Example - might need update) ---
@pytest.mark.asyncio
async def test_create_document_endpoint(
    integration_test_client: AsyncClient, # Changed from test_client? Assess if lifespan needed
    app: FastAPI, # Added app fixture
    mock_ingestion_service: AsyncMock # Keep relevant mock
):
    """Tests the document creation endpoint (POST /api/v1/documents)."""
    doc_content = "This is the content of the new document."
    doc_metadata = {"source": "test_create", "custom": "value"}
    doc_id_expected = "new-doc-123" # Assuming ingestion service returns an ID

    # Configure mock
    mock_ingestion_service.handle_new_document.reset_mock()
    # Simulate the ingestion service returning the document ID upon background processing (or immediate if sync)
    mock_ingestion_service.handle_new_document.return_value = doc_id_expected

    # Apply override for ingestion service
    original_override = app.dependency_overrides.get(get_ingestion_service)
    app.dependency_overrides[get_ingestion_service] = lambda: mock_ingestion_service

    payload = {"content": doc_content, "metadata": doc_metadata}

    try:
        # Make the POST request
        response = await integration_test_client.post("/api/v1/documents", json=payload)

        # Assertions (endpoint likely returns 202 Accepted if background processing)
        # assert response.status_code == status.HTTP_202_ACCEPTED, f"Expected 202, got {response.status_code}"
        # Corrected: This endpoint directly creates the document node, so 201 is expected.
        assert response.status_code == status.HTTP_201_CREATED, f"Expected 201, got {response.status_code}"

        # Verify the response payload matches the expected ID (it's generated internally now)
        response_data = response.json()
        assert "id" in response_data, "Response should contain the document ID"
        # assert response_data["id"] == doc_id_expected # Cannot assert specific ID as it's generated

        # Verify the ingestion service was called correctly (might be async call)
        # Check how handle_new_document is called (sync/async, args)
        # Adjust assertion based on whether it's called directly or via background tasks
        # mock_ingestion_service.handle_new_document.assert_called_once() # Or assert_awaited_once
        # args, kwargs = mock_ingestion_service.handle_new_document.call_args
        # assert kwargs['content'] == doc_content
        # assert kwargs['metadata'] == doc_metadata
        # assert kwargs['document_id'] is not None # Check if ID is passed or generated
        
    finally:
        # Clean up override
        if original_override:
            app.dependency_overrides[get_ingestion_service] = original_override
        elif get_ingestion_service in app.dependency_overrides:
             del app.dependency_overrides[get_ingestion_service]

# TODO: Add tests for GET /documents/{doc_id}, GET /documents/ etc. if they exist
# Ensure all tests in this file use the appropriate client (test_client vs integration_test_client)
# and handle mocking correctly based on whether lifespan events are required.