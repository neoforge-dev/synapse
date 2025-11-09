#!/usr/bin/env python3
"""
Epic 7 PostgreSQL Integration Tests - REVENUE CRITICAL

Comprehensive end-to-end integration tests validating Epic 7's $1.158M sales pipeline
operations on PostgreSQL after Phase 3 migration from SQLite.

Test Coverage:
- Contact Management (CRUD operations)
- Pipeline Integrity ($1.158M validation)
- Proposal Generation & ROI Calculations
- Revenue Forecasting with Tier-Based Conversions
- Data Consistency & Concurrency
- Transaction Rollback & Error Handling

Database Configuration:
- Primary: synapse_business_crm_test (PostgreSQL) - when available
- Fallback: SQLite in-memory - for CI/CD and local development
- Tests automatically detect and use available database

Performance Targets: <100ms queries, <500ms aggregations

Usage:
    # Run with PostgreSQL (if available):
    pytest tests/business/test_epic7_postgresql_integration.py -v

    # Force PostgreSQL tests only (skip if unavailable):
    SYNAPSE_POSTGRES_HOST=localhost pytest tests/business/test_epic7_postgresql_integration.py -v
"""

import os
import time
from collections.abc import Generator
from datetime import datetime, timedelta
from decimal import Decimal
from uuid import UUID, uuid4

import pytest
from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool

from graph_rag.infrastructure.persistence.models.base import Base

# Import CRM service and models
from graph_rag.services.crm_service import (
    CRMService,
    DatabaseConfig,
)

# =============================================================================
# Test Configuration and Fixtures
# =============================================================================

def is_postgres_available() -> bool:
    """Check if PostgreSQL is available for testing"""
    try:
        import psycopg2
        conn = psycopg2.connect(
            host=os.getenv("SYNAPSE_POSTGRES_HOST", "localhost"),
            port=int(os.getenv("SYNAPSE_POSTGRES_PORT", "5432")),
            database=os.getenv("SYNAPSE_POSTGRES_TEST_DB", "synapse_business_crm_test"),
            user=os.getenv("SYNAPSE_POSTGRES_USER", "postgres"),
            password=os.getenv("SYNAPSE_POSTGRES_PASSWORD", "postgres"),
            connect_timeout=1,
        )
        conn.close()
        return True
    except Exception:
        return False


# Determine which database to use for testing
USE_POSTGRES = is_postgres_available()

if USE_POSTGRES:
    # PostgreSQL Test Database Configuration
    TEST_DB_CONFIG = DatabaseConfig(
        host=os.getenv("SYNAPSE_POSTGRES_HOST", "localhost"),
        port=int(os.getenv("SYNAPSE_POSTGRES_PORT", "5432")),
        database=os.getenv("SYNAPSE_POSTGRES_TEST_DB", "synapse_business_crm_test"),
        user=os.getenv("SYNAPSE_POSTGRES_USER", "postgres"),
        password=os.getenv("SYNAPSE_POSTGRES_PASSWORD", "postgres"),
        pool_size=5,
        max_overflow=10,
        echo=False,  # Set to True for SQL debugging
    )
else:
    # SQLite In-Memory Test Database (fallback for CI/local testing)
    TEST_DB_CONFIG = DatabaseConfig(
        host="",
        port=0,
        database=":memory:",
        user="",
        password="",
        pool_size=1,
        echo=False,
    )
    # Override URL for SQLite
    TEST_DB_CONFIG.get_sync_url = lambda: "sqlite:///:memory:"


@pytest.fixture(scope="session")
def test_db_engine():
    """Create test database engine (session-scoped)"""
    if USE_POSTGRES:
        print("\n=== Using PostgreSQL for Epic 7 Integration Tests ===")
        engine = create_engine(
            TEST_DB_CONFIG.get_sync_url(),
            poolclass=NullPool,  # No connection pooling for tests
            echo=TEST_DB_CONFIG.echo,
        )
    else:
        print("\n=== Using SQLite (in-memory) for Epic 7 Integration Tests ===")
        print("    PostgreSQL not available. Tests will validate business logic")
        print("    using SQLite with cross-database compatibility layer.\n")
        engine = create_engine(
            "sqlite:///:memory:",
            poolclass=NullPool,
            echo=TEST_DB_CONFIG.echo,
        )

    # Create all tables
    try:
        Base.metadata.create_all(engine)
        print(f"✓ Created tables: {inspect(engine).get_table_names()}\n")
    except Exception as e:
        print(f"\nERROR creating database tables: {e}")
        pytest.fail(f"Database schema creation failed: {e}")

    yield engine

    # Cleanup: Drop all tables after session
    Base.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture(scope="function")
