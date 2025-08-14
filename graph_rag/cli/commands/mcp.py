import json

import typer
from rich.console import Console
from rich.table import Table

from graph_rag.mcp.server import health_check, serve

app = typer.Typer(help="MCP (Model Context Protocol) server management for Synapse GraphRAG")
console = Console()


@app.command("start")
def start_server(
    host: str = typer.Option("127.0.0.1", "--host", "-h", help="Host to bind MCP server to"),
    port: int = typer.Option(8765, "--port", "-p", help="Port to bind MCP server to"),
    transport: str = typer.Option("tcp", "--transport", "-t", help="Transport type: tcp or stdio"),
    api_url: str | None = typer.Option(None, "--api-url", help="Synapse API base URL"),
    check_health: bool = typer.Option(True, "--check-health/--no-check-health", help="Check health before starting"),
):
    """Start the MCP server for Synapse GraphRAG tools.
    
    The server exposes tools for document ingestion, search, and question answering
    that can be used by MCP clients like VS Code and Claude IDE.
    """
    # Set API URL if provided
    if api_url:
        import os
        os.environ["SYNAPSE_API_BASE_URL"] = api_url

    # Health check first
    if check_health:
        console.print("[blue]Checking system health...[/blue]")
        status = health_check()

        if not status["healthy"]:
            console.print("[red]Health check failed![/red]")
            for error in status["errors"]:
                console.print(f"  ❌ {error}")

            if not status["mcp_available"]:
                console.print("\n[yellow]Install MCP support with:[/yellow]")
                console.print("  pip install 'synapse-graph-rag[mcp]'")

            if not status["api_available"]:
                console.print("\n[yellow]Start the Synapse API server first:[/yellow]")
                console.print("  synapse up")

            raise typer.Exit(1)

        console.print(f"[green]✅ Health check passed ({status['tools_count']} tools available)[/green]")

    # Start server
    console.print(f"[blue]Starting MCP server on {transport}://{host}:{port}[/blue]")

    try:
        serve(host=host, port=port, transport=transport)
    except RuntimeError as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)
    except KeyboardInterrupt:
        console.print("\n[yellow]MCP server stopped[/yellow]")


@app.command("health")
def check_health_command():
    """Check health of MCP server dependencies and connectivity."""
    status = health_check()

    # Create a table for the status
    table = Table(title="MCP Server Health Status")
    table.add_column("Component", style="bold")
    table.add_column("Status")
    table.add_column("Details")

    # MCP package
    mcp_status = "✅ Available" if status["mcp_available"] else "❌ Not installed"
    mcp_details = status.get("mcp_version", "Not installed")
    table.add_row("MCP Package", mcp_status, mcp_details)

    # API connectivity
    api_status = "✅ Connected" if status["api_available"] else "❌ Unavailable"
    api_details = status.get("api_url", "Not reachable")
    table.add_row("Synapse API", api_status, api_details)

    # Tools
    tools_status = f"✅ {status['tools_count']} available" if status["tools_count"] > 0 else "❌ None"
    tools_details = ", ".join(status.get("tools", []))
    table.add_row("MCP Tools", tools_status, tools_details)

    console.print(table)

    # Print errors if any
    if status["errors"]:
        console.print("\n[red]Issues detected:[/red]")
        for error in status["errors"]:
            console.print(f"  • {error}")

    # Overall status
    if status["healthy"]:
        console.print("\n[green]🎉 MCP server is ready to start![/green]")
    else:
        console.print("\n[red]❌ MCP server has issues that need to be resolved.[/red]")

        # Provide helpful suggestions
        if not status["mcp_available"]:
            console.print("\n[yellow]💡 Install MCP support:[/yellow]")
            console.print("  pip install 'synapse-graph-rag[mcp]'")

        if not status["api_available"]:
            console.print("\n[yellow]💡 Start the Synapse API server:[/yellow]")
            console.print("  synapse up")

    # Exit with error code if unhealthy for CI/scripts
    if not status["healthy"]:
        raise typer.Exit(1)


@app.command("info")
def info():
    """Show information about available MCP tools and their schemas."""
    try:
        from graph_rag.mcp.server import make_tools

        tools = make_tools()

        console.print("[bold]Synapse GraphRAG MCP Server[/bold]")
        console.print(f"Available tools: {len(tools)}\n")

        for tool in tools:
            console.print(f"[bold blue]{tool.name}[/bold blue]")
            console.print(f"  {tool.description}\n")

            # Show required parameters
            schema = tool.input_schema
            required = schema.get("required", [])
            properties = schema.get("properties", {})

            if required:
                console.print("  [bold]Required parameters:[/bold]")
                for param in required:
                    prop = properties.get(param, {})
                    param_type = prop.get("type", "unknown")
                    description = prop.get("description", "No description")
                    console.print(f"    • {param} ({param_type}): {description}")

            # Show optional parameters
            optional = [k for k in properties.keys() if k not in required]
            if optional:
                console.print("  [bold]Optional parameters:[/bold]")
                for param in optional:
                    prop = properties[param]
                    param_type = prop.get("type", "unknown")
                    default = prop.get("default")
                    description = prop.get("description", "No description")
                    default_str = f" (default: {default})" if default is not None else ""
                    console.print(f"    • {param} ({param_type}): {description}{default_str}")

            console.print()

    except Exception as e:
        console.print(f"[red]Error loading tools: {e}[/red]")
        raise typer.Exit(1)


