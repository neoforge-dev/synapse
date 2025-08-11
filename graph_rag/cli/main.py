import logging
from typing import Optional

import typer

from graph_rag import __version__  # Assume version is defined in __init__.py
from graph_rag.cli.commands.admin import check_health  # Import admin command

# Import command functions directly
from graph_rag.cli.commands.ingest import ingest_command
from graph_rag.cli.commands.discover import discover_command
from graph_rag.cli.commands.parse import parse_command
from graph_rag.cli.commands.store import store_command
from graph_rag.cli.commands.search import search_query
from graph_rag.cli.commands.suggest import run_suggest as suggest_command
from graph_rag.cli.commands.query import app as query_app
from graph_rag.cli.commands.config import app as config_app
from graph_rag.config import get_settings  # Import factory

settings = get_settings()  # Get settings instance

# Configure root logger for CLI based on settings
logging.basicConfig(
    level=settings.api_log_level.upper(),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("synapse.cli")

# Main Typer application
app = typer.Typer(
    name="synapse",
    help="CLI for interacting with the Synapse Graph-Enhanced RAG system.",
    add_completion=False,  # Disable shell completion for simplicity
    no_args_is_help=True,
)

# Register commands directly
app.command("ingest")(ingest_command)
app.command("discover")(discover_command)
app.command("parse")(parse_command)
app.command("store")(store_command)
app.command("search")(search_query)
app.add_typer(query_app, name="query")
app.command("suggest")(suggest_command)
app.add_typer(config_app, name="config")
app.command("admin-health")(check_health)  # Renamed for clarity


# Version callback
def version_callback(value: bool):
    if value:
        print(f"Synapse CLI Version: {__version__}")
        raise typer.Exit()


@app.callback()
def main_callback(
    ctx: typer.Context,
    version: Optional[bool] = typer.Option(
        None,
        "--version",
        "-V",
        callback=version_callback,
        is_eager=True,
        help="Show the application's version and exit.",
    ),
    quiet: bool = typer.Option(
        False,
        "--quiet",
        help="Reduce logging verbosity to warnings only.",
    ),
    verbose: bool = typer.Option(
        False,
        "--verbose",
        "--debug",
        help="Increase logging verbosity (debug level).",
    ),
):
    """
    Synapse Command Line Interface.

    Use 'ingest', 'search', or 'admin-health' commands.
    """
    try:
        # Adjust logging level based on flags (quiet < default < verbose)
        if quiet:
            logging.getLogger().setLevel(logging.WARNING)
        elif verbose:
            logging.getLogger().setLevel(logging.DEBUG)
        logger.debug(f"Invoking command: {ctx.invoked_subcommand}")
    except Exception as e:
        logger.error(f"Error in CLI: {e!s}", exc_info=True)
        raise typer.Exit(code=1)


def main():
    """Main entry point for the CLI."""
    try:
        app()
    except Exception as e:
        logger.error(f"Fatal error in CLI: {e!s}", exc_info=True)
        raise typer.Exit(code=1)


if __name__ == "__main__":
    main()
