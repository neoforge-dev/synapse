"""Initialize Synapse GraphRAG with interactive setup wizard."""

import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.prompt import Confirm, Prompt
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.panel import Panel
from rich.table import Table

console = Console()
app = typer.Typer(help="Interactive setup wizard for Synapse GraphRAG")


@app.command("wizard")
def setup_wizard(
    quick: bool = typer.Option(False, "--quick", help="Skip interactive prompts and use defaults"),
    vector_only: bool = typer.Option(False, "--vector-only", help="Set up in vector-only mode (no Docker/Memgraph)"),
):
    """Interactive setup wizard for first-time users."""
    
    console.print(Panel.fit("🧠 Welcome to Synapse GraphRAG Setup!", style="bold blue"))
    console.print()
    
    if not quick:
        console.print("This wizard will help you set up Synapse for your knowledge base.")
        console.print("You can always reconfigure later using environment variables or config files.")
        console.print()
    
    # Step 1: Check system requirements
    console.print("[bold]Step 1: Checking system requirements...[/bold]")
    
    requirements = _check_system_requirements()
    _display_requirements_table(requirements)
    
    # Determine setup mode
    if vector_only:
        setup_mode = "vector_only"
        console.print("[yellow]📝 Vector-only mode selected - graph features will be limited[/yellow]")
    elif not requirements["docker"]["available"] and not quick:
        if Confirm.ask("Docker is not available. Would you like to continue in vector-only mode?"):
            setup_mode = "vector_only"
        else:
            console.print("[red]Docker is required for full graph features. Please install Docker and re-run setup.[/red]")
            raise typer.Exit(1)
    else:
        setup_mode = "full"
    
    # Step 2: Configure LLM provider
    console.print("\n[bold]Step 2: Configure LLM provider...[/bold]")
    
    if not quick:
        console.print("Synapse can use different LLM providers for answer generation:")
        console.print("• OpenAI (GPT models) - requires API key")
        console.print("• Anthropic (Claude) - requires API key") 
        console.print("• Ollama (local models) - free, requires Ollama installation")
        console.print("• Mock (for testing) - no real answers")
        console.print()
    
    llm_config = _configure_llm_provider(quick)
    
    # Step 3: Set up directories and config
    console.print("\n[bold]Step 3: Setting up configuration...[/bold]")
    config_path = _setup_configuration(setup_mode, llm_config, quick)
    
    # Step 4: Start services if needed
    if setup_mode == "full":
        console.print("\n[bold]Step 4: Starting services...[/bold]")
        _start_services(quick)
    
    # Step 5: Verify setup
    console.print("\n[bold]Step 5: Verifying setup...[/bold]")
    success = _verify_setup(setup_mode)
    
    if success:
        _show_success_message(setup_mode, config_path)
    else:
        _show_troubleshooting_help(setup_mode)


@app.command("check")
def check_setup():
    """Check current Synapse setup and configuration."""
    
    console.print("[bold]Synapse GraphRAG Setup Check[/bold]\n")
    
    # Check requirements
    requirements = _check_system_requirements()
    _display_requirements_table(requirements)
    
    # Check configuration
    console.print("\n[bold]Configuration:[/bold]")
    config_table = Table()
    config_table.add_column("Setting")
    config_table.add_column("Value")
    config_table.add_column("Status")
    
    from graph_rag.config import get_settings
    settings = get_settings()
    
    # LLM configuration
    llm_status = "✅ Configured" if settings.llm_type != "mock" else "⚠️ Mock only"
    config_table.add_row("LLM Provider", settings.llm_type, llm_status)
    
    # Vector store
    vector_status = "✅ Available"
    config_table.add_row("Vector Store", settings.vector_store_type, vector_status)
    
    # Graph store
    if getattr(settings, 'vector_only_mode', False):
        graph_status = "➖ Disabled (vector-only mode)"
    elif requirements["docker"]["available"]:
        graph_status = "✅ Available (Docker ready)"
    else:
        graph_status = "❌ Docker not available"
    config_table.add_row("Graph Store", "Memgraph" if not getattr(settings, 'vector_only_mode', False) else "Disabled", graph_status)
    
    console.print(config_table)
    
    # Check running services
    console.print("\n[bold]Services:[/bold]")
    _check_services_status()


