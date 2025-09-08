#!/usr/bin/env python3
"""
Epic 7 Week 1 Sales Automation Web Interface
Professional CRM and proposal generation interface for systematic sales conversion
"""

import logging
from datetime import datetime
from typing import Dict, List, Optional
import json
import sqlite3

from fastapi import FastAPI, HTTPException, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
import uvicorn

from .epic7_sales_automation import SalesAutomationEngine, CRMContact

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# FastAPI app
app = FastAPI(title="Epic 7 Sales Automation", description="Systematic $2M+ ARR Sales Engine", version="1.0.0")

# Initialize templates
templates = Jinja2Templates(directory="business_development/templates")

# Global sales engine instance
sales_engine = SalesAutomationEngine()

# Pydantic models
class ContactUpdate(BaseModel):
    name: Optional[str] = None
    company: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    notes: Optional[str] = None

class ProposalRequest(BaseModel):
    contact_id: str
    inquiry_type: Optional[str] = None

# API Routes
@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    """Sales automation dashboard"""
    summary = sales_engine.get_sales_pipeline_summary()
    
    # Get recent contacts
    conn = sqlite3.connect(sales_engine.db_path)
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT contact_id, name, company, lead_score, priority_tier, qualification_status, estimated_value, created_at
        FROM crm_contacts 
        ORDER BY lead_score DESC, created_at DESC 
        LIMIT 10
    ''')
    recent_contacts = cursor.fetchall()
    
    # Get recent proposals
    cursor.execute('''
        SELECT p.proposal_id, c.name, c.company, p.proposal_value, p.estimated_close_probability, p.status, p.generated_at
        FROM generated_proposals p
        JOIN crm_contacts c ON p.contact_id = c.contact_id
        ORDER BY p.generated_at DESC
        LIMIT 5
    ''')
    recent_proposals = cursor.fetchall()
    
    conn.close()
    
    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "summary": summary,
        "recent_contacts": recent_contacts,
        "recent_proposals": recent_proposals
    })

@app.get("/contacts", response_class=HTMLResponse)
async def contacts_page(request: Request):
    """CRM contacts management page"""
    conn = sqlite3.connect(sales_engine.db_path)
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT contact_id, name, company, company_size, lead_score, qualification_status, 
               priority_tier, estimated_value, next_action, next_action_date, created_at
        FROM crm_contacts 
        ORDER BY lead_score DESC, created_at DESC
    ''')
    contacts = cursor.fetchall()
    conn.close()
    
    return templates.TemplateResponse("contacts.html", {
        "request": request,
        "contacts": contacts
    })

@app.get("/contacts/{contact_id}", response_class=HTMLResponse)
async def contact_detail(request: Request, contact_id: str):
    """Individual contact detail page"""
    conn = sqlite3.connect(sales_engine.db_path)
    cursor = conn.cursor()
    
    # Get contact details
    cursor.execute('SELECT * FROM crm_contacts WHERE contact_id = ?', (contact_id,))
    contact_data = cursor.fetchone()
    
    if not contact_data:
        raise HTTPException(status_code=404, detail="Contact not found")
    
    columns = [description[0] for description in cursor.description]
    contact = dict(zip(columns, contact_data, strict=False))
    
    # Get proposals for this contact
    cursor.execute('''
        SELECT proposal_id, template_used, proposal_value, estimated_close_probability, 
               status, generated_at, sent_at
        FROM generated_proposals 
        WHERE contact_id = ?
        ORDER BY generated_at DESC
    ''', (contact_id,))
    proposals = cursor.fetchall()
    
    # Get lead scoring history
    cursor.execute('''
        SELECT previous_score, new_score, scoring_factors, scored_at
        FROM lead_scoring_history
        WHERE contact_id = ?
        ORDER BY scored_at DESC
        LIMIT 10
    ''', (contact_id,))
    scoring_history = cursor.fetchall()
    
    conn.close()
    
    return templates.TemplateResponse("contact_detail.html", {
        "request": request,
        "contact": contact,
        "proposals": proposals,
        "scoring_history": scoring_history
    })

