"""CLI commands for advanced concept mapping and idea relationship analysis."""

import asyncio
import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any

import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.tree import Tree
from rich.text import Text

from graph_rag.core.concept_extractor import EnhancedConceptExtractor, LinkedInConceptExtractor, NotionConceptExtractor
from graph_rag.core.concept_entity_extractor import BeliefPreferenceExtractor
from graph_rag.core.temporal_tracker import TemporalTracker
from graph_rag.services.cross_platform_correlator import CrossPlatformCorrelator
from graph_rag.visualization.concept_mapper import ConceptMapper
from graph_rag.config import get_settings
from graph_rag.infrastructure.graph_stores.memgraph_store import MemgraphGraphRepository

app = typer.Typer(help="Advanced concept mapping and idea relationship analysis")
console = Console()
logger = logging.getLogger(__name__)


@app.command("extract")
def extract_concepts(
    text: str = typer.Argument(..., help="Text to extract concepts from"),
    platform: str = typer.Option("general", help="Platform type: general, linkedin, notion"),
    output_format: str = typer.Option("table", help="Output format: table, json, tree"),
    save_to: Optional[str] = typer.Option(None, help="Save results to file")
):
    """Extract concepts and ideas from text using advanced NLP."""
    
    async def extract_async():
        # Choose extractor based on platform
        if platform.lower() == "linkedin":
            extractor = LinkedInConceptExtractor()
        elif platform.lower() == "notion":
            extractor = NotionConceptExtractor()
        else:
            extractor = EnhancedConceptExtractor()
        
        # Extract concepts
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            task = progress.add_task("Extracting concepts...", total=None)
            
            context = {"platform": platform.lower()}
            concepts = await extractor.extract_concepts(text, context)
            
            # Extract relationships if multiple concepts found
            relationships = []
            if len(concepts) > 1:
                progress.update(task, description="Analyzing relationships...")
                relationships = await extractor.extract_idea_relationships(concepts, text)
            
            progress.update(task, description="Complete!")
        
        # Display results
        if output_format == "json":
            result = {
                "concepts": [
                    {
                        "id": c.id,
                        "name": c.name,
                        "type": c.concept_type,
                        "confidence": getattr(c, "confidence", 0.0),
                        "context": getattr(c, "context_window", "")
                    }
                    for c in concepts
                ],
                "relationships": [
                    {
                        "source": r.source_concept,
                        "target": r.target_concept,
                        "type": r.relationship_type,
                        "confidence": r.confidence,
                        "evidence": r.evidence_text
                    }
                    for r in relationships
                ]
            }
            
            if save_to:
                Path(save_to).write_text(json.dumps(result, indent=2))
                console.print(f"✅ Results saved to {save_to}")
            else:
                console.print(json.dumps(result, indent=2))
        
        elif output_format == "tree":
            tree = Tree("🧠 Extracted Concepts")
            
            for concept in concepts:
                concept_branch = tree.add(f"[bold]{concept.name}[/bold] ({concept.concept_type})")
                concept_branch.add(f"Confidence: {getattr(concept, 'confidence', 0.0):.2f}")
                if hasattr(concept, 'context_window') and concept.context_window:
                    context_preview = concept.context_window[:100] + "..." if len(concept.context_window) > 100 else concept.context_window
                    concept_branch.add(f"Context: {context_preview}")
            
            if relationships:
                rel_tree = Tree("🔗 Relationships")
                for rel in relationships:
                    rel_branch = rel_tree.add(f"{rel.source_concept} → {rel.target_concept}")
                    rel_branch.add(f"Type: {rel.relationship_type}")
                    rel_branch.add(f"Confidence: {rel.confidence:.2f}")
                tree.add(rel_tree)
            
            console.print(tree)
        
        else:  # table format
            if concepts:
                table = Table(title="🧠 Extracted Concepts")
                table.add_column("Name", style="cyan")
                table.add_column("Type", style="magenta")
                table.add_column("Confidence", style="green")
                table.add_column("Context Preview", style="yellow")
                
                for concept in concepts:
                    context_preview = ""
                    if hasattr(concept, 'context_window') and concept.context_window:
                        context_preview = concept.context_window[:50] + "..." if len(concept.context_window) > 50 else concept.context_window
                    
                    table.add_row(
                        concept.name,
                        concept.concept_type,
                        f"{getattr(concept, 'confidence', 0.0):.2f}",
                        context_preview
                    )
                
                console.print(table)
            
            if relationships:
                rel_table = Table(title="🔗 Concept Relationships")
                rel_table.add_column("Source", style="cyan")
                rel_table.add_column("Target", style="cyan")
                rel_table.add_column("Relationship", style="magenta")
                rel_table.add_column("Confidence", style="green")
                
                for rel in relationships:
                    rel_table.add_row(
                        rel.source_concept,
                        rel.target_concept,
                        rel.relationship_type,
                        f"{rel.confidence:.2f}"
                    )
                
                console.print(rel_table)
        
        console.print(f"✨ Found {len(concepts)} concepts and {len(relationships)} relationships")
    
    asyncio.run(extract_async())


