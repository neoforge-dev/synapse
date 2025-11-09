"""Enhanced search with explanations and entity relations."""

import json
from typing import Any

import httpx
import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

app = typer.Typer(help="Enhanced search with explanations and entity relations")
console = Console()

DEFAULT_API_URL = "http://localhost:8000/api/v1"


def _make_search_request(query: str, limit: int, api_url: str) -> dict[str, Any]:
    """Make a search request to the API."""
    url = f"{api_url}/search/query"

    payload = {
        "query": query,
        "search_type": "vector",
        "limit": limit
    }

    try:
        response = httpx.post(url, json=payload, timeout=30.0)
        response.raise_for_status()
        return response.json()
    except httpx.RequestError as e:
        console.print(f"[red]Error connecting to API: {e}[/red]")
        raise typer.Exit(1) from None
    except httpx.HTTPStatusError as e:
        console.print(f"[red]API returned error {e.response.status_code}: {e.response.text}[/red]")
        raise typer.Exit(1) from None


def _get_entity_neighbors(entity_id: str, api_url: str) -> dict[str, Any]:
    """Get entity neighbors from the graph."""
    url = f"{api_url}/graph/neighbors"

    params = {
        "id": entity_id,
        "depth": 1
    }

    try:
        response = httpx.get(url, params=params, timeout=10.0)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        console.print(f"[yellow]Could not fetch entity relations for {entity_id}: {e}[/yellow]")
        return {"nodes": [], "edges": []}


def _extract_entities_from_text(text: str) -> list[str]:
    """Extract potential entity mentions from text (simple keyword-based approach)."""
    # Simple approach: look for capitalized words that might be entities
    import re

    # Look for capitalized words/phrases (potential entities)
    potential_entities = re.findall(r'\b[A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+)*\b', text)

    # Filter out common words that aren't likely entities
    stop_words = {'The', 'This', 'That', 'And', 'Or', 'But', 'If', 'When', 'Where', 'How', 'Why', 'What', 'Who'}
    entities = [e for e in potential_entities if e not in stop_words and len(e) > 2]

    return list(set(entities))  # Remove duplicates


def _generate_explanation(query: str, result: dict[str, Any]) -> str:
    """Generate explanation for why this result is relevant."""
    chunk = result.get("chunk", {})
    score = result.get("score", 0.0)
    text = chunk.get("text", "")

    # Simple explanation based on content analysis
    explanation_parts = []

    # Analyze relevance
    if score > 0.5:
        explanation_parts.append("🎯 **High relevance** - Strong semantic similarity to your query")
    elif score > 0.2:
        explanation_parts.append("📍 **Moderate relevance** - Contains related concepts")
    else:
        explanation_parts.append("🔍 **Potential relevance** - May contain contextual information")

    # Check for query terms
    query_words = query.lower().split()
    text_lower = text.lower()
    matching_words = [word for word in query_words if word in text_lower]
    if matching_words:
        explanation_parts.append(f"💬 **Direct matches**: {', '.join(matching_words)}")

    # Identify content type
    if len(text) > 500:
        explanation_parts.append("📄 **Comprehensive content** - Detailed information available")
    elif len(text) < 100:
        explanation_parts.append("🏷️  **Summary content** - Concise key information")

    return " • ".join(explanation_parts)


def _format_enhanced_result(query: str, result: dict[str, Any], index: int, api_url: str, show_entities: bool = True) -> None:
    """Format and display enhanced search result with explanations and entity context."""
    chunk = result.get("chunk", {})
    score = result.get("score", 0.0)
    doc = result.get("document", {})

    text = chunk.get("text", "")
    chunk_id = chunk.get("id", "")

    # Extract metadata
    topics = doc.get("metadata", {}).get("topics", [])
    source = doc.get("metadata", {}).get("id_source", "unknown")

    # Generate explanation
    explanation = _generate_explanation(query, result)

    # Panel title with enhanced info
    panel_title = f"🔍 Result #{index}"
    if topics:
        panel_title += f" - {', '.join(topics[:2])}"
    if score > 0:
        panel_title += f" (similarity: {score:.3f})"

    # Main content
    content = Text()

    # Add explanation
    content.append("💡 ", style="bold yellow")
    content.append("Why this is relevant:\n", style="bold")
    content.append(f"{explanation}\n\n", style="dim")

    # Add main text (truncated if long)
    content.append("📝 ", style="bold blue")
    content.append("Content:\n", style="bold")
    display_text = text[:400] + "..." if len(text) > 400 else text
    content.append(f"{display_text}\n\n", style="")

    # Add entity analysis if requested
    if show_entities:
        entities = _extract_entities_from_text(text)
        if entities:
            content.append("🏷️ ", style="bold green")
            content.append("Entities mentioned: ", style="bold")
            content.append(f"{', '.join(entities[:5])}\n", style="green")

            # Try to get graph relations for first entity
            if entities and len(entities) > 0:
                entity_relations = _get_entity_neighbors(entities[0], api_url)
                if entity_relations.get("edges"):
                    content.append(f"🔗 Graph connections for '{entities[0]}': ", style="dim")
                    edge_types = [edge.get("type", "UNKNOWN") for edge in entity_relations.get("edges", [])[:3]]
                    content.append(f"{', '.join(set(edge_types))}\n", style="dim cyan")

    # Add source info
    content.append(f"\n[dim]📁 Source: {source} | ID: {chunk_id[:8]}...[/dim]")

    console.print(Panel(content, title=panel_title, border_style="blue"))


