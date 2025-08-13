import typer

from graph_rag.mcp.server import serve

app = typer.Typer(help="Run MCP server for Synapse tools")


@app.command()
def run(host: str = typer.Option("127.0.0.1", "--host"), port: int = typer.Option(8765, "--port")):
    """Start the MCP server (requires 'mcp' package)."""
    try:
        serve(host=host, port=port)
    except RuntimeError as e:
        typer.echo(str(e))
        raise typer.Exit(1)
