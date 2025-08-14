"""MCP server implementation for Synapse GraphRAG system.

Exposes comprehensive tools for IDE integration:
- ingest_files: Ingest documents into the knowledge base with metadata
- search: Search documents and chunks with various strategies
- query_answer: Ask questions and get synthesized answers with sources

Provides proper error handling, schema validation, and MCP protocol compliance.
Designed for seamless integration with VS Code, Claude IDE, and other MCP clients.
"""
from __future__ import annotations

import json
import logging
import os
import sys
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import httpx

DEFAULT_BASE = os.getenv("SYNAPSE_API_BASE_URL", "http://localhost:8000")
API_V1 = f"{DEFAULT_BASE.rstrip('/')}/api/v1"

# Configure logging
logger = logging.getLogger(__name__)

# MCP tool input schemas
INGEST_FILES_SCHEMA = {
    "type": "object",
    "properties": {
        "paths": {
            "type": "array",
            "items": {"type": "string"},
            "description": "List of file paths to ingest",
            "minItems": 1
        },
        "embeddings": {
            "type": "boolean",
            "description": "Whether to generate embeddings for the documents",
            "default": True
        },
        "replace": {
            "type": "boolean",
            "description": "Whether to replace existing documents with same ID",
            "default": True
        },
        "metadata": {
            "type": "object",
            "description": "Additional metadata to attach to all documents",
            "additionalProperties": True
        }
    },
    "required": ["paths"]
}

SEARCH_SCHEMA = {
    "type": "object",
    "properties": {
        "query": {
            "type": "string",
            "description": "Search query text",
            "minLength": 1
        },
        "limit": {
            "type": "integer",
            "description": "Maximum number of results to return",
            "default": 10,
            "minimum": 1,
            "maximum": 100
        },
        "search_type": {
            "type": "string",
            "enum": ["vector", "keyword", "hybrid"],
            "description": "Type of search to perform",
            "default": "vector"
        },
        "threshold": {
            "type": "number",
            "description": "Similarity threshold for filtering results",
            "minimum": 0.0,
            "maximum": 1.0
        }
    },
    "required": ["query"]
}

QUERY_ANSWER_SCHEMA = {
    "type": "object",
    "properties": {
        "question": {
            "type": "string",
            "description": "Question to ask the system",
            "minLength": 1
        },
        "k": {
            "type": "integer",
            "description": "Number of relevant chunks to retrieve",
            "default": 5,
            "minimum": 1,
            "maximum": 20
        },
        "include_graph": {
            "type": "boolean",
            "description": "Whether to include graph-based context in the answer",
            "default": False
        },
        "stream": {
            "type": "boolean",
            "description": "Whether to stream the response (not supported in MCP)",
            "default": False
        }
    },
    "required": ["question"]
}

LIST_DOCUMENTS_SCHEMA = {
    "type": "object",
    "properties": {
        "limit": {
            "type": "integer",
            "description": "Maximum number of documents to return",
            "default": 20,
            "minimum": 1,
            "maximum": 100
        },
        "offset": {
            "type": "integer",
            "description": "Number of documents to skip",
            "default": 0,
            "minimum": 0
        }
    }
}

GET_DOCUMENT_SCHEMA = {
    "type": "object",
    "properties": {
        "document_id": {
            "type": "string",
            "description": "ID of the document to retrieve",
            "minLength": 1
        }
    },
    "required": ["document_id"]
}

DELETE_DOCUMENT_SCHEMA = {
    "type": "object",
    "properties": {
        "document_id": {
            "type": "string",
            "description": "ID of the document to delete",
            "minLength": 1
        }
    },
    "required": ["document_id"]
}

SYSTEM_STATUS_SCHEMA = {
    "type": "object",
    "properties": {}
}


@dataclass
class McpTool:
    name: str
    description: str
    handler: Callable[..., Any]
    input_schema: dict[str, Any]


class McpError(Exception):
    """Base exception for MCP server errors."""

    def __init__(self, message: str, code: str = "INTERNAL_ERROR", details: dict | None = None):
        self.message = message
        self.code = code
        self.details = details or {}
        super().__init__(message)


