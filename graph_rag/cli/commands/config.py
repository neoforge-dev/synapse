import json
from pathlib import Path

import typer
from rich.console import Console
from rich.prompt import Confirm, Prompt

from graph_rag.config import Settings

app = typer.Typer(help="Configuration utilities")
console = Console()


@app.command()
def show(as_json: bool = typer.Option(False, "--json", help="Emit JSON")) -> None:
    """Show effective settings (after env resolution)."""
    s = Settings()
    data = s.model_dump(exclude={"memgraph_password"})
    if as_json:
        typer.echo(json.dumps(data, ensure_ascii=False, indent=2))
    else:
        for k, v in data.items():
            typer.echo(f"{k}={v}")


@app.command()
def init(
    path: Path | None = typer.Option(None, "--path", help="Path to write configuration files"),
    force: bool = typer.Option(False, "--force", help="Overwrite if exists"),
    interactive: bool = typer.Option(True, "--interactive/--no-interactive", help="Interactive configuration wizard"),
    setup_type: str = typer.Option("development", "--type", help="Setup type: development, production, mcp-only, vector-only"),
) -> None:
    """Initialize Synapse GraphRAG configuration with interactive setup wizard."""

    console.print("[bold blue]🚀 Synapse GraphRAG Configuration Setup[/bold blue]\n")

    # Determine base path
    base_path = path or Path(".")
    base_path.mkdir(exist_ok=True)

    env_file = base_path / ".env"

    # Check for existing files
    if env_file.exists() and not force:
        console.print(f"[yellow]Configuration file already exists: {env_file}[/yellow]")
        if not Confirm.ask("Overwrite existing configuration?"):
            console.print("[red]Setup cancelled[/red]")
            raise typer.Exit(1)
        force = True

    config = {}

    if interactive:
        console.print("[bold]Setup Configuration[/bold]\n")

        # Quick setup choice
        if Confirm.ask("Use Vector-Only Mode? (No Docker/Memgraph required)", default=False):
            setup_type = "vector-only"
            console.print("[green]✅ Vector-only mode selected - no graph database required![/green]\n")

        # API Configuration
        console.print("[bold cyan]API Server Configuration[/bold cyan]")
        config["SYNAPSE_API_HOST"] = Prompt.ask("API Host", default="0.0.0.0")
        config["SYNAPSE_API_PORT"] = Prompt.ask("API Port", default="8000")
        config["SYNAPSE_API_LOG_LEVEL"] = Prompt.ask(
            "Log Level",
            choices=["DEBUG", "INFO", "WARNING", "ERROR"],
            default="INFO"
        )

        # Graph/Memgraph Configuration (skip if vector-only)
        if setup_type != "vector-only":
            console.print("\n[bold cyan]Memgraph Database Configuration[/bold cyan]")
            config["SYNAPSE_MEMGRAPH_HOST"] = Prompt.ask("Memgraph Host", default="127.0.0.1")
            config["SYNAPSE_MEMGRAPH_PORT"] = Prompt.ask("Memgraph Port", default="7687")
            config["SYNAPSE_MEMGRAPH_USE_SSL"] = "true" if Confirm.ask("Use SSL for Memgraph?", default=False) else "false"

            if Confirm.ask("Configure Memgraph authentication?", default=False):
                config["SYNAPSE_MEMGRAPH_USERNAME"] = Prompt.ask("Username")
                config["SYNAPSE_MEMGRAPH_PASSWORD"] = Prompt.ask("Password", password=True)
        else:
            config["SYNAPSE_DISABLE_GRAPH"] = "true"

        # Vector Store Configuration
        console.print("\n[bold cyan]Vector Store Configuration[/bold cyan]")
        vector_store_type = Prompt.ask(
            "Vector Store Type",
            choices=["faiss", "simple"],
            default="faiss"
        )
        config["SYNAPSE_VECTOR_STORE_TYPE"] = vector_store_type

        if vector_store_type == "faiss":
            config["SYNAPSE_VECTOR_STORE_PATH"] = Prompt.ask(
                "FAISS Store Path",
                default="~/.synapse/faiss_store"
            )

        # Embedding Configuration
        console.print("\n[bold cyan]Embedding Configuration[/bold cyan]")
        embedding_provider = Prompt.ask(
            "Embedding Provider",
            choices=["sentence-transformers", "openai", "mock"],
            default="sentence-transformers"
        )
        config["SYNAPSE_EMBEDDING_PROVIDER"] = embedding_provider

        if embedding_provider == "sentence-transformers":
            model = Prompt.ask(
                "Embedding Model",
                default="all-MiniLM-L6-v2",
                show_default=True
            )
            config["SYNAPSE_VECTOR_STORE_EMBEDDING_MODEL"] = model
        elif embedding_provider == "openai":
            config["OPENAI_API_KEY"] = Prompt.ask("OpenAI API Key", password=True)

        # MCP Configuration
        if setup_type in ["development", "mcp-only"] or Confirm.ask("\nConfigure MCP server?", default=True):
            console.print("\n[bold cyan]MCP Server Configuration[/bold cyan]")
            config["SYNAPSE_MCP_HOST"] = Prompt.ask("MCP Host", default="127.0.0.1")
            config["SYNAPSE_MCP_PORT"] = Prompt.ask("MCP Port", default="8765")
            config["SYNAPSE_API_BASE_URL"] = f"http://{config.get('SYNAPSE_API_HOST', '0.0.0.0')}:{config.get('SYNAPSE_API_PORT', '8000')}"

    else:
        # Non-interactive defaults based on setup type
        if setup_type == "production":
            config.update({
                "SYNAPSE_API_HOST": "0.0.0.0",
                "SYNAPSE_API_PORT": "8000",
                "SYNAPSE_API_LOG_LEVEL": "INFO",
                "SYNAPSE_API_LOG_JSON": "true",
                "SYNAPSE_ENABLE_METRICS": "true",
                "SYNAPSE_MEMGRAPH_HOST": "memgraph",
                "SYNAPSE_MEMGRAPH_PORT": "7687",
                "SYNAPSE_MEMGRAPH_USE_SSL": "true",
                "SYNAPSE_VECTOR_STORE_TYPE": "faiss",
                "SYNAPSE_VECTOR_STORE_PATH": "/data/faiss_store",
                "SYNAPSE_EMBEDDING_PROVIDER": "sentence-transformers",
                "SYNAPSE_VECTOR_STORE_EMBEDDING_MODEL": "all-MiniLM-L6-v2",
            })
        elif setup_type == "mcp-only":
            config.update({
                "SYNAPSE_API_BASE_URL": "http://localhost:8000",
                "SYNAPSE_MCP_HOST": "127.0.0.1",
                "SYNAPSE_MCP_PORT": "8765",
            })
        elif setup_type == "vector-only":
            config.update({
                "SYNAPSE_API_HOST": "0.0.0.0",
                "SYNAPSE_API_PORT": "8000",
                "SYNAPSE_API_LOG_LEVEL": "INFO",
                "SYNAPSE_DISABLE_GRAPH": "true",
                "SYNAPSE_VECTOR_STORE_TYPE": "simple",
                "SYNAPSE_EMBEDDING_PROVIDER": "sentence-transformers",
                "SYNAPSE_VECTOR_STORE_EMBEDDING_MODEL": "all-MiniLM-L6-v2",
            })
        else:  # development
            config.update({
                "SYNAPSE_API_HOST": "0.0.0.0",
                "SYNAPSE_API_PORT": "8000",
                "SYNAPSE_API_LOG_LEVEL": "DEBUG",
                "SYNAPSE_API_LOG_JSON": "false",
                "SYNAPSE_ENABLE_METRICS": "true",
                "SYNAPSE_MEMGRAPH_HOST": "127.0.0.1",
                "SYNAPSE_MEMGRAPH_PORT": "7687",
                "SYNAPSE_MEMGRAPH_USE_SSL": "false",
                "SYNAPSE_VECTOR_STORE_TYPE": "faiss",
                "SYNAPSE_VECTOR_STORE_PATH": "~/.synapse/faiss_store",
                "SYNAPSE_EMBEDDING_PROVIDER": "sentence-transformers",
                "SYNAPSE_VECTOR_STORE_EMBEDDING_MODEL": "all-MiniLM-L6-v2",
                "SYNAPSE_API_BASE_URL": "http://localhost:8000",
                "SYNAPSE_MCP_HOST": "127.0.0.1",
                "SYNAPSE_MCP_PORT": "8765",
            })

    # Generate .env file
    env_content = "# Synapse GraphRAG Configuration\n"
    env_content += f"# Generated with setup type: {setup_type}\n\n"

    for key, value in config.items():
        env_content += f"{key}={value}\n"

    env_file.write_text(env_content)
    console.print(f"\n[green]✅ Configuration written to {env_file}[/green]")

    # Create MCP configuration examples if requested
    if setup_type in ["development", "mcp-only"] or config.get("SYNAPSE_MCP_HOST"):
        _create_mcp_configs(base_path, config)

    # Create directories
    _create_directories(config)

    # Show next steps
    _show_next_steps(setup_type, config)


