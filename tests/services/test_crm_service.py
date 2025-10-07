"""
Unit tests for CRM Service

These tests demonstrate the usage of the CRM service layer and verify
all operations work correctly. Tests use in-memory SQLite for fast execution.
"""

import pytest
from datetime import datetime, timedelta
from decimal import Decimal
from uuid import uuid4

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from graph_rag.infrastructure.persistence.models.base import Base
from graph_rag.infrastructure.persistence.models.crm import (
    ContactModel,
    SalesPipelineModel,
    LeadQualificationModel,
    ProposalModel,
    ABTestCampaignModel,
    RevenueForecastModel,
)
from graph_rag.services.crm_service import (
    CRMService,
    DatabaseConfig,
    ContactNotFoundError,
    CRMServiceError,
    get_crm_service,
)


@pytest.fixture
def test_db_config():
    """Create test database configuration using SQLite in-memory"""
    config = DatabaseConfig(
        host="",
        port=0,
        database=":memory:",
        user="",
        password="",
        pool_size=1,
        echo=False,
    )
    # Override URL for SQLite
    config.get_sync_url = lambda: "sqlite:///:memory:"
    return config


@pytest.fixture
def crm_service(test_db_config):
    """Create CRM service with test database"""
    service = CRMService(db_config=test_db_config, use_async=False)

    # Create tables
    Base.metadata.create_all(service.engine)

    yield service

    # Cleanup
    service.close()


@pytest.fixture
def sample_contact(crm_service):
    """Create a sample contact for testing"""
    contact = crm_service.create_contact(
        name="Sarah Chen",
        email="sarah.chen@dataflow.com",
        company="DataFlow Analytics",
        title="VP of Engineering",
        phone="+1-555-0101",
        linkedin_profile="https://linkedin.com/in/sarahchen",
        lead_score=85,
        estimated_value=Decimal("120000.00"),
        priority_tier="platinum",
        qualification_status="qualified",
        next_action="Schedule strategic consultation",
        next_action_date=datetime.now() + timedelta(days=2),
        notes="Series B company, 50-200 employees. Looking for fractional CTO services.",
    )
    return contact


class TestContactManagement:
    """Test contact CRUD operations"""

    def test_create_contact(self, crm_service):
        """Test creating a new contact"""
        contact = crm_service.create_contact(
            name="John Doe",
            email="john.doe@example.com",
            company="Example Corp",
            title="CTO",
            lead_score=75,
            estimated_value=Decimal("50000.00"),
            priority_tier="gold",
        )

        assert contact.contact_id is not None
        assert contact.name == "John Doe"
        assert contact.email == "john.doe@example.com"
        assert contact.lead_score == 75
        assert contact.priority_tier == "gold"
        assert contact.created_at is not None

    def test_get_contact(self, crm_service, sample_contact):
        """Test retrieving a contact by ID"""
        retrieved = crm_service.get_contact(sample_contact.contact_id)

        assert retrieved is not None
        assert retrieved.contact_id == sample_contact.contact_id
        assert retrieved.name == sample_contact.name
        assert retrieved.email == sample_contact.email

    def test_get_contact_by_email(self, crm_service, sample_contact):
        """Test retrieving a contact by email"""
        retrieved = crm_service.get_contact_by_email(sample_contact.email)

        assert retrieved is not None
        assert retrieved.contact_id == sample_contact.contact_id
        assert retrieved.email == sample_contact.email

    def test_get_nonexistent_contact(self, crm_service):
        """Test retrieving a non-existent contact"""
        retrieved = crm_service.get_contact(uuid4())

        assert retrieved is None

    def test_update_contact(self, crm_service, sample_contact):
        """Test updating contact fields"""
        updated = crm_service.update_contact(
            sample_contact.contact_id,
            lead_score=90,
            qualification_status="qualified",
            notes="Updated notes with new information",
        )

        assert updated.lead_score == 90
        assert updated.qualification_status == "qualified"
        assert "Updated notes" in updated.notes
        assert updated.updated_at > sample_contact.updated_at

    def test_update_nonexistent_contact(self, crm_service):
        """Test updating a non-existent contact raises error"""
        with pytest.raises(ContactNotFoundError):
            crm_service.update_contact(
                uuid4(),
                lead_score=50,
            )

    def test_delete_contact(self, crm_service, sample_contact):
        """Test deleting a contact"""
        result = crm_service.delete_contact(sample_contact.contact_id)

        assert result is True

        # Verify deletion
        retrieved = crm_service.get_contact(sample_contact.contact_id)
        assert retrieved is None

    def test_delete_nonexistent_contact(self, crm_service):
        """Test deleting a non-existent contact"""
        result = crm_service.delete_contact(uuid4())

        assert result is False

    def test_list_contacts(self, crm_service):
        """Test listing contacts with filters"""
        # Create multiple contacts
        crm_service.create_contact(
            name="Contact 1",
            email="contact1@example.com",
            lead_score=90,
            priority_tier="platinum",
            qualification_status="qualified",
        )
        crm_service.create_contact(
            name="Contact 2",
            email="contact2@example.com",
            lead_score=70,
            priority_tier="gold",
            qualification_status="qualified",
        )
        crm_service.create_contact(
            name="Contact 3",
            email="contact3@example.com",
            lead_score=40,
            priority_tier="silver",
            qualification_status="prospect",
        )

        # Test listing all contacts
        all_contacts = crm_service.list_contacts()
        assert len(all_contacts) == 3

        # Test filtering by qualification status
        qualified = crm_service.list_contacts(qualification_status="qualified")
        assert len(qualified) == 2

        # Test filtering by priority tier
        platinum = crm_service.list_contacts(priority_tier="platinum")
        assert len(platinum) == 1
        assert platinum[0].name == "Contact 1"

        # Test filtering by minimum lead score
        high_score = crm_service.list_contacts(min_lead_score=70)
        assert len(high_score) == 2

        # Test pagination
        page1 = crm_service.list_contacts(limit=2, offset=0)
        assert len(page1) == 2
        page2 = crm_service.list_contacts(limit=2, offset=2)
        assert len(page2) == 1


