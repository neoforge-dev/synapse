import pytest
import json
from typer.testing import CliRunner
from unittest.mock import patch, MagicMock, AsyncMock
from pathlib import Path

# Import the main Typer app
from graph_rag.cli.main import app as main_cli_app

runner = CliRunner()

# --- Test Cases ---

@patch('graph_rag.cli.commands.ingest.process_and_store_document', new_callable=AsyncMock)
@patch('graph_rag.config.settings.Settings')
@patch('graph_rag.cli.commands.ingest.MemgraphRepository')
@patch('graph_rag.cli.commands.ingest.SimpleDocumentProcessor')
@patch('graph_rag.cli.commands.ingest.SpacyEntityExtractor')
def test_ingest_file_success(
    mock_extractor_cls: MagicMock,
    mock_processor_cls: MagicMock,
    mock_repo_cls: MagicMock,
    mock_settings_cls: MagicMock,
    mock_process_store: AsyncMock,
    tmp_path: Path
):
    """Test successful ingestion using file input (local processing)."""
    # Create a temporary file
    test_file_content = "Content from a test file.\nSecond line."
    test_file = tmp_path / "test_doc.txt"
    test_file.write_text(test_file_content, encoding='utf-8')

    test_metadata = '{"source": "cli-file-test"}'

    # Mock the instance methods if needed, though patching the async function directly might be enough
    mock_repo_instance = MagicMock()
    mock_processor_instance = MagicMock()
    mock_extractor_instance = MagicMock()
    mock_repo_cls.return_value = mock_repo_instance
    mock_processor_cls.return_value = mock_processor_instance
    mock_extractor_cls.return_value = mock_extractor_instance

    # Configure Settings mock if necessary
    mock_settings_instance = MagicMock()
    mock_settings_instance.MEMGRAPH_HOST = "localhost"
    mock_settings_instance.MEMGRAPH_PORT = 7687
    mock_settings_instance.MEMGRAPH_USERNAME = "user"
    mock_settings_instance.MEMGRAPH_PASSWORD = MagicMock()
    mock_settings_instance.MEMGRAPH_PASSWORD.get_secret_value.return_value = "pass"
    mock_settings_cls.return_value = mock_settings_instance

    result = runner.invoke(
        main_cli_app,
        ["ingest", str(test_file), "--metadata", test_metadata]
    )

    print(f"CLI Output:\n{result.stdout}")
    print(f"CLI Exception: {result.exception}")
    assert result.exit_code == 0

    # Verify process_and_store_document was called correctly
    mock_process_store.assert_called_once()
    call_args, call_kwargs = mock_process_store.call_args
    assert call_args[0] == test_file
    assert call_args[1] == json.loads(test_metadata)
    assert call_args[2] is mock_repo_instance
    assert call_args[3] is mock_processor_instance
    assert call_args[4] is mock_extractor_instance

def test_ingest_missing_file_argument():
    """Test calling ingest without the required file_path argument."""
    result = runner.invoke(main_cli_app, ["ingest"])

    print(f"CLI Output:\n{result.stdout}")
    assert result.exit_code != 0
    assert "Missing argument 'FILE_PATH'" in result.stdout

def test_ingest_file_not_found():
    """Test calling ingest with a non-existent file path."""
    non_existent_path = "/path/to/hopefully/nonexistent/file.txt"
    result = runner.invoke(main_cli_app, ["ingest", non_existent_path])

    print(f"CLI Output:\n{result.stdout}")
    assert result.exit_code != 0
    assert non_existent_path in result.stdout
    assert "does not exist" in result.stdout

@patch('graph_rag.cli.commands.ingest.process_and_store_document', new_callable=AsyncMock)
def test_ingest_invalid_metadata_json(mock_process_store: AsyncMock, tmp_path: Path):
    """Test calling ingest with invalid JSON for metadata."""
    test_file = tmp_path / "dummy.txt"
    test_file.touch()
    invalid_metadata = '{"key": value}'

    result = runner.invoke(
        main_cli_app,
        ["ingest", str(test_file), "--metadata", invalid_metadata]
    )

    print(f"CLI Output (may be empty due to I/O error):\n{result.stdout}")
    print(f"CLI Exception: {result.exception}")
    assert result.exit_code != 0
    mock_process_store.assert_not_called()