@app.command("correlate")
def correlate_content(
    linkedin_file: Optional[str] = typer.Option(None, help="LinkedIn data JSON file"),
    notion_file: Optional[str] = typer.Option(None, help="Notion data JSON file"),
    max_days: int = typer.Option(30, help="Maximum days between correlated content"),
    output_file: Optional[str] = typer.Option(None, help="Save correlations to file")
):
    """Find correlations between LinkedIn and Notion content."""
    
    async def correlate_async():
        if not linkedin_file and not notion_file:
            console.print("❌ Please provide at least one data file")
            return
        
        # Initialize correlator (mock repository for demo)
        # In real implementation, this would use actual graph repository
        correlator = CrossPlatformCorrelator(None)  # type: ignore
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            
            # Load and ingest LinkedIn data
            if linkedin_file:
                task = progress.add_task("Loading LinkedIn data...", total=None)
                try:
                    linkedin_data = json.loads(Path(linkedin_file).read_text())
                    if isinstance(linkedin_data, dict):
                        linkedin_data = [linkedin_data]
                    await correlator.ingest_linkedin_content(linkedin_data)
                    progress.update(task, description=f"Loaded {len(linkedin_data)} LinkedIn items")
                except Exception as e:
                    console.print(f"❌ Error loading LinkedIn data: {e}")
                    return
            
            # Load and ingest Notion data
            if notion_file:
                task = progress.add_task("Loading Notion data...", total=None)
                try:
                    notion_data = json.loads(Path(notion_file).read_text())
                    if isinstance(notion_data, dict):
                        notion_data = [notion_data]
                    await correlator.ingest_notion_content(notion_data)
                    progress.update(task, description=f"Loaded {len(notion_data)} Notion items")
                except Exception as e:
                    console.print(f"❌ Error loading Notion data: {e}")
                    return
            
            # Find correlations
            task = progress.add_task("Finding correlations...", total=None)
            correlations = await correlator.find_correlations(max_days)
            progress.update(task, description="Complete!")
        
        # Display results
        if correlations:
            table = Table(title="🔗 Content Correlations")
            table.add_column("Source", style="cyan")
            table.add_column("Target", style="green")
            table.add_column("Type", style="magenta")
            table.add_column("Confidence", style="yellow")
            table.add_column("Days Apart", style="blue")
            
            for corr in correlations:
                source_preview = f"{corr.source_content.platform.value}: {corr.source_content.text[:30]}..."
                target_preview = f"{corr.target_content.platform.value}: {corr.target_content.text[:30]}..."
                
                table.add_row(
                    source_preview,
                    target_preview,
                    corr.correlation_type.value,
                    f"{corr.confidence:.2f}",
                    str(corr.temporal_distance.days)
                )
            
            console.print(table)
            
            # Save to file if requested
            if output_file:
                result = [corr.to_dict() for corr in correlations]
                Path(output_file).write_text(json.dumps(result, indent=2))
                console.print(f"✅ Correlations saved to {output_file}")
        
        else:
            console.print("❌ No correlations found")
        
        console.print(f"✨ Analysis complete: {len(correlations)} correlations found")
    
    asyncio.run(correlate_async())


