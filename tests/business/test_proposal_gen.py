#!/usr/bin/env python3
"""
Epic 7 Proposal Generation Tests
Tests for automated proposal generation and ROI calculation accuracy
"""

import pytest
import sqlite3
import tempfile
import json
from datetime import datetime
from pathlib import Path
import sys

# Add project root to path for imports
project_root = Path(__file__).parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from business_development.epic7_sales_automation import SalesAutomationEngine, CRMContact

class TestProposalGeneration:
    """Test automated proposal generation functionality"""
    
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
    def test_contacts(self, sales_engine):
        """Create test contacts for different service types"""
        contacts = [
            CRMContact(
                contact_id="team-building-client",
                name="Sarah Johnson",
                company="TechGrowth Inc",
                company_size="Series A (20-50 employees)",
                title="VP Engineering",
                email="sarah@techgrowth.com",
                linkedin_profile="linkedin.com/in/sarahjohnson",
                phone="+1-555-0123",
                lead_score=78,
                qualification_status="qualified",
                estimated_value=45000,
                priority_tier="gold",
                next_action="Generate proposal",
                next_action_date=datetime.now().isoformat(),
                created_at=datetime.now().isoformat(),
                updated_at=datetime.now().isoformat(),
                notes="Team building inquiry - 25-person team struggling with velocity"
            ),
            CRMContact(
                contact_id="fractional-cto-client",
                name="Michael Chen",
                company="ScaleUp Solutions",
                company_size="Series B (50-200 employees)",
                title="CEO",
                email="michael@scaleup.com",
                linkedin_profile="linkedin.com/in/michaelchen",
                phone="+1-555-0456",
                lead_score=92,
                qualification_status="qualified",
                estimated_value=120000,
                priority_tier="platinum",
                next_action="Generate proposal",
                next_action_date=datetime.now().isoformat(),
                created_at=datetime.now().isoformat(),
                updated_at=datetime.now().isoformat(),
                notes="Fractional CTO inquiry - need strategic technical leadership"
            ),
            CRMContact(
                contact_id="nobuild-audit-client",
                name="Jennifer Park",
                company="DevTools Corp",
                company_size="Series A (20-50 employees)",
                title="CTO",
                email="jen@devtools.com",
                linkedin_profile="linkedin.com/in/jenniferpark",
                phone="+1-555-0789",
                lead_score=65,
                qualification_status="qualified",
                estimated_value=35000,
                priority_tier="silver",
                next_action="Generate proposal",
                next_action_date=datetime.now().isoformat(),
                created_at=datetime.now().isoformat(),
                updated_at=datetime.now().isoformat(),
                notes="NOBUILD audit inquiry - too much custom development"
            )
        ]
        
        sales_engine._save_contacts(contacts)
        return contacts
    
    def test_team_building_proposal_generation(self, sales_engine, test_contacts):
        """Test automated proposal generation for team building services"""
        client = next(c for c in test_contacts if c.contact_id == "team-building-client")
        
        proposal = sales_engine.generate_automated_proposal(
            contact_id=client.contact_id,
            inquiry_type="team_building"
        )
        
        assert 'error' not in proposal, f"Proposal generation failed: {proposal.get('error')}"
        assert 'proposal_id' in proposal, "Proposal ID not generated"
        assert 'content' in proposal, "Proposal content not generated"
        
        content = proposal['content']
        
        # Verify personalization
        assert client.name in content['client_name'], "Client name not personalized"
        assert client.company in content['company_name'], "Company name not personalized"
        
        # Verify team building specific content
        assert "team" in content['template_title'].lower(), "Should be team building proposal"
        assert "velocity" in content['executive_summary'].lower() or "performance" in content['executive_summary'].lower()
        
        # Verify ROI calculations are team building specific
        roi = content['roi_analysis']
        assert 'team_size' in roi, "Team building ROI should include team size"
        assert roi['team_size'] > 0, "Team size should be calculated"
        assert roi['annual_cost_savings'] > 0, "Should show cost savings"
        assert roi['productivity_gains'] > 0, "Should show productivity gains"
    
    def test_fractional_cto_proposal_generation(self, sales_engine, test_contacts):
        """Test automated proposal generation for fractional CTO services"""
        client = next(c for c in test_contacts if c.contact_id == "fractional-cto-client")
        
        proposal = sales_engine.generate_automated_proposal(
            contact_id=client.contact_id,
            inquiry_type="fractional_cto"
        )
        
        assert 'error' not in proposal, "Fractional CTO proposal generation failed"
        
        content = proposal['content']
        
        # Verify fractional CTO specific content
        assert "cto" in content['template_title'].lower(), "Should be fractional CTO proposal"
        assert "technical leadership" in content['executive_summary'].lower()
        
        # Verify ROI calculations are fractional CTO specific
        roi = content['roi_analysis']
        assert roi['investment_cost'] == client.estimated_value, "Investment cost should match estimated value"
        assert roi['roi_percentage'] > 0, "Fractional CTO should show positive ROI"
        
        # High-value fractional CTO should have strong ROI
        if client.estimated_value >= 100000:
            assert roi['roi_percentage'] >= 200, "High-value fractional CTO should show strong ROI (200%+)"
    
    def test_nobuild_audit_proposal_generation(self, sales_engine, test_contacts):
        """Test automated proposal generation for NOBUILD audit services"""
        client = next(c for c in test_contacts if c.contact_id == "nobuild-audit-client")
        
        proposal = sales_engine.generate_automated_proposal(
            contact_id=client.contact_id,
            inquiry_type="nobuild_audit"
        )
        
        assert 'error' not in proposal, "NOBUILD audit proposal generation failed"
        
        content = proposal['content']
        
        # Verify NOBUILD specific content
        assert "nobuild" in content['template_title'].lower() or "build vs buy" in content['template_title'].lower()
        assert "audit" in content['template_title'].lower()
        
        # Verify ROI calculations are NOBUILD specific
        roi = content['roi_analysis']
        assert roi['annual_cost_savings'] > 0, "NOBUILD audit should show cost savings"
        assert roi['payback_months'] <= 12, "NOBUILD audit should have quick payback"