@app.get("/proposals", response_class=HTMLResponse)
async def proposals_page(request: Request):
    """Proposal management page"""
    conn = sqlite3.connect(sales_engine.db_path)
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT p.proposal_id, c.name, c.company, c.priority_tier, p.template_used,
               p.proposal_value, p.estimated_close_probability, p.status, p.generated_at, p.sent_at
        FROM generated_proposals p
        JOIN crm_contacts c ON p.contact_id = c.contact_id
        ORDER BY p.generated_at DESC
    ''')
    proposals = cursor.fetchall()
    conn.close()
    
    return templates.TemplateResponse("proposals.html", {
        "request": request,
        "proposals": proposals
    })

@app.get("/proposals/{proposal_id}", response_class=HTMLResponse)
async def proposal_detail(request: Request, proposal_id: str):
    """Individual proposal detail page"""
    conn = sqlite3.connect(sales_engine.db_path)
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT p.*, c.name, c.company, c.company_size, c.priority_tier
        FROM generated_proposals p
        JOIN crm_contacts c ON p.contact_id = c.contact_id
        WHERE p.proposal_id = ?
    ''', (proposal_id,))
    
    proposal_data = cursor.fetchone()
    
    if not proposal_data:
        raise HTTPException(status_code=404, detail="Proposal not found")
    
    columns = [description[0] for description in cursor.description]
    proposal = dict(zip(columns, proposal_data, strict=False))
    
    # Parse JSON content
    proposal['content'] = json.loads(proposal['proposal_content'])
    proposal['roi'] = json.loads(proposal['roi_calculation'])
    
    conn.close()
    
    return templates.TemplateResponse("proposal_detail.html", {
        "request": request,
        "proposal": proposal
    })

@app.get("/analytics", response_class=HTMLResponse)
async def analytics_page(request: Request):
    """Sales analytics and insights page"""
    summary = sales_engine.get_sales_pipeline_summary()
    
    conn = sqlite3.connect(sales_engine.db_path)
    cursor = conn.cursor()
    
    # Lead score distribution
    cursor.execute('''
        SELECT 
            CASE 
                WHEN lead_score >= 80 THEN '80-100'
                WHEN lead_score >= 60 THEN '60-79'
                WHEN lead_score >= 40 THEN '40-59'
                ELSE '0-39'
            END as score_range,
            COUNT(*) as count
        FROM crm_contacts
        GROUP BY score_range
    ''')
    score_distribution = cursor.fetchall()
    
    # Company size distribution
    cursor.execute('''
        SELECT company_size, COUNT(*) as count, SUM(estimated_value) as total_value
        FROM crm_contacts
        GROUP BY company_size
        ORDER BY total_value DESC
    ''')
    company_distribution = cursor.fetchall()
    
    # Inquiry type performance
    cursor.execute('''
        SELECT 
            c.notes, 
            COUNT(*) as count,
            AVG(c.lead_score) as avg_score,
            SUM(c.estimated_value) as total_value
        FROM crm_contacts c
        GROUP BY SUBSTR(c.notes, 1, 50)
        HAVING count > 0
        ORDER BY total_value DESC
        LIMIT 10
    ''')
    inquiry_performance = cursor.fetchall()
    
    conn.close()
    
    return templates.TemplateResponse("analytics.html", {
        "request": request,
        "summary": summary,
        "score_distribution": score_distribution,
        "company_distribution": company_distribution,
        "inquiry_performance": inquiry_performance
    })

# API Endpoints
@app.post("/api/import-inquiries")
async def import_inquiries():
    """Import consultation inquiries from existing system"""
    try:
        contacts = sales_engine.import_consultation_inquiries()
        return {"success": True, "imported_count": len(contacts), "contacts": [c.__dict__ for c in contacts]}
    except Exception as e:
        logger.error(f"Failed to import inquiries: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/generate-proposal")
async def generate_proposal(request: ProposalRequest):
    """Generate automated proposal for contact"""
    try:
        proposal = sales_engine.generate_automated_proposal(request.contact_id, request.inquiry_type)
        if 'error' in proposal:
            raise HTTPException(status_code=404, detail=proposal['error'])
        return {"success": True, "proposal": proposal}
    except Exception as e:
        logger.error(f"Failed to generate proposal: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/api/contacts/{contact_id}")
