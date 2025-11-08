"""
Business Development Test Configuration and Fixtures
Provides shared test fixtures for business development components
"""

import sys
import tempfile
from datetime import datetime
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

# Add the project root to Python path to import business_development
project_root = Path(__file__).parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from business_development.consultation_inquiry_detector import (
    ConsultationInquiryDetector,
    InquiryPattern,
)
from business_development.linkedin_posting_system import (
    LinkedInBusinessDevelopmentEngine,
)

# ============================================================================
# TEST DATABASE FIXTURES
# ============================================================================

@pytest.fixture
def temp_business_db():
    """Create temporary business development database for testing"""
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
        db_path = tmp.name

    # Initialize the database with proper schema
    engine = LinkedInBusinessDevelopmentEngine(db_path=db_path)
    yield db_path

    # Cleanup
    Path(db_path).unlink(missing_ok=True)


@pytest.fixture
def mock_business_database():
    """Mock business database with sample data"""
    db_data = {
        'linkedin_posts': [
            {
                'post_id': 'test-post-1',
                'content': 'Test post about team building and 10x performance',
                'posted_at': '2025-01-20T07:00:00',
                'week_theme': 'Team Building and Culture',
                'day': 'Monday',
                'target_audience': 'Startup founders, CTOs',
                'business_objective': 'Generate team building consultation inquiries',
                'expected_engagement_rate': 0.08,
                'expected_consultation_inquiries': 2,
                'impressions': 1500,
                'likes': 120,
                'comments': 8,
                'consultation_requests': 3,
                'actual_engagement_rate': 0.085
            },
            {
                'post_id': 'test-post-2',
                'content': 'Post about fractional CTO services and technical leadership',
                'posted_at': '2025-01-21T06:30:00',
                'week_theme': 'Technical Leadership',
                'day': 'Tuesday',
                'target_audience': 'Series A startups',
                'business_objective': 'Generate fractional CTO inquiries',
                'expected_engagement_rate': 0.09,
                'expected_consultation_inquiries': 1,
                'impressions': 2000,
                'likes': 180,
                'comments': 12,
                'consultation_requests': 2,
                'actual_engagement_rate': 0.096
            }
        ],
        'consultation_inquiries': [
            {
                'inquiry_id': 'test-inquiry-1',
                'source_post_id': 'test-post-1',
                'contact_name': 'John Smith',
                'company': 'TechStartup Inc',
                'company_size': 'Series A (20-50 employees)',
                'inquiry_type': 'team_building',
                'inquiry_channel': 'linkedin_comment',
                'inquiry_text': 'Great post! We are struggling with team velocity at our 25-person startup. Would love to discuss your approach.',
                'estimated_value': 25000,
                'priority_score': 4,
                'status': 'new',
                'created_at': '2025-01-20T08:15:00'
            },
            {
                'inquiry_id': 'test-inquiry-2',
                'source_post_id': 'test-post-2',
                'contact_name': 'Sarah Johnson',
                'company': 'InnovaCorp',
                'company_size': 'Series B (50-200 employees)',
                'inquiry_type': 'fractional_cto',
                'inquiry_channel': 'linkedin_dm',
                'inquiry_text': 'Hi! We need a part-time CTO to help with our technical strategy and scaling. Are you available for fractional work?',
                'estimated_value': 75000,
                'priority_score': 5,
                'status': 'new',
                'created_at': '2025-01-21T09:30:00'
            },
            {
                'inquiry_id': 'test-inquiry-3',
                'source_post_id': 'test-post-1',
                'contact_name': 'Mike Chen',
                'company': 'DevTools Ltd',
                'company_size': 'Seed/Pre-Series A (5-20 employees)',
                'inquiry_type': 'nobuild_audit',
                'inquiry_channel': 'linkedin_comment',
                'inquiry_text': 'Interesting take on build vs buy. We have been building everything custom. Need help with technology audit.',
                'estimated_value': 20000,
                'priority_score': 3,
                'status': 'new',
                'created_at': '2025-01-20T14:45:00'
            }
        ]
    }
    return db_data


# ============================================================================
# CONSULTATION INQUIRY FIXTURES
# ============================================================================

