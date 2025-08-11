import json
from pathlib import Path
from typing import Optional

import typer

from graph_rag.config import Settings

app = typer.Typer(help="Configuration utilities")


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
    path: Optional[Path] = typer.Option(None, "--path", help="Path to write .env"),
    force: bool = typer.Option(False, "--force", help="Overwrite if exists"),
) -> None:
    """Create a .env template with common settings."""
    p = path or Path(".env")
    if p.exists() and not force:
        typer.echo(f"Refusing to overwrite existing {p}. Use --force to override.")
        raise typer.Exit(code=1)
    template = (
        "# Synapse configuration\n"
        "SYNAPSE_API_HOST=0.0.0.0\n"
        "SYNAPSE_API_PORT=8000\n"
        "SYNAPSE_API_LOG_LEVEL=INFO\n"
        "SYNAPSE_API_LOG_JSON=false\n"
        "SYNAPSE_ENABLE_METRICS=true\n"
        "SYNAPSE_VECTOR_STORE_TYPE=faiss\n"
        "SYNAPSE_VECTOR_STORE_PATH=~/.graph_rag/faiss_store\n"
        "SYNAPSE_EMBEDDING_PROVIDER=sentence-transformers\n"
        "SYNAPSE_VECTOR_STORE_EMBEDDING_MODEL=all-MiniLM-L6-v2\n"
        "# Memgraph\n"
        "SYNAPSE_MEMGRAPH_HOST=127.0.0.1\n"
        "SYNAPSE_MEMGRAPH_PORT=7687\n"
        "SYNAPSE_MEMGRAPH_USE_SSL=false\n"
    )
    p.write_text(template)
    typer.echo(f"Wrote {p}")
