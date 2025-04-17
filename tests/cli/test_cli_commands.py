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
@patch('graph_rag.cli.commands.ingest.MemgraphRepository') # <<< ADD THIS PATCH
def test_ingest_document_file_success(mock_memgraph_repo, mock_exit, mock_process_and_store, tmp_path):
    """Test successful ingestion via file path argument."""
    # Create temporary file
    test_file = tmp_path / "test_doc.txt"
    test_file.write_text("Content from file.")
    metadata_dict = {"source": "cli-test"}
    metadata_json = json.dumps(metadata_dict)

    # Configure the mock to simulate successful processing
    mock_process_and_store.return_value = None # Assume it returns None on success

    # Optional: Configure the patched MemgraphRepository mock if needed
    # mock_memgraph_repo.return_value = AsyncMock() # Example

    try:
        # Run the command directly
        from graph_rag.cli.commands.ingest import ingest
        ingest(file_path=str(test_file), metadata=metadata_json)
        
        # Verify mocks were called as expected
        mock_exit.assert_not_called()
        mock_process_and_store.assert_called_once()
        # Access the actual arguments passed to the mocked process_and_store_document
        call_args_list = mock_process_and_store.call_args_list
        assert len(call_args_list) == 1
        args, kwargs = call_args_list[0]
        
        assert isinstance(args[0], Path) and str(args[0]) == str(test_file) # Check Path object
        assert args[1] == metadata_dict # Check parsed metadata dict
        # Check the other args (repo, processor, extractor) if necessary, 
        # though they are instantiated within the (patched) ingest command context
        # assert isinstance(args[2], MagicMock) # Should be the mock_memgraph_repo instance

    except Exception as e:
        pytest.fail(f"Test failed with exception: {e}")

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

    try:
        # Run the command directly
        from graph_rag.cli.commands.ingest import ingest
        ingest(file_path=str(test_file), metadata="{invalid-json")
        pytest.fail("Expected the command to fail with invalid JSON")
    except Exception:
        # Should have tried to exit with non-zero code
        mock_exit.assert_called_once()
        assert mock_exit.call_args[0][0] != 0

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

    try:
        # Run the command directly with explicit URL (bypassing typer.Option)
        from graph_rag.cli.commands.search import search_query
        search_query(
            query="test query", 
            search_type="vector", 
            limit=5, 
            stream=False,
            api_url="http://localhost:8000/api/v1/search/query"
        )
        
        # Verify expected behavior
        mock_exit.assert_not_called()
        mock_client_instance.post.assert_called_once()
        call_args = mock_client_instance.post.call_args
        assert "http://localhost:8000/api/v1/search/query?stream=false" in str(call_args)
    except Exception as e:
        pytest.fail(f"Test failed with exception: {e}")

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

    try:
        # Run the command directly with explicit URL (bypassing typer.Option)
        from graph_rag.cli.commands.search import search_query
        search_query(
            query="stream test", 
            search_type="vector", 
            limit=10, 
            stream=True,
            api_url="http://localhost:8000/api/v1/search/query"
        )
        
        # Verify expected behavior
        mock_exit.assert_not_called()
        mock_httpx_stream.assert_called_once()
        call_args = mock_httpx_stream.call_args
        assert "http://localhost:8000/api/v1/search/query?stream=true" in str(call_args)
    except Exception as e:
        pytest.fail(f"Test failed with exception: {e}")

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