class TestLeadScoringAndQualification:
    """Test lead scoring operations"""

    def test_update_lead_score(self, crm_service, sample_contact):
        """Test updating lead score with qualification history"""
        qualification = crm_service.update_lead_score(
            sample_contact.contact_id,
            new_score=92,
            qualification_criteria={
                "company_size": "Series B",
                "budget_confirmed": True,
                "decision_timeframe": "Q1 2025",
            },
            qualification_notes="Strong buying signals, budget approved",
            qualified_by="sales_team",
        )

        assert qualification.contact_id == sample_contact.contact_id
        assert qualification.calculated_score == 92
        assert qualification.qualification_criteria["budget_confirmed"] is True

        # Verify contact score was updated
        updated_contact = crm_service.get_contact(sample_contact.contact_id)
        assert updated_contact.lead_score == 92
        assert updated_contact.qualification_status == "qualified"

    def test_lead_score_auto_qualification(self, crm_service):
        """Test automatic qualification status based on score"""
        # High score -> qualified
        contact1 = crm_service.create_contact(
            name="High Score",
            email="high@example.com",
            lead_score=80,
        )
        crm_service.update_lead_score(contact1.contact_id, 85)
        updated1 = crm_service.get_contact(contact1.contact_id)
        assert updated1.qualification_status == "qualified"

        # Medium score -> prospect
        contact2 = crm_service.create_contact(
            name="Medium Score",
            email="medium@example.com",
            lead_score=50,
        )
        crm_service.update_lead_score(contact2.contact_id, 55)
        updated2 = crm_service.get_contact(contact2.contact_id)
        assert updated2.qualification_status == "prospect"

        # Low score -> disqualified
        contact3 = crm_service.create_contact(
            name="Low Score",
            email="low@example.com",
            lead_score=30,
        )
        crm_service.update_lead_score(contact3.contact_id, 25)
        updated3 = crm_service.get_contact(contact3.contact_id)
        assert updated3.qualification_status == "disqualified"

    def test_get_qualification_history(self, crm_service, sample_contact):
        """Test retrieving qualification history"""
        # Create multiple qualification records
        crm_service.update_lead_score(sample_contact.contact_id, 70, qualification_notes="Initial score")
        crm_service.update_lead_score(sample_contact.contact_id, 80, qualification_notes="After call")
        crm_service.update_lead_score(sample_contact.contact_id, 90, qualification_notes="Budget confirmed")

        history = crm_service.get_qualification_history(sample_contact.contact_id)

        assert len(history) == 3
        # Most recent first
        assert history[0].calculated_score == 90
        assert history[1].calculated_score == 80
        assert history[2].calculated_score == 70


