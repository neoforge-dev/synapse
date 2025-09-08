#!/usr/bin/env python3
"""
Epic 7 CRM Business Logic Tests - REVENUE CRITICAL
Tests for CRM operations and pipeline management protecting $1.158M business pipeline
"""

import pytest
import sqlite3
import tempfile
import json
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import Mock, patch
import sys

# Add project root to path for imports
project_root = Path(__file__).parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from business_development.epic7_sales_automation import SalesAutomationEngine, CRMContact

class TestEpic7CRMCore:
    """Test Epic 7 CRM core operations - HIGHEST PRIORITY"""
    
    @pytest.fixture
    def temp_sales_db(self):
        """Create temporary sales automation database"""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
            db_path = tmp.name
        
        # Initialize the database
        engine = SalesAutomationEngine(db_path=db_path)
        yield db_path
        
        # Cleanup
        Path(db_path).unlink(missing_ok=True)
    
    @pytest.fixture
    def sales_engine(self, temp_sales_db):
        """Sales automation engine with test database"""
        return SalesAutomationEngine(db_path=temp_sales_db)
    
    def test_database_initialization(self, sales_engine):
        """Test that database initializes correctly with all required tables"""
        conn = sqlite3.connect(sales_engine.db_path)
        cursor = conn.cursor()
        
        # Check all critical tables exist
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        
        required_tables = [
            'crm_contacts',
            'lead_scoring_history',
            'generated_proposals',
            'sales_pipeline',
            'linkedin_automation_tracking',
            'ab_test_campaigns',
            'ab_test_results',
            'revenue_forecasts',
            'roi_templates'
        ]
        
        for table in required_tables:
            assert table in tables, f"Critical table {table} missing from database"
        
        conn.close()
    
    def test_contact_crud_operations(self, sales_engine):
        """Test CRM contact CRUD operations protecting 16 contacts, $1.158M pipeline"""
        # Create test contact
        contact = CRMContact(
            contact_id="test-crm-001",
            name="Sarah Chen",
            company="DataFlow Analytics",
            company_size="Series B (50-200 employees)",
            title="CTO",
            email="sarah@dataflow.com",
            linkedin_profile="linkedin.com/in/sarachen",
            phone="+1-555-0123",
            lead_score=85,
            qualification_status="qualified",
            estimated_value=120000,
            priority_tier="platinum",
            next_action="Initial outreach and qualification call",
            next_action_date=(datetime.now() + timedelta(days=1)).isoformat(),
            created_at=datetime.now().isoformat(),
            updated_at=datetime.now().isoformat(),
            notes="High-value fractional CTO prospect from LinkedIn"
        )
        
        # Save contact
        sales_engine._save_contacts([contact])
        
        # Read contact back
        conn = sqlite3.connect(sales_engine.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM crm_contacts WHERE contact_id = ?", (contact.contact_id,))
        saved_contact = cursor.fetchone()
        conn.close()
        
        assert saved_contact is not None, "Contact was not saved to database"
        assert saved_contact[1] == "Sarah Chen", "Contact name not saved correctly"
        assert saved_contact[8] == 85, "Lead score not saved correctly"
        assert saved_contact[10] == 120000, "Estimated value not saved correctly"
    
    def test_consultation_inquiry_import(self, sales_engine):
        """Test import of existing consultation inquiries into CRM"""
        # Mock consultation database with test data
        consultation_db = sales_engine.consultation_db_path
        conn = sqlite3.connect(consultation_db)
        cursor = conn.cursor()
        
        # Create consultation_inquiries table if it doesn't exist
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS consultation_inquiries (
                inquiry_id TEXT PRIMARY KEY,
                contact_name TEXT,
                company TEXT,
                company_size TEXT,
                inquiry_type TEXT,
                inquiry_text TEXT,
                estimated_value INTEGER,
                priority_score INTEGER,
                status TEXT DEFAULT 'new',
                created_at TEXT
            )
        ''')
        
        # Insert test consultation inquiry
        cursor.execute('''
            INSERT OR REPLACE INTO consultation_inquiries
            (inquiry_id, contact_name, company, company_size, inquiry_type, inquiry_text,
             estimated_value, priority_score, status, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            "test-inquiry-001",
            "Michael Rodriguez", 
            "FinTech Solutions Corp",
            "Enterprise (500+ employees)",
            "team_building",
            "Our 200+ engineering team is struggling with velocity. Need systematic approach.",
            85000,
            4,
            "new",
            datetime.now().isoformat()
        ))
        conn.commit()
        conn.close()
        
        # Import consultation inquiries
        imported_contacts = sales_engine.import_consultation_inquiries(include_synthetic=False)
        
        assert len(imported_contacts) > 0, "No contacts imported from consultation inquiries"
        
        # Verify imported contact data
        contact = imported_contacts[0]
        assert contact.name == "Michael Rodriguez"
        assert contact.estimated_value == 85000
        assert contact.lead_score > 0, "Lead score should be calculated for imported contacts"
        assert contact.priority_tier in ['platinum', 'gold', 'silver', 'bronze']
    
    def test_lead_scoring_algorithm(self, sales_engine):
        """Test ML-based lead scoring algorithm accuracy"""
        # Test high-value inquiry
        high_value_text = "We need strategic technical leadership for our Series B growth. Looking for fractional CTO to guide architecture decisions and team scaling. Budget approved and timeline is urgent."
        
        score = sales_engine._enhanced_ml_lead_scoring(
            inquiry_text=high_value_text,
            company_size="Series B (50-200 employees)",
            priority_score=5,
            inquiry_type="fractional_cto",
            company="DataFlow Analytics"
        )
        
        assert score >= 80, f"High-value inquiry should score 80+, got {score}"
        
        # Test low-value inquiry
        low_value_text = "Nice post"
        
        score = sales_engine._enhanced_ml_lead_scoring(
            inquiry_text=low_value_text,
            company_size="Unknown",
            priority_score=1,
            inquiry_type="general",
            company="Unknown"
        )
        
        assert score <= 50, f"Low-value inquiry should score 50 or less, got {score}"
    
    def test_priority_tier_determination(self, sales_engine):
        """Test priority tier assignment for pipeline management"""
        # Platinum tier
        tier = sales_engine._determine_priority_tier(lead_score=85, estimated_value=120000)
        assert tier == "platinum", f"Expected platinum tier, got {tier}"
        
        # Gold tier
        tier = sales_engine._determine_priority_tier(lead_score=75, estimated_value=50000)
        assert tier == "gold", f"Expected gold tier, got {tier}"
        
        # Silver tier
        tier = sales_engine._determine_priority_tier(lead_score=60, estimated_value=25000)
        assert tier == "silver", f"Expected silver tier, got {tier}"
        
        # Bronze tier
        tier = sales_engine._determine_priority_tier(lead_score=30, estimated_value=5000)
        assert tier == "bronze", f"Expected bronze tier, got {tier}"