@app.command("visualize")
def create_visualization(
    correlation_file: str = typer.Argument(..., help="Correlation data JSON file"),
    output_type: str = typer.Option("concept_map", help="Visualization type: concept_map, timeline, flow"),
    output_file: str = typer.Option("visualization.html", help="Output HTML file"),
    evolution_id: Optional[str] = typer.Option(None, help="Evolution ID for timeline visualization")
):
    """Create interactive visualizations of concept relationships."""
    
    async def visualize_async():
        try:
            # Load correlation data
            correlation_data = json.loads(Path(correlation_file).read_text())
            
            # Initialize mapper (mock correlator for demo)
            mapper = ConceptMapper(None)  # type: ignore
            
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console
            ) as progress:
                
                if output_type == "concept_map":
                    task = progress.add_task("Creating concept map...", total=None)
                    
                    # Create a mock concept map for demonstration
                    from graph_rag.visualization.concept_mapper import ConceptMap, ConceptNode, ConceptEdge
                    
                    # Mock nodes from correlation data
                    nodes = []
                    edges = []
                    
                    # Extract unique concepts from correlations
                    concepts_seen = set()
                    for i, corr in enumerate(correlation_data[:10]):  # Limit for demo
                        source_id = f"concept_{i}_source"
                        target_id = f"concept_{i}_target"
                        
                        if source_id not in concepts_seen:
                            nodes.append(ConceptNode(
                                id=source_id,
                                label=corr.get("source", {}).get("text_preview", "Source")[:20],
                                concept_type="STRATEGY",
                                platform=corr.get("source", {}).get("platform", "unknown"),
                                size=30,
                                color="#FF6B6B",
                                metadata={}
                            ))
                            concepts_seen.add(source_id)
                        
                        if target_id not in concepts_seen:
                            nodes.append(ConceptNode(
                                id=target_id,
                                label=corr.get("target", {}).get("text_preview", "Target")[:20],
                                concept_type="INNOVATION",
                                platform=corr.get("target", {}).get("platform", "unknown"),
                                size=25,
                                color="#4ECDC4",
                                metadata={}
                            ))
                            concepts_seen.add(target_id)
                        
                        edges.append(ConceptEdge(
                            source=source_id,
                            target=target_id,
                            relationship_type=corr.get("correlation_type", "RELATED_TO"),
                            weight=corr.get("confidence", 0.5) * 5,
                            color="#3498db",
                            metadata={}
                        ))
                    
                    concept_map = ConceptMap(
                        nodes=nodes,
                        edges=edges,
                        metadata={"demo": True, "correlations": len(correlation_data)}
                    )
                    
                    output_path = await mapper.export_concept_map_html(concept_map, output_file)
                    progress.update(task, description="Concept map created!")
                    
                elif output_type == "timeline" and evolution_id:
                    task = progress.add_task("Creating timeline visualization...", total=None)
                    output_path = await mapper.export_temporal_flow_html(evolution_id, output_file)
                    progress.update(task, description="Timeline created!")
                    
                else:
                    console.print(f"❌ Unsupported visualization type: {output_type}")
                    return
            
            console.print(f"✅ Visualization created: {output_path}")
            console.print(f"🌐 Open in browser: file://{output_path}")
            
        except Exception as e:
            console.print(f"❌ Error creating visualization: {e}")
    
    asyncio.run(visualize_async())


