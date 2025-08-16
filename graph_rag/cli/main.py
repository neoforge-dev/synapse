import logging

import typer

from graph_rag import __version__  # Assume version is defined in __init__.py
from graph_rag.cli.commands.admin import app as admin_app
from graph_rag.cli.commands.analytics import app as analytics_app
from graph_rag.cli.commands.compose import app as compose_app
from graph_rag.cli.commands.config import app as config_app
from graph_rag.cli.commands.discover import discover_command
from graph_rag.cli.commands.enhanced_search import app as enhanced_search_app
from graph_rag.cli.commands.graph import app as graph_app
from graph_rag.cli.commands.insights import app as insights_app

# Import command functions directly
from graph_rag.cli.commands.ingest import ingest_command
from graph_rag.cli.commands.init import app as init_app
from graph_rag.cli.commands.mcp import app as mcp_app
from graph_rag.cli.commands.notion import app as notion_app
from graph_rag.cli.commands.parse import parse_command
from graph_rag.cli.commands.query import app as query_app
from graph_rag.cli.commands.search import search_query
from graph_rag.cli.commands.store import store_command
from graph_rag.cli.commands.suggest import run_suggest as suggest_command
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
app.add_typer(enhanced_search_app, name="explain")
app.add_typer(query_app, name="query")
app.add_typer(graph_app, name="graph")
app.add_typer(insights_app, name="insights")
app.add_typer(analytics_app, name="analytics")
app.add_typer(notion_app, name="notion")
app.command("suggest")(suggest_command)
app.add_typer(config_app, name="config")
app.add_typer(admin_app, name="admin")
app.add_typer(mcp_app, name="mcp")
app.add_typer(compose_app, name="compose")
app.add_typer(init_app, name="init")


# Top-level convenience: synapse up (delegates to compose up with enhanced features)
@app.command("up")
def up(
    compose: str | None = typer.Option(None, "--compose", help="Path to docker-compose.yml"),
    detached: bool = typer.Option(True, "--detached/--no-detached", help="Run docker compose up -d"),
    dev: bool = typer.Option(False, "--dev", help="Use development compose file"),
    start_docker: bool = typer.Option(True, "--start-docker/--no-start-docker", help="Auto-start Docker Desktop on macOS"),
    wait_services: bool = typer.Option(True, "--wait/--no-wait", help="Wait for services to be ready"),
    wait_timeout: int = typer.Option(60, "--timeout", help="Timeout for service readiness"),
    pull: bool = typer.Option(False, "--pull", help="Pull latest images before starting"),
    build: bool = typer.Option(False, "--build", help="Build images before starting"),
):
    """Bring up the Synapse GraphRAG stack with enhanced health checks and monitoring."""
    from graph_rag.cli.commands.compose import compose_up

    compose_up(
        compose_file=compose,
        detached=detached,
        dev=dev,
        start_docker=start_docker,
        wait_services=wait_services,
        wait_timeout=wait_timeout,
        pull=pull,
        build=build,
    )


@app.command("down")
def down(
    compose: str | None = typer.Option(None, "--compose", help="Path to docker-compose.yml"),
    dev: bool = typer.Option(False, "--dev", help="Use development compose file"),
    volumes: bool = typer.Option(False, "--volumes", "-v", help="Remove volumes"),
):
    """Stop the Synapse GraphRAG stack."""
    from graph_rag.cli.commands.compose import compose_down

    compose_down(
        compose_file=compose,
        dev=dev,
        volumes=volumes,
    )


# Version callback
def version_callback(value: bool):
    if value:
        print(f"Synapse CLI Version: {__version__}")
        raise typer.Exit()


@app.callback()
def main_callback(
    ctx: typer.Context,
    version: bool | None = typer.Option(
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
