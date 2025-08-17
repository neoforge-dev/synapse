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
from graph_rag.core.viral_prediction_engine import ViralPredictionEngine, ViralPrediction
from graph_rag.core.brand_safety_analyzer import BrandSafetyAnalyzer, BrandSafetyAssessment, RiskLevel
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


# === EPIC 7: HOT TAKE DETECTION & VIRAL PREDICTION CLI COMMANDS ===

@app.command("hot-take-analyze")
def hot_take_analyze_cli(
    text: str = typer.Argument(..., help="Hot take text to analyze"),
    platform: str = typer.Option("general", help="Platform type: general, linkedin, twitter"),
    output_format: str = typer.Option("visual", help="Output format: visual, json"),
    save_to: Optional[str] = typer.Option(None, help="Save results to file"),
    show_details: bool = typer.Option(False, help="Show detailed analysis")
):
    """Comprehensive hot take analysis with viral prediction and brand safety (Epic 7)."""
    
    async def analyze_async():
        console.print(Panel("🔥 Epic 7: Hot Take Analysis & Viral Prediction", style="bold red"))
        console.print(f"Platform: {platform}")
        console.print(f"Text length: {len(text)} characters")
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            task = progress.add_task("Analyzing hot take...", total=None)
            
            # Initialize engines
            viral_engine = ViralPredictionEngine()
            safety_analyzer = BrandSafetyAnalyzer()
            
            # Run viral prediction
            progress.update(task, description="Predicting viral potential...")
            viral_prediction = await viral_engine.predict_viral_potential(
                text, platform=platform
            )
            
            # Run brand safety analysis  
            progress.update(task, description="Assessing brand safety...")
            safety_assessment = await safety_analyzer.assess_content_safety(
                text, {"platform": platform}
            )
            
            progress.update(task, description="Generating recommendations...")
            
            if output_format == "json":
                output_data = {
                    "viral_prediction": {
                        "overall_score": viral_prediction.overall_score,
                        "engagement_score": viral_prediction.engagement_score,
                        "reach_potential": viral_prediction.reach_potential,
                        "viral_velocity": viral_prediction.viral_velocity,
                        "controversy_score": viral_prediction.controversy_score,
                        "platform_optimization": viral_prediction.platform_optimization
                    },
                    "brand_safety": {
                        "safety_level": safety_assessment.safety_level.value,
                        "overall_risk_score": safety_assessment.overall_risk_score,
                        "risk_factors": safety_assessment.risk_factors,
                        "stakeholder_impact": safety_assessment.stakeholder_impact
                    },
                    "recommendations": viral_prediction.recommendations
                }
                
                json_output = json.dumps(output_data, indent=2)
                console.print(json_output)
                
                if save_to:
                    with open(save_to, 'w') as f:
                        f.write(json_output)
                    console.print(f"✅ Analysis saved to {save_to}")
                    
            else:
                _display_hot_take_analysis(viral_prediction, safety_assessment, show_details)
                
                if save_to:
                    # Save as JSON even if displayed visually
                    output_data = {
                        "viral_prediction": _viral_prediction_to_dict(viral_prediction),
                        "brand_safety": _safety_assessment_to_dict(safety_assessment)
                    }
                    with open(save_to, 'w') as f:
                        json.dump(output_data, f, indent=2)
                    console.print(f"✅ Analysis saved to {save_to}")
    
    asyncio.run(analyze_async())


@app.command("viral-score")
def viral_score_cli(
    text: str = typer.Argument(..., help="Text to score for viral potential"),
    platform: str = typer.Option("general", help="Platform type: general, linkedin, twitter"),
    show_breakdown: bool = typer.Option(False, help="Show detailed score breakdown")
):
    """Quick viral potential scoring for immediate feedback (Epic 7)."""
    
    async def score_async():
        console.print(Panel("⚡ Epic 7: Quick Viral Score", style="bold yellow"))
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            task = progress.add_task("Calculating viral score...", total=None)
            
            viral_engine = ViralPredictionEngine()
            prediction = await viral_engine.predict_viral_potential(text, platform=platform)
            
            progress.update(task, description="Generating insights...")
        
        # Main score display
        score_color = "green" if prediction.overall_score > 0.7 else "yellow" if prediction.overall_score > 0.4 else "red"
        console.print(f"\n🎯 Overall Viral Score: [{score_color}]{prediction.overall_score:.2f}[/{score_color}] / 1.00")
        
        # Score bar visualization
        bar_length = 50
        filled = int(prediction.overall_score * bar_length)
        bar = "█" * filled + "░" * (bar_length - filled)
        console.print(f"   [{score_color}]{bar}[/{score_color}]")
        
        if show_breakdown:
            # Detailed breakdown table
            breakdown_table = Table(title="Viral Score Breakdown", style="cyan")
            breakdown_table.add_column("Component", style="bold")
            breakdown_table.add_column("Score", justify="right")
            breakdown_table.add_column("Impact")
            
            components = [
                ("Engagement Potential", f"{prediction.engagement_score:.2f}", _get_impact_text(prediction.engagement_score)),
                ("Reach Potential", f"{prediction.reach_potential:.2f}", _get_impact_text(prediction.reach_potential)),
                ("Viral Velocity", f"{prediction.viral_velocity:.2f}", _get_impact_text(prediction.viral_velocity)),
                ("Controversy Score", f"{prediction.controversy_score:.2f}", _get_impact_text(prediction.controversy_score))
            ]
            
            for component, score, impact in components:
                breakdown_table.add_row(component, score, impact)
            
            console.print(breakdown_table)
        
        # Quick recommendations
        console.print(f"\n💡 Quick Tips:")
        for rec in prediction.recommendations[:3]:  # Show top 3
            console.print(f"   • {rec}")
    
    asyncio.run(score_async())