class TestSalesPipelineManagement:
    """Test sales pipeline operations"""

    def test_create_pipeline_entry(self, crm_service, sample_contact):
        """Test creating a pipeline entry"""
        pipeline = crm_service.create_pipeline_entry(
            contact_id=sample_contact.contact_id,
            stage="qualified",
            probability=Decimal("0.65"),
            deal_value=Decimal("120000.00"),
            expected_close_date=datetime.now() + timedelta(days=45),
            notes="Strong interest, moving to proposal stage",
        )

        assert pipeline.pipeline_id is not None
        assert pipeline.contact_id == sample_contact.contact_id
        assert pipeline.stage == "qualified"
        assert pipeline.probability == Decimal("0.65")
        assert pipeline.deal_value == Decimal("120000.00")

    def test_create_pipeline_for_nonexistent_contact(self, crm_service):
        """Test creating pipeline entry for non-existent contact fails"""
        with pytest.raises(ContactNotFoundError):
            crm_service.create_pipeline_entry(
                contact_id=uuid4(),
                stage="qualified",
                probability=Decimal("0.5"),
                deal_value=Decimal("50000.00"),
            )

    def test_update_pipeline_stage(self, crm_service, sample_contact):
        """Test updating pipeline stage"""
        pipeline = crm_service.create_pipeline_entry(
            contact_id=sample_contact.contact_id,
            stage="qualified",
            probability=Decimal("0.50"),
            deal_value=Decimal("100000.00"),
        )

        updated = crm_service.update_pipeline_stage(
            pipeline.pipeline_id,
            stage="proposal_sent",
            probability=Decimal("0.70"),
            notes="Proposal delivered successfully",
        )

        assert updated.stage == "proposal_sent"
        assert updated.probability == Decimal("0.70")
        assert "Proposal delivered" in updated.notes

    def test_get_pipeline_summary(self, crm_service):
        """Test getting pipeline summary with metrics"""
        # Create contacts with different tiers and values
        contact1 = crm_service.create_contact(
            name="Platinum Contact",
            email="platinum@example.com",
            lead_score=90,
            estimated_value=Decimal("150000.00"),
            priority_tier="platinum",
            qualification_status="qualified",
        )
        contact2 = crm_service.create_contact(
            name="Gold Contact",
            email="gold@example.com",
            lead_score=75,
            estimated_value=Decimal("80000.00"),
            priority_tier="gold",
            qualification_status="qualified",
        )
        contact3 = crm_service.create_contact(
            name="Silver Contact",
            email="silver@example.com",
            lead_score=55,
            estimated_value=Decimal("30000.00"),
            priority_tier="silver",
            qualification_status="prospect",
        )

        # Create pipeline entries
        crm_service.create_pipeline_entry(
            contact1.contact_id,
            stage="proposal_sent",
            probability=Decimal("0.70"),
            deal_value=Decimal("150000.00"),
        )
        crm_service.create_pipeline_entry(
            contact2.contact_id,
            stage="qualified",
            probability=Decimal("0.50"),
            deal_value=Decimal("80000.00"),
        )

        summary = crm_service.get_pipeline_summary()

        assert summary["total_contacts"] == 3
        assert summary["qualified_leads"] == 2
        assert summary["total_pipeline_value"] == 260000.0

        # Check tier breakdown
        assert len(summary["by_tier"]) == 3
        platinum_tier = next(t for t in summary["by_tier"] if t["tier"] == "platinum")
        assert platinum_tier["count"] == 1
        assert platinum_tier["value"] == 150000.0

        # Check stage breakdown
        assert len(summary["by_stage"]) == 2
        proposal_stage = next(s for s in summary["by_stage"] if s["stage"] == "proposal_sent")
        assert proposal_stage["count"] == 1
        assert proposal_stage["total_value"] == 150000.0
        assert proposal_stage["weighted_value"] == 105000.0  # 150000 * 0.70


