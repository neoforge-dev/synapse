"""Docker Compose management commands for Synapse GraphRAG."""

import json
import os
import socket
import subprocess
import sys
import time
from pathlib import Path

import httpx
import typer
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

console = Console()
app = typer.Typer(help="Docker Compose management for Synapse GraphRAG stack")

DEFAULT_COMPOSE_FILE = "docker-compose.yml"
DEFAULT_DEV_COMPOSE_FILE = "docker-compose.dev.yml"


@app.command("up")
def compose_up(
    compose_file: str | None = typer.Option(None, "--compose", "-c", help="Path to docker-compose.yml"),
    detached: bool = typer.Option(True, "--detached/--no-detached", "-d", help="Run in detached mode"),
    dev: bool = typer.Option(False, "--dev", help="Use development compose file"),
    start_docker: bool = typer.Option(True, "--start-docker/--no-start-docker", help="Auto-start Docker Desktop on macOS"),
    wait_services: bool = typer.Option(True, "--wait/--no-wait", help="Wait for services to be ready"),
    wait_timeout: int = typer.Option(60, "--timeout", help="Timeout in seconds for service readiness"),
    pull: bool = typer.Option(False, "--pull", help="Pull latest images before starting"),
    build: bool = typer.Option(False, "--build", help="Build images before starting"),
):
    """Start the Synapse GraphRAG stack with Docker Compose.
    
    This command starts Memgraph and the GraphRAG API server, with optional
    health checks to ensure services are ready before completing.
    """
    # Determine compose file
    if compose_file:
        compose_path = Path(compose_file)
    elif dev:
        compose_path = Path(DEFAULT_DEV_COMPOSE_FILE)
    else:
        compose_path = Path(DEFAULT_COMPOSE_FILE)

    if not compose_path.exists():
        console.print(f"[red]Compose file not found: {compose_path}[/red]")
        raise typer.Exit(1)

    console.print(f"[blue]Using compose file: {compose_path}[/blue]")

    # Ensure Docker is running
    try:
        _ensure_docker_running(start_docker, wait_timeout)
    except Exception as e:
        console.print(f"[red]Docker error: {e}[/red]")
        raise typer.Exit(1)

    # Build compose command
    cmd = ["docker", "compose", "-f", str(compose_path)]

    if pull:
        console.print("[blue]Pulling latest images...[/blue]")
        try:
            subprocess.run(cmd + ["pull"], check=True)
            console.print("[green]✅ Images pulled successfully[/green]")
        except subprocess.CalledProcessError as e:
            console.print(f"[yellow]Warning: Failed to pull images: {e}[/yellow]")

    # Start services
    up_cmd = cmd + ["up"]
    if detached:
        up_cmd.append("-d")
    if build:
        up_cmd.append("--build")

    console.print(f"[blue]Starting services: {' '.join(up_cmd)}[/blue]")

    try:
        result = subprocess.run(up_cmd, check=True, capture_output=True, text=True)
        console.print("[green]✅ Services started successfully[/green]")

        if result.stdout:
            console.print(result.stdout)

    except subprocess.CalledProcessError as e:
        console.print(f"[red]Failed to start services: {e}[/red]")
        if e.stderr:
            console.print(e.stderr)
        raise typer.Exit(1)

    if not wait_services:
        return

    # Wait for services to be ready
    console.print("[blue]Waiting for services to be ready...[/blue]")

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        # Wait for Memgraph
        memgraph_task = progress.add_task("Waiting for Memgraph...", total=None)
        if _wait_for_memgraph(wait_timeout):
            progress.update(memgraph_task, description="✅ Memgraph ready")
        else:
            progress.update(memgraph_task, description="❌ Memgraph timeout")
            console.print("[yellow]Warning: Memgraph may not be ready[/yellow]")

        # Wait for API
        api_task = progress.add_task("Waiting for API...", total=None)
        if _wait_for_api(wait_timeout):
            progress.update(api_task, description="✅ API ready")
        else:
            progress.update(api_task, description="❌ API timeout")
            console.print("[yellow]Warning: API may not be ready[/yellow]")

    # Show status
    status(compose_file=str(compose_path), dev=dev)