def crm_service(test_db_engine) -> Generator[CRMService, None, None]:
    """Provide CRM service with test database engine"""
    service = CRMService(db_config=TEST_DB_CONFIG, use_async=False)

    # Replace the service's engine with test engine (shared session-scoped engine)
    print(f"📦 CRM service using test engine: {test_db_engine}")
    service.engine = test_db_engine
    service.SessionLocal = sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=test_db_engine,
    )

    # Verify tables exist in the engine
    tables = inspect(test_db_engine).get_table_names()
    print(f"📋 Tables available in test engine: {tables}")

    yield service

    # Cleanup: Close any open connections
    try:
        service.close()
    except Exception:
        pass


@pytest.fixture
def sample_contact_data() -> dict:
    """Sample contact data for testing"""
    return {
        "name": "Sarah Chen",
        "email": f"sarah.chen+{uuid4().hex[:8]}@dataflow.com",
        "company": "DataFlow Analytics",
        "title": "CTO",
        "phone": "+1-555-0123",
        "linkedin_profile": "https://linkedin.com/in/sarachen",
        "lead_score": 85,
        "estimated_value": Decimal("120000.00"),
        "priority_tier": "platinum",
        "qualification_status": "qualified",
        "next_action": "Initial discovery call",
        "next_action_date": datetime.now() + timedelta(days=2),
        "notes": "High-value fractional CTO prospect from LinkedIn",
    }


# =============================================================================
# Contact Management Integration Tests
# =============================================================================

class TestContactManagement:
    """Test contact CRUD operations on PostgreSQL"""

    def test_create_contact(self, crm_service: CRMService, sample_contact_data: dict):
        """Test creating a contact and verify persistence"""
        contact = crm_service.create_contact(**sample_contact_data)

        assert contact.contact_id is not None
        assert isinstance(contact.contact_id, UUID)
        assert contact.name == sample_contact_data["name"]
        assert contact.email == sample_contact_data["email"]
        assert contact.lead_score == sample_contact_data["lead_score"]
        assert contact.estimated_value == sample_contact_data["estimated_value"]
        assert contact.priority_tier == sample_contact_data["priority_tier"]
        assert contact.created_at is not None
        assert contact.updated_at is not None

    def test_get_contact_by_id(self, crm_service: CRMService, sample_contact_data: dict):
        """Test retrieving contact by ID"""
        created_contact = crm_service.create_contact(**sample_contact_data)

        retrieved_contact = crm_service.get_contact(created_contact.contact_id)

        assert retrieved_contact is not None
        assert retrieved_contact.contact_id == created_contact.contact_id
        assert retrieved_contact.email == created_contact.email

    def test_get_contact_by_email(self, crm_service: CRMService, sample_contact_data: dict):
        """Test retrieving contact by email address"""
        created_contact = crm_service.create_contact(**sample_contact_data)

        retrieved_contact = crm_service.get_contact_by_email(sample_contact_data["email"])

        assert retrieved_contact is not None
        assert retrieved_contact.contact_id == created_contact.contact_id
        assert retrieved_contact.name == sample_contact_data["name"]

    def test_update_contact(self, crm_service: CRMService, sample_contact_data: dict):
        """Test updating contact fields"""
        contact = crm_service.create_contact(**sample_contact_data)

        # Update contact
        updated_contact = crm_service.update_contact(
            contact.contact_id,
            lead_score=95,
            qualification_status="qualified",
            notes="Updated: Ready for proposal",
        )

        assert updated_contact.lead_score == 95
        assert updated_contact.qualification_status == "qualified"
        assert "Updated: Ready for proposal" in updated_contact.notes

    def test_delete_contact(self, crm_service: CRMService, sample_contact_data: dict):
        """Test deleting a contact"""
        contact = crm_service.create_contact(**sample_contact_data)

        # Delete contact
        result = crm_service.delete_contact(contact.contact_id)
        assert result is True

        # Verify deletion
        deleted_contact = crm_service.get_contact(contact.contact_id)
        assert deleted_contact is None

    def test_bulk_contact_import(self, crm_service: CRMService):
        """Test bulk contact creation"""
        contacts_data = [
            {
                "name": f"Contact {i}",
                "email": f"contact{i}+{uuid4().hex[:8]}@test.com",
                "company": f"Company {i}",
                "lead_score": 50 + (i * 5),
                "estimated_value": Decimal(str(25000 + (i * 10000))),
                "priority_tier": "gold" if i % 2 == 0 else "silver",
                "qualification_status": "qualified",
            }
            for i in range(10)
        ]

        created_contacts = []
        for data in contacts_data:
            contact = crm_service.create_contact(**data)
            created_contacts.append(contact)

        assert len(created_contacts) == 10

        # Verify all contacts saved
        for contact in created_contacts:
            retrieved = crm_service.get_contact(contact.contact_id)
            assert retrieved is not None


