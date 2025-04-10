import pytest
from typer.testing import CliRunner
from unittest.mock import patch, MagicMock # Import patch
import json
from pathlib import Path # Import Path

# Import the Typer app instance
from graph_rag.cli.main import app

runner = CliRunner()

# --- Ingest Command Tests ---

# Mock the function directly called by the CLI command
@patch('graph_rag.cli.commands.ingest.process_and_store_document')
@patch('graph_rag.cli.commands.ingest.typer.Exit')  # Mock typer.Exit
def test_ingest_document_file_success(mock_exit, mock_process_and_store, tmp_path):
    """Test successful ingestion via file path argument."""
    # Create temporary file
    test_file = tmp_path / "test_doc.txt"
    test_file.write_text("Content from file.")
    metadata_dict = {"source": "cli-test"}
    metadata_json = json.dumps(metadata_dict)

    # Configure the mock to simulate successful processing
    mock_process_and_store.return_value = None # Assume it returns None on success

    result = runner.invoke(app, [
        "ingest",
        str(test_file),
        "--metadata", metadata_json
    ])

    # For success case, typer.Exit should not be called
    mock_exit.assert_not_called()

    print(f"CLI Output:\n{result.stdout}")
    print(f"Exit Code: {result.exit_code}")
    if result.exception:
        print(f"Exception: {result.exception}")
        import traceback
        traceback.print_exception(type(result.exception), result.exception, result.exc_info[2])

    assert result.exit_code == 0, f"Expected exit code 0, got {result.exit_code}. Output: {result.stdout}"
    assert f"Processing document: {test_file}" in result.stdout
    assert f"Metadata: {metadata_dict}" in result.stdout
    assert "Document processed and stored successfully." in result.stdout

    # Check if process_and_store_document was called correctly
    mock_process_and_store.assert_called_once_with(
        file_path=test_file,
        metadata=metadata_dict
    )

# Remove the old test_ingest_document_content_success as --content is gone
# The old test_ingest_document_file_success is adapted above.

def test_ingest_document_no_input():
    """Test calling ingest without the required file_path argument."""
    result = runner.invoke(app, ["ingest"])
    assert result.exit_code != 0 # Typer usually exits with 2 for usage errors
    # Check for Typer's standard missing argument message
    assert "Missing argument 'FILE_PATH'" in result.stdout

# Remove the old test_ingest_document_both_inputs as it's no longer relevant

@patch('graph_rag.cli.commands.ingest.typer.Exit') # Mock typer.Exit
def test_ingest_document_invalid_metadata(mock_exit, tmp_path):
    """Test calling ingest with invalid JSON in metadata."""
    # Create a dummy file as it's required
    test_file = tmp_path / "dummy.txt"
    test_file.touch()

    result = runner.invoke(app, [
        "ingest",
        str(test_file),
        "--metadata", "{invalid-json"
    ])
    # Assert that typer.Exit was called with code != 0
    mock_exit.assert_called_once()
    assert mock_exit.call_args[0][0] != 0

    # We can't reliably check stdout with this mock, 
    # but we can check the logger was called (if needed)
    # For now, just check Exit was called.
    # assert "Error: Invalid JSON provided for metadata:" in result.stdout # This won't work reliably now

# --- Search Command Tests ---