class ValidationError(McpError):
    """Exception for input validation errors."""

    def __init__(self, message: str, field: str | None = None):
        super().__init__(message, "VALIDATION_ERROR", {"field": field})


class ConnectionError(McpError):
    """Exception for API connection errors."""

    def __init__(self, message: str, status_code: int | None = None):
        super().__init__(message, "CONNECTION_ERROR", {"status_code": status_code})


def _client() -> httpx.Client:
    """Create HTTP client with proper timeout and error handling."""
    return httpx.Client(
        timeout=httpx.Timeout(30.0, connect=10.0),
        follow_redirects=True,
        headers={"User-Agent": "Synapse-MCP/1.0"}
    )


def _validate_input(data: dict[str, Any], schema: dict[str, Any]) -> dict[str, Any]:
    """Basic input validation against JSON schema."""
    required = schema.get("required", [])
    properties = schema.get("properties", {})

    # Check required fields
    for field in required:
        if field not in data:
            raise ValidationError(f"Missing required field: {field}", field)

    # Basic type validation
    validated = {}
    for key, value in data.items():
        if key in properties:
            prop_schema = properties[key]
            prop_type = prop_schema.get("type")

            # Type checking
            if prop_type == "string" and not isinstance(value, str):
                raise ValidationError(f"Field {key} must be a string", key)
            elif prop_type == "integer" and not isinstance(value, int):
                raise ValidationError(f"Field {key} must be an integer", key)
            elif prop_type == "boolean" and not isinstance(value, bool):
                raise ValidationError(f"Field {key} must be a boolean", key)
            elif prop_type == "array" and not isinstance(value, list):
                raise ValidationError(f"Field {key} must be an array", key)

            # Range validation
            if prop_type == "integer":
                min_val = prop_schema.get("minimum")
                max_val = prop_schema.get("maximum")
                if min_val is not None and value < min_val:
                    raise ValidationError(f"Field {key} must be >= {min_val}", key)
                if max_val is not None and value > max_val:
                    raise ValidationError(f"Field {key} must be <= {max_val}", key)

            # String length validation
            if prop_type == "string":
                min_len = prop_schema.get("minLength")
                if min_len is not None and len(value) < min_len:
                    raise ValidationError(f"Field {key} must be at least {min_len} characters", key)

            # Array length validation
            if prop_type == "array":
                min_items = prop_schema.get("minItems")
                if min_items is not None and len(value) < min_items:
                    raise ValidationError(f"Field {key} must have at least {min_items} items", key)

            # Enum validation
            enum_values = prop_schema.get("enum")
            if enum_values and value not in enum_values:
                raise ValidationError(f"Field {key} must be one of: {', '.join(enum_values)}", key)

            validated[key] = value
        else:
            # Allow additional properties for metadata
            validated[key] = value

    # Set defaults
    for key, prop_schema in properties.items():
        if key not in validated and "default" in prop_schema:
            validated[key] = prop_schema["default"]

    return validated


