import json
import logging
import os

import httpx
import typer

API_BASE_URL = os.getenv("SYNAPSE_API_BASE_URL", "http://localhost:8000/api/v1")
ASK_URL = f"{API_BASE_URL}/query/ask"

logger = logging.getLogger(__name__)


app = typer.Typer(help="Content ideation and suggestions using the knowledge base")


@app.callback(invoke_without_command=True)
def _default(
    topic: str = typer.Argument(..., help="Topic or question to ideate on"),
    k: int = typer.Option(5, "--k", help="Max context chunks to retrieve"),
    include_graph: bool = typer.Option(
        False, "--graph/--no-graph", help="Include graph context if available"
    ),
    style: str | None = typer.Option(
        None,
        "--style",
        help="Optional style profile or tone (e.g. 'concise, analytical')",
    ),
    count: int = typer.Option(5, "--count", help="Number of ideas to produce"),
    json_out: bool = typer.Option(False, "--json", help="Emit JSON output"),
    api_url: str = typer.Option(ASK_URL, help="URL of the ask API endpoint."),
):
    """Default entrypoint so `synapse suggest ...` works without subcommand."""
    return run_suggest(
        topic=topic,
        k=k,
        include_graph=include_graph,
        style=style,
        count=count,
        json_out=json_out,
        api_url=api_url,
    )


def run_suggest(
    topic: str = typer.Argument(..., help="Topic or question to ideate on"),
    k: int = typer.Option(5, "--k", help="Max context chunks to retrieve"),
    include_graph: bool = typer.Option(
        False, "--graph/--no-graph", help="Include graph context if available"
    ),
    style: str | None = typer.Option(
        None,
        "--style",
        help="Optional style profile or tone (e.g. 'concise, analytical')",
    ),
    count: int = typer.Option(5, "--count", help="Number of ideas to produce"),
    json_out: bool = typer.Option(False, "--json", help="Emit JSON output"),
    api_url: str = typer.Option(ASK_URL, help="URL of the ask API endpoint."),
):
    """Generate suggestions/ideas grounded in your corpus and graph."""
    prologue = (
        f"Generate {count} high-signal ideas on: {topic}. "
        "Focus on actionable, non-obvious insights."
    )
    if style:
        prologue += f" Adopt this style profile: {style}."

    payload = {"text": prologue, "k": k, "include_graph": include_graph}

    try:
        with httpx.Client() as client:
            resp = client.post(api_url, json=payload, timeout=60.0)
            resp.raise_for_status()
            data = resp.json()
            answer = data.get("answer", "")
            if json_out:
                typer.echo(
                    json.dumps({"topic": topic, "ideas": answer}, ensure_ascii=False)
                )
            else:
                typer.echo(answer)
    except httpx.HTTPStatusError as exc:
        logger.error(
            f"API returned an error: {exc.response.status_code} - {exc.response.text}"
        )
        raise typer.Exit(code=1) from None
    except Exception as e:
        logger.error(f"Suggest command failed: {e}", exc_info=True)
        raise typer.Exit(code=1) from None


# Keep an explicit subcommand for future extension, but default is callback
@app.command("generate")
def _generate(
    topic: str,
    k: int = 5,
    include_graph: bool = False,
    style: str | None = None,
    count: int = 5,
    json_out: bool = False,
    api_url: str = ASK_URL,
):
    return run_suggest(
        topic=topic,
        k=k,
        include_graph=include_graph,
        style=style,
        count=count,
        json_out=json_out,
        api_url=api_url,
    )