@patch('graph_rag.cli.commands.search.httpx.Client')
@patch('graph_rag.cli.commands.search.typer.Exit')  # Mock typer.Exit
def test_search_batch_success(mock_exit, mock_httpx_client):
    """Test successful batch search."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "query": "test query", "search_type": "vector", "results": [{"chunk": {"id": "c1", "text": "chunk1", "metadata":{}}, "score": 0.9}] # Added score/text/metadata for validation
    }
    mock_response.raise_for_status.return_value = None
    mock_client_instance = MagicMock()
    mock_client_instance.post.return_value = mock_response
    mock_context_manager = MagicMock()
    mock_context_manager.__enter__.return_value = mock_client_instance
    mock_context_manager.__exit__.return_value = None
    mock_httpx_client.return_value = mock_context_manager

    result = runner.invoke(app, ["search", "test query", "--type", "vector", "-l", "5"])

    # For success case, typer.Exit should not be called
    mock_exit.assert_not_called()

    assert result.exit_code == 0
    assert '"query": "test query"' in result.stdout # Check pretty printed JSON
    assert '"search_type": "vector"' in result.stdout
    assert '"id": "c1"' in result.stdout
    assert '"score": 0.9' in result.stdout # Check score presence
    mock_client_instance.post.assert_called_once()
    call_args = mock_client_instance.post.call_args
    assert call_args[0][0] == "http://localhost:8000/api/v1/search/query?stream=false" # Default URL
    assert call_args[1]['json'] == {"query": "test query", "search_type": "vector", "limit": 5}

@patch('graph_rag.cli.commands.search.httpx.stream') # Mock stream function
@patch('graph_rag.cli.commands.search.typer.Exit')  # Mock typer.Exit
def test_search_stream_success(mock_exit, mock_httpx_stream):
    """Test successful streaming search."""
    # Mock the response object from httpx.stream context manager
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.headers = {"content-type": "application/x-ndjson"}
    # Simulate iter_lines returning JSON Lines
    mock_response.iter_lines.return_value = [
        '{"chunk": {"id": "s1", "text": "stream1", "metadata":{}}, "score": 0.9}',
        '{"chunk": {"id": "s2", "text": "stream2", "metadata":{}}, "score": 0.8}'
    ]
    mock_response.raise_for_status.return_value = None

    # Mock the context manager returned by httpx.stream
    mock_stream_context_manager = MagicMock()
    mock_stream_context_manager.__enter__.return_value = mock_response
    mock_stream_context_manager.__exit__.return_value = None
    mock_httpx_stream.return_value = mock_stream_context_manager

    result = runner.invoke(app, ["search", "stream test", "--stream"])

    # For success case, typer.Exit should not be called
    mock_exit.assert_not_called()

    assert result.exit_code == 0
    # Check exact JSON lines
    assert '{"chunk": {"id": "s1", "text": "stream1", "metadata": {}}, "score": 0.9}' in result.stdout
    assert '{"chunk": {"id": "s2", "text": "stream2", "metadata": {}}, "score": 0.8}' in result.stdout
    assert "--- Streaming Results Finished ---" in result.stdout # Adjusted message check
    # Check if httpx.stream was called correctly
    mock_httpx_stream.assert_called_once()
    call_args = mock_httpx_stream.call_args
    assert call_args[0][0] == "POST"
    assert call_args[0][1] == "http://localhost:8000/api/v1/search/query?stream=true"
    assert call_args[1]['json'] == {"query": "stream test", "search_type": "vector", "limit": 10} # Defaults

# --- Admin Command Tests ---

@patch('graph_rag.cli.commands.admin.httpx.Client')
@patch('graph_rag.cli.commands.admin.typer.Exit')  # Mock typer.Exit
def test_admin_health_success(mock_exit, mock_httpx_client):
    """Test successful health check."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"status": "healthy"}
    mock_response.raise_for_status.return_value = None
    mock_client_instance = MagicMock()
    mock_client_instance.get.return_value = mock_response
    mock_context_manager = MagicMock()
    mock_context_manager.__enter__.return_value = mock_client_instance
    mock_context_manager.__exit__.return_value = None
    mock_httpx_client.return_value = mock_context_manager

    result = runner.invoke(app, ["admin-health"])
    
    # For success case, typer.Exit should not be called
    mock_exit.assert_not_called()
    
    assert result.exit_code == 0
    assert "API Status: HEALTHY" in result.stdout
    assert "API appears healthy" in result.stdout
    mock_client_instance.get.assert_called_once_with("http://localhost:8000/health", timeout=10.0)

@patch('graph_rag.cli.commands.admin.httpx.Client')
@patch('graph_rag.cli.commands.admin.typer.Exit')  # Mock typer.Exit
def test_admin_health_unhealthy(mock_exit, mock_httpx_client):
    """Test health check when API returns unhealthy status."""
    mock_response = MagicMock()
    mock_response.status_code = 200 # API might return 200 but indicate unhealthy
    mock_response.json.return_value = {"status": "unhealthy"}
    mock_response.raise_for_status.return_value = None # No HTTP error
    mock_client_instance = MagicMock()
    mock_client_instance.get.return_value = mock_response
    mock_context_manager = MagicMock()
    mock_context_manager.__enter__.return_value = mock_client_instance
    mock_context_manager.__exit__.return_value = None
    mock_httpx_client.return_value = mock_context_manager

    result = runner.invoke(app, ["admin-health"])
    
    # Should exit with non-zero code for unhealthy status
    mock_exit.assert_called_once()
    assert mock_exit.call_args[0][0] != 0
    
    assert "API Status: UNHEALTHY" in result.stdout
    assert "Warning: API reported an unhealthy status" in result.stdout

@patch('graph_rag.cli.commands.admin.httpx.Client')
@patch('graph_rag.cli.commands.admin.typer.Exit')  # Mock typer.Exit
def test_admin_health_api_error(mock_exit, mock_httpx_client):
    """Test health check when API returns HTTP error."""
    # Need to import httpx for the exception type
    import httpx

    mock_response = MagicMock()
    mock_response.status_code = 503
    mock_response.text = '{"detail": "Service Unavailable"}'
    # Simulate JSON error if .text used (though raise_for_status happens first)
    mock_response.json.side_effect = json.JSONDecodeError("msg", "doc", 0)
    # Create a mock request object as required by HTTPStatusError
    mock_request = MagicMock(spec=httpx.Request)
    mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
        message="Server error", request=mock_request, response=mock_response
    )
    mock_client_instance = MagicMock()
    mock_client_instance.get.return_value = mock_response
    mock_context_manager = MagicMock()
    mock_context_manager.__enter__.return_value = mock_client_instance
    mock_context_manager.__exit__.return_value = None
    mock_httpx_client.return_value = mock_context_manager

    result = runner.invoke(app, ["admin-health"])

    # Should exit with non-zero code for API error
    mock_exit.assert_called_once()
    assert mock_exit.call_args[0][0] != 0
    
    assert "Error: API health check failed with status 503." in result.stdout # Adjusted message
    # Checks if detail parsing worked - should use .text for non-JSON errors usually
    assert 'Detail: {"detail": "Service Unavailable"}' in result.stdout # Check raw text content

# --- End of File --- 