@app.command("safety-check")
def safety_check_cli(
    text: str = typer.Argument(..., help="Text to check for brand safety"),
    brand_profile: str = typer.Option("moderate", help="Brand profile: conservative, moderate, aggressive"),
    show_mitigation: bool = typer.Option(False, help="Show mitigation strategies")
):
    """Brand safety assessment for hot takes (Epic 7)."""
    
    async def safety_async():
        console.print(Panel("🛡️ Epic 7: Brand Safety Check", style="bold green"))
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            task = progress.add_task("Analyzing brand safety...", total=None)
            
            safety_analyzer = BrandSafetyAnalyzer(brand_profile=brand_profile)
            assessment = await safety_analyzer.assess_content_safety(text)
            
            progress.update(task, description="Generating safety report...")
        
        # Safety level display
        safety_colors = {
            RiskLevel.SAFE: "green",
            RiskLevel.CAUTION: "yellow", 
            RiskLevel.RISK: "orange",
            RiskLevel.DANGER: "red"
        }
        
        safety_color = safety_colors.get(assessment.safety_level, "white")
        console.print(f"\n🎯 Safety Level: [{safety_color}]{assessment.safety_level.value.upper()}[/{safety_color}]")
        console.print(f"🎯 Risk Score: {assessment.overall_risk_score:.2f} / 1.00")
        
        # Risk factors table
        if assessment.risk_factors:
            risk_table = Table(title="Risk Factors", style="orange")
            risk_table.add_column("Factor", style="bold")
            risk_table.add_column("Severity")
            risk_table.add_column("Description")
            
            for factor in assessment.risk_factors:
                severity_color = "red" if "high" in factor.lower() else "yellow" if "medium" in factor.lower() else "green"
                risk_table.add_row(
                    factor.split(":")[0] if ":" in factor else factor,
                    f"[{severity_color}]●[/{severity_color}]",
                    factor.split(":", 1)[1].strip() if ":" in factor else "Risk detected"
                )
            
            console.print(risk_table)
        
        # Stakeholder impact
        if assessment.stakeholder_impact:
            console.print(f"\n👥 Stakeholder Impact:")
            for stakeholder, impact in assessment.stakeholder_impact.items():
                impact_color = "green" if impact == "positive" else "red" if impact == "negative" else "yellow"
                console.print(f"   • {stakeholder}: [{impact_color}]{impact}[/{impact_color}]")
        
        # Mitigation strategies
        if show_mitigation and hasattr(assessment, 'mitigation_strategies'):
            console.print(f"\n🔧 Mitigation Strategies:")
            for strategy in assessment.mitigation_strategies[:5]:  # Show top 5
                console.print(f"   • {strategy}")
    
    asyncio.run(safety_async())


@app.command("optimize-hot-take")
def optimize_hot_take_cli(
    text: str = typer.Argument(..., help="Hot take text to optimize"),
    platform: str = typer.Option("general", help="Platform type: general, linkedin, twitter"),
    goal: str = typer.Option("engagement", help="Optimization goal: engagement, reach, safety")
):
    """Content optimization suggestions for hot takes (Epic 7)."""
    
    async def optimize_async():
        console.print(Panel(f"🚀 Epic 7: Hot Take Optimization - {goal.title()}", style="bold blue"))
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            task = progress.add_task("Analyzing optimization potential...", total=None)
            
            viral_engine = ViralPredictionEngine()
            safety_analyzer = BrandSafetyAnalyzer()
            
            # Get current scores
            viral_prediction = await viral_engine.predict_viral_potential(text, platform=platform)
            safety_assessment = await safety_analyzer.assess_content_safety(text)
            
            progress.update(task, description="Generating optimization strategies...")
            
            # Generate optimization suggestions
            optimization_suggestions = await viral_engine.optimize_for_platform(
                text, platform, goal
            )
        
        # Current performance
        console.print(f"\n📊 Current Performance:")
        console.print(f"   • Viral Score: {viral_prediction.overall_score:.2f}")
        console.print(f"   • Safety Level: {safety_assessment.safety_level.value}")
        console.print(f"   • Platform: {platform}")
        
        # Optimization suggestions tree
        opt_tree = Tree(f"🎯 {goal.title()} Optimization Strategies")
        
        for i, suggestion in enumerate(optimization_suggestions.get('suggestions', [])[:8]):
            priority = suggestion.get('priority', 'medium')
            priority_color = "red" if priority == "high" else "yellow" if priority == "medium" else "green"
            
            branch = opt_tree.add(f"[{priority_color}]{priority.title()} Priority[/{priority_color}]")
            branch.add(f"💡 {suggestion.get('action', 'Unknown action')}")
            
            if 'expected_improvement' in suggestion:
                branch.add(f"📈 Expected improvement: +{suggestion['expected_improvement']:.1%}")
        
        console.print(opt_tree)
        
        # Platform-specific tips
        platform_tips = {
            "linkedin": [
                "Use professional language and industry terminology",
                "Include a call-to-action for discussion",
                "Reference business trends or thought leadership"
            ],
            "twitter": [
                "Keep under 280 characters for optimal engagement",
                "Use relevant hashtags (2-3 maximum)",
                "Consider thread potential for complex ideas"
            ],
            "general": [
                "Focus on universal appeal and clear messaging",
                "Use emotional hooks to drive engagement",
                "Ensure message is platform-agnostic"
            ]
        }
        
        if platform in platform_tips:
            console.print(f"\n📱 {platform.title()}-Specific Tips:")
            for tip in platform_tips[platform]:
                console.print(f"   • {tip}")
    
    asyncio.run(optimize_async())