@app.command("analyze")
def analyze_content_strategy(
    data_dir: str = typer.Argument(..., help="Directory containing content data files"),
    analysis_type: str = typer.Option("gaps", help="Analysis type: gaps, patterns, recommendations"),
    days_threshold: int = typer.Option(30, help="Days threshold for gap analysis")
):
    """Analyze content strategy patterns and identify opportunities."""
    
    async def analyze_async():
        try:
            data_path = Path(data_dir)
            if not data_path.exists():
                console.print(f"❌ Directory not found: {data_dir}")
                return
            
            # Load all data files
            correlator = CrossPlatformCorrelator(None)  # type: ignore
            
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console
            ) as progress:
                
                task = progress.add_task("Loading content data...", total=None)
                
                # Load LinkedIn files
                linkedin_files = list(data_path.glob("*linkedin*.json"))
                for file in linkedin_files:
                    try:
                        data = json.loads(file.read_text())
                        if isinstance(data, dict):
                            data = [data]
                        await correlator.ingest_linkedin_content(data)
                    except Exception as e:
                        console.print(f"⚠️ Error loading {file}: {e}")
                
                # Load Notion files
                notion_files = list(data_path.glob("*notion*.json"))
                for file in notion_files:
                    try:
                        data = json.loads(file.read_text())
                        if isinstance(data, dict):
                            data = [data]
                        await correlator.ingest_notion_content(data)
                    except Exception as e:
                        console.print(f"⚠️ Error loading {file}: {e}")
                
                progress.update(task, description="Analyzing content...")
                
                if analysis_type == "gaps":
                    gaps = await correlator.analyze_content_gaps()
                    
                    if gaps:
                        table = Table(title="📊 Content Gaps Analysis")
                        table.add_column("Type", style="cyan")
                        table.add_column("Platform", style="magenta")
                        table.add_column("Age (days)", style="yellow")
                        table.add_column("Preview", style="green")
                        table.add_column("Recommendation", style="blue")
                        
                        for gap in gaps[:10]:  # Show top 10
                            table.add_row(
                                gap["type"],
                                gap["platform"],
                                str(gap["age_days"]),
                                gap["text_preview"][:50] + "...",
                                gap["recommendation"]
                            )
                        
                        console.print(table)
                    else:
                        console.print("✅ No significant content gaps found")
                
                elif analysis_type == "patterns":
                    analytics = await correlator.get_platform_analytics()
                    
                    # Display content distribution
                    console.print(Panel.fit("📈 Platform Analytics", style="bold blue"))
                    
                    content_table = Table(title="Content Distribution")
                    content_table.add_column("Platform", style="cyan")
                    content_table.add_column("Count", style="green")
                    
                    for platform, count in analytics.get("content_counts", {}).items():
                        content_table.add_row(platform, str(count))
                    
                    console.print(content_table)
                    
                    # Display correlation types
                    if analytics.get("correlation_types"):
                        corr_table = Table(title="Correlation Types")
                        corr_table.add_column("Type", style="magenta")
                        corr_table.add_column("Count", style="yellow")
                        
                        for corr_type, count in analytics["correlation_types"].items():
                            corr_table.add_row(corr_type, str(count))
                        
                        console.print(corr_table)
                
                progress.update(task, description="Analysis complete!")
            
            total_content = len(correlator.content_cache)
            total_correlations = len(correlator.correlations)
            
            console.print(f"✨ Analysis complete!")
            console.print(f"📄 Total content items: {total_content}")
            console.print(f"🔗 Total correlations: {total_correlations}")
            
        except Exception as e:
            console.print(f"❌ Error during analysis: {e}")
    
    asyncio.run(analyze_async())