@app.command()
def mcp_examples(
    output_dir: Path | None = typer.Option(None, "--output", help="Output directory for examples"),
    api_url: str = typer.Option("http://localhost:8000", "--api-url", help="API base URL"),
) -> None:
    """Generate MCP configuration examples for VS Code and Claude Desktop."""

    output_path = output_dir or Path("mcp-config")
    output_path.mkdir(exist_ok=True)

    config = {"SYNAPSE_API_BASE_URL": api_url}
    _create_mcp_configs(output_path, config)

    console.print(f"[green]✅ MCP configuration examples created in {output_path}[/green]")

    # Show usage instructions
    console.print("\n[bold]Usage Instructions:[/bold]")
    console.print("• VS Code: Copy vscode-settings.json content to your VS Code settings")
    console.print("• Claude Desktop: Copy claude-desktop-config.json to Claude's config directory")


def _create_mcp_configs(base_path: Path, config: dict) -> None:
    """Create MCP configuration examples."""
    api_url = config.get("SYNAPSE_API_BASE_URL", "http://localhost:8000")

    # VS Code configuration
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

    (base_path / "vscode-settings.json").write_text(
        json.dumps(vscode_config, indent=2)
    )

    # Claude Desktop configuration
    claude_config = {
        "mcpServers": {
            "synapse-graph-rag": {
                "command": "synapse",
                "args": ["mcp", "start", "--transport", "stdio"],
                "env": {
                    "SYNAPSE_API_BASE_URL": api_url
                }
            }
        }
    }

    (base_path / "claude-desktop-config.json").write_text(
        json.dumps(claude_config, indent=2)
    )

    # Create setup instructions
    instructions = f"""# MCP Configuration Instructions

## VS Code Setup

1. Open VS Code settings (Cmd/Ctrl + ,)
2. Click "Open Settings (JSON)" icon
3. Add the content from `vscode-settings.json` to your settings

## Claude Desktop Setup

1. Locate Claude Desktop config file:
   - macOS: ~/Library/Application Support/Claude/claude_desktop_config.json
   - Windows: %APPDATA%\\Claude\\claude_desktop_config.json
   - Linux: ~/.config/claude/claude_desktop_config.json

2. Replace or merge the content from `claude-desktop-config.json`
3. Restart Claude Desktop

## Testing

1. Ensure Synapse API is running:
   ```bash
   synapse up
   ```

2. Test MCP server:
   ```bash
   synapse mcp health
   ```

3. Start using the tools in your IDE!

## API Configuration

Current API URL: {api_url}

If your API is running on a different URL, update the SYNAPSE_API_BASE_URL in the configuration files.
"""

    (base_path / "README.md").write_text(instructions)

    console.print(f"[green]✅ MCP configuration examples created in {base_path}[/green]")


