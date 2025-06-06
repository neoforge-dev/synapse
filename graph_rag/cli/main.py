import typer
import logging
from typing import Optional
from rich.logging import RichHandler
from graph_rag.cli.commands import admin, ingest, search, query # Assuming these are submodules/files
from graph_rag.config import get_settings # Import factory

# Import command functions directly
from graph_rag.cli.commands.ingest import ingest_command
from graph_rag.cli.commands.search import search_query
from graph_rag.cli.commands.admin import check_health # Import admin command

from graph_rag import __version__ # Assume version is defined in __init__.py

settings = get_settings() # Get settings instance

# Configure root logger for CLI based on settings
logging.basicConfig(
    level=settings.api_log_level.upper(),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[RichHandler(rich_tracebacks=True)]
)
logger = logging.getLogger("synapse.cli")

# Main Typer application
app = typer.Typer(
    name="synapse",
    help="CLI for interacting with the Synapse Graph-Enhanced RAG system.",
    add_completion=False, # Disable shell completion for simplicity
    no_args_is_help=True
)

# Register commands directly
app.command("ingest")(ingest_command)
app.command("search")(search_query)
app.command("admin-health")(check_health) # Renamed for clarity

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
    
    Use 'ingest', 'search', or 'admin-health' commands.
    """
    try:
        logger.debug(f"Invoking command: {ctx.invoked_subcommand}")
    except Exception as e:
        logger.error(f"Error in CLI: {str(e)}", exc_info=True)
        raise typer.Exit(code=1)

def main():
    """Main entry point for the CLI."""
    try:
        app()
    except Exception as e:
        logger.error(f"Fatal error in CLI: {str(e)}", exc_info=True)
        raise typer.Exit(code=1)

if __name__ == "__main__":
    main() 