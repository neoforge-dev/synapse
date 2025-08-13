import json
import logging
import sys
import subprocess

import httpx
import typer
import os

API_BASE_URL = os.getenv("SYNAPSE_API_BASE_URL", "http://localhost:8000")
HEALTH_URL = f"{API_BASE_URL}/health"
API_V1 = f"{API_BASE_URL}/api/v1"

logger = logging.getLogger(__name__)
app = typer.Typer(help="Admin and maintenance commands")


@app.command("health")
def check_health(
    api_url: str = typer.Option(
        HEALTH_URL, help="URL of the health check API endpoint."
    ),
):
    """Check the health status of the Synapse API."""
    logger.info(f"Checking API health at {api_url}...")

    try:
        with httpx.Client() as client:
            response = client.get(api_url, timeout=10.0)
            response.raise_for_status()  # Raises for 4xx/5xx

            response_data = response.json()
            logger.info(
                f"API Health Response ({response.status_code}): {response_data}"
            )
            status = response_data.get("status", "unknown")
            print(f"API Status: {status.upper()}")
            if response.status_code != 200 or status != "healthy":
                print("Warning: API reported an unhealthy status.", file=sys.stderr)
                raise SystemExit(1)
            print("API appears healthy.")

    except httpx.RequestError as exc:
        logger.error(
            f"API request failed: {exc.request.method} {exc.request.url} - {exc}"
        )
        print(
            f"Error: Failed to connect to the API at {api_url}. Is it running?",
            file=sys.stderr,
        )
        raise SystemExit(1)
    except httpx.HTTPStatusError as exc:
        logger.error(
            f"API returned an error: {exc.response.status_code} - {exc.response.text}"
        )
        detail = exc.response.text
        try:
            detail_json = exc.response.json()
            detail = detail_json.get("detail", detail)
        except json.JSONDecodeError:
            pass
        print(
            f"Error: API health check failed with status {exc.response.status_code}. Detail: {detail}",
            file=sys.stderr,
        )
        raise SystemExit(1)
    except Exception as e:
        logger.error(
            f"An unexpected error occurred during health check: {e}", exc_info=True
        )
        print(f"An unexpected error occurred: {e}", file=sys.stderr)
        raise SystemExit(1)


@app.command("vector-stats")
def vector_stats(
    api_url: str = typer.Option(f"{API_V1}/admin/vector/stats", help="Admin vector stats endpoint"),
):
    try:
        with httpx.Client() as client:
            r = client.get(api_url, timeout=15.0)
            r.raise_for_status()
            print(json.dumps(r.json(), indent=2))
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        raise SystemExit(1)


@app.command("vector-rebuild")
def vector_rebuild(
    api_url: str = typer.Option(f"{API_V1}/admin/vector/rebuild", help="Admin vector rebuild endpoint"),
):
    try:
        with httpx.Client() as client:
            r = client.post(api_url, timeout=60.0)
            r.raise_for_status()
            print(json.dumps(r.json(), indent=2))
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        raise SystemExit(1)


@app.command("integrity-check")
def integrity_check(
    api_url: str = typer.Option(f"{API_V1}/admin/integrity/check", help="Integrity check endpoint"),
):
    try:
        with httpx.Client() as client:
            r = client.get(api_url, timeout=30.0)
            r.raise_for_status()
            print(json.dumps(r.json(), indent=2))
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        raise SystemExit(1)


@app.command("up")
def up(
    compose_file: str = typer.Option(None, "--compose", help="Path to docker-compose.yml"),
    detached: bool = typer.Option(True, "--detached/--no-detached", help="Run docker compose up -d"),
    wait_bolt: bool = typer.Option(
        True,
        "--wait-bolt/--no-wait-bolt",
        help="Wait for Memgraph Bolt (127.0.0.1:7687) to accept connections",
    ),
    wait_timeout: int = typer.Option(60, "--wait-timeout", help="Seconds to wait for Bolt readiness"),
):
    """Bring up Memgraph/API via docker compose and optionally wait for Bolt readiness."""
    compose = compose_file or os.getenv("SYNAPSE_DOCKER_COMPOSE", "docker-compose.yml")
    args = ["docker", "compose", "-f", compose, "up"]
    if detached:
        args.append("-d")
    logger.info("Running: %s", " ".join(args))
    try:
        proc = subprocess.run(args, check=True)
        if proc.returncode == 0:
            typer.echo("compose up completed")
        else:
            raise RuntimeError(f"compose exited with {proc.returncode}")
    except Exception as e:
        typer.echo(f"Failed to run docker compose: {e}")
        raise typer.Exit(1)

    if not wait_bolt:
        return

    # Poll Bolt port for readiness
    import socket
    import time as _time

    host = os.getenv("SYNAPSE_MEMGRAPH_HOST", "127.0.0.1")
    try:
        port = int(os.getenv("SYNAPSE_MEMGRAPH_PORT", "7687"))
    except ValueError:
        port = 7687

    deadline = _time.time() + max(1, wait_timeout)
    typer.echo(f"Waiting for Memgraph Bolt at {host}:{port} (timeout {wait_timeout}s)...")
    while _time.time() < deadline:
        try:
            with socket.create_connection((host, port), timeout=2.0):
                typer.echo("Memgraph Bolt is ready.")
                return
        except OSError:
            _time.sleep(1.0)

    typer.echo("Timed out waiting for Memgraph Bolt readiness.")
    raise typer.Exit(2)
