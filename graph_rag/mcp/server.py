"""
Minimal MCP server skeleton and tool adapters for Synapse.

Exposes tools:
- ingest_files(paths: list[str], embeddings: bool, replace: bool)
- search(query: str, limit: int = 10, search_type: str = "vector")
- query_answer(text: str, k: int = 5, include_graph: bool = False)

If the optional `mcp` package is available, `serve()` will start an MCP server
that registers these tools. Otherwise, this module still provides `make_tools`
for direct invocation or testing.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, List

import httpx

DEFAULT_BASE = os.getenv("SYNAPSE_API_BASE_URL", "http://localhost:8000")
API_V1 = f"{DEFAULT_BASE.rstrip('/')}/api/v1"


@dataclass
class McpTool:
    name: str
    description: str
    handler: Callable[..., Any]


def _client() -> httpx.Client:
    return httpx.Client(timeout=30.0)


def _ingest_files(paths: List[str], embeddings: bool = True, replace: bool = True) -> List[dict]:
    """Read files and POST to /ingestion/documents.

    Returns a list of {document_id, task_id, status} dicts.
    """
    results: List[dict] = []
    url = f"{API_V1}/ingestion/documents"
    with _client() as client:
        for p in paths:
            path = Path(p)
            if not path.exists() or not path.is_file():
                results.append({"path": str(path), "error": "not_found"})
                continue
            content = path.read_text(encoding="utf-8")
            metadata = {"source": "mcp", "path": str(path)}
            payload = {
                "document_id": str(path),
                "content": content,
                "metadata": metadata,
                # embeddings/replace handled inside service via defaults; kept informational here
            }
            r = client.post(url, json=payload)
            try:
                r.raise_for_status()
                results.append(r.json())
            except httpx.HTTPStatusError:
                results.append({"path": str(path), "status": r.status_code, "body": r.text})
    return results


def _search(query: str, limit: int = 10, search_type: str = "vector") -> dict:
    url = f"{API_V1}/search/query?stream=false"
    payload = {"query": query, "search_type": search_type, "limit": limit}
    with _client() as client:
        r = client.post(url, json=payload)
        r.raise_for_status()
        return r.json()


def _query_answer(text: str, k: int = 5, include_graph: bool = False) -> dict:
    url = f"{API_V1}/query/ask"
    payload = {"text": text, "k": k, "include_graph": include_graph}
    with _client() as client:
        r = client.post(url, json=payload)
        r.raise_for_status()
        return r.json()


def make_tools() -> List[McpTool]:
    return [
        McpTool(
            name="ingest_files",
            description="Ingest local files into Synapse",
            handler=_ingest_files,
        ),
        McpTool(
            name="search",
            description="Search for relevant chunks (vector or keyword)",
            handler=_search,
        ),
        McpTool(
            name="query_answer",
            description="Ask a question and get a synthesized answer",
            handler=_query_answer,
        ),
    ]


def serve(host: str = "127.0.0.1", port: int = 8765) -> None:
    """Start an MCP server if the dependency is available.

    Note: This is a long-lived process. Designed for real environments; tests
    should import and use `make_tools` instead of invoking `serve`.
    """
    try:
        # Deferred imports to avoid hard dependency
        from mcp.server import Server
        from mcp.types import Tool
    except Exception:  # pragma: no cover - optional dependency
        raise RuntimeError(
            "mcp package is not installed. Install 'mcp' to run the MCP server."
        )

    tools = make_tools()
    server = Server("synapse-mcp")

    # Register tools
    for t in tools:
        server.add_tool(
            Tool(
                name=t.name,
                description=t.description,
                inputSchema={
                    "type": "object",
                    "properties": {
                        # Keep schemas simple; clients can discover via help
                    },
                },
            ),
            t.handler,
        )

    # Run TCP server (alternatives: stdio or WebSocket)
    server.run_tcp(host=host, port=port)
