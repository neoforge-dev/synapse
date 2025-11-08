#!/usr/bin/env python3
"""
Epic 7 End-to-End Consultation Workflow Tests
Tests for complete consultation process from inquiry to revenue tracking
"""

import sqlite3
import sys
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

import pytest

# Add project root to path for imports
project_root = Path(__file__).parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from business_development.epic7_sales_automation import SalesAutomationEngine


class TestConsultationWorkflow:
    """Test end-to-end consultation workflow"""

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
    def consultation_inquiry_data(self):
        """Sample consultation inquiry data"""
        return [
            {
                'inquiry_id': 'workflow-test-001',
                'contact_name': 'Alex Rodriguez',
                'company': 'TechScale Inc',
                'company_size': 'Series B (50-200 employees)',
                'inquiry_type': 'fractional_cto',
                'inquiry_text': 'We need strategic technical leadership for our Series B growth. Looking for fractional CTO to guide architecture decisions and team scaling. Budget allocated and decision timeline is Q1.',
                'estimated_value': 120000,
                'priority_score': 5,
                'status': 'new',
                'created_at': datetime.now().isoformat()
            },
            {
                'inquiry_id': 'workflow-test-002',
                'contact_name': 'Maria Santos',
                'company': 'GrowthTech Ltd',
                'company_size': 'Series A (20-50 employees)',
                'inquiry_type': 'team_building',
                'inquiry_text': 'Our 35-person engineering team is struggling with velocity. Need systematic approach to improve team performance and delivery predictability.',
                'estimated_value': 55000,
                'priority_score': 4,
                'status': 'new',
                'created_at': datetime.now().isoformat()
            }
        ]

    def setup_consultation_database(self, sales_engine, inquiry_data):
        """Setup consultation database with test data"""
        conn = sqlite3.connect(sales_engine.consultation_db_path)
        cursor = conn.cursor()

        # Create consultation_inquiries table
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

        # Insert test data
        for inquiry in inquiry_data:
            cursor.execute('''
                INSERT OR REPLACE INTO consultation_inquiries
                (inquiry_id, contact_name, company, company_size, inquiry_type, 
                 inquiry_text, estimated_value, priority_score, status, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                inquiry['inquiry_id'], inquiry['contact_name'], inquiry['company'],
                inquiry['company_size'], inquiry['inquiry_type'], inquiry['inquiry_text'],
                inquiry['estimated_value'], inquiry['priority_score'],
                inquiry['status'], inquiry['created_at']
            ))

        conn.commit()
        conn.close()

    def test_complete_workflow_high_value_prospect(self, sales_engine, consultation_inquiry_data):
        """Test complete workflow for high-value prospect"""
        # Setup consultation data
        self.setup_consultation_database(sales_engine, consultation_inquiry_data)

        # Step 1: Import consultation inquiries into CRM
        imported_contacts = sales_engine.import_consultation_inquiries(include_synthetic=False)

        assert len(imported_contacts) >= 2, "Should import test consultation inquiries"

        # Find high-value prospect (fractional CTO inquiry)
        high_value_contact = next((c for c in imported_contacts if 'fractional' in c.notes.lower()), None)
        assert high_value_contact is not None, "Should have fractional CTO prospect"

        # Step 2: Verify lead scoring and qualification
        assert high_value_contact.lead_score >= 80, f"High-value prospect should have score 80+, got {high_value_contact.lead_score}"
        assert high_value_contact.qualification_status == "qualified", "High-value prospect should be qualified"
        assert high_value_contact.priority_tier in ["platinum", "gold"], "High-value prospect should be high priority"

        # Step 3: Generate automated proposal
        proposal = sales_engine.generate_automated_proposal(high_value_contact.contact_id)
        assert 'error' not in proposal, "Proposal generation should succeed"

        proposal_content = proposal['content']
        assert proposal_content['close_probability'] >= 0.6, "High-value prospect should have high close probability"

        # Step 4: Integrate LinkedIn automation
        linkedin_automation = sales_engine.integrate_linkedin_automation(high_value_contact.contact_id)
        assert 'error' not in linkedin_automation, "LinkedIn automation should be scheduled"
        assert linkedin_automation['linkedin_sequence_scheduled'], "LinkedIn sequence should be scheduled"

        # Step 5: Verify pipeline tracking
        summary = sales_engine.get_sales_pipeline_summary()
        assert summary['platinum_leads'] >= 1 or summary['gold_leads'] >= 1, "Should have high-priority leads in pipeline"
        assert summary['total_pipeline_value'] >= high_value_contact.estimated_value, "Pipeline value should include new prospect"

    def test_workflow_with_multiple_prospects(self, sales_engine, consultation_inquiry_data):
        """Test workflow handling multiple prospects simultaneously"""
        # Setup consultation data with more prospects
        extended_inquiry_data = consultation_inquiry_data + [
            {
                'inquiry_id': 'workflow-test-003',
                'contact_name': 'David Kim',
                'company': 'DevTools Pro',
                'company_size': 'Series A (20-50 employees)',
                'inquiry_type': 'nobuild_audit',
                'inquiry_text': 'Need technology audit to optimize build vs buy decisions. Burning budget on custom development.',
                'estimated_value': 30000,
                'priority_score': 3,
                'status': 'new',
                'created_at': datetime.now().isoformat()
            }
        ]

        self.setup_consultation_database(sales_engine, extended_inquiry_data)

        # Import all prospects
        imported_contacts = sales_engine.import_consultation_inquiries(include_synthetic=False)
        assert len(imported_contacts) >= 3, "Should import all consultation inquiries"

        # Generate proposals for all qualified leads
        qualified_contacts = [c for c in imported_contacts if c.qualification_status == 'qualified']
        generated_proposals = []

        for contact in qualified_contacts:
            proposal = sales_engine.generate_automated_proposal(contact.contact_id)
            if 'error' not in proposal:
                generated_proposals.append(proposal)

        assert len(generated_proposals) >= 2, "Should generate proposals for multiple qualified leads"

        # Verify pipeline summary reflects all prospects
        summary = sales_engine.get_sales_pipeline_summary()
        assert summary['total_contacts'] >= 3, "Pipeline should include all imported contacts"
        assert summary['qualified_leads'] >= 2, "Should have multiple qualified leads"

    def test_linkedin_automation_integration(self, sales_engine, consultation_inquiry_data):
        """Test LinkedIn automation integration in workflow"""
        self.setup_consultation_database(sales_engine, consultation_inquiry_data)

        # Import and process prospects
        imported_contacts = sales_engine.import_consultation_inquiries(include_synthetic=False)
        qualified_contacts = [c for c in imported_contacts if c.qualification_status == 'qualified']

        linkedin_integrations = []
        for contact in qualified_contacts:
            if contact.priority_tier in ['platinum', 'gold']:
                integration = sales_engine.integrate_linkedin_automation(contact.contact_id)
                if 'error' not in integration:
                    linkedin_integrations.append(integration)

        assert len(linkedin_integrations) >= 1, "Should have LinkedIn automation for high-priority leads"

        # Verify automation sequences are appropriate for priority tier
        for integration in linkedin_integrations:
            assert 'follow_up_sequence' in integration, "Should have follow-up sequence"
            assert len(integration['follow_up_sequence']) >= 2, "Should have multi-touch sequence"
            assert integration['estimated_conversion_lift'] > 0.15, "Should show conversion lift"

    def test_revenue_forecasting_integration(self, sales_engine, consultation_inquiry_data):
        """Test revenue forecasting with consultation workflow"""
        self.setup_consultation_database(sales_engine, consultation_inquiry_data)

        # Process prospects through workflow
        imported_contacts = sales_engine.import_consultation_inquiries(include_synthetic=False)

        # Generate proposals to populate pipeline
        for contact in imported_contacts:
            if contact.qualification_status == 'qualified':
                sales_engine.generate_automated_proposal(contact.contact_id)

        # Generate revenue forecast
        forecast = sales_engine.generate_revenue_forecast("annual")

        assert forecast['current_pipeline_revenue'] > 0, "Should have current pipeline revenue"
        assert forecast['total_projected_revenue'] > 0, "Should have total projected revenue"

        # Verify ARR target tracking
        arr_achievement = forecast['arr_target_achievement']
        assert arr_achievement['target'] == 2000000, "ARR target should be $2M"
        assert arr_achievement['projected'] > 0, "Should have projected ARR"

    def test_ab_testing_workflow_integration(self, sales_engine, consultation_inquiry_data):
        """Test A/B testing integration with consultation workflow"""
        self.setup_consultation_database(sales_engine, consultation_inquiry_data)

        # Create A/B test campaign
        campaign_id = sales_engine.create_ab_test_campaign(
            test_name="Consultation Follow-up Optimization",
            variant_a_description="Direct technical approach",
            variant_b_description="Value-first business approach"
        )

        assert campaign_id.startswith("ab-test-"), "Should generate valid campaign ID"

        # Import prospects and assign to variants
        imported_contacts = sales_engine.import_consultation_inquiries(include_synthetic=False)

        variant_assignments = {}
        for contact in imported_contacts:
            variant = sales_engine.assign_ab_test_variant(campaign_id, contact.contact_id)
            variant_assignments[contact.contact_id] = variant
            assert variant in ['a', 'b'], f"Should assign valid variant, got {variant}"

        # Verify consistent assignment
        for contact in imported_contacts:
            variant2 = sales_engine.assign_ab_test_variant(campaign_id, contact.contact_id)
            assert variant_assignments[contact.contact_id] == variant2, "Variant assignment should be consistent"


class TestPipelineTracking:
    """Test sales pipeline tracking and metrics"""

    @pytest.fixture
    def temp_sales_db(self):
        """Create temporary sales automation database"""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
            db_path = tmp.name

        engine = SalesAutomationEngine(db_path=db_path)
        yield db_path

        Path(db_path).unlink(missing_ok=True)

    @pytest.fixture
    def sales_engine_with_pipeline(self, temp_sales_db):
        """Sales engine with populated pipeline data"""
        engine = SalesAutomationEngine(db_path=temp_sales_db)

        # Create a realistic consultation pipeline
        consultation_data = []
        base_date = datetime.now()

        for i in range(12):  # Create 12 consultation inquiries
            inquiry_date = base_date - timedelta(days=i*2)
            consultation_data.append({
                'inquiry_id': f'pipeline-test-{i+1:03d}',
                'contact_name': f'Contact {i+1}',
                'company': f'Company {i+1}',
                'company_size': ['Series B (50-200 employees)', 'Series A (20-50 employees)', 'Enterprise (500+ employees)'][i % 3],
                'inquiry_type': ['fractional_cto', 'team_building', 'nobuild_audit'][i % 3],
                'inquiry_text': f'Test inquiry {i+1} with various business requirements',
                'estimated_value': [75000, 45000, 25000, 120000, 35000][i % 5],
                'priority_score': [5, 4, 3, 5, 4][i % 5],
                'status': 'new',
                'created_at': inquiry_date.isoformat()
            })

        # Setup consultation database
        conn = sqlite3.connect(engine.consultation_db_path)
        cursor = conn.cursor()

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

        for inquiry in consultation_data:
            cursor.execute('''
                INSERT OR REPLACE INTO consultation_inquiries
                (inquiry_id, contact_name, company, company_size, inquiry_type,
                 inquiry_text, estimated_value, priority_score, status, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                inquiry['inquiry_id'], inquiry['contact_name'], inquiry['company'],
                inquiry['company_size'], inquiry['inquiry_type'], inquiry['inquiry_text'],
                inquiry['estimated_value'], inquiry['priority_score'],
                inquiry['status'], inquiry['created_at']
            ))

        conn.commit()
        conn.close()

        # Import and process inquiries
        engine.import_consultation_inquiries(include_synthetic=False)

        return engine

    def test_pipeline_health_calculation(self, sales_engine_with_pipeline):
        """Test pipeline health score calculation"""
        summary = sales_engine_with_pipeline.get_sales_pipeline_summary()

        health_score = summary['pipeline_health_score']
        assert 0 <= health_score <= 100, f"Health score should be 0-100, got {health_score}"

        # With 12 prospects and some qualified, health should be reasonable
        assert health_score >= 40, f"With populated pipeline, health score should be decent, got {health_score}"

        # Generate proposals to improve health score
        conn = sqlite3.connect(sales_engine_with_pipeline.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT contact_id FROM crm_contacts WHERE qualification_status = 'qualified' LIMIT 5")
        qualified_contacts = cursor.fetchall()
        conn.close()

        for contact_row in qualified_contacts:
            sales_engine_with_pipeline.generate_automated_proposal(contact_row[0])

        # Health score should improve with proposals
        updated_summary = sales_engine_with_pipeline.get_sales_pipeline_summary()
        updated_health = updated_summary['pipeline_health_score']
        assert updated_health >= health_score, "Health score should improve with proposals"

    def test_revenue_projections_accuracy(self, sales_engine_with_pipeline):
        """Test revenue projection accuracy"""
        forecast = sales_engine_with_pipeline.generate_revenue_forecast("annual")

        # Verify projection components
        assert forecast['current_pipeline_revenue'] > 0, "Should have current pipeline revenue"
        assert forecast['growth_pipeline_revenue'] > 0, "Should project growth pipeline"
        assert forecast['total_projected_revenue'] > forecast['current_pipeline_revenue'], "Total should exceed current pipeline"

        # Verify confidence intervals are reasonable
        confidence = forecast['confidence_interval']
        projected_revenue = forecast['total_projected_revenue']

        assert confidence['min'] < projected_revenue < confidence['max'], "Projected revenue should be within confidence interval"
        assert confidence['max'] <= projected_revenue * 1.3, "Max confidence shouldn't be unrealistic"
        assert confidence['min'] >= projected_revenue * 0.7, "Min confidence shouldn't be too pessimistic"

    def test_tier_breakdown_accuracy(self, sales_engine_with_pipeline):
        """Test pipeline tier breakdown accuracy"""
        forecast = sales_engine_with_pipeline.generate_revenue_forecast("annual")
        tier_breakdown = forecast['tier_breakdown']

        # Should have data for multiple tiers
        assert len(tier_breakdown) > 0, "Should have tier breakdown data"

        for tier, data in tier_breakdown.items():
            assert tier in ['platinum', 'gold', 'silver', 'bronze'], f"Invalid tier: {tier}"
            assert 'contact_count' in data, f"Tier {tier} missing contact count"
            assert 'average_value' in data, f"Tier {tier} missing average value"
            assert 'conversion_rate' in data, f"Tier {tier} missing conversion rate"
            assert 'projected_revenue' in data, f"Tier {tier} missing projected revenue"

            # Verify logical relationships
            assert data['contact_count'] >= 0, f"Tier {tier} should have non-negative contact count"
            assert data['conversion_rate'] > 0, f"Tier {tier} should have positive conversion rate"

    def test_arr_target_tracking(self, sales_engine_with_pipeline):
        """Test ARR target achievement tracking"""
        forecast = sales_engine_with_pipeline.generate_revenue_forecast("annual")
        arr_data = forecast['arr_target_achievement']

        assert arr_data['target'] == 2000000, "ARR target should be $2M"
        assert arr_data['projected'] > 0, "Should have positive projected ARR"
        assert 0 <= arr_data['achievement_percentage'] <= 200, "Achievement percentage should be reasonable"

        # Gap calculation should be correct
        if arr_data['projected'] < arr_data['target']:
            expected_gap = arr_data['target'] - arr_data['projected']
            assert arr_data['gap'] == expected_gap, "Gap calculation should be correct"
        else:
            assert arr_data['gap'] == 0, "Gap should be 0 when target is met"


class TestBusinessContinuityValidation:
    """CRITICAL: Test business continuity validation and pipeline protection"""

    @pytest.fixture
    def temp_sales_db(self):
        """Create temporary sales automation database"""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
            db_path = tmp.name

        engine = SalesAutomationEngine(db_path=db_path)
        yield db_path

        Path(db_path).unlink(missing_ok=True)

    @pytest.fixture
    def sales_engine_with_high_value_pipeline(self, temp_sales_db):
        """Sales engine with high-value pipeline simulating $1.158M+ value"""
        engine = SalesAutomationEngine(db_path=temp_sales_db)

        # Create high-value consultation pipeline
        high_value_inquiries = [
            {
                'inquiry_id': 'hv-001',
                'contact_name': 'Enterprise Client 1',
                'company': 'Major Corp',
                'company_size': 'Enterprise (500+ employees)',
                'inquiry_type': 'fractional_cto',
                'inquiry_text': 'Strategic technical leadership for enterprise transformation',
                'estimated_value': 200000,
                'priority_score': 5,
                'status': 'new',
                'created_at': datetime.now().isoformat()
            },
            {
                'inquiry_id': 'hv-002',
                'contact_name': 'Series B Client 1',
                'company': 'ScaleUp Inc',
                'company_size': 'Series B (50-200 employees)',
                'inquiry_type': 'team_building',
                'inquiry_text': 'Systematic team optimization for 150+ engineers',
                'estimated_value': 150000,
                'priority_score': 5,
                'status': 'new',
                'created_at': datetime.now().isoformat()
            },
            {
                'inquiry_id': 'hv-003',
                'contact_name': 'Series B Client 2',
                'company': 'TechGiant Ltd',
                'company_size': 'Series B (50-200 employees)',
                'inquiry_type': 'fractional_cto',
                'inquiry_text': 'Technical architecture and strategic guidance',
                'estimated_value': 120000,
                'priority_score': 4,
                'status': 'new',
                'created_at': datetime.now().isoformat()
            }
        ]

        # Add medium-value prospects to reach $1.158M+
        for i in range(15):  # Add 15 more prospects
            high_value_inquiries.append({
                'inquiry_id': f'mv-{i+1:03d}',
                'contact_name': f'Series A Client {i+1}',
                'company': f'Growth Company {i+1}',
                'company_size': 'Series A (20-50 employees)',
                'inquiry_type': ['team_building', 'nobuild_audit', 'fractional_cto'][i % 3],
                'inquiry_text': f'Series A consultation inquiry {i+1}',
                'estimated_value': [45000, 35000, 65000, 55000, 40000][i % 5],
                'priority_score': [4, 3, 4, 3, 4][i % 5],
                'status': 'new',
                'created_at': datetime.now().isoformat()
            })

        # Setup database
        conn = sqlite3.connect(engine.consultation_db_path)
        cursor = conn.cursor()

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

        for inquiry in high_value_inquiries:
            cursor.execute('''
                INSERT OR REPLACE INTO consultation_inquiries
                (inquiry_id, contact_name, company, company_size, inquiry_type,
                 inquiry_text, estimated_value, priority_score, status, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                inquiry['inquiry_id'], inquiry['contact_name'], inquiry['company'],
                inquiry['company_size'], inquiry['inquiry_type'], inquiry['inquiry_text'],
                inquiry['estimated_value'], inquiry['priority_score'],
                inquiry['status'], inquiry['created_at']
            ))

        conn.commit()
        conn.close()

        # Import inquiries
        engine.import_consultation_inquiries(include_synthetic=False)

        return engine

    def test_pipeline_value_protection(self, sales_engine_with_high_value_pipeline):
        """CRITICAL: Test that pipeline value meets/exceeds $1.158M target"""
        summary = sales_engine_with_high_value_pipeline.get_sales_pipeline_summary()

        total_pipeline_value = summary['total_pipeline_value']
        target_value = 1158000  # $1.158M

        assert total_pipeline_value >= target_value, \
            f"Pipeline value ${total_pipeline_value:,} below target ${target_value:,}"

        # Verify contact count (should be 16+ contacts as specified)
        assert summary['total_contacts'] >= 16, \
            f"Expected at least 16 contacts, got {summary['total_contacts']}"

    def test_business_data_integrity(self, sales_engine_with_high_value_pipeline):
        """CRITICAL: Test business data integrity and accessibility"""
        # Verify database files exist and are not corrupted
        assert Path(sales_engine_with_high_value_pipeline.db_path).exists(), \
            "CRM database file should exist"

        assert Path(sales_engine_with_high_value_pipeline.consultation_db_path).exists(), \
            "Consultation database file should exist"

        # Verify database content integrity
        conn = sqlite3.connect(sales_engine_with_high_value_pipeline.db_path)
        cursor = conn.cursor()

        # Check all contacts are accessible
        cursor.execute("SELECT COUNT(*) FROM crm_contacts")
        contact_count = cursor.fetchone()[0]
        assert contact_count >= 16, f"Expected at least 16 contacts in database, got {contact_count}"

        # Check no data corruption in critical fields
        cursor.execute("""
            SELECT contact_id, name, company, estimated_value, lead_score 
            FROM crm_contacts 
            WHERE name IS NOT NULL AND company IS NOT NULL AND estimated_value > 0
        """)
        valid_contacts = cursor.fetchall()

        assert len(valid_contacts) >= 16, "All contacts should have valid core data"

        conn.close()

    def test_zero_disruption_operations(self, sales_engine_with_high_value_pipeline):
        """CRITICAL: Test that all operations work without disrupting business data"""
        # Capture initial state
        initial_summary = sales_engine_with_high_value_pipeline.get_sales_pipeline_summary()
        initial_contacts = initial_summary['total_contacts']
        initial_value = initial_summary['total_pipeline_value']

        # Perform various operations that should NOT disrupt business data
        operations_performed = []

        try:
            # Generate revenue forecast
            forecast = sales_engine_with_high_value_pipeline.generate_revenue_forecast("annual")
            operations_performed.append("revenue_forecast")

            # Create A/B test campaign
            campaign_id = sales_engine_with_high_value_pipeline.create_ab_test_campaign(
                "Test Campaign", "Variant A", "Variant B"
            )
            operations_performed.append("ab_test_creation")

            # Generate proposals for qualified leads
            conn = sqlite3.connect(sales_engine_with_high_value_pipeline.db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT contact_id FROM crm_contacts WHERE qualification_status = 'qualified' LIMIT 3")
            qualified_contacts = cursor.fetchall()
            conn.close()

            for contact_row in qualified_contacts:
                sales_engine_with_high_value_pipeline.generate_automated_proposal(contact_row[0])
            operations_performed.append("proposal_generation")

        except Exception as e:
            pytest.fail(f"Business operation failed: {e}. Operations completed: {operations_performed}")

        # Verify business data integrity after operations
        final_summary = sales_engine_with_high_value_pipeline.get_sales_pipeline_summary()

        assert final_summary['total_contacts'] == initial_contacts, \
            "Contact count should remain stable after operations"

        assert final_summary['total_pipeline_value'] == initial_value, \
            "Pipeline value should remain stable after operations"

        # Additional checks
        assert final_summary['total_proposals'] >= len(qualified_contacts), \
            "Proposals should be generated without disrupting core data"

    def test_backup_and_recovery_readiness(self, sales_engine_with_high_value_pipeline):
        """CRITICAL: Test backup and recovery procedures for business continuity"""
        # Export current pipeline data
        export_data = sales_engine_with_high_value_pipeline.export_pipeline_data()

        # Verify export contains all critical business data
        assert 'summary_metrics' in export_data, "Export should include summary metrics"
        assert 'contacts' in export_data, "Export should include contact data"
        assert 'proposals' in export_data, "Export should include proposal data"

        # Verify contact data completeness
        exported_contacts = export_data['contacts']
        assert len(exported_contacts) >= 16, "Export should include all contacts"

        # Verify critical fields are present
        for contact in exported_contacts[:5]:  # Check first 5 contacts
            required_fields = ['contact_id', 'name', 'company', 'estimated_value', 'lead_score']
            for field in required_fields:
                assert field in contact, f"Contact export missing critical field: {field}"

        # Verify pipeline value is preserved in export
        export_summary = export_data['summary_metrics']
        assert export_summary['total_pipeline_value'] >= 1158000, \
            "Exported pipeline value should meet target"


if __name__ == "__main__":
    # Run tests with detailed output
    pytest.main([__file__, "-v", "--tb=short"])
