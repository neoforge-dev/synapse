"""Advanced business intelligence analytics and insights."""

import json
from collections import Counter, defaultdict
from typing import Dict, List, Any, Tuple

import httpx
import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich.progress import track
from rich.tree import Tree

app = typer.Typer(help="Advanced business analytics and intelligence")
console = Console()

DEFAULT_API_URL = "http://localhost:8000/api/v1"

# Advanced business analysis frameworks
BUSINESS_FRAMEWORKS = {
    "swot": {
        "strengths": ["competitive advantage", "core competencies", "unique value", "strong performance"],
        "weaknesses": ["challenges", "limitations", "gaps", "areas for improvement"],
        "opportunities": ["market opportunities", "growth potential", "emerging trends", "new markets"],
        "threats": ["risks", "competitive threats", "market challenges", "external risks"]
    },
    "porter": {
        "competitive_rivalry": ["competition", "competitive landscape", "market share", "rivals"],
        "supplier_power": ["supplier relationships", "supply chain", "vendor management", "procurement"],
        "buyer_power": ["customer power", "customer demands", "buyer behavior", "market influence"],
        "threat_of_substitutes": ["alternative solutions", "substitutes", "competitive products", "replacement options"],
        "barriers_to_entry": ["market barriers", "entry requirements", "competitive moats", "industry barriers"]
    },
    "value_chain": {
        "primary_activities": ["operations", "logistics", "marketing", "sales", "service"],
        "support_activities": ["infrastructure", "hr management", "technology", "procurement"]
    }
}


def _make_search_request(query: str, limit: int, api_url: str) -> Dict[str, Any]:
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
    except Exception as e:
        console.print(f"[red]Error making search request: {e}[/red]")
        return {"results": []}


def _extract_keywords(text: str) -> List[str]:
    """Extract keywords from text using simple NLP."""
    import re
    
    # Remove common stop words and extract meaningful terms
    stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'is', 'are', 'was', 'were', 'be', 'been', 'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could', 'should', 'may', 'might', 'can', 'shall', 'this', 'that', 'these', 'those'}
    
    # Extract words, filter out stop words and short words
    words = re.findall(r'\b[a-zA-Z]+\b', text.lower())
    keywords = [w for w in words if w not in stop_words and len(w) > 3]
    
    return keywords


def _analyze_content_themes(results: List[Dict]) -> Dict[str, int]:
    """Analyze common themes across search results."""
    all_keywords = []
    
    for result in results:
        text = result.get("chunk", {}).get("text", "")
        keywords = _extract_keywords(text)
        all_keywords.extend(keywords)
    
    # Count keyword frequency
    keyword_counts = Counter(all_keywords)
    return dict(keyword_counts.most_common(10))


def _calculate_coverage_metrics(results: List[Dict]) -> Dict[str, Any]:
    """Calculate coverage and quality metrics for search results."""
    if not results:
        return {"total_results": 0}
    
    total_chars = sum(len(r.get("chunk", {}).get("text", "")) for r in results)
    avg_length = total_chars / len(results) if results else 0
    
    # Document diversity
    doc_ids = [r.get("chunk", {}).get("document_id") for r in results]
    unique_docs = len(set(doc_ids))
    
    # Topic diversity
    all_topics = []
    for r in results:
        topics = r.get("document", {}).get("metadata", {}).get("topics", [])
        all_topics.extend(topics)
    unique_topics = len(set(all_topics))
    
    return {
        "total_results": len(results),
        "unique_documents": unique_docs,
        "unique_topics": unique_topics,
        "avg_content_length": int(avg_length),
        "total_content_chars": total_chars,
        "document_diversity": unique_docs / len(results) if results else 0
    }


