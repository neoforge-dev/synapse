import uuid  # Import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock

import pytest
from fastapi import status
from httpx import AsyncClient

# Import schemas needed for assertions/mocking response structure
# from graph_rag.api.main import app # Import app for client -- No longer needed
from graph_rag.domain.models import Entity  # Import Entity for mocking

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
EXPECTED_MERGED_METADATA.update(
    UPDATED_METADATA
)  # {"source": "patched", "topic": "initial", "status": "complete"}

# Dummy node data for get_entity_by_id mock (as Entity)
DUMMY_ENTITY_DATA = Entity(
    id=DOC_ID_TO_UPDATE, type="Document", properties=BASE_METADATA
)

DUMMY_ENTITY_DATA_REPO_ERROR = Entity(  # For the repo error test case
    id=DOC_ID_REPO_ERROR,
    type="Document",
    properties={"some_key": "some_value"},  # Give it some initial properties
)

# Expected updated entity after successful patch (used for second get_entity_by_id mock)
EXPECTED_UPDATED_ENTITY_AFTER_PATCH = Entity(
    id=DOC_ID_TO_UPDATE, type="Document", properties=EXPECTED_MERGED_METADATA
)


@pytest.mark.asyncio
async def test_delete_document_endpoint_success(
    test_client: AsyncClient,  # Changed from integration_test_client
    mock_graph_repo: AsyncMock,  # Need mock repo now
):
    """Tests successful deletion of a document via the API endpoint."""

    # Generate a unique ID for this test run
    doc_id_to_delete = f"test-delete-{uuid.uuid4()}"

    # Mock repository response for deletion
    mock_graph_repo.delete_document.reset_mock()
    mock_graph_repo.delete_document.return_value = True  # Simulate successful delete

    # --- Step 1: Delete the document using the mocked client ---
    response = await test_client.delete(f"/api/v1/documents/{doc_id_to_delete}")

    # Assertions for successful deletion
    assert response.status_code == status.HTTP_204_NO_CONTENT, (
        f"Expected 204, got {response.status_code}, response: {response.text}"
    )
    mock_graph_repo.delete_document.assert_awaited_once_with(doc_id_to_delete)


@pytest.mark.asyncio
async def test_delete_document_endpoint_not_found(
    test_client: AsyncClient,  # Changed from integration_test_client
    mock_graph_repo: AsyncMock,
):
    """Tests attempting to delete a non-existent document via the API endpoint."""

    # Configure mock to simulate document not found in the repository layer
    mock_graph_repo.delete_document.reset_mock()
    mock_graph_repo.delete_document.return_value = (
        False  # Simulate repo returning False
    )

    # --- Step 1: Attempt to delete a non-existent document ---
    # Use a unique ID guaranteed not to exist (or verify it doesn't exist)
    doc_id_not_found = f"test-non-existent-{uuid.uuid4()}"

    # Make the DELETE request
    response = await test_client.delete(f"/api/v1/documents/{doc_id_not_found}")

    # Assertions
    # The endpoint logic should catch the `False` from the repo and return 404
    assert response.status_code == status.HTTP_404_NOT_FOUND, (
        f"Expected 404, got {response.status_code}"
    )
    # Verify the mock was called as expected
    mock_graph_repo.delete_document.assert_awaited_once_with(doc_id_not_found)
    # Check response detail if available
    # assert response.json() == {"detail": f"Document with id {doc_id_not_found} not found"} # Adjust based on actual response


