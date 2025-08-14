"""Tests for MCP server functionality."""

from unittest.mock import Mock, patch

import httpx
import pytest

from graph_rag.mcp.server import (
    INGEST_FILES_SCHEMA,
    SEARCH_SCHEMA,
    ConnectionError,
    McpError,
    ValidationError,
    _get_document,
    _ingest_files,
    _list_documents,
    _query_answer,
    _search,
    _system_status,
    _validate_input,
    health_check,
    make_tools,
)


class TestSchemaValidation:
    """Test input validation against schemas."""

    def test_validate_ingest_files_schema_valid(self):
        """Test valid input for ingest_files schema."""
        valid_input = {
            "paths": ["/path/to/file.txt"],
            "embeddings": True,
            "replace": False,
            "metadata": {"source": "test"}
        }

        result = _validate_input(valid_input, INGEST_FILES_SCHEMA)
        assert result["paths"] == ["/path/to/file.txt"]
        assert result["embeddings"] is True
        assert result["replace"] is False
        assert result["metadata"]["source"] == "test"

    def test_validate_ingest_files_schema_defaults(self):
        """Test default values are applied."""
        minimal_input = {"paths": ["/path/to/file.txt"]}

        result = _validate_input(minimal_input, INGEST_FILES_SCHEMA)
        assert result["paths"] == ["/path/to/file.txt"]
        assert result["embeddings"] is True  # default
        assert result["replace"] is True     # default

    def test_validate_missing_required_field(self):
        """Test validation fails for missing required field."""
        invalid_input = {"embeddings": True}  # missing required 'paths'

        with pytest.raises(ValidationError) as exc_info:
            _validate_input(invalid_input, INGEST_FILES_SCHEMA)

        assert "Missing required field: paths" in str(exc_info.value)
        assert exc_info.value.details["field"] == "paths"

    def test_validate_wrong_type(self):
        """Test validation fails for wrong type."""
        invalid_input = {"paths": "not_a_list"}  # should be array

        with pytest.raises(ValidationError) as exc_info:
            _validate_input(invalid_input, INGEST_FILES_SCHEMA)

        assert "must be an array" in str(exc_info.value)

    def test_validate_search_schema_with_enum(self):
        """Test enum validation for search_type."""
        valid_input = {"query": "test", "search_type": "vector"}
        result = _validate_input(valid_input, SEARCH_SCHEMA)
        assert result["search_type"] == "vector"

        # Invalid enum value
        invalid_input = {"query": "test", "search_type": "invalid"}
        with pytest.raises(ValidationError) as exc_info:
            _validate_input(invalid_input, SEARCH_SCHEMA)
        assert "must be one of" in str(exc_info.value)

    def test_validate_integer_range(self):
        """Test integer range validation."""
        # Valid range
        valid_input = {"query": "test", "limit": 50}
        result = _validate_input(valid_input, SEARCH_SCHEMA)
        assert result["limit"] == 50

        # Below minimum
        invalid_input = {"query": "test", "limit": 0}
        with pytest.raises(ValidationError) as exc_info:
            _validate_input(invalid_input, SEARCH_SCHEMA)
        assert "must be >= 1" in str(exc_info.value)


class TestMcpTools:
    """Test MCP tool creation and basic functionality."""

    def test_make_tools_returns_expected_count(self):
        """Test that make_tools returns the expected number of tools."""
        tools = make_tools()
        assert len(tools) == 7  # Updated count with new tools

        tool_names = [tool.name for tool in tools]
        expected_tools = [
            "ingest_files", "search", "query_answer",
            "list_documents", "get_document", "delete_document", "system_status"
        ]
        for expected_tool in expected_tools:
            assert expected_tool in tool_names

    def test_tool_schemas_are_valid(self):
        """Test that all tools have valid schemas."""
        tools = make_tools()

        for tool in tools:
            assert isinstance(tool.name, str)
            assert isinstance(tool.description, str)
            assert isinstance(tool.input_schema, dict)
            assert callable(tool.handler)

            # Schema should have basic structure
            assert "type" in tool.input_schema
            assert tool.input_schema["type"] == "object"