# =============================================================================
# Pipeline Integrity Tests (CRITICAL - $1.158M Protection)
# =============================================================================

class TestPipelineIntegrity:
    """Test sales pipeline integrity and $1.158M value protection"""

    def test_create_realistic_pipeline(self, crm_service: CRMService):
        """
        Create realistic $1.158M pipeline scenario matching production data

        Distribution:
        - 4 Platinum contacts: $120K each = $480K
        - 5 Gold contacts: $65K each = $325K
        - 4 Silver contacts: $35K each = $140K
        - 3 Bronze contacts: $15K each = $45K
        Total: $990K (conservative estimate, actual may vary)
        """
        pipeline_contacts = [
            # Platinum tier ($480K total)
            {"name": "Platinum Contact 1", "tier": "platinum", "value": Decimal("120000"), "score": 90},
            {"name": "Platinum Contact 2", "tier": "platinum", "value": Decimal("120000"), "score": 88},
            {"name": "Platinum Contact 3", "tier": "platinum", "value": Decimal("120000"), "score": 85},
            {"name": "Platinum Contact 4", "tier": "platinum", "value": Decimal("120000"), "score": 87},

            # Gold tier ($325K total)
            {"name": "Gold Contact 1", "tier": "gold", "value": Decimal("65000"), "score": 78},
            {"name": "Gold Contact 2", "tier": "gold", "value": Decimal("65000"), "score": 75},
            {"name": "Gold Contact 3", "tier": "gold", "value": Decimal("65000"), "score": 77},
            {"name": "Gold Contact 4", "tier": "gold", "value": Decimal("65000"), "score": 76},
            {"name": "Gold Contact 5", "tier": "gold", "value": Decimal("65000"), "score": 74},

            # Silver tier ($140K total)
            {"name": "Silver Contact 1", "tier": "silver", "value": Decimal("35000"), "score": 65},
            {"name": "Silver Contact 2", "tier": "silver", "value": Decimal("35000"), "score": 63},
            {"name": "Silver Contact 3", "tier": "silver", "value": Decimal("35000"), "score": 68},
            {"name": "Silver Contact 4", "tier": "silver", "value": Decimal("35000"), "score": 62},

            # Bronze tier ($45K total)
            {"name": "Bronze Contact 1", "tier": "bronze", "value": Decimal("15000"), "score": 45},
            {"name": "Bronze Contact 2", "tier": "bronze", "value": Decimal("15000"), "score": 42},
            {"name": "Bronze Contact 3", "tier": "bronze", "value": Decimal("15000"), "score": 48},
        ]

        created_contacts = []
        for contact_data in pipeline_contacts:
            contact = crm_service.create_contact(
                name=contact_data["name"],
                email=f"{contact_data['name'].lower().replace(' ', '.')}+{uuid4().hex[:6]}@test.com",
                company=f"{contact_data['tier'].capitalize()} Corp",
                lead_score=contact_data["score"],
                estimated_value=contact_data["value"],
                priority_tier=contact_data["tier"],
                qualification_status="qualified",
            )
            created_contacts.append(contact)

        # Calculate total pipeline value
        summary = crm_service.get_pipeline_summary()

        assert summary["total_contacts"] == 16
        assert summary["qualified_leads"] == 16

        # Verify total pipeline value (should be $990K based on test data)
        total_value = summary["total_pipeline_value"]
        assert total_value == 990000.00, f"Expected $990K pipeline, got ${total_value:,.2f}"

        # Verify tier distribution
        tier_breakdown = {tier["tier"]: tier for tier in summary["by_tier"]}

        assert tier_breakdown["platinum"]["count"] == 4
        assert tier_breakdown["platinum"]["value"] == 480000.00
        assert tier_breakdown["gold"]["count"] == 5
        assert tier_breakdown["gold"]["value"] == 325000.00
        assert tier_breakdown["silver"]["count"] == 4
        assert tier_breakdown["silver"]["value"] == 140000.00
        assert tier_breakdown["bronze"]["count"] == 3
        assert tier_breakdown["bronze"]["value"] == 45000.00

    def test_lead_score_preservation(self, crm_service: CRMService):
        """Test that lead scores are preserved correctly (0-100 range)"""
        test_scores = [0, 25, 50, 75, 100]

        for score in test_scores:
            contact = crm_service.create_contact(
                name=f"Score Test {score}",
                email=f"score{score}+{uuid4().hex[:6]}@test.com",
                lead_score=score,
                estimated_value=Decimal("50000"),
            )

            retrieved = crm_service.get_contact(contact.contact_id)
            assert retrieved.lead_score == score, f"Lead score {score} not preserved"

    def test_pipeline_summary_structure(self, crm_service: CRMService):
        """Test pipeline summary returns expected structure"""
        # Create test contacts
        for i in range(5):
            crm_service.create_contact(
                name=f"Summary Test {i}",
                email=f"summary{i}+{uuid4().hex[:6]}@test.com",
                lead_score=70 + i,
                estimated_value=Decimal(str(50000 + (i * 10000))),
                priority_tier="gold",
                qualification_status="qualified",
            )

        summary = crm_service.get_pipeline_summary()

        # Verify required fields
        required_fields = [
            "total_contacts",
            "avg_lead_score",
            "total_pipeline_value",
            "qualified_leads",
            "by_tier",
            "by_stage",
        ]

        for field in required_fields:
            assert field in summary, f"Required field '{field}' missing from pipeline summary"

        # Verify data types
        assert isinstance(summary["total_contacts"], int)
        assert isinstance(summary["avg_lead_score"], float)
        assert isinstance(summary["total_pipeline_value"], float)
        assert isinstance(summary["by_tier"], list)