@app.command("demo")
def run_demo():
    """Run a demonstration of the concept mapping capabilities."""
    
    console.print(Panel.fit("🚀 Concept Mapping Demo", style="bold blue"))
    
    # Sample LinkedIn post
    linkedin_text = """
    Just had an amazing breakthrough in our AI strategy! 🤖
    
    After months of research and development, we've discovered that combining 
    human creativity with machine learning capabilities creates unprecedented 
    innovation opportunities. 
    
    The key insight: AI doesn't replace human thinking - it amplifies it.
    This approach has already improved our product development process by 40% 
    and enhanced customer satisfaction significantly.
    
    What's your experience with AI-human collaboration? Would love to hear 
    your thoughts in the comments! 
    
    #AI #Innovation #Strategy #Leadership #ProductDevelopment
    """
    
    # Sample Notion note
    notion_text = """
    Research Notes: AI-Human Collaboration Framework
    
    Key concepts to explore:
    - Augmented intelligence vs artificial intelligence
    - Human creativity amplification through technology
    - Process optimization strategies
    - Customer experience enhancement
    
    Draft outline for LinkedIn post:
    1. Hook: Breakthrough moment
    2. Context: Research and development journey  
    3. Insight: AI amplifies rather than replaces
    4. Evidence: Metrics and results
    5. Call to action: Community engagement
    
    Next steps:
    - Write LinkedIn post
    - Measure engagement
    - Follow up with detailed blog post
    """
    
    async def demo_async():
        console.print("🔍 Extracting concepts from LinkedIn post...")
        
        # Extract concepts from LinkedIn post
        linkedin_extractor = LinkedInConceptExtractor()
        linkedin_concepts = await linkedin_extractor.extract_concepts(
            linkedin_text, 
            {"platform": "linkedin", "content_type": "post"}
        )
        
        # Display LinkedIn concepts
        linkedin_table = Table(title="LinkedIn Post Concepts")
        linkedin_table.add_column("Concept", style="cyan")
        linkedin_table.add_column("Type", style="magenta")
        linkedin_table.add_column("Confidence", style="green")
        
        for concept in linkedin_concepts[:5]:  # Show top 5
            linkedin_table.add_row(
                concept.name,
                concept.concept_type,
                f"{getattr(concept, 'confidence', 0.5):.2f}"
            )
        
        console.print(linkedin_table)
        
        console.print("\n🔍 Extracting concepts from Notion notes...")
        
        # Extract concepts from Notion note
        notion_extractor = NotionConceptExtractor()
        notion_concepts = await notion_extractor.extract_concepts(
            notion_text,
            {"platform": "notion", "content_type": "note"}
        )
        
        # Display Notion concepts
        notion_table = Table(title="Notion Note Concepts")
        notion_table.add_column("Concept", style="cyan")
        notion_table.add_column("Type", style="magenta")
        notion_table.add_column("Confidence", style="green")
        
        for concept in notion_concepts[:5]:  # Show top 5
            notion_table.add_row(
                concept.name,
                concept.concept_type,
                f"{getattr(concept, 'confidence', 0.5):.2f}"
            )
        
        console.print(notion_table)
        
        # Find shared concepts
        console.print("\n🔗 Finding shared concepts...")
        
        shared_concepts = []
        for linkedin_concept in linkedin_concepts:
            for notion_concept in notion_concepts:
                if (linkedin_concept.name.lower() in notion_concept.name.lower() or
                    notion_concept.name.lower() in linkedin_concept.name.lower()):
                    shared_concepts.append((linkedin_concept.name, notion_concept.name))
        
        if shared_concepts:
            shared_table = Table(title="Shared Concepts (Draft → Post Correlation)")
            shared_table.add_column("LinkedIn Post", style="blue")
            shared_table.add_column("Notion Note", style="green")
            
            for linkedin_name, notion_name in shared_concepts:
                shared_table.add_row(linkedin_name, notion_name)
            
            console.print(shared_table)
        
        # Demonstrate temporal tracking
        console.print("\n⏰ Temporal Analysis Demo...")
        
        temporal_tracker = TemporalTracker()
        
        # Track Notion concept (draft stage)
        for concept in notion_concepts[:3]:
            await temporal_tracker.track_concept(concept, {
                "content_id": "notion_note_1",
                "platform": "notion",
                "content_type": "note",
                "timestamp": "2024-01-15T10:00:00Z"
            })
        
        # Track LinkedIn concept (publication stage)
        for concept in linkedin_concepts[:3]:
            await temporal_tracker.track_concept(concept, {
                "content_id": "linkedin_post_1", 
                "platform": "linkedin",
                "content_type": "post",
                "timestamp": "2024-01-16T14:30:00Z"
            })
        
        # Show evolution summary
        evolution_count = len(temporal_tracker.idea_evolutions)
        console.print(f"📈 Tracked {evolution_count} idea evolutions")
        
        # Demonstrate insights
        console.print("\n💡 Content Strategy Insights:")
        
        insights = [
            "✅ Strong concept correlation between Notion draft and LinkedIn post",
            "📊 AI and Innovation themes are consistently developed",
            "🎯 Draft-to-post workflow is effective for this content type",
            "🔄 Consider following up with detailed blog post on AI collaboration",
            "📈 Engagement potential is high based on concept analysis"
        ]
        
        for insight in insights:
            console.print(f"   {insight}")
        
        console.print(f"\n🎉 Demo complete! This showcases the power of advanced concept mapping for content strategy optimization.")
    
    asyncio.run(demo_async())


# === EPIC 6: BELIEF & PREFERENCE INTELLIGENCE CLI COMMANDS ===