class TestHealthCheck:
    """Test health check functionality."""

    @patch('graph_rag.mcp.server._client')
    def test_health_check_success(self, mock_client_factory):
        """Test successful health check."""
        mock_client = Mock()
        mock_client.__enter__ = Mock(return_value=mock_client)
        mock_client.__exit__ = Mock(return_value=None)
        mock_client_factory.return_value = mock_client

        # Mock successful API response
        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_client.get.return_value = mock_response

        with patch('mcp.server.Server'):  # Mock MCP package availability
            status = health_check()

        assert status["healthy"] is True
        assert status["api_available"] is True
        assert status["tools_count"] > 0

    def test_health_check_no_mcp_package(self):
        """Test health check when MCP package is not available."""
        with patch('graph_rag.mcp.server._client'):
            status = health_check()

        assert status["healthy"] is False
        assert status["mcp_available"] is False
        assert "MCP package not installed" in status["errors"]

    @patch('graph_rag.mcp.server._client')
    def test_health_check_api_unavailable(self, mock_client_factory):
        """Test health check when API is unavailable."""
        mock_client = Mock()
        mock_client.__enter__ = Mock(return_value=mock_client)
        mock_client.__exit__ = Mock(return_value=None)
        mock_client_factory.return_value = mock_client

        # Mock API connection failure
        mock_client.get.side_effect = httpx.ConnectError("Connection failed")

        status = health_check()

        assert status["healthy"] is False
        assert status["api_available"] is False
        assert any("API not available" in error for error in status["errors"])