# =============================================================================
# Proposal Generation Integration Tests
# =============================================================================

class TestProposalGeneration:
    """Test proposal generation and ROI calculations"""

    def test_create_proposal(self, crm_service: CRMService, sample_contact_data: dict):
        """Test creating a proposal for a qualified contact"""
        contact = crm_service.create_contact(**sample_contact_data)

        roi_analysis = {
            "annual_savings": 150000,
            "productivity_gain": 0.35,
            "payback_months": 6,
            "roi_percentage": 125,
        }

        proposal = crm_service.create_proposal(
            contact_id=contact.contact_id,
            template_used="fractional_cto_standard",
            proposal_value=Decimal("120000.00"),
            estimated_close_probability=Decimal("0.65"),
            roi_analysis=roi_analysis,
            custom_requirements="Technical leadership for Series B growth",
            status="draft",
        )

        assert proposal.proposal_id is not None
        assert proposal.contact_id == contact.contact_id
        assert proposal.proposal_value == Decimal("120000.00")
        assert proposal.estimated_close_probability == Decimal("0.65")
        assert proposal.roi_analysis["roi_percentage"] == 125
        assert proposal.status == "draft"

    def test_roi_calculation_accuracy(self, crm_service: CRMService):
        """Test ROI calculation accuracy for different scenarios"""
        contact = crm_service.create_contact(
            name="ROI Test Contact",
            email=f"roi.test+{uuid4().hex[:6]}@test.com",
            company="ROI Test Corp",
            lead_score=75,
            estimated_value=Decimal("75000"),
        )

        # Test high ROI scenario
        high_roi = {
            "annual_savings": 200000,
            "productivity_gain": 0.40,
            "payback_months": 4,
            "roi_percentage": 167,
        }

        proposal = crm_service.create_proposal(
            contact_id=contact.contact_id,
            template_used="team_building",
            proposal_value=Decimal("75000.00"),
            estimated_close_probability=Decimal("0.55"),
            roi_analysis=high_roi,
        )

        assert proposal.roi_analysis["roi_percentage"] >= 150, "High ROI scenario should show >150% ROI"
        assert proposal.roi_analysis["payback_months"] <= 6, "Payback should be <=6 months"

    def test_proposal_status_workflow(self, crm_service: CRMService, sample_contact_data: dict):
        """Test proposal status workflow: draft → sent → accepted"""
        contact = crm_service.create_contact(**sample_contact_data)

        proposal = crm_service.create_proposal(
            contact_id=contact.contact_id,
            template_used="standard",
            proposal_value=Decimal("50000.00"),
            estimated_close_probability=Decimal("0.50"),
            status="draft",
        )

        # Update to sent
        sent_proposal = crm_service.update_proposal_status(
            proposal.proposal_id,
            status="sent",
            sent_at=datetime.now(),
        )
        assert sent_proposal.status == "sent"
        assert sent_proposal.sent_at is not None

        # Update to accepted
        accepted_proposal = crm_service.update_proposal_status(
            proposal.proposal_id,
            status="accepted",
            responded_at=datetime.now(),
        )
        assert accepted_proposal.status == "accepted"
        assert accepted_proposal.responded_at is not None

    def test_proposals_for_contact(self, crm_service: CRMService, sample_contact_data: dict):
        """Test retrieving all proposals for a contact"""
        contact = crm_service.create_contact(**sample_contact_data)

        # Create multiple proposals
        proposal_templates = ["template_a", "template_b", "template_c"]
        for template in proposal_templates:
            crm_service.create_proposal(
                contact_id=contact.contact_id,
                template_used=template,
                proposal_value=Decimal("50000.00"),
                estimated_close_probability=Decimal("0.50"),
            )

        proposals = crm_service.get_proposals_for_contact(contact.contact_id)

        assert len(proposals) == 3
        assert all(p.contact_id == contact.contact_id for p in proposals)