def _check_system_requirements() -> dict:
    """Check system requirements and return status."""
    requirements = {
        "python": {"available": False, "version": None, "min_version": "3.10"},
        "docker": {"available": False, "version": None, "running": False},
        "uv": {"available": False, "version": None},
    }
    
    # Check Python
    try:
        result = subprocess.run([sys.executable, "--version"], capture_output=True, text=True)
        if result.returncode == 0:
            version = result.stdout.strip().split()[1]
            requirements["python"]["available"] = True
            requirements["python"]["version"] = version
    except Exception:
        pass
    
    # Check Docker
    try:
        result = subprocess.run(["docker", "--version"], capture_output=True, text=True)
        if result.returncode == 0:
            version = result.stdout.strip().split()[2].rstrip(',')
            requirements["docker"]["available"] = True
            requirements["docker"]["version"] = version
            
            # Check if Docker is running
            result = subprocess.run(["docker", "info"], capture_output=True, text=True)
            requirements["docker"]["running"] = result.returncode == 0
    except Exception:
        pass
    
    # Check uv
    try:
        result = subprocess.run(["uv", "--version"], capture_output=True, text=True)
        if result.returncode == 0:
            version = result.stdout.strip().split()[1]
            requirements["uv"]["available"] = True
            requirements["uv"]["version"] = version
    except Exception:
        pass
    
    return requirements


def _display_requirements_table(requirements: dict):
    """Display system requirements in a table."""
    table = Table()
    table.add_column("Requirement")
    table.add_column("Status")
    table.add_column("Version")
    table.add_column("Notes")
    
    # Python
    python_req = requirements["python"]
    if python_req["available"]:
        status = "✅ Available"
        notes = "Good to go!"
    else:
        status = "❌ Missing"
        notes = f"Install Python {python_req['min_version']}+"
    table.add_row("Python", status, python_req.get("version", "N/A"), notes)
    
    # Docker
    docker_req = requirements["docker"]
    if docker_req["available"]:
        if docker_req["running"]:
            status = "✅ Available & Running"
            notes = "Ready for full graph features"
        else:
            status = "⚠️ Available but not running"
            notes = "Start Docker for graph features"
    else:
        status = "❌ Missing"
        notes = "Install for graph features (optional)"
    table.add_row("Docker", status, docker_req.get("version", "N/A"), notes)
    
    # uv
    uv_req = requirements["uv"]
    if uv_req["available"]:
        status = "✅ Available"
        notes = "Package manager ready"
    else:
        status = "❌ Missing"
        notes = "pip install uv"
    table.add_row("uv", status, uv_req.get("version", "N/A"), notes)
    
    console.print(table)


def _configure_llm_provider(quick: bool) -> dict:
    """Configure LLM provider settings."""
    
    if quick:
        console.print("Using mock LLM provider for quick setup")
        return {"type": "mock"}
    
    provider_choice = Prompt.ask(
        "Choose LLM provider",
        choices=["openai", "anthropic", "ollama", "mock"],
        default="mock"
    )
    
    config = {"type": provider_choice}
    
    if provider_choice == "openai":
        api_key = Prompt.ask("Enter OpenAI API key (will be stored in environment)", password=True)
        config["api_key"] = api_key
        config["model"] = Prompt.ask("Choose model", default="gpt-4o-mini")
        
    elif provider_choice == "anthropic":
        api_key = Prompt.ask("Enter Anthropic API key (will be stored in environment)", password=True)
        config["api_key"] = api_key
        config["model"] = Prompt.ask("Choose model", default="claude-3-5-haiku-20241022")
        
    elif provider_choice == "ollama":
        config["base_url"] = Prompt.ask("Ollama server URL", default="http://localhost:11434")
        config["model"] = Prompt.ask("Model name", default="llama3.2:3b")
        console.print("[yellow]💡 Make sure Ollama is running and the model is pulled: ollama pull llama3.2:3b[/yellow]")
    
    return config


def _setup_configuration(setup_mode: str, llm_config: dict, quick: bool) -> Path:
    """Set up configuration files and environment."""
    
    # Create config directory
    config_dir = Path.home() / ".synapse"
    config_dir.mkdir(exist_ok=True)
    
    # Create environment file
    env_file = config_dir / ".env"
    
    env_vars = []
    
    # LLM configuration
    env_vars.append(f"SYNAPSE_LLM_TYPE={llm_config['type']}")
    
    if llm_config["type"] == "openai" and "api_key" in llm_config:
        env_vars.append(f"SYNAPSE_OPENAI_API_KEY={llm_config['api_key']}")
        env_vars.append(f"SYNAPSE_LLM_MODEL_NAME={llm_config.get('model', 'gpt-4o-mini')}")
        
    elif llm_config["type"] == "anthropic" and "api_key" in llm_config:
        env_vars.append(f"SYNAPSE_ANTHROPIC_API_KEY={llm_config['api_key']}")
        env_vars.append(f"SYNAPSE_LLM_MODEL_NAME={llm_config.get('model', 'claude-3-5-haiku-20241022')}")
        
    elif llm_config["type"] == "ollama":
        env_vars.append(f"SYNAPSE_OLLAMA_BASE_URL={llm_config.get('base_url', 'http://localhost:11434')}")
        env_vars.append(f"SYNAPSE_LLM_MODEL_NAME={llm_config.get('model', 'llama3.2:3b')}")
    
    # Setup mode configuration
    if setup_mode == "vector_only":
        env_vars.append("SYNAPSE_VECTOR_ONLY_MODE=true")
    
    # Write environment file
    with open(env_file, "w") as f:
        f.write("# Synapse GraphRAG Configuration\n")
        f.write("# Generated by setup wizard\n\n")
        for var in env_vars:
            f.write(f"{var}\n")
    
    console.print(f"✅ Configuration saved to {env_file}")
    console.print("[yellow]💡 You can edit this file to modify settings later[/yellow]")
    
    return env_file