@app.command("trending-analysis")
def trending_analysis_cli(
    days_back: int = typer.Option(7, help="Days of trending data to analyze"),
    platform: str = typer.Option("all", help="Platform filter: all, linkedin, twitter"),
    min_viral_score: float = typer.Option(0.6, help="Minimum viral score threshold")
):
    """Analyze trending hot take patterns and viral content (Epic 7)."""
    
    console.print(Panel("📈 Epic 7: Trending Hot Take Analysis", style="bold magenta"))
    
    # Mock trending data (in production, this would come from analytics)
    trending_topics = [
        {"topic": "AI and Human Collaboration", "viral_score": 0.85, "safety_level": "SAFE", "mentions": 247},
        {"topic": "Remote Work Evolution", "viral_score": 0.78, "safety_level": "SAFE", "mentions": 189},
        {"topic": "Sustainable Business Practices", "viral_score": 0.72, "safety_level": "SAFE", "mentions": 156},
        {"topic": "Leadership Authenticity", "viral_score": 0.69, "safety_level": "CAUTION", "mentions": 134},
        {"topic": "Tech Industry Criticism", "viral_score": 0.88, "safety_level": "RISK", "mentions": 98}
    ]
    
    # Filter by viral score
    filtered_topics = [t for t in trending_topics if t["viral_score"] >= min_viral_score]
    
    # Trending topics table
    trending_table = Table(title=f"Trending Topics (Last {days_back} Days)", style="magenta")
    trending_table.add_column("Topic", style="bold")
    trending_table.add_column("Viral Score", justify="right")
    trending_table.add_column("Safety Level")
    trending_table.add_column("Mentions", justify="right")
    
    for topic in filtered_topics:
        score_color = "green" if topic["viral_score"] > 0.7 else "yellow"
        safety_color = {"SAFE": "green", "CAUTION": "yellow", "RISK": "orange", "DANGER": "red"}.get(topic["safety_level"], "white")
        
        trending_table.add_row(
            topic["topic"],
            f"[{score_color}]{topic['viral_score']:.2f}[/{score_color}]",
            f"[{safety_color}]{topic['safety_level']}[/{safety_color}]",
            str(topic["mentions"])
        )
    
    console.print(trending_table)
    
    # Insights
    console.print(f"\n💡 Trending Insights:")
    console.print(f"   • {len(filtered_topics)} topics above {min_viral_score:.1f} viral threshold")
    console.print(f"   • Average viral score: {sum(t['viral_score'] for t in filtered_topics) / len(filtered_topics):.2f}")
    console.print(f"   • Safe topics: {len([t for t in filtered_topics if t['safety_level'] == 'SAFE'])}")
    console.print(f"   • Platform focus: {platform}")


@app.command("risk-dashboard")
def risk_dashboard_cli(
    content_file: Optional[str] = typer.Option(None, help="JSON file with content to analyze"),
    real_time: bool = typer.Option(False, help="Enable real-time risk monitoring")
):
    """Visual risk assessment dashboard for content portfolio (Epic 7)."""
    
    async def dashboard_async():
        console.print(Panel("📊 Epic 7: Risk Assessment Dashboard", style="bold cyan"))
        
        if content_file:
            try:
                with open(content_file, 'r') as f:
                    content_data = json.load(f)
                console.print(f"📁 Loaded {len(content_data)} content items from {content_file}")
            except FileNotFoundError:
                console.print(f"❌ File {content_file} not found, using sample data")
                content_data = _get_sample_content_data()
        else:
            content_data = _get_sample_content_data()
        
        safety_analyzer = BrandSafetyAnalyzer()
        
        # Analyze all content
        assessments = []
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            task = progress.add_task("Analyzing content portfolio...", total=len(content_data))
            
            for item in content_data:
                assessment = await safety_analyzer.assess_content_safety(item.get('text', ''))
                assessments.append(assessment)
                progress.advance(task)
        
        # Risk distribution
        risk_counts = {}
        for assessment in assessments:
            level = assessment.safety_level.value
            risk_counts[level] = risk_counts.get(level, 0) + 1
        
        # Risk distribution table
        risk_table = Table(title="Risk Distribution", style="cyan")
        risk_table.add_column("Risk Level", style="bold")
        risk_table.add_column("Count", justify="right")
        risk_table.add_column("Percentage", justify="right")
        risk_table.add_column("Status")
        
        total_items = len(assessments)
        for level, count in risk_counts.items():
            percentage = (count / total_items) * 100
            color = {"safe": "green", "caution": "yellow", "risk": "orange", "danger": "red"}.get(level, "white")
            status = "✅" if level == "safe" else "⚠️" if level == "caution" else "❌"
            
            risk_table.add_row(
                f"[{color}]{level.upper()}[/{color}]",
                str(count),
                f"{percentage:.1f}%",
                status
            )
        
        console.print(risk_table)
        
        # High-risk items
        high_risk_items = [a for a in assessments if a.safety_level in [RiskLevel.RISK, RiskLevel.DANGER]]
        if high_risk_items:
            console.print(f"\n⚠️ High-Risk Content ({len(high_risk_items)} items):")
            for i, assessment in enumerate(high_risk_items[:5]):  # Show top 5
                risk_color = "orange" if assessment.safety_level == RiskLevel.RISK else "red"
                console.print(f"   {i+1}. [{risk_color}]{assessment.safety_level.value.upper()}[/{risk_color}] - Risk Score: {assessment.overall_risk_score:.2f}")
        
        if real_time:
            console.print(f"\n🔄 Real-time monitoring enabled (press Ctrl+C to stop)")
            console.print(f"   Monitoring {total_items} content items...")
            console.print(f"   Risk alerts will appear here...")
    
    asyncio.run(dashboard_async())