class TestProposalManagement:
    """Test proposal operations"""

    def test_create_proposal(self, crm_service, sample_contact):
        """Test creating a proposal"""
        proposal = crm_service.create_proposal(
            contact_id=sample_contact.contact_id,
            template_used="fractional_cto",
            proposal_value=Decimal("120000.00"),
            estimated_close_probability=Decimal("0.75"),
            roi_analysis={
                "annual_cost_savings": 180000,
                "productivity_gains": 250000,
                "payback_months": 3.4,
                "roi_percentage": 258.3,
            },
            custom_requirements="Focus on Series B scaling challenges",
            status="draft",
        )

        assert proposal.proposal_id is not None
        assert proposal.contact_id == sample_contact.contact_id
        assert proposal.template_used == "fractional_cto"
        assert proposal.proposal_value == Decimal("120000.00")
        assert proposal.status == "draft"
        assert proposal.roi_analysis["payback_months"] == 3.4

    def test_update_proposal_status(self, crm_service, sample_contact):
        """Test updating proposal status"""
        proposal = crm_service.create_proposal(
            contact_id=sample_contact.contact_id,
            template_used="team_building",
            proposal_value=Decimal("75000.00"),
            estimated_close_probability=Decimal("0.65"),
            status="draft",
        )

        sent_time = datetime.now()
        updated = crm_service.update_proposal_status(
            proposal.proposal_id,
            status="sent",
            sent_at=sent_time,
        )

        assert updated.status == "sent"
        assert updated.sent_at == sent_time

    def test_get_proposals_for_contact(self, crm_service, sample_contact):
        """Test retrieving all proposals for a contact"""
        # Create multiple proposals
        crm_service.create_proposal(
            sample_contact.contact_id,
            "fractional_cto",
            Decimal("120000.00"),
            Decimal("0.75"),
            status="draft",
        )
        crm_service.create_proposal(
            sample_contact.contact_id,
            "team_building",
            Decimal("50000.00"),
            Decimal("0.60"),
            status="sent",
        )
        crm_service.create_proposal(
            sample_contact.contact_id,
            "nobuild_audit",
            Decimal("30000.00"),
            Decimal("0.50"),
            status="draft",
        )

        # Get all proposals
        all_proposals = crm_service.get_proposals_for_contact(sample_contact.contact_id)
        assert len(all_proposals) == 3

        # Filter by status
        sent_proposals = crm_service.get_proposals_for_contact(
            sample_contact.contact_id,
            status="sent",
        )
        assert len(sent_proposals) == 1
        assert sent_proposals[0].status == "sent"


