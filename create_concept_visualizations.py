#!/usr/bin/env python3
"""
Create comprehensive interactive concept maps and visualizations based on all our analysis.

This script uses Synapse's ConceptMapper to create visual representations of:
- Professional concepts and relationships from LinkedIn analysis
- Business strategy patterns from technical documents  
- Cross-platform content correlations
- Knowledge management frameworks
"""

import asyncio
import json
import logging
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class AnalysisData:
    """Container for analysis data from various sources."""
    professional_journey: Dict[str, Any]
    content_strategy: Dict[str, Any]
    business_intelligence: Dict[str, Any]
    cross_platform_correlations: Dict[str, Any]
    knowledge_graph_stats: Dict[str, Any]


@dataclass
class ConceptNode:
    """Enhanced node representation for concept visualization."""
    id: str
    label: str
    concept_type: str
    platform: str
    size: float
    color: str
    x: float = 0.0
    y: float = 0.0
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


@dataclass
class ConceptEdge:
    """Enhanced edge representation for concept relationships."""
    source: str
    target: str
    relationship_type: str
    weight: float
    color: str
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class ComprehensiveConceptMapper:
    """Service for creating comprehensive concept maps from analysis data."""
    
    def __init__(self):
        self.color_schemes = {
            # Concept types
            "STRATEGY": "#FF6B6B",
            "INNOVATION": "#4ECDC4", 
            "PROCESS": "#45B7D1",
            "INSIGHT": "#96CEB4",
            "ENGAGEMENT": "#FFEAA7",
            "KNOWLEDGE": "#DDA0DD",
            "TECHNICAL": "#A29BFE",
            "BUSINESS": "#FD79A8",
            "CAREER": "#FDCB6E",
            "NETWORK": "#6C5CE7",
            
            # Platforms
            "linkedin": "#0077B5",
            "notion": "#000000",
            "blog": "#FF5722",
            "synapse": "#74B9FF",
            "github": "#24292e",
            
            # Relationships
            "BUILDS_UPON": "#2ecc71",
            "INFLUENCES": "#f39c12",
            "CORRELATES": "#1abc9c",
            "ENABLES": "#9b59b6",
            "EVOLVES_TO": "#3498db",
            
            "default": "#95A5A6"
        }
    
    async def load_analysis_data(self) -> AnalysisData:
        """Load analysis data from various sources."""
        logger.info("Loading analysis data...")
        
        # Load LinkedIn analysis summary
        linkedin_analysis = await self._load_text_file("docs/analysis/LINKEDIN_ANALYSIS_SUMMARY.md")
        
        # Load content strategy analysis
        content_strategy = await self._load_text_file("docs/analysis/CONTENT_STRATEGY_PLATFORM_COMPLETE.md")
        
        # Load comprehensive intelligence data
        intelligence_data = await self._load_json_file("visualizations/comprehensive_intelligence.json")
        
        # Extract key data points
        professional_journey = {
            "career_stages": [
                {"stage": "Individual Contributor", "years": "2009-2013", "focus": "Full-stack development"},
                {"stage": "Technical Leader", "years": "2014-2018", "focus": "Team leadership, architecture"},
                {"stage": "Fractional CTO", "years": "2019-2024", "focus": "Strategic guidance, scaling"},
                {"stage": "Platform Creator", "years": "2024+", "focus": "Synapse development, content strategy"}
            ],
            "technologies": ["Python", "Node.js", "React", "AWS", "Docker", "Kubernetes", "PostgreSQL", "Redis"],
            "industries": ["Gaming (Ubisoft)", "Healthcare (Specta.AI)", "Fintech (BVNK)", "IoT (Arnia Software)"]
        }
        
        content_strategy_data = {
            "content_evolution": [
                {"phase": "Personal Experience", "content": "Career stories and technical challenges"},
                {"phase": "LinkedIn Insights", "content": "Technical architecture debates, industry commentary"},
                {"phase": "Platform Capabilities", "content": "Synapse development, knowledge management"},
                {"phase": "Business Intelligence", "content": "Strategic analysis, market insights"}
            ],
            "engagement_patterns": {
                "high_engagement": ["Technical Architecture Debates", "Business-Technical Integration"],
                "optimal_timing": "6:30-7:00 AM",
                "best_formats": ["Architecture decisions", "Technical depth with business context"]
            }
        }
        
        cross_platform_data = {
            "platform_relationships": [
                {"source": "LinkedIn", "target": "Notion", "type": "draft_to_structured"},
                {"source": "Notion", "target": "Blog", "type": "research_to_publication"},
                {"source": "Blog", "target": "Synapse", "type": "content_to_knowledge"},
                {"source": "Synapse", "target": "Business Intelligence", "type": "data_to_insights"}
            ]
        }
        
        return AnalysisData(
            professional_journey=professional_journey,
            content_strategy=content_strategy_data,
            business_intelligence=intelligence_data,
            cross_platform_correlations=cross_platform_data,
            knowledge_graph_stats={
                "total_entities": 483,
                "total_relationships": 2399,
                "relationship_types": ["MENTIONS", "CONTAINS", "MENTIONS_TOPIC", "HAS_TOPIC"]
            }
        )
    
    async def _load_text_file(self, file_path: str) -> str:
        """Load text file content."""
        try:
            path = Path(file_path)
            if path.exists():
                return path.read_text()
            return ""
        except Exception as e:
            logger.warning(f"Could not load {file_path}: {e}")
            return ""
    
    async def _load_json_file(self, file_path: str) -> Dict[str, Any]:
        """Load JSON file content."""
        try:
            path = Path(file_path)
            if path.exists():
                return json.loads(path.read_text())
            return {}
        except Exception as e:
            logger.warning(f"Could not load {file_path}: {e}")
            return {}
    
    async def create_main_concept_network(self, data: AnalysisData) -> Dict[str, Any]:
        """Create the main concept network visualization."""
        logger.info("Creating main concept network...")
        
        nodes = []
        edges = []
        
        # Create nodes for key concepts
        concept_id = 0
        
        # Professional journey concepts
        for stage in data.professional_journey["career_stages"]:
            concept_id += 1
            nodes.append(ConceptNode(
                id=f"career_{concept_id}",
                label=stage["stage"],
                concept_type="CAREER",
                platform="linkedin",
                size=40,
                color=self.color_schemes["CAREER"],
                metadata={
                    "years": stage["years"],
                    "focus": stage["focus"],
                    "category": "professional_development"
                }
            ))
        
        # Technology concepts
        for tech in data.professional_journey["technologies"]:
            concept_id += 1
            nodes.append(ConceptNode(
                id=f"tech_{concept_id}",
                label=tech,
                concept_type="TECHNICAL",
                platform="github",
                size=25,
                color=self.color_schemes["TECHNICAL"],
                metadata={"category": "technology"}
            ))
        
        # Content strategy concepts
        for phase in data.content_strategy["content_evolution"]:
            concept_id += 1
            nodes.append(ConceptNode(
                id=f"content_{concept_id}",
                label=phase["phase"],
                concept_type="STRATEGY",
                platform="synapse",
                size=35,
                color=self.color_schemes["STRATEGY"],
                metadata={
                    "content": phase["content"],
                    "category": "content_strategy"
                }
            ))
        
        # Business intelligence concepts
        business_concepts = [
            {"name": "Market Analysis", "type": "INSIGHT"},
            {"name": "Competitive Intelligence", "type": "STRATEGY"},
            {"name": "Network Growth", "type": "ENGAGEMENT"},
            {"name": "Knowledge Management", "type": "PROCESS"}
        ]
        
        for concept in business_concepts:
            concept_id += 1
            nodes.append(ConceptNode(
                id=f"business_{concept_id}",
                label=concept["name"],
                concept_type=concept["type"],
                platform="synapse",
                size=30,
                color=self.color_schemes[concept["type"]],
                metadata={"category": "business_intelligence"}
            ))
        
        # Create relationships between concepts
        edge_id = 0
        
        # Career progression relationships
        career_nodes = [n for n in nodes if n.concept_type == "CAREER"]
        for i in range(len(career_nodes) - 1):
            edge_id += 1
            edges.append(ConceptEdge(
                source=career_nodes[i].id,
                target=career_nodes[i + 1].id,
                relationship_type="EVOLVES_TO",
                weight=3.0,
                color=self.color_schemes["EVOLVES_TO"],
                metadata={"type": "temporal_progression"}
            ))
        
        # Content evolution relationships
        content_nodes = [n for n in nodes if n.concept_type == "STRATEGY"]
        for i in range(len(content_nodes) - 1):
            edge_id += 1
            edges.append(ConceptEdge(
                source=content_nodes[i].id,
                target=content_nodes[i + 1].id,
                relationship_type="BUILDS_UPON",
                weight=2.5,
                color=self.color_schemes["BUILDS_UPON"],
                metadata={"type": "content_evolution"}
            ))
        
        # Cross-category relationships
        if career_nodes and content_nodes:
            edge_id += 1
            edges.append(ConceptEdge(
                source=career_nodes[-1].id,  # Latest career stage
                target=content_nodes[0].id,   # First content phase
                relationship_type="INFLUENCES",
                weight=2.0,
                color=self.color_schemes["INFLUENCES"],
                metadata={"type": "experience_to_content"}
            ))
        
        return {
            "nodes": [asdict(node) for node in nodes],
            "edges": [asdict(edge) for edge in edges],
            "metadata": {
                "title": "Synapse Concept Network",
                "description": "Interactive visualization of professional concepts and relationships",
                "node_count": len(nodes),
                "edge_count": len(edges),
                "created_at": datetime.now().isoformat()
            }
        }
    
    async def create_professional_journey_flow(self, data: AnalysisData) -> Dict[str, Any]:
        """Create professional journey flow visualization."""
        logger.info("Creating professional journey flow...")
        
        timeline_data = {
            "title": "Professional Development Journey",
            "subtitle": "Individual contributor → Technical Leader → Fractional CTO → Platform Creator",
            "timeline": [],
            "milestones": [],
            "skills_evolution": []
        }
        
        # Career stages timeline
        for i, stage in enumerate(data.professional_journey["career_stages"]):
            timeline_data["timeline"].append({
                "index": i,
                "stage": stage["stage"],
                "years": stage["years"],
                "focus": stage["focus"],
                "x": i * 200 + 100,
                "y": 150,
                "color": self.color_schemes["CAREER"]
            })
        
        # Key milestones
        milestones = [
            {"year": "2013", "event": "Led first development team", "impact": "Team leadership skills"},
            {"year": "2016", "event": "Architected microservices platform", "impact": "System design expertise"},
            {"year": "2019", "event": "First fractional CTO role", "impact": "Strategic consulting"},
            {"year": "2024", "event": "Launched Synapse platform", "impact": "Product development"}
        ]
        
        timeline_data["milestones"] = milestones
        
        # Skills evolution over time
        skills_by_period = {
            "2009-2013": ["Python", "JavaScript", "SQL", "Web Development"],
            "2014-2018": ["System Architecture", "Team Leadership", "AWS", "Docker"],
            "2019-2023": ["Strategic Planning", "Due Diligence", "Scaling", "Product Strategy"],
            "2024+": ["AI/ML", "Knowledge Graphs", "Content Strategy", "Platform Development"]
        }
        
        timeline_data["skills_evolution"] = skills_by_period
        
        return timeline_data
    
    async def create_cross_platform_correlations(self, data: AnalysisData) -> Dict[str, Any]:
        """Create cross-platform correlation network."""
        logger.info("Creating cross-platform correlations...")
        
        platforms = ["LinkedIn", "Notion", "Blog", "Synapse", "GitHub"]
        
        nodes = []
        for i, platform in enumerate(platforms):
            nodes.append({
                "id": platform.lower(),
                "label": platform,
                "type": "platform",
                "size": 50,
                "color": self.color_schemes.get(platform.lower(), self.color_schemes["default"]),
                "x": (i % 3) * 200 + 100,
                "y": (i // 3) * 150 + 100
            })
        
        # Add content type nodes
        content_types = [
            {"name": "Technical Posts", "platform": "linkedin"},
            {"name": "Research Notes", "platform": "notion"},
            {"name": "Published Articles", "platform": "blog"},
            {"name": "Knowledge Base", "platform": "synapse"},
            {"name": "Code Examples", "platform": "github"}
        ]
        
        for content in content_types:
            nodes.append({
                "id": content["name"].lower().replace(" ", "_"),
                "label": content["name"],
                "type": "content",
                "size": 30,
                "color": self.color_schemes["KNOWLEDGE"],
                "platform": content["platform"]
            })
        
        # Create relationships
        edges = []
        correlations = data.cross_platform_correlations["platform_relationships"]
        
        for i, correlation in enumerate(correlations):
            edges.append({
                "source": correlation["source"].lower(),
                "target": correlation["target"].lower(),
                "type": correlation["type"],
                "weight": 2.0,
                "color": self.color_schemes["CORRELATES"]
            })
        
        return {
            "nodes": nodes,
            "edges": edges,
            "metadata": {
                "title": "Cross-Platform Content Correlations",
                "description": "Flow of content and ideas across platforms",
                "platform_count": len(platforms),
                "correlation_count": len(correlations)
            }
        }
    
    async def create_strategic_insights_network(self, data: AnalysisData) -> Dict[str, Any]:
        """Create strategic insights relationship map."""
        logger.info("Creating strategic insights network...")
        
        insights = [
            {"name": "Technical Leadership Authenticity", "type": "INSIGHT", "strength": 5},
            {"name": "High-Engagement Content Patterns", "type": "STRATEGY", "strength": 4},
            {"name": "Network Composition Intelligence", "type": "KNOWLEDGE", "strength": 4},
            {"name": "Content Strategy Optimization", "type": "PROCESS", "strength": 5},
            {"name": "Business Development Pipeline", "type": "BUSINESS", "strength": 3},
            {"name": "Market Differentiation", "type": "STRATEGY", "strength": 4},
            {"name": "Technology Ecosystem Position", "type": "TECHNICAL", "strength": 4},
            {"name": "Fractional CTO Positioning", "type": "BUSINESS", "strength": 5}
        ]
        
        nodes = []
        for i, insight in enumerate(insights):
            nodes.append({
                "id": f"insight_{i}",
                "label": insight["name"],
                "type": insight["type"],
                "size": insight["strength"] * 10,
                "color": self.color_schemes[insight["type"]],
                "strength": insight["strength"]
            })
        
        # Create strategic relationships
        edges = []
        strategic_relationships = [
            (0, 1, "ENABLES"),      # Technical auth enables content patterns
            (1, 2, "INFLUENCES"),   # Content patterns influence network
            (2, 3, "BUILDS_UPON"),  # Network intelligence builds content strategy
            (3, 4, "ENABLES"),      # Content strategy enables business dev
            (0, 7, "ENABLES"),      # Technical auth enables CTO positioning
            (4, 5, "BUILDS_UPON"),  # Business dev builds differentiation
            (6, 0, "INFLUENCES"),   # Ecosystem position influences tech auth
            (7, 5, "ENABLES")       # CTO positioning enables differentiation
        ]
        
        for source_idx, target_idx, relationship_type in strategic_relationships:
            edges.append({
                "source": f"insight_{source_idx}",
                "target": f"insight_{target_idx}",
                "type": relationship_type,
                "weight": 2.0,
                "color": self.color_schemes[relationship_type]
            })
        
        return {
            "nodes": nodes,
            "edges": edges,
            "metadata": {
                "title": "Strategic Insights Network",
                "description": "Relationships between key strategic insights and business opportunities",
                "insight_count": len(insights),
                "relationship_count": len(edges)
            }
        }
    
    async def export_html_visualization(self, data: Dict[str, Any], 
                                      output_path: str, 
                                      title: str,
                                      description: str = "") -> str:
        """Export visualization as interactive HTML."""
        
        html_template = """
<!DOCTYPE html>
<html>
<head>
    <title>{title}</title>
    <script src="https://d3js.org/d3.v7.min.js"></script>
    <style>
        body {{ 
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; 
            margin: 0; 
            padding: 20px; 
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
        }}
        .container {{ 
            max-width: 1400px; 
            margin: 0 auto; 
            background: white; 
            border-radius: 12px; 
            box-shadow: 0 10px 30px rgba(0,0,0,0.2);
            padding: 30px;
        }}
        .header {{
            text-align: center;
            margin-bottom: 30px;
            padding-bottom: 20px;
            border-bottom: 2px solid #eee;
        }}
        .header h1 {{
            color: #2c3e50;
            margin: 0;
            font-size: 2.5em;
            font-weight: 300;
        }}
        .header p {{
            color: #7f8c8d;
            font-size: 1.1em;
            margin: 10px 0 0 0;
        }}
        .controls {{ 
            margin-bottom: 20px; 
            display: flex;
            gap: 15px;
            align-items: center;
            flex-wrap: wrap;
        }}
        .control-group {{
            display: flex;
            align-items: center;
            gap: 10px;
        }}
        .btn {{
            background: #3498db;
            color: white;
            border: none;
            padding: 8px 16px;
            border-radius: 5px;
            cursor: pointer;
            transition: all 0.3s ease;
        }}
        .btn:hover {{
            background: #2980b9;
            transform: translateY(-1px);
        }}
        .select {{
            padding: 8px 12px;
            border: 1px solid #ddd;
            border-radius: 5px;
            background: white;
        }}
        .map-container {{ 
            border: 2px solid #ecf0f1; 
            border-radius: 8px; 
            background: #fafafa;
        }}
        .tooltip {{ 
            position: absolute; 
            padding: 15px; 
            background: rgba(44, 62, 80, 0.95); 
            color: white; 
            border-radius: 8px; 
            pointer-events: none; 
            font-size: 13px;
            line-height: 1.4;
            max-width: 300px;
            box-shadow: 0 5px 15px rgba(0,0,0,0.3);
        }}
        .legend {{ 
            position: absolute;
            top: 100px;
            right: 30px;
            width: 250px; 
            padding: 20px; 
            background: rgba(255,255,255,0.95); 
            border-radius: 8px; 
            border: 1px solid #ddd;
            box-shadow: 0 3px 10px rgba(0,0,0,0.1);
        }}
        .legend h3 {{
            margin: 0 0 15px 0;
            color: #2c3e50;
            font-size: 16px;
        }}
        .legend-item {{
            display: flex;
            align-items: center;
            margin: 8px 0;
            font-size: 12px;
        }}
        .legend-color {{
            width: 12px;
            height: 12px;
            border-radius: 50%;
            margin-right: 8px;
        }}
        .node {{ cursor: pointer; transition: all 0.3s ease; }}
        .node:hover {{ stroke: #2c3e50; stroke-width: 3px; }}
        .link {{ stroke-opacity: 0.6; transition: all 0.3s ease; }}
        .selected {{ stroke: #e74c3c; stroke-width: 4px; }}
        .stats {{
            display: flex;
            justify-content: space-around;
            margin: 20px 0;
            padding: 15px;
            background: #ecf0f1;
            border-radius: 8px;
        }}
        .stat {{
            text-align: center;
        }}
        .stat-number {{
            font-size: 24px;
            font-weight: bold;
            color: #2c3e50;
        }}
        .stat-label {{
            font-size: 12px;
            color: #7f8c8d;
            text-transform: uppercase;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🧠 {title}</h1>
            <p>{description}</p>
        </div>
        
        <div class="stats">
            <div class="stat">
                <div class="stat-number" id="nodeCount">0</div>
                <div class="stat-label">Concepts</div>
            </div>
            <div class="stat">
                <div class="stat-number" id="edgeCount">0</div>
                <div class="stat-label">Relationships</div>
            </div>
            <div class="stat">
                <div class="stat-number" id="selectedCount">0</div>
                <div class="stat-label">Selected</div>
            </div>
        </div>
        
        <div class="controls">
            <div class="control-group">
                <button class="btn" onclick="resetZoom()">🔍 Reset View</button>
                <button class="btn" onclick="toggleLabels()">🏷️ Toggle Labels</button>
                <button class="btn" onclick="centerGraph()">🎯 Center Graph</button>
            </div>
            <div class="control-group">
                <label>Filter by type:</label>
                <select class="select" id="typeFilter" onchange="filterByType()">
                    <option value="all">All Types</option>
                </select>
            </div>
            <div class="control-group">
                <label>Layout:</label>
                <select class="select" id="layoutSelect" onchange="changeLayout()">
                    <option value="force">Force-Directed</option>
                    <option value="circular">Circular</option>
                    <option value="hierarchical">Hierarchical</option>
                </select>
            </div>
        </div>
        
        <div class="legend">
            <h3>Legend</h3>
            <div><strong>Node Size:</strong> Concept importance</div>
            <div><strong>Edge Width:</strong> Relationship strength</div>
            <div style="margin: 10px 0;"><strong>Concept Types:</strong></div>
            <div id="legendItems"></div>
        </div>
        
        <svg class="map-container" width="1000" height="700"></svg>
    </div>
    
    <div class="tooltip" style="opacity: 0;"></div>
    
    <script>
        const data = {data_json};
        
        // Update stats
        document.getElementById('nodeCount').textContent = data.nodes.length;
        document.getElementById('edgeCount').textContent = data.edges.length;
        
        // Populate type filter
        const types = [...new Set(data.nodes.map(n => n.concept_type || n.type))];
        const typeFilter = document.getElementById('typeFilter');
        types.forEach(type => {{
            if (type) {{
                const option = document.createElement('option');
                option.value = type;
                option.textContent = type;
                typeFilter.appendChild(option);
            }}
        }});
        
        // Populate legend
        const legendItems = document.getElementById('legendItems');
        types.forEach(type => {{
            if (type) {{
                const node = data.nodes.find(n => (n.concept_type || n.type) === type);
                if (node) {{
                    const item = document.createElement('div');
                    item.className = 'legend-item';
                    item.innerHTML = `<div class="legend-color" style="background-color: ${{node.color}}"></div>${{type}}`;
                    legendItems.appendChild(item);
                }}
            }}
        }});
        
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
        let simulation = d3.forceSimulation()
            .force("link", d3.forceLink().id(d => d.id).distance(100))
            .force("charge", d3.forceManyBody().strength(-300))
            .force("center", d3.forceCenter(width / 2, height / 2))
            .force("collision", d3.forceCollide().radius(d => (d.size || 20) / 2 + 5));
        
        let link, node, labels;
        
        function initGraph() {{
            // Create links
            link = g.append("g")
                .attr("class", "links")
                .selectAll("line")
                .data(data.edges)
                .enter().append("line")
                .attr("class", "link")
                .attr("stroke", d => d.color)
                .attr("stroke-width", d => Math.max(1, (d.weight || 1) * 2))
                .attr("marker-end", "url(#arrowhead)");
            
            // Add arrow markers
            svg.append("defs").append("marker")
                .attr("id", "arrowhead")
                .attr("viewBox", "0 -5 10 10")
                .attr("refX", 15)
                .attr("refY", 0)
                .attr("markerWidth", 6)
                .attr("markerHeight", 6)
                .attr("orient", "auto")
                .append("path")
                .attr("d", "M0,-5L10,0L0,5")
                .attr("fill", "#999");
            
            // Create nodes
            node = g.append("g")
                .attr("class", "nodes")
                .selectAll("circle")
                .data(data.nodes)
                .enter().append("circle")
                .attr("class", "node")
                .attr("r", d => (d.size || 20) / 2)
                .attr("fill", d => d.color)
                .call(d3.drag()
                    .on("start", dragstarted)
                    .on("drag", dragged)
                    .on("end", dragended));
            
            // Add labels
            labels = g.append("g")
                .attr("class", "labels")
                .selectAll("text")
                .data(data.nodes)
                .enter().append("text")
                .text(d => d.label)
                .attr("font-size", "11px")
                .attr("font-weight", "500")
                .attr("dx", d => (d.size || 20) / 2 + 5)
                .attr("dy", 4)
                .attr("fill", "#2c3e50");
            
            // Add tooltips
            const tooltip = d3.select(".tooltip");
            
            node.on("mouseover", function(event, d) {{
                tooltip.transition().duration(200).style("opacity", .9);
                let tooltipContent = `<strong>${{d.label}}</strong><br/>`;
                if (d.concept_type) tooltipContent += `Type: ${{d.concept_type}}<br/>`;
                if (d.platform) tooltipContent += `Platform: ${{d.platform}}<br/>`;
                if (d.metadata) {{
                    Object.entries(d.metadata).forEach(([key, value]) => {{
                        if (key !== 'category' && value && typeof value === 'string' && value.length < 100) {{
                            tooltipContent += `${{key}}: ${{value}}<br/>`;
                        }}
                    }});
                }}
                
                tooltip.html(tooltipContent)
                    .style("left", (event.pageX + 10) + "px")
                    .style("top", (event.pageY - 28) + "px");
            }})
            .on("mouseout", function(d) {{
                tooltip.transition().duration(500).style("opacity", 0);
            }})
            .on("click", function(event, d) {{
                d3.select(this).classed("selected", !d3.select(this).classed("selected"));
                updateSelectedCount();
            }});
            
            // Start simulation
            simulation
                .nodes(data.nodes)
                .on("tick", ticked);
            
            simulation.force("link")
                .links(data.edges);
        }}
        
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
        
        function centerGraph() {{
            const bounds = g.node().getBBox();
            const centerX = bounds.x + bounds.width / 2;
            const centerY = bounds.y + bounds.height / 2;
            const scale = 0.8 / Math.max(bounds.width / width, bounds.height / height);
            const transform = d3.zoomIdentity
                .translate(width / 2 - scale * centerX, height / 2 - scale * centerY)
                .scale(scale);
            svg.transition().duration(750).call(zoom.transform, transform);
        }}
        
        let labelsVisible = true;
        function toggleLabels() {{
            labelsVisible = !labelsVisible;
            labels.style("opacity", labelsVisible ? 1 : 0);
        }}
        
        function filterByType() {{
            const selectedType = document.getElementById("typeFilter").value;
            
            node.style("opacity", d => {{
                return selectedType === "all" || (d.concept_type || d.type) === selectedType ? 1 : 0.2;
            }});
            
            labels.style("opacity", d => {{
                const typeVisible = selectedType === "all" || (d.concept_type || d.type) === selectedType;
                return typeVisible && labelsVisible ? 1 : 0;
            }});
            
            link.style("opacity", d => {{
                const sourceVisible = selectedType === "all" || (d.source.concept_type || d.source.type) === selectedType;
                const targetVisible = selectedType === "all" || (d.target.concept_type || d.target.type) === selectedType;
                return sourceVisible && targetVisible ? 0.6 : 0.1;
            }});
        }}
        
        function changeLayout() {{
            const layout = document.getElementById("layoutSelect").value;
            
            if (layout === "circular") {{
                const radius = Math.min(width, height) / 3;
                const angleStep = (2 * Math.PI) / data.nodes.length;
                
                data.nodes.forEach((d, i) => {{
                    const angle = i * angleStep;
                    d.fx = width / 2 + radius * Math.cos(angle);
                    d.fy = height / 2 + radius * Math.sin(angle);
                }});
            }} else if (layout === "hierarchical") {{
                // Simple hierarchical layout
                const levels = {{}};
                data.nodes.forEach(d => {{
                    const level = d.metadata?.category || 'default';
                    if (!levels[level]) levels[level] = [];
                    levels[level].push(d);
                }});
                
                Object.keys(levels).forEach((level, levelIndex) => {{
                    const nodesInLevel = levels[level];
                    const y = (levelIndex + 1) * (height / (Object.keys(levels).length + 1));
                    nodesInLevel.forEach((d, nodeIndex) => {{
                        d.fx = (nodeIndex + 1) * (width / (nodesInLevel.length + 1));
                        d.fy = y;
                    }});
                }});
            }} else {{
                // Force-directed (remove fixed positions)
                data.nodes.forEach(d => {{
                    d.fx = null;
                    d.fy = null;
                }});
            }}
            
            simulation.alpha(1).restart();
        }}
        
        function updateSelectedCount() {{
            const selected = node.filter(function() {{ return d3.select(this).classed("selected"); }});
            document.getElementById('selectedCount').textContent = selected.size();
        }}
        
        // Initialize graph
        initGraph();
        
        // Auto-center after initial layout
        setTimeout(() => {{
            centerGraph();
        }}, 2000);
    </script>
</body>
</html>
        """
        
        data_json = json.dumps(data, default=str, indent=2)
        html_content = html_template.format(
            title=title,
            description=description,
            data_json=data_json
        )
        
        output_file = Path(output_path)
        output_file.write_text(html_content)
        
        logger.info(f"Visualization exported to {output_file.absolute()}")
        return str(output_file.absolute())


async def main():
    """Main function to create all visualizations."""
    logger.info("Starting comprehensive concept visualization creation...")
    
    # Initialize mapper and load data
    mapper = ComprehensiveConceptMapper()
    data = await mapper.load_analysis_data()
    
    # Create output directory
    output_dir = Path("visualizations")
    output_dir.mkdir(exist_ok=True)
    
    # 1. Main concept network
    logger.info("Creating main concept network...")
    concept_network = await mapper.create_main_concept_network(data)
    concept_map_path = await mapper.export_html_visualization(
        concept_network,
        "visualizations/synapse_concept_map.html",
        "Synapse Concept Network",
        "Interactive visualization of professional concepts and strategic relationships"
    )
    
    # 2. Professional journey flow
    logger.info("Creating professional journey flow...")
    journey_data = await mapper.create_professional_journey_flow(data)
    
    # Convert timeline data to nodes/edges format for visualization
    journey_viz = {
        "nodes": journey_data["timeline"],
        "edges": [
            {
                "source": journey_data["timeline"][i]["index"],
                "target": journey_data["timeline"][i+1]["index"],
                "type": "EVOLVES_TO",
                "weight": 2.0,
                "color": "#3498db"
            } for i in range(len(journey_data["timeline"]) - 1)
        ],
        "metadata": {
            "title": "Professional Development Journey",
            "skills_evolution": journey_data["skills_evolution"]
        }
    }
    
    journey_path = await mapper.export_html_visualization(
        journey_viz,
        "visualizations/professional_journey_flow.html", 
        "Professional Development Journey",
        "Career progression from Individual Contributor to Platform Creator"
    )
    
    # 3. Cross-platform correlations
    logger.info("Creating cross-platform correlations...")
    correlation_data = await mapper.create_cross_platform_correlations(data)
    correlation_path = await mapper.export_html_visualization(
        correlation_data,
        "visualizations/cross_platform_correlations.html",
        "Cross-Platform Content Correlations", 
        "Flow of content and ideas across LinkedIn, Notion, Blog, Synapse, and GitHub"
    )
    
    # 4. Strategic insights network
    logger.info("Creating strategic insights network...")
    insights_data = await mapper.create_strategic_insights_network(data)
    insights_path = await mapper.export_html_visualization(
        insights_data,
        "visualizations/strategic_insights_network.html",
        "Strategic Insights Network",
        "Relationships between key strategic insights and business opportunities"
    )
    
    # Create summary report
    summary = {
        "created_at": datetime.now().isoformat(),
        "visualizations": [
            {
                "name": "Synapse Concept Map",
                "file": concept_map_path,
                "description": "Main concept network showing professional and strategic relationships",
                "nodes": len(concept_network["nodes"]),
                "edges": len(concept_network["edges"])
            },
            {
                "name": "Professional Journey Flow", 
                "file": journey_path,
                "description": "Career progression timeline with skills evolution",
                "stages": len(journey_data["timeline"]),
                "skill_periods": len(journey_data["skills_evolution"])
            },
            {
                "name": "Cross-Platform Correlations",
                "file": correlation_path, 
                "description": "Content flow between platforms",
                "platforms": len(correlation_data["nodes"]),
                "correlations": len(correlation_data["edges"])
            },
            {
                "name": "Strategic Insights Network",
                "file": insights_path,
                "description": "Business strategy and opportunity relationships", 
                "insights": len(insights_data["nodes"]),
                "relationships": len(insights_data["edges"])
            }
        ],
        "total_concepts": sum(len(viz["visualizations"][i]["nodes"]) if i < 2 else viz["visualizations"][i].get("stages", 0) + viz["visualizations"][i].get("platforms", 0) for i, viz in enumerate([{"visualizations": [{"nodes": concept_network["nodes"]}, {"nodes": journey_viz["nodes"]}, {"platforms": len(correlation_data["nodes"])}, {"insights": len(insights_data["nodes"])}]}])),
        "features": [
            "Interactive node manipulation and filtering",
            "Concept type color coding", 
            "Relationship strength visualization",
            "Zoom and pan capabilities",
            "Multiple layout algorithms",
            "Real-time statistics",
            "Responsive design"
        ]
    }
    
    summary_path = output_dir / "visualization_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2))
    
    logger.info("\\n🎉 Comprehensive concept visualizations created successfully!")
    logger.info(f"📊 Generated {len(summary['visualizations'])} interactive HTML visualizations")
    logger.info(f"📁 Output directory: {output_dir.absolute()}")
    logger.info(f"📋 Summary report: {summary_path.absolute()}")
    
    return summary


if __name__ == "__main__":
    asyncio.run(main())