def _ingest_files(paths: list[str], embeddings: bool = True, replace: bool = True, metadata: dict | None = None) -> dict[str, Any]:
    """Read files and POST to /ingestion/documents.

    Args:
        paths: List of file paths to ingest
        embeddings: Whether to generate embeddings
        replace: Whether to replace existing documents
        metadata: Additional metadata to attach to documents

    Returns:
        Dict with success status, results, and error details
    """
    logger.info(f"Ingesting {len(paths)} files with embeddings={embeddings}, replace={replace}")

    results = []
    errors = []
    url = f"{API_V1}/ingestion/documents"

    try:
        with _client() as client:
            for p in paths:
                path = Path(p)

                # Validate file exists and is readable
                if not path.exists():
                    error = {"path": str(path), "error": "file_not_found", "message": f"File does not exist: {path}"}
                    errors.append(error)
                    continue

                if not path.is_file():
                    error = {"path": str(path), "error": "not_a_file", "message": f"Path is not a file: {path}"}
                    errors.append(error)
                    continue

                try:
                    # Read file content
                    content = path.read_text(encoding="utf-8")
                    if not content.strip():
                        logger.warning(f"File is empty: {path}")

                    # Prepare metadata
                    file_metadata = {"source": "mcp", "path": str(path.absolute()), "filename": path.name}
                    if metadata:
                        file_metadata.update(metadata)

                    # Prepare payload
                    payload = {
                        "document_id": str(path.absolute()),
                        "content": content,
                        "metadata": file_metadata,
                    }

                    # Make API call
                    logger.debug(f"Posting document: {path}")
                    response = client.post(url, json=payload)
                    response.raise_for_status()

                    result = response.json()
                    result["path"] = str(path)
                    results.append(result)
                    logger.info(f"Successfully ingested: {path}")

                except UnicodeDecodeError as e:
                    error = {"path": str(path), "error": "encoding_error", "message": f"Cannot read file as UTF-8: {e}"}
                    errors.append(error)
                except httpx.HTTPStatusError as e:
                    error_msg = f"HTTP {e.response.status_code}: {e.response.text[:200]}"
                    error = {"path": str(path), "error": "api_error", "status_code": e.response.status_code, "message": error_msg}
                    errors.append(error)
                except Exception as e:
                    error = {"path": str(path), "error": "unexpected_error", "message": str(e)}
                    errors.append(error)

    except httpx.ConnectError:
        raise ConnectionError(f"Cannot connect to Synapse API at {API_V1}. Is the server running?")
    except Exception as e:
        raise McpError(f"Unexpected error during ingestion: {e}")

    return {
        "success": len(errors) == 0,
        "ingested_count": len(results),
        "error_count": len(errors),
        "results": results,
        "errors": errors
    }


def _search(query: str, limit: int = 10, search_type: str = "vector", threshold: float | None = None) -> dict[str, Any]:
    """Search for relevant chunks using various strategies.

    Args:
        query: Search query text
        limit: Maximum number of results
        search_type: Type of search (vector, keyword, hybrid)
        threshold: Similarity threshold for filtering

    Returns:
        Search results with chunks, scores, and metadata
    """
    logger.info(f"Searching with query='{query[:50]}...', type={search_type}, limit={limit}")

    url = f"{API_V1}/search/query"
    payload = {
        "query": query,
        "search_type": search_type,
        "limit": limit,
        "stream": False
    }

    if threshold is not None:
        payload["threshold"] = threshold

    try:
        with _client() as client:
            response = client.post(url, json=payload)
            response.raise_for_status()

            result = response.json()

            # Enhance result with metadata
            enhanced_result = {
                "query": query,
                "search_type": search_type,
                "limit": limit,
                "threshold": threshold,
                "results_count": len(result.get("results", [])),
                **result
            }

            logger.info(f"Found {enhanced_result['results_count']} results")
            return enhanced_result

    except httpx.HTTPStatusError as e:
        error_msg = f"Search failed with HTTP {e.response.status_code}: {e.response.text[:200]}"
        raise ConnectionError(error_msg, e.response.status_code)
    except httpx.ConnectError:
        raise ConnectionError(f"Cannot connect to Synapse API at {API_V1}. Is the server running?")
    except Exception as e:
        raise McpError(f"Unexpected error during search: {e}")


def _query_answer(question: str, k: int = 5, include_graph: bool = False, stream: bool = False) -> dict[str, Any]:
    """Ask a question and get a synthesized answer with sources.

    Args:
        question: Question to ask the system
        k: Number of relevant chunks to retrieve
        include_graph: Whether to include graph context
        stream: Whether to stream response (not supported in MCP)

    Returns:
        Answer with sources, confidence, and metadata
    """
    logger.info(f"Answering question: '{question[:50]}...', k={k}, graph={include_graph}")

    url = f"{API_V1}/query/ask"
    payload = {
        "text": question,
        "k": k,
        "include_graph": include_graph,
        "stream": False  # MCP doesn't support streaming
    }

    try:
        with _client() as client:
            response = client.post(url, json=payload)
            response.raise_for_status()

            result = response.json()

            # Enhance result with metadata
            enhanced_result = {
                "question": question,
                "k": k,
                "include_graph": include_graph,
                "timestamp": result.get("timestamp"),
                **result
            }

            logger.info(f"Generated answer with {len(result.get('sources', []))} sources")
            return enhanced_result

    except httpx.HTTPStatusError as e:
        error_msg = f"Query failed with HTTP {e.response.status_code}: {e.response.text[:200]}"
        raise ConnectionError(error_msg, e.response.status_code)
    except httpx.ConnectError:
        raise ConnectionError(f"Cannot connect to Synapse API at {API_V1}. Is the server running?")
    except Exception as e:
        raise McpError(f"Unexpected error during query: {e}")