@app.command("swot")
def swot_analysis(
    api_url: str = typer.Option(DEFAULT_API_URL, "--api-url", help="API base URL"),
    limit: int = typer.Option(5, "--limit", "-l", help="Results per SWOT category"),
    export_json: bool = typer.Option(False, "--json", help="Export as JSON")
) -> None:
    """Perform SWOT analysis using business intelligence from knowledge graph."""
    
    console.print("\n[bold blue]📊 SWOT Analysis[/bold blue]")
    console.print("[dim]Analyzing Strengths, Weaknesses, Opportunities, and Threats[/dim]\n")
    
    swot_results = {}
    
    for category, queries in track(BUSINESS_FRAMEWORKS["swot"].items(), description="Analyzing SWOT categories..."):
        category_results = []
        
        for query in queries[:2]:  # Limit queries per category
            result = _make_search_request(query, limit, api_url)
            category_results.extend(result.get("results", []))
        
        swot_results[category] = category_results
    
    if export_json:
        console.print(json.dumps(swot_results, indent=2))
        return
    
    # Display SWOT matrix
    table = Table(title="SWOT Analysis Matrix")
    table.add_column("Strengths", style="green")
    table.add_column("Weaknesses", style="red")
    table.add_column("Opportunities", style="yellow")
    table.add_column("Threats", style="magenta")
    
    max_items = max(len(swot_results.get(cat, [])) for cat in ["strengths", "weaknesses", "opportunities", "threats"])
    
    for i in range(min(max_items, 3)):  # Show top 3 items per category
        row = []
        for category in ["strengths", "weaknesses", "opportunities", "threats"]:
            if i < len(swot_results.get(category, [])):
                item = swot_results[category][i]
                text = item.get("chunk", {}).get("text", "")[:80] + "..."
                row.append(text)
            else:
                row.append("")
        table.add_row(*row)
    
    console.print(table)
    
    # Show insights summary
    for category, results in swot_results.items():
        if results:
            themes = _analyze_content_themes(results)
            console.print(f"\n[bold]{category.upper()} Key Themes:[/bold]")
            for theme, count in list(themes.items())[:3]:
                console.print(f"  • {theme} ({count} mentions)")


@app.command("trends")
def trend_analysis(
    timeframe: str = typer.Option("quarterly", "--timeframe", "-t", help="Analysis timeframe: monthly, quarterly, yearly"),
    api_url: str = typer.Option(DEFAULT_API_URL, "--api-url", help="API base URL"),
    limit: int = typer.Option(10, "--limit", "-l", help="Results per trend query")
) -> None:
    """Analyze business trends and patterns over time."""
    
    console.print(f"\n[bold green]📈 {timeframe.upper()} Trend Analysis[/bold green]")
    
    trend_queries = [
        "growth trends",
        "market changes", 
        "performance metrics",
        "customer behavior",
        "technology adoption",
        "competitive landscape"
    ]
    
    trend_data = {}
    
    for query in track(trend_queries, description="Analyzing trends..."):
        result = _make_search_request(query, limit, api_url)
        results = result.get("results", [])
        
        # Analyze themes in results
        themes = _analyze_content_themes(results)
        metrics = _calculate_coverage_metrics(results)
        
        trend_data[query] = {
            "themes": themes,
            "metrics": metrics,
            "results_count": len(results)
        }
    
    # Display trend summary
    trend_table = Table(title=f"{timeframe.capitalize()} Trend Summary")
    trend_table.add_column("Trend Area", style="cyan")
    trend_table.add_column("Results", justify="right")
    trend_table.add_column("Top Theme", style="yellow")
    trend_table.add_column("Coverage", style="green")
    
    for trend, data in trend_data.items():
        top_theme = list(data["themes"].keys())[0] if data["themes"] else "N/A"
        coverage = f"{data['metrics']['unique_documents']} docs"
        
        trend_table.add_row(
            trend.title(),
            str(data["results_count"]),
            top_theme,
            coverage
        )
    
    console.print(trend_table)
    
    # Show detailed insights for top trend
    if trend_data:
        top_trend = max(trend_data.items(), key=lambda x: x[1]["results_count"])
        console.print(f"\n[bold]🎯 Deep Dive: {top_trend[0].title()}[/bold]")
        
        themes_text = ", ".join(f"{k}({v})" for k, v in list(top_trend[1]["themes"].items())[:5])
        console.print(f"Key themes: {themes_text}")