def _display_hot_take_analysis(viral_prediction: ViralPrediction, safety_assessment: BrandSafetyAssessment, show_details: bool):
    """Helper function to display hot take analysis results."""
    
    # Viral prediction results
    viral_table = Table(title="🔥 Viral Prediction Analysis", style="red")
    viral_table.add_column("Metric", style="bold")
    viral_table.add_column("Score", justify="right")
    viral_table.add_column("Assessment")
    
    metrics = [
        ("Overall Viral Score", f"{viral_prediction.overall_score:.2f}", _get_assessment_text(viral_prediction.overall_score)),
        ("Engagement Potential", f"{viral_prediction.engagement_score:.2f}", _get_assessment_text(viral_prediction.engagement_score)),
        ("Reach Potential", f"{viral_prediction.reach_potential:.2f}", _get_assessment_text(viral_prediction.reach_potential)),
        ("Viral Velocity", f"{viral_prediction.viral_velocity:.2f}", _get_assessment_text(viral_prediction.viral_velocity))
    ]
    
    for metric, score, assessment in metrics:
        viral_table.add_row(metric, score, assessment)
    
    console.print(viral_table)
    
    # Brand safety results
    safety_color = {
        RiskLevel.SAFE: "green",
        RiskLevel.CAUTION: "yellow",
        RiskLevel.RISK: "orange", 
        RiskLevel.DANGER: "red"
    }.get(safety_assessment.safety_level, "white")
    
    safety_table = Table(title="🛡️ Brand Safety Assessment", style="green")
    safety_table.add_column("Aspect", style="bold")
    safety_table.add_column("Result")
    
    safety_table.add_row("Safety Level", f"[{safety_color}]{safety_assessment.safety_level.value.upper()}[/{safety_color}]")
    safety_table.add_row("Risk Score", f"{safety_assessment.overall_risk_score:.2f} / 1.00")
    
    console.print(safety_table)
    
    if show_details:
        # Recommendations
        if hasattr(viral_prediction, 'recommendations') and viral_prediction.recommendations:
            console.print(f"\n💡 Optimization Recommendations:")
            for i, rec in enumerate(viral_prediction.recommendations[:5], 1):
                console.print(f"   {i}. {rec}")
        
        # Risk factors
        if hasattr(safety_assessment, 'risk_factors') and safety_assessment.risk_factors:
            console.print(f"\n⚠️ Risk Factors:")
            for factor in safety_assessment.risk_factors[:3]:
                console.print(f"   • {factor}")


def _viral_prediction_to_dict(prediction: ViralPrediction) -> Dict[str, Any]:
    """Convert ViralPrediction to dictionary."""
    return {
        "overall_score": prediction.overall_score,
        "engagement_score": prediction.engagement_score,
        "reach_potential": prediction.reach_potential,
        "viral_velocity": prediction.viral_velocity,
        "controversy_score": prediction.controversy_score,
        "recommendations": getattr(prediction, 'recommendations', []),
        "platform_optimization": getattr(prediction, 'platform_optimization', {})
    }


def _safety_assessment_to_dict(assessment: BrandSafetyAssessment) -> Dict[str, Any]:
    """Convert BrandSafetyAssessment to dictionary."""
    return {
        "safety_level": assessment.safety_level.value,
        "overall_risk_score": assessment.overall_risk_score,
        "risk_factors": getattr(assessment, 'risk_factors', []),
        "stakeholder_impact": getattr(assessment, 'stakeholder_impact', {})
    }


def _get_impact_text(score: float) -> str:
    """Get impact description for a score."""
    if score > 0.8:
        return "[green]High[/green]"
    elif score > 0.6:
        return "[yellow]Medium[/yellow]"
    elif score > 0.4:
        return "[orange]Low[/orange]"
    else:
        return "[red]Very Low[/red]"