async def update_contact(contact_id: str, contact_update: ContactUpdate):
    """Update contact information"""
    try:
        conn = sqlite3.connect(sales_engine.db_path)
        cursor = conn.cursor()
        
        # Build update query
        updates = []
        values = []
        
        for field, value in contact_update.dict(exclude_unset=True).items():
            if value is not None:
                updates.append(f"{field} = ?")
                values.append(value)
        
        if updates:
            updates.append("updated_at = ?")
            values.append(datetime.now().isoformat())
            values.append(contact_id)
            
            query = f"UPDATE crm_contacts SET {', '.join(updates)} WHERE contact_id = ?"
            cursor.execute(query, values)
            conn.commit()
        
        conn.close()
        
        return {"success": True, "updated_fields": list(contact_update.dict(exclude_unset=True).keys())}
    except Exception as e:
        logger.error(f"Failed to update contact: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/proposals/{proposal_id}/send")
async def send_proposal(proposal_id: str):
    """Mark proposal as sent"""
    try:
        conn = sqlite3.connect(sales_engine.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE generated_proposals 
            SET status = 'sent', sent_at = ?
            WHERE proposal_id = ?
        ''', (datetime.now().isoformat(), proposal_id))
        
        conn.commit()
        conn.close()
        
        return {"success": True, "message": "Proposal marked as sent"}
    except Exception as e:
        logger.error(f"Failed to send proposal: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/pipeline-summary")
async def pipeline_summary():
    """Get current pipeline summary"""
    try:
        summary = sales_engine.get_sales_pipeline_summary()
        return summary
    except Exception as e:
        logger.error(f"Failed to get pipeline summary: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Initialize templates directory and HTML templates
def create_templates():
    """Create HTML templates for the web interface"""
    import os
    
    template_dir = "business_development/templates"
    os.makedirs(template_dir, exist_ok=True)
    
    # Dashboard template
    dashboard_html = '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Epic 7 Sales Automation Dashboard</title>
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; margin: 0; padding: 20px; background: #f5f5f5; }
        .container { max-width: 1200px; margin: 0 auto; }
        .header { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; border-radius: 10px; margin-bottom: 30px; }
        .header h1 { margin: 0; font-size: 2.5em; }
        .header p { margin: 10px 0 0; opacity: 0.9; }
        .metrics { display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 20px; margin-bottom: 30px; }
        .metric-card { background: white; padding: 25px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
        .metric-value { font-size: 2.5em; font-weight: bold; color: #333; margin-bottom: 5px; }
        .metric-label { color: #666; font-size: 0.9em; text-transform: uppercase; letter-spacing: 1px; }
        .metric-change { font-size: 0.85em; margin-top: 10px; }
        .positive { color: #10b981; }
        .neutral { color: #6b7280; }
        .section { background: white; border-radius: 10px; padding: 25px; margin-bottom: 20px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
        .section h2 { margin: 0 0 20px; color: #333; border-bottom: 2px solid #eee; padding-bottom: 10px; }
        table { width: 100%; border-collapse: collapse; }
        th, td { text-align: left; padding: 12px; border-bottom: 1px solid #eee; }
        th { background: #f8f9fa; font-weight: 600; }
        .priority-platinum { background: #fdf2f8; color: #be185d; padding: 4px 8px; border-radius: 4px; font-size: 0.8em; }
        .priority-gold { background: #fef3c7; color: #d97706; padding: 4px 8px; border-radius: 4px; font-size: 0.8em; }
        .priority-silver { background: #f1f5f9; color: #475569; padding: 4px 8px; border-radius: 4px; font-size: 0.8em; }
        .nav { background: white; padding: 20px; border-radius: 10px; margin-bottom: 20px; }
        .nav a { margin-right: 20px; text-decoration: none; color: #667eea; font-weight: 500; }
        .nav a:hover { color: #764ba2; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Epic 7 Sales Automation</h1>
            <p>Systematic $2M+ ARR Sales Engine - Converting Leads to Revenue</p>
        </div>
        
        <div class="nav">
            <a href="/">Dashboard</a>
            <a href="/contacts">CRM Contacts</a>
            <a href="/proposals">Proposals</a>
            <a href="/analytics">Analytics</a>
        </div>
        
        <div class="metrics">
            <div class="metric-card">
                <div class="metric-value">{{ summary.total_contacts }}</div>
                <div class="metric-label">Total Contacts</div>
                <div class="metric-change neutral">{{ summary.qualified_leads }} qualified leads</div>
            </div>
            <div class="metric-card">
                <div class="metric-value">${{ "{:,}".format(summary.total_pipeline_value) }}</div>
                <div class="metric-label">Pipeline Value</div>
                <div class="metric-change positive">{{ summary.pipeline_health_score }}% health score</div>
            </div>
            <div class="metric-card">
                <div class="metric-value">{{ summary.avg_close_probability }}%</div>
                <div class="metric-label">Avg Close Rate</div>
                <div class="metric-change neutral">{{ summary.sent_proposals }} sent proposals</div>
            </div>
            <div class="metric-card">
                <div class="metric-value">${{ "{:,}".format(summary.projected_annual_revenue) }}</div>
                <div class="metric-label">Projected ARR</div>
                <div class="metric-change positive">{% if summary.projected_annual_revenue >= 2000000 %}🎉 Target Met!{% else %}Need ${{ "{:,}".format(2000000 - summary.projected_annual_revenue) }} more{% endif %}</div>
            </div>
        </div>
        
        <div class="section">
            <h2>High-Priority Contacts</h2>
            <table>
                <thead>
                    <tr>
                        <th>Name</th>
                        <th>Company</th>
                        <th>Lead Score</th>
                        <th>Priority</th>
                        <th>Value</th>
                        <th>Actions</th>
                    </tr>
                </thead>
                <tbody>
                    {% for contact in recent_contacts %}
                    <tr>
                        <td><a href="/contacts/{{ contact[0] }}">{{ contact[1] }}</a></td>
                        <td>{{ contact[2] }}</td>
                        <td>{{ contact[3] }}</td>
                        <td><span class="priority-{{ contact[4] }}">{{ contact[4]|title }}</span></td>
                        <td>${{ "{:,}".format(contact[6]) }}</td>
                        <td><a href="/contacts/{{ contact[0] }}">View Details</a></td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>
        </div>
        
        <div class="section">
            <h2>Recent Proposals</h2>
            <table>
                <thead>
                    <tr>
                        <th>Contact</th>
                        <th>Company</th>
                        <th>Value</th>
                        <th>Close Probability</th>
                        <th>Status</th>
                        <th>Generated</th>
                    </tr>
                </thead>
                <tbody>
                    {% for proposal in recent_proposals %}
                    <tr>
                        <td><a href="/proposals/{{ proposal[0] }}">{{ proposal[1] }}</a></td>
                        <td>{{ proposal[2] }}</td>
                        <td>${{ "{:,}".format(proposal[3]) }}</td>
                        <td>{{ "{:.1%}".format(proposal[4]) }}</td>
                        <td>{{ proposal[5]|title }}</td>
                        <td>{{ proposal[6][:10] }}</td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>
        </div>
    </div>
</body>
</html>'''
    
    with open(f"{template_dir}/dashboard.html", "w") as f:
        f.write(dashboard_html)
    
    # Contacts template
    contacts_html = '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>CRM Contacts - Epic 7 Sales Automation</title>
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; margin: 0; padding: 20px; background: #f5f5f5; }
        .container { max-width: 1400px; margin: 0 auto; }
        .header { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; border-radius: 10px; margin-bottom: 30px; }
        .nav { background: white; padding: 20px; border-radius: 10px; margin-bottom: 20px; }
        .nav a { margin-right: 20px; text-decoration: none; color: #667eea; font-weight: 500; }
        .section { background: white; border-radius: 10px; padding: 25px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
        table { width: 100%; border-collapse: collapse; }
        th, td { text-align: left; padding: 12px; border-bottom: 1px solid #eee; }
        th { background: #f8f9fa; font-weight: 600; position: sticky; top: 0; }
        .lead-score { font-weight: bold; }
        .score-high { color: #10b981; }
        .score-medium { color: #f59e0b; }
        .score-low { color: #ef4444; }
        .priority-platinum { background: #fdf2f8; color: #be185d; padding: 4px 8px; border-radius: 4px; font-size: 0.8em; }
        .priority-gold { background: #fef3c7; color: #d97706; padding: 4px 8px; border-radius: 4px; font-size: 0.8em; }
        .priority-silver { background: #f1f5f9; color: #475569; padding: 4px 8px; border-radius: 4px; font-size: 0.8em; }
        .priority-bronze { background: #f3f4f6; color: #6b7280; padding: 4px 8px; border-radius: 4px; font-size: 0.8em; }
        .qualified { background: #d1fae5; color: #065f46; padding: 4px 8px; border-radius: 4px; font-size: 0.8em; }
        .unqualified { background: #fef3c7; color: #92400e; padding: 4px 8px; border-radius: 4px; font-size: 0.8em; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>CRM Contacts</h1>
            <p>Lead Management and Qualification System</p>
        </div>
        
        <div class="nav">
            <a href="/">Dashboard</a>
            <a href="/contacts">CRM Contacts</a>
            <a href="/proposals">Proposals</a>
            <a href="/analytics">Analytics</a>
        </div>
        
        <div class="section">
            <h2>All Contacts</h2>
            <table>
                <thead>
                    <tr>
                        <th>Name</th>
                        <th>Company</th>
                        <th>Company Size</th>
                        <th>Lead Score</th>
                        <th>Status</th>
                        <th>Priority</th>
                        <th>Value</th>
                        <th>Next Action</th>
                        <th>Due Date</th>
                        <th>Actions</th>
                    </tr>
                </thead>
                <tbody>
                    {% for contact in contacts %}
                    <tr>
                        <td><a href="/contacts/{{ contact[0] }}">{{ contact[1] }}</a></td>
                        <td>{{ contact[2] }}</td>
                        <td>{{ contact[3] }}</td>
                        <td class="lead-score {% if contact[4] >= 70 %}score-high{% elif contact[4] >= 40 %}score-medium{% else %}score-low{% endif %}">{{ contact[4] }}</td>
                        <td><span class="{{ contact[5] }}">{{ contact[5]|title }}</span></td>
                        <td><span class="priority-{{ contact[6] }}">{{ contact[6]|title }}</span></td>
                        <td>${{ "{:,}".format(contact[7]) }}</td>
                        <td>{{ contact[8][:30] }}...</td>
                        <td>{{ contact[9][:10] if contact[9] else 'Not set' }}</td>
                        <td>
                            <a href="/contacts/{{ contact[0] }}">View</a>
                            <button onclick="generateProposal('{{ contact[0] }}')">Generate Proposal</button>
                        </td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>
        </div>
    </div>
    
    <script>
        function generateProposal(contactId) {
            fetch('/api/generate-proposal', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({contact_id: contactId})
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    alert('Proposal generated successfully!');
                    window.location.reload();
                } else {
                    alert('Error generating proposal: ' + data.detail);
                }
            });
        }
    </script>
</body>
</html>'''
    
    with open(f"{template_dir}/contacts.html", "w") as f:
        f.write(contacts_html)

# Create templates when module is imported
create_templates()

if __name__ == "__main__":
    print("🚀 Starting Epic 7 Sales Automation Web Interface")
    print("🔗 Access dashboard at: http://localhost:8001")
    print("📊 CRM system ready for systematic lead conversion")
    
    # Import inquiries on startup
    try:
        contacts = sales_engine.import_consultation_inquiries()
        print(f"✅ Imported {len(contacts)} consultation inquiries into CRM")
    except Exception as e:
        print(f"⚠️  Import warning: {e}")
    
    uvicorn.run(app, host="0.0.0.0", port=8001)