def _list_documents(limit: int = 20, offset: int = 0) -> dict[str, Any]:
    """List documents in the knowledge base with pagination."""
    logger.info(f"Listing documents: limit={limit}, offset={offset}")

    url = f"{API_V1}/documents/"
    params = {"limit": limit, "offset": offset}

    try:
        with _client() as client:
            response = client.get(url, params=params)
            response.raise_for_status()

            result = response.json()
            logger.info(f"Found {len(result.get('documents', []))} documents")
            return result

    except httpx.HTTPStatusError as e:
        error_msg = f"List documents failed with HTTP {e.response.status_code}: {e.response.text[:200]}"
        raise ConnectionError(error_msg, e.response.status_code)
    except httpx.ConnectError:
        raise ConnectionError(f"Cannot connect to Synapse API at {API_V1}. Is the server running?")
    except Exception as e:
        raise McpError(f"Unexpected error listing documents: {e}")


def _get_document(document_id: str) -> dict[str, Any]:
    """Get a specific document by ID."""
    logger.info(f"Getting document: {document_id}")

    url = f"{API_V1}/documents/{document_id}"

    try:
        with _client() as client:
            response = client.get(url)
            response.raise_for_status()

            result = response.json()
            logger.info(f"Retrieved document: {document_id}")
            return result

    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            raise McpError(f"Document not found: {document_id}", "DOCUMENT_NOT_FOUND")
        error_msg = f"Get document failed with HTTP {e.response.status_code}: {e.response.text[:200]}"
        raise ConnectionError(error_msg, e.response.status_code)
    except httpx.ConnectError:
        raise ConnectionError(f"Cannot connect to Synapse API at {API_V1}. Is the server running?")
    except Exception as e:
        raise McpError(f"Unexpected error getting document: {e}")


def _delete_document(document_id: str) -> dict[str, Any]:
    """Delete a document from the knowledge base."""
    logger.info(f"Deleting document: {document_id}")

    url = f"{API_V1}/documents/{document_id}"

    try:
        with _client() as client:
            response = client.delete(url)
            response.raise_for_status()

            result = response.json() if response.content else {"deleted": True, "document_id": document_id}
            logger.info(f"Deleted document: {document_id}")
            return result

    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            raise McpError(f"Document not found: {document_id}", "DOCUMENT_NOT_FOUND")
        error_msg = f"Delete document failed with HTTP {e.response.status_code}: {e.response.text[:200]}"
        raise ConnectionError(error_msg, e.response.status_code)
    except httpx.ConnectError:
        raise ConnectionError(f"Cannot connect to Synapse API at {API_V1}. Is the server running?")
    except Exception as e:
        raise McpError(f"Unexpected error deleting document: {e}")