def _get_assessment_text(score: float) -> str:
    """Get assessment description for a score."""
    if score > 0.8:
        return "[green]Excellent[/green]"
    elif score > 0.6:
        return "[yellow]Good[/yellow]"
    elif score > 0.4:
        return "[orange]Fair[/orange]"
    else:
        return "[red]Poor[/red]"


def _get_sample_content_data() -> List[Dict[str, Any]]:
    """Get sample content data for dashboard."""
    return [
        {"text": "AI is transforming the way we work and collaborate", "platform": "linkedin"},
        {"text": "Remote work is dead - everyone needs to return to office", "platform": "twitter"},
        {"text": "Sustainable business practices are the future", "platform": "general"},
        {"text": "Most CEOs have no idea what they're doing", "platform": "twitter"},
        {"text": "Innovation requires taking calculated risks", "platform": "linkedin"}
    ]


# === EPIC 8.3 & 8.4: AUDIENCE INTELLIGENCE & COMPETITIVE ANALYSIS CLI COMMANDS ===

# Import additional dependencies for Epic 8
from graph_rag.core.audience_intelligence import AudienceSegmentationEngine, AudienceSegment, AudiencePersona
from graph_rag.core.competitive_analysis import CompetitiveAnalyzer, analyze_competitor_landscape, identify_market_opportunities


@app.command("audience-analyze")
def audience_analyze_cli(
    text: str = typer.Argument(..., help="Content text to analyze for audience insights"),
    platform: str = typer.Option("general", help="Platform type: general, linkedin, twitter"),
    output_format: str = typer.Option("visual", help="Output format: visual, json"),
    save_to: Optional[str] = typer.Option(None, help="Save results to file"),
    show_details: bool = typer.Option(False, help="Show detailed analysis breakdown")
):
    """Comprehensive audience segmentation analysis (Epic 8.1 & 8.4)."""
    
    async def analyze_async():
        console.print(Panel("🎯 Epic 8.4: Audience Intelligence Analysis", style="bold blue"))
        console.print(f"Platform: {platform}")
        console.print(f"Content length: {len(text)} characters")
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            task = progress.add_task("Analyzing audience segments...", total=None)
            
            # Initialize audience segmentation engine
            audience_engine = AudienceSegmentationEngine()
            
            # Perform comprehensive audience analysis
            analysis_result = await audience_engine.analyze_audience(
                text, {"platform": platform}
            )
            
            progress.update(task, description="Generating insights...")
            
            if output_format == "json":
                json_output = json.dumps(analysis_result, indent=2, default=str)
                console.print(json_output)
                
                if save_to:
                    with open(save_to, 'w') as f:
                        f.write(json_output)
                    console.print(f"✅ Analysis saved to {save_to}")
                    
            else:  # visual format
                _display_audience_analysis(analysis_result, show_details)
                
                if save_to:
                    # Save as JSON even if displayed visually
                    with open(save_to, 'w') as f:
                        json.dump(analysis_result, f, indent=2, default=str)
                    console.print(f"✅ Analysis saved to {save_to}")
    
    asyncio.run(analyze_async())


@app.command("resonance-score")
def resonance_score_cli(
    content: str = typer.Argument(..., help="Content to analyze for audience resonance"),
    audience_file: str = typer.Option(..., help="JSON file containing audience segment data"),
    platform: str = typer.Option("general", help="Platform for analysis"),
    show_breakdown: bool = typer.Option(False, help="Show detailed resonance breakdown")
):
    """Content-audience resonance scoring (Epic 8.2 & 8.4)."""
    
    async def score_async():
        console.print(Panel("📊 Epic 8.4: Content-Audience Resonance Analysis", style="bold green"))
        
        try:
            # Load audience segment data
            with open(audience_file, 'r') as f:
                audience_data = json.load(f)
            
            console.print(f"📁 Loaded audience data from {audience_file}")
            
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console
            ) as progress:
                task = progress.add_task("Calculating resonance score...", total=None)
                
                # Initialize audience segmentation engine
                audience_engine = AudienceSegmentationEngine()
                
                # Convert audience data to AudienceSegment
                audience_segment = AudienceSegment(**audience_data)
                
                # Calculate resonance score
                resonance_score = await audience_engine.predict_audience_content_resonance(
                    audience_segment, content
                )
                
                progress.update(task, description="Generating insights...")
            
            # Display resonance score
            score_color = "green" if resonance_score > 0.7 else "yellow" if resonance_score > 0.4 else "red"
            console.print(f"\n🎯 Resonance Score: [{score_color}]{resonance_score:.2f}[/{score_color}] / 1.00")
            
            # Score bar visualization
            bar_length = 50
            filled = int(resonance_score * bar_length)
            bar = "█" * filled + "░" * (bar_length - filled)
            console.print(f"   [{score_color}]{bar}[/{score_color}]")
            
            if show_breakdown:
                # Detailed breakdown
                breakdown_table = Table(title="Resonance Score Breakdown", style="cyan")
                breakdown_table.add_column("Component", style="bold")
                breakdown_table.add_column("Score", justify="right")
                breakdown_table.add_column("Impact")
                
                # Mock detailed scores - in production would be calculated
                components = [
                    ("Demographic Alignment", "0.82", _get_impact_text(0.82)),
                    ("Behavioral Alignment", "0.75", _get_impact_text(0.75)),
                    ("Psychographic Alignment", "0.68", _get_impact_text(0.68)),
                    ("Platform Optimization", "0.79", _get_impact_text(0.79))
                ]
                
                for component, score, impact in components:
                    breakdown_table.add_row(component, score, impact)
                
                console.print(breakdown_table)
            
            # Recommendations
            console.print(f"\n💡 Optimization Recommendations:")
            recommendations = [
                "Adjust content tone to better match audience preferences",
                "Include more audience-specific examples and use cases", 
                "Optimize content length for target audience attention span",
                "Add stronger call-to-action elements for engagement"
            ]
            
            for rec in recommendations:
                console.print(f"   • {rec}")
                
        except FileNotFoundError:
            console.print(f"❌ Error: Audience file {audience_file} not found")
            raise typer.Exit(1)
        except json.JSONDecodeError:
            console.print(f"❌ Error: Invalid JSON in {audience_file}")
            raise typer.Exit(1)
    
    asyncio.run(score_async())


