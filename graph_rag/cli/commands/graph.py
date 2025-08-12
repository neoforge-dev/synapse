import json
from typing import Optional

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
    types: Optional[str] = typer.Option(None, "--types", help="Comma-separated relationship types"),
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
    seed: Optional[str] = typer.Option(None, "--seed", help="Seed id for subgraph export"),
    depth: int = typer.Option(1, "--depth", help="Traversal depth (1..3)"),
    format: str = typer.Option("json", "--format", help="Export format: json|graphml"),
    outfile: Optional[str] = typer.Option(None, "--out", help="Write to file path"),
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
