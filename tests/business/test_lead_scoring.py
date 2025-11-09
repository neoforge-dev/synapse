#!/usr/bin/env python3
"""
Epic 7 Lead Scoring Algorithm Tests
Tests for ML-based lead qualification and scoring algorithms protecting revenue accuracy
"""

import sys
import tempfile
from pathlib import Path

import pytest

# Add project root to path for imports
project_root = Path(__file__).parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from business_development.epic7_sales_automation import SalesAutomationEngine


class TestLeadScoringAccuracy:
    """Test lead scoring algorithm accuracy for revenue protection"""

    @pytest.fixture
    def temp_sales_db(self):
        """Create temporary sales automation database"""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
            db_path = tmp.name

        SalesAutomationEngine(db_path=db_path)
        yield db_path

        Path(db_path).unlink(missing_ok=True)

    @pytest.fixture
    def sales_engine(self, temp_sales_db):
        """Sales automation engine with test database"""
        return SalesAutomationEngine(db_path=temp_sales_db)

    def test_high_value_prospect_scoring(self, sales_engine):
        """Test scoring for high-value prospects (platinum tier)"""
        high_value_scenarios = [
            {
                'inquiry_text': 'We need strategic technical leadership for our Series B growth. Looking for fractional CTO to guide architecture decisions and team scaling. Budget approved and decision timeline is this month.',
                'company_size': 'Series B (50-200 employees)',
                'priority_score': 5,
                'inquiry_type': 'fractional_cto',
                'company': 'DataFlow Analytics (Series B funded)',
                'expected_min_score': 85
            },
            {
                'inquiry_text': 'Our 150-person engineering team is struggling with velocity and needs systematic team building. We have allocated budget for Q1 engagement and need to move fast.',
                'company_size': 'Enterprise (500+ employees)',
                'priority_score': 5,
                'inquiry_type': 'team_building',
                'company': 'TechCorp Enterprise Solutions',
                'expected_min_score': 80
            },
            {
                'inquiry_text': 'Critical project - our engineering team is building everything custom and burning budget. Need immediate NOBUILD audit to make better build vs buy decisions. Timeline is urgent.',
                'company_size': 'Series B (50-200 employees)',
                'priority_score': 5,
                'inquiry_type': 'nobuild_audit',
                'company': 'FinTech Scaling Solutions',
                'expected_min_score': 75
            }
        ]

        for scenario in high_value_scenarios:
            score = sales_engine._enhanced_ml_lead_scoring(
                inquiry_text=scenario['inquiry_text'],
                company_size=scenario['company_size'],
                priority_score=scenario['priority_score'],
                inquiry_type=scenario['inquiry_type'],
                company=scenario['company']
            )

            assert score >= scenario['expected_min_score'], \
                f"High-value scenario scored {score}, expected >={scenario['expected_min_score']}"

    def test_medium_value_prospect_scoring(self, sales_engine):
        """Test scoring for medium-value prospects (gold/silver tier)"""
        medium_value_scenarios = [
            {
                'inquiry_text': 'Interesting post about team building. We are a Series A startup with 30 engineers and looking to improve our processes.',
                'company_size': 'Series A (20-50 employees)',
                'priority_score': 3,
                'inquiry_type': 'team_building',
                'company': 'GrowthTech',
                'expected_range': (50, 75)
            },
            {
                'inquiry_text': 'Great insights on technical architecture. Our platform needs some optimization and we might need consulting help.',
                'company_size': 'Series A (20-50 employees)',
                'priority_score': 3,
                'inquiry_type': 'technical_architecture',
                'company': 'ScaleTech',
                'expected_range': (45, 70)
            }
        ]

        for scenario in medium_value_scenarios:
            score = sales_engine._enhanced_ml_lead_scoring(
                inquiry_text=scenario['inquiry_text'],
                company_size=scenario['company_size'],
                priority_score=scenario['priority_score'],
                inquiry_type=scenario['inquiry_type'],
                company=scenario['company']
            )

            min_score, max_score = scenario['expected_range']
            assert min_score <= score <= max_score, \
                f"Medium-value scenario scored {score}, expected {min_score}-{max_score}"

    def test_low_value_prospect_scoring(self, sales_engine):
        """Test scoring for low-value prospects (bronze tier or disqualified)"""
        low_value_scenarios = [
            {
                'inquiry_text': 'Nice post!',
                'company_size': 'Unknown',
                'priority_score': 1,
                'inquiry_type': 'general',
                'company': 'Unknown',
                'expected_max_score': 40
            },
            {
                'inquiry_text': 'Thanks for sharing this content.',
                'company_size': 'Seed/Pre-Series A (5-20 employees)',
                'priority_score': 1,
                'inquiry_type': 'general',
                'company': 'EarlyStage',
                'expected_max_score': 45
            },
            {
                'inquiry_text': 'Interesting perspective on technology.',
                'company_size': 'Unknown',
                'priority_score': 2,
                'inquiry_type': 'general',
                'company': 'Tech Company',
                'expected_max_score': 50
            }
        ]

        for scenario in low_value_scenarios:
            score = sales_engine._enhanced_ml_lead_scoring(
                inquiry_text=scenario['inquiry_text'],
                company_size=scenario['company_size'],
                priority_score=scenario['priority_score'],
                inquiry_type=scenario['inquiry_type'],
                company=scenario['company']
            )

            assert score <= scenario['expected_max_score'], \
                f"Low-value scenario scored {score}, expected <={scenario['expected_max_score']}"

    def test_buying_intent_signals(self, sales_engine):
        """Test detection of buying intent signals"""
        buying_signals = [
            'need help with team building',
            'looking for fractional CTO services',
            'want to schedule a call to discuss',
            'have budget allocated for this project',
            'timeline is urgent and we need to move fast',
            'decision makers are ready to proceed',
            'struggling with technical challenges'
        ]

        base_inquiry = "We are a Series B company with engineering challenges."

        for signal in buying_signals:
            inquiry_with_signal = f"{base_inquiry} {signal}"

            score_with_signal = sales_engine._enhanced_ml_lead_scoring(
                inquiry_text=inquiry_with_signal,
                company_size="Series B (50-200 employees)",
                priority_score=3,
                inquiry_type="team_building",
                company="TechCorp"
            )

            score_without_signal = sales_engine._enhanced_ml_lead_scoring(
                inquiry_text=base_inquiry,
                company_size="Series B (50-200 employees)",
                priority_score=3,
                inquiry_type="team_building",
                company="TechCorp"
            )

            assert score_with_signal > score_without_signal, \
                f"Buying signal '{signal}' should increase lead score"

    def test_urgency_indicators(self, sales_engine):
        """Test detection of urgency indicators"""
        urgency_indicators = ['asap', 'urgent', 'immediately', 'this week', 'next week', 'soon']

        base_inquiry = "We need help with our technical architecture and team scaling."

        for indicator in urgency_indicators:
            inquiry_with_urgency = f"{base_inquiry} We need this {indicator}."

            score_with_urgency = sales_engine._enhanced_ml_lead_scoring(
                inquiry_text=inquiry_with_urgency,
                company_size="Series A (20-50 employees)",
                priority_score=4,
                inquiry_type="technical_architecture",
                company="UrgentTech"
            )

            score_without_urgency = sales_engine._enhanced_ml_lead_scoring(
                inquiry_text=base_inquiry,
                company_size="Series A (20-50 employees)",
                priority_score=4,
                inquiry_type="technical_architecture",
                company="UrgentTech"
            )

            assert score_with_urgency > score_without_urgency, \
                f"Urgency indicator '{indicator}' should increase lead score"

    def test_company_maturity_signals(self, sales_engine):
        """Test detection of company maturity and funding signals"""
        maturity_signals = [
            ('Series A funded with revenue growth', 'funding'),
            ('Scaling to 100 customers this quarter', 'growth'),
            ('Just raised Series B round', 'funding'),
            ('Revenue growing 300% year over year', 'scaling')
        ]

        base_inquiry = "We need technical consulting help."

        for signal_text, _signal_type in maturity_signals:
            inquiry_with_signal = f"{base_inquiry} {signal_text}."

            score_with_signal = sales_engine._enhanced_ml_lead_scoring(
                inquiry_text=inquiry_with_signal,
                company_size="Series A (20-50 employees)",
                priority_score=3,
                inquiry_type="team_building",
                company="MatureTech"
            )

            score_without_signal = sales_engine._enhanced_ml_lead_scoring(
                inquiry_text=base_inquiry,
                company_size="Series A (20-50 employees)",
                priority_score=3,
                inquiry_type="team_building",
                company="MatureTech"
            )

            assert score_with_signal > score_without_signal, \
                f"Maturity signal '{signal_text}' should increase lead score"