def _system_status() -> dict[str, Any]:
    """Get comprehensive system status and health information."""
    logger.info("Getting system status")

    try:
        with _client() as client:
            # Get basic health
            health_url = f"{DEFAULT_BASE}/health"
            health_response = client.get(health_url)
            health_response.raise_for_status()
            health_data = health_response.json()

            # Try to get detailed health if available
            detailed_health = {}
            try:
                detailed_url = f"{API_V1}/admin/health/detailed"
                detailed_response = client.get(detailed_url, timeout=15.0)
                if detailed_response.status_code == 200:
                    detailed_health = detailed_response.json()
            except Exception:
                pass  # Detailed health is optional

            # Try to get performance stats
            performance_stats = {}
            try:
                perf_url = f"{API_V1}/admin/performance/stats"
                perf_response = client.get(perf_url)
                if perf_response.status_code == 200:
                    performance_stats = perf_response.json()
            except Exception:
                pass  # Performance stats are optional

            # Try to get cache stats
            cache_stats = {}
            try:
                cache_url = f"{API_V1}/admin/cache/stats"
                cache_response = client.get(cache_url)
                if cache_response.status_code == 200:
                    cache_stats = cache_response.json()
            except Exception:
                pass  # Cache stats are optional

            status = {
                "health": health_data,
                "api_base_url": DEFAULT_BASE,
                "api_v1_url": API_V1,
                "mcp_server": "connected"
            }

            if detailed_health:
                status["detailed_health"] = detailed_health
            if performance_stats:
                status["performance"] = performance_stats
            if cache_stats:
                status["cache"] = cache_stats

            logger.info("Retrieved comprehensive system status")
            return status

    except httpx.HTTPStatusError as e:
        error_msg = f"System status failed with HTTP {e.response.status_code}: {e.response.text[:200]}"
        raise ConnectionError(error_msg, e.response.status_code)
    except httpx.ConnectError:
        raise ConnectionError(f"Cannot connect to Synapse API at {DEFAULT_BASE}. Is the server running?")
    except Exception as e:
        raise McpError(f"Unexpected error getting system status: {e}")


def _wrap_handler(handler: Callable, schema: dict[str, Any]) -> Callable:
    """Wrap a handler function with input validation and error handling."""

    def wrapper(**kwargs) -> dict[str, Any]:
        try:
            # Validate input
            validated_input = _validate_input(kwargs, schema)

            # Call handler
            result = handler(**validated_input)

            # Ensure result is JSON serializable
            return {
                "success": True,
                "data": result,
                "timestamp": json.dumps(None)  # Will be replaced by actual timestamp
            }

        except ValidationError as e:
            logger.error(f"Validation error: {e.message}")
            return {
                "success": False,
                "error": {
                    "type": "validation_error",
                    "message": e.message,
                    "code": e.code,
                    "details": e.details
                }
            }
        except ConnectionError as e:
            logger.error(f"Connection error: {e.message}")
            return {
                "success": False,
                "error": {
                    "type": "connection_error",
                    "message": e.message,
                    "code": e.code,
                    "details": e.details
                }
            }
        except McpError as e:
            logger.error(f"MCP error: {e.message}")
            return {
                "success": False,
                "error": {
                    "type": "mcp_error",
                    "message": e.message,
                    "code": e.code,
                    "details": e.details
                }
            }
        except Exception as e:
            logger.error(f"Unexpected error: {e}", exc_info=True)
            return {
                "success": False,
                "error": {
                    "type": "internal_error",
                    "message": f"Internal server error: {str(e)}",
                    "code": "INTERNAL_ERROR"
                }
            }

    return wrapper


def make_tools() -> list[McpTool]:
    """Create MCP tools with proper validation and error handling."""
    return [
        McpTool(
            name="ingest_files",
            description="Ingest documents into the Synapse knowledge base. Supports various file formats and automatically generates embeddings for vector search.",
            handler=_wrap_handler(_ingest_files, INGEST_FILES_SCHEMA),
            input_schema=INGEST_FILES_SCHEMA
        ),
        McpTool(
            name="search",
            description="Search for relevant chunks in the knowledge base. Supports vector similarity search, keyword search, and hybrid approaches.",
            handler=_wrap_handler(_search, SEARCH_SCHEMA),
            input_schema=SEARCH_SCHEMA
        ),
        McpTool(
            name="query_answer",
            description="Ask questions and get synthesized answers with source citations. Combines retrieval with language model generation for comprehensive responses.",
            handler=_wrap_handler(_query_answer, QUERY_ANSWER_SCHEMA),
            input_schema=QUERY_ANSWER_SCHEMA
        ),
        McpTool(
            name="list_documents",
            description="List all documents in the knowledge base with pagination support. Useful for exploring the document collection.",
            handler=_wrap_handler(_list_documents, LIST_DOCUMENTS_SCHEMA),
            input_schema=LIST_DOCUMENTS_SCHEMA
        ),
        McpTool(
            name="get_document",
            description="Retrieve a specific document by its ID. Returns the full document content and metadata.",
            handler=_wrap_handler(_get_document, GET_DOCUMENT_SCHEMA),
            input_schema=GET_DOCUMENT_SCHEMA
        ),
        McpTool(
            name="delete_document",
            description="Delete a document from the knowledge base. This will remove the document and all its associated chunks and embeddings.",
            handler=_wrap_handler(_delete_document, DELETE_DOCUMENT_SCHEMA),
            input_schema=DELETE_DOCUMENT_SCHEMA
        ),
        McpTool(
            name="system_status",
            description="Get comprehensive system status including health, performance metrics, and cache statistics. Useful for monitoring system health.",
            handler=_wrap_handler(_system_status, SYSTEM_STATUS_SCHEMA),
            input_schema=SYSTEM_STATUS_SCHEMA
        ),
    ]