class TestEpic7ProposalGeneration:
    """Test automated proposal generation and ROI calculations"""
    
    @pytest.fixture
    def temp_sales_db(self):
        """Create temporary sales automation database"""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
            db_path = tmp.name
        
        engine = SalesAutomationEngine(db_path=db_path)
        yield db_path
        
        Path(db_path).unlink(missing_ok=True)
    
    @pytest.fixture
    def sales_engine(self, temp_sales_db):
        """Sales automation engine with test database"""
        return SalesAutomationEngine(db_path=temp_sales_db)
    
    @pytest.fixture
    def test_contact(self, sales_engine):
        """Create test contact for proposal generation"""
        contact = CRMContact(
            contact_id="test-proposal-contact",
            name="Jennifer Kim",
            company="Healthcare Innovation Labs",
            company_size="Series A (20-50 employees)",
            title="VP Engineering",
            email="jen@healthtech.com",
            linkedin_profile="linkedin.com/in/jenniferk",
            phone="+1-555-0456",
            lead_score=75,
            qualification_status="qualified",
            estimated_value=35000,
            priority_tier="gold",
            next_action="Generate proposal",
            next_action_date=datetime.now().isoformat(),
            created_at=datetime.now().isoformat(),
            updated_at=datetime.now().isoformat(),
            notes="NOBUILD audit inquiry - reducing custom development overhead"
        )
        
        sales_engine._save_contacts([contact])
        return contact
    
    def test_proposal_generation(self, sales_engine, test_contact):
        """Test automated proposal generation with ROI calculations"""
        proposal = sales_engine.generate_automated_proposal(
            contact_id=test_contact.contact_id,
            inquiry_type="nobuild_audit"
        )
        
        assert 'error' not in proposal, f"Proposal generation failed: {proposal.get('error')}"
        assert 'proposal_id' in proposal, "Proposal ID not generated"
        assert 'content' in proposal, "Proposal content not generated"
        
        content = proposal['content']
        
        # Verify proposal structure
        required_fields = [
            'client_name', 'company_name', 'template_title', 
            'executive_summary', 'problem_statement', 'solution_overview',
            'roi_analysis', 'timeline', 'investment_proposal', 'next_steps'
        ]
        
        for field in required_fields:
            assert field in content, f"Required field {field} missing from proposal"
        
        # Verify ROI calculations
        roi = content['roi_analysis']
        assert 'total_annual_benefit' in roi, "ROI analysis missing total annual benefit"
        assert 'roi_percentage' in roi, "ROI analysis missing ROI percentage"
        assert 'payback_months' in roi, "ROI analysis missing payback period"
        assert roi['total_annual_benefit'] > 0, "ROI should show positive benefit"
    
    def test_roi_calculation_accuracy(self, sales_engine, test_contact):
        """Test ROI calculation accuracy for different service types"""
        # Test team building ROI
        contact_team_building = CRMContact(
            contact_id="test-team-building",
            name="Test Client",
            company="Test Company",
            company_size="Series B (50-200 employees)",
            title="CTO",
            email="test@test.com",
            linkedin_profile="",
            phone="",
            lead_score=75,
            qualification_status="qualified",
            estimated_value=75000,
            priority_tier="gold",
            next_action="",
            next_action_date="",
            created_at="",
            updated_at="",
            notes="Team building inquiry"
        )
        
        sales_engine._save_contacts([contact_team_building])
        
        # Calculate ROI
        conn = sqlite3.connect(sales_engine.db_path)
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM crm_contacts WHERE contact_id = ?', (contact_team_building.contact_id,))
        contact_data = cursor.fetchone()
        columns = [description[0] for description in cursor.description]
        contact_dict = dict(zip(columns, contact_data, strict=False))
        conn.close()
        
        cost_factors = {
            'time_savings_per_developer': 8,
            'average_developer_cost': 150000,
            'delivery_acceleration': 2.5,
            'quality_improvement': 40
        }
        
        roi = sales_engine._calculate_client_roi(contact_dict, cost_factors)
        
        assert roi['team_size'] > 0, "Team size should be calculated"
        assert roi['annual_cost_savings'] > 0, "Should show annual cost savings"
        assert roi['productivity_gains'] > 0, "Should show productivity gains"
        assert roi['roi_percentage'] > 100, "Team building should show strong ROI"
    
    def test_proposal_close_probability(self, sales_engine, test_contact):
        """Test close probability estimation accuracy"""
        proposal = sales_engine.generate_automated_proposal(test_contact.contact_id)
        close_prob = proposal['content']['close_probability']
        
        assert 0 <= close_prob <= 1.0, f"Close probability {close_prob} should be between 0 and 1"
        
        # High-value qualified leads should have higher close probability
        if test_contact.lead_score >= 70 and test_contact.estimated_value >= 25000:
            assert close_prob >= 0.4, f"High-value qualified lead should have close probability >= 40%, got {close_prob:.1%}"