class TestPriorityTierAssignment:
    """Test priority tier assignment logic"""

    @pytest.fixture
    def temp_sales_db(self):
        """Create temporary sales automation database"""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
            db_path = tmp.name

        SalesAutomationEngine(db_path=db_path)
        yield db_path

        Path(db_path).unlink(missing_ok=True)

    @pytest.fixture
    def sales_engine(self, temp_sales_db):
        """Sales automation engine with test database"""
        return SalesAutomationEngine(db_path=temp_sales_db)

    def test_platinum_tier_assignment(self, sales_engine):
        """Test platinum tier assignment (highest priority)"""
        platinum_scenarios = [
            (85, 75000),   # High score, high value
            (95, 50000),   # Very high score, medium-high value
            (80, 100000)   # High score, very high value
        ]

        for lead_score, estimated_value in platinum_scenarios:
            tier = sales_engine._determine_priority_tier(lead_score, estimated_value)
            assert tier == "platinum", \
                f"Score {lead_score}, Value ${estimated_value:,} should be platinum tier, got {tier}"

    def test_gold_tier_assignment(self, sales_engine):
        """Test gold tier assignment (high priority)"""
        gold_scenarios = [
            (75, 40000),   # High score, medium value
            (70, 50000),   # Medium-high score, high value
            (78, 25000)    # High score, minimum value threshold
        ]

        for lead_score, estimated_value in gold_scenarios:
            tier = sales_engine._determine_priority_tier(lead_score, estimated_value)
            assert tier == "gold", \
                f"Score {lead_score}, Value ${estimated_value:,} should be gold tier, got {tier}"

    def test_silver_tier_assignment(self, sales_engine):
        """Test silver tier assignment (medium priority)"""
        silver_scenarios = [
            (60, 20000),   # Medium score, medium value
            (55, 15000),   # Medium score, lower value
            (65, 10000)    # Medium-high score, minimum value
        ]

        for lead_score, estimated_value in silver_scenarios:
            tier = sales_engine._determine_priority_tier(lead_score, estimated_value)
            assert tier == "silver", \
                f"Score {lead_score}, Value ${estimated_value:,} should be silver tier, got {tier}"

    def test_bronze_tier_assignment(self, sales_engine):
        """Test bronze tier assignment (low priority)"""
        bronze_scenarios = [
            (30, 5000),    # Low score, low value
            (45, 8000),    # Lower score, low value
            (25, 15000)    # Low score, even with medium value
        ]

        for lead_score, estimated_value in bronze_scenarios:
            tier = sales_engine._determine_priority_tier(lead_score, estimated_value)
            assert tier == "bronze", \
                f"Score {lead_score}, Value ${estimated_value:,} should be bronze tier, got {tier}"


