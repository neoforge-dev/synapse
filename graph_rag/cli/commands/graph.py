import json
import webbrowser

import httpx
import typer

from graph_rag.config import get_settings

settings = get_settings()
API_BASE_URL = f"http://{settings.api_host}:{settings.api_port}/api/v1"

app = typer.Typer(help="Graph exploration commands")


@app.command()
def neighbors(
    id: str = typer.Option(..., "--id", help="Start node id"),
    depth: int = typer.Option(1, "--depth", help="Traversal depth (1..3)"),
    types: str | None = typer.Option(None, "--types", help="Comma-separated relationship types"),
    json_out: bool = typer.Option(False, "--json", help="Print JSON result"),
):
    url = f"{API_BASE_URL}/graph/neighbors"
    params = {"id": id, "depth": depth}
    if types:
        params["types"] = types
    with httpx.Client() as client:
        r = client.get(url, params=params)
        r.raise_for_status()
        data = r.json()
    if json_out:
        typer.echo(json.dumps(data, indent=2))
    else:
        typer.echo(f"nodes={len(data.get('nodes', []))} edges={len(data.get('edges', []))}")


@app.command()
def export(
    seed: str | None = typer.Option(None, "--seed", help="Seed id for subgraph export"),
    depth: int = typer.Option(1, "--depth", help="Traversal depth (1..3)"),
    format: str = typer.Option("json", "--format", help="Export format: json|graphml"),
    outfile: str | None = typer.Option(None, "--out", help="Write to file path"),
):
    url = f"{API_BASE_URL}/graph/export"
    params = {"format": format, "depth": depth}
    if seed:
        params["seed"] = seed
    with httpx.Client() as client:
        r = client.get(url, params=params)
        r.raise_for_status()
        body = r.text
    if outfile:
        with open(outfile, "w", encoding="utf-8") as f:
            f.write(body)
        typer.echo(f"wrote {format} to {outfile}")
    else:
        typer.echo(body)


@app.command("viz")
def viz(
    seed: str | None = typer.Option(None, "--seed", help="Starting node for visualization"),
    port: int = typer.Option(8000, "--port", help="API server port"),
    host: str = typer.Option("localhost", "--host", help="API server host"),
    open_browser: bool = typer.Option(True, "--open/--no-open", help="Open browser automatically"),
):
    """Open interactive graph visualization in browser."""
    base_url = f"http://{host}:{port}/api/v1/graph/viz"
    url = f"{base_url}?seed={seed}" if seed else base_url

    print(f"Graph visualization URL: {url}")

    if open_browser:
        try:
            webbrowser.open(url)
            print("Opened visualization in default browser.")
        except Exception as e:
            print(f"Could not open browser: {e}")
            print("Please open the URL manually.")
    else:
        print("Use --open to open in browser automatically.")