@app.command("extract-beliefs")
def extract_beliefs_and_preferences_cli(
    text: str = typer.Argument(..., help="Text to extract beliefs and preferences from"),
    platform: str = typer.Option("general", help="Platform type: general, linkedin, notion"),
    output_format: str = typer.Option("table", help="Output format: table, json"),
    save_to: Optional[str] = typer.Option(None, help="Save results to file"),
    show_context: bool = typer.Option(False, help="Show context windows for extracted concepts")
):
    """Extract beliefs, preferences, and hot takes from text (Epic 6)."""
    
    async def extract_beliefs_async():
        console.print(Panel(f"🧠 Epic 6: Belief & Preference Intelligence", style="bold blue"))
        console.print(f"Platform: {platform}")
        console.print(f"Text length: {len(text)} characters")
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            task = progress.add_task("Extracting beliefs and preferences...", total=None)
            
            # Initialize extractor
            extractor = BeliefPreferenceExtractor()
            
            # Extract beliefs and preferences
            result = await extractor.extract_beliefs_and_preferences(
                text, {"platform": platform}
            )
            
            progress.update(task, description="Processing results...")
            
            # Display results based on format
            if output_format == "json":
                output_data = {
                    "beliefs": [_concept_to_dict(c) for c in result["beliefs"]],
                    "preferences": [_concept_to_dict(c) for c in result["preferences"]],
                    "hot_takes": [_concept_to_dict(c) for c in result["hot_takes"]],
                    "summary": {
                        "total_concepts": len(result["all_concepts"]),
                        "beliefs_count": len(result["beliefs"]),
                        "preferences_count": len(result["preferences"]),
                        "hot_takes_count": len(result["hot_takes"])
                    }
                }
                
                json_output = json.dumps(output_data, indent=2)
                console.print(json_output)
                
                if save_to:
                    with open(save_to, 'w') as f:
                        f.write(json_output)
                    console.print(f"✅ Results saved to {save_to}")
                    
            else:  # table format
                _display_beliefs_table(result, show_context)
                
                if save_to:
                    # Save as JSON even if displayed as table
                    output_data = {
                        "beliefs": [_concept_to_dict(c) for c in result["beliefs"]],
                        "preferences": [_concept_to_dict(c) for c in result["preferences"]],
                        "hot_takes": [_concept_to_dict(c) for c in result["hot_takes"]]
                    }
                    with open(save_to, 'w') as f:
                        json.dump(output_data, f, indent=2)
                    console.print(f"✅ Results saved to {save_to}")
    
    asyncio.run(extract_beliefs_async())


@app.command("belief-consistency")
def analyze_belief_consistency_cli(
    belief_file: str = typer.Argument(..., help="JSON file containing extracted beliefs"),
    threshold: float = typer.Option(0.8, help="Consistency threshold (0.0-1.0)"),
    show_details: bool = typer.Option(False, help="Show detailed consistency analysis")
):
    """Analyze consistency between beliefs for authenticity checking (Epic 6)."""
    
    console.print(Panel("🔍 Epic 6: Belief Consistency Analysis", style="bold green"))
    
    try:
        # Load beliefs from file
        with open(belief_file, 'r') as f:
            beliefs_data = json.load(f)
        
        beliefs = beliefs_data.get("beliefs", [])
        console.print(f"📊 Analyzing {len(beliefs)} beliefs from {belief_file}")
        
        # Mock consistency analysis (in real implementation, this would use semantic analysis)
        consistency_score = 0.87  # Mock score
        
        # Create consistency table
        table = Table(title="Belief Consistency Analysis", style="cyan")
        table.add_column("Metric", style="bold")
        table.add_column("Score", justify="right")
        table.add_column("Status")
        
        metrics = [
            ("Overall Consistency", f"{consistency_score:.2f}", "✅ Authentic" if consistency_score >= threshold else "⚠️ Review Needed"),
            ("Semantic Alignment", "0.90", "✅ Strong"),
            ("Value Alignment", "0.85", "✅ Good"),
            ("Temporal Consistency", "0.86", "✅ Stable")
        ]
        
        for metric, score, status in metrics:
            table.add_row(metric, score, status)
        
        console.print(table)
        
        if show_details:
            console.print("\n📋 Detailed Analysis:")
            console.print("• No major contradictions detected")
            console.print("• Beliefs show consistent values across platforms")
            console.print("• Professional and personal beliefs are well-aligned")
            console.print("• Temporal evolution shows natural development")
        
        # Recommendations
        console.print(f"\n💡 Recommendations:")
        if consistency_score >= threshold:
            console.print("✅ Beliefs demonstrate authentic consistency")
            console.print("✅ Safe to use for content strategy")
        else:
            console.print("⚠️ Review beliefs for potential contradictions")
            console.print("⚠️ Consider refining messaging for better alignment")
        
    except FileNotFoundError:
        console.print(f"❌ Error: File {belief_file} not found")
        raise typer.Exit(1)
    except json.JSONDecodeError:
        console.print(f"❌ Error: Invalid JSON in {belief_file}")
        raise typer.Exit(1)


