"""CLI command for experiment consolidation and deduplication."""

import asyncio
import json
from datetime import datetime
from pathlib import Path

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from graph_rag.core.consolidation import SimilarityThreshold
from graph_rag.services.experiment_consolidator import SynapseExperimentConsolidator

console = Console()
app = typer.Typer(
    name="consolidate",
    help="Consolidate and deduplicate overlapping experimental documents.",
    add_completion=False,
)


@app.command("discover")
def discover_candidates(
    search_path: str = typer.Argument(
        help="Directory path to search for experimental documents"
    ),
    patterns: list[str] | None = typer.Option(
        ["*.md", "*.txt"],
        "--pattern",
        "-p",
        help="File patterns to match (can be specified multiple times)"
    ),
    output_format: str = typer.Option(
        "table",
        "--format",
        "-f",
        help="Output format: 'table', 'json', or 'summary'"
    ),
    output_file: str | None = typer.Option(
        None,
        "--output",
        "-o",
        help="Save results to file"
    ),
):
    """Discover experimental documents that are candidates for consolidation."""
    async def _discover():
        consolidator = SynapseExperimentConsolidator()

        with console.status(f"[bold green]Discovering candidates in {search_path}..."):
            candidates = await consolidator.discover_candidates(search_path, patterns)

        if not candidates:
            console.print(f"[red]No candidates found in {search_path}")
            return

        console.print(f"[green]Found {len(candidates)} consolidation candidates")

        if output_format == "json":
            _output_candidates_json(candidates, output_file)
        elif output_format == "summary":
            _output_candidates_summary(candidates, output_file)
        else:
            _output_candidates_table(candidates, output_file)

    asyncio.run(_discover())


@app.command("analyze")
def analyze_similarity(
    search_path: str = typer.Argument(
        help="Directory path to search for experimental documents"
    ),
    threshold: float = typer.Option(
        SimilarityThreshold.HIGH_SIMILARITY.value,
        "--threshold",
        "-t",
        help="Similarity threshold for matching (0.0-1.0)"
    ),
    patterns: list[str] | None = typer.Option(
        ["*.md", "*.txt"],
        "--pattern",
        "-p",
        help="File patterns to match"
    ),
    show_matches: bool = typer.Option(
        True,
        "--show-matches/--no-matches",
        help="Show detailed similarity matches"
    ),
    output_file: str | None = typer.Option(
        None,
        "--output",
        "-o",
        help="Save results to file"
    ),
):
    """Analyze similarity between experimental documents."""
    async def _analyze():
        consolidator = SynapseExperimentConsolidator()

        with console.status(f"[bold green]Analyzing similarity in {search_path}..."):
            # Discover candidates
            candidates = await consolidator.discover_candidates(search_path, patterns)

            if not candidates:
                console.print(f"[red]No candidates found in {search_path}")
                return

            # Find similar documents
            similarity_matches = await consolidator.find_similar_documents(
                candidates, threshold
            )

        console.print(f"[green]Analyzed {len(candidates)} candidates")
        console.print(f"[blue]Found {len(similarity_matches)} similarity matches above {threshold:.1%}")

        if show_matches and similarity_matches:
            _display_similarity_matches(similarity_matches)

        if output_file:
            _save_similarity_analysis(candidates, similarity_matches, output_file)

    asyncio.run(_analyze())


@app.command("consolidate")
def consolidate_experiments(
    search_path: str = typer.Argument(
        help="Directory path to search for experimental documents"
    ),
    threshold: float = typer.Option(
        SimilarityThreshold.HIGH_SIMILARITY.value,
        "--threshold",
        "-t",
        help="Similarity threshold for consolidation (0.0-1.0)"
    ),
    patterns: list[str] | None = typer.Option(
        ["*.md", "*.txt"],
        "--pattern",
        "-p",
        help="File patterns to match"
    ),
    output_dir: str | None = typer.Option(
        None,
        "--output-dir",
        "-o",
        help="Directory to save consolidation results"
    ),
    format_output: str = typer.Option(
        "markdown",
        "--format",
        "-f",
        help="Output format: 'markdown', 'json', or 'report'"
    ),
):
    """Run full consolidation process on experimental documents."""
    async def _consolidate():
        consolidator = SynapseExperimentConsolidator()

        with console.status("[bold green]Running consolidation analysis..."):
            report = await consolidator.run_full_consolidation(
                search_path, threshold, patterns
            )

        # Display summary
        _display_consolidation_summary(report)

        # Save detailed results
        if output_dir:
            _save_consolidation_results(report, output_dir, format_output)
        else:
            _display_consolidation_details(report)

    asyncio.run(_consolidate())


