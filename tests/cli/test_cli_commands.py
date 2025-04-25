import pytest
from typer.testing import CliRunner
from unittest.mock import patch, MagicMock # Import patch
import json
from pathlib import Path # Import Path
from unittest.mock import AsyncMock

# Import the Typer app instance
from graph_rag.cli.main import app

runner = CliRunner()

# --- Ingest Command Tests ---

# Mock the function directly called by the CLI command
@patch("graph_rag.cli.commands.ingest.process_and_store_document", new_callable=AsyncMock)
@patch("graph_rag.cli.commands.ingest.SimpleDocumentProcessor")
@patch("graph_rag.cli.commands.ingest.SpacyEntityExtractor")
@patch("graph_rag.cli.commands.ingest.MemgraphGraphRepository")  # Corrected class name
@patch('graph_rag.cli.commands.ingest.typer.echo') # Mock echo to check output
def test_ingest_document_file_success(
    mock_echo,
    mock_repo,
    mock_extractor,
    mock_processor,
    mock_process_and_store,
    tmp_path
):
    """Test successful ingestion via file path argument using CliRunner."""
    # Create temporary file
    test_file = tmp_path / "test_doc.txt"
    test_file.write_text("Content from file.")
    metadata_dict = {"source": "cli-test"}
    metadata_json = json.dumps(metadata_dict)

    # Configure the mock IngestionResult object
    mock_result = MagicMock()
    mock_result.document_id = str(test_file)
    mock_result.num_chunks = 5
    mock_process_and_store.return_value = mock_result

    # Run the command using CliRunner
    result = runner.invoke(
        app,
        [
            "ingest",
            str(test_file), # Pass path as string argument
            "--metadata",
            metadata_json,
        ],
    )

    # Print result for debugging
    print(f"CLI Runner Result (Success Test):\nExit Code: {result.exit_code}\nOutput:\n{result.stdout}\nException:\n{result.exception}")

    # Verify mocks were called as expected
    assert result.exit_code == 0, f"CLI command failed unexpectedly: {result.stdout}"
    mock_process_and_store.assert_called_once()

    # Check arguments passed to process_and_store_document
    call_args, call_kwargs = mock_process_and_store.call_args
    assert isinstance(call_args[0], Path) and str(call_args[0]) == str(test_file)
    assert call_args[1] == metadata_dict

    # Check output message
    mock_echo.assert_called_with(f"Successfully processed and stored {test_file} including graph links.")

    # Mock exit should not be called in success case
    # mock_exit is removed

def test_ingest_document_no_input():
    """Test calling ingest without the required file_path argument."""
    result = runner.invoke(app, ["ingest"])
    assert result.exit_code != 0 # Typer usually exits with 2 for usage errors
    # Check for Typer's standard missing argument message
    assert "Missing argument 'FILE_PATH'" in result.stdout

# Remove the old test_ingest_document_both_inputs as it's no longer relevant

@patch("graph_rag.cli.commands.ingest.process_and_store_document", new_callable=AsyncMock)
@patch('graph_rag.cli.commands.ingest.typer.echo') # Mock echo to check error output
def test_ingest_document_invalid_metadata(mock_echo, mock_process_and_store, tmp_path):
    """Test calling ingest with invalid JSON in metadata using CliRunner."""
    # Create a dummy file as it's required
    test_file = tmp_path / "dummy.txt"
    test_file.touch()
    invalid_metadata = "{invalid-json"

    # Run the command using CliRunner
    result = runner.invoke(
        app,
        [
            "ingest",
            str(test_file),
            "--metadata",
            invalid_metadata,
        ],
    )

    # Print result for debugging
    print(f"CLI Runner Result (Invalid Metadata Test):\nExit Code: {result.exit_code}\nOutput:\n{result.stdout}\nException:\n{result.exception}")

    # Check exit code and error message
    assert result.exit_code != 0, "Command should have failed with invalid JSON"
    mock_echo.assert_any_call("Error: Invalid JSON in metadata")
    # process_and_store should not be called if metadata parsing fails
    mock_process_and_store.assert_not_called()

