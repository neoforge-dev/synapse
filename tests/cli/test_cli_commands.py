import pytest
from typer.testing import CliRunner
from unittest.mock import patch, MagicMock # Import patch
import json

# Import the Typer app instance
from graph_rag.cli.main import app

runner = CliRunner()

# --- Ingest Command Tests --- 

@patch('graph_rag.cli.commands.ingest.httpx.Client') # Mock the client
def test_ingest_document_content_success(mock_httpx_client):
    """Test successful ingestion via --content option."""
    # Configure the mock context manager and response
    mock_response = MagicMock()
    mock_response.status_code = 202
    mock_response.json.return_value = {"document_id": "mock-id", "status": "processing started"}
    mock_response.raise_for_status.return_value = None
    
    mock_client_instance = MagicMock()
    mock_client_instance.post.return_value = mock_response
    
    mock_context_manager = MagicMock()
    mock_context_manager.__enter__.return_value = mock_client_instance
    mock_context_manager.__exit__.return_value = None
    mock_httpx_client.return_value = mock_context_manager
    
    result = runner.invoke(app, [
        "ingest", "document", 
        "--content", "This is test content.", 
        "--metadata", '{"source": "cli-test"}'
    ])
    
    assert result.exit_code == 0
    assert "Ingestion request accepted by API" in result.stdout
    assert '"document_id": "mock-id"' in result.stdout
    # Check if httpx.Client().post was called correctly
    mock_client_instance.post.assert_called_once()
    call_args = mock_client_instance.post.call_args
    assert call_args[0][0] == "http://localhost:8000/api/v1/ingestion/documents" # Default URL
    assert call_args[1]['json'] == {"content": "This is test content.", "metadata": {"source": "cli-test"}}

@patch('graph_rag.cli.commands.ingest.httpx.Client')
def test_ingest_document_file_success(mock_httpx_client, tmp_path):
    """Test successful ingestion via --file option."""
    # Setup mocks (same as above)
    mock_response = MagicMock()
    mock_response.status_code = 202
    mock_response.json.return_value = {"document_id": "file-mock-id", "status": "processing started"}
    mock_response.raise_for_status.return_value = None
    mock_client_instance = MagicMock()
    mock_client_instance.post.return_value = mock_response
    mock_context_manager = MagicMock()
    mock_context_manager.__enter__.return_value = mock_client_instance
    mock_context_manager.__exit__.return_value = None
    mock_httpx_client.return_value = mock_context_manager
    
    # Create temporary file
    test_file = tmp_path / "test_doc.txt"
    test_file.write_text("Content from file.")
    
    result = runner.invoke(app, [
        "ingest", "document", 
        "--file", str(test_file), 
    ])
    
    assert result.exit_code == 0
    assert "Ingestion request accepted by API" in result.stdout
    mock_client_instance.post.assert_called_once()
    call_args = mock_client_instance.post.call_args
    assert call_args[1]['json'] == {"content": "Content from file.", "metadata": {"source": "cli"}} # Default metadata

def test_ingest_document_no_input():
    result = runner.invoke(app, ["ingest", "document"])
    assert result.exit_code != 0
    assert "Error: Must provide either" in result.stdout

def test_ingest_document_both_inputs():
    result = runner.invoke(app, ["ingest", "document", "--content", "abc", "--file", "dummy.txt"])
    assert result.exit_code != 0
    assert "Error: Cannot provide both" in result.stdout

def test_ingest_document_invalid_metadata():
    result = runner.invoke(app, ["ingest", "document", "--content", "abc", "--metadata", "{invalid-json"]) 
    assert result.exit_code != 0
    assert "Error: Invalid JSON provided" in result.stdout

# --- Search Command Tests --- 