@app.command("down")
def compose_down(
    compose_file: str | None = typer.Option(None, "--compose", "-c", help="Path to docker-compose.yml"),
    dev: bool = typer.Option(False, "--dev", help="Use development compose file"),
    volumes: bool = typer.Option(False, "--volumes", "-v", help="Remove volumes"),
    remove_orphans: bool = typer.Option(True, "--remove-orphans/--keep-orphans", help="Remove orphan containers"),
):
    """Stop and remove the Synapse GraphRAG stack."""

    # Determine compose file
    if compose_file:
        compose_path = Path(compose_file)
    elif dev:
        compose_path = Path(DEFAULT_DEV_COMPOSE_FILE)
    else:
        compose_path = Path(DEFAULT_COMPOSE_FILE)

    if not compose_path.exists():
        console.print(f"[red]Compose file not found: {compose_path}[/red]")
        raise typer.Exit(1)

    # Build command
    cmd = ["docker", "compose", "-f", str(compose_path), "down"]

    if volumes:
        cmd.append("--volumes")
    if remove_orphans:
        cmd.append("--remove-orphans")

    console.print(f"[blue]Stopping services: {' '.join(cmd)}[/blue]")

    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        console.print("[green]✅ Services stopped successfully[/green]")

        if result.stdout:
            console.print(result.stdout)

    except subprocess.CalledProcessError as e:
        console.print(f"[red]Failed to stop services: {e}[/red]")
        if e.stderr:
            console.print(e.stderr)
        raise typer.Exit(1)


@app.command("status")
def status(
    compose_file: str | None = typer.Option(None, "--compose", "-c", help="Path to docker-compose.yml"),
    dev: bool = typer.Option(False, "--dev", help="Use development compose file"),
):
    """Show status of Synapse GraphRAG services."""

    # Determine compose file
    if compose_file:
        compose_path = Path(compose_file)
    elif dev:
        compose_path = Path(DEFAULT_DEV_COMPOSE_FILE)
    else:
        compose_path = Path(DEFAULT_COMPOSE_FILE)

    if not compose_path.exists():
        console.print(f"[red]Compose file not found: {compose_path}[/red]")
        return

    # Get service status
    cmd = ["docker", "compose", "-f", str(compose_path), "ps", "--format", "json"]

    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        services_data = []

        # Parse JSON output (one JSON object per line)
        for line in result.stdout.strip().split('\n'):
            if line.strip():
                try:
                    services_data.append(json.loads(line))
                except json.JSONDecodeError:
                    continue

        if not services_data:
            console.print("[yellow]No services running[/yellow]")
            return

        # Create status table
        table = Table(title="Synapse GraphRAG Services Status")
        table.add_column("Service", style="bold")
        table.add_column("Status")
        table.add_column("Health")
        table.add_column("Ports")

        for service in services_data:
            name = service.get("Name", "unknown")
            state = service.get("State", "unknown")
            health = service.get("Health", "N/A")
            ports = service.get("Publishers", [])

            # Format status with colors
            if state == "running":
                status_display = "[green]Running[/green]"
            elif state == "exited":
                status_display = "[red]Exited[/red]"
            else:
                status_display = f"[yellow]{state.title()}[/yellow]"

            # Format health
            if health == "healthy":
                health_display = "[green]✅ Healthy[/green]"
            elif health == "unhealthy":
                health_display = "[red]❌ Unhealthy[/red]"
            elif health == "starting":
                health_display = "[yellow]🔄 Starting[/yellow]"
            else:
                health_display = health

            # Format ports
            port_strings = []
            for port_info in ports:
                if isinstance(port_info, dict):
                    published = port_info.get("PublishedPort")
                    target = port_info.get("TargetPort")
                    if published and target:
                        port_strings.append(f"{published}:{target}")
            ports_display = ", ".join(port_strings) if port_strings else "N/A"

            table.add_row(name, status_display, health_display, ports_display)

        console.print(table)

        # Additional health checks
        console.print("\n[bold]Service Health Checks:[/bold]")

        # Check Memgraph
        memgraph_status = "✅ Ready" if _check_memgraph() else "❌ Not ready"
        console.print(f"Memgraph (Bolt): {memgraph_status}")

        # Check API
        api_status = "✅ Ready" if _check_api() else "❌ Not ready"
        console.print(f"GraphRAG API: {api_status}")

    except subprocess.CalledProcessError as e:
        console.print(f"[red]Failed to get service status: {e}[/red]")