def _create_directories(config: dict) -> None:
    """Create necessary directories."""
    dirs_to_create = []

    # Vector store directory
    if config.get("SYNAPSE_VECTOR_STORE_PATH"):
        path = Path(config["SYNAPSE_VECTOR_STORE_PATH"]).expanduser()
        dirs_to_create.append(path)

    # Default data directory
    synapse_dir = Path.home() / ".synapse"
    dirs_to_create.extend([
        synapse_dir,
        synapse_dir / "data",
        synapse_dir / "logs",
        synapse_dir / "cache",
    ])

    for dir_path in dirs_to_create:
        dir_path.mkdir(parents=True, exist_ok=True)

    console.print(f"[green]✅ Created directories: {len(dirs_to_create)} directories[/green]")


def _show_next_steps(setup_type: str, config: dict) -> None:
    """Show next steps after configuration."""
    console.print("\n[bold green]🎉 Setup Complete![/bold green]\n")

    console.print("[bold]Next Steps:[/bold]")

    if setup_type != "mcp-only":
        console.print("1. Start the services:")
        console.print("   [cyan]synapse up[/cyan]\n")

    if config.get("SYNAPSE_MCP_HOST"):
        console.print("2. Test MCP server:")
        console.print("   [cyan]synapse mcp health[/cyan]")
        console.print("   [cyan]synapse mcp start[/cyan]\n")

        console.print("3. Configure your IDE:")
        console.print("   • VS Code: Copy [cyan]mcp-config/vscode-settings.json[/cyan] to your settings")
        console.print("   • Claude Desktop: Copy [cyan]mcp-config/claude-desktop-config.json[/cyan] to Claude config\n")

    console.print("4. Ingest some documents:")
    console.print("   [cyan]synapse ingest /path/to/documents[/cyan]\n")

    console.print("5. Test search and queries:")
    console.print("   [cyan]synapse search 'your query'[/cyan]")
    console.print("   [cyan]synapse query ask 'your question'[/cyan]\n")

    console.print("[dim]For more help, run: [cyan]synapse --help[/cyan][/dim]")