@pytest.mark.asyncio
async def test_delete_document_endpoint_repository_error(
    test_client: AsyncClient,  # Changed from integration_test_client
    mock_graph_repo: AsyncMock,
):
    """Test error handling when the repository fails during deletion."""

    # Generate a unique ID for this test run
    doc_id_repo_error = f"test-repo-error-{uuid.uuid4()}"

    # Configure the mock to raise an exception during deletion
    mock_graph_repo.delete_document.reset_mock()
    mock_graph_repo.delete_document.side_effect = Exception(
        "Simulated DB error during delete"
    )

    # --- Step 1: Attempt to delete, expecting repository error ---
    response = await test_client.delete(f"/api/v1/documents/{doc_id_repo_error}")

    # Assertions
    assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR, (
        f"Expected 500, got {response.status_code}"
    )
    assert "detail" in response.json()
    # Check if the detail message indicates the failure reason
    assert "Failed to delete document" in response.json()["detail"], (
        f"Unexpected error detail: {response.json()['detail']}"
    )
    # Verify the mock was called
    mock_graph_repo.delete_document.assert_awaited_once_with(doc_id_repo_error)


@pytest.mark.asyncio
async def test_patch_document_metadata_success(
    test_client: AsyncClient, mock_graph_repo: AsyncMock
):
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
    mock_graph_repo.add_entity.return_value = (
        None  # add_entity doesn't return anything significant
    )

    mock_graph_repo.reset_mock()  # Reset calls, not side effects
    # Re-apply side effects after reset_mock
    mock_graph_repo.get_entity_by_id.side_effect = mock_get_entity
    mock_graph_repo.add_entity.return_value = None

    response = await test_client.patch(
        f"/api/v1/documents/{DOC_ID_TO_UPDATE}/metadata",
        json={"properties": UPDATED_METADATA},  # Schema expects {"properties": {...}}
    )

    # Debugging output
    print(f"Response Status: {response.status_code}")
    print(f"Response JSON: {response.text}")
    print(f"get_entity_by_id calls: {mock_graph_repo.get_entity_by_id.call_args_list}")
    print(f"add_entity calls: {mock_graph_repo.add_entity.call_args_list}")
    # Check response
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["id"] == DOC_ID_TO_UPDATE
    # Check that the final returned metadata matches the fully merged dictionary
    assert response.json()["metadata"] == EXPECTED_MERGED_METADATA
    # Verify mocks
    mock_graph_repo.get_entity_by_id.assert_awaited_once_with(DOC_ID_TO_UPDATE)
    # The endpoint calls add_entity with the merged properties
    expected_call_entity = Entity(
        id=DOC_ID_TO_UPDATE,
        type="Document",  # Assume type remains constant
        properties=EXPECTED_MERGED_METADATA,
    )
    mock_graph_repo.add_entity.assert_awaited_once_with(expected_call_entity)


@pytest.mark.asyncio
async def test_patch_document_no_body(
    test_client: AsyncClient, mock_graph_repo: AsyncMock
):
    """Test PATCH endpoint when no request body is provided."""
    response = await test_client.patch(
        f"/api/v1/documents/{DOC_ID_TO_UPDATE}/metadata", json=None
    )
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    mock_graph_repo.get_entity_by_id.assert_not_awaited()
    mock_graph_repo.add_entity.assert_not_awaited()


@pytest.mark.asyncio
async def test_patch_document_invalid_field(
    test_client: AsyncClient, mock_graph_repo: AsyncMock
):
    """Test PATCH endpoint when the request body has an invalid structure."""
    response = await test_client.patch(
        f"/api/v1/documents/{DOC_ID_TO_UPDATE}/metadata",
        json={"invalid_key": {"a": 1}},  # Does not match expected {"properties": {...}}
    )
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    mock_graph_repo.get_entity_by_id.assert_not_awaited()
    mock_graph_repo.add_entity.assert_not_awaited()