@app.command("kpis")
def kpi_analysis(
    category: str = typer.Option("all", "--category", "-c", help="KPI category: financial, operational, customer, growth, all"),
    api_url: str = typer.Option(DEFAULT_API_URL, "--api-url", help="API base URL"),
    limit: int = typer.Option(8, "--limit", "-l", help="Results per KPI area")
) -> None:
    """Analyze Key Performance Indicators from business intelligence."""
    
    kpi_categories = {
        "financial": ["revenue", "profit margins", "cost reduction", "ROI", "cash flow"],
        "operational": ["efficiency", "productivity", "quality metrics", "process improvement"],
        "customer": ["customer satisfaction", "retention rate", "acquisition cost", "lifetime value"],
        "growth": ["market share", "expansion", "new markets", "scaling", "user growth"]
    }
    
    console.print(f"\n[bold cyan]📊 KPI Analysis: {category.upper()}[/bold cyan]")
    
    categories_to_analyze = [category] if category != "all" else list(kpi_categories.keys())
    
    kpi_results = {}
    
    for cat in categories_to_analyze:
        if cat not in kpi_categories:
            console.print(f"[red]Unknown category: {cat}[/red]")
            continue
            
        console.print(f"\n[bold]Analyzing {cat.upper()} KPIs...[/bold]")
        
        cat_results = {}
        for kpi in track(kpi_categories[cat], description=f"Processing {cat} KPIs"):
            result = _make_search_request(kpi, limit, api_url)
            results = result.get("results", [])
            
            metrics = _calculate_coverage_metrics(results)
            themes = _analyze_content_themes(results)
            
            cat_results[kpi] = {
                "coverage": metrics,
                "themes": themes,
                "result_count": len(results)
            }
        
        kpi_results[cat] = cat_results
        
        # Display category summary
        kpi_table = Table(title=f"{cat.title()} KPI Summary")
        kpi_table.add_column("KPI", style="cyan")
        kpi_table.add_column("Results", justify="right")
        kpi_table.add_column("Docs", justify="right") 
        kpi_table.add_column("Top Theme", style="yellow")
        
        for kpi, data in cat_results.items():
            top_theme = list(data["themes"].keys())[0] if data["themes"] else "N/A"
            
            kpi_table.add_row(
                kpi.title(),
                str(data["result_count"]),
                str(data["coverage"]["unique_documents"]),
                top_theme
            )
        
        console.print(kpi_table)


@app.command("competitive")
def competitive_analysis(
    framework: str = typer.Option("porter", "--framework", "-f", help="Analysis framework: porter, generic"),
    api_url: str = typer.Option(DEFAULT_API_URL, "--api-url", help="API base URL"),
    limit: int = typer.Option(6, "--limit", "-l", help="Results per analysis area")
) -> None:
    """Perform competitive analysis using Porter's Five Forces or other frameworks."""
    
    if framework not in ["porter", "generic"]:
        console.print("[red]Available frameworks: porter, generic[/red]")
        return
    
    console.print(f"\n[bold magenta]⚔️ Competitive Analysis: {framework.upper()}[/bold magenta]")
    
    if framework == "porter":
        forces = BUSINESS_FRAMEWORKS["porter"]
        
        porter_results = {}
        
        for force, queries in track(forces.items(), description="Analyzing Porter's Five Forces..."):
            force_results = []
            
            for query in queries[:2]:  # Limit queries per force
                result = _make_search_request(query, limit, api_url)
                force_results.extend(result.get("results", []))
            
            porter_results[force] = force_results
        
        # Display Porter's Five Forces analysis
        for force, results in porter_results.items():
            if results:
                console.print(f"\n[bold]{force.replace('_', ' ').title()}:[/bold]")
                themes = _analyze_content_themes(results)
                metrics = _calculate_coverage_metrics(results)
                
                console.print(f"  Coverage: {metrics['unique_documents']} documents, {metrics['total_results']} results")
                
                if themes:
                    top_themes = list(themes.items())[:3]
                    for theme, count in top_themes:
                        console.print(f"  • {theme} ({count} mentions)")
    
    else:  # generic competitive analysis
        generic_queries = [
            "competitive advantages",
            "market positioning", 
            "differentiation strategy",
            "competitive threats",
            "market leaders"
        ]
        
        console.print("\n[bold]Generic Competitive Analysis:[/bold]")
        
        for query in track(generic_queries, description="Analyzing competitive landscape..."):
            result = _make_search_request(query, limit, api_url)
            results = result.get("results", [])
            
            if results:
                themes = _analyze_content_themes(results)
                console.print(f"\n[cyan]{query.title()}:[/cyan]")
                for theme, count in list(themes.items())[:3]:
                    console.print(f"  • {theme} ({count} mentions)")


