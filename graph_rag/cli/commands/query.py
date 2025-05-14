import json
import logging
import sys
from typing import Any, Optional

import httpx
import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from graph_rag.config import get_settings

# Import settings and shared request helper
# Need to make make_api_request accessible, maybe move to a shared cli.utils?
# For now, duplicate or adjust path assuming it's moved.
# Let's assume we move make_api_request to graph_rag/cli/utils.py
# from ..utils import make_api_request

# --- Configuration ---
# Construct default API URL from settings
settings = get_settings()
DEFAULT_API_BASE_URL = f"http://{settings.api_host}:{settings.api_port}/api/v1"
DEFAULT_QUERY_URL = f"{DEFAULT_API_BASE_URL}/query/"

# Logging and Console
logging.basicConfig(
    level=logging.WARNING, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)
console = Console()


# --- Temporary make_api_request (move to utils) ---
def make_api_request(
    url: str, method: str = "POST", payload: Optional[dict[str, Any]] = None
) -> dict[str, Any]:
    """Makes a request to the specified API endpoint and handles common errors."""
    logger.info(f"Sending {method} request to {url}...")
    try:
        with httpx.Client() as client:
            if method.upper() == "POST":
                response = client.post(
                    url, json=payload, timeout=60.0
                )  # Longer timeout for query
            elif method.upper() == "GET":
                response = client.get(url, timeout=30.0)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")

            response.raise_for_status()  # Raise exception for 4xx/5xx errors

            response_data = response.json()
            logger.info(f"API Response ({response.status_code}): {response_data}")
            return response_data

    except httpx.RequestError as exc:
        error_msg = f"Error: Failed to connect to the API at {url}. Is it running? Details: {exc}"
        logger.error(error_msg)
        console.print(f"[bold red]{error_msg}[/bold red]")
        raise typer.Exit(code=1)
    except httpx.HTTPStatusError as exc:
        error_msg = f"Error: API returned status {exc.response.status_code}. Response: {exc.response.text}"
        logger.error(error_msg)
        console.print(f"[bold red]{error_msg}[/bold red]")
        raise typer.Exit(code=1)
    except json.JSONDecodeError as e:
        # Access response text carefully
        response_text = "N/A"
        if (
            "exc" in locals()
            and hasattr(exc, "response")
            and hasattr(exc.response, "text")
        ):
            response_text = exc.response.text
        error_msg = f"Error: Could not decode JSON response from API. Details: {e}. Response text: {response_text}"
        logger.error(error_msg)
        console.print(f"[bold red]{error_msg}[/bold red]")
        raise typer.Exit(code=1)
    except Exception as e:
        error_msg = f"An unexpected error occurred during API request: {e}"
        logger.error(error_msg, exc_info=True)
        console.print(f"[bold red]{error_msg}[/bold red]")
        raise typer.Exit(code=1)


# --- Typer App for Query Commands ---
app = typer.Typer(help="Commands for querying the GraphRAG system.")


@app.command("ask")
def ask_query(
    query_text: str = typer.Argument(..., help="The natural language query to ask."),
    k: Optional[int] = typer.Option(
        None, "--k", help="Number of relevant chunks to retrieve (vector search)."
    ),
    show_chunks: bool = typer.Option(
        False, "--show-chunks", "-c", help="Display the text of relevant chunks."
    ),
    show_graph: bool = typer.Option(
        False,
        "--show-graph",
        "-g",
        help="Display the graph context (entities/relationships).",
    ),
    raw: bool = typer.Option(
        False, "--raw", help="Output the raw JSON response from the API."
    ),
    api_url: str = typer.Option(
        DEFAULT_QUERY_URL, "--url", help="URL of the query API endpoint."
    ),
):
    """Submits a query to the GraphRAG API and displays the results."""

    console.print(f"[bold blue]Querying API at {api_url}...[/bold blue]")

    # --- Prepare API Payload ---
    config = {}
    if k is not None:
        config["k"] = k

    payload = {"query_text": query_text, "config": config}

    # --- Call API ---
    try:
        with console.status("[bold green]Processing query...[/bold green]"):
            response_data = make_api_request(api_url, method="POST", payload=payload)
    except typer.Exit:
        # Error already printed by make_api_request
        sys.exit(1)  # Ensure exit

    # --- Output Result ---
    if raw:
        console.print(json.dumps(response_data, indent=2))
        raise typer.Exit()

    # Display formatted output
    console.print(
        Panel(
            response_data.get("answer", "No answer received."),
            title="[bold green]Answer[/bold green]",
        )
    )

    if show_chunks and response_data.get("relevant_chunks"):
        console.print("\n[bold yellow]Relevant Chunks:[/bold yellow]")
        chunks_table = Table(show_header=True, header_style="bold magenta")
        chunks_table.add_column("ID", style="dim", width=15)
        chunks_table.add_column("Document ID", width=15)
        chunks_table.add_column("Text Snippet")
        # chunks_table.add_column("Score", width=8)

        for chunk in response_data["relevant_chunks"]:
            snippet = chunk.get("text", "")[:150] + (
                "..." if len(chunk.get("text", "")) > 150 else ""
            )
            # score_str = f"{chunk.get('score'):.3f}" if chunk.get('score') is not None else "N/A"
            chunks_table.add_row(
                chunk.get("id", "N/A"),
                chunk.get("document_id", "N/A"),
                snippet,
                # score_str
            )
        console.print(chunks_table)

    if show_graph and response_data.get("graph_context"):
        console.print("\n[bold cyan]Graph Context:[/bold cyan]")
        graph_context = response_data["graph_context"]

        if graph_context.get("entities"):
            console.print("  [bold]Entities:[/bold]")
            entities_table = Table(show_header=True, header_style="bold blue")
            entities_table.add_column("ID", style="dim")
            entities_table.add_column("Name")
            entities_table.add_column("Type")
            entities_table.add_column("Metadata")
            for entity in graph_context["entities"]:
                entities_table.add_row(
                    entity.get("id", "N/A"),
                    entity.get("name", "N/A"),
                    entity.get("type", "N/A"),
                    json.dumps(entity.get("metadata", {})),
                )
            console.print(entities_table)

        if graph_context.get("relationships"):
            console.print("\n  [bold]Relationships:[/bold]")
            rels_table = Table(show_header=True, header_style="bold blue")
            rels_table.add_column("Source ID", style="dim")
            rels_table.add_column("Type")
            rels_table.add_column("Target ID", style="dim")
            rels_table.add_column("Metadata")
            for rel in graph_context["relationships"]:
                # Access nested source/target dictionaries if the API model returns them that way
                source_id = (
                    rel.get("source", {}).get("id", "N/A")
                    if isinstance(rel.get("source"), dict)
                    else rel.get("source_id", "N/A")
                )
                target_id = (
                    rel.get("target", {}).get("id", "N/A")
                    if isinstance(rel.get("target"), dict)
                    else rel.get("target_id", "N/A")
                )
                rels_table.add_row(
                    source_id,
                    rel.get("type", "N/A"),
                    target_id,
                    json.dumps(rel.get("metadata", {})),
                )
            console.print(rels_table)


# Entry point for this specific command group (optional)
if __name__ == "__main__":
    app()