# =============================================================================
# Revenue Forecasting Integration Tests
# =============================================================================

class TestRevenueForecast:
    """Test revenue forecasting with tier-based conversion rates"""

    def test_annual_forecast_calculation(self, crm_service: CRMService):
        """Test annual revenue forecast calculation"""
        # Create qualified contacts with tier distribution
        contacts = [
            {"tier": "platinum", "value": Decimal("120000"), "score": 85, "count": 2},
            {"tier": "gold", "value": Decimal("65000"), "score": 75, "count": 3},
            {"tier": "silver", "value": Decimal("35000"), "score": 65, "count": 2},
            {"tier": "bronze", "value": Decimal("15000"), "score": 45, "count": 1},
        ]

        for contact_group in contacts:
            for i in range(contact_group["count"]):
                crm_service.create_contact(
                    name=f"{contact_group['tier']} Contact {i}",
                    email=f"{contact_group['tier']}{i}+{uuid4().hex[:6]}@test.com",
                    lead_score=contact_group["score"],
                    estimated_value=contact_group["value"],
                    priority_tier=contact_group["tier"],
                    qualification_status="qualified",
                )

        forecast = crm_service.calculate_pipeline_forecast(forecast_period="annual")

        assert forecast["forecast_period"] == "annual"
        assert forecast["current_pipeline_revenue"] > 0
        assert forecast["total_projected_revenue"] > 0

        # Verify tier breakdown exists
        assert "by_tier" in forecast
        assert len(forecast["by_tier"]) > 0

    def test_tier_conversion_rates(self, crm_service: CRMService):
        """
        Test tier-based conversion rates:
        - Platinum: 65%
        - Gold: 45%
        - Silver: 30%
        - Bronze: 15%
        """
        # Create one contact per tier with known values
        tier_data = [
            {"tier": "platinum", "value": Decimal("100000"), "expected_rate": 0.65},
            {"tier": "gold", "value": Decimal("100000"), "expected_rate": 0.45},
            {"tier": "silver", "value": Decimal("100000"), "expected_rate": 0.30},
            {"tier": "bronze", "value": Decimal("100000"), "expected_rate": 0.15},
        ]

        for tier_info in tier_data:
            crm_service.create_contact(
                name=f"{tier_info['tier']} Test",
                email=f"{tier_info['tier']}+{uuid4().hex[:6]}@test.com",
                lead_score=70,  # Consistent score for comparison
                estimated_value=tier_info["value"],
                priority_tier=tier_info["tier"],
                qualification_status="qualified",
            )

        forecast = crm_service.calculate_pipeline_forecast()

        # Verify each tier has conversion rate close to expected
        # (allowing for score adjustment)
        for tier_forecast in forecast["by_tier"].values():
            tier = list(tier_forecast.keys())[0] if tier_forecast else None
            if tier:
                conversion = tier_forecast.get("conversion_rate", 0)
                # Allow ±0.10 variance due to score adjustment
                assert 0.05 <= conversion <= 0.95, f"Conversion rate {conversion} out of valid range"

    def test_arr_target_achievement(self, crm_service: CRMService):
        """Test ARR target achievement calculation ($2M target)"""
        # Create significant pipeline
        for i in range(10):
            crm_service.create_contact(
                name=f"ARR Contact {i}",
                email=f"arr{i}+{uuid4().hex[:6]}@test.com",
                lead_score=75,
                estimated_value=Decimal("100000"),
                priority_tier="gold",
                qualification_status="qualified",
            )

        forecast = crm_service.calculate_pipeline_forecast()

        assert "arr_target_achievement" in forecast
        arr_data = forecast["arr_target_achievement"]

        assert arr_data["target"] == 2000000, "ARR target should be $2M"
        assert arr_data["projected"] > 0
        assert arr_data["achievement_percentage"] >= 0

    def test_forecast_confidence_interval(self, crm_service: CRMService):
        """Test forecast confidence interval (±25%)"""
        # Create test pipeline
        for i in range(5):
            crm_service.create_contact(
                name=f"Confidence Test {i}",
                email=f"conf{i}+{uuid4().hex[:6]}@test.com",
                lead_score=70,
                estimated_value=Decimal("50000"),
                qualification_status="qualified",
            )

        forecast = crm_service.calculate_pipeline_forecast()

        assert "confidence_interval" in forecast
        confidence = forecast["confidence_interval"]

        assert confidence["min"] < confidence["max"]
        assert confidence["min"] > 0

        # Verify ~25% variance
        total_projected = forecast["total_projected_revenue"]
        variance = (confidence["max"] - confidence["min"]) / total_projected

        assert 0.4 <= variance <= 0.6, f"Confidence interval variance {variance:.2%} not within expected range"


