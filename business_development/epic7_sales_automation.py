#!/usr/bin/env python3
"""
Epic 7 Week 1 Sales Automation System
Converts working lead generation into systematic $2M+ ARR sales engine
"""

import logging
import sqlite3
import json
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from typing import Dict, List, Optional, Tuple
import pandas as pd
import numpy as np
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@dataclass
class CRMContact:
    """Enhanced CRM contact with lead scoring"""
    contact_id: str
    name: str
    company: str
    company_size: str
    title: str
    email: str
    linkedin_profile: str
    phone: str
    lead_score: int  # 0-100
    qualification_status: str  # unqualified, qualified, disqualified
    estimated_value: int
    priority_tier: str  # platinum, gold, silver, bronze
    next_action: str
    next_action_date: str
    created_at: str
    updated_at: str
    notes: str

@dataclass  
class ProposalTemplate:
    """Business proposal template with ROI calculations"""
    template_id: str
    inquiry_type: str
    title: str
    executive_summary: str
    problem_statement: str
    solution_overview: str
    roi_calculation: Dict
    timeline: str
    investment_range: str
    next_steps: str
    created_at: str

class SalesAutomationEngine:
    """Epic 7 Week 1 Sales Automation System"""
    
    def __init__(self, db_path: str = "business_development/epic7_sales_automation.db"):
        self.db_path = db_path
        self.consultation_db_path = "business_development/linkedin_business_development.db"
        self._init_database()
        self._init_proposal_templates()
        
    def _init_database(self):
        """Initialize Epic 7 sales automation database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # CRM Contacts table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS crm_contacts (
                contact_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                company TEXT,
                company_size TEXT,
                title TEXT,
                email TEXT,
                linkedin_profile TEXT,
                phone TEXT,
                lead_score INTEGER DEFAULT 0,
                qualification_status TEXT DEFAULT 'unqualified',
                estimated_value INTEGER DEFAULT 0,
                priority_tier TEXT DEFAULT 'bronze',
                next_action TEXT,
                next_action_date TEXT,
                created_at TEXT,
                updated_at TEXT,
                notes TEXT
            )
        ''')
        
        # Lead Scoring History table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS lead_scoring_history (
                scoring_id TEXT PRIMARY KEY,
                contact_id TEXT,
                previous_score INTEGER,
                new_score INTEGER,
                scoring_factors TEXT, -- JSON
                scored_at TEXT,
                FOREIGN KEY (contact_id) REFERENCES crm_contacts (contact_id)
            )
        ''')
        
        # Proposal Generation table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS generated_proposals (
                proposal_id TEXT PRIMARY KEY,
                contact_id TEXT,
                inquiry_id TEXT,
                template_used TEXT,
                proposal_content TEXT, -- JSON
                roi_calculation TEXT, -- JSON
                estimated_close_probability REAL,
                proposal_value INTEGER,
                status TEXT DEFAULT 'draft',
                generated_at TEXT,
                sent_at TEXT,
                FOREIGN KEY (contact_id) REFERENCES crm_contacts (contact_id)
            )
        ''')
        
        # Sales Pipeline Tracking table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS sales_pipeline (
                pipeline_id TEXT PRIMARY KEY,
                contact_id TEXT,
                stage TEXT, -- lead, qualified, proposal_sent, negotiating, closed_won, closed_lost
                value INTEGER,
                probability REAL,
                expected_close_date TEXT,
                created_at TEXT,
                updated_at TEXT,
                stage_history TEXT, -- JSON
                FOREIGN KEY (contact_id) REFERENCES crm_contacts (contact_id)
            )
        ''')
        
        # ROI Calculator Templates table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS roi_templates (
                template_id TEXT PRIMARY KEY,
                inquiry_type TEXT,
                template_name TEXT,
                cost_factors TEXT, -- JSON
                benefit_factors TEXT, -- JSON
                calculation_formula TEXT,
                industry_benchmarks TEXT, -- JSON
                created_at TEXT,
                updated_at TEXT
            )
        ''')
        
        conn.commit()
        conn.close()
        logger.info("Epic 7 sales automation database initialized")
        
    def _init_proposal_templates(self):
        """Initialize business proposal templates"""
        templates = [
            {
                "template_id": "team_building_proposal",
                "inquiry_type": "team_building",
                "title": "Team Performance Optimization & 10x Velocity Program",
                "executive_summary": "Transform your engineering team into a high-performance, predictable delivery engine through proven methodologies that have helped companies achieve 3-5x velocity improvements.",
                "problem_statement": "Most scaling companies experience diminishing returns as team size grows - communication overhead, inconsistent processes, and cultural dilution reduce per-person productivity.",
                "solution_overview": "Comprehensive 90-day team transformation program including velocity diagnostics, process optimization, cultural alignment, and sustainable growth frameworks.",
                "roi_calculation": {
                    "time_savings_per_developer": 8, # hours per week
                    "average_developer_cost": 150000, # annual salary + benefits
                    "team_size_multiplier": 1.0,
                    "delivery_acceleration": 2.5, # 2.5x faster delivery
                    "quality_improvement": 40, # % reduction in bugs
                },
                "timeline": "90-day intensive program with ongoing optimization",
                "investment_range": "$25,000 - $75,000",
                "next_steps": "30-minute team velocity diagnostic call to assess current state and identify specific optimization opportunities"
            },
            {
                "template_id": "fractional_cto_proposal", 
                "inquiry_type": "fractional_cto",
                "title": "Fractional CTO Services - Strategic Technical Leadership",
                "executive_summary": "Part-time executive technical leadership providing strategic guidance, architecture decisions, and team development without full-time CTO costs.",
                "problem_statement": "Growing companies need senior technical leadership but can't justify full-time CTO costs or don't have enough technical complexity to warrant a full-time hire.",
                "solution_overview": "20-40 hours per month of strategic technical leadership including architecture review, technology roadmapping, team mentoring, and executive technical communication.",
                "roi_calculation": {
                    "full_time_cto_cost": 300000, # annual cost
                    "fractional_percentage": 30, # % of full-time
                    "bad_technical_decisions_prevented": 2, # major decisions per year
                    "cost_per_bad_decision": 150000, # average cost of wrong technology choice
                    "team_productivity_increase": 25, # % improvement
                },
                "timeline": "6-month initial engagement with quarterly reviews",
                "investment_range": "$75,000 - $150,000 annually",
                "next_steps": "45-minute technical strategy assessment to identify immediate priorities and long-term roadmap"
            },
            {
                "template_id": "nobuild_audit_proposal",
                "inquiry_type": "nobuild_audit", 
                "title": "#NOBUILD Technology Audit - Build vs Buy Optimization",
                "executive_summary": "Comprehensive technology stack audit identifying opportunities to replace custom development with proven SaaS solutions, reducing engineering costs by 40-60%.",
                "problem_statement": "Engineering teams often build custom solutions when excellent SaaS alternatives exist, leading to unnecessary development costs, maintenance burden, and slower time-to-market.",
                "solution_overview": "Complete technology audit using #NOBUILD methodology to identify optimization opportunities, cost-benefit analysis of current vs alternative solutions, and implementation roadmap.",
                "roi_calculation": {
                    "custom_development_hours": 2000, # hours per year on custom features
                    "average_developer_hourly_cost": 100,
                    "maintenance_multiplier": 1.5, # ongoing maintenance costs
                    "saas_replacement_savings": 50, # % savings from SaaS alternatives
                    "time_to_market_acceleration": 3, # 3x faster delivery
                },
                "timeline": "6-week audit with implementation recommendations",
                "investment_range": "$20,000 - $50,000",
                "next_steps": "Technology stack analysis session to identify initial audit scope and quick wins"
            }
        ]
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        for template in templates:
            cursor.execute('''
                INSERT OR REPLACE INTO roi_templates 
                (template_id, inquiry_type, template_name, cost_factors, benefit_factors, 
                 calculation_formula, industry_benchmarks, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                template["template_id"],
                template["inquiry_type"],
                template["title"],
                json.dumps(template["roi_calculation"]),
                json.dumps({"solution_benefits": template["solution_overview"]}),
                json.dumps({"formula": "cost_savings + productivity_gains - investment"}),
                json.dumps({"industry_avg_improvement": "2.5x velocity, 40% cost reduction"}),
                datetime.now().isoformat(),
                datetime.now().isoformat()
            ))
            
        conn.commit()
        conn.close()
        logger.info("Proposal templates initialized")
        
    def import_consultation_inquiries(self) -> List[CRMContact]:
        """Import existing consultation inquiries into CRM system"""
        # Read from existing consultation database
        conn = sqlite3.connect(self.consultation_db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT inquiry_id, contact_name, company, company_size, inquiry_type, 
                   inquiry_text, estimated_value, priority_score, created_at
            FROM consultation_inquiries
            WHERE status IN ('new', 'contacted')
        ''')
        
        inquiries = cursor.fetchall()
        conn.close()
        
        imported_contacts = []
        
        for inquiry in inquiries:
            inquiry_id, name, company, company_size, inquiry_type, inquiry_text, estimated_value, priority_score, created_at = inquiry
            
            # Generate contact ID
            contact_id = f"crm-{inquiry_id}"
            
            # Calculate lead score based on inquiry data
            lead_score = self._calculate_lead_score(inquiry_text, company_size, priority_score, inquiry_type)
            
            # Determine qualification status and priority tier
            qualification_status = "qualified" if lead_score >= 70 else "unqualified" if lead_score >= 40 else "disqualified"
            priority_tier = self._determine_priority_tier(lead_score, estimated_value)
            
            # Create CRM contact
            contact = CRMContact(
                contact_id=contact_id,
                name=name,
                company=company or "Unknown",
                company_size=company_size,
                title="Unknown", # Would need LinkedIn profile analysis
                email="", # Would need to be collected
                linkedin_profile="", # Would need to be enriched
                phone="", # Would need to be collected
                lead_score=lead_score,
                qualification_status=qualification_status,
                estimated_value=estimated_value,
                priority_tier=priority_tier,
                next_action="Initial outreach and qualification call",
                next_action_date=(datetime.now() + timedelta(days=1)).isoformat(),
                created_at=created_at,
                updated_at=datetime.now().isoformat(),
                notes=f"Imported from consultation inquiry. Original inquiry: {inquiry_text[:200]}..."
            )
            
            imported_contacts.append(contact)
            
        # Save to CRM database
        self._save_contacts(imported_contacts)
        
        logger.info(f"Imported {len(imported_contacts)} consultation inquiries into CRM system")
        return imported_contacts
        
    def _calculate_lead_score(self, inquiry_text: str, company_size: str, priority_score: int, inquiry_type: str) -> int:
        """ML-based lead scoring algorithm"""
        score = 0
        
        # Base score from consultation inquiry priority
        score += priority_score * 15  # Max 75 points from priority
        
        # Company size scoring
        size_scores = {
            "Enterprise (500+ employees)": 25,
            "Series B (50-200 employees)": 20,
            "Series A (20-50 employees)": 15,
            "Seed/Pre-Series A (5-20 employees)": 10,
            "Unknown": 5
        }
        score += size_scores.get(company_size, 5)
        
        # Inquiry type value scoring
        type_scores = {
            "fractional_cto": 20,
            "technical_architecture": 15,
            "team_building": 12,
            "nobuild_audit": 10,
            "startup_scaling": 8,
            "general_consultation": 5
        }
        score += type_scores.get(inquiry_type, 5)
        
        # Text analysis for buying intent signals
        buying_signals = [
            "need help", "looking for", "interested in", "want to discuss",
            "schedule", "call", "meeting", "budget", "timeline", "decision",
            "struggling", "problem", "challenge", "solution"
        ]
        
        text_lower = inquiry_text.lower()
        signal_count = sum(1 for signal in buying_signals if signal in text_lower)
        score += min(signal_count * 3, 15)  # Max 15 points for buying signals
        
        # Urgency indicators
        urgency_signals = ["asap", "urgent", "immediately", "this week", "next week", "soon"]
        if any(signal in text_lower for signal in urgency_signals):
            score += 10
            
        # Company maturity indicators
        maturity_signals = ["funded", "series", "revenue", "customers", "scaling", "growth"]
        if any(signal in text_lower for signal in maturity_signals):
            score += 5
            
        return min(score, 100)  # Cap at 100
        
    def _determine_priority_tier(self, lead_score: int, estimated_value: int) -> str:
        """Determine priority tier based on lead score and estimated value"""
        if lead_score >= 80 and estimated_value >= 50000:
            return "platinum"
        elif lead_score >= 70 and estimated_value >= 25000:
            return "gold"
        elif lead_score >= 50 and estimated_value >= 10000:
            return "silver"
        else:
            return "bronze"
            
    def _save_contacts(self, contacts: List[CRMContact]):
        """Save contacts to CRM database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        for contact in contacts:
            cursor.execute('''
                INSERT OR REPLACE INTO crm_contacts 
                (contact_id, name, company, company_size, title, email, linkedin_profile, phone,
                 lead_score, qualification_status, estimated_value, priority_tier, next_action,
                 next_action_date, created_at, updated_at, notes)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                contact.contact_id, contact.name, contact.company, contact.company_size,
                contact.title, contact.email, contact.linkedin_profile, contact.phone,
                contact.lead_score, contact.qualification_status, contact.estimated_value,
                contact.priority_tier, contact.next_action, contact.next_action_date,
                contact.created_at, contact.updated_at, contact.notes
            ))
            
        conn.commit()
        conn.close()
        
    def generate_automated_proposal(self, contact_id: str, inquiry_type: str = None) -> Dict:
        """Generate automated proposal with ROI calculator"""
        # Get contact information
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM crm_contacts WHERE contact_id = ?', (contact_id,))
        contact_data = cursor.fetchone()
        
        if not contact_data:
            return {"error": "Contact not found"}
            
        # Convert to dict
        columns = [description[0] for description in cursor.description]
        contact = dict(zip(columns, contact_data, strict=False))
        
        # Get appropriate template
        template_inquiry_type = inquiry_type or self._infer_inquiry_type_from_contact(contact)
        
        cursor.execute('SELECT * FROM roi_templates WHERE inquiry_type = ?', (template_inquiry_type,))
        template_data = cursor.fetchone()
        
        if not template_data:
            # Use general template
            cursor.execute('SELECT * FROM roi_templates LIMIT 1')
            template_data = cursor.fetchone()
            
        template_columns = [description[0] for description in cursor.description]
        template = dict(zip(template_columns, template_data, strict=False))
        
        # Calculate ROI specific to this client
        roi_calculation = self._calculate_client_roi(contact, json.loads(template['cost_factors']))
        
        # Generate proposal content
        proposal_content = {
            "client_name": contact['name'],
            "company_name": contact['company'],
            "template_title": template['template_name'],
            "executive_summary": self._personalize_executive_summary(contact, template),
            "problem_statement": self._personalize_problem_statement(contact, template),
            "solution_overview": self._personalize_solution_overview(contact, template),
            "roi_analysis": roi_calculation,
            "timeline": self._generate_timeline(contact, template_inquiry_type),
            "investment_proposal": self._generate_investment_proposal(contact, roi_calculation),
            "next_steps": self._generate_next_steps(contact),
            "close_probability": self._estimate_close_probability(contact, roi_calculation)
        }
        
        # Save proposal
        proposal_id = f"prop-{contact_id}-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        
        cursor.execute('''
            INSERT INTO generated_proposals 
            (proposal_id, contact_id, inquiry_id, template_used, proposal_content,
             roi_calculation, estimated_close_probability, proposal_value, status, generated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            proposal_id, contact_id, contact.get('contact_id'), template['template_id'],
            json.dumps(proposal_content), json.dumps(roi_calculation),
            proposal_content['close_probability'], contact['estimated_value'],
            'draft', datetime.now().isoformat()
        ))
        
        conn.commit()
        conn.close()
        
        logger.info(f"Generated automated proposal {proposal_id} for {contact['name']}")
        return {"proposal_id": proposal_id, "content": proposal_content}
        
    def _calculate_client_roi(self, contact: Dict, cost_factors: Dict) -> Dict:
        """Calculate ROI specific to client's situation"""
        # Extract company size for calculations
        company_size_map = {
            "Seed/Pre-Series A (5-20 employees)": 12,
            "Series A (20-50 employees)": 35,
            "Series B (50-200 employees)": 125,
            "Enterprise (500+ employees)": 750
        }
        
        team_size = company_size_map.get(contact['company_size'], 25)
        
        # Calculate based on cost factors from template
        annual_cost_savings = 0
        productivity_gains = 0
        
        if 'time_savings_per_developer' in cost_factors:
            # Team building ROI calculation
            hours_saved_per_week = cost_factors['time_savings_per_developer'] * team_size
            annual_hours_saved = hours_saved_per_week * 50  # 50 working weeks
            average_hourly_cost = cost_factors['average_developer_cost'] / (40 * 50)  # Annual to hourly
            annual_cost_savings = annual_hours_saved * average_hourly_cost
            
            # Delivery acceleration value
            delivery_acceleration = cost_factors.get('delivery_acceleration', 1.5)
            productivity_gains = team_size * cost_factors['average_developer_cost'] * (delivery_acceleration - 1) * 0.3  # 30% of acceleration value
            
        elif 'full_time_cto_cost' in cost_factors:
            # Fractional CTO ROI calculation  
            full_time_cost = cost_factors['full_time_cto_cost']
            fractional_cost = full_time_cost * (cost_factors['fractional_percentage'] / 100)
            annual_cost_savings = full_time_cost - fractional_cost
            
            # Bad decision prevention value
            decisions_prevented = cost_factors.get('bad_technical_decisions_prevented', 1)
            decision_cost = cost_factors.get('cost_per_bad_decision', 100000)
            productivity_gains = decisions_prevented * decision_cost
            
        elif 'custom_development_hours' in cost_factors:
            # NOBUILD audit ROI calculation
            dev_hours = cost_factors['custom_development_hours']
            hourly_cost = cost_factors['average_developer_hourly_cost']
            maintenance_multiplier = cost_factors.get('maintenance_multiplier', 1.5)
            annual_dev_cost = dev_hours * hourly_cost * maintenance_multiplier
            
            savings_percentage = cost_factors.get('saas_replacement_savings', 40) / 100
            annual_cost_savings = annual_dev_cost * savings_percentage
            
            # Time to market value
            time_acceleration = cost_factors.get('time_to_market_acceleration', 2)
            productivity_gains = annual_dev_cost * (time_acceleration - 1) * 0.4  # 40% of acceleration value
            
        # Calculate total ROI
        total_annual_benefit = annual_cost_savings + productivity_gains
        investment_cost = contact['estimated_value']
        
        roi_percentage = ((total_annual_benefit - investment_cost) / investment_cost) * 100 if investment_cost > 0 else 0
        payback_months = (investment_cost / (total_annual_benefit / 12)) if total_annual_benefit > 0 else 24
        
        return {
            "team_size": team_size,
            "annual_cost_savings": int(annual_cost_savings),
            "productivity_gains": int(productivity_gains),
            "total_annual_benefit": int(total_annual_benefit),
            "investment_cost": investment_cost,
            "roi_percentage": round(roi_percentage, 1),
            "payback_months": round(payback_months, 1),
            "three_year_value": int(total_annual_benefit * 3 - investment_cost)
        }
        
    def _personalize_executive_summary(self, contact: Dict, template: Dict) -> str:
        """Personalize executive summary for client"""
        base_summary = "Transform your engineering capabilities and achieve measurable business results through proven methodologies."
        
        if contact['company_size'] == "Enterprise (500+ employees)":
            return f"{base_summary} With your enterprise scale, we focus on systematic improvements that compound across large teams."
        elif "Series B" in contact['company_size']:
            return f"{base_summary} At your Series B stage, optimizing engineering efficiency directly impacts your path to profitability."
        elif "Series A" in contact['company_size']:
            return f"{base_summary} As a Series A company, building scalable engineering processes now prevents future bottlenecks."
        else:
            return f"{base_summary} For early-stage companies, establishing strong engineering foundations accelerates growth."
            
    def _personalize_problem_statement(self, contact: Dict, template: Dict) -> str:
        """Personalize problem statement for client"""
        base_problems = {
            "team_building": "Growing engineering teams often experience decreased per-person productivity due to communication overhead and process inconsistencies.",
            "fractional_cto": "Companies need strategic technical leadership but face challenges with full-time CTO costs and finding the right fit.",
            "nobuild_audit": "Engineering teams frequently build custom solutions when superior SaaS alternatives exist, leading to unnecessary costs and maintenance burden."
        }
        
        problem = base_problems.get(template.get('inquiry_type', 'general'), "Technical challenges are limiting business growth and efficiency.")
        
        # Add company-specific context
        if "startup" in contact['company'].lower() or "Seed" in contact['company_size']:
            problem += " For startups, these inefficiencies can be especially costly as resources are limited and speed-to-market is critical."
            
        return problem
        
    def _personalize_solution_overview(self, contact: Dict, template: Dict) -> str:
        """Personalize solution overview for client"""
        solutions = {
            "team_building": f"Comprehensive team transformation program tailored for {contact['company_size']} organizations, focusing on velocity optimization and scalable processes.",
            "fractional_cto": f"Strategic technical leadership engagement designed for {contact['company_size']} companies, providing executive-level technical guidance without full-time commitment.",
            "nobuild_audit": f"Technology stack optimization using #NOBUILD methodology, specifically calibrated for {contact['company_size']} operational complexity."
        }
        
        return solutions.get(template.get('inquiry_type', 'general'), f"Customized technical consulting engagement designed for {contact['company_size']} organizations.")
        
    def _generate_timeline(self, contact: Dict, inquiry_type: str) -> str:
        """Generate project timeline based on client and service type"""
        timelines = {
            "team_building": "90-day intensive program with 30-day velocity diagnostic, 45-day implementation, and 15-day optimization phase",
            "fractional_cto": "6-month initial engagement with monthly strategic reviews and quarterly roadmap updates",
            "nobuild_audit": "6-week comprehensive audit: Week 1-2 discovery, Week 3-4 analysis, Week 5-6 recommendations and roadmap",
            "general": "Customized timeline based on specific requirements and objectives"
        }
        
        timeline = timelines.get(inquiry_type, timelines["general"])
        
        # Adjust for company size
        if "Enterprise" in contact['company_size']:
            timeline += ". Extended timeline may be required for enterprise-scale implementations."
        elif "Seed" in contact['company_size']:
            timeline += ". Accelerated timeline possible for smaller teams with faster decision-making."
            
        return timeline
        
    def _generate_investment_proposal(self, contact: Dict, roi_calculation: Dict) -> Dict:
        """Generate investment proposal with options"""
        base_investment = contact['estimated_value']
        
        # Create tiered options
        options = {
            "essential": {
                "price": int(base_investment * 0.7),
                "description": "Core deliverables with standard support",
                "timeline": "Standard timeline",
                "included": ["Core methodology", "Implementation guide", "30-day follow-up"]
            },
            "recommended": {
                "price": base_investment,
                "description": "Complete program with extended support",
                "timeline": "Full timeline with optimization phase",
                "included": ["Full methodology", "Implementation support", "90-day optimization", "Team training"]
            },
            "premium": {
                "price": int(base_investment * 1.5),
                "description": "Comprehensive program with ongoing advisory",
                "timeline": "Extended engagement with 6-month advisory",
                "included": ["Full methodology", "Implementation support", "6-month advisory", "Team training", "Quarterly reviews"]
            }
        }
        
        # Add ROI context
        annual_benefit = roi_calculation.get('total_annual_benefit', 0)
        for option in options.values():
            option['roi_multiple'] = round(annual_benefit / option['price'], 1) if option['price'] > 0 else 0
            
        return options
        
    def _generate_next_steps(self, contact: Dict) -> List[str]:
        """Generate recommended next steps"""
        steps = [
            "30-minute discovery call to understand specific challenges and objectives",
            "Comprehensive assessment of current state and improvement opportunities",
            "Customized proposal with detailed ROI analysis and timeline",
            "Pilot engagement or full program kickoff"
        ]
        
        # Customize based on priority tier
        if contact['priority_tier'] == 'platinum':
            steps.insert(1, "Priority scheduling within 24-48 hours")
        elif contact['priority_tier'] == 'gold':
            steps.insert(1, "Expedited scheduling within 3-5 business days")
            
        return steps
        
    def _estimate_close_probability(self, contact: Dict, roi_calculation: Dict) -> float:
        """Estimate probability of closing based on contact and ROI data"""
        probability = 0.3  # Base probability
        
        # Lead score impact
        lead_score = contact.get('lead_score', 50)
        if lead_score >= 80:
            probability += 0.3
        elif lead_score >= 60:
            probability += 0.2
        elif lead_score >= 40:
            probability += 0.1
            
        # ROI impact
        roi_percentage = roi_calculation.get('roi_percentage', 0)
        if roi_percentage >= 300:
            probability += 0.2
        elif roi_percentage >= 200:
            probability += 0.15
        elif roi_percentage >= 100:
            probability += 0.1
            
        # Company size impact
        if "Enterprise" in contact['company_size'] or "Series B" in contact['company_size']:
            probability += 0.1
        elif "Series A" in contact['company_size']:
            probability += 0.05
            
        # Priority tier impact
        tier_bonus = {
            'platinum': 0.15,
            'gold': 0.1, 
            'silver': 0.05,
            'bronze': 0.0
        }
        probability += tier_bonus.get(contact['priority_tier'], 0)
        
        return min(probability, 0.95)  # Cap at 95%
        
    def _infer_inquiry_type_from_contact(self, contact: Dict) -> str:
        """Infer inquiry type from contact notes/data"""
        notes = contact.get('notes', '').lower()
        
        if any(keyword in notes for keyword in ['fractional cto', 'cto services', 'technical leadership']):
            return 'fractional_cto'
        elif any(keyword in notes for keyword in ['team building', 'team velocity', 'team performance']):
            return 'team_building'
        elif any(keyword in notes for keyword in ['build vs buy', 'nobuild', 'technology audit']):
            return 'nobuild_audit'
        else:
            return 'team_building'  # Default
            
    def get_sales_pipeline_summary(self) -> Dict:
        """Get comprehensive sales pipeline summary"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get contact statistics
        cursor.execute('''
            SELECT 
                COUNT(*) as total_contacts,
                AVG(lead_score) as avg_lead_score,
                SUM(estimated_value) as total_pipeline_value,
                COUNT(CASE WHEN qualification_status = 'qualified' THEN 1 END) as qualified_leads,
                COUNT(CASE WHEN priority_tier = 'platinum' THEN 1 END) as platinum_leads,
                COUNT(CASE WHEN priority_tier = 'gold' THEN 1 END) as gold_leads
            FROM crm_contacts
        ''')
        
        stats = cursor.fetchone()
        
        # Get proposal statistics
        cursor.execute('''
            SELECT 
                COUNT(*) as total_proposals,
                AVG(estimated_close_probability) as avg_close_probability,
                SUM(proposal_value) as total_proposal_value,
                COUNT(CASE WHEN status = 'sent' THEN 1 END) as sent_proposals
            FROM generated_proposals
        ''')
        
        proposal_stats = cursor.fetchone()
        
        conn.close()
        
        return {
            "total_contacts": stats[0] or 0,
            "avg_lead_score": round(stats[1] or 0, 1),
            "total_pipeline_value": stats[2] or 0,
            "qualified_leads": stats[3] or 0,
            "platinum_leads": stats[4] or 0,
            "gold_leads": stats[5] or 0,
            "total_proposals": proposal_stats[0] or 0,
            "avg_close_probability": round((proposal_stats[1] or 0) * 100, 1),
            "total_proposal_value": proposal_stats[2] or 0,
            "sent_proposals": proposal_stats[3] or 0,
            "pipeline_health_score": self._calculate_pipeline_health_score(stats, proposal_stats),
            "projected_annual_revenue": self._project_annual_revenue(stats, proposal_stats)
        }
        
    def _calculate_pipeline_health_score(self, stats, proposal_stats) -> float:
        """Calculate overall pipeline health score (0-100)"""
        score = 0
        
        # Contact quality (40% of score)
        total_contacts = stats[0] or 1
        qualified_ratio = (stats[3] or 0) / total_contacts
        avg_score = stats[1] or 0
        
        score += qualified_ratio * 20  # Up to 20 points for qualification ratio
        score += (avg_score / 100) * 20  # Up to 20 points for average lead score
        
        # Pipeline value (30% of score)
        pipeline_value = stats[2] or 0
        if pipeline_value >= 1000000:  # $1M+ pipeline
            score += 30
        elif pipeline_value >= 500000:  # $500K+ pipeline
            score += 20
        elif pipeline_value >= 100000:  # $100K+ pipeline
            score += 10
            
        # Proposal activity (30% of score)
        total_proposals = proposal_stats[0] or 0
        avg_close_prob = proposal_stats[1] or 0
        
        if total_proposals > 0:
            score += min((total_proposals / total_contacts) * 15, 15)  # Up to 15 points for proposal ratio
            score += avg_close_prob * 15  # Up to 15 points for close probability
            
        return min(score, 100)
        
    def _project_annual_revenue(self, stats, proposal_stats) -> int:
        """Project annual revenue based on current pipeline"""
        total_pipeline_value = stats[2] or 0
        avg_close_probability = proposal_stats[1] or 0.3
        
        # Assume current pipeline represents 3 months of activity
        quarterly_expected_revenue = total_pipeline_value * avg_close_probability
        annual_projection = quarterly_expected_revenue * 4
        
        return int(annual_projection)

def main():
    """Demonstrate Epic 7 Week 1 Sales Automation System"""
    print("🚀 Epic 7 Week 1 Sales Automation System")
    print("Converting working lead generation into systematic $2M+ ARR sales engine\n")
    
    # Initialize sales automation engine
    engine = SalesAutomationEngine()
    
    # Import existing consultation inquiries
    print("📥 Importing consultation inquiries into CRM system...")
    contacts = engine.import_consultation_inquiries()
    print(f"✅ Imported {len(contacts)} contacts into CRM system\n")
    
    # Generate proposals for qualified leads
    print("📋 Generating automated proposals for qualified leads...")
    qualified_contacts = [c for c in contacts if c.qualification_status == 'qualified']
    
    for contact in qualified_contacts[:3]:  # Generate for top 3 qualified leads
        proposal = engine.generate_automated_proposal(contact.contact_id)
        if 'error' not in proposal:
            print(f"✅ Generated proposal for {contact.name} - Close probability: {proposal['content']['close_probability']:.1%}")
    
    print()
    
    # Get pipeline summary
    print("📊 Sales Pipeline Summary:")
    summary = engine.get_sales_pipeline_summary()
    
    print(f"📈 Total Contacts: {summary['total_contacts']}")
    print(f"🎯 Qualified Leads: {summary['qualified_leads']}")
    print(f"⭐ Platinum Leads: {summary['platinum_leads']}")
    print(f"🥇 Gold Leads: {summary['gold_leads']}")
    print(f"💰 Total Pipeline Value: ${summary['total_pipeline_value']:,}")
    print(f"📑 Generated Proposals: {summary['total_proposals']}")
    print(f"🎲 Average Close Probability: {summary['avg_close_probability']}%")
    print(f"🏥 Pipeline Health Score: {summary['pipeline_health_score']:.1f}/100")
    print(f"📅 Projected Annual Revenue: ${summary['projected_annual_revenue']:,}")
    
    print(f"\n✅ Epic 7 Week 1 Sales Automation System operational!")
    print(f"🎯 Ready to systematically convert {summary['qualified_leads']} qualified leads")
    print(f"💼 ${summary['total_pipeline_value']:,} pipeline value under automated management")
    
    if summary['projected_annual_revenue'] >= 2000000:
        print("🎉 $2M+ ARR target achievable with current pipeline!")
    else:
        needed_additional = 2000000 - summary['projected_annual_revenue']
        print(f"📈 Need ${needed_additional:,} additional pipeline for $2M ARR target")

if __name__ == "__main__":
    main()