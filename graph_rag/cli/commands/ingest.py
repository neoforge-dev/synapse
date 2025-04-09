"""CLI command for document ingestion."""
import logging
import json
import sys
from pathlib import Path
from typing import Optional, Dict, Any
import asyncio
import httpx
import typer

from graph_rag.config import settings
from graph_rag.cli.config import cli_config

# Configure logging for CLI
logging.basicConfig(
    level=settings.api_log_level.upper(),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Create Typer app for ingest commands
app = typer.Typer(help="Commands for ingesting documents into the knowledge graph.")

async def ingest_file(file_path: Path, metadata_dict: Dict[str, Any]) -> None:
    """Async helper function to handle file ingestion."""
    async with httpx.AsyncClient() as client:
        try:
            with open(file_path, "rb") as f:
                files = {"file": (file_path.name, f, "application/octet-stream")}
                data = {"metadata": json.dumps(metadata_dict)}
                
                response = await client.post(
                    cli_config.ingestion_url,
                    files=files,
                    data=data
                )
                response.raise_for_status()
                typer.echo(f"Successfully ingested document: {response.json()}")
        except httpx.HTTPError as e:
            logger.error(f"Error ingesting document: {str(e)}")
            typer.echo(f"Error ingesting document: {str(e)}", err=True)
            if e.response is not None:
                typer.echo(f"Response: {e.response.text}", err=True)
            raise typer.Exit(1)
        except Exception as e:
            logger.error(f"Error processing file: {str(e)}")
            typer.echo(f"Error processing file: {str(e)}", err=True)
            raise typer.Exit(1)

@app.command()
def ingest(
    file_path: Path = typer.Argument(
        ...,
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
        help="Path to the document file to ingest"
    ),
    api_url: Optional[str] = typer.Option(
        None,
        "--api-url",
        help="Override the default API URL"
    ),
    metadata: Optional[str] = typer.Option(
        None,
        "--metadata",
        help="JSON string of additional metadata"
    )
) -> None:
    """Ingest a document into the knowledge graph."""
    # Override API URL if provided
    if api_url:
        cli_config.api_base_url = api_url
    
    # Parse metadata if provided
    metadata_dict: Dict[str, Any] = {}
    if metadata:
        try:
            metadata_dict = json.loads(metadata)
        except json.JSONDecodeError:
            logger.error("Invalid JSON in metadata")
            typer.echo("Error: Invalid JSON in metadata", err=True)
            raise typer.Exit(1)
    
    # Run the async ingestion
    asyncio.run(ingest_file(file_path, metadata_dict))

if __name__ == "__main__":
    app() 