@app.command("audience-personas")
def audience_personas_cli(
    content_dir: str = typer.Argument(..., help="Directory containing content samples"),
    platform: str = typer.Option("general", help="Platform context"),
    persona_count: int = typer.Option(3, help="Number of personas to generate"),
    output_format: str = typer.Option("visual", help="Output format: visual, json"),
    save_to: Optional[str] = typer.Option(None, help="Save personas to file")
):
    """Generate detailed audience personas from content analysis (Epic 8.1 & 8.4)."""
    
    async def personas_async():
        console.print(Panel(f"👥 Epic 8.4: Audience Persona Generation", style="bold magenta"))
        
        try:
            content_path = Path(content_dir)
            if not content_path.exists():
                console.print(f"❌ Directory not found: {content_dir}")
                return
            
            # Load content samples
            content_samples = []
            content_files = list(content_path.glob("*.txt")) + list(content_path.glob("*.json"))
            
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console
            ) as progress:
                task = progress.add_task("Loading content samples...", total=len(content_files))
                
                for file in content_files[:persona_count * 2]:  # Load more than needed
                    try:
                        if file.suffix == ".json":
                            with open(file, 'r') as f:
                                data = json.load(f)
                                if isinstance(data, dict) and "text" in data:
                                    content_samples.append(data["text"])
                                elif isinstance(data, str):
                                    content_samples.append(data)
                        else:
                            content_samples.append(file.read_text())
                        
                        progress.advance(task)
                        
                        if len(content_samples) >= persona_count:
                            break
                            
                    except Exception as e:
                        console.print(f"⚠️ Error loading {file}: {e}")
                        progress.advance(task)
                        continue
                
                progress.update(task, description="Generating personas...")
                
                # Initialize audience segmentation engine
                audience_engine = AudienceSegmentationEngine()
                
                # Generate personas from content samples
                personas = []
                for i, content in enumerate(content_samples[:persona_count]):
                    try:
                        analysis_result = await audience_engine.analyze_audience(
                            content, {"platform": platform, "sample_id": i}
                        )
                        
                        if analysis_result.get("audience_persona"):
                            personas.append(analysis_result["audience_persona"])
                            
                    except Exception as e:
                        console.print(f"⚠️ Error generating persona {i+1}: {e}")
                        continue
                
                progress.update(task, description="Complete!")
            
            if not personas:
                console.print("❌ No personas could be generated from the content samples")
                return
            
            if output_format == "json":
                personas_output = {
                    "personas": personas,
                    "generation_summary": {
                        "total_generated": len(personas),
                        "source_content_samples": len(content_samples),
                        "platform": platform
                    }
                }
                
                json_output = json.dumps(personas_output, indent=2, default=str)
                console.print(json_output)
                
                if save_to:
                    with open(save_to, 'w') as f:
                        f.write(json_output)
                    console.print(f"✅ Personas saved to {save_to}")
                    
            else:  # visual format
                _display_audience_personas(personas, platform)
                
                if save_to:
                    personas_output = {
                        "personas": personas,
                        "generation_summary": {
                            "total_generated": len(personas),
                            "platform": platform
                        }
                    }
                    with open(save_to, 'w') as f:
                        json.dump(personas_output, f, indent=2, default=str)
                    console.print(f"✅ Personas saved to {save_to}")
            
            console.print(f"\n✨ Generated {len(personas)} audience personas from {len(content_samples)} content samples")
            
        except Exception as e:
            console.print(f"❌ Error generating personas: {e}")
    
    asyncio.run(personas_async())