@patch('graph_rag.cli.commands.search.httpx.Client')
def test_search_batch_success(mock_httpx_client):
    """Test successful batch search."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "query": "test query", "search_type": "vector", "results": [{"chunk": {"id": "c1"}}]
    }
    mock_response.raise_for_status.return_value = None
    mock_client_instance = MagicMock()
    mock_client_instance.post.return_value = mock_response
    mock_context_manager = MagicMock()
    mock_context_manager.__enter__.return_value = mock_client_instance
    mock_context_manager.__exit__.return_value = None
    mock_httpx_client.return_value = mock_context_manager
    
    result = runner.invoke(app, ["search", "query", "test query", "--type", "vector", "-l", "5"])
    
    assert result.exit_code == 0
    assert '"query": "test query"' in result.stdout # Check pretty printed JSON
    assert '"search_type": "vector"' in result.stdout
    assert '"id": "c1"' in result.stdout
    mock_client_instance.post.assert_called_once()
    call_args = mock_client_instance.post.call_args
    assert call_args[0][0] == "http://localhost:8000/api/v1/search/query?stream=false"
    assert call_args[1]['json'] == {"query": "test query", "search_type": "vector", "limit": 5}

@patch('graph_rag.cli.commands.search.httpx.stream') # Mock stream function
def test_search_stream_success(mock_httpx_stream):
    """Test successful streaming search."""
    # Mock the response object from httpx.stream context manager
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.headers = {"content-type": "application/x-ndjson"}
    # Simulate iter_lines returning JSON Lines
    mock_response.iter_lines.return_value = [
        '{"chunk": {"id": "s1"}, "score": 0.9}',
        '{"chunk": {"id": "s2"}, "score": 0.8}'
    ]
    mock_response.raise_for_status.return_value = None

    # Mock the context manager returned by httpx.stream
    mock_stream_context_manager = MagicMock()
    mock_stream_context_manager.__enter__.return_value = mock_response
    mock_stream_context_manager.__exit__.return_value = None
    mock_httpx_stream.return_value = mock_stream_context_manager

    result = runner.invoke(app, ["search", "query", "stream test", "--stream"])
    
    assert result.exit_code == 0
    assert '{"chunk": {"id": "s1"}, "score": 0.9}' in result.stdout
    assert '{"chunk": {"id": "s2"}, "score": 0.8}' in result.stdout
    assert "--- Streaming Results" in result.stdout
    # Check if httpx.stream was called correctly
    mock_httpx_stream.assert_called_once()
    call_args = mock_httpx_stream.call_args
    assert call_args[0][0] == "POST"
    assert call_args[0][1] == "http://localhost:8000/api/v1/search/query?stream=true"
    assert call_args[1]['json'] == {"query": "stream test", "search_type": "vector", "limit": 10} # Defaults

def test_search_invalid_type():
    result = runner.invoke(app, ["search", "query", "abc", "--type", "banana"])
    assert result.exit_code != 0
    assert "Invalid search type" in result.stdout

# --- Admin Command Tests ---

@patch('graph_rag.cli.commands.admin.httpx.Client')
def test_admin_health_success(mock_httpx_client):
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

    result = runner.invoke(app, ["admin", "health"])
    
    assert result.exit_code == 0
    assert "API Status: HEALTHY" in result.stdout
    assert "API appears healthy" in result.stdout
    mock_client_instance.get.assert_called_once_with("http://localhost:8000/health", timeout=10.0)

@patch('graph_rag.cli.commands.admin.httpx.Client')
def test_admin_health_unhealthy(mock_httpx_client):
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

    result = runner.invoke(app, ["admin", "health"])
    
    assert result.exit_code != 0 # Should exit with error code
    assert "API Status: UNHEALTHY" in result.stdout
    assert "Warning: API reported an unhealthy status" in result.stdout

@patch('graph_rag.cli.commands.admin.httpx.Client')
def test_admin_health_api_error(mock_httpx_client):
    """Test health check when API returns HTTP error."""
    mock_response = MagicMock()
    mock_response.status_code = 503
    mock_response.text = '{"detail": "Service Unavailable"}'
    mock_response.json.side_effect = json.JSONDecodeError("msg", "doc", 0) # Simulate JSON error if .text used
    mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
        message="Server error", request=MagicMock(), response=mock_response
    )
    mock_client_instance = MagicMock()
    mock_client_instance.get.return_value = mock_response
    mock_context_manager = MagicMock()
    mock_context_manager.__enter__.return_value = mock_client_instance
    mock_context_manager.__exit__.return_value = None
    mock_httpx_client.return_value = mock_context_manager

    result = runner.invoke(app, ["admin", "health"])
    
    assert result.exit_code != 0
    assert "Error: API health check failed with status 503" in result.stdout
    # Checks if detail parsing worked
    # assert "Detail: {"detail": "Service Unavailable"}" in result.stdout # Raw text expected here
    assert "Detail: {'detail': 'Service Unavailable'}" in result.stdout 