def _start_services(quick: bool):
    """Start required services."""
    
    if quick or Confirm.ask("Start Memgraph and API services now?"):
        try:
            console.print("Starting services...")
            from graph_rag.cli.commands.compose import compose_up
            
            compose_up(
                compose_file=None,
                detached=True,
                dev=False,
                start_docker=True,
                wait_services=True,
                wait_timeout=60,
                pull=False,
                build=False,
            )
            console.print("✅ Services started successfully")
        except Exception as e:
            console.print(f"[red]Failed to start services: {e}[/red]")
            console.print("You can try starting manually with: synapse up")


def _verify_setup(setup_mode: str) -> bool:
    """Verify the setup is working."""
    
    success = True
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        
        # Test API
        task = progress.add_task("Testing API connection...", total=None)
        try:
            import httpx
            with httpx.Client() as client:
                response = client.get("http://localhost:8000/health", timeout=10.0)
                if response.status_code == 200:
                    progress.update(task, description="✅ API connection successful")
                else:
                    progress.update(task, description="❌ API connection failed")
                    success = False
        except Exception:
            progress.update(task, description="❌ API not accessible")
            success = False
        
        # Test basic functionality
        task2 = progress.add_task("Testing basic functionality...", total=None)
        try:
            # Simple test of the CLI
            result = subprocess.run(["synapse", "--version"], capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                progress.update(task2, description="✅ CLI working correctly")
            else:
                progress.update(task2, description="❌ CLI test failed")
                success = False
        except Exception:
            progress.update(task2, description="❌ CLI not working")
            success = False
    
    return success


def _check_services_status():
    """Check status of running services."""
    
    service_table = Table()
    service_table.add_column("Service")
    service_table.add_column("Status")
    service_table.add_column("Port")
    
    # Check API
    try:
        import httpx
        with httpx.Client() as client:
            response = client.get("http://localhost:8000/health", timeout=5.0)
            if response.status_code == 200:
                api_status = "✅ Running"
            else:
                api_status = "❌ Unhealthy"
    except Exception:
        api_status = "❌ Not running"
    
    service_table.add_row("GraphRAG API", api_status, "8000")
    
    # Check Memgraph
    try:
        import socket
        with socket.create_connection(("localhost", 7687), timeout=5.0):
            memgraph_status = "✅ Running"
    except Exception:
        memgraph_status = "❌ Not running"
    
    service_table.add_row("Memgraph", memgraph_status, "7687")
    
    console.print(service_table)


def _show_success_message(setup_mode: str, config_path: Path):
    """Show success message with next steps."""
    
    console.print(Panel.fit("🎉 Setup completed successfully!", style="bold green"))
    console.print()
    
    console.print("[bold]Next steps:[/bold]")
    console.print("1. Try ingesting your first document:")
    console.print("   [cyan]synapse ingest 'Your content here' --title 'Test Document'[/cyan]")
    console.print()
    console.print("2. Search your knowledge base:")
    console.print("   [cyan]synapse search 'your query'[/cyan]")
    console.print()
    console.print("3. Ask questions:")
    console.print("   [cyan]synapse query ask 'What is this about?'[/cyan]")
    console.print()
    
    if setup_mode == "vector_only":
        console.print("[yellow]💡 You're running in vector-only mode. To enable full graph features:[/yellow]")
        console.print("[yellow]   • Install Docker: https://docker.com[/yellow]")
        console.print("[yellow]   • Run: synapse up[/yellow]")
        console.print()
    
    console.print(f"[dim]Configuration saved to: {config_path}[/dim]")
    console.print("[dim]Use 'synapse init check' to verify your setup anytime[/dim]")


def _show_troubleshooting_help(setup_mode: str):
    """Show troubleshooting help."""
    
    console.print(Panel.fit("⚠️ Setup had some issues", style="bold yellow"))
    console.print()
    
    console.print("[bold]Troubleshooting steps:[/bold]")
    console.print("1. Check system requirements:")
    console.print("   [cyan]synapse init check[/cyan]")
    console.print()
    console.print("2. View service logs:")
    console.print("   [cyan]synapse compose logs[/cyan]")
    console.print()
    console.print("3. Restart services:")
    console.print("   [cyan]synapse up[/cyan]")
    console.print()
    console.print("4. Try vector-only mode:")
    console.print("   [cyan]synapse init wizard --vector-only[/cyan]")
    console.print()
    console.print("For more help, visit: https://docs.anthropic.com/en/docs/claude-code")