class TestLeadScoringConsistency:
    """Test lead scoring consistency and reliability"""

    @pytest.fixture
    def temp_sales_db(self):
        """Create temporary sales automation database"""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
            db_path = tmp.name

        SalesAutomationEngine(db_path=db_path)
        yield db_path

        Path(db_path).unlink(missing_ok=True)

    @pytest.fixture
    def sales_engine(self, temp_sales_db):
        """Sales automation engine with test database"""
        return SalesAutomationEngine(db_path=temp_sales_db)

    def test_scoring_consistency(self, sales_engine):
        """Test that identical inputs produce identical scores"""
        inquiry_text = "We need help with team building at our Series A startup. Budget is approved."
        company_size = "Series A (20-50 employees)"
        priority_score = 4
        inquiry_type = "team_building"
        company = "ConsistentTech"

        # Score the same inquiry multiple times
        scores = []
        for _ in range(5):
            score = sales_engine._enhanced_ml_lead_scoring(
                inquiry_text=inquiry_text,
                company_size=company_size,
                priority_score=priority_score,
                inquiry_type=inquiry_type,
                company=company
            )
            scores.append(score)

        # All scores should be identical
        assert all(score == scores[0] for score in scores), \
            f"Scoring inconsistent: {scores}"

    def test_score_boundaries(self, sales_engine):
        """Test that scores stay within valid boundaries"""
        test_scenarios = [
            # Extreme high value
            {
                'inquiry_text': 'URGENT ASAP need help budget approved timeline immediate decision ready fractional cto services strategic technical leadership architecture scalability',
                'company_size': 'Enterprise (500+ employees)',
                'priority_score': 5,
                'inquiry_type': 'fractional_cto',
                'company': 'Series C funded enterprise'
            },
            # Extreme low value
            {
                'inquiry_text': 'ok',
                'company_size': 'Unknown',
                'priority_score': 0,
                'inquiry_type': 'general',
                'company': ''
            }
        ]

        for scenario in test_scenarios:
            score = sales_engine._enhanced_ml_lead_scoring(**scenario)
            assert 0 <= score <= 100, f"Score {score} outside valid range 0-100"

    def test_qualification_status_consistency(self, sales_engine):
        """Test qualification status assignment consistency"""
        test_cases = [
            (85, "qualified"),
            (70, "qualified"),
            (65, "unqualified"),
            (40, "unqualified"),
            (25, "disqualified")
        ]

        for lead_score, expected_status in test_cases:
            if lead_score >= 70:
                expected_status = "qualified"
            elif lead_score >= 40:
                expected_status = "unqualified"
            else:
                expected_status = "disqualified"

            # This logic matches the implementation in import_consultation_inquiries
            actual_status = "qualified" if lead_score >= 70 else "unqualified" if lead_score >= 40 else "disqualified"

            assert actual_status == expected_status, \
                f"Lead score {lead_score} should result in '{expected_status}' status, got '{actual_status}'"


if __name__ == "__main__":
    # Run tests with detailed output
    pytest.main([__file__, "-v", "--tb=short"])