class TestEpic7PipelineManagement:
    """Test sales pipeline management and revenue tracking"""
    
    @pytest.fixture
    def temp_sales_db(self):
        """Create temporary sales automation database"""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
            db_path = tmp.name
        
        engine = SalesAutomationEngine(db_path=db_path)
        yield db_path
        
        Path(db_path).unlink(missing_ok=True)
    
    @pytest.fixture
    def sales_engine_with_data(self, temp_sales_db):
        """Sales engine with populated test data"""
        engine = SalesAutomationEngine(db_path=temp_sales_db)
        
        # Import synthetic consultation data for comprehensive testing
        contacts = engine.import_consultation_inquiries(include_synthetic=True)
        
        # Generate proposals for qualified leads
        qualified_contacts = [c for c in contacts if c.qualification_status == 'qualified']
        for contact in qualified_contacts[:5]:  # Generate 5 proposals for testing
            engine.generate_automated_proposal(contact.contact_id)
        
        return engine
    
    def test_pipeline_summary_calculation(self, sales_engine_with_data):
        """Test sales pipeline summary calculations"""
        summary = sales_engine_with_data.get_sales_pipeline_summary()
        
        # Verify summary structure
        required_fields = [
            'total_contacts', 'avg_lead_score', 'total_pipeline_value',
            'qualified_leads', 'platinum_leads', 'gold_leads',
            'total_proposals', 'avg_close_probability', 'total_proposal_value',
            'sent_proposals', 'pipeline_health_score', 'projected_annual_revenue'
        ]
        
        for field in required_fields:
            assert field in summary, f"Required field {field} missing from pipeline summary"
        
        # Verify data consistency
        assert summary['total_contacts'] > 0, "Should have contacts in pipeline"
        assert summary['qualified_leads'] <= summary['total_contacts'], "Qualified leads should not exceed total contacts"
        assert summary['total_pipeline_value'] > 0, "Should have pipeline value"
        assert 0 <= summary['pipeline_health_score'] <= 100, "Health score should be between 0-100"
    
    def test_revenue_forecasting(self, sales_engine_with_data):
        """Test revenue forecasting calculations"""
        forecast = sales_engine_with_data.generate_revenue_forecast("annual")
        
        # Verify forecast structure
        required_fields = [
            'forecast_period', 'current_pipeline_revenue', 'growth_pipeline_revenue',
            'total_projected_revenue', 'confidence_interval', 'tier_breakdown',
            'forecast_date', 'arr_target_achievement'
        ]
        
        for field in required_fields:
            assert field in forecast, f"Required field {field} missing from revenue forecast"
        
        # Verify ARR target tracking
        arr_data = forecast['arr_target_achievement']
        assert arr_data['target'] == 2000000, "ARR target should be $2M"
        assert arr_data['projected'] > 0, "Should have projected revenue"
        assert arr_data['achievement_percentage'] >= 0, "Achievement percentage should be non-negative"
        
        # Verify confidence intervals
        confidence = forecast['confidence_interval']
        assert confidence['min'] < confidence['max'], "Min confidence should be less than max"
        assert confidence['min'] > 0, "Min confidence should be positive"
    
    def test_pipeline_health_score(self, sales_engine_with_data):
        """Test pipeline health score calculation"""
        summary = sales_engine_with_data.get_sales_pipeline_summary()
        health_score = summary['pipeline_health_score']
        
        # Health score should be reasonable for test data
        assert 0 <= health_score <= 100, "Health score should be between 0-100"
        
        # With qualified leads and proposals, health score should be decent
        if summary['qualified_leads'] > 0 and summary['total_proposals'] > 0:
            assert health_score >= 30, "Health score should be reasonable with qualified leads and proposals"
    
    def test_business_continuity_validation(self, sales_engine_with_data):
        """CRITICAL: Test that business continuity is maintained during operations"""
        # Verify $1.158M pipeline is protected
        summary = sales_engine_with_data.get_sales_pipeline_summary()
        
        # This should represent realistic pipeline value for 15+ contacts
        expected_min_pipeline = 500000  # Minimum pipeline value expected
        
        assert summary['total_pipeline_value'] >= expected_min_pipeline, \
            f"Pipeline value ${summary['total_pipeline_value']:,} below expected minimum ${expected_min_pipeline:,}"
        
        # Verify all contacts are accessible
        conn = sqlite3.connect(sales_engine_with_data.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM crm_contacts")
        contact_count = cursor.fetchone()[0]
        conn.close()
        
        assert contact_count >= 15, f"Expected at least 15 contacts, got {contact_count}"
        
        # Verify database integrity
        assert Path(sales_engine_with_data.db_path).exists(), "Sales database file should exist"
        assert Path(sales_engine_with_data.db_path).stat().st_size > 0, "Sales database should not be empty"


class TestEpic7WebInterface:
    """Test Epic 7 web interface functionality"""
    
    @pytest.fixture
    def test_client(self):
        """Test client for Epic 7 web interface"""
        try:
            from fastapi.testclient import TestClient
            from business_development.epic7_web_interface import app
            return TestClient(app)
        except ImportError:
            pytest.skip("Epic 7 web interface not available")
    
    def test_dashboard_endpoint(self, test_client):
        """Test dashboard endpoint responds correctly"""
        if test_client is None:
            pytest.skip("Test client not available")
            
        response = test_client.get("/")
        assert response.status_code == 200, "Dashboard should be accessible"
        
        # Check that response contains HTML
        assert "text/html" in response.headers.get("content-type", ""), "Dashboard should return HTML"
    
    def test_api_pipeline_summary(self, test_client):
        """Test API pipeline summary endpoint"""
        if test_client is None:
            pytest.skip("Test client not available")
            
        response = test_client.get("/api/pipeline-summary")
        assert response.status_code == 200, "Pipeline summary API should be accessible"
        
        # Verify JSON response structure
        data = response.json()
        assert isinstance(data, dict), "Pipeline summary should return dictionary"
        assert "total_contacts" in data, "Pipeline summary should include contact count"
    
    def test_contact_management_endpoints(self, test_client):
        """Test contact management API endpoints"""
        if test_client is None:
            pytest.skip("Test client not available")
            
        # Test contacts page
        response = test_client.get("/contacts")
        assert response.status_code == 200, "Contacts page should be accessible"
        
        # Test proposals page
        response = test_client.get("/proposals")
        assert response.status_code == 200, "Proposals page should be accessible"
        
        # Test analytics page
        response = test_client.get("/analytics")
        assert response.status_code == 200, "Analytics page should be accessible"


if __name__ == "__main__":
    # Run tests with detailed output
    pytest.main([__file__, "-v", "--tb=short"])