@app.command("config")
def show_config(
    format: str = typer.Option("table", "--format", "-f", help="Output format: table, json, or env")
):
    """Show MCP server configuration and examples for IDE integration."""

    # Get current configuration
    import os

    from graph_rag.config import get_settings

    settings = get_settings()
    api_url = os.getenv("SYNAPSE_API_BASE_URL", "http://localhost:8000")

    config = {
        "api_url": api_url,
        "mcp_host": "127.0.0.1",
        "mcp_port": 8765,
        "transport": "tcp",
        "tools_available": 3
    }

    if format == "json":
        console.print(json.dumps(config, indent=2))
    elif format == "env":
        console.print("# Environment variables for MCP configuration")
        console.print(f"export SYNAPSE_API_BASE_URL='{api_url}'")
        console.print("export MCP_HOST='127.0.0.1'")
        console.print("export MCP_PORT='8765'")
    else:
        # Table format
        table = Table(title="MCP Server Configuration")
        table.add_column("Setting", style="bold")
        table.add_column("Value")
        table.add_column("Description")

        table.add_row("API URL", config["api_url"], "Synapse GraphRAG API endpoint")
        table.add_row("MCP Host", config["mcp_host"], "Host for MCP server")
        table.add_row("MCP Port", str(config["mcp_port"]), "Port for MCP server")
        table.add_row("Transport", config["transport"], "MCP transport protocol")
        table.add_row("Tools", str(config["tools_available"]), "Available MCP tools")

        console.print(table)

    # Show VS Code configuration example
    if format == "table":
        console.print("\n[bold]VS Code MCP Configuration Example:[/bold]")
        console.print("Add to your VS Code settings.json:")
        console.print()

        vscode_config = {
            "mcp.servers": {
                "synapse-graph-rag": {
                    "command": "synapse",
                    "args": ["mcp", "start", "--transport", "stdio"],
                    "env": {
                        "SYNAPSE_API_BASE_URL": api_url
                    }
                }
            }
        }

        console.print(json.dumps(vscode_config, indent=2))


@app.command("test")
def test_tools(
    tool: str | None = typer.Option(None, "--tool", "-t", help="Test specific tool (ingest_files, search, query_answer)"),
    api_url: str | None = typer.Option(None, "--api-url", help="Synapse API base URL"),
):
    """Test MCP tools functionality with sample data."""

    # Set API URL if provided
    if api_url:
        import os
        os.environ["SYNAPSE_API_BASE_URL"] = api_url

    try:
        from graph_rag.mcp.server import make_tools

        tools = make_tools()
        tools_dict = {t.name: t for t in tools}

        if tool and tool not in tools_dict:
            console.print(f"[red]Tool '{tool}' not found. Available: {', '.join(tools_dict.keys())}[/red]")
            raise typer.Exit(1)

        # Test search tool with a simple query
        if not tool or tool == "search":
            console.print("[blue]Testing search tool...[/blue]")
            search_tool = tools_dict["search"]

            try:
                result = search_tool.handler(query="test", limit=5)
                if result.get("success"):
                    console.print("  ✅ Search tool working")
                    data = result.get("data", {})
                    console.print(f"    Found {data.get('results_count', 0)} results")
                else:
                    console.print("  ❌ Search tool failed")
                    console.print(f"    Error: {result.get('error', {}).get('message', 'Unknown error')}")
            except Exception as e:
                console.print(f"  ❌ Search tool error: {e}")

        # Test query_answer tool
        if not tool or tool == "query_answer":
            console.print("[blue]Testing query_answer tool...[/blue]")
            qa_tool = tools_dict["query_answer"]

            try:
                result = qa_tool.handler(question="What is this system?")
                if result.get("success"):
                    console.print("  ✅ Query answer tool working")
                    data = result.get("data", {})
                    answer_length = len(data.get("answer", ""))
                    sources_count = len(data.get("sources", []))
                    console.print(f"    Generated answer ({answer_length} chars) with {sources_count} sources")
                else:
                    console.print("  ❌ Query answer tool failed")
                    console.print(f"    Error: {result.get('error', {}).get('message', 'Unknown error')}")
            except Exception as e:
                console.print(f"  ❌ Query answer tool error: {e}")

        console.print("\n[green]Tool testing complete![/green]")

    except Exception as e:
        console.print(f"[red]Error testing tools: {e}[/red]")
        raise typer.Exit(1)


# Alias for backward compatibility
@app.command("run")
def run_server(
    host: str = typer.Option("127.0.0.1", "--host"),
    port: int = typer.Option(8765, "--port"),
):
    """Start the MCP server (alias for 'start' command)."""
    start_server(host=host, port=port)
