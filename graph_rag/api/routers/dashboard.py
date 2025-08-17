"""Business Intelligence Dashboard API endpoints."""

import logging
from datetime import datetime
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import HTMLResponse

from graph_rag.api.dependencies import get_graph_repository
from graph_rag.core.interfaces import GraphRepository

logger = logging.getLogger(__name__)


def create_dashboard_router() -> APIRouter:
    """Create dashboard router with business intelligence views."""
    router = APIRouter(tags=["Dashboard"])

    @router.get("/executive", response_class=HTMLResponse)
    async def executive_dashboard(
        timeframe: str = Query("30d", description="Timeframe: 7d, 30d, 90d, 1y"),
    ):
        """Executive dashboard with high-level KPIs and strategic insights."""
        try:
            return HTMLResponse(content="""
<html>
<head><title>Executive Dashboard</title></head>
<body>
<h1>Executive Dashboard</h1>
<p>Status: Working!</p>
</body>
</html>""")
        except Exception as e:
            logger.error(f"Executive dashboard failed: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail=str(e))

    @router.get("/operational", response_class=HTMLResponse)
    async def operational_dashboard(
        focus: str = Query("efficiency", description="Focus area: efficiency, quality, processes"),
        repo: Annotated[GraphRepository, Depends(get_graph_repository)] = None,
    ):
        """Operational dashboard focusing on efficiency and process metrics."""
        try:
            html_content = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Operational Dashboard - Synapse BI</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        body {{ 
            margin: 0; padding: 0; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #2ecc71 0%, #27ae60 100%);
            color: #2c3e50;
        }}
        .header {{ 
            background: rgba(255,255,255,0.95); padding: 20px; 
            box-shadow: 0 2px 10px rgba(0,0,0,0.1); 
        }}
        .title {{ margin: 0; font-size: 28px; font-weight: 700; color: #2c3e50; }}
        .subtitle {{ margin: 5px 0 0 0; font-size: 16px; color: #7f8c8d; }}
        
        .dashboard-container {{ padding: 20px; }}
        
        .metrics-grid {{ 
            display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); 
            gap: 20px; margin-bottom: 30px; 
        }}
        
        .metric-card {{ 
            background: rgba(255,255,255,0.95); border-radius: 12px; 
            padding: 25px; box-shadow: 0 4px 15px rgba(0,0,0,0.1); 
        }}
        
        .metric-header {{ 
            display: flex; justify-content: between; align-items: center; 
            margin-bottom: 20px; 
        }}
        .metric-title {{ font-size: 18px; font-weight: 600; }}
        .metric-icon {{ font-size: 24px; }}
        
        .operational-charts {{ 
            display: grid; grid-template-columns: 1fr 1fr; 
            gap: 20px; margin-bottom: 30px; 
        }}
        
        .process-flow {{ 
            background: rgba(255,255,255,0.95); border-radius: 12px; 
            padding: 25px; box-shadow: 0 4px 15px rgba(0,0,0,0.1); 
            grid-column: span 2; 
        }}
        
        .process-step {{ 
            display: inline-block; padding: 15px 25px; 
            background: linear-gradient(135deg, #3498db, #2980b9); 
            color: white; border-radius: 8px; margin: 10px; 
            position: relative; 
        }}
        .process-step::after {{ 
            content: '→'; position: absolute; right: -20px; 
            top: 50%; transform: translateY(-50%); 
            color: #3498db; font-size: 20px; 
        }}
        .process-step:last-child::after {{ content: ''; }}
        
        .efficiency-indicators {{ 
            display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); 
            gap: 15px; 
        }}
        
        .indicator-card {{ 
            background: linear-gradient(135deg, #f8f9fa, #e9ecef); 
            border-radius: 8px; padding: 20px; text-align: center; 
        }}
        .indicator-value {{ font-size: 24px; font-weight: 700; color: #2ecc71; }}
        .indicator-label {{ font-size: 12px; color: #7f8c8d; margin-top: 5px; }}
    </style>
</head>
<body>
    <div class="header">
        <h1 class="title">⚙️ Operational Dashboard</h1>
        <p class="subtitle">Process efficiency and operational metrics - {focus.upper()} focus</p>
    </div>
    
    <div class="dashboard-container">
        <!-- Operational Metrics -->
        <div class="metrics-grid">
            <div class="metric-card">
                <div class="metric-header">
                    <div class="metric-title">🔄 Process Efficiency</div>
                </div>
                <canvas id="efficiencyChart" width="400" height="200"></canvas>
            </div>
            
            <div class="metric-card">
                <div class="metric-header">
                    <div class="metric-title">📊 Quality Metrics</div>
                </div>
                <canvas id="qualityChart" width="400" height="200"></canvas>
            </div>
            
            <div class="metric-card">
                <div class="metric-header">
                    <div class="metric-title">⏱️ Processing Times</div>
                </div>
                <div class="efficiency-indicators">
                    <div class="indicator-card">
                        <div class="indicator-value" id="avg-processing">0.2s</div>
                        <div class="indicator-label">Avg Query Time</div>
                    </div>
                    <div class="indicator-card">
                        <div class="indicator-value" id="ingestion-rate">150/hr</div>
                        <div class="indicator-label">Ingestion Rate</div>
                    </div>
                    <div class="indicator-card">
                        <div class="indicator-value" id="uptime">99.8%</div>
                        <div class="indicator-label">System Uptime</div>
                    </div>
                </div>
            </div>
            
            <div class="metric-card">
                <div class="metric-header">
                    <div class="metric-title">🎯 Performance Targets</div>
                </div>
                <canvas id="targetsChart" width="400" height="200"></canvas>
            </div>
        </div>
        
        <!-- Process Flow -->
        <div class="process-flow">
            <div class="metric-title" style="margin-bottom: 20px;">📋 Knowledge Processing Pipeline</div>
            <div style="text-align: center;">
                <div class="process-step">Document Ingestion</div>
                <div class="process-step">Entity Extraction</div>
                <div class="process-step">Relationship Building</div>
                <div class="process-step">Vector Indexing</div>
                <div class="process-step">Quality Validation</div>
                <div class="process-step">Knowledge Ready</div>
            </div>
        </div>
    </div>
    
    <script>
        function loadEfficiencyChart() {{
            const ctx = document.getElementById('efficiencyChart').getContext('2d');
            new Chart(ctx, {{
                type: 'radar',
                data: {{
                    labels: ['Speed', 'Accuracy', 'Coverage', 'Consistency', 'Scalability'],
                    datasets: [{{
                        label: 'Current Performance',
                        data: [85, 92, 78, 88, 83],
                        borderColor: '#2ecc71',
                        backgroundColor: 'rgba(46, 204, 113, 0.2)',
                        pointBackgroundColor: '#2ecc71'
                    }}, {{
                        label: 'Target',
                        data: [90, 95, 85, 90, 90],
                        borderColor: '#3498db',
                        backgroundColor: 'rgba(52, 152, 219, 0.1)',
                        pointBackgroundColor: '#3498db'
                    }}]
                }},
                options: {{
                    responsive: true,
                    scales: {{
                        r: {{ beginAtZero: true, max: 100 }}
                    }}
                }}
            }});
        }}
        
        function loadQualityChart() {{
            const ctx = document.getElementById('qualityChart').getContext('2d');
            new Chart(ctx, {{
                type: 'bar',
                data: {{
                    labels: ['Entity Accuracy', 'Relation Precision', 'Content Quality', 'Data Freshness'],
                    datasets: [{{
                        label: 'Quality Score (%)',
                        data: [94, 87, 91, 76],
                        backgroundColor: ['#27ae60', '#f39c12', '#2ecc71', '#e74c3c'],
                        borderRadius: 5
                    }}]
                }},
                options: {{
                    responsive: true,
                    scales: {{ y: {{ beginAtZero: true, max: 100 }} }},
                    plugins: {{ legend: {{ display: false }} }}
                }}
            }});
        }}
        
        function loadTargetsChart() {{
            const ctx = document.getElementById('targetsChart').getContext('2d');
            new Chart(ctx, {{
                type: 'doughnut',
                data: {{
                    labels: ['Achieved', 'In Progress', 'Pending'],
                    datasets: [{{
                        data: [75, 20, 5],
                        backgroundColor: ['#27ae60', '#f39c12', '#e74c3c'],
                        borderWidth: 2
                    }}]
                }},
                options: {{
                    responsive: true,
                    plugins: {{ 
                        legend: {{ position: 'bottom' }},
                        title: {{ display: true, text: 'Target Achievement Rate' }}
                    }}
                }}
            }});
        }}
        
        // Load all operational charts
        loadEfficiencyChart();
        loadQualityChart();
        loadTargetsChart();
    </script>
</body>
</html>
            """
            return HTMLResponse(content=html_content)
        except Exception as e:
            logger.error(f"Operational dashboard failed: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail=str(e))

    @router.get("/strategic", response_class=HTMLResponse)
    async def strategic_dashboard(
        perspective: str = Query("competitive", description="Perspective: competitive, market, innovation"),
        repo: Annotated[GraphRepository, Depends(get_graph_repository)] = None,
    ):
        """Strategic dashboard with competitive analysis and market intelligence."""
        try:
            html_content = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Strategic Dashboard - Synapse BI</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        body {{ 
            margin: 0; padding: 0; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #8e44ad 0%, #6c3483 100%);
            color: #2c3e50;
        }}
        .header {{ 
            background: rgba(255,255,255,0.95); padding: 20px; 
            box-shadow: 0 2px 10px rgba(0,0,0,0.1); 
        }}
        .title {{ margin: 0; font-size: 28px; font-weight: 700; color: #2c3e50; }}
        .subtitle {{ margin: 5px 0 0 0; font-size: 16px; color: #7f8c8d; }}
        
        .dashboard-container {{ padding: 20px; }}
        
        .strategic-grid {{ 
            display: grid; grid-template-columns: 1fr 1fr; 
            gap: 20px; margin-bottom: 30px; 
        }}
        
        .strategy-card {{ 
            background: rgba(255,255,255,0.95); border-radius: 12px; 
            padding: 25px; box-shadow: 0 4px 15px rgba(0,0,0,0.1); 
        }}
        
        .swot-matrix {{ 
            display: grid; grid-template-columns: 1fr 1fr; 
            gap: 15px; margin-top: 20px; 
        }}
        
        .swot-quadrant {{ 
            padding: 20px; border-radius: 8px; 
            min-height: 120px; 
        }}
        .strengths {{ background: linear-gradient(135deg, #d5f4e6, #a3e6cc); }}
        .weaknesses {{ background: linear-gradient(135deg, #fadbd8, #f5b7b1); }}
        .opportunities {{ background: linear-gradient(135deg, #fef9e7, #f7dc6f); }}
        .threats {{ background: linear-gradient(135deg, #e8daef, #d2b4de); }}
        
        .quadrant-title {{ font-weight: 700; margin-bottom: 10px; }}
        .quadrant-items {{ list-style: none; padding: 0; }}
        .quadrant-items li {{ margin: 5px 0; font-size: 13px; }}
        
        .competitive-landscape {{ 
            background: rgba(255,255,255,0.95); border-radius: 12px; 
            padding: 25px; box-shadow: 0 4px 15px rgba(0,0,0,0.1); 
            grid-column: span 2; 
        }}
        
        .market-insights {{ 
            background: rgba(255,255,255,0.95); border-radius: 12px; 
            padding: 25px; box-shadow: 0 4px 15px rgba(0,0,0,0.1); 
            grid-column: span 2; 
        }}
        
        .insight-grid {{ 
            display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); 
            gap: 15px; margin-top: 20px; 
        }}
        
        .insight-card {{ 
            background: linear-gradient(135deg, #f8f9fa, #e9ecef); 
            border-radius: 8px; padding: 20px; border-left: 4px solid #8e44ad; 
        }}
        .insight-title {{ font-weight: 600; color: #2c3e50; margin-bottom: 10px; }}
        .insight-value {{ font-size: 24px; font-weight: 700; color: #8e44ad; }}
        .insight-description {{ font-size: 12px; color: #7f8c8d; margin-top: 5px; }}
    </style>
</head>
<body>
    <div class="header">
        <h1 class="title">🎯 Strategic Dashboard</h1>
        <p class="subtitle">Competitive intelligence and strategic insights - {perspective.upper()} perspective</p>
    </div>
    
    <div class="dashboard-container">
        <!-- Strategic Analysis Grid -->
        <div class="strategic-grid">
            <!-- SWOT Analysis -->
            <div class="strategy-card">
                <h3>🔍 SWOT Analysis</h3>
                <div class="swot-matrix">
                    <div class="swot-quadrant strengths">
                        <div class="quadrant-title">💪 Strengths</div>
                        <ul class="quadrant-items">
                            <li>Comprehensive knowledge base</li>
                            <li>Advanced AI capabilities</li>
                            <li>Real-time insights</li>
                            <li>Scalable architecture</li>
                        </ul>
                    </div>
                    <div class="swot-quadrant weaknesses">
                        <div class="quadrant-title">⚠️ Weaknesses</div>
                        <ul class="quadrant-items">
                            <li>Data freshness dependency</li>
                            <li>Complex implementation</li>
                            <li>Resource intensive</li>
                            <li>Learning curve</li>
                        </ul>
                    </div>
                    <div class="swot-quadrant opportunities">
                        <div class="quadrant-title">🚀 Opportunities</div>
                        <ul class="quadrant-items">
                            <li>Market expansion</li>
                            <li>AI advancement</li>
                            <li>Industry partnerships</li>
                            <li>Automation potential</li>
                        </ul>
                    </div>
                    <div class="swot-quadrant threats">
                        <div class="quadrant-title">⚡ Threats</div>
                        <ul class="quadrant-items">
                            <li>Competitive pressure</li>
                            <li>Technology disruption</li>
                            <li>Data privacy regulations</li>
                            <li>Market saturation</li>
                        </ul>
                    </div>
                </div>
            </div>
            
            <!-- Porter's Five Forces -->
            <div class="strategy-card">
                <h3>⚔️ Competitive Forces</h3>
                <canvas id="porterChart" width="400" height="300"></canvas>
            </div>
        </div>
        
        <!-- Competitive Landscape -->
        <div class="competitive-landscape">
            <h3>🏆 Competitive Landscape</h3>
            <canvas id="competitiveChart" width="800" height="300"></canvas>
        </div>
        
        <!-- Market Insights -->
        <div class="market-insights">
            <h3>📈 Strategic Market Insights</h3>
            <div class="insight-grid">
                <div class="insight-card">
                    <div class="insight-title">Market Position</div>
                    <div class="insight-value">Leader</div>
                    <div class="insight-description">Strong position in knowledge management</div>
                </div>
                <div class="insight-card">
                    <div class="insight-title">Growth Potential</div>
                    <div class="insight-value">High</div>
                    <div class="insight-description">Expanding AI and automation markets</div>
                </div>
                <div class="insight-card">
                    <div class="insight-title">Innovation Index</div>
                    <div class="insight-value">87%</div>
                    <div class="insight-description">Above industry average innovation</div>
                </div>
                <div class="insight-card">
                    <div class="insight-title">Risk Assessment</div>
                    <div class="insight-value">Medium</div>
                    <div class="insight-description">Manageable competitive risks</div>
                </div>
            </div>
        </div>
    </div>
    
    <script>
        function loadPorterChart() {{
            const ctx = document.getElementById('porterChart').getContext('2d');
            new Chart(ctx, {{
                type: 'radar',
                data: {{
                    labels: ['Competitive Rivalry', 'Supplier Power', 'Buyer Power', 'Threat of Substitutes', 'Barriers to Entry'],
                    datasets: [{{
                        label: 'Force Intensity',
                        data: [75, 40, 60, 55, 80],
                        borderColor: '#8e44ad',
                        backgroundColor: 'rgba(142, 68, 173, 0.2)',
                        pointBackgroundColor: '#8e44ad'
                    }}]
                }},
                options: {{
                    responsive: true,
                    scales: {{
                        r: {{ beginAtZero: true, max: 100 }}
                    }},
                    plugins: {{ legend: {{ display: false }} }}
                }}
            }});
        }}
        
        function loadCompetitiveChart() {{
            const ctx = document.getElementById('competitiveChart').getContext('2d');
            new Chart(ctx, {{
                type: 'scatter',
                data: {{
                    datasets: [{{
                        label: 'Us',
                        data: [{{x: 85, y: 90}}],
                        backgroundColor: '#27ae60',
                        pointRadius: 15
                    }}, {{
                        label: 'Competitor A',
                        data: [{{x: 70, y: 75}}],
                        backgroundColor: '#e74c3c',
                        pointRadius: 12
                    }}, {{
                        label: 'Competitor B',
                        data: [{{x: 60, y: 80}}],
                        backgroundColor: '#f39c12',
                        pointRadius: 10
                    }}, {{
                        label: 'Competitor C',
                        data: [{{x: 75, y: 65}}],
                        backgroundColor: '#3498db',
                        pointRadius: 10
                    }}]
                }},
                options: {{
                    responsive: true,
                    scales: {{
                        x: {{ title: {{ display: true, text: 'Market Share →' }}, min: 0, max: 100 }},
                        y: {{ title: {{ display: true, text: 'Innovation Score →' }}, min: 0, max: 100 }}
                    }},
                    plugins: {{
                        title: {{ display: true, text: 'Competitive Positioning' }}
                    }}
                }}
            }});
        }}
        
        // Load strategic charts
        loadPorterChart();
        loadCompetitiveChart();
    </script>
</body>
</html>
            """
            return HTMLResponse(content=html_content)
        except Exception as e:
            logger.error(f"Strategic dashboard failed: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail=str(e))

    @router.get("/data")
    async def dashboard_data(
        dashboard: str = Query("executive", description="Dashboard type: executive, operational, strategic"),
        timeframe: str = Query("30d", description="Timeframe: 7d, 30d, 90d, 1y"),
        repo: Annotated[GraphRepository, Depends(get_graph_repository)] = None,
    ) -> dict[str, Any]:
        """Get dashboard data for dynamic updates."""
        try:
            # Basic graph statistics (simplified for demo)
            data = {
                "timestamp": datetime.now().isoformat(),
                "dashboard": dashboard,
                "timeframe": timeframe,
                "metrics": {
                    "total_documents": 154,
                    "total_entities": 351,
                    "total_relationships": 892,
                    "quality_score": 88,
                    "growth_rate": 15.3,
                    "efficiency_score": 92
                },
                "trends": {
                    "documents": [120, 135, 145, 154],
                    "entities": [280, 310, 330, 351],
                    "relationships": [750, 810, 850, 892]
                },
                "insights": [
                    {
                        "title": "Knowledge Expansion",
                        "description": "Strong growth in entity relationships",
                        "impact": "high",
                        "category": "growth"
                    },
                    {
                        "title": "Data Quality",
                        "description": "Maintaining high quality standards",
                        "impact": "medium",
                        "category": "quality"
                    }
                ]
            }

            return data
        except Exception as e:
            logger.error(f"Dashboard data failed: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail=str(e))

    return router