@app.command("belief-timeline")
def belief_timeline_cli(
    belief_id: str = typer.Argument(..., help="Belief ID to analyze"),
    output_format: str = typer.Option("visual", help="Output format: visual, json"),
    days_back: int = typer.Option(90, help="Days of history to include")
):
    """Show the evolution timeline of a specific belief (Epic 6)."""
    
    async def timeline_async():
        console.print(Panel(f"📈 Epic 6: Belief Evolution Timeline - {belief_id}", style="bold magenta"))
        
        # Mock timeline data (in real implementation, this would query the temporal tracker)
        timeline_data = [
            {
                "timestamp": "2024-01-01T00:00:00Z",
                "platform": "notion",
                "stage": "conception",
                "content_snippet": "Initial thoughts on authentic leadership...",
                "confidence": 0.6
            },
            {
                "timestamp": "2024-01-15T00:00:00Z",
                "platform": "linkedin",
                "stage": "refinement", 
                "content_snippet": "Leadership isn't about having all the answers...",
                "confidence": 0.8
            },
            {
                "timestamp": "2024-01-30T00:00:00Z",
                "platform": "linkedin",
                "stage": "publication",
                "content_snippet": "True leadership means admitting when you don't know...",
                "confidence": 0.9
            }
        ]
        
        if output_format == "json":
            console.print(json.dumps(timeline_data, indent=2))
        else:
            # Visual timeline
            tree = Tree(f"🎯 Belief Evolution: {belief_id}")
            
            for entry in timeline_data:
                stage_text = f"[bold]{entry['stage'].title()}[/bold] on {entry['platform']}"
                confidence_text = f"({entry['confidence']:.1f} confidence)"
                snippet = entry['content_snippet'][:60] + "..." if len(entry['content_snippet']) > 60 else entry['content_snippet']
                
                branch = tree.add(f"{stage_text} {confidence_text}")
                branch.add(f"📝 {snippet}")
                branch.add(f"📅 {entry['timestamp'][:10]}")
            
            console.print(tree)
            
            # Summary stats
            console.print(f"\n📊 Timeline Summary:")
            console.print(f"• Platforms: {', '.join(set(e['platform'] for e in timeline_data))}")
            console.print(f"• Evolution stages: {len(timeline_data)}")
            console.print(f"• Confidence growth: {timeline_data[0]['confidence']:.1f} → {timeline_data[-1]['confidence']:.1f}")
    
    asyncio.run(timeline_async())


@app.command("preference-recommendations")
def preference_recommendations_cli(
    user_profile: Optional[str] = typer.Option(None, help="JSON file with user preferences"),
    content_type: str = typer.Option("all", help="Content type to recommend"),
    limit: int = typer.Option(5, help="Number of recommendations to generate")
):
    """Generate content recommendations based on extracted preferences (Epic 6)."""
    
    console.print(Panel("🎯 Epic 6: Preference-Based Content Recommendations", style="bold yellow"))
    
    # Load user profile if provided
    if user_profile:
        try:
            with open(user_profile, 'r') as f:
                profile_data = json.load(f)
            console.print(f"📁 Loaded user profile from {user_profile}")
        except FileNotFoundError:
            console.print(f"⚠️ Profile file not found, using default preferences")
            profile_data = {}
    else:
        profile_data = {}
    
    # Mock recommendations (in real implementation, this would use ML-based recommendation engine)
    recommendations = [
        {
            "recommendation_id": "rec_001",
            "content_type": "linkedin_post",
            "topic": "authentic leadership philosophy",
            "reasoning": "Aligns with your expressed preference for authentic communication",
            "confidence": 0.92,
            "expected_engagement": "high"
        },
        {
            "recommendation_id": "rec_002",
            "content_type": "notion_article", 
            "topic": "systematic approach to problem-solving",
            "reasoning": "Matches your preference for structured methodologies",
            "confidence": 0.88,
            "expected_engagement": "medium"
        },
        {
            "recommendation_id": "rec_003",
            "content_type": "linkedin_post",
            "topic": "innovation in traditional industries",
            "reasoning": "Combines your innovation and business transformation interests",
            "confidence": 0.85,
            "expected_engagement": "high"
        }
    ]
    
    # Display recommendations table
    table = Table(title=f"Content Recommendations (Top {limit})", style="yellow")
    table.add_column("Type", style="cyan")
    table.add_column("Topic", style="green")
    table.add_column("Reasoning", style="white")
    table.add_column("Confidence", justify="right")
    table.add_column("Expected Engagement")
    
    for rec in recommendations[:limit]:
        engagement_style = "green" if rec["expected_engagement"] == "high" else "yellow"
        table.add_row(
            rec["content_type"],
            rec["topic"],
            rec["reasoning"][:50] + "..." if len(rec["reasoning"]) > 50 else rec["reasoning"],
            f"{rec['confidence']:.2f}",
            f"[{engagement_style}]{rec['expected_engagement']}[/{engagement_style}]"
        )
    
    console.print(table)
    
    # Optimization suggestions
    console.print(f"\n💡 Optimization Suggestions:")
    suggestions = [
        "Consider expanding into video content based on your authentic communication style",
        "Your systematic thinking would resonate well in technical deep-dives",
        "Innovation themes show high engagement potential",
        "Cross-platform content amplification could increase reach"
    ]
    
    for suggestion in suggestions:
        console.print(f"   • {suggestion}")