class TestRevenueForecast:
    """Test revenue forecasting operations"""

    def test_create_revenue_forecast(self, crm_service):
        """Test creating a revenue forecast"""
        forecast = crm_service.create_revenue_forecast(
            forecast_period="annual",
            predicted_revenue=Decimal("1500000.00"),
            confidence_level=Decimal("0.85"),
            forecast_model="tier_based",
            input_parameters={
                "pipeline_count": 25,
                "avg_deal_size": 60000,
                "conversion_rate": 0.45,
            },
        )

        assert forecast.forecast_id is not None
        assert forecast.forecast_period == "annual"
        assert forecast.predicted_revenue == Decimal("1500000.00")
        assert forecast.confidence_level == Decimal("0.85")
        assert forecast.input_parameters["pipeline_count"] == 25

    def test_calculate_pipeline_forecast(self, crm_service):
        """Test calculating forecast from current pipeline"""
        # Create contacts with different tiers
        crm_service.create_contact(
            "Platinum 1", "p1@example.com",
            lead_score=90, estimated_value=Decimal("150000.00"),
            priority_tier="platinum", qualification_status="qualified",
        )
        crm_service.create_contact(
            "Platinum 2", "p2@example.com",
            lead_score=85, estimated_value=Decimal("120000.00"),
            priority_tier="platinum", qualification_status="qualified",
        )
        crm_service.create_contact(
            "Gold 1", "g1@example.com",
            lead_score=75, estimated_value=Decimal("80000.00"),
            priority_tier="gold", qualification_status="qualified",
        )
        crm_service.create_contact(
            "Silver 1", "s1@example.com",
            lead_score=60, estimated_value=Decimal("40000.00"),
            priority_tier="silver", qualification_status="qualified",
        )

        forecast = crm_service.calculate_pipeline_forecast(forecast_period="annual")

        assert forecast["forecast_period"] == "annual"
        assert forecast["current_pipeline_revenue"] > 0
        assert forecast["growth_pipeline_revenue"] > 0
        assert forecast["total_projected_revenue"] > 0
        assert "confidence_interval" in forecast
        assert forecast["confidence_interval"]["min"] < forecast["confidence_interval"]["max"]
        assert "by_tier" in forecast
        assert "arr_target_achievement" in forecast

        # Verify tier breakdown exists
        assert "platinum" in forecast["by_tier"]
        platinum = forecast["by_tier"]["platinum"]
        assert platinum["contact_count"] == 2
        assert platinum["conversion_rate"] > 0

    def test_forecast_different_periods(self, crm_service, sample_contact):
        """Test forecasting for different time periods"""
        # Monthly forecast
        monthly = crm_service.calculate_pipeline_forecast("monthly")
        assert monthly["forecast_period"] == "monthly"

        # Quarterly forecast
        quarterly = crm_service.calculate_pipeline_forecast("quarterly")
        assert quarterly["forecast_period"] == "quarterly"

        # Annual forecast
        annual = crm_service.calculate_pipeline_forecast("annual")
        assert annual["forecast_period"] == "annual"

        # Annual should be approximately 12x monthly (with growth)
        # Not exact due to growth calculations
        assert annual["current_pipeline_revenue"] > monthly["current_pipeline_revenue"]


class TestABTestingCampaigns:
    """Test A/B testing campaign operations"""

    def test_create_ab_test_campaign(self, crm_service):
        """Test creating an A/B test campaign"""
        campaign = crm_service.create_ab_test_campaign(
            name="LinkedIn Outreach Optimization",
            test_type="linkedin_message",
            target_metric="response_rate",
            variants={
                "variant_a": {
                    "name": "Direct Approach",
                    "message": "I'd like to discuss your technical challenges",
                },
                "variant_b": {
                    "name": "Value-First Approach",
                    "message": "I have insights that might help optimize your engineering costs",
                },
            },
            description="Testing different outreach approaches for platinum tier contacts",
            status="active",
        )

        assert campaign.campaign_id is not None
        assert campaign.name == "LinkedIn Outreach Optimization"
        assert campaign.test_type == "linkedin_message"
        assert campaign.status == "active"
        assert "variant_a" in campaign.variants
        assert "variant_b" in campaign.variants

    def test_update_ab_test_results(self, crm_service):
        """Test updating A/B test campaign results"""
        campaign = crm_service.create_ab_test_campaign(
            name="Email Subject Test",
            test_type="email_subject",
            target_metric="open_rate",
            variants={"variant_a": {}, "variant_b": {}},
        )

        results = {
            "variant_a": {
                "sent": 100,
                "opened": 35,
                "clicked": 12,
                "converted": 3,
            },
            "variant_b": {
                "sent": 100,
                "opened": 48,
                "clicked": 18,
                "converted": 5,
            },
            "statistical_significance": 0.95,
            "winning_variant": "variant_b",
        }

        updated = crm_service.update_ab_test_results(
            campaign.campaign_id,
            results=results,
            winner_variant="variant_b",
        )

        assert updated.results == results
        assert updated.winner_variant == "variant_b"
        assert updated.results["statistical_significance"] == 0.95


class TestHealthAndMaintenance:
    """Test service health and maintenance operations"""

    def test_health_check(self, crm_service):
        """Test database health check"""
        health = crm_service.health_check()

        assert health["status"] == "healthy"
        assert "connection_pool" in health

    def test_service_close(self, crm_service):
        """Test closing service connections"""
        # Should not raise errors
        crm_service.close()