@app.command("forecast")
def business_forecast(
    horizon: str = typer.Option("short", "--horizon", "-h", help="Forecast horizon: short, medium, long"),
    focus: str = typer.Option("growth", "--focus", "-f", help="Focus area: growth, revenue, market, technology"),
    api_url: str = typer.Option(DEFAULT_API_URL, "--api-url", help="API base URL"),
    limit: int = typer.Option(10, "--limit", "-l", help="Results per forecast query")
) -> None:
    """Generate business forecasts and future scenario analysis."""
    
    horizon_queries = {
        "short": ["quarterly outlook", "near-term trends", "immediate opportunities", "short-term goals"],
        "medium": ["annual planning", "yearly projections", "medium-term strategy", "12-month outlook"],
        "long": ["long-term vision", "strategic roadmap", "future scenarios", "multi-year planning"]
    }
    
    focus_queries = {
        "growth": ["growth projections", "expansion plans", "scaling strategy"],
        "revenue": ["revenue forecast", "income projections", "financial outlook"],  
        "market": ["market evolution", "industry trends", "customer shifts"],
        "technology": ["technology roadmap", "innovation pipeline", "digital transformation"]
    }
    
    console.print(f"\n[bold blue]🔮 Business Forecast: {horizon.upper()}-term {focus.upper()}[/bold blue]")
    
    # Combine horizon and focus queries
    queries = horizon_queries.get(horizon, []) + focus_queries.get(focus, [])
    
    forecast_data = {}
    
    for query in track(queries, description="Generating forecast..."):
        result = _make_search_request(query, limit, api_url)
        results = result.get("results", [])
        
        themes = _analyze_content_themes(results)
        metrics = _calculate_coverage_metrics(results)
        
        forecast_data[query] = {
            "themes": themes,
            "metrics": metrics,
            "confidence": min(1.0, len(results) / limit)  # Simple confidence score
        }
    
    # Display forecast summary
    forecast_table = Table(title=f"{horizon.title()}-term {focus.title()} Forecast")
    forecast_table.add_column("Forecast Area", style="cyan")
    forecast_table.add_column("Confidence", style="green")
    forecast_table.add_column("Key Indicators", style="yellow")
    
    for query, data in forecast_data.items():
        confidence = f"{data['confidence']:.1%}"
        indicators = ", ".join(list(data["themes"].keys())[:3])
        
        forecast_table.add_row(
            query.title(),
            confidence,
            indicators
        )
    
    console.print(forecast_table)
    
    # Show scenario analysis
    console.print(f"\n[bold]📋 Scenario Analysis for {focus.title()}:[/bold]")
    
    # Aggregate all themes for overall insights
    all_themes = Counter()
    for data in forecast_data.values():
        all_themes.update(data["themes"])
    
    top_themes = all_themes.most_common(5)
    for i, (theme, count) in enumerate(top_themes, 1):
        console.print(f"{i}. [cyan]{theme}[/cyan] - {count} mentions across forecasts")


if __name__ == "__main__":
    app()