def serve(host: str = "127.0.0.1", port: int = 8765, transport: str = "tcp") -> None:
    """Start an MCP server with comprehensive tool support.

    Args:
        host: Host to bind to (for TCP transport)
        port: Port to bind to (for TCP transport)
        transport: Transport type ('tcp' or 'stdio')

    Note: This is a long-lived process. Designed for production environments.
    Tests should import and use `make_tools` instead of invoking `serve`.
    """
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        stream=sys.stderr
    )

    logger.info(f"Starting Synapse MCP server on {transport}://{host}:{port}")

    try:
        # Deferred imports to avoid hard dependency
        from mcp.server import Server
        from mcp.types import Tool
    except ImportError as e:  # pragma: no cover
        error_msg = (
            "MCP package is not installed. Install with: pip install 'synapse-graph-rag[mcp]'"
        )
        logger.error(error_msg)
        raise RuntimeError(error_msg) from e

    # Test API connectivity
    try:
        with _client() as client:
            health_url = f"{DEFAULT_BASE}/health"
            response = client.get(health_url)
            response.raise_for_status()
            logger.info(f"Successfully connected to Synapse API at {DEFAULT_BASE}")
    except Exception as e:
        logger.warning(f"Cannot reach Synapse API at {DEFAULT_BASE}: {e}")
        logger.warning("MCP server will start but tools may fail until API is available")

    # Create server
    server = Server("synapse-graph-rag")
    tools = make_tools()

    logger.info(f"Registering {len(tools)} MCP tools")

    # Register tools with detailed schemas
    for tool in tools:
        server.add_tool(
            Tool(
                name=tool.name,
                description=tool.description,
                inputSchema=tool.input_schema,
            ),
            tool.handler,
        )
        logger.info(f"Registered tool: {tool.name}")

    # Start server
    try:
        if transport == "stdio":
            logger.info("Starting MCP server with stdio transport")
            server.run_stdio()
        else:
            logger.info(f"Starting MCP server on {host}:{port}")
            server.run_tcp(host=host, port=port)
    except KeyboardInterrupt:
        logger.info("MCP server shutting down")
    except Exception as e:
        logger.error(f"MCP server error: {e}")
        raise


def health_check() -> dict[str, Any]:
    """Check health of MCP server dependencies."""
    status = {
        "mcp_available": False,
        "api_available": False,
        "tools_count": 0,
        "errors": []
    }

    # Check MCP package
    try:
        import mcp
        status["mcp_available"] = True
        status["mcp_version"] = getattr(mcp, "__version__", "unknown")
    except ImportError:
        status["errors"].append("MCP package not installed")

    # Check API connectivity
    try:
        with _client() as client:
            health_url = f"{DEFAULT_BASE}/health"
            response = client.get(health_url, timeout=5.0)
            response.raise_for_status()
            status["api_available"] = True
            status["api_url"] = DEFAULT_BASE
    except Exception as e:
        status["errors"].append(f"API not available: {e}")

    # Count available tools
    try:
        tools = make_tools()
        status["tools_count"] = len(tools)
        status["tools"] = [t.name for t in tools]
    except Exception as e:
        status["errors"].append(f"Error loading tools: {e}")

    status["healthy"] = status["mcp_available"] and status["api_available"] and status["tools_count"] > 0

    return status