class TestROICalculations:
    """Test ROI calculation accuracy for different service types"""
    
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
    
    def test_team_building_roi_calculation(self, sales_engine):
        """Test ROI calculation accuracy for team building services"""
        contact_data = {
            'name': 'Test Client',
            'company': 'Test Company',
            'company_size': 'Series B (50-200 employees)',
            'estimated_value': 75000
        }
        
        cost_factors = {
            'time_savings_per_developer': 8,  # 8 hours per week per developer
            'average_developer_cost': 150000,  # Annual cost
            'delivery_acceleration': 2.5,  # 2.5x faster delivery
            'quality_improvement': 40  # 40% fewer bugs
        }
        
        roi = sales_engine._calculate_client_roi(contact_data, cost_factors)
        
        # Verify calculations
        expected_team_size = 125  # Series B (50-200) maps to ~125
        assert roi['team_size'] == expected_team_size, f"Expected team size {expected_team_size}, got {roi['team_size']}"
        
        # Verify substantial cost savings
        expected_annual_savings = expected_team_size * 8 * 50 * (150000 / (40 * 50))  # Team * hours * weeks * hourly rate
        assert abs(roi['annual_cost_savings'] - expected_annual_savings) < 1000, "Annual cost savings calculation incorrect"
        
        # Verify positive ROI
        assert roi['roi_percentage'] > 100, "Team building should show strong ROI"
        assert roi['payback_months'] <= 12, "Team building should have reasonable payback period"
    
    def test_fractional_cto_roi_calculation(self, sales_engine):
        """Test ROI calculation accuracy for fractional CTO services"""
        contact_data = {
            'name': 'Test Client',
            'company': 'Test Company', 
            'company_size': 'Series B (50-200 employees)',
            'estimated_value': 120000
        }
        
        cost_factors = {
            'full_time_cto_cost': 300000,  # Annual full-time CTO cost
            'fractional_percentage': 40,   # 40% of full-time
            'bad_technical_decisions_prevented': 2,  # Major decisions per year
            'cost_per_bad_decision': 150000,  # Cost of wrong tech choice
            'team_productivity_increase': 25  # 25% improvement
        }
        
        roi = sales_engine._calculate_client_roi(contact_data, cost_factors)
        
        # Verify cost savings calculation
        expected_savings = 300000 - (300000 * 0.4)  # Full-time cost - fractional cost
        assert roi['annual_cost_savings'] == expected_savings, "Fractional CTO cost savings incorrect"
        
        # Verify productivity gains
        expected_gains = 2 * 150000  # Decisions prevented * cost per decision
        assert roi['productivity_gains'] == expected_gains, "Productivity gains calculation incorrect"
        
        # Verify strong ROI for fractional CTO
        assert roi['roi_percentage'] >= 200, "Fractional CTO should show strong ROI (200%+)"
    
    def test_nobuild_audit_roi_calculation(self, sales_engine):
        """Test ROI calculation accuracy for NOBUILD audit services"""
        contact_data = {
            'name': 'Test Client',
            'company': 'Test Company',
            'company_size': 'Series A (20-50 employees)',
            'estimated_value': 35000
        }
        
        cost_factors = {
            'custom_development_hours': 2000,  # Hours per year
            'average_developer_hourly_cost': 100,  # Hourly rate
            'maintenance_multiplier': 1.5,  # Ongoing maintenance cost
            'saas_replacement_savings': 50,  # 50% savings
            'time_to_market_acceleration': 3  # 3x faster
        }
        
        roi = sales_engine._calculate_client_roi(contact_data, cost_factors)
        
        # Verify calculations
        expected_annual_dev_cost = 2000 * 100 * 1.5  # Hours * rate * maintenance
        expected_savings = expected_annual_dev_cost * 0.5  # 50% savings
        
        assert abs(roi['annual_cost_savings'] - expected_savings) < 1000, "NOBUILD savings calculation incorrect"
        assert roi['productivity_gains'] > 0, "Should show productivity gains from faster delivery"
        assert roi['roi_percentage'] > 400, "NOBUILD audit should show very strong ROI"
    
    def test_roi_edge_cases(self, sales_engine):
        """Test ROI calculation edge cases and boundary conditions"""
        # Zero investment case
        contact_data = {
            'name': 'Test',
            'company': 'Test',
            'company_size': 'Seed/Pre-Series A (5-20 employees)',
            'estimated_value': 0
        }
        
        cost_factors = {
            'time_savings_per_developer': 5,
            'average_developer_cost': 120000
        }
        
        roi = sales_engine._calculate_client_roi(contact_data, cost_factors)
        
        # Should handle zero investment gracefully
        assert roi['investment_cost'] == 0
        assert roi['roi_percentage'] == 0, "Zero investment should result in 0 ROI percentage"
        
        # Very small team case
        small_team_data = {
            'name': 'Small Team',
            'company': 'Startup',
            'company_size': 'Seed/Pre-Series A (5-20 employees)',
            'estimated_value': 15000
        }
        
        roi = sales_engine._calculate_client_roi(small_team_data, cost_factors)
        
        assert roi['team_size'] > 0, "Should calculate team size for small companies"
        assert roi['team_size'] <= 20, "Small team size should be reasonable"