@app.command("extract-metrics")
def extract_metrics(
    search_path: str = typer.Argument(
        help="Directory path to search for experimental documents"
    ),
    patterns: list[str] | None = typer.Option(
        ["*.md", "*.txt"],
        "--pattern",
        "-p",
        help="File patterns to match"
    ),
    metric_types: list[str] | None = typer.Option(
        None,
        "--type",
        help="Filter by metric types: performance, percentage, throughput, cost, time, engagement"
    ),
    min_confidence: float = typer.Option(
        0.5,
        "--min-confidence",
        help="Minimum confidence score for metrics (0.0-1.0)"
    ),
    output_file: str | None = typer.Option(
        None,
        "--output",
        "-o",
        help="Save metrics to file"
    ),
):
    """Extract and analyze success metrics from experimental documents."""
    async def _extract():
        consolidator = SynapseExperimentConsolidator()

        with console.status(f"[bold green]Extracting metrics from {search_path}..."):
            candidates = await consolidator.discover_candidates(search_path, patterns)

        if not candidates:
            console.print(f"[red]No candidates found in {search_path}")
            return

        # Collect all metrics
        all_metrics = []
        for candidate in candidates:
            all_metrics.extend(candidate.extracted_metrics)

        # Filter by confidence and type
        filtered_metrics = [
            m for m in all_metrics
            if m.confidence_score >= min_confidence
        ]

        if metric_types:
            type_filter = set(metric_types)
            filtered_metrics = [
                m for m in filtered_metrics
                if m.metric_type.value in type_filter
            ]

        console.print(f"[green]Extracted {len(filtered_metrics)} metrics from {len(candidates)} documents")

        if filtered_metrics:
            _display_metrics_table(filtered_metrics)

        if output_file:
            _save_metrics_to_file(filtered_metrics, output_file)

    asyncio.run(_extract())


def _output_candidates_table(candidates, output_file=None):
    """Display candidates in a rich table format."""
    table = Table(title="Consolidation Candidates")
    table.add_column("File", style="cyan")
    table.add_column("Title", style="magenta")
    table.add_column("Type", style="green")
    table.add_column("Metrics", justify="right", style="blue")
    table.add_column("Patterns", justify="right", style="yellow")

    for candidate in candidates:
        table.add_row(
            Path(candidate.file_path).name,
            candidate.title[:50] + "..." if len(candidate.title) > 50 else candidate.title,
            candidate.content_type,
            str(len(candidate.extracted_metrics)),
            str(len(candidate.architectural_patterns)),
        )

    console.print(table)


def _output_candidates_json(candidates, output_file=None):
    """Output candidates in JSON format."""
    data = [
        {
            "file_path": candidate.file_path,
            "title": candidate.title,
            "content_type": candidate.content_type,
            "metrics_count": len(candidate.extracted_metrics),
            "patterns_count": len(candidate.architectural_patterns),
            "content_hash": candidate.content_hash,
        }
        for candidate in candidates
    ]

    if output_file:
        with open(output_file, 'w') as f:
            json.dump(data, f, indent=2)
        console.print(f"[green]Candidates saved to {output_file}")
    else:
        console.print_json(data=data)


def _output_candidates_summary(candidates, output_file=None):
    """Output candidates summary."""
    summary = {
        "total_candidates": len(candidates),
        "content_types": {},
        "total_metrics": 0,
        "total_patterns": 0,
    }

    for candidate in candidates:
        # Count by content type
        content_type = candidate.content_type
        summary["content_types"][content_type] = summary["content_types"].get(content_type, 0) + 1

        # Count metrics and patterns
        summary["total_metrics"] += len(candidate.extracted_metrics)
        summary["total_patterns"] += len(candidate.architectural_patterns)

    if output_file:
        with open(output_file, 'w') as f:
            json.dump(summary, f, indent=2)
        console.print(f"[green]Summary saved to {output_file}")
    else:
        console.print_json(data=summary)


def _display_similarity_matches(similarity_matches):
    """Display similarity matches in a table."""
    table = Table(title="Similarity Matches")
    table.add_column("Document A", style="cyan")
    table.add_column("Document B", style="magenta")
    table.add_column("Similarity", justify="right", style="green")
    table.add_column("Overlap %", justify="right", style="blue")

    for match in similarity_matches:
        table.add_row(
            Path(match.candidate_a.file_path).name,
            Path(match.candidate_b.file_path).name,
            f"{match.similarity_score:.1%}",
            f"{match.overlap_percentage:.1%}",
        )

    console.print(table)