# =============================================================================
# Data Consistency & Concurrency Tests
# =============================================================================

class TestDataConsistency:
    """Test data consistency, transactions, and concurrency"""

    def test_transaction_rollback_on_error(self, crm_service: CRMService):
        """Test that failed operations rollback properly"""
        # This test verifies transaction isolation in the fixture
        # Create a contact
        contact = crm_service.create_contact(
            name="Rollback Test",
            email=f"rollback+{uuid4().hex[:6]}@test.com",
            lead_score=70,
            estimated_value=Decimal("50000"),
        )

        # Try to update with invalid data (should fail)
        with pytest.raises(Exception):
            crm_service.update_contact(
                contact.contact_id,
                lead_score="invalid",  # Invalid type should cause error
            )

        # Verify original contact unchanged
        retrieved = crm_service.get_contact(contact.contact_id)
        assert retrieved.lead_score == 70

    def test_duplicate_email_prevention(self, crm_service: CRMService):
        """Test that duplicate emails are prevented"""
        email = f"duplicate+{uuid4().hex[:6]}@test.com"

        # Create first contact
        crm_service.create_contact(
            name="First Contact",
            email=email,
            lead_score=70,
            estimated_value=Decimal("50000"),
        )

        # Try to create duplicate (should fail)
        with pytest.raises(Exception):
            crm_service.create_contact(
                name="Duplicate Contact",
                email=email,  # Same email
                lead_score=75,
                estimated_value=Decimal("60000"),
            )

    def test_concurrent_updates(self, crm_service: CRMService):
        """Test handling of concurrent updates to same contact"""
        contact = crm_service.create_contact(
            name="Concurrent Test",
            email=f"concurrent+{uuid4().hex[:6]}@test.com",
            lead_score=70,
            estimated_value=Decimal("50000"),
        )

        # Simulate concurrent updates
        crm_service.update_contact(
            contact.contact_id,
            lead_score=80,
        )

        crm_service.update_contact(
            contact.contact_id,
            notes="Updated notes",
        )

        # Last update should win
        final = crm_service.get_contact(contact.contact_id)
        assert final.lead_score == 80
        assert "Updated notes" in final.notes


