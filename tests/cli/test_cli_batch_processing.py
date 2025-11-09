"""Tests for CLI batch processing functionality."""

import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest
from typer.testing import CliRunner

from graph_rag.cli.main import app


@pytest.fixture
def runner():
    """Create CLI test runner."""
    return CliRunner()


@pytest.fixture
def large_test_directory():
    """Create a large test directory with many files."""
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)

        # Create 150 test files (more than the 100 threshold for auto batch processing)
        for i in range(150):
            file_path = temp_path / f"test_file_{i:03d}.md"
            file_path.write_text(f"""---
title: Test Document {i}
tags: [test, batch]
---

# Test Document {i}

This is test content for document {i} in the batch processing test.
The content is substantial enough to trigger processing.

## Section 1
Some content here.

## Section 2
More content here.
""")

        yield temp_path


@pytest.fixture
def small_test_directory():
    """Create a small test directory with few files."""
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)

        # Create 5 test files (under the 100 threshold)
        for i in range(5):
            file_path = temp_path / f"small_test_{i}.md"
            file_path.write_text(f"# Small Test {i}\nContent for small test {i}")

        yield temp_path


def test_auto_batch_processing_for_large_collections(runner, large_test_directory):
    """Test that batch processing is automatically enabled for large collections."""
    # Mock the database connections to avoid actual database calls
    with patch('graph_rag.api.dependencies.create_graph_repository') as mock_repo, \
         patch('graph_rag.api.dependencies.create_embedding_service'), \
         patch('graph_rag.api.dependencies.create_vector_store'):

        # Configure mocks
        mock_repo_instance = mock_repo.return_value
        mock_repo_instance.connect.return_value = None
        mock_repo_instance.close.return_value = None

        # Run the CLI command with dry-run to test detection logic
        result = runner.invoke(app, [
            "ingest",
            str(large_test_directory),
            "--dry-run",
            "--json"
        ])

        # Should succeed without errors
        assert result.exit_code == 0, f"Command failed with output: {result.stdout}"

        # Verify it found the expected number of files
        import json
        output = json.loads(result.stdout)
        assert len(output) == 150


def test_manual_batch_processing_enable(runner, small_test_directory):
    """Test manually enabling batch processing with --batch flag."""
    with patch('graph_rag.api.dependencies.create_graph_repository') as mock_repo, \
         patch('graph_rag.api.dependencies.create_embedding_service'), \
         patch('graph_rag.api.dependencies.create_vector_store'):

        # Configure mocks
        mock_repo_instance = mock_repo.return_value
        mock_repo_instance.connect.return_value = None
        mock_repo_instance.close.return_value = None

        # Run with --batch flag to force batch processing
        result = runner.invoke(app, [
            "ingest",
            str(small_test_directory),
            "--batch",
            "--dry-run",
            "--json"
        ])

        # Should succeed
        assert result.exit_code == 0, f"Command failed with output: {result.stdout}"

        # Verify output format
        import json
        output = json.loads(result.stdout)
        assert len(output) == 5


def test_manual_batch_processing_disable(runner, large_test_directory):
    """Test manually disabling batch processing with --no-batch flag."""
    with patch('graph_rag.api.dependencies.create_graph_repository') as mock_repo, \
         patch('graph_rag.api.dependencies.create_embedding_service'), \
         patch('graph_rag.api.dependencies.create_vector_store'):

        # Configure mocks
        mock_repo_instance = mock_repo.return_value
        mock_repo_instance.connect.return_value = None
        mock_repo_instance.close.return_value = None

        # Run with --no-batch flag to disable batch processing
        result = runner.invoke(app, [
            "ingest",
            str(large_test_directory),
            "--no-batch",
            "--dry-run",
            "--json"
        ])

        # Should succeed
        assert result.exit_code == 0, f"Command failed with output: {result.stdout}"

        # Verify output format
        import json
        output = json.loads(result.stdout)
        assert len(output) == 150


def test_custom_batch_size(runner, small_test_directory):
    """Test using custom batch size."""
    with patch('graph_rag.api.dependencies.create_graph_repository') as mock_repo, \
         patch('graph_rag.api.dependencies.create_embedding_service'), \
         patch('graph_rag.api.dependencies.create_vector_store'):

        # Configure mocks
        mock_repo_instance = mock_repo.return_value
        mock_repo_instance.connect.return_value = None
        mock_repo_instance.close.return_value = None

        # Run with custom batch size
        result = runner.invoke(app, [
            "ingest",
            str(small_test_directory),
            "--batch",
            "--batch-size", "2",
            "--dry-run",
            "--json"
        ])

        # Should succeed
        assert result.exit_code == 0, f"Command failed with output: {result.stdout}"

        # Verify output
        import json
        output = json.loads(result.stdout)
        assert len(output) == 5


