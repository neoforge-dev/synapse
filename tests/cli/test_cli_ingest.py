import pytest
import json
from typer.testing import CliRunner
from unittest.mock import patch, MagicMock

# Import the main Typer app and the specific command app
from graph_rag.cli.main import app as main_cli_app
# Assuming the make_api_request helper is in cli.commands.ingest
# If moved to utils, adjust the patch target
from graph_rag.cli.commands.ingest import make_api_request

runner = CliRunner()

# --- Test Cases --- 

@patch('graph_rag.cli.commands.ingest.make_api_request')
def test_ingest_content_success(mock_make_request: MagicMock):
    """Test successful ingestion using direct content input."""
    mock_response_data = {"message": "Ingestion task accepted.", "document_id": "doc-cli-content"}
    mock_make_request.return_value = mock_response_data
    
    test_content = "This is content from the CLI test."
    test_metadata = '{"source": "cli-test", "run": 1}'
    
    result = runner.invoke(
        main_cli_app,
        ["ingest", "ingest", "--content", test_content, "--metadata", test_metadata]
    )
    
    print(f"CLI Output:\n{result.stdout}")
    assert result.exit_code == 0
    assert "Ingestion request accepted by API" in result.stdout
    assert f"Document ID: {mock_response_data['document_id']}" in result.stdout
    
    # Verify make_api_request was called correctly
    mock_make_request.assert_called_once()
    call_args, call_kwargs = mock_make_request.call_args
    assert len(call_args) == 2 # url, payload
    # URL check might be fragile if settings change, check contains relevant part
    assert "/ingestion/documents" in call_args[0]
    payload = call_args[1]
    assert payload["content"] == test_content
    assert payload["metadata"] == json.loads(test_metadata)
    assert "document_id" not in payload # ID was not provided

@patch('graph_rag.cli.commands.ingest.make_api_request')
def test_ingest_file_success(mock_make_request: MagicMock, tmp_path):
    """Test successful ingestion using file input."""
    mock_response_data = {"message": "Ingestion task accepted.", "document_id": "doc-cli-file"}
    mock_make_request.return_value = mock_response_data
    
    # Create a temporary file
    test_file_content = "Content from a test file.\nSecond line."
    test_file = tmp_path / "test_doc.txt"
    test_file.write_text(test_file_content, encoding='utf-8')
    
    test_metadata = '{"source": "cli-file-test"}'
    test_doc_id = "explicit-file-id"
    
    result = runner.invoke(
        main_cli_app,
        ["ingest", "ingest", "--file", str(test_file), "--metadata", test_metadata, "--doc-id", test_doc_id]
    )
    
    print(f"CLI Output:\n{result.stdout}")
    assert result.exit_code == 0
    assert "Ingestion request accepted by API" in result.stdout
    assert f"Document ID: {mock_response_data['document_id']}" in result.stdout
    
    # Verify make_api_request call
    mock_make_request.assert_called_once()
    call_args, call_kwargs = mock_make_request.call_args
    payload = call_args[1]
    assert payload["content"] == test_file_content
    assert payload["metadata"] == json.loads(test_metadata)
    assert payload["document_id"] == test_doc_id

def test_ingest_missing_input(tmp_path):
    """Test calling ingest without --content or --file."""
    result = runner.invoke(main_cli_app, ["ingest", "ingest"])
    
    print(f"CLI Output:\n{result.stdout}")
    print(f"CLI Stderr:\n{result.stderr}") # Print stderr for debugging
    assert result.exit_code != 0
    # Check stderr if typer prints error there, otherwise stdout
    assert "Error: Must provide either --content/-c or --file/-f" in result.stderr or \
           "Error: Must provide either --content/-c or --file/-f" in result.stdout
           
def test_ingest_both_content_and_file(tmp_path):
    """Test calling ingest with both --content and --file."""
    test_file = tmp_path / "dummy.txt"
    test_file.touch()
    
    result = runner.invoke(main_cli_app, ["ingest", "ingest", "--content", "abc", "--file", str(test_file)])
    
    print(f"CLI Output:\n{result.stdout}")
    print(f"CLI Stderr:\n{result.stderr}")
    assert result.exit_code != 0
    assert "Error: Cannot provide both --content/-c and --file/-f" in result.stderr or \
           "Error: Cannot provide both --content/-c and --file/-f" in result.stdout

def test_ingest_file_not_found():
    """Test calling ingest with a non-existent file path."""
    # Typer's `exists=True` handles this validation before our command runs
    result = runner.invoke(main_cli_app, ["ingest", "ingest", "--file", "/path/to/nonexistent/file.txt"])
    
    print(f"CLI Output:\n{result.stdout}")
    print(f"CLI Stderr:\n{result.stderr}")
    assert result.exit_code != 0 
    assert "Invalid value for '--file' / '-f'" in result.stdout or \
           "File \'/path/to/nonexistent/file.txt\' does not exist" in result.stdout

def test_ingest_invalid_metadata_json():
    """Test calling ingest with invalid JSON for metadata."""
    result = runner.invoke(
        main_cli_app,
        ["ingest", "ingest", "--content", "some content", "--metadata", '{"key": value}'] # Invalid JSON
    )
    
    print(f"CLI Output:\n{result.stdout}")
    print(f"CLI Stderr:\n{result.stderr}")
    assert result.exit_code != 0
    assert "Error: Invalid JSON provided for metadata" in result.stderr or \
           "Error: Invalid JSON provided for metadata" in result.stdout

@patch('graph_rag.cli.commands.ingest.make_api_request')
def test_ingest_api_connection_error(mock_make_request: MagicMock):
    """Test CLI behavior when the API request fails (connection error)."""
    from httpx import RequestError
    mock_make_request.side_effect = RequestError("Connection refused", request=MagicMock())
    
    result = runner.invoke(
        main_cli_app,
        ["ingest", "ingest", "--content", "test content"]
    )
    
    print(f"CLI Output:\n{result.stdout}")
    print(f"CLI Stderr:\n{result.stderr}")
    assert result.exit_code != 0
    assert "Error: Failed to connect to the API" in result.stderr or \
           "Error: Failed to connect to the API" in result.stdout

@patch('graph_rag.cli.commands.ingest.make_api_request')
def test_ingest_api_http_error(mock_make_request: MagicMock):
    """Test CLI behavior when the API returns an HTTP error status."""
    from httpx import HTTPStatusError, Response, Request
    mock_response = Response(status_code=500, request=Request('POST', ''), text="Internal Server Error")
    mock_make_request.side_effect = HTTPStatusError("Server error", request=mock_response.request, response=mock_response)
    
    result = runner.invoke(
        main_cli_app,
        ["ingest", "ingest", "--content", "test content"]
    )
    
    print(f"CLI Output:\n{result.stdout}")
    print(f"CLI Stderr:\n{result.stderr}")
    assert result.exit_code != 0
    assert "Error: API returned status 500" in result.stderr or \
           "Error: API returned status 500" in result.stdout 