class TestProposalPersonalization:
    """Test proposal content personalization"""
    
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
    
    def test_executive_summary_personalization(self, sales_engine):
        """Test executive summary personalization by company stage"""
        template = {'inquiry_type': 'team_building'}
        
        # Test different company sizes
        company_scenarios = [
            {
                'company_size': 'Enterprise (500+ employees)',
                'expected_keywords': ['enterprise', 'scale', 'large teams']
            },
            {
                'company_size': 'Series B (50-200 employees)', 
                'expected_keywords': ['series b', 'profitability', 'growth']
            },
            {
                'company_size': 'Series A (20-50 employees)',
                'expected_keywords': ['series a', 'scalable', 'processes']
            },
            {
                'company_size': 'Seed/Pre-Series A (5-20 employees)',
                'expected_keywords': ['early-stage', 'foundations', 'accelerates']
            }
        ]
        
        for scenario in company_scenarios:
            contact = {'company_size': scenario['company_size']}
            summary = sales_engine._personalize_executive_summary(contact, template)
            
            # Should contain stage-appropriate language
            summary_lower = summary.lower()
            stage_match = any(keyword in summary_lower for keyword in scenario['expected_keywords'])
            assert stage_match, f"Executive summary for {scenario['company_size']} should contain stage-appropriate keywords"
    
    def test_problem_statement_personalization(self, sales_engine):
        """Test problem statement personalization"""
        template = {'inquiry_type': 'fractional_cto'}
        
        # Test startup-specific problem statement
        startup_contact = {
            'company': 'StartupTech Inc',
            'company_size': 'Seed/Pre-Series A (5-20 employees)'
        }
        
        problem_statement = sales_engine._personalize_problem_statement(startup_contact, template)
        
        # Should include startup-specific challenges
        assert 'startup' in problem_statement.lower(), "Should mention startup-specific challenges"
        assert len(problem_statement) > 100, "Problem statement should be substantial"
    
    def test_solution_overview_personalization(self, sales_engine):
        """Test solution overview personalization by service type"""
        service_types = [
            {
                'inquiry_type': 'team_building',
                'expected_keywords': ['team transformation', 'velocity', 'processes']
            },
            {
                'inquiry_type': 'fractional_cto',
                'expected_keywords': ['strategic', 'technical leadership', 'guidance']
            },
            {
                'inquiry_type': 'nobuild_audit',
                'expected_keywords': ['technology stack', 'optimization', 'nobuild']
            }
        ]
        
        for service in service_types:
            contact = {'company_size': 'Series A (20-50 employees)'}
            template = {'inquiry_type': service['inquiry_type']}
            
            solution = sales_engine._personalize_solution_overview(contact, template)
            
            # Should contain service-appropriate keywords
            solution_lower = solution.lower()
            keyword_match = any(keyword in solution_lower for keyword in service['expected_keywords'])
            assert keyword_match, f"Solution for {service['inquiry_type']} should contain appropriate keywords"
    
    def test_timeline_personalization(self, sales_engine):
        """Test timeline personalization by company size and service type"""
        # Enterprise timeline should mention extended timeline
        enterprise_contact = {'company_size': 'Enterprise (500+ employees)'}
        timeline = sales_engine._generate_timeline(enterprise_contact, 'team_building')
        assert 'extended' in timeline.lower() or 'enterprise' in timeline.lower()
        
        # Seed company timeline should mention acceleration
        seed_contact = {'company_size': 'Seed/Pre-Series A (5-20 employees)'}
        timeline = sales_engine._generate_timeline(seed_contact, 'team_building')
        assert 'accelerated' in timeline.lower() or 'faster' in timeline.lower()
    
    def test_next_steps_personalization(self, sales_engine):
        """Test next steps personalization by priority tier"""
        # Platinum tier should have priority scheduling
        platinum_contact = {'priority_tier': 'platinum'}
        steps = sales_engine._generate_next_steps(platinum_contact)
        assert any('24-48' in step or 'priority' in step.lower() for step in steps)
        
        # Gold tier should have expedited scheduling
        gold_contact = {'priority_tier': 'gold'}
        steps = sales_engine._generate_next_steps(gold_contact)
        assert any('3-5' in step or 'expedited' in step.lower() for step in steps)
        
        # All tiers should have basic next steps
        bronze_contact = {'priority_tier': 'bronze'}
        steps = sales_engine._generate_next_steps(bronze_contact)
        assert len(steps) >= 3, "Should have at least 3 next steps"