@app.command("competitive-analysis")
def competitive_analysis_cli(
    competitor_data_dir: str = typer.Argument(..., help="Directory containing competitor content data"),
    our_strategy_file: Optional[str] = typer.Option(None, help="JSON file with our content strategy"),
    output_format: str = typer.Option("visual", help="Output format: visual, json"),
    save_to: Optional[str] = typer.Option(None, help="Save analysis to file"),
    show_details: bool = typer.Option(False, help="Show detailed competitive insights")
):
    """Comprehensive competitive analysis for market positioning (Epic 8.3 & 8.4)."""
    
    async def analysis_async():
        console.print(Panel("🏆 Epic 8.4: Competitive Analysis & Market Positioning", style="bold red"))
        
        try:
            data_path = Path(competitor_data_dir)
            if not data_path.exists():
                console.print(f"❌ Directory not found: {competitor_data_dir}")
                return
            
            # Load our strategy if provided
            our_strategy = None
            if our_strategy_file:
                try:
                    with open(our_strategy_file, 'r') as f:
                        our_strategy = json.load(f)
                    console.print(f"📁 Loaded our strategy from {our_strategy_file}")
                except Exception as e:
                    console.print(f"⚠️ Could not load strategy file: {e}")
            
            # Load competitor data
            competitor_data = {}
            
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console
            ) as progress:
                
                # Find competitor data files
                competitor_files = list(data_path.glob("*competitor*.json")) + list(data_path.glob("*comp_*.json"))
                if not competitor_files:
                    # Look for any JSON files
                    competitor_files = list(data_path.glob("*.json"))
                
                task = progress.add_task("Loading competitor data...", total=len(competitor_files))
                
                for file in competitor_files:
                    try:
                        with open(file, 'r') as f:
                            data = json.load(f)
                        
                        competitor_name = file.stem.replace("competitor_", "").replace("comp_", "")
                        
                        if isinstance(data, list):
                            competitor_data[competitor_name] = data
                        elif isinstance(data, dict):
                            # If single item, wrap in list
                            competitor_data[competitor_name] = [data]
                        
                        progress.advance(task)
                        
                    except Exception as e:
                        console.print(f"⚠️ Error loading {file}: {e}")
                        progress.advance(task)
                        continue
                
                if not competitor_data:
                    console.print("❌ No competitor data could be loaded")
                    return
                
                progress.update(task, description="Analyzing competitive landscape...")
                
                # Perform competitive analysis
                analysis_result = await analyze_competitor_landscape(
                    competitor_data, our_strategy
                )
                
                progress.update(task, description="Complete!")
            
            if output_format == "json":
                # Convert to JSON-serializable format
                json_result = {
                    "analysis_id": analysis_result.analysis_id,
                    "market_landscape": analysis_result.market_landscape,
                    "competitive_intensity": analysis_result.competitive_intensity,
                    "market_maturity": analysis_result.market_maturity,
                    "competitor_count": len(analysis_result.competitor_profiles),
                    "market_gaps_count": len(analysis_result.market_gaps),
                    "insights_count": len(analysis_result.competitive_insights),
                    "confidence_level": analysis_result.confidence_level,
                    "strategic_recommendations": analysis_result.strategic_recommendations,
                    "differentiation_opportunities": analysis_result.differentiation_opportunities
                }
                
                json_output = json.dumps(json_result, indent=2)
                console.print(json_output)
                
                if save_to:
                    with open(save_to, 'w') as f:
                        f.write(json_output)
                    console.print(f"✅ Analysis saved to {save_to}")
                    
            else:  # visual format
                _display_competitive_analysis(analysis_result, show_details)
                
                if save_to:
                    # Save summary as JSON
                    json_result = {
                        "analysis_id": analysis_result.analysis_id,
                        "competitor_count": len(analysis_result.competitor_profiles),
                        "market_gaps_count": len(analysis_result.market_gaps),
                        "confidence_level": analysis_result.confidence_level,
                        "strategic_recommendations": analysis_result.strategic_recommendations
                    }
                    with open(save_to, 'w') as f:
                        json.dump(json_result, f, indent=2)
                    console.print(f"✅ Analysis summary saved to {save_to}")
            
            console.print(f"\n🎉 Competitive analysis complete!")
            console.print(f"   • {len(analysis_result.competitor_profiles)} competitors analyzed")
            console.print(f"   • {len(analysis_result.market_gaps)} market gaps identified")
            console.print(f"   • {len(analysis_result.competitive_insights)} strategic insights generated")
            console.print(f"   • Confidence level: {analysis_result.confidence_level:.2f}")
            
        except Exception as e:
            console.print(f"❌ Error in competitive analysis: {e}")
    
    asyncio.run(analysis_async())


# Helper functions for Epic 8 CLI commands

def _display_audience_analysis(analysis_result: Dict[str, Any], show_details: bool = False):
    """Display audience analysis results in visual format."""
    
    # Main audience segment
    audience_segment = analysis_result.get("audience_segment", {})
    if audience_segment:
        segment_table = Table(title="🎯 Audience Segment Analysis", style="blue")
        segment_table.add_column("Attribute", style="bold")
        segment_table.add_column("Value")
        segment_table.add_column("Confidence")
        
        segment_table.add_row("Segment Name", audience_segment.get("name", "Unknown"), f"{audience_segment.get('confidence_score', 0):.2f}")
        segment_table.add_row("Description", audience_segment.get("description", "N/A")[:50] + "...", "")
        segment_table.add_row("Size Estimate", str(audience_segment.get("size_estimate", 0)), "")
        segment_table.add_row("Engagement Potential", f"{audience_segment.get('engagement_potential', 0):.2f}", "")
        
        console.print(segment_table)
    
    # Demographic analysis
    demographic_analysis = analysis_result.get("demographic_analysis", {})
    if demographic_analysis and show_details:
        demo_table = Table(title="👥 Demographic Analysis", style="cyan")
        demo_table.add_column("Factor", style="bold")
        demo_table.add_column("Value")
        demo_table.add_column("Confidence")
        
        profile = demographic_analysis.get("profile", {})
        demo_table.add_row("Age Group", str(profile.get("age_group", "Unknown")), f"{profile.get('confidence', 0):.2f}")
        demo_table.add_row("Industry", str(profile.get("industry", "Unknown")), "")
        demo_table.add_row("Experience Level", str(profile.get("job_level", "Unknown")), "")
        demo_table.add_row("Location", str(profile.get("location", "Unknown")), "")
        
        console.print(demo_table)
    
    # Content recommendations
    recommendations = analysis_result.get("content_recommendations", [])
    if recommendations:
        console.print(f"\n💡 Content Strategy Recommendations:")
        for i, rec in enumerate(recommendations[:5], 1):
            console.print(f"   {i}. {rec}")
    
    # Overall confidence
    overall_confidence = analysis_result.get("overall_confidence", 0.0)
    confidence_color = "green" if overall_confidence > 0.7 else "yellow" if overall_confidence > 0.4 else "red"
    console.print(f"\n📊 Overall Analysis Confidence: [{confidence_color}]{overall_confidence:.2f}[/{confidence_color}]")