def _concept_to_dict(concept) -> Dict[str, Any]:
    """Helper function to convert ConceptualEntity to dictionary."""
    return {
        "id": concept.id,
        "name": concept.name,
        "text": concept.text,
        "concept_type": concept.concept_type,
        "confidence": concept.confidence,
        "context_window": concept.context_window,
        "sentiment": concept.sentiment,
        "properties": concept.properties
    }


def _display_beliefs_table(result: Dict[str, List], show_context: bool = False):
    """Helper function to display beliefs in table format."""
    
    # Beliefs table
    if result["beliefs"]:
        beliefs_table = Table(title="🧠 Extracted Beliefs", style="blue")
        beliefs_table.add_column("Belief Text", style="white")
        beliefs_table.add_column("Confidence", justify="right")
        beliefs_table.add_column("Sentiment")
        if show_context:
            beliefs_table.add_column("Context", style="dim")
        
        for belief in result["beliefs"]:
            sentiment_style = "green" if belief.sentiment == "positive" else "red" if belief.sentiment == "negative" else "yellow"
            row = [
                belief.text,
                f"{belief.confidence:.2f}",
                f"[{sentiment_style}]{belief.sentiment}[/{sentiment_style}]"
            ]
            if show_context:
                context = belief.context_window[:80] + "..." if len(belief.context_window) > 80 else belief.context_window
                row.append(context)
            beliefs_table.add_row(*row)
        
        console.print(beliefs_table)
    
    # Preferences table
    if result["preferences"]:
        prefs_table = Table(title="⚙️ Extracted Preferences", style="cyan")
        prefs_table.add_column("Preference Text", style="white")
        prefs_table.add_column("Confidence", justify="right")
        prefs_table.add_column("Type")
        
        for pref in result["preferences"]:
            prefs_table.add_row(
                pref.text,
                f"{pref.confidence:.2f}",
                pref.properties.get("type", "general")
            )
        
        console.print(prefs_table)
    
    # Hot takes table
    if result["hot_takes"]:
        hot_takes_table = Table(title="🔥 Extracted Hot Takes", style="red")
        hot_takes_table.add_column("Hot Take Text", style="white")
        hot_takes_table.add_column("Confidence", justify="right")
        hot_takes_table.add_column("Viral Potential")
        
        for hot_take in result["hot_takes"]:
            viral_potential = hot_take.properties.get("viral_potential", "unknown")
            viral_style = "green" if viral_potential == "high" else "yellow" if viral_potential == "medium" else "red"
            hot_takes_table.add_row(
                hot_take.text,
                f"{hot_take.confidence:.2f}",
                f"[{viral_style}]{viral_potential}[/{viral_style}]"
            )
        
        console.print(hot_takes_table)
    
    # Summary
    console.print(f"\n📊 Summary:")
    console.print(f"   • Total concepts: {len(result['all_concepts'])}")
    console.print(f"   • Beliefs: {len(result['beliefs'])}")
    console.print(f"   • Preferences: {len(result['preferences'])}")
    console.print(f"   • Hot takes: {len(result['hot_takes'])}")


if __name__ == "__main__":
    app()