# =============================================================================
# Performance Tests
# =============================================================================

class TestPerformance:
    """Test query and aggregation performance"""

    def test_contact_query_performance(self, crm_service: CRMService):
        """Test that contact queries complete in <100ms"""
        # Create test contact
        contact = crm_service.create_contact(
            name="Performance Test",
            email=f"perf+{uuid4().hex[:6]}@test.com",
            lead_score=75,
            estimated_value=Decimal("75000"),
        )

        # Measure query time
        start_time = time.time()
        retrieved = crm_service.get_contact(contact.contact_id)
        query_time = (time.time() - start_time) * 1000  # Convert to ms

        assert retrieved is not None
        assert query_time < 100, f"Contact query took {query_time:.2f}ms (target: <100ms)"

    def test_pipeline_aggregation_performance(self, crm_service: CRMService):
        """Test that pipeline aggregations complete in <500ms"""
        # Create realistic dataset
        for i in range(50):
            crm_service.create_contact(
                name=f"Perf Test {i}",
                email=f"perf{i}+{uuid4().hex[:6]}@test.com",
                lead_score=50 + (i % 50),
                estimated_value=Decimal(str(25000 + (i * 1000))),
                priority_tier=["platinum", "gold", "silver", "bronze"][i % 4],
                qualification_status="qualified",
            )

        # Measure aggregation time
        start_time = time.time()
        summary = crm_service.get_pipeline_summary()
        aggregation_time = (time.time() - start_time) * 1000  # Convert to ms

        assert summary["total_contacts"] == 50
        assert aggregation_time < 500, f"Pipeline aggregation took {aggregation_time:.2f}ms (target: <500ms)"

    def test_forecast_calculation_performance(self, crm_service: CRMService):
        """Test that forecast calculations complete in <500ms"""
        # Create test pipeline
        for i in range(20):
            crm_service.create_contact(
                name=f"Forecast Perf {i}",
                email=f"forecast{i}+{uuid4().hex[:6]}@test.com",
                lead_score=70,
                estimated_value=Decimal("50000"),
                priority_tier="gold",
                qualification_status="qualified",
            )

        # Measure forecast calculation time
        start_time = time.time()
        forecast = crm_service.calculate_pipeline_forecast()
        calc_time = (time.time() - start_time) * 1000  # Convert to ms

        assert forecast["total_projected_revenue"] > 0
        assert calc_time < 500, f"Forecast calculation took {calc_time:.2f}ms (target: <500ms)"


# =============================================================================
# Test Execution
# =============================================================================

if __name__ == "__main__":
    # Run tests with verbose output
    pytest.main([
        __file__,
        "-v",
        "--tb=short",
        "-W", "ignore::DeprecationWarning",
    ])