class TestInvestmentProposalGeneration:
    """Test investment proposal and pricing tier generation"""
    
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
    
    def test_investment_proposal_structure(self, sales_engine):
        """Test investment proposal structure and pricing tiers"""
        contact = {'estimated_value': 50000}
        roi_calculation = {
            'total_annual_benefit': 200000,
            'roi_percentage': 300
        }
        
        investment_proposal = sales_engine._generate_investment_proposal(contact, roi_calculation)
        
        # Should have three pricing tiers
        expected_tiers = ['essential', 'recommended', 'premium']
        for tier in expected_tiers:
            assert tier in investment_proposal, f"Missing {tier} pricing tier"
            
            tier_data = investment_proposal[tier]
            assert 'price' in tier_data, f"{tier} tier missing price"
            assert 'description' in tier_data, f"{tier} tier missing description"
            assert 'included' in tier_data, f"{tier} tier missing included features"
            assert 'roi_multiple' in tier_data, f"{tier} tier missing ROI multiple"
        
        # Verify pricing relationships
        assert investment_proposal['essential']['price'] < investment_proposal['recommended']['price']
        assert investment_proposal['recommended']['price'] < investment_proposal['premium']['price']
        
        # Verify ROI multiples are calculated
        for tier in expected_tiers:
            roi_multiple = investment_proposal[tier]['roi_multiple']
            assert roi_multiple > 0, f"{tier} tier should have positive ROI multiple"
    
    def test_close_probability_estimation(self, sales_engine):
        """Test close probability estimation based on multiple factors"""
        # High probability scenario
        high_prob_contact = {
            'lead_score': 90,
            'priority_tier': 'platinum',
            'company_size': 'Series B (50-200 employees)',
            'estimated_value': 100000
        }
        
        high_prob_roi = {
            'roi_percentage': 400,
            'total_annual_benefit': 500000
        }
        
        prob = sales_engine._estimate_close_probability(high_prob_contact, high_prob_roi)
        assert prob >= 0.7, f"High-value scenario should have high close probability, got {prob:.1%}"
        
        # Low probability scenario
        low_prob_contact = {
            'lead_score': 30,
            'priority_tier': 'bronze',
            'company_size': 'Unknown',
            'estimated_value': 5000
        }
        
        low_prob_roi = {
            'roi_percentage': 50,
            'total_annual_benefit': 10000
        }
        
        prob = sales_engine._estimate_close_probability(low_prob_contact, low_prob_roi)
        assert prob <= 0.5, f"Low-value scenario should have low close probability, got {prob:.1%}"
        
        # Probability should never exceed 95%
        extreme_contact = {
            'lead_score': 100,
            'priority_tier': 'platinum',
            'company_size': 'Enterprise (500+ employees)',
            'estimated_value': 500000
        }
        
        extreme_roi = {
            'roi_percentage': 1000,
            'total_annual_benefit': 5000000
        }
        
        prob = sales_engine._estimate_close_probability(extreme_contact, extreme_roi)
        assert prob <= 0.95, f"Close probability should be capped at 95%, got {prob:.1%}"


if __name__ == "__main__":
    # Run tests with detailed output
    pytest.main([__file__, "-v", "--tb=short"])