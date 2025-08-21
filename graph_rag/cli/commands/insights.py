"""Smart business intelligence discovery commands."""

import json
from typing import Any

import httpx
import typer
from rich.console import Console
from rich.panel import Panel
from rich.text import Text

app = typer.Typer(help="Business intelligence and smart discovery commands")
console = Console()

DEFAULT_API_URL = "http://localhost:8000/api/v1"

# Business-focused search queries for insights
BUSINESS_INSIGHTS = {
    "strategy": [
        "business strategy",
        "strategic planning",
        "growth strategy",
        "competitive advantage",
        "market strategy"
    ],
    "revenue": [
        "revenue growth",
        "revenue streams",
        "monetization",
        "pricing strategy",
        "sales strategy"
    ],
    "operations": [
        "operational efficiency",
        "process optimization",
        "cost reduction",
        "resource allocation",
        "productivity"
    ],
    "innovation": [
        "innovation strategy",
        "product development",
        "technology trends",
        "R&D",
        "digital transformation"
    ],
    "market": [
        "market analysis",
        "customer insights",
        "market trends",
        "competitive analysis",
        "market opportunity"
    ],
    "team": [
        "team building",
        "leadership development",
        "organizational culture",
        "talent acquisition",
        "employee engagement"
    ]
}


def _make_search_request(query: str, limit: int = 5, api_url: str = DEFAULT_API_URL) -> dict[str, Any]:
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
        raise typer.Exit(1)
    except httpx.HTTPStatusError as e:
        console.print(f"[red]API returned error {e.response.status_code}: {e.response.text}[/red]")
        raise typer.Exit(1)


def _format_insights(results: list[dict], query: str) -> None:
    """Format and display search results as business insights."""
    if not results:
        console.print(f"[yellow]No insights found for: {query}[/yellow]")
        return

    console.print(f"\n[bold blue]💡 Insights for: {query}[/bold blue]")

    for i, result in enumerate(results, 1):
        chunk = result.get("chunk", {})
        score = result.get("score", 0.0)
        doc = result.get("document", {})

        text = chunk.get("text", "")[:200] + "..." if len(chunk.get("text", "")) > 200 else chunk.get("text", "")

        # Extract metadata
        topics = doc.get("metadata", {}).get("topics", []) if doc else []
        source = doc.get("metadata", {}).get("id_source", "unknown") if doc else "unknown"

        panel_title = f"Insight #{i}"
        if topics:
            panel_title += f" - {', '.join(topics[:2])}"
        if score > 0:
            panel_title += f" (relevance: {score:.3f})"

        panel_content = Text()
        panel_content.append(text)
        if source != "unknown":
            panel_content.append(f"\n\n[dim]Source: {source}[/dim]")

        console.print(Panel(panel_content, title=panel_title, border_style="blue"))


@app.command("explore")
def explore_category(
    category: str = typer.Argument(..., help="Business category to explore (strategy, revenue, operations, innovation, market, team)"),
    limit: int = typer.Option(3, "--limit", "-l", help="Results per insight area"),
    api_url: str = typer.Option(DEFAULT_API_URL, "--api-url", help="API base URL"),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON")
) -> None:
    """Explore business insights by category."""

    if category not in BUSINESS_INSIGHTS:
        available = ", ".join(BUSINESS_INSIGHTS.keys())
        console.print(f"[red]Unknown category '{category}'. Available: {available}[/red]")
        raise typer.Exit(1)

    queries = BUSINESS_INSIGHTS[category]

    if json_output:
        all_results = {}
        for query in queries:
            result = _make_search_request(query, limit, api_url)
            all_results[query] = result.get("results", [])
        console.print(json.dumps(all_results, indent=2))
    else:
        console.print(f"\n[bold green]🔍 Exploring {category.upper()} insights[/bold green]")

        for query in queries:
            result = _make_search_request(query, limit, api_url)
            results = result.get("results", [])
            _format_insights(results, query)