class TestConvenienceFunctions:
    """Test convenience functions and factory methods"""

    def test_get_crm_service(self):
        """Test get_crm_service factory function"""
        service = get_crm_service(
            database=":memory:",
            use_async=False,
        )

        # Override for SQLite
        service.engine = create_engine("sqlite:///:memory:")
        service.SessionLocal = sessionmaker(bind=service.engine)
        Base.metadata.create_all(service.engine)

        # Should be able to create a contact
        contact = service.create_contact(
            name="Test User",
            email="test@example.com",
        )

        assert contact.contact_id is not None
        service.close()


class TestErrorHandling:
    """Test error handling and edge cases"""

    def test_create_duplicate_email_fails(self, crm_service):
        """Test that creating duplicate email raises error"""
        crm_service.create_contact(
            name="First User",
            email="duplicate@example.com",
        )

        # Second contact with same email should fail
        with pytest.raises(CRMServiceError):
            crm_service.create_contact(
                name="Second User",
                email="duplicate@example.com",
            )

    def test_invalid_operations_raise_errors(self, crm_service):
        """Test that invalid operations raise appropriate errors"""
        # Update non-existent contact
        with pytest.raises(ContactNotFoundError):
            crm_service.update_contact(uuid4(), name="Updated")

        # Update lead score for non-existent contact
        with pytest.raises(ContactNotFoundError):
            crm_service.update_lead_score(uuid4(), 80)

        # Create pipeline for non-existent contact
        with pytest.raises(ContactNotFoundError):
            crm_service.create_pipeline_entry(
                uuid4(), "qualified", Decimal("0.5"), Decimal("50000")
            )


# Usage Examples as Documentation
def example_basic_usage():
    """
    Example: Basic CRM service usage

    This demonstrates the typical workflow for managing contacts
    and generating proposals in the Epic 7 sales automation system.
    """
    # Initialize service
    service = get_crm_service(database=":memory:")

    # Create a contact
    contact = service.create_contact(
        name="Sarah Chen",
        email="sarah.chen@dataflow.com",
        company="DataFlow Analytics",
        title="VP of Engineering",
        lead_score=85,
        estimated_value=Decimal("120000.00"),
        priority_tier="platinum",
    )

    # Update lead score after qualification
    service.update_lead_score(
        contact.contact_id,
        new_score=92,
        qualification_criteria={"budget_confirmed": True},
        qualified_by="sales_team",
    )

    # Create pipeline entry
    pipeline = service.create_pipeline_entry(
        contact.contact_id,
        stage="qualified",
        probability=Decimal("0.75"),
        deal_value=Decimal("120000.00"),
    )

    # Create proposal
    proposal = service.create_proposal(
        contact.contact_id,
        template_used="fractional_cto",
        proposal_value=Decimal("120000.00"),
        estimated_close_probability=Decimal("0.75"),
        roi_analysis={"annual_savings": 180000},
    )

    # Get pipeline summary
    summary = service.get_pipeline_summary()
    print(f"Total pipeline value: ${summary['total_pipeline_value']:,.2f}")

    service.close()


def example_revenue_forecasting():
    """
    Example: Revenue forecasting

    Demonstrates how to use the forecasting capabilities
    to project revenue based on current pipeline.
    """
    service = get_crm_service(database=":memory:")

    # Create qualified contacts
    for i in range(5):
        service.create_contact(
            name=f"Contact {i}",
            email=f"contact{i}@example.com",
            lead_score=75 + i * 3,
            estimated_value=Decimal(str(50000 + i * 20000)),
            priority_tier="gold" if i < 3 else "silver",
            qualification_status="qualified",
        )

    # Generate forecast
    forecast = service.calculate_pipeline_forecast("annual")

    print(f"Annual revenue projection: ${forecast['total_projected_revenue']:,.2f}")
    print(f"ARR target achievement: {forecast['arr_target_achievement']['achievement_percentage']:.1f}%")

    service.close()


if __name__ == "__main__":
    # Run usage examples
    print("=" * 60)
    print("CRM Service Usage Examples")
    print("=" * 60)

    print("\n1. Basic Usage:")
    example_basic_usage()

    print("\n2. Revenue Forecasting:")
    example_revenue_forecasting()

    print("\n" + "=" * 60)
    print("Run 'pytest tests/services/test_crm_service.py -v' for full test suite")