@app.command("logs")
def logs(
    service: str | None = typer.Argument(None, help="Service name to show logs for"),
    compose_file: str | None = typer.Option(None, "--compose", "-c", help="Path to docker-compose.yml"),
    dev: bool = typer.Option(False, "--dev", help="Use development compose file"),
    follow: bool = typer.Option(False, "--follow", "-f", help="Follow log output"),
    tail: int | None = typer.Option(None, "--tail", help="Number of lines to show from end of logs"),
):
    """Show logs for Synapse GraphRAG services."""

    # Determine compose file
    if compose_file:
        compose_path = Path(compose_file)
    elif dev:
        compose_path = Path(DEFAULT_DEV_COMPOSE_FILE)
    else:
        compose_path = Path(DEFAULT_COMPOSE_FILE)

    if not compose_path.exists():
        console.print(f"[red]Compose file not found: {compose_path}[/red]")
        raise typer.Exit(1)

    # Build command
    cmd = ["docker", "compose", "-f", str(compose_path), "logs"]

    if follow:
        cmd.append("--follow")
    if tail:
        cmd.extend(["--tail", str(tail)])
    if service:
        cmd.append(service)

    console.print(f"[blue]Showing logs: {' '.join(cmd)}[/blue]")

    try:
        # Use Popen for streaming output
        process = subprocess.Popen(cmd)
        process.wait()
    except KeyboardInterrupt:
        console.print("\n[yellow]Log streaming stopped[/yellow]")
        process.terminate()


@app.command("restart")
def restart(
    service: str | None = typer.Argument(None, help="Service name to restart (or all if not specified)"),
    compose_file: str | None = typer.Option(None, "--compose", "-c", help="Path to docker-compose.yml"),
    dev: bool = typer.Option(False, "--dev", help="Use development compose file"),
):
    """Restart Synapse GraphRAG services."""

    # Determine compose file
    if compose_file:
        compose_path = Path(compose_file)
    elif dev:
        compose_path = Path(DEFAULT_DEV_COMPOSE_FILE)
    else:
        compose_path = Path(DEFAULT_COMPOSE_FILE)

    if not compose_path.exists():
        console.print(f"[red]Compose file not found: {compose_path}[/red]")
        raise typer.Exit(1)

    # Build command
    cmd = ["docker", "compose", "-f", str(compose_path), "restart"]
    if service:
        cmd.append(service)

    console.print(f"[blue]Restarting services: {' '.join(cmd)}[/blue]")

    try:
        subprocess.run(cmd, check=True)
        console.print("[green]✅ Services restarted successfully[/green]")
    except subprocess.CalledProcessError as e:
        console.print(f"[red]Failed to restart services: {e}[/red]")
        raise typer.Exit(1)


def _ensure_docker_running(start_docker: bool, timeout_seconds: int = 60) -> None:
    """Ensure Docker daemon is running."""
    def _docker_info_ok() -> bool:
        try:
            result = subprocess.run(["docker", "info"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return result.returncode == 0
        except Exception:
            return False

    # Fast path
    if _docker_info_ok():
        return

    if sys.platform == "darwin" and start_docker:
        try:
            # Launch Docker Desktop
            subprocess.Popen(["open", "-a", "Docker"])
            console.print("[blue]Starting Docker Desktop...[/blue]")
        except Exception as e:
            raise RuntimeError(f"Failed to start Docker Desktop: {e}")

        # Poll until docker works or timeout
        deadline = time.time() + max(10, timeout_seconds)
        while time.time() < deadline:
            if _docker_info_ok():
                console.print("[green]✅ Docker is running[/green]")
                return
            time.sleep(1.5)

        raise RuntimeError("Timed out waiting for Docker Desktop to start.")

    # Non-macOS or not allowed to auto-start
    raise RuntimeError("Docker is not running. Please start Docker and retry.")


def _wait_for_memgraph(timeout: int = 60) -> bool:
    """Wait for Memgraph to accept connections."""
    host = os.getenv("SYNAPSE_MEMGRAPH_HOST", "127.0.0.1")
    try:
        port = int(os.getenv("SYNAPSE_MEMGRAPH_PORT", "7687"))
    except ValueError:
        port = 7687

    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with socket.create_connection((host, port), timeout=2.0):
                return True
        except OSError:
            time.sleep(1.0)

    return False


def _check_memgraph() -> bool:
    """Quick check if Memgraph is ready."""
    return _wait_for_memgraph(timeout=5)


def _wait_for_api(timeout: int = 60) -> bool:
    """Wait for GraphRAG API to be ready."""
    api_url = os.getenv("SYNAPSE_API_BASE_URL", "http://localhost:8000")
    health_url = f"{api_url}/health"

    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with httpx.Client() as client:
                response = client.get(health_url, timeout=5.0)
                if response.status_code == 200:
                    data = response.json()
                    if data.get("status") == "healthy":
                        return True
        except Exception:
            pass
        time.sleep(2.0)

    return False


def _check_api() -> bool:
    """Quick check if API is ready."""
    return _wait_for_api(timeout=5)