@app.command("explain")
def enhanced_search(
    query: str = typer.Argument(..., help="Search query"),
    limit: int = typer.Option(5, "--limit", "-l", help="Number of results"),
    entities: bool = typer.Option(True, "--entities/--no-entities", help="Show entity analysis"),
    relations: bool = typer.Option(True, "--relations/--no-relations", help="Show graph relations"),
    api_url: str = typer.Option(DEFAULT_API_URL, "--api-url", help="API base URL"),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON")
) -> None:
    """Enhanced search with explanations and entity relationship analysis."""

    console.print(f"\n[bold blue]🔍 Enhanced Search Results for: [cyan]{query}[/cyan][/bold blue]")

    # Perform search
    result = _make_search_request(query, limit, api_url)
    results = result.get("results", [])

    if not results:
        console.print("[yellow]No results found for your query.[/yellow]")
        return

    if json_output:
        # Enhanced JSON output with explanations
        enhanced_results = []
        for i, res in enumerate(results, 1):
            enhanced_res = dict(res)
            enhanced_res["explanation"] = _generate_explanation(query, res)
            if entities:
                text = res.get("chunk", {}).get("text", "")
                enhanced_res["entities"] = _extract_entities_from_text(text)
            enhanced_results.append(enhanced_res)

        console.print(json.dumps({"query": query, "results": enhanced_results}, indent=2))
    else:
        # Rich formatted output
        for i, res in enumerate(results, 1):
            _format_enhanced_result(query, res, i, api_url, show_entities=entities and relations)
            if i < len(results):
                console.print()  # Add spacing between results


@app.command("compare")
def compare_queries(
    query1: str = typer.Argument(..., help="First query"),
    query2: str = typer.Argument(..., help="Second query"),
    limit: int = typer.Option(3, "--limit", "-l", help="Results per query"),
    api_url: str = typer.Option(DEFAULT_API_URL, "--api-url", help="API base URL")
) -> None:
    """Compare search results between two queries to identify relationships."""

    console.print("\n[bold magenta]⚖️  Comparing Search Results[/bold magenta]")
    console.print(f"Query 1: [cyan]{query1}[/cyan]")
    console.print(f"Query 2: [cyan]{query2}[/cyan]\n")

    # Get results for both queries
    result1 = _make_search_request(query1, limit, api_url)
    result2 = _make_search_request(query2, limit, api_url)

    results1 = result1.get("results", [])
    results2 = result2.get("results", [])

    # Find overlapping chunks
    chunks1_ids = {r.get("chunk", {}).get("id") for r in results1}
    chunks2_ids = {r.get("chunk", {}).get("id") for r in results2}
    overlap = chunks1_ids & chunks2_ids

    if overlap:
        console.print(f"[green]🎯 Found {len(overlap)} overlapping results - these concepts are related![/green]")
        console.print(f"Shared content IDs: {', '.join(list(overlap)[:3])}")
    else:
        console.print("[yellow]🔍 No direct overlapping results - these may be distinct concepts[/yellow]")

    # Show side-by-side comparison
    table = Table(title="Query Comparison")
    table.add_column(f"Query 1: {query1}", style="cyan")
    table.add_column(f"Query 2: {query2}", style="magenta")

    max_results = max(len(results1), len(results2))
    for i in range(max_results):
        text1 = ""
        text2 = ""

        if i < len(results1):
            chunk1 = results1[i].get("chunk", {})
            text1 = chunk1.get("text", "")[:100] + "..." if len(chunk1.get("text", "")) > 100 else chunk1.get("text", "")

        if i < len(results2):
            chunk2 = results2[i].get("chunk", {})
            text2 = chunk2.get("text", "")[:100] + "..." if len(chunk2.get("text", "")) > 100 else chunk2.get("text", "")

        table.add_row(text1, text2)

    console.print(table)


if __name__ == "__main__":
    app()