@patch('graph_rag.cli.commands.ingest.process_and_store_document', new_callable=AsyncMock)
@patch('graph_rag.config.settings.Settings')
@patch('graph_rag.cli.commands.ingest.MemgraphRepository')
@patch('graph_rag.cli.commands.ingest.SimpleDocumentProcessor')
@patch('graph_rag.cli.commands.ingest.SpacyEntityExtractor')
def test_cli_large_file_handling(
    mock_extractor_cls: MagicMock,
    mock_processor_cls: MagicMock,
    mock_repo_cls: MagicMock,
    mock_settings_cls: MagicMock,
    mock_process_store: AsyncMock,
    tmp_path: Path
):
    """Test CLI handling of large files (local processing)."""
    # Create a large file (adjust size if needed, 1MB might be slow)
    large_content = "Test " * 50000
    test_file = tmp_path / "large_file.txt"
    test_file.write_text(large_content, encoding='utf-8')

    # Mock settings and components as in the success test
    mock_repo_instance = MagicMock()
    mock_processor_instance = MagicMock()
    mock_extractor_instance = MagicMock()
    mock_repo_cls.return_value = mock_repo_instance
    mock_processor_cls.return_value = mock_processor_instance
    mock_extractor_cls.return_value = mock_extractor_instance
    mock_settings_instance = MagicMock()
    mock_settings_instance.MEMGRAPH_HOST = "localhost"
    mock_settings_instance.MEMGRAPH_PORT = 7687
    mock_settings_instance.MEMGRAPH_USERNAME = "user"
    mock_settings_instance.MEMGRAPH_PASSWORD = MagicMock()
    mock_settings_instance.MEMGRAPH_PASSWORD.get_secret_value.return_value = "pass"
    mock_settings_cls.return_value = mock_settings_instance

    result = runner.invoke(
        main_cli_app,
        ["ingest", str(test_file)]
    )

    assert result.exit_code == 0
    mock_process_store.assert_called_once()

@patch('graph_rag.cli.commands.ingest.process_and_store_document', new_callable=AsyncMock)
@patch('graph_rag.config.settings.Settings')
@patch('graph_rag.cli.commands.ingest.MemgraphRepository')
@patch('graph_rag.cli.commands.ingest.SimpleDocumentProcessor')
@patch('graph_rag.cli.commands.ingest.SpacyEntityExtractor')
def test_cli_special_chars_handling(
    mock_extractor_cls: MagicMock,
    mock_processor_cls: MagicMock,
    mock_repo_cls: MagicMock,
    mock_settings_cls: MagicMock,
    mock_process_store: AsyncMock,
    tmp_path: Path
):
    """Test CLI handling of files with special characters (local processing)."""
    special_content = "Test file with special chars: \n\t\r\b\f\\\"'"
    test_file = tmp_path / "special.txt"
    test_file.write_text(special_content, encoding='utf-8')

    # Mock settings and components
    mock_repo_instance = MagicMock()
    mock_processor_instance = MagicMock()
    mock_extractor_instance = MagicMock()
    mock_repo_cls.return_value = mock_repo_instance
    mock_processor_cls.return_value = mock_processor_instance
    mock_extractor_cls.return_value = mock_extractor_instance
    mock_settings_instance = MagicMock()
    mock_settings_instance.MEMGRAPH_HOST = "localhost"
    mock_settings_instance.MEMGRAPH_PORT = 7687
    mock_settings_instance.MEMGRAPH_USERNAME = "user"
    mock_settings_instance.MEMGRAPH_PASSWORD = MagicMock()
    mock_settings_instance.MEMGRAPH_PASSWORD.get_secret_value.return_value = "pass"
    mock_settings_cls.return_value = mock_settings_instance

    result = runner.invoke(
        main_cli_app,
        ["ingest", str(test_file)]
    )

    assert result.exit_code == 0
    mock_process_store.assert_called_once()

@patch('graph_rag.cli.commands.ingest.process_and_store_document', new_callable=AsyncMock)
@patch('graph_rag.config.settings.Settings')
@patch('graph_rag.cli.commands.ingest.MemgraphRepository')
@patch('graph_rag.cli.commands.ingest.SimpleDocumentProcessor')
@patch('graph_rag.cli.commands.ingest.SpacyEntityExtractor')
def test_ingest_processing_error(
    mock_extractor_cls: MagicMock,
    mock_processor_cls: MagicMock,
    mock_repo_cls: MagicMock,
    mock_settings_cls: MagicMock,
    mock_process_store: AsyncMock,
    tmp_path: Path
):
    """Test error handling during the local document processing stage."""
    test_file = tmp_path / "error_doc.txt"
    test_file.write_text("Some content", encoding='utf-8')

    # Mock settings and components
    mock_repo_instance = MagicMock()
    mock_processor_instance = MagicMock()
    mock_extractor_instance = MagicMock()
    mock_repo_cls.return_value = mock_repo_instance
    mock_processor_cls.return_value = mock_processor_instance
    mock_extractor_cls.return_value = mock_extractor_instance
    mock_settings_instance = MagicMock()
    mock_settings_instance.MEMGRAPH_HOST = "localhost"
    mock_settings_instance.MEMGRAPH_PORT = 7687
    mock_settings_instance.MEMGRAPH_USERNAME = "user"
    mock_settings_instance.MEMGRAPH_PASSWORD = MagicMock()
    mock_settings_instance.MEMGRAPH_PASSWORD.get_secret_value.return_value = "pass"
    mock_settings_cls.return_value = mock_settings_instance

    # Simulate an error during processing
    error_message = "Simulated processing failure"
    mock_process_store.side_effect = Exception(error_message)

    result = runner.invoke(
        main_cli_app,
        ["ingest", str(test_file)]
    )

    print(f"CLI Output:\n{result.stdout}")
    print(f"CLI Exception: {result.exception}")
    assert result.exit_code != 0
    mock_process_store.assert_called_once()