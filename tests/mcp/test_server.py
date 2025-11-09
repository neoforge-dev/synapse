"""Tests for MCP server functionality."""

import sys
from datetime import datetime
from types import ModuleType
from unittest.mock import Mock, patch

import httpx
import pytest

from graph_rag.mcp.server import (
    INGEST_FILES_SCHEMA,
    SEARCH_SCHEMA,
    ConnectionError,
    McpError,
    ValidationError,
    _delete_document,
    _get_document,
    _ingest_files,
    _list_documents,
    _query_answer,
    _search,
    _system_status,
    _validate_input,
    _wrap_handler,
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

        fake_mcp = ModuleType("mcp")
        fake_mcp.__version__ = "0.1"

        with patch.dict(sys.modules, {'mcp': fake_mcp}):
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
    def test_ingest_files_success(self, mock_client_factory, tmp_path):
        """Test ingest_files successfully posts document content."""
        test_file = tmp_path / "document.txt"
        test_file.write_text("Sample content", encoding="utf-8")

        mock_client = Mock()
        mock_client.__enter__ = Mock(return_value=mock_client)
        mock_client.__exit__ = Mock(return_value=None)
        mock_client_factory.return_value = mock_client

        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {"document_id": str(test_file), "status": "ok"}
        mock_client.post.return_value = mock_response

        result = _ingest_files([str(test_file)], metadata={"tag": "unit-test"})

        assert result["success"] is True
        assert result["ingested_count"] == 1
        assert result["error_count"] == 0
        assert result["results"][0]["path"] == str(test_file)

        mock_client.post.assert_called_once()
        _, kwargs = mock_client.post.call_args
        payload = kwargs["json"]
        assert payload["document_id"] == str(test_file.resolve())
        assert payload["metadata"]["filename"] == "document.txt"
        assert payload["metadata"]["tag"] == "unit-test"
        assert payload["content"] == "Sample content"
        assert payload["generate_embeddings"] is True
        assert payload["replace_existing"] is True

    @patch('graph_rag.mcp.server._client')
    def test_ingest_files_custom_flags(self, mock_client_factory, tmp_path):
        """Custom embedding/replace flags propagate to API payload."""
        test_file = tmp_path / "document.txt"
        test_file.write_text("Sample content", encoding="utf-8")

        mock_client = Mock()
        mock_client.__enter__ = Mock(return_value=mock_client)
        mock_client.__exit__ = Mock(return_value=None)
        mock_client_factory.return_value = mock_client

        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {"document_id": str(test_file)}
        mock_client.post.return_value = mock_response

        result = _ingest_files(
            [str(test_file)],
            embeddings=False,
            replace=False,
            metadata={"tag": "unit-test"},
        )

        assert result["success"] is True
        mock_client.post.assert_called_once()
        _, kwargs = mock_client.post.call_args
        payload = kwargs["json"]
        assert payload["generate_embeddings"] is False
        assert payload["replace_existing"] is False

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
    def test_delete_document_success(self, mock_client_factory):
        """Test successful document deletion with empty response body."""
        mock_client = Mock()
        mock_client.__enter__ = Mock(return_value=mock_client)
        mock_client.__exit__ = Mock(return_value=None)
        mock_client_factory.return_value = mock_client

        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_response.content = b""
        mock_client.delete.return_value = mock_response

        result = _delete_document("doc-123")

        assert result == {"deleted": True, "document_id": "doc-123"}
        mock_client.delete.assert_called_once()

    @patch('graph_rag.mcp.server._client')
    def test_delete_document_not_found(self, mock_client_factory):
        """Test delete document returns DOCUMENT_NOT_FOUND for 404."""
        mock_client = Mock()
        mock_client.__enter__ = Mock(return_value=mock_client)
        mock_client.__exit__ = Mock(return_value=None)
        mock_client_factory.return_value = mock_client

        mock_response = Mock()
        mock_response.status_code = 404
        http_error = httpx.HTTPStatusError("Not found", request=Mock(), response=mock_response)
        mock_client.delete.side_effect = http_error

        with pytest.raises(McpError) as exc_info:
            _delete_document("missing")

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


class TestHandlerWrapper:
    """Test wrapper logic around MCP tool handlers."""

    def test_wrap_handler_success(self):
        """Wrapper returns success payload with ISO timestamp."""
        schema = {
            "type": "object",
            "properties": {"name": {"type": "string"}},
            "required": ["name"],
        }

        def handler(name: str) -> dict[str, str]:
            return {"greeting": f"Hello {name}"}

        wrapped = _wrap_handler(handler, schema)
        result = wrapped(name="Synapse")

        assert result["success"] is True
        assert result["data"] == {"greeting": "Hello Synapse"}
        # Should be parseable ISO8601 timestamp
        datetime.fromisoformat(result["timestamp"])

    def test_wrap_handler_validation_error(self):
        """Wrapper surfaces validation errors without calling handler."""
        schema = {
            "type": "object",
            "properties": {"name": {"type": "string"}},
            "required": ["name"],
        }

        handler = Mock()
        wrapped = _wrap_handler(handler, schema)
        result = wrapped()

        assert result["success"] is False
        assert result["error"]["type"] == "validation_error"
        assert result["error"]["code"] == "VALIDATION_ERROR"
        handler.assert_not_called()

    def test_wrap_handler_connection_error(self):
        """Wrapper normalizes ConnectionError exceptions."""
        schema = {
            "type": "object",
            "properties": {"name": {"type": "string"}},
            "required": ["name"],
        }

        def handler(name: str) -> dict[str, str]:
            raise ConnectionError("failed", status_code=503)

        wrapped = _wrap_handler(handler, schema)
        result = wrapped(name="Synapse")

        assert result["success"] is False
        assert result["error"]["type"] == "connection_error"
        assert result["error"]["code"] == "CONNECTION_ERROR"
        assert result["error"]["details"]["status_code"] == 503


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


class TestNewEndpointCoverage:
    """Test recently added endpoints and parameter validation."""

    @patch('graph_rag.mcp.server._client')
    def test_search_with_threshold_parameter(self, mock_client_factory):
        """Test search endpoint with threshold parameter for similarity filtering."""
        mock_client = Mock()
        mock_client.__enter__ = Mock(return_value=mock_client)
        mock_client.__exit__ = Mock(return_value=None)
        mock_client_factory.return_value = mock_client

        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {"results": [{"chunk": {"text": "relevant"}, "score": 0.85}]}
        mock_client.post.return_value = mock_response

        result = _search("test query", threshold=0.8)

        assert result["threshold"] == 0.8
        mock_client.post.assert_called_once()
        _, kwargs = mock_client.post.call_args
        assert kwargs["json"]["threshold"] == 0.8

    @patch('graph_rag.mcp.server._client')
    def test_search_with_hybrid_search_type(self, mock_client_factory):
        """Test search endpoint with hybrid search type combining vector and keyword."""
        mock_client = Mock()
        mock_client.__enter__ = Mock(return_value=mock_client)
        mock_client.__exit__ = Mock(return_value=None)
        mock_client_factory.return_value = mock_client

        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {"results": []}
        mock_client.post.return_value = mock_response

        result = _search("test", search_type="hybrid", limit=15)

        assert result["search_type"] == "hybrid"
        assert result["limit"] == 15
        mock_client.post.assert_called_once()

    @patch('graph_rag.mcp.server._client')
    def test_query_answer_with_graph_context(self, mock_client_factory):
        """Test query answer endpoint with graph-based context inclusion."""
        mock_client = Mock()
        mock_client.__enter__ = Mock(return_value=mock_client)
        mock_client.__exit__ = Mock(return_value=None)
        mock_client_factory.return_value = mock_client

        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {
            "answer": "Graph-enhanced answer",
            "sources": [],
            "timestamp": "2023-01-01T00:00:00Z"
        }
        mock_client.post.return_value = mock_response

        result = _query_answer("What is graph RAG?", k=10, include_graph=True)

        assert result["include_graph"] is True
        assert result["k"] == 10
        mock_client.post.assert_called_once()
        _, kwargs = mock_client.post.call_args
        assert kwargs["json"]["include_graph"] is True

    @patch('graph_rag.mcp.server._client')
    def test_list_documents_with_pagination(self, mock_client_factory):
        """Test list documents with various pagination parameters."""
        mock_client = Mock()
        mock_client.__enter__ = Mock(return_value=mock_client)
        mock_client.__exit__ = Mock(return_value=None)
        mock_client_factory.return_value = mock_client

        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {"documents": [], "total": 100}
        mock_client.get.return_value = mock_response

        result = _list_documents(limit=50, offset=25)

        assert result["total"] == 100
        mock_client.get.assert_called_once()
        _, kwargs = mock_client.get.call_args
        assert kwargs["params"]["limit"] == 50
        assert kwargs["params"]["offset"] == 25

    @patch('graph_rag.mcp.server._client')
    def test_list_documents_empty_results(self, mock_client_factory):
        """Test list documents when no documents exist in the knowledge base."""
        mock_client = Mock()
        mock_client.__enter__ = Mock(return_value=mock_client)
        mock_client.__exit__ = Mock(return_value=None)
        mock_client_factory.return_value = mock_client

        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {"documents": [], "total": 0}
        mock_client.get.return_value = mock_response

        result = _list_documents(limit=10, offset=0)

        assert len(result["documents"]) == 0
        assert result["total"] == 0

    @patch('graph_rag.mcp.server._client')
    def test_get_document_success(self, mock_client_factory):
        """Test successful document retrieval with full metadata."""
        mock_client = Mock()
        mock_client.__enter__ = Mock(return_value=mock_client)
        mock_client.__exit__ = Mock(return_value=None)
        mock_client_factory.return_value = mock_client

        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {
            "document_id": "doc-123",
            "content": "Document content",
            "metadata": {"source": "test", "tags": ["important"]}
        }
        mock_client.get.return_value = mock_response

        result = _get_document("doc-123")

        assert result["document_id"] == "doc-123"
        assert result["content"] == "Document content"
        assert result["metadata"]["tags"] == ["important"]
        mock_client.get.assert_called_once()

    @patch('graph_rag.mcp.server._client')
    def test_system_status_with_performance_metrics(self, mock_client_factory):
        """Test system status includes optional performance and cache metrics."""
        mock_client = Mock()
        mock_client.__enter__ = Mock(return_value=mock_client)
        mock_client.__exit__ = Mock(return_value=None)
        mock_client_factory.return_value = mock_client

        def mock_get(url, **kwargs):
            if "health" in url and "detailed" not in url:
                mock_resp = Mock()
                mock_resp.raise_for_status.return_value = None
                mock_resp.json.return_value = {"status": "healthy"}
                return mock_resp
            elif "performance" in url:
                mock_resp = Mock()
                mock_resp.status_code = 200
                mock_resp.json.return_value = {"avg_response_time_ms": 45.3}
                return mock_resp
            elif "cache" in url:
                mock_resp = Mock()
                mock_resp.status_code = 200
                mock_resp.json.return_value = {"hit_rate": 0.85}
                return mock_resp
            else:
                mock_resp = Mock()
                mock_resp.status_code = 200
                mock_resp.json.return_value = {}
                return mock_resp

        mock_client.get.side_effect = mock_get

        result = _system_status()

        assert result["health"]["status"] == "healthy"
        assert "performance" in result
        assert "cache" in result
        assert result["performance"]["avg_response_time_ms"] == 45.3
        assert result["cache"]["hit_rate"] == 0.85

    @patch('graph_rag.mcp.server._client')
    def test_search_with_keyword_type(self, mock_client_factory):
        """Test search endpoint with keyword search type."""
        mock_client = Mock()
        mock_client.__enter__ = Mock(return_value=mock_client)
        mock_client.__exit__ = Mock(return_value=None)
        mock_client_factory.return_value = mock_client

        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {"results": [{"chunk": {"text": "keyword match"}, "score": 1.0}]}
        mock_client.post.return_value = mock_response

        result = _search("exact phrase", search_type="keyword")

        assert result["search_type"] == "keyword"
        assert result["results_count"] == 1


class TestErrorScenarios:
    """Test comprehensive error scenarios and edge cases."""

    def test_validate_malformed_metadata(self):
        """Test validation with malformed metadata object."""
        # Metadata should be an object, but we pass a string
        valid_schema = INGEST_FILES_SCHEMA.copy()
        invalid_input = {
            "paths": ["/test/path.txt"],
            "metadata": "not_an_object"
        }

        # This should not raise since we allow additional properties
        # But in real scenario, API would reject this
        result = _validate_input(invalid_input, valid_schema)
        # Validation passes malformed metadata through since additionalProperties is True
        assert result["metadata"] == "not_an_object"

    @patch('graph_rag.mcp.server._client')
    def test_search_with_invalid_http_status(self, mock_client_factory):
        """Test search with 500 Internal Server Error response."""
        mock_client = Mock()
        mock_client.__enter__ = Mock(return_value=mock_client)
        mock_client.__exit__ = Mock(return_value=None)
        mock_client_factory.return_value = mock_client

        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.text = "Internal server error: Database connection failed"
        http_error = httpx.HTTPStatusError("Server error", request=Mock(), response=mock_response)
        mock_client.post.side_effect = http_error

        with pytest.raises(ConnectionError) as exc_info:
            _search("test query")

        assert exc_info.value.code == "CONNECTION_ERROR"
        assert exc_info.value.details["status_code"] == 500
        assert "Internal server error" in str(exc_info.value)

    @patch('graph_rag.mcp.server._client')
    def test_query_answer_timeout(self, mock_client_factory):
        """Test query answer with timeout error for long-running operations."""
        mock_client = Mock()
        mock_client.__enter__ = Mock(return_value=mock_client)
        mock_client.__exit__ = Mock(return_value=None)
        mock_client_factory.return_value = mock_client

        mock_client.post.side_effect = httpx.TimeoutException("Request timeout")

        with pytest.raises(McpError) as exc_info:
            _query_answer("complex question requiring long processing")

        assert "Unexpected error during query" in str(exc_info.value)

    def test_validate_negative_integer_values(self):
        """Test validation rejects negative values for positive-only integer fields."""
        invalid_input = {"query": "test", "limit": -5}

        with pytest.raises(ValidationError) as exc_info:
            _validate_input(invalid_input, SEARCH_SCHEMA)

        assert "must be >= 1" in str(exc_info.value)
        assert exc_info.value.details["field"] == "limit"

    def test_validate_exceeds_maximum_limit(self):
        """Test validation rejects values exceeding maximum limits."""
        invalid_input = {"query": "test", "limit": 150}

        with pytest.raises(ValidationError) as exc_info:
            _validate_input(invalid_input, SEARCH_SCHEMA)

        assert "must be <= 100" in str(exc_info.value)
        assert exc_info.value.details["field"] == "limit"

    @patch('graph_rag.mcp.server._client')
    def test_ingest_files_with_http_400_error(self, mock_client_factory, tmp_path):
        """Test ingest files handles 400 Bad Request errors gracefully."""
        test_file = tmp_path / "bad_content.txt"
        test_file.write_text("Content", encoding="utf-8")

        mock_client = Mock()
        mock_client.__enter__ = Mock(return_value=mock_client)
        mock_client.__exit__ = Mock(return_value=None)
        mock_client_factory.return_value = mock_client

        mock_response = Mock()
        mock_response.status_code = 400
        mock_response.text = "Invalid document format"
        http_error = httpx.HTTPStatusError("Bad request", request=Mock(), response=mock_response)
        mock_client.post.side_effect = http_error

        result = _ingest_files([str(test_file)])

        assert result["success"] is False
        assert result["error_count"] == 1
        assert result["errors"][0]["error"] == "api_error"
        assert result["errors"][0]["status_code"] == 400


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    @patch('graph_rag.mcp.server._client')
    def test_ingest_files_with_empty_content(self, mock_client_factory, tmp_path):
        """Test ingesting files with empty content (warning logged but processed)."""
        test_file = tmp_path / "empty.txt"
        test_file.write_text("", encoding="utf-8")

        mock_client = Mock()
        mock_client.__enter__ = Mock(return_value=mock_client)
        mock_client.__exit__ = Mock(return_value=None)
        mock_client_factory.return_value = mock_client

        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {"document_id": str(test_file)}
        mock_client.post.return_value = mock_response

        result = _ingest_files([str(test_file)])

        assert result["success"] is True
        assert result["ingested_count"] == 1
        mock_client.post.assert_called_once()
        _, kwargs = mock_client.post.call_args
        assert kwargs["json"]["content"] == ""

    @patch('graph_rag.mcp.server.Path')
    @patch('graph_rag.mcp.server._client')
    def test_ingest_files_with_directory_path(self, mock_client_factory, mock_path):
        """Test ingest files rejects directory paths (not files)."""
        mock_path.return_value.exists.return_value = True
        mock_path.return_value.is_file.return_value = False
        mock_path.return_value.__str__ = Mock(return_value="/test/directory")

        result = _ingest_files(["/test/directory"])

        assert result["success"] is False
        assert result["error_count"] == 1
        assert result["errors"][0]["error"] == "not_a_file"

    @patch('graph_rag.mcp.server._client')
    def test_search_with_maximum_limit(self, mock_client_factory):
        """Test search endpoint with maximum allowed limit (boundary test)."""
        mock_client = Mock()
        mock_client.__enter__ = Mock(return_value=mock_client)
        mock_client.__exit__ = Mock(return_value=None)
        mock_client_factory.return_value = mock_client

        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {"results": []}
        mock_client.post.return_value = mock_response

        result = _search("test", limit=100)  # Maximum allowed limit

        assert result["limit"] == 100
        assert result["results_count"] == 0

    @patch('graph_rag.mcp.server._client')
    def test_delete_document_with_special_characters_in_id(self, mock_client_factory):
        """Test delete document with special characters in document ID."""
        mock_client = Mock()
        mock_client.__enter__ = Mock(return_value=mock_client)
        mock_client.__exit__ = Mock(return_value=None)
        mock_client_factory.return_value = mock_client

        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_response.content = b""
        mock_client.delete.return_value = mock_response

        doc_id = "doc-123-abc_XYZ.test@example.com"
        result = _delete_document(doc_id)

        assert result["deleted"] is True
        assert result["document_id"] == doc_id

    @patch('graph_rag.mcp.server._client')
    def test_system_status_partial_failure(self, mock_client_factory):
        """Test system status when some optional endpoints fail gracefully."""
        mock_client = Mock()
        mock_client.__enter__ = Mock(return_value=mock_client)
        mock_client.__exit__ = Mock(return_value=None)
        mock_client_factory.return_value = mock_client

        def mock_get(url, **kwargs):
            if "health" in url and "detailed" not in url:
                mock_resp = Mock()
                mock_resp.raise_for_status.return_value = None
                mock_resp.json.return_value = {"status": "healthy"}
                return mock_resp
            elif "performance" in url:
                # Performance endpoint fails
                raise httpx.ConnectError("Performance service unavailable")
            elif "cache" in url:
                mock_resp = Mock()
                mock_resp.status_code = 200
                mock_resp.json.return_value = {"hit_rate": 0.90}
                return mock_resp
            else:
                mock_resp = Mock()
                mock_resp.status_code = 200
                mock_resp.json.return_value = {}
                return mock_resp

        mock_client.get.side_effect = mock_get

        result = _system_status()

        # Should succeed with partial data
        assert result["health"]["status"] == "healthy"
        assert "performance" not in result  # Failed endpoint excluded
        assert "cache" in result
        assert result["cache"]["hit_rate"] == 0.90

    def test_wrap_handler_with_generic_exception(self):
        """Test handler wrapper catches and formats generic exceptions."""
        schema = {
            "type": "object",
            "properties": {"name": {"type": "string"}},
            "required": ["name"],
        }

        def handler(name: str) -> dict[str, str]:
            raise RuntimeError("Unexpected runtime error")

        wrapped = _wrap_handler(handler, schema)
        result = wrapped(name="test")

        assert result["success"] is False
        assert result["error"]["type"] == "internal_error"
        assert result["error"]["code"] == "INTERNAL_ERROR"
        assert "Unexpected runtime error" in result["error"]["message"]

    def test_validate_empty_string_with_min_length(self):
        """Test validation rejects empty strings when minLength is specified."""
        invalid_input = {"query": "", "limit": 10}

        with pytest.raises(ValidationError) as exc_info:
            _validate_input(invalid_input, SEARCH_SCHEMA)

        assert "must be at least 1 characters" in str(exc_info.value)
        assert exc_info.value.details["field"] == "query"