# --- Search Command Tests ---

@patch('graph_rag.cli.commands.search.HTTPClient')
@patch('graph_rag.cli.commands.search.typer.echo') # Mock echo for output check
def test_search_batch_success(mock_echo, mock_httpx_client):
    """Test successful batch search using CliRunner."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "query": "test query", "search_type": "vector", "results": [{"chunk": {"id": "c1", "text": "chunk1", "metadata":{}}, "score": 0.9}]
    }
    mock_response.raise_for_status.return_value = None
    mock_client_instance = MagicMock()
    mock_client_instance.post.return_value = mock_response
    mock_context_manager = MagicMock()
    mock_context_manager.__enter__.return_value = mock_client_instance
    mock_context_manager.__exit__.return_value = None
    mock_httpx_client.return_value = mock_context_manager

    # Use CliRunner to invoke the search command
    result = runner.invoke(
        app,
        [
            "search",
            "test query",
            "--type",
            "vector",
            "--limit",
            "5"
            # Use default API URL from the command definition
        ]
    )

    # Print result for debugging
    print(f"CLI Runner Result (Search Batch Success Test):\nExit Code: {result.exit_code}\nOutput:\n{result.stdout}\nException:\n{result.exception}")

    # Verify expected behavior
    assert result.exit_code == 0, f"CLI command failed unexpectedly: {result.stdout}"
    mock_client_instance.post.assert_called_once()
    call_args, call_kwargs = mock_client_instance.post.call_args
    # Check URL and payload
    assert call_args[0].startswith("http://localhost:8000/api/v1/search/query")
    assert "stream=false" in call_args[0]
    expected_payload = {"query": "test query", "search_type": "vector", "limit": 5}
    assert call_kwargs["json"] == expected_payload
    # Check that the JSON output was printed (mocking typer.echo or print needed)
    # Instead of mocking print, we check stdout contains the expected JSON structure
    assert '"query": "test query"' in result.stdout
    assert '"results":' in result.stdout

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

    # Use CliRunner to invoke the search command
    result = runner.invoke(
        app,
        [
            "search",
            "stream test",
            "--type",
            "vector",
            "--limit",
            "10",
            "--stream" # Add the stream flag
        ]
    )

    # Print result for debugging
    print(f"CLI Runner Result (Search Stream Success Test):\nExit Code: {result.exit_code}\nOutput:\n{result.stdout}\nException:\n{result.exception}")

    # Verify expected behavior
    assert result.exit_code == 0, f"CLI command failed unexpectedly: {result.stdout}"
    mock_exit.assert_not_called()
    mock_httpx_stream.assert_called_once()
    call_args, call_kwargs = mock_httpx_stream.call_args
    # Check URL and payload
    assert call_args[0] == "POST"
    assert call_args[1].startswith("http://localhost:8000/api/v1/search/query")
    assert "stream=true" in call_args[1]
    expected_payload = {"query": "stream test", "search_type": "vector", "limit": 10}
    assert call_kwargs["json"] == expected_payload
    # Check stdout contains the streamed lines
    assert '{"chunk": {"id": "s1", "text": "stream1"' in result.stdout
    assert '{"chunk": {"id": "s2", "text": "stream2"' in result.stdout

# Note: The search batch tests were using a non-existent `search batch` subcommand.
# The actual command is `search query`. We will adapt the tests below.
# If a distinct `search batch` command is needed later, these tests would need further changes.

@patch('graph_rag.cli.commands.search.HTTPClient')
@patch('graph_rag.cli.commands.search.typer.echo') # Mock echo to check output
def test_search_batch_partial_failure(mock_echo, mock_httpx_client):
    """Test search command (non-stream) with partial failure status in response."""
    mock_response = MagicMock()
    mock_response.status_code = 207 # Multi-Status indicates partial success/failure
    mock_response.json.return_value = {
        "query": "partial fail query",
        "search_type": "vector",
        "results": [
            {"chunk": {"id": "ok1", "text": "ok chunk"}, "score": 0.9},
            {"error": "Failed to process chunk xyz", "score": 0.0} # Simulate an error for one part
        ]
    }
    mock_response.raise_for_status.side_effect = None # Don't raise on 207
    mock_client_instance = MagicMock()
    mock_client_instance.post.return_value = mock_response
    mock_context_manager = MagicMock()
    mock_context_manager.__enter__.return_value = mock_client_instance
    mock_context_manager.__exit__.return_value = None
    mock_httpx_client.return_value = mock_context_manager

    # Run the command using CliRunner
    result = runner.invoke(
        app,
        [
            "search",
            "partial fail query",
            "--type", "vector"
            # Use default limit and non-stream
        ],
    )

    # Print result for debugging
    print(f"CLI Runner Result (Search Partial Fail Test):\nExit Code: {result.exit_code}\nOutput:\n{result.stdout}\nException:\n{result.exception}")

    # Check that command succeeded (exit code 0) because API call itself was okay (207)
    # The CLI currently just prints the JSON, including errors within the results list.
    assert result.exit_code == 0
    # Check the output contains the JSON with the error detail
    assert '"query": "partial fail query"' in result.stdout
    assert '"error": "Failed to process chunk xyz"' in result.stdout
    mock_client_instance.post.assert_called_once()

@patch('graph_rag.cli.commands.search.HTTPClient')
@patch('graph_rag.cli.commands.search.typer.Exit') # Mock Exit again
@patch('graph_rag.cli.commands.search.typer.echo') # Mock echo
def test_search_batch_empty_request(mock_echo, mock_exit, mock_httpx_client):
    """Test search query command with an empty query string."""
    # Run the command with an empty query
    result = runner.invoke(
        app,
        [
            "search",
            "" # Empty query argument
        ]
    )

    # Print result for debugging
    print(f"CLI Runner Result (Search Empty Query Test):\nExit Code: {result.exit_code}\nOutput:\n{result.stdout}\nException:\n{result.exception}")

    # Check that the command exited due to validation
    mock_exit.assert_called_once_with(code=1)
    # HTTP client should not have been called
    mock_httpx_client.assert_not_called()
    # echo should not have been called for printing results
    # mock_echo.assert_not_called() # Might be called by Typer for errors, safer to not assert this

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

    try:
        # Run the command directly with explicit URL (bypassing typer.Option)
        from graph_rag.cli.commands.admin import check_health
        check_health(api_url="http://localhost:8000/health")
        
        # Verify expected behavior
        mock_exit.assert_not_called()
        mock_client_instance.get.assert_called_once_with("http://localhost:8000/health", timeout=10.0)
    except Exception as e:
        pytest.fail(f"Test failed with exception: {e}")

@patch('graph_rag.cli.commands.admin.httpx.Client')
@patch('graph_rag.cli.commands.admin.typer.Exit')  # Mock typer.Exit
def test_admin_health_unhealthy(mock_exit, mock_httpx_client):
    """Test unhealthy API response."""
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

    with pytest.raises(SystemExit) as exc_info:
        # Run the command directly with explicit URL (bypassing typer.Option)
        from graph_rag.cli.commands.admin import check_health
        check_health(api_url="http://localhost:8000/health")
    
    # Check if the exit code is non-zero (typically 1)
    assert exc_info.value.code != 0
    
    # Verify that the underlying httpx call was made correctly
    mock_client_instance.get.assert_called_once_with("http://localhost:8000/health", timeout=10.0)
    # We don't need to check mock_exit anymore, as SystemExit is raised directly

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

    with pytest.raises(SystemExit) as exc_info:
        # Run the command directly with explicit URL (bypassing typer.Option)
        from graph_rag.cli.commands.admin import check_health
        check_health(api_url="http://localhost:8000/health")

    # Check if the exit code is non-zero (typically 1)
    assert exc_info.value.code != 0
    
    # Verify that the underlying httpx call was made correctly
    mock_client_instance.get.assert_called_once_with("http://localhost:8000/health", timeout=10.0)
    # We don't need to check mock_exit anymore, as SystemExit is raised directly

# --- End of File --- 