@app.command("themes")
def discover_themes(
    limit: int = typer.Option(5, "--limit", "-l", help="Results per theme"),
    api_url: str = typer.Option(DEFAULT_API_URL, "--api-url", help="API base URL"),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON")
) -> None:
    """Discover key business themes across all categories."""

    console.print("\n[bold magenta]🎯 Discovering Key Business Themes[/bold magenta]")

    theme_queries = [
        "key objectives",
        "main challenges",
        "core values",
        "success metrics",
        "future goals"
    ]

    if json_output:
        all_results = {}
        for query in theme_queries:
            result = _make_search_request(query, limit, api_url)
            all_results[query] = result.get("results", [])
        console.print(json.dumps(all_results, indent=2))
    else:
        for query in theme_queries:
            result = _make_search_request(query, limit, api_url)
            results = result.get("results", [])
            _format_insights(results, query)


@app.command("opportunities")
def find_opportunities(
    focus: str = typer.Option("growth", "--focus", "-f", help="Focus area: growth, efficiency, innovation, market"),
    limit: int = typer.Option(4, "--limit", "-l", help="Results per opportunity type"),
    api_url: str = typer.Option(DEFAULT_API_URL, "--api-url", help="API base URL"),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON")
) -> None:
    """Identify business opportunities based on focus area."""

    opportunity_queries = {
        "growth": ["expansion opportunities", "new markets", "growth potential", "scaling strategies"],
        "efficiency": ["process improvements", "cost savings", "automation opportunities", "efficiency gains"],
        "innovation": ["innovation gaps", "emerging technologies", "product opportunities", "creative solutions"],
        "market": ["market gaps", "unmet needs", "competitive advantages", "market trends"]
    }

    if focus not in opportunity_queries:
        available = ", ".join(opportunity_queries.keys())
        console.print(f"[red]Unknown focus '{focus}'. Available: {available}[/red]")
        raise typer.Exit(1)

    queries = opportunity_queries[focus]

    console.print(f"\n[bold yellow]💰 {focus.upper()} Opportunities[/bold yellow]")

    if json_output:
        all_results = {}
        for query in queries:
            result = _make_search_request(query, limit, api_url)
            all_results[query] = result.get("results", [])
        console.print(json.dumps(all_results, indent=2))
    else:
        for query in queries:
            result = _make_search_request(query, limit, api_url)
            results = result.get("results", [])
            _format_insights(results, query)


@app.command("summary")
def business_summary(
    api_url: str = typer.Option(DEFAULT_API_URL, "--api-url", help="API base URL"),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON")
) -> None:
    """Generate a comprehensive business intelligence summary."""

    console.print("\n[bold cyan]📊 Business Intelligence Summary[/bold cyan]")

    # High-level overview queries
    summary_queries = [
        "mission vision",
        "business model",
        "target market",
        "competitive position",
        "key performance indicators"
    ]

    if json_output:
        all_results = {}
        for query in summary_queries:
            result = _make_search_request(query, 2, api_url)
            all_results[query] = result.get("results", [])
        console.print(json.dumps(all_results, indent=2))
    else:
        for query in summary_queries:
            result = _make_search_request(query, 2, api_url)
            results = result.get("results", [])
            _format_insights(results, query)


@app.command("trends")
def analyze_trends(
    timeframe: str = typer.Option("current", "--timeframe", "-t", help="Timeframe: current, emerging, future"),
    limit: int = typer.Option(3, "--limit", "-l", help="Results per trend"),
    api_url: str = typer.Option(DEFAULT_API_URL, "--api-url", help="API base URL"),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON")
) -> None:
    """Analyze business trends and patterns."""

    trend_queries = {
        "current": ["current trends", "market dynamics", "industry shifts", "consumer behavior"],
        "emerging": ["emerging trends", "new opportunities", "disruption", "innovation trends"],
        "future": ["future outlook", "predictions", "long-term trends", "strategic foresight"]
    }

    if timeframe not in trend_queries:
        available = ", ".join(trend_queries.keys())
        console.print(f"[red]Unknown timeframe '{timeframe}'. Available: {available}[/red]")
        raise typer.Exit(1)

    queries = trend_queries[timeframe]

    console.print(f"\n[bold green]📈 {timeframe.upper()} Trends Analysis[/bold green]")

    if json_output:
        all_results = {}
        for query in queries:
            result = _make_search_request(query, limit, api_url)
            all_results[query] = result.get("results", [])
        console.print(json.dumps(all_results, indent=2))
    else:
        for query in queries:
            result = _make_search_request(query, limit, api_url)
            results = result.get("results", [])
            _format_insights(results, query)


if __name__ == "__main__":
    app()
