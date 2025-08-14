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
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Union

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


@dataclass
class McpTool:
    name: str
    description: str
    handler: Callable[..., Any]
    input_schema: Dict[str, Any]


class McpError(Exception):
    """Base exception for MCP server errors."""
    
    def __init__(self, message: str, code: str = "INTERNAL_ERROR", details: Optional[Dict] = None):
        self.message = message
        self.code = code
        self.details = details or {}
        super().__init__(message)


class ValidationError(McpError):
    """Exception for input validation errors."""
    
    def __init__(self, message: str, field: Optional[str] = None):
        super().__init__(message, "VALIDATION_ERROR", {"field": field})


class ConnectionError(McpError):
    """Exception for API connection errors."""
    
    def __init__(self, message: str, status_code: Optional[int] = None):
        super().__init__(message, "CONNECTION_ERROR", {"status_code": status_code})


def _client() -> httpx.Client:
    """Create HTTP client with proper timeout and error handling."""
    return httpx.Client(
        timeout=httpx.Timeout(30.0, connect=10.0),
        follow_redirects=True,
        headers={"User-Agent": "Synapse-MCP/1.0"}
    )


def _validate_input(data: Dict[str, Any], schema: Dict[str, Any]) -> Dict[str, Any]:
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


def _ingest_files(paths: List[str], embeddings: bool = True, replace: bool = True, metadata: Optional[Dict] = None) -> Dict[str, Any]:
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


def _search(query: str, limit: int = 10, search_type: str = "vector", threshold: Optional[float] = None) -> Dict[str, Any]:
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


def _query_answer(question: str, k: int = 5, include_graph: bool = False, stream: bool = False) -> Dict[str, Any]:
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


def _wrap_handler(handler: Callable, schema: Dict[str, Any]) -> Callable:
    """Wrap a handler function with input validation and error handling."""
    
    def wrapper(**kwargs) -> Dict[str, Any]:
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


def make_tools() -> List[McpTool]:
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


def health_check() -> Dict[str, Any]:
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