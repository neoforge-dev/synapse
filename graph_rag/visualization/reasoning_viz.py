"""
Reasoning chain visualization utilities.

This module provides functions to generate interactive HTML and SVG visualizations
of multi-step reasoning processes.
"""

import json
import html
import logging
from typing import Any, Dict
from graph_rag.core.reasoning_engine import ReasoningResult

logger = logging.getLogger(__name__)


def generate_reasoning_html(reasoning_result: ReasoningResult) -> str:
    """
    Generate interactive HTML visualization for a reasoning chain.
    
    Creates a self-contained HTML page with embedded CSS and JavaScript
    that visualizes the step-by-step reasoning process.
    
    Args:
        reasoning_result: The reasoning result to visualize
        
    Returns:
        Complete HTML page as a string
    """
    if reasoning_result is None:
        raise ValueError("reasoning_result cannot be None")
    
    # Convert reasoning result to JSON-serializable format
    viz_data = reasoning_result.get_visualization()
    
    # Safely encode the data as JSON for embedding in HTML
    json_data = json.dumps(viz_data, ensure_ascii=False, indent=2)
    
    html_template = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Reasoning Chain Visualization</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            margin: 0;
            padding: 20px;
            background-color: #f8f9fa;
            color: #333;
            line-height: 1.6;
        }}
        
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            overflow: hidden;
        }}
        
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
        }}
        
        .question {{
            font-size: 1.4em;
            font-weight: 600;
            margin: 0;
            line-height: 1.4;
        }}
        
        .summary {{
            margin-top: 15px;
            opacity: 0.9;
            font-size: 0.9em;
        }}
        
        .reasoning-chain {{
            padding: 0;
        }}
        
        .step {{
            border-bottom: 1px solid #eee;
            transition: all 0.3s ease;
            cursor: pointer;
        }}
        
        .step:hover {{
            background-color: #f8f9fa;
        }}
        
        .step:last-child {{
            border-bottom: none;
        }}
        
        .step-header {{
            padding: 20px 30px;
            display: flex;
            align-items: center;
            justify-content: space-between;
        }}
        
        .step-info {{
            flex: 1;
        }}
        
        .step-name {{
            font-size: 1.1em;
            font-weight: 600;
            color: #2c3e50;
            margin: 0 0 5px 0;
        }}
        
        .step-description {{
            color: #6c757d;
            font-size: 0.9em;
            margin: 0;
        }}
        
        .step-status {{
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 0.8em;
            font-weight: 500;
            text-transform: uppercase;
        }}
        
        .status-completed {{
            background-color: #d4edda;
            color: #155724;
        }}
        
        .status-failed {{
            background-color: #f8d7da;
            color: #721c24;
        }}
        
        .status-pending {{
            background-color: #fff3cd;
            color: #856404;
        }}
        
        .status-running {{
            background-color: #cce7ff;
            color: #004085;
        }}
        
        .step-details {{
            padding: 0 30px 20px;
            display: none;
            border-top: 1px solid #f0f0f0;
            background-color: #fafafa;
        }}
        
        .step-details.active {{
            display: block;
        }}
        
        .detail-section {{
            margin: 15px 0;
        }}
        
        .detail-label {{
            font-weight: 600;
            color: #2c3e50;
            margin-bottom: 8px;
            font-size: 0.9em;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }}
        
        .detail-content {{
            background: white;
            padding: 15px;
            border-radius: 6px;
            border-left: 4px solid #667eea;
            font-size: 0.9em;
        }}
        
        .final-answer {{
            margin: 30px;
            padding: 25px;
            background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
            color: white;
            border-radius: 8px;
        }}
        
        .final-answer h3 {{
            margin: 0 0 15px 0;
            font-size: 1.2em;
        }}
        
        .final-answer-content {{
            font-size: 1em;
            line-height: 1.6;
        }}
        
        .expand-icon {{
            margin-left: 10px;
            transition: transform 0.3s ease;
        }}
        
        .expand-icon.rotated {{
            transform: rotate(180deg);
        }}
        
        .timeline {{
            position: relative;
            padding-left: 30px;
        }}
        
        .timeline::before {{
            content: '';
            position: absolute;
            left: 15px;
            top: 0;
            bottom: 0;
            width: 2px;
            background: #dee2e6;
        }}
        
        .timeline-step {{
            position: relative;
            margin-bottom: 0;
        }}
        
        .timeline-step::before {{
            content: '';
            position: absolute;
            left: -23px;
            top: 25px;
            width: 16px;
            height: 16px;
            border-radius: 50%;
            border: 3px solid white;
            box-shadow: 0 0 0 2px #667eea;
        }}
        
        .timeline-step.completed::before {{
            background-color: #28a745;
            box-shadow: 0 0 0 2px #28a745;
        }}
        
        .timeline-step.failed::before {{
            background-color: #dc3545;
            box-shadow: 0 0 0 2px #dc3545;
        }}
        
        @media (max-width: 768px) {{
            body {{
                padding: 10px;
            }}
            
            .header, .step-header, .step-details, .final-answer {{
                padding: 20px;
            }}
            
            .timeline {{
                padding-left: 20px;
            }}
            
            .timeline-step::before {{
                left: -18px;
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1 class="question" id="main-question">Loading...</h1>
            <div class="summary" id="summary">Analyzing reasoning chain...</div>
        </div>
        
        <div class="reasoning-chain timeline" id="reasoning-viz">
            <!-- Steps will be populated by JavaScript -->
        </div>
        
        <div class="final-answer" id="final-answer" style="display: none;">
            <h3>Final Answer</h3>
            <div class="final-answer-content" id="final-answer-content"></div>
        </div>
    </div>

    <script>
        // Embedded reasoning data
        const reasoningData = {json_data};
        
        function escapeHtml(text) {{
            const div = document.createElement('div');
            div.textContent = text;
            return div.innerHTML;
        }}
        
        function formatStepName(name) {{
            return name.replace(/_/g, ' ')
                      .replace(/\\b\\w/g, l => l.toUpperCase());
        }}
        
        function renderSteps() {{
            const container = document.getElementById('reasoning-viz');
            const steps = reasoningData.steps || [];
            
            container.innerHTML = '';
            
            steps.forEach((step, index) => {{
                const stepDiv = document.createElement('div');
                stepDiv.className = `step timeline-step ${{step.status}}`;
                stepDiv.innerHTML = `
                    <div class="step-header" onclick="toggleStep(${{index}})">
                        <div class="step-info">
                            <h3 class="step-name">${{escapeHtml(formatStepName(step.name))}}</h3>
                            <p class="step-description">${{escapeHtml(step.description || '')}}</p>
                        </div>
                        <span class="step-status status-${{step.status}}">${{step.status}}</span>
                        <span class="expand-icon">▼</span>
                    </div>
                    <div class="step-details" id="step-details-${{index}}">
                        <div class="detail-section">
                            <div class="detail-label">Query</div>
                            <div class="detail-content">${{escapeHtml(step.query || 'N/A')}}</div>
                        </div>
                        <div class="detail-section">
                            <div class="detail-label">Answer</div>
                            <div class="detail-content">${{escapeHtml(step.answer || 'N/A')}}</div>
                        </div>
                        <div class="detail-section">
                            <div class="detail-label">Reasoning</div>
                            <div class="detail-content">${{escapeHtml(step.reasoning || 'N/A')}}</div>
                        </div>
                    </div>
                `;
                container.appendChild(stepDiv);
            }});
        }}
        
        function toggleStep(index) {{
            const details = document.getElementById(`step-details-${{index}}`);
            const icon = details.parentElement.querySelector('.expand-icon');
            
            if (details.classList.contains('active')) {{
                details.classList.remove('active');
                icon.classList.remove('rotated');
            }} else {{
                // Close all other steps
                document.querySelectorAll('.step-details.active').forEach(el => {{
                    el.classList.remove('active');
                }});
                document.querySelectorAll('.expand-icon.rotated').forEach(el => {{
                    el.classList.remove('rotated');
                }});
                
                // Open this step
                details.classList.add('active');
                icon.classList.add('rotated');
            }}
        }}
        
        function renderFinalAnswer() {{
            const finalAnswerDiv = document.getElementById('final-answer');
            const finalAnswerContent = document.getElementById('final-answer-content');
            
            if (reasoningData.final_answer) {{
                finalAnswerContent.textContent = reasoningData.final_answer;
                finalAnswerDiv.style.display = 'block';
            }}
        }}
        
        function renderHeader() {{
            const questionEl = document.getElementById('main-question');
            const summaryEl = document.getElementById('summary');
            
            questionEl.textContent = reasoningData.question || 'Reasoning Analysis';
            
            const summary = reasoningData.summary || {{}};
            const totalSteps = summary.total_steps || 0;
            const completedSteps = summary.completed_steps || 0;
            
            summaryEl.textContent = `${{completedSteps}} of ${{totalSteps}} steps completed`;
        }}
        
        // Initialize the visualization
        document.addEventListener('DOMContentLoaded', function() {{
            renderHeader();
            renderSteps();
            renderFinalAnswer();
        }});
        
        // Export functionality (could be extended)
        window.exportData = function(format) {{
            if (format === 'json') {{
                const blob = new Blob([JSON.stringify(reasoningData, null, 2)], {{
                    type: 'application/json'
                }});
                const url = URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = 'reasoning-chain.json';
                a.click();
                URL.revokeObjectURL(url);
            }}
        }};
    </script>
</body>
</html>"""
    
    return html_template


def generate_reasoning_svg(reasoning_result: ReasoningResult) -> str:
    """
    Generate SVG visualization for a reasoning chain.
    
    Creates a flowchart-style SVG showing the reasoning steps and their relationships.
    
    Args:
        reasoning_result: The reasoning result to visualize
        
    Returns:
        SVG content as a string
    """
    steps = reasoning_result.reasoning_chain.steps
    
    # Calculate dimensions
    step_width = 250
    step_height = 80
    step_spacing = 120
    margin = 50
    
    total_width = step_width + (2 * margin)
    total_height = len(steps) * (step_height + step_spacing) + margin
    
    # Start building SVG
    svg_parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'width="{total_width}" height="{total_height}" '
        f'viewBox="0 0 {total_width} {total_height}">',
        
        # Add styles
        '<defs>',
        '<style>',
        '.step-box { fill: #f8f9fa; stroke: #667eea; stroke-width: 2; rx: 8; }',
        '.step-completed { fill: #d4edda; stroke: #28a745; }',
        '.step-failed { fill: #f8d7da; stroke: #dc3545; }',
        '.step-text { font-family: Arial, sans-serif; font-size: 12px; fill: #333; }',
        '.step-name { font-weight: bold; font-size: 14px; }',
        '.arrow { stroke: #667eea; stroke-width: 2; fill: none; marker-end: url(#arrowhead); }',
        '</style>',
        
        # Arrow marker
        '<marker id="arrowhead" markerWidth="10" markerHeight="7" refX="10" refY="3.5" orient="auto">',
        '<polygon points="0 0, 10 3.5, 0 7" fill="#667eea" />',
        '</marker>',
        '</defs>'
    ]
    
    # Add title
    svg_parts.extend([
        f'<text x="{total_width//2}" y="30" text-anchor="middle" class="step-name" font-size="16">',
        f'{html.escape(reasoning_result.question[:80] + ("..." if len(reasoning_result.question) > 80 else ""))}',
        '</text>'
    ])
    
    # Draw steps
    for i, step in enumerate(steps):
        y = margin + 50 + i * (step_height + step_spacing)
        x = margin
        
        # Determine step style based on status
        step_class = f"step-box step-{step.status}" if step.status in ['completed', 'failed'] else "step-box"
        
        # Draw step rectangle
        svg_parts.append(f'<rect x="{x}" y="{y}" width="{step_width}" height="{step_height}" class="{step_class}"/>')
        
        # Add step name
        step_name = step.name.replace('_', ' ').title()
        svg_parts.extend([
            f'<text x="{x + step_width//2}" y="{y + 25}" text-anchor="middle" class="step-text step-name">',
            f'{html.escape(step_name[:30] + ("..." if len(step_name) > 30 else ""))}',
            '</text>'
        ])
        
        # Add step status
        svg_parts.extend([
            f'<text x="{x + step_width//2}" y="{y + 45}" text-anchor="middle" class="step-text">',
            f'Status: {html.escape(step.status)}',
            '</text>'
        ])
        
        # Add brief answer if available
        if step.result and step.result.answer:
            answer_brief = step.result.answer[:40] + ("..." if len(step.result.answer) > 40 else "")
            svg_parts.extend([
                f'<text x="{x + step_width//2}" y="{y + 65}" text-anchor="middle" class="step-text" font-size="10">',
                f'{html.escape(answer_brief)}',
                '</text>'
            ])
        
        # Draw arrow to next step (if not the last step)
        if i < len(steps) - 1:
            arrow_start_y = y + step_height
            arrow_end_y = arrow_start_y + step_spacing - 10
            arrow_x = x + step_width // 2
            
            svg_parts.append(
                f'<line x1="{arrow_x}" y1="{arrow_start_y}" x2="{arrow_x}" y2="{arrow_end_y}" class="arrow"/>'
            )
    
    # Add final answer box if available
    if reasoning_result.final_answer:
        final_y = margin + 50 + len(steps) * (step_height + step_spacing)
        svg_parts.extend([
            f'<rect x="{margin}" y="{final_y}" width="{step_width}" height="{step_height}" '
            f'fill="#f093fb" stroke="#f5576c" stroke-width="2" rx="8"/>',
            
            f'<text x="{margin + step_width//2}" y="{final_y + 25}" text-anchor="middle" class="step-text step-name" fill="white">',
            'Final Answer',
            '</text>',
            
            f'<text x="{margin + step_width//2}" y="{final_y + 45}" text-anchor="middle" class="step-text" fill="white" font-size="10">',
            f'{html.escape(reasoning_result.final_answer[:50] + ("..." if len(reasoning_result.final_answer) > 50 else ""))}',
            '</text>'
        ])
        
        # Draw arrow to final answer
        if steps:
            last_step_y = margin + 50 + (len(steps) - 1) * (step_height + step_spacing) + step_height
            arrow_x = margin + step_width // 2
            svg_parts.append(
                f'<line x1="{arrow_x}" y1="{last_step_y}" x2="{arrow_x}" y2="{final_y - 10}" class="arrow"/>'
            )
    
    svg_parts.append('</svg>')
    
    return '\n'.join(svg_parts)