@pytest.fixture
def sample_consultation_inquiries():
    """Sample consultation inquiry data for testing"""
    return [
        {
            'text': 'Great post! We are struggling with team velocity at our Series A startup. Our 15-person engineering team seems to be slowing down despite hiring more people. Would love to discuss your approach to team building.',
            'source_post_id': '2025-01-20-monday-10x-teams',
            'commenter_name': 'Sarah Johnson',
            'commenter_profile': 'CTO at TechStartup Inc, Series A company with 25 employees',
            'expected_type': 'team_building',
            'expected_priority': 5,  # Higher priority due to strong consultation indicators
            'expected_value': 25000
        },
        {
            'text': 'This resonates! We have been looking for a fractional CTO to help us implement better engineering processes and scale our architecture. Are you available for this type of work?',
            'source_post_id': '2025-01-21-tuesday-technical-leadership',
            'commenter_name': 'Mike Chen',
            'commenter_profile': 'Founder at InnovaCorp, Series B startup, 75 employees',
            'expected_type': 'fractional_cto',
            'expected_priority': 5,
            'expected_value': 75000
        },
        {
            'text': 'Interesting perspective on the #NOBUILD approach. Our startup has been building everything custom and burning through our engineering budget. Need help with a technology audit to make better build vs buy decisions.',
            'source_post_id': '2025-01-22-wednesday-nobuild',
            'commenter_name': 'Alex Rivera',
            'commenter_profile': 'VP Engineering at DevTools Ltd, early stage startup',
            'expected_type': 'nobuild_audit',
            'expected_priority': 5,  # Higher priority due to "Need help" strong indicator
            'expected_value': 20000
        },
        {
            'text': 'Love this post! Can you help with our hiring strategy? We are a seed stage company trying to scale from 8 to 25 engineers.',
            'source_post_id': '2025-01-23-thursday-hiring',
            'commenter_name': 'Lisa Park',
            'commenter_profile': 'Founder at CodeCraft, seed stage, 12 employees',
            'expected_type': 'hiring_strategy',
            'expected_priority': 5,  # Higher priority due to strong consultation indicators ("Can you help")
            'expected_value': 15000
        }
    ]


@pytest.fixture
def sample_linkedin_posts():
    """Sample LinkedIn post data for testing"""
    return [
        {
            'post_id': '2025-01-20-monday-10x-teams',
            'content': 'Building 10x engineering teams is not about hiring 10x engineers. It is about creating systems, culture, and processes that multiply individual contributions.',
            'posted_at': '2025-01-20T07:00:00',
            'week_theme': 'Team Building and Culture',
            'day': 'Monday',
            'target_audience': 'Startup founders, CTOs, engineering managers',
            'business_objective': 'Generate 2-3 team building consultation inquiries',
            'expected_engagement_rate': 0.08,
            'expected_consultation_inquiries': 2
        },
        {
            'post_id': '2025-01-21-tuesday-technical-leadership',
            'content': 'Fractional CTO services: Getting strategic technical leadership without the full-time commitment. Here is when it works best.',
            'posted_at': '2025-01-21T06:30:00',
            'week_theme': 'Technical Leadership',
            'day': 'Tuesday',
            'target_audience': 'Series A/B startups',
            'business_objective': 'Generate fractional CTO inquiries',
            'expected_engagement_rate': 0.09,
            'expected_consultation_inquiries': 1
        },
        {
            'post_id': '2025-01-22-wednesday-nobuild',
            'content': 'The #NOBUILD philosophy: Why building everything custom is usually the wrong choice. Smart technology decisions save 40-60% on engineering costs.',
            'posted_at': '2025-01-22T08:00:00',
            'week_theme': 'Technology Decisions',
            'day': 'Wednesday',
            'target_audience': 'Technical founders, CTOs',
            'business_objective': 'Generate technology audit inquiries',
            'expected_engagement_rate': 0.07,
            'expected_consultation_inquiries': 2
        }
    ]


# ============================================================================
# BUSINESS LOGIC FIXTURES
# ============================================================================

@pytest.fixture
def mock_inquiry_patterns():
    """Mock inquiry patterns for testing detection logic"""
    return [
        InquiryPattern(
            keywords=["team building", "team velocity", "team performance", "10x team"],
            inquiry_type="team_building",
            priority_boost=2,
            estimated_value_base=25000
        ),
        InquiryPattern(
            keywords=["fractional cto", "part time cto", "interim cto", "technical advisor"],
            inquiry_type="fractional_cto",
            priority_boost=5,
            estimated_value_base=75000
        ),
        InquiryPattern(
            keywords=["nobuild", "build vs buy", "technology audit", "engineering efficiency"],
            inquiry_type="nobuild_audit",
            priority_boost=3,
            estimated_value_base=20000
        ),
        InquiryPattern(
            keywords=["hiring", "recruitment", "team scaling", "hiring strategy"],
            inquiry_type="hiring_strategy",
            priority_boost=2,
            estimated_value_base=15000
        )
    ]


# ============================================================================
# BUSINESS COMPONENT FIXTURES
# ============================================================================

@pytest.fixture
def consultation_detector(temp_business_db, mock_inquiry_patterns):
    """Consultation inquiry detector with test database"""
    detector = ConsultationInquiryDetector()
    detector.business_engine.db_path = temp_business_db
    detector.inquiry_patterns = mock_inquiry_patterns
    return detector


@pytest.fixture
def linkedin_business_engine(temp_business_db):
    """LinkedIn business development engine with test database"""
    return LinkedInBusinessDevelopmentEngine(db_path=temp_business_db)