def _display_consolidation_summary(report):
    """Display consolidation summary."""
    summary_panel = Panel(
        f"""[bold green]Consolidation Complete[/bold green]

📊 [blue]Analysis Summary:[/blue]
   • Candidates Analyzed: {report.total_candidates_analyzed}
   • Similarity Matches: {report.similarity_matches_found}
   • Experiments Consolidated: {len(report.experiments_consolidated)}

🎯 [blue]Key Findings:[/blue]
   • High-Value Patterns: {len(report.high_value_patterns)}
   • Top Performing Metrics: {len(report.top_performing_metrics)}
   • Average Evidence Score: {report.processing_summary.get('average_evidence_score', 0):.1%}

💡 [blue]Recommendations:[/blue]
   • {len(report.recommendations)} actionable insights generated
        """,
        title="Consolidation Report",
        border_style="bright_green",
    )
    console.print(summary_panel)


def _display_consolidation_details(report):
    """Display detailed consolidation results."""
    if report.experiments_consolidated:
        console.print("\n[bold blue]Consolidated Experiments:[/bold blue]")

        for i, experiment in enumerate(report.experiments_consolidated[:5], 1):
            panel = Panel(
                f"""[bold]{experiment.title}[/bold]

[blue]Summary:[/blue] {experiment.summary}

[blue]Sources:[/blue] {len(experiment.source_candidates)} documents
[blue]Metrics:[/blue] {len(experiment.proven_metrics)} proven metrics
[blue]Patterns:[/blue] {len(experiment.architectural_patterns)} architectural patterns
[blue]Evidence Score:[/blue] {experiment.evidence_ranking:.1%}

[blue]Top Recommendations:[/blue]
{chr(10).join(f"• {rec}" for rec in experiment.recommendations[:3])}
                """,
                title=f"Experiment #{i}",
                border_style="blue",
            )
            console.print(panel)

    if report.top_performing_metrics:
        console.print("\n[bold blue]Top Performing Metrics:[/bold blue]")
        _display_metrics_table(report.top_performing_metrics[:10])


def _display_metrics_table(metrics):
    """Display metrics in a table format."""
    table = Table(title="Success Metrics")
    table.add_column("Type", style="cyan")
    table.add_column("Value", justify="right", style="magenta")
    table.add_column("Unit", style="green")
    table.add_column("Confidence", justify="right", style="blue")
    table.add_column("Context", style="yellow")

    for metric in metrics:
        table.add_row(
            metric.metric_type.value.replace('_', ' ').title(),
            f"{metric.value:,.2f}",
            metric.unit,
            f"{metric.confidence_score:.1%}",
            metric.context[:60] + "..." if len(metric.context) > 60 else metric.context,
        )

    console.print(table)


def _save_consolidation_results(report, output_dir, format_output):
    """Save consolidation results to files."""
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    if format_output == "json":
        # Save as JSON
        report_file = output_path / "consolidation_report.json"
        with open(report_file, 'w') as f:
            json.dump(report.dict(), f, indent=2, default=str)
        console.print(f"[green]Report saved to {report_file}")

    elif format_output == "markdown":
        # Save as Markdown
        report_file = output_path / "consolidation_report.md"
        markdown_content = _generate_markdown_report(report)
        with open(report_file, 'w') as f:
            f.write(markdown_content)
        console.print(f"[green]Report saved to {report_file}")

    else:  # report format
        # Save multiple files
        _save_detailed_report_files(report, output_path)