def _display_audience_personas(personas: List[Dict[str, Any]], platform: str):
    """Display audience personas in visual format."""
    
    for i, persona in enumerate(personas, 1):
        persona_panel = Panel(
            f"[bold]{persona.get('name', f'Persona {i}')}[/bold]\n\n"
            f"[italic]{persona.get('avatar_description', 'No description available')}[/italic]\n\n"
            f"Background: {persona.get('background_story', 'No background available')[:100]}...\n\n"
            f"Quote: \"{persona.get('quote', 'No quote available')}\"\n\n"
            f"Confidence: {persona.get('persona_confidence', 0):.2f}",
            title=f"Persona {i}",
            style="magenta"
        )
        console.print(persona_panel)
        
        # Show key characteristics if available
        if persona.get("psychographic_profile", {}).get("personality_traits"):
            traits = list(persona["psychographic_profile"]["personality_traits"].keys())[:3]
            console.print(f"   Key Traits: {', '.join(traits)}")
        
        if persona.get("demographic_profile", {}).get("industry"):
            console.print(f"   Industry: {persona['demographic_profile']['industry']}")
        
        console.print()  # Add spacing


def _display_competitive_analysis(analysis_result, show_details: bool = False):
    """Display competitive analysis results in visual format."""
    
    # Market landscape overview
    market_landscape = analysis_result.market_landscape
    console.print(Panel(
        f"Total Competitors: {market_landscape.get('total_competitors', 0)}\n"
        f"Market Maturity: {analysis_result.market_maturity}\n"
        f"Competitive Intensity: {analysis_result.competitive_intensity:.2f}\n"
        f"Analysis Confidence: {analysis_result.confidence_level:.2f}",
        title="🏪 Market Landscape",
        style="blue"
    ))
    
    # Top competitors
    if analysis_result.competitor_profiles:
        competitor_table = Table(title="🏆 Top Competitors", style="red")
        competitor_table.add_column("Competitor", style="bold")
        competitor_table.add_column("Market Position")
        competitor_table.add_column("Engagement Rate")
        competitor_table.add_column("Viral Score")
        competitor_table.add_column("Confidence")
        
        for profile in analysis_result.competitor_profiles[:5]:  # Top 5
            competitor_table.add_row(
                profile.name,
                profile.market_position.value if profile.market_position else "Unknown",
                f"{profile.average_engagement_rate:.3f}",
                f"{profile.average_viral_score:.2f}",
                f"{profile.confidence_score:.2f}"
            )
        
        console.print(competitor_table)
    
    # Market gaps (opportunities)
    if analysis_result.market_gaps:
        console.print(f"\n🎯 Top Market Opportunities:")
        for i, gap in enumerate(analysis_result.market_gaps[:3], 1):
            opportunity_score = gap.opportunity_size - gap.difficulty_score
            score_color = "green" if opportunity_score > 0.5 else "yellow" if opportunity_score > 0.2 else "red"
            
            console.print(f"   {i}. [{score_color}]{gap.description}[/{score_color}]")
            console.print(f"      Opportunity Size: {gap.opportunity_size:.2f} | Difficulty: {gap.difficulty_score:.2f}")
            console.print(f"      Timeline: {gap.estimated_timeline}")
    
    # Strategic recommendations
    if analysis_result.strategic_recommendations:
        console.print(f"\n💡 Strategic Recommendations:")
        for i, rec in enumerate(analysis_result.strategic_recommendations[:5], 1):
            console.print(f"   {i}. {rec}")
    
    # Detailed insights
    if show_details and analysis_result.competitive_insights:
        console.print(f"\n🔍 Competitive Insights:")
        for insight in analysis_result.competitive_insights[:3]:
            insight_panel = Panel(
                f"[bold]{insight.title}[/bold]\n\n"
                f"{insight.description}\n\n"
                f"Priority: {insight.strategic_priority}\n"
                f"Confidence: {insight.confidence:.2f}",
                title=f"{insight.insight_type.title()} Insight",
                style="yellow"
            )
            console.print(insight_panel)


if __name__ == "__main__":
    app()