def test_batch_processing_help_text(runner):
    """Test that batch processing options appear in help text."""
    result = runner.invoke(app, ["ingest", "--help"])

    assert result.exit_code == 0
    help_text = result.stdout

    # Verify batch-related options are documented
    assert "--batch-size" in help_text
    assert "--batch" in help_text and "--no-batch" in help_text
    assert "batch" in help_text.lower()


@pytest.mark.integration
def test_batch_processing_performance_characteristics(runner):
    """Test that batch processing has expected performance characteristics."""
    import tempfile
    import time

    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)

        # Create a medium-sized collection for performance testing
        file_count = 100
        for i in range(file_count):
            file_path = temp_path / f"perf_test_{i:03d}.md"
            file_path.write_text(f"# Performance Test {i}\nContent for performance testing document {i}.")

        with patch('graph_rag.api.dependencies.create_graph_repository') as mock_repo, \
             patch('graph_rag.api.dependencies.create_embedding_service'), \
             patch('graph_rag.api.dependencies.create_vector_store'):

            # Configure mocks
            mock_repo_instance = mock_repo.return_value
            mock_repo_instance.connect.return_value = None
            mock_repo_instance.close.return_value = None

            # Test dry-run performance (should be fast)
            start_time = time.monotonic()
            result = runner.invoke(app, [
                "ingest",
                str(temp_path),
                "--dry-run",
                "--json"
            ])
            end_time = time.monotonic()

            # Should complete quickly for dry run
            processing_time = end_time - start_time
            assert processing_time < 5.0, f"Dry run took too long: {processing_time:.2f}s"

            # Should succeed
            assert result.exit_code == 0, f"Command failed with output: {result.stdout}"

            # Verify all files were detected
            import json
            output = json.loads(result.stdout)
            assert len(output) == file_count


def test_batch_processing_with_include_exclude_filters(runner):
    """Test batch processing works with include/exclude filters."""
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)

        # Create mixed file types
        for i in range(10):
            # Create .md files
            md_file = temp_path / f"document_{i}.md"
            md_file.write_text(f"# Document {i}\nMarkdown content")

            # Create .txt files
            txt_file = temp_path / f"text_{i}.txt"
            txt_file.write_text(f"Text document {i}")

            # Create .py files (should be excluded)
            py_file = temp_path / f"script_{i}.py"
            py_file.write_text(f"# Python script {i}\nprint('hello')")

        with patch('graph_rag.api.dependencies.create_graph_repository') as mock_repo, \
             patch('graph_rag.api.dependencies.create_embedding_service'), \
             patch('graph_rag.api.dependencies.create_vector_store'):

            # Configure mocks
            mock_repo_instance = mock_repo.return_value
            mock_repo_instance.connect.return_value = None
            mock_repo_instance.close.return_value = None

            # Test with include filter for only .md files
            result = runner.invoke(app, [
                "ingest",
                str(temp_path),
                "--include", "*.md",
                "--batch",
                "--dry-run",
                "--json"
            ])

            assert result.exit_code == 0

            import json
            output = json.loads(result.stdout)
            # Should only include .md files
            assert len(output) == 10
            for item in output:
                assert item["path"].endswith(".md")


def test_batch_processing_error_handling(runner):
    """Test batch processing handles errors gracefully."""
    # Test with non-existent directory
    result = runner.invoke(app, [
        "ingest",
        "/path/that/does/not/exist",
        "--batch",
        "--dry-run"
    ])

    # Should fail gracefully
    assert result.exit_code == 1
    assert "does not exist" in result.stdout


def test_batch_size_validation(runner, small_test_directory):
    """Test that batch size is validated."""
    with patch('graph_rag.api.dependencies.create_graph_repository') as mock_repo, \
         patch('graph_rag.api.dependencies.create_embedding_service'), \
         patch('graph_rag.api.dependencies.create_vector_store'):

        # Configure mocks
        mock_repo_instance = mock_repo.return_value
        mock_repo_instance.connect.return_value = None
        mock_repo_instance.close.return_value = None

        # Test with very small batch size (should work)
        result = runner.invoke(app, [
            "ingest",
            str(small_test_directory),
            "--batch",
            "--batch-size", "1",
            "--dry-run"
        ])

        assert result.exit_code == 0

        # Test with large batch size (should work)
        result = runner.invoke(app, [
            "ingest",
            str(small_test_directory),
            "--batch",
            "--batch-size", "1000",
            "--dry-run"
        ])

        assert result.exit_code == 0