class TestToolHandlers:
    """Test individual tool handlers with mocked HTTP calls."""

    @patch('graph_rag.mcp.server._client')
    def test_search_success(self, mock_client_factory):
        """Test successful search operation."""
        mock_client = Mock()
        mock_client.__enter__ = Mock(return_value=mock_client)
        mock_client.__exit__ = Mock(return_value=None)
        mock_client_factory.return_value = mock_client

        # Mock successful API response
        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {
            "results": [
                {"chunk": {"text": "test result"}, "score": 0.95}
            ]
        }
        mock_client.post.return_value = mock_response

        result = _search("test query", limit=5)

        assert "results" in result
        assert result["query"] == "test query"
        assert result["results_count"] == 1
        mock_client.post.assert_called_once()

    @patch('graph_rag.mcp.server._client')
    def test_search_connection_error(self, mock_client_factory):
        """Test search with connection error."""
        mock_client = Mock()
        mock_client.__enter__ = Mock(return_value=mock_client)
        mock_client.__exit__ = Mock(return_value=None)
        mock_client_factory.return_value = mock_client

        mock_client.post.side_effect = httpx.ConnectError("Connection failed")

        with pytest.raises(ConnectionError) as exc_info:
            _search("test query")

        assert "Cannot connect to Synapse API" in str(exc_info.value)

    @patch('graph_rag.mcp.server._client')
    def test_query_answer_success(self, mock_client_factory):
        """Test successful query answer operation."""
        mock_client = Mock()
        mock_client.__enter__ = Mock(return_value=mock_client)
        mock_client.__exit__ = Mock(return_value=None)
        mock_client_factory.return_value = mock_client

        # Mock successful API response
        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {
            "answer": "Test answer",
            "sources": [{"chunk_id": "1", "content": "source"}],
            "timestamp": "2023-01-01T00:00:00Z"
        }
        mock_client.post.return_value = mock_response

        result = _query_answer("test question", k=3)

        assert result["answer"] == "Test answer"
        assert result["question"] == "test question"
        assert result["k"] == 3
        assert len(result["sources"]) == 1

    @patch('graph_rag.mcp.server.Path')
    @patch('graph_rag.mcp.server._client')
    def test_ingest_files_file_not_found(self, mock_client_factory, mock_path):
        """Test ingest_files with non-existent file."""
        # Mock file that doesn't exist
        mock_path.return_value.exists.return_value = False
        mock_path.return_value.__str__ = Mock(return_value="/nonexistent/file.txt")

        result = _ingest_files(["/nonexistent/file.txt"])

        assert result["success"] is False
        assert result["error_count"] == 1
        assert len(result["errors"]) == 1
        assert result["errors"][0]["error"] == "file_not_found"

    @patch('graph_rag.mcp.server._client')
    def test_list_documents_success(self, mock_client_factory):
        """Test successful list documents operation."""
        mock_client = Mock()
        mock_client.__enter__ = Mock(return_value=mock_client)
        mock_client.__exit__ = Mock(return_value=None)
        mock_client_factory.return_value = mock_client

        # Mock successful API response
        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {
            "documents": [
                {"id": "doc1", "title": "Document 1"},
                {"id": "doc2", "title": "Document 2"}
            ],
            "total": 2
        }
        mock_client.get.return_value = mock_response

        result = _list_documents(limit=10, offset=0)

        assert len(result["documents"]) == 2
        assert result["total"] == 2
        mock_client.get.assert_called_once()

    @patch('graph_rag.mcp.server._client')
    def test_get_document_not_found(self, mock_client_factory):
        """Test get document with 404 response."""
        mock_client = Mock()
        mock_client.__enter__ = Mock(return_value=mock_client)
        mock_client.__exit__ = Mock(return_value=None)
        mock_client_factory.return_value = mock_client

        # Mock 404 response
        mock_response = Mock()
        mock_response.status_code = 404
        http_error = httpx.HTTPStatusError("Not found", request=Mock(), response=mock_response)
        mock_client.get.side_effect = http_error

        with pytest.raises(McpError) as exc_info:
            _get_document("nonexistent-doc")

        assert exc_info.value.code == "DOCUMENT_NOT_FOUND"
        assert "Document not found" in str(exc_info.value)

    @patch('graph_rag.mcp.server._client')
    def test_system_status_success(self, mock_client_factory):
        """Test successful system status operation."""
        mock_client = Mock()
        mock_client.__enter__ = Mock(return_value=mock_client)
        mock_client.__exit__ = Mock(return_value=None)
        mock_client_factory.return_value = mock_client

        # Mock successful responses for all endpoints
        mock_health_response = Mock()
        mock_health_response.raise_for_status.return_value = None
        mock_health_response.json.return_value = {"status": "healthy"}

        mock_detailed_response = Mock()
        mock_detailed_response.status_code = 200
        mock_detailed_response.json.return_value = {"components": []}

        def mock_get(url, **kwargs):
            if "health" in url and "detailed" not in url:
                return mock_health_response
            elif "detailed" in url:
                return mock_detailed_response
            else:
                # For other admin endpoints, return empty success
                mock_resp = Mock()
                mock_resp.status_code = 200
                mock_resp.json.return_value = {}
                return mock_resp

        mock_client.get.side_effect = mock_get

        result = _system_status()

        assert result["health"]["status"] == "healthy"
        assert result["mcp_server"] == "connected"
        assert "api_base_url" in result


class TestErrorHandling:
    """Test error handling and edge cases."""

    def test_validation_error_properties(self):
        """Test ValidationError has correct properties."""
        error = ValidationError("Test message", field="test_field")

        assert error.message == "Test message"
        assert error.code == "VALIDATION_ERROR"
        assert error.details["field"] == "test_field"

    def test_connection_error_properties(self):
        """Test ConnectionError has correct properties."""
        error = ConnectionError("Connection failed", status_code=500)

        assert error.message == "Connection failed"
        assert error.code == "CONNECTION_ERROR"
        assert error.details["status_code"] == 500

    def test_mcp_error_properties(self):
        """Test McpError has correct properties."""
        error = McpError("MCP error", code="CUSTOM_ERROR", details={"key": "value"})

        assert error.message == "MCP error"
        assert error.code == "CUSTOM_ERROR"
        assert error.details["key"] == "value"