def _generate_markdown_report(report):
    """Generate a markdown consolidation report."""
    markdown = f"""# Experiment Consolidation Report

Generated: {report.generated_at.strftime('%Y-%m-%d %H:%M:%S')}

## Summary

- **Candidates Analyzed**: {report.total_candidates_analyzed}
- **Similarity Matches Found**: {report.similarity_matches_found}
- **Experiments Consolidated**: {len(report.experiments_consolidated)}
- **High-Value Patterns Identified**: {len(report.high_value_patterns)}
- **Top Performing Metrics**: {len(report.top_performing_metrics)}

## Consolidated Experiments

"""

    for i, experiment in enumerate(report.experiments_consolidated, 1):
        markdown += f"""### {i}. {experiment.title}

**Summary**: {experiment.summary}

**Evidence Ranking**: {experiment.evidence_ranking:.1%}

**Source Documents**: {len(experiment.source_candidates)}
{chr(10).join(f"- {Path(candidate.file_path).name}" for candidate in experiment.source_candidates)}

**Proven Metrics**: {len(experiment.proven_metrics)}
{chr(10).join(f"- {metric.metric_type.value}: {metric.value} {metric.unit} (confidence: {metric.confidence_score:.1%})" for metric in experiment.proven_metrics[:5])}

**Architectural Patterns**: {len(experiment.architectural_patterns)}
{chr(10).join(f"- {pattern.pattern_name} (evidence: {pattern.evidence_strength:.1%})" for pattern in experiment.architectural_patterns)}

**Recommendations**:
{chr(10).join(f"- {rec}" for rec in experiment.recommendations)}

---

"""

    # Add top patterns section
    if report.high_value_patterns:
        markdown += """## High-Value Architectural Patterns

"""
        for pattern in report.high_value_patterns[:10]:
            markdown += f"""### {pattern.pattern_name}

**Evidence Strength**: {pattern.evidence_strength:.1%}

**Description**: {pattern.description}

**Benefits**:
{chr(10).join(f"- {benefit}" for benefit in pattern.benefits)}

**Challenges**:
{chr(10).join(f"- {challenge}" for challenge in pattern.challenges)}

**Use Cases**:
{chr(10).join(f"- {use_case}" for use_case in pattern.use_cases)}

---

"""

    # Add recommendations section
    markdown += """## Overall Recommendations

"""
    for rec in report.recommendations:
        markdown += f"- {rec}\n"

    return markdown


def _save_detailed_report_files(report, output_path):
    """Save detailed report files in multiple formats."""
    # Main report JSON
    report_file = output_path / "consolidation_report.json"
    with open(report_file, 'w') as f:
        json.dump(report.dict(), f, indent=2, default=str)

    # Consolidated experiments
    experiments_file = output_path / "consolidated_experiments.json"
    experiments_data = [exp.dict() for exp in report.experiments_consolidated]
    with open(experiments_file, 'w') as f:
        json.dump(experiments_data, f, indent=2, default=str)

    # High-value patterns
    patterns_file = output_path / "high_value_patterns.json"
    patterns_data = [pattern.dict() for pattern in report.high_value_patterns]
    with open(patterns_file, 'w') as f:
        json.dump(patterns_data, f, indent=2, default=str)

    # Top metrics
    metrics_file = output_path / "top_performing_metrics.json"
    metrics_data = [metric.dict() for metric in report.top_performing_metrics]
    with open(metrics_file, 'w') as f:
        json.dump(metrics_data, f, indent=2, default=str)

    # Markdown summary
    markdown_file = output_path / "consolidation_summary.md"
    with open(markdown_file, 'w') as f:
        f.write(_generate_markdown_report(report))

    console.print(f"[green]Detailed reports saved to {output_path}")
    console.print(f"[blue]Files created: {len(list(output_path.glob('*')))} files")


def _save_similarity_analysis(candidates, similarity_matches, output_file):
    """Save similarity analysis results."""
    data = {
        "analysis_summary": {
            "total_candidates": len(candidates),
            "similarity_matches": len(similarity_matches),
            "analysis_timestamp": datetime.now().isoformat(),
        },
        "candidates": [
            {
                "file_path": candidate.file_path,
                "title": candidate.title,
                "content_type": candidate.content_type,
                "content_hash": candidate.content_hash,
            }
            for candidate in candidates
        ],
        "similarity_matches": [
            {
                "candidate_a": Path(match.candidate_a.file_path).name,
                "candidate_b": Path(match.candidate_b.file_path).name,
                "similarity_score": match.similarity_score,
                "overlap_percentage": match.overlap_percentage,
                "matching_sections_count": len(match.matching_sections),
            }
            for match in similarity_matches
        ],
    }

    with open(output_file, 'w') as f:
        json.dump(data, f, indent=2, default=str)

    console.print(f"[green]Similarity analysis saved to {output_file}")


def _save_metrics_to_file(metrics, output_file):
    """Save metrics to a file."""
    data = [
        {
            "metric_type": metric.metric_type.value,
            "value": metric.value,
            "unit": metric.unit,
            "confidence_score": metric.confidence_score,
            "context": metric.context,
            "source_location": metric.source_location,
        }
        for metric in metrics
    ]

    if output_file.endswith('.json'):
        with open(output_file, 'w') as f:
            json.dump(data, f, indent=2)
    else:
        # Save as CSV
        import csv
        with open(output_file, 'w', newline='') as f:
            if data:
                writer = csv.DictWriter(f, fieldnames=data[0].keys())
                writer.writeheader()
                writer.writerows(data)

    console.print(f"[green]Metrics saved to {output_file}")


if __name__ == "__main__":
    app()
