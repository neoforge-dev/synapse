"""Interactive concept mapping and visualization system."""

import json
import logging
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from graph_rag.core.concept_extractor import ConceptualEntity, IdeaRelationship
from graph_rag.core.temporal_tracker import IdeaEvolution
from graph_rag.services.cross_platform_correlator import CrossPlatformCorrelator

logger = logging.getLogger(__name__)


@dataclass
class ConceptNode:
    """Node representation for concept visualization."""
    id: str
    label: str
    concept_type: str
    platform: str
    size: float  # Based on importance/frequency
    color: str
    metadata: dict[str, Any]
    position: dict[str, float] | None = None  # x, y coordinates


@dataclass
class ConceptEdge:
    """Edge representation for concept relationships."""
    source: str
    target: str
    relationship_type: str
    weight: float
    color: str
    metadata: dict[str, Any]


@dataclass
class ConceptMap:
    """Complete concept map structure."""
    nodes: list[ConceptNode]
    edges: list[ConceptEdge]
    metadata: dict[str, Any]
    layout: str = "force-directed"


class ConceptMapper:
    """Service for creating interactive concept maps."""

    def __init__(self, correlator: CrossPlatformCorrelator):
        self.correlator = correlator
        self.color_schemes = {
            "STRATEGY": "#FF6B6B",
            "INNOVATION": "#4ECDC4",
            "PROCESS": "#45B7D1",
            "INSIGHT": "#96CEB4",
            "ENGAGEMENT": "#FFEAA7",
            "KNOWLEDGE": "#DDA0DD",
            "CONCEPT": "#98D8C8",
            "linkedin": "#0077B5",
            "notion": "#000000",
            "blog": "#FF5722",
            "default": "#95A5A6"
        }

    async def create_concept_map(self, evolution_ids: list[str] = None,
                               time_range: tuple[datetime, datetime] = None) -> ConceptMap:
        """Create a comprehensive concept map."""

        # Gather all concepts and relationships
        concepts = []
        relationships = []

        if evolution_ids:
            # Map specific evolutions
            for evo_id in evolution_ids:
                evolution = await self.correlator.temporal_tracker.idea_evolutions.get(evo_id)
                if evolution:
                    evo_concepts, evo_relationships = await self._extract_evolution_data(evolution)
                    concepts.extend(evo_concepts)
                    relationships.extend(evo_relationships)
        else:
            # Map all available concepts
            for evolution in self.correlator.temporal_tracker.idea_evolutions.values():
                evo_concepts, evo_relationships = await self._extract_evolution_data(evolution)
                concepts.extend(evo_concepts)
                relationships.extend(evo_relationships)

        # Add cross-platform correlations
        correlation_relationships = await self._extract_correlation_relationships()
        relationships.extend(correlation_relationships)

        # Filter by time range if specified
        if time_range:
            concepts = [c for c in concepts if time_range[0] <= c.metadata.get("timestamp", datetime.min) <= time_range[1]]

        # Create nodes and edges
        nodes = await self._create_concept_nodes(concepts)
        edges = await self._create_concept_edges(relationships, [n.id for n in nodes])

        # Calculate layout positions
        nodes_with_positions = await self._calculate_layout(nodes, edges)

        metadata = {
            "created_at": datetime.now().isoformat(),
            "node_count": len(nodes_with_positions),
            "edge_count": len(edges),
            "time_range": [t.isoformat() for t in time_range] if time_range else None,
            "evolution_count": len(evolution_ids) if evolution_ids else len(self.correlator.temporal_tracker.idea_evolutions)
        }

        return ConceptMap(
            nodes=nodes_with_positions,
            edges=edges,
            metadata=metadata
        )

    async def _extract_evolution_data(self, evolution: IdeaEvolution) -> tuple[list[ConceptualEntity], list[IdeaRelationship]]:
        """Extract concepts and relationships from an evolution."""
        concepts = []
        relationships = []

        for version in evolution.concept_versions:
            concepts.append(version.concept)

            # Create temporal relationships between versions
            if version.predecessor_id:
                relationship = IdeaRelationship(
                    source_concept=version.predecessor_id,
                    target_concept=version.concept.id,
                    relationship_type="EVOLVES_TO",
                    confidence=0.9,
                    evidence_text="Temporal evolution"
                )
                relationships.append(relationship)

        return concepts, relationships

    async def _extract_correlation_relationships(self) -> list[IdeaRelationship]:
        """Extract relationships from cross-platform correlations."""
        relationships = []

        for correlation in self.correlator.correlations:
            # Create relationship based on correlation
            relationship = IdeaRelationship(
                source_concept=correlation.source_content.content_id,
                target_concept=correlation.target_content.content_id,
                relationship_type=f"CORRELATES_{correlation.correlation_type.value.upper()}",
                confidence=correlation.confidence,
                evidence_text=f"Cross-platform correlation: {correlation.evidence}"
            )
            relationships.append(relationship)

        return relationships

    async def _create_concept_nodes(self, concepts: list[ConceptualEntity]) -> list[ConceptNode]:
        """Create visualization nodes from concepts."""
        nodes = []
        concept_frequency = {}

        # Count concept frequency for sizing
        for concept in concepts:
            concept_frequency[concept.id] = concept_frequency.get(concept.id, 0) + 1

        for concept in concepts:
            frequency = concept_frequency[concept.id]
            size = min(max(frequency * 10, 20), 100)  # Size between 20-100

            platform = concept.metadata.get("platform", "unknown")
            color = self.color_schemes.get(concept.concept_type,
                   self.color_schemes.get(platform,
                   self.color_schemes["default"]))

            node = ConceptNode(
                id=concept.id,
                label=concept.name,
                concept_type=concept.concept_type,
                platform=platform,
                size=size,
                color=color,
                metadata={
                    "frequency": frequency,
                    "confidence": getattr(concept, "confidence", 0.5),
                    "platform": platform,
                    "original_metadata": concept.metadata
                }
            )
            nodes.append(node)

        return nodes

    async def _create_concept_edges(self, relationships: list[IdeaRelationship],
                                  valid_node_ids: list[str]) -> list[ConceptEdge]:
        """Create visualization edges from relationships."""
        edges = []

        for relationship in relationships:
            # Only include edges where both nodes exist
            if (relationship.source_concept in valid_node_ids and
                relationship.target_concept in valid_node_ids):

                weight = relationship.confidence * 5  # Scale for visualization
                color = self._get_relationship_color(relationship.relationship_type)

                edge = ConceptEdge(
                    source=relationship.source_concept,
                    target=relationship.target_concept,
                    relationship_type=relationship.relationship_type,
                    weight=weight,
                    color=color,
                    metadata={
                        "confidence": relationship.confidence,
                        "evidence": relationship.evidence_text
                    }
                )
                edges.append(edge)

        return edges

    def _get_relationship_color(self, relationship_type: str) -> str:
        """Get color for relationship type."""
        color_map = {
            "EVOLVES_TO": "#3498db",
            "BUILDS_UPON": "#2ecc71",
            "CONTRADICTS": "#e74c3c",
            "INFLUENCES": "#f39c12",
            "ENABLES": "#9b59b6",
            "CORRELATES_DRAFT_TO_POST": "#1abc9c",
            "CORRELATES_POST_TO_COMMENT": "#34495e",
            "RELATED_TO": "#95a5a6"
        }
        return color_map.get(relationship_type, "#bdc3c7")

    async def _calculate_layout(self, nodes: list[ConceptNode], edges: list[ConceptEdge]) -> list[ConceptNode]:
        """Calculate layout positions for nodes."""
        # Simple circular layout for now - can be enhanced with force-directed algorithms
        import math

        node_count = len(nodes)
        center_x, center_y = 400, 300  # Canvas center
        radius = 200

        for i, node in enumerate(nodes):
            angle = 2 * math.pi * i / node_count
            x = center_x + radius * math.cos(angle)
            y = center_y + radius * math.sin(angle)

            node.position = {"x": x, "y": y}

        return nodes

    async def create_temporal_flow_map(self, evolution_id: str) -> dict[str, Any]:
        """Create a temporal flow visualization for idea evolution."""
        evolution = self.correlator.temporal_tracker.idea_evolutions.get(evolution_id)
        if not evolution:
            return {}

        chronological_versions = evolution.get_chronological_versions()

        # Create timeline visualization data
        timeline_data = {
            "evolution_id": evolution_id,
            "core_idea": evolution.core_idea_id,
            "timeline": [],
            "platforms": [],
            "stages": []
        }

        for i, version in enumerate(chronological_versions):
            timeline_data["timeline"].append({
                "index": i,
                "timestamp": version.timestamp.isoformat(),
                "platform": version.platform.value,
                "stage": version.stage.value,
                "concept_name": version.concept.name,
                "concept_id": version.concept.id,
                "content_snippet": version.content_snippet[:200] if version.content_snippet else "",
                "engagement_metrics": version.engagement_metrics
            })

        # Extract unique platforms and stages
        timeline_data["platforms"] = list(set(v.platform.value for v in chronological_versions))
        timeline_data["stages"] = list(set(v.stage.value for v in chronological_versions))

        return timeline_data

    async def create_cross_platform_flow(self) -> dict[str, Any]:
        """Create visualization of content flow between platforms."""
        transitions = await self.correlator.temporal_tracker.get_platform_transition_patterns()

        # Create Sankey diagram data
        platforms = set()
        for source, targets in transitions.items():
            platforms.add(source)
            platforms.update(targets.keys())

        platform_list = list(platforms)
        platform_indices = {platform: i for i, platform in enumerate(platform_list)}

        links = []
        for source, targets in transitions.items():
            source_idx = platform_indices[source]
            for target, count in targets.items():
                target_idx = platform_indices[target]
                links.append({
                    "source": source_idx,
                    "target": target_idx,
                    "value": count,
                    "source_name": source,
                    "target_name": target
                })

        return {
            "nodes": [{"name": platform} for platform in platform_list],
            "links": links,
            "platform_indices": platform_indices
        }

    async def export_concept_map_html(self, concept_map: ConceptMap,
                                    output_path: str = "concept_map.html") -> str:
        """Export concept map as interactive HTML."""

        html_template = """
<!DOCTYPE html>
<html>
<head>
    <title>Interactive Concept Map</title>
    <script src="https://d3js.org/d3.v7.min.js"></script>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 0; padding: 20px; }}
        .container {{ max-width: 1200px; margin: 0 auto; }}
        .controls {{ margin-bottom: 20px; }}
        .map-container {{ border: 1px solid #ddd; border-radius: 8px; }}
        .tooltip {{ position: absolute; padding: 10px; background: rgba(0,0,0,0.8); color: white; border-radius: 4px; pointer-events: none; }}
        .legend {{ float: right; width: 200px; padding: 10px; background: #f9f9f9; border-radius: 4px; }}
        .node {{ cursor: pointer; }}
        .link {{ stroke-opacity: 0.6; }}
        .selected {{ stroke: #ff0000; stroke-width: 3px; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>🧠 Interactive Concept Map</h1>
        <div class="controls">
            <button onclick="resetZoom()">Reset View</button>
            <button onclick="toggleLabels()">Toggle Labels</button>
            <label>
                Filter by type:
                <select id="typeFilter" onchange="filterByType()">
                    <option value="all">All Types</option>
                    <option value="STRATEGY">Strategy</option>
                    <option value="INNOVATION">Innovation</option>
                    <option value="PROCESS">Process</option>
                    <option value="INSIGHT">Insight</option>
                </select>
            </label>
        </div>
        
        <div class="legend">
            <h3>Legend</h3>
            <div><strong>Node Size:</strong> Concept frequency</div>
            <div><strong>Edge Width:</strong> Relationship strength</div>
            <div><strong>Colors:</strong></div>
            <div style="color: #FF6B6B;">● Strategy</div>
            <div style="color: #4ECDC4;">● Innovation</div>
            <div style="color: #45B7D1;">● Process</div>
            <div style="color: #96CEB4;">● Insight</div>
        </div>
        
        <svg class="map-container" width="800" height="600"></svg>
    </div>
    
    <div class="tooltip" style="opacity: 0;"></div>
    
    <script>
        const data = {data_json};
        
        const svg = d3.select("svg");
        const width = +svg.attr("width");
        const height = +svg.attr("height");
        
        const g = svg.append("g");
        
        // Add zoom behavior
        const zoom = d3.zoom()
            .scaleExtent([0.1, 4])
            .on("zoom", (event) => g.attr("transform", event.transform));
        svg.call(zoom);
        
        // Create simulation
        const simulation = d3.forceSimulation()
            .force("link", d3.forceLink().id(d => d.id).distance(100))
            .force("charge", d3.forceManyBody().strength(-300))
            .force("center", d3.forceCenter(width / 2, height / 2));
        
        // Create links
        const link = g.append("g")
            .attr("class", "links")
            .selectAll("line")
            .data(data.edges)
            .enter().append("line")
            .attr("class", "link")
            .attr("stroke", d => d.color)
            .attr("stroke-width", d => Math.max(1, d.weight));
        
        // Create nodes
        const node = g.append("g")
            .attr("class", "nodes")
            .selectAll("circle")
            .data(data.nodes)
            .enter().append("circle")
            .attr("class", "node")
            .attr("r", d => d.size / 2)
            .attr("fill", d => d.color)
            .call(d3.drag()
                .on("start", dragstarted)
                .on("drag", dragged)
                .on("end", dragended));
        
        // Add labels
        const labels = g.append("g")
            .attr("class", "labels")
            .selectAll("text")
            .data(data.nodes)
            .enter().append("text")
            .text(d => d.label)
            .attr("font-size", "12px")
            .attr("dx", 15)
            .attr("dy", 4);
        
        // Add tooltips
        const tooltip = d3.select(".tooltip");
        
        node.on("mouseover", function(event, d) {{
            tooltip.transition().duration(200).style("opacity", .9);
            tooltip.html(`
                <strong>${{d.label}}</strong><br/>
                Type: ${{d.concept_type}}<br/>
                Platform: ${{d.platform}}<br/>
                Frequency: ${{d.metadata.frequency}}
            `)
            .style("left", (event.pageX + 10) + "px")
            .style("top", (event.pageY - 28) + "px");
        }})
        .on("mouseout", function(d) {{
            tooltip.transition().duration(500).style("opacity", 0);
        }});
        
        // Start simulation
        simulation
            .nodes(data.nodes)
            .on("tick", ticked);
        
        simulation.force("link")
            .links(data.edges);
        
        function ticked() {{
            link
                .attr("x1", d => d.source.x)
                .attr("y1", d => d.source.y)
                .attr("x2", d => d.target.x)
                .attr("y2", d => d.target.y);
            
            node
                .attr("cx", d => d.x)
                .attr("cy", d => d.y);
            
            labels
                .attr("x", d => d.x)
                .attr("y", d => d.y);
        }}
        
        function dragstarted(event, d) {{
            if (!event.active) simulation.alphaTarget(0.3).restart();
            d.fx = d.x;
            d.fy = d.y;
        }}
        
        function dragged(event, d) {{
            d.fx = event.x;
            d.fy = event.y;
        }}
        
        function dragended(event, d) {{
            if (!event.active) simulation.alphaTarget(0);
            d.fx = null;
            d.fy = null;
        }}
        
        function resetZoom() {{
            svg.transition().duration(750).call(zoom.transform, d3.zoomIdentity);
        }}
        
        let labelsVisible = true;
        function toggleLabels() {{
            labelsVisible = !labelsVisible;
            labels.style("opacity", labelsVisible ? 1 : 0);
        }}
        
        function filterByType() {{
            const selectedType = document.getElementById("typeFilter").value;
            
            node.style("opacity", d => {{
                return selectedType === "all" || d.concept_type === selectedType ? 1 : 0.2;
            }});
            
            labels.style("opacity", d => {{
                const typeVisible = selectedType === "all" || d.concept_type === selectedType;
                return typeVisible && labelsVisible ? 1 : 0;
            }});
        }}
    </script>
</body>
</html>
        """

        # Convert concept map to JSON
        data_json = json.dumps({
            "nodes": [asdict(node) for node in concept_map.nodes],
            "edges": [asdict(edge) for edge in concept_map.edges],
            "metadata": concept_map.metadata
        }, default=str)

        # Fill template
        html_content = html_template.format(data_json=data_json)

        # Write to file
        output_file = Path(output_path)
        output_file.write_text(html_content)

        logger.info(f"Concept map exported to {output_file.absolute()}")
        return str(output_file.absolute())

    async def export_temporal_flow_html(self, evolution_id: str,
                                      output_path: str = "temporal_flow.html") -> str:
        """Export temporal flow as interactive HTML timeline."""

        timeline_data = await self.create_temporal_flow_map(evolution_id)

        html_template = """
<!DOCTYPE html>
<html>
<head>
    <title>Idea Evolution Timeline</title>
    <script src="https://d3js.org/d3.v7.min.js"></script>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 0; padding: 20px; }}
        .timeline {{ margin: 20px 0; }}
        .timeline-item {{ margin: 10px 0; padding: 10px; border-left: 3px solid #3498db; background: #f8f9fa; }}
        .platform-notion {{ border-left-color: #000000; }}
        .platform-linkedin {{ border-left-color: #0077B5; }}
        .timestamp {{ font-size: 12px; color: #666; }}
        .stage {{ display: inline-block; padding: 2px 8px; border-radius: 12px; font-size: 10px; background: #e9ecef; margin: 2px; }}
        .engagement {{ margin-top: 10px; }}
    </style>
</head>
<body>
    <h1>📈 Idea Evolution Timeline</h1>
    <h2>Evolution: {evolution_id}</h2>
    
    <div class="timeline" id="timeline"></div>
    
    <script>
        const timelineData = {timeline_json};
        
        const timeline = d3.select("#timeline");
        
        timelineData.timeline.forEach(item => {{
            const div = timeline.append("div")
                .attr("class", `timeline-item platform-${{item.platform}}`);
            
            div.append("div")
                .attr("class", "timestamp")
                .text(new Date(item.timestamp).toLocaleString());
            
            div.append("div")
                .attr("class", "stage")
                .text(item.stage);
            
            div.append("h4")
                .text(item.concept_name);
            
            if (item.content_snippet) {{
                div.append("p")
                    .text(item.content_snippet);
            }}
            
            if (Object.keys(item.engagement_metrics).length > 0) {{
                const engagement = div.append("div")
                    .attr("class", "engagement");
                
                engagement.append("strong").text("Engagement: ");
                
                Object.entries(item.engagement_metrics).forEach(([key, value]) => {{
                    engagement.append("span")
                        .text(`${{key}}: ${{value}} `);
                }});
            }}
        }});
    </script>
</body>
</html>
        """

        timeline_json = json.dumps(timeline_data, default=str)
        html_content = html_template.format(
            evolution_id=evolution_id,
            timeline_json=timeline_json
        )

        output_file = Path(output_path)
        output_file.write_text(html_content)

        logger.info(f"Temporal flow exported to {output_file.absolute()}")
        return str(output_file.absolute())
