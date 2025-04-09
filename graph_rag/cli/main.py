import typer
import logging
from typing import Optional

# Import command modules
from graph_rag.cli.commands import ingest, query # Add other command groups later
from graph_rag import __version__ # Assume version is defined in __init__.py
from graph_rag.config import settings # Use settings for logging config

# Configure root logger for CLI based on settings
logging.basicConfig(level=settings.api_log_level.upper(), format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("synapse.cli")

# Main Typer application
app = typer.Typer(
    name="synapse",
    help="CLI for interacting with the Synapse Graph-Enhanced RAG system (API).",
    add_completion=False, # Disable shell completion for simplicity
    no_args_is_help=True
)

# Add command groups (sub-applications)
app.add_typer(ingest.app, name="ingest", help="Commands for ingesting data via the API.")
app.add_typer(query.app, name="query", help="Commands for querying the GraphRAG system via the API.")

# Version callback
def version_callback(value: bool):
    if value:
        print(f"Synapse CLI Version: {__version__}")
        raise typer.Exit()

@app.callback()
def main_callback(
    ctx: typer.Context,
    version: Optional[bool] = typer.Option(
        None, "--version", "-V", callback=version_callback, is_eager=True,
        help="Show the application's version and exit."
    )
):
    """
    Synapse Command Line Interface.
    
    Use 'ingest' or 'query' commands.
    """
    # Can add global options or context setup here if needed
    # logger.debug(f"CLI Context: {ctx.invoked_subcommand}")
    pass

# Entry point
def main_callback(ctx: typer.Context):
    """GraphRAG MCP Command Line Interface"""
    # You can add global options or context setup here if needed
    logger.debug(f"Invoking command: {ctx.invoked_subcommand}")


if __name__ == "__main__":
    app() 