@pytest.fixture
def automation_dashboard(temp_business_db):
    """Automation dashboard with mocked dependencies"""
    # Import AutomationDashboard dynamically to avoid circular import issues
    from business_development.automation_dashboard import AutomationDashboard

    with patch('business_development.automation_dashboard.LinkedInAPIClient') as mock_api, \
         patch('business_development.automation_dashboard.ContentAutomationPipeline') as mock_pipeline, \
         patch('business_development.automation_dashboard.LinkedInContentGenerator') as mock_generator:

        # Configure mocks
        mock_api.return_value.api_available = True
        mock_pipeline.return_value.get_automation_status.return_value = {
            'automation_active': True,
            'scheduled_posts': 5,
            'next_post_time': '2025-01-22T06:30:00'
        }
        mock_generator.return_value.generate_content.return_value = Mock()

        dashboard = AutomationDashboard()
        dashboard.business_engine.db_path = temp_business_db
        return dashboard


# ============================================================================
# BUSINESS PERFORMANCE FIXTURES
# ============================================================================

@pytest.fixture
def business_metrics_sample():
    """Sample business metrics for testing calculations"""
    return {
        'total_posts': 7,
        'total_impressions': 15000,
        'total_engagement': 1200,
        'total_consultation_requests': 11,
        'total_profile_views': 450,
        'total_connection_requests': 25,
        'avg_engagement_rate': 0.08,
        'pipeline_value': 435000,
        'won_value': 50000,
        'discovery_calls': 4,
        'proposals_sent': 2,
        'contracts_won': 1
    }


@pytest.fixture
def high_priority_inquiries():
    """High priority consultation inquiries for testing urgent alerts"""
    return [
        {
            'inquiry_id': 'urgent-inquiry-1',
            'contact_name': 'Alex Johnson',
            'company': 'ScaleTech',
            'inquiry_type': 'fractional_cto',
            'priority_score': 5,
            'estimated_value': 75000,
            'created_at': '2025-01-19T10:00:00',  # 2+ days old
            'status': 'new'
        },
        {
            'inquiry_id': 'urgent-inquiry-2',
            'contact_name': 'Maria Garcia',
            'company': 'GrowthStartup',
            'inquiry_type': 'team_building',
            'priority_score': 4,
            'estimated_value': 30000,
            'created_at': '2025-01-20T15:30:00',  # 1+ day old
            'status': 'new'
        }
    ]


# ============================================================================
# MOCK EXTERNAL DEPENDENCIES
# ============================================================================

@pytest.fixture
def mock_linkedin_api():
    """Mock LinkedIn API client for testing"""
    mock_api = Mock()
    mock_api.api_available = True
    mock_api.post_content.return_value = {
        'success': True,
        'post_id': 'linkedin-12345',
        'scheduled_time': '2025-01-22T06:30:00'
    }
    mock_api.get_post_analytics.return_value = {
        'impressions': 1500,
        'likes': 120,
        'comments': 8,
        'shares': 3,
        'clicks': 45
    }
    return mock_api


@pytest.fixture
def mock_content_generator():
    """Mock content generator for testing"""
    mock_generator = Mock()
    mock_content = Mock()
    mock_content.full_post = "Test generated LinkedIn content about team building and 10x performance."
    mock_content.content_type.value = "team_building"
    mock_content.engagement_prediction = 0.085
    mock_content.generation_metadata = {
        'content_length': 150,
        'estimated_read_time': 0.5
    }
    mock_generator.generate_content.return_value = mock_content
    return mock_generator


# ============================================================================
# DATETIME FIXTURES
# ============================================================================

@pytest.fixture
def fixed_datetime():
    """Fixed datetime for consistent testing"""
    return datetime(2025, 1, 22, 10, 30, 0)


@pytest.fixture
def business_hours_datetime():
    """Business hours datetime for testing optimal posting times"""
    return datetime(2025, 1, 23, 6, 30, 0)  # Thursday 6:30 AM


# ============================================================================
# REVENUE CALCULATION FIXTURES
# ============================================================================

@pytest.fixture
def pipeline_value_scenarios():
    """Different pipeline value scenarios for testing business calculations"""
    return {
        'under_target': [
            {'estimated_value': 15000, 'status': 'new'},
            {'estimated_value': 20000, 'status': 'new'},
            {'estimated_value': 10000, 'status': 'contacted'}
        ],  # Total: $45K (below $50K target)
        'on_target': [
            {'estimated_value': 25000, 'status': 'new'},
            {'estimated_value': 30000, 'status': 'contacted'},
            {'estimated_value': 20000, 'status': 'discovery_scheduled'}
        ],  # Total: $75K (above target)
        'high_value': [
            {'estimated_value': 75000, 'status': 'new'},      # Fractional CTO
            {'estimated_value': 40000, 'status': 'contacted'}, # Architecture
            {'estimated_value': 25000, 'status': 'proposal_sent'}, # Team building
            {'estimated_value': 30000, 'status': 'new'},      # Efficiency audit
            {'estimated_value': 50000, 'status': 'closed_won'} # Won contract
        ]  # Total: $220K active + $50K won
    }