@pytest.mark.asyncio
async def test_patch_document_not_found(
    test_client: AsyncClient, mock_graph_repo: AsyncMock
):
    """Test PATCH endpoint when the document ID does not exist."""

    async def mock_get_entity(entity_id):
        if entity_id == DOC_ID_UPDATE_NOT_FOUND:
            return None  # Simulate document not found
        return DUMMY_ENTITY_DATA  # Default for other calls if any

    mock_graph_repo.get_entity_by_id.side_effect = mock_get_entity
    mock_graph_repo.reset_mock()
    mock_graph_repo.get_entity_by_id.side_effect = mock_get_entity

    response = await test_client.patch(
        f"/api/v1/documents/{DOC_ID_UPDATE_NOT_FOUND}/metadata",
        json={"properties": {"status": "new"}},
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND
    response_json = response.json()
    assert (
        response_json.get("detail")
        == f"Document with id '{DOC_ID_UPDATE_NOT_FOUND}' not found"
    )
    assert "request_id" in response_json  # Optionally assert presence

    # Verify mocks were called as expected
    mock_graph_repo.get_entity_by_id.assert_awaited_once_with(DOC_ID_UPDATE_NOT_FOUND)


@pytest.mark.asyncio
async def test_patch_document_repository_error(
    test_client: AsyncClient, mock_graph_repo: AsyncMock
):
    """Test PATCH endpoint error handling when the repository fails during update."""

    async def mock_get_entity(entity_id):
        if entity_id == DOC_ID_REPO_ERROR:
            return DUMMY_ENTITY_DATA_REPO_ERROR  # Return the initial entity
        return None

    mock_graph_repo.get_entity_by_id.side_effect = mock_get_entity

    # Mock add_entity to raise an exception
    mock_graph_repo.add_entity.side_effect = Exception("DB error on update")

    mock_graph_repo.reset_mock()
    mock_graph_repo.get_entity_by_id.side_effect = mock_get_entity
    mock_graph_repo.add_entity.side_effect = Exception("DB error on update")

    response = await test_client.patch(
        f"/api/v1/documents/{DOC_ID_REPO_ERROR}/metadata",
        json={"properties": {"source": "patch-attempt"}},
    )

    assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
    # assert response.json() == {"detail": "Failed to update document metadata"} # Ignore request_id
    response_json = response.json()
    assert response_json.get("detail") == "Failed to update document metadata"
    assert "request_id" in response_json  # Optionally assert presence

    # Verify mocks were called
    mock_graph_repo.get_entity_by_id.assert_awaited_once_with(DOC_ID_REPO_ERROR)


@pytest.mark.asyncio
async def test_create_document_endpoint(
    test_client: AsyncClient,  # Changed from integration_test_client
    mock_graph_repo: AsyncMock,
):
    """Tests successful document creation via the API endpoint using mocks."""
    doc_payload = {
        "id": f"test-doc-{uuid.uuid4()}",
        "content": "This is the content of the test document.",
        "metadata": {"source": "test_suite", "type": "creation_test"},
    }

    # Ensure the GraphRepository mock has a clean state
    mock_graph_repo.add_entity.reset_mock()
    mock_graph_repo.add_entity.side_effect = None
    mock_graph_repo.add_entity.return_value = None  # Ensure it returns normally

    response = await test_client.post("/api/v1/documents", json=doc_payload)

    assert response.status_code == status.HTTP_201_CREATED, (
        f"Expected 201, got {response.status_code}, Response: {response.text}"
    )
    response_data = response.json()
    assert response_data["id"] == doc_payload["id"]

    # Verify the repository was called to add the entity
    mock_graph_repo.add_entity.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_document_endpoint_success(
    test_client: AsyncClient,
    mock_graph_repo: AsyncMock,  # Need mock repo
):
    """Tests successful retrieval of a document by ID via the API endpoint."""

    # Generate a unique ID for this test run
    doc_id_to_get = f"test-get-{uuid.uuid4()}"

    # Create a mock Entity that represents a Document node in the graph
    now_utc = datetime.now(timezone.utc)
    mock_document_entity = Entity(
        id=doc_id_to_get,
        type="Document",
        properties={
            "metadata": {"source": "test_get"},
            "created_at": now_utc.isoformat(),  # Include timestamps if API returns them
            "updated_at": now_utc.isoformat(),
            # Include other relevant document properties from schema if necessary
        },
    )

    # Configure mock repository to return the mock entity
    mock_graph_repo.get_entity_by_id.reset_mock()  # Ensure a clean mock state for this specific method
    mock_graph_repo.get_entity_by_id.return_value = (
        mock_document_entity  # Set the return value AFTER resetting
    )

    # --- Step 1: Get the document using the mocked client ---
    response = await test_client.get(f"/api/v1/documents/{doc_id_to_get}")

    # Assertions for successful retrieval
    assert response.status_code == status.HTTP_200_OK, (
        f"Expected 200, got {response.status_code}, response: {response.text}"
    )

    response_data = response.json()

    # Construct the expected response data based on the DocumentResponse schema
    # DocumentResponse has: id, metadata, type, created_at, updated_at (no content field)
    # Convert date strings to datetime objects for reliable comparison
    expected_created_at = (
        datetime.fromisoformat(
            mock_document_entity.properties.get("created_at").replace("Z", "+00:00")
        )
        if mock_document_entity.properties.get("created_at")
        else None
    )
    expected_updated_at = (
        datetime.fromisoformat(
            mock_document_entity.properties.get("updated_at").replace("Z", "+00:00")
        )
        if mock_document_entity.properties.get("updated_at")
        else None
    )

    assert response_data["id"] == mock_document_entity.id
    assert response_data["metadata"] == mock_document_entity.properties.get("metadata")
    assert response_data["type"] == mock_document_entity.type

    # Compare datetime objects after parsing from response
    response_created_at = (
        datetime.fromisoformat(response_data["created_at"].replace("Z", "+00:00"))
        if response_data.get("created_at")
        else None
    )
    response_updated_at = (
        datetime.fromisoformat(response_data["updated_at"].replace("Z", "+00:00"))
        if response_data.get("updated_at")
        else None
    )

    assert response_created_at == expected_created_at
    assert response_updated_at == expected_updated_at

    # Verify mock was called
    mock_graph_repo.get_entity_by_id.assert_awaited_once_with(doc_id_to_get)


@pytest.mark.asyncio
async def test_get_document_endpoint_not_found(
    test_client: AsyncClient, mock_graph_repo: AsyncMock
):
    """Tests retrieving a non-existent document by ID via the API endpoint."""

    # Generate a unique ID guaranteed not to exist
    doc_id_not_found_get = f"test-get-not-found-{uuid.uuid4()}"

    # Configure mock repository to return None (document not found)
    mock_graph_repo.get_entity_by_id.reset_mock()
    mock_graph_repo.get_entity_by_id.return_value = None

    # --- Step 1: Attempt to get a non-existent document ---
    response = await test_client.get(f"/api/v1/documents/{doc_id_not_found_get}")

    # Assertions
    assert response.status_code == status.HTTP_404_NOT_FOUND, (
        f"Expected 404, got {response.status_code}"
    )

    # Check response detail if available
    response_json = response.json()
    assert "detail" in response_json
    assert (
        f"Document with id '{doc_id_not_found_get}' not found"
        in response_json["detail"]
    )

    # Verify mock was called
    mock_graph_repo.get_entity_by_id.assert_awaited_once_with(doc_id_not_found_get)


# TODO: Add tests for GET /documents/{doc_id}, GET /documents/ etc. if they exist
# Ensure all tests in this file use the appropriate client (test_client vs integration_test_client)
# and handle mocking correctly based on whether lifespan events are required.


# Add tests for GET /api/v1/documents/ (List Documents)
@pytest.mark.asyncio
async def test_list_documents_endpoint_success(
    test_client: AsyncClient,
    mock_graph_repo: AsyncMock,  # Need mock repo
):
    """Tests successful retrieval of a list of documents via the API endpoint."""

    # Create mock Entity objects representing Document nodes
    doc1_id = f"list-doc-{uuid.uuid4()}-1"
    doc2_id = f"list-doc-{uuid.uuid4()}-2"

    # Use datetime.now(timezone.utc) and then format with .isoformat() for consistency
    now_utc = datetime.now(timezone.utc)

    mock_document_entity_1 = Entity(
        id=doc1_id,
        type="Document",
        properties={
            "metadata": {"source": "test_list", "order": 1},
            "created_at": now_utc.isoformat(),
            "updated_at": now_utc.isoformat(),
        },
    )
    mock_document_entity_2 = Entity(
        id=doc2_id,
        type="Document",
        properties={
            "metadata": {"source": "test_list", "order": 2},
            "created_at": now_utc.isoformat(),
            "updated_at": now_utc.isoformat(),
        },
    )
    mock_document_list = [mock_document_entity_1, mock_document_entity_2]

    # Configure mock repository to return the list of mock entities
    mock_graph_repo.search_entities_by_properties.reset_mock()  # Use the correct method name
    mock_graph_repo.search_entities_by_properties.return_value = mock_document_list

    # --- Step 1: Get the list of documents using the mocked client ---
    response = await test_client.get("/api/v1/documents")

    # Assertions for successful retrieval
    assert response.status_code == status.HTTP_200_OK, (
        f"Expected 200, got {response.status_code}, response: {response.text}"
    )

    response_data = response.json()

    # Assert that the response is a list of the correct length
    assert isinstance(response_data, list)
    assert len(response_data) == len(mock_document_list)

    # Construct the expected response data based on the DocumentResponse schema for each entity
    # DocumentResponse has: id, metadata, type, created_at, updated_at (no content field)
    expected_response_data = [
        {
            "id": doc.id,
            "metadata": doc.properties.get("metadata"),
            "type": doc.type,
            "created_at": doc.properties.get(
                "created_at"
            ),  # Keep as string for parsing below
            "updated_at": doc.properties.get(
                "updated_at"
            ),  # Keep as string for parsing below
        }
        for doc in mock_document_list
    ]

    # Compare the received list with the expected list (order might matter depending on API impl)
    # Assuming order doesn't strictly matter for a basic list endpoint, compare sets or sort lists
    # Let's sort by ID for consistent comparison
    # assert sorted(response_data, key=lambda x: x["id"]) == sorted(expected_response_data, key=lambda x: x["id"]) # Old direct comparison

    # Compare element by element, parsing dates for reliable comparison
    assert len(response_data) == len(expected_response_data)

    # Sort both lists by ID for consistent comparison
    sorted_response_data = sorted(response_data, key=lambda x: x["id"])
    sorted_expected_data = sorted(expected_response_data, key=lambda x: x["id"])

    for i in range(len(sorted_response_data)):
        response_item = sorted_response_data[i]
        expected_item = sorted_expected_data[i]

        assert response_item["id"] == expected_item["id"]
        assert response_item["metadata"] == expected_item["metadata"]
        assert response_item["type"] == expected_item["type"]

        # Parse dates before comparison
        response_created_at = (
            datetime.fromisoformat(response_item["created_at"].replace("Z", "+00:00"))
            if response_item.get("created_at")
            else None
        )
        expected_created_at = (
            datetime.fromisoformat(expected_item["created_at"].replace("Z", "+00:00"))
            if expected_item.get("created_at")
            else None
        )
        assert response_created_at == expected_created_at

        response_updated_at = (
            datetime.fromisoformat(response_item["updated_at"].replace("Z", "+00:00"))
            if response_item.get("updated_at")
            else None
        )
        expected_updated_at = (
            datetime.fromisoformat(expected_item["updated_at"].replace("Z", "+00:00"))
            if expected_item.get("updated_at")
            else None
        )
        assert response_updated_at == expected_updated_at

    # Verify mock was called with the correct parameters
    mock_graph_repo.search_entities_by_properties.assert_awaited_once_with(
        {"type": "Document"}, limit=100
    )


@pytest.mark.asyncio
async def test_list_documents_endpoint_no_results(
    test_client: AsyncClient,
    mock_graph_repo: AsyncMock,  # Need mock repo
):
    """Tests retrieval of an empty list when no documents exist."""

    # Configure mock repository to return an empty list
    mock_graph_repo.search_entities_by_properties.reset_mock()
    mock_graph_repo.search_entities_by_properties.return_value = []

    # --- Step 1: Get the list of documents ---
    response = await test_client.get("/api/v1/documents")

    # Assertions
    assert response.status_code == status.HTTP_200_OK, (
        f"Expected 200, got {response.status_code}"
    )

    response_data = response.json()

    # Assert that the response is an empty list
    assert isinstance(response_data, list)
    assert len(response_data) == 0
    assert response_data == []

    # Verify mock was called
    mock_graph_repo.search_entities_by_properties.assert_awaited_once_with(
        {"type": "Document"}, limit=100
    )


@pytest.mark.asyncio
async def test_list_documents_endpoint_repository_error(
    test_client: AsyncClient,
    mock_graph_repo: AsyncMock,  # Need mock repo
):
    """Tests error handling when the repository fails during document list retrieval."""

    # Configure mock repository to raise an exception
    repository_error = RuntimeError("Simulated repository error during list")
    mock_graph_repo.search_entities_by_properties.reset_mock()
    mock_graph_repo.search_entities_by_properties.side_effect = repository_error

    # --- Step 1: Attempt to get the list of documents, expecting repository error ---
    response = await test_client.get("/api/v1/documents")

    # Assertions
    assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR, (
        f"Expected 500, got {response.status_code}"
    )

    response_json = response.json()
    assert "detail" in response_json
    # Check if the detail message indicates a failure (specific error message might vary)
    assert "Failed to retrieve documents" in response_json["detail"]

    # Verify mock was called
    mock_graph_repo.search_entities_by_properties.assert_awaited_once_with(
        {"type": "Document"}, limit=100
    )


@pytest.mark.asyncio
async def test_create_document_endpoint_invalid_input(test_client: AsyncClient):
    """Tests document creation via API fails with invalid input (e.g., missing content)."""
    # Invalid payload: missing 'content'
    invalid_payload = {
        "id": f"test-invalid-{uuid.uuid4()}",
        "metadata": {"source": "test_suite"},
        # 'content' is missing
    }

    response = await test_client.post("/api/v1/documents", json=invalid_payload)

    # Assertions
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY, (
        f"Expected 422, got {response.status_code}, Response: {response.text}"
    )

    response_data = response.json()
    assert "detail" in response_data
    assert isinstance(response_data["detail"], list)
    assert len(response_data["detail"]) > 0

    # Check for specific validation error message/location if possible
    error_detail = response_data["detail"][0]
    assert error_detail.get("loc") == ["body", "content"]
    assert "Field required" in error_detail.get("msg")


@pytest.mark.asyncio
async def test_create_document_endpoint_repository_error(
    test_client: AsyncClient, mock_graph_repo: AsyncMock
):
    """Tests document creation via API handles errors from the graph repository."""
    valid_payload = {
        "id": f"test-repo-error-{uuid.uuid4()}",
        "content": "Content for repository error test.",
        "metadata": {"source": "test_suite", "type": "repository_error_test"},
    }

    # Configure mock repository to raise an exception
    repository_error = RuntimeError("Simulated repository failure")
    mock_graph_repo.add_entity.reset_mock()
    mock_graph_repo.add_entity.side_effect = repository_error

    response = await test_client.post("/api/v1/documents", json=valid_payload)

    # Assertions
    assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR, (
        f"Expected 500, got {response.status_code}, Response: {response.text}"
    )

    response_data = response.json()
    assert "detail" in response_data
    assert "Failed to add document" in response_data["detail"]

    # Verify the mock was called
    mock_graph_repo.add_entity.assert_awaited_once()
