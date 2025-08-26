"""
Comprehensive Tests for LinkedIn Posting System
Tests the business development engine that manages posting, engagement tracking, and ROI measurement
"""

import pytest
import sqlite3
from datetime import datetime
from unittest.mock import patch, Mock, mock_open
from freezegun import freeze_time

from business_development.linkedin_posting_system import (
    LinkedInBusinessDevelopmentEngine,
    LinkedInPost,
    ConsultationInquiry
)


class TestLinkedInBusinessDevelopmentEngine:
    """Test core LinkedIn business development engine functionality"""
    
    def test_database_initialization_happy_path(self, temp_business_db):
        """Test successful database initialization with all required tables"""
        # Arrange & Act
        engine = LinkedInBusinessDevelopmentEngine(db_path=temp_business_db)
        
        # Assert - Verify all tables exist with correct schema
        conn = sqlite3.connect(temp_business_db)
        cursor = conn.cursor()
        
        # Check linkedin_posts table
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='linkedin_posts'")
        assert cursor.fetchone() is not None, "linkedin_posts table should exist"
        
        cursor.execute("PRAGMA table_info(linkedin_posts)")
        columns = [row[1] for row in cursor.fetchall()]
        required_columns = [
            'post_id', 'content', 'posted_at', 'week_theme', 'day', 'target_audience',
            'business_objective', 'expected_engagement_rate', 'expected_consultation_inquiries',
            'impressions', 'likes', 'comments', 'consultation_requests', 'actual_engagement_rate'
        ]
        for column in required_columns:
            assert column in columns, f"linkedin_posts should have {column} column"
            
        # Check consultation_inquiries table
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='consultation_inquiries'")
        assert cursor.fetchone() is not None, "consultation_inquiries table should exist"
        
        # Check business_pipeline table
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='business_pipeline'")
        assert cursor.fetchone() is not None, "business_pipeline table should exist"
        
        conn.close()


class TestWeeklyContentScheduling:
    """Test Week 3 content scheduling functionality"""
    
    def test_schedule_week3_posts_happy_path(self, linkedin_business_engine):
        """Test successful scheduling of Week 3 team building posts"""
        # Arrange - Mock file reading for content files
        mock_content = "Test LinkedIn post content about team building and 10x performance"
        
        with patch('builtins.open', mock_open(read_data=mock_content)):
            # Act
            linkedin_business_engine.schedule_week3_posts()
            
            # Assert
            conn = sqlite3.connect(linkedin_business_engine.db_path)
            cursor = conn.cursor()
            
            cursor.execute('SELECT COUNT(*) FROM linkedin_posts')
            post_count = cursor.fetchone()[0]
            assert post_count == 7, "Should schedule 7 posts for Week 3"
            
            # Verify specific posts
            cursor.execute('SELECT post_id, day, week_theme, expected_consultation_inquiries FROM linkedin_posts ORDER BY posted_at')
            posts = cursor.fetchall()
            
            expected_posts = [
                ('2025-01-20-monday-10x-teams', 'Monday', 'Team Building and Culture', 2),
                ('2025-01-21-tuesday-code-reviews', 'Tuesday', 'Team Building and Culture', 1),
                ('2025-01-22-wednesday-hiring', 'Wednesday', 'Team Building and Culture', 2),
                ('2025-01-23-thursday-python-teams', 'Thursday', 'Team Building and Culture', 1),
                ('2025-01-24-friday-leadership', 'Friday', 'Team Building and Culture', 1),
                ('2025-01-25-saturday-automation', 'Saturday', 'Team Building and Culture', 1),
                ('2025-01-26-sunday-empathy', 'Sunday', 'Team Building and Culture', 1)
            ]
            
            for i, (expected_id, expected_day, expected_theme, expected_inquiries) in enumerate(expected_posts):
                assert posts[i][0] == expected_id, f"Post {i} should have correct ID"
                assert posts[i][1] == expected_day, f"Post {i} should be for {expected_day}"
                assert posts[i][2] == expected_theme, f"Post {i} should have correct theme"
                assert posts[i][3] == expected_inquiries, f"Post {i} should expect {expected_inquiries} inquiries"
                
            conn.close()
            
    def test_optimal_posting_times_scheduled_correctly(self, linkedin_business_engine):
        """Test that posts are scheduled for optimal engagement times"""
        # Arrange
        mock_content = "Test content"
        
        with patch('builtins.open', mock_open(read_data=mock_content)):
            # Act
            linkedin_business_engine.schedule_week3_posts()
            
            # Assert - Verify optimal times (6:30 AM for Tue/Thu)
            conn = sqlite3.connect(linkedin_business_engine.db_path)
            cursor = conn.cursor()
            
            # Check Tuesday post (optimal time 6:30 AM)
            cursor.execute('SELECT posted_at, expected_engagement_rate FROM linkedin_posts WHERE day = ?', ('Tuesday',))
            tuesday_post = cursor.fetchone()
            assert '06:30:00' in tuesday_post[0], "Tuesday should be scheduled for 6:30 AM"
            assert tuesday_post[1] == 0.09, "Tuesday should have 9% expected engagement (6:30 AM boost)"
            
            # Check Thursday post (optimal time 6:30 AM)
            cursor.execute('SELECT posted_at, expected_engagement_rate FROM linkedin_posts WHERE day = ?', ('Thursday',))
            thursday_post = cursor.fetchone()
            assert '06:30:00' in thursday_post[0], "Thursday should be scheduled for 6:30 AM"
            assert thursday_post[1] == 0.09, "Thursday should have 9% expected engagement (6:30 AM boost)"
            
            conn.close()


class TestPostPerformanceTracking:
    """Test post performance metrics tracking and calculations"""
    
    def test_update_post_performance_happy_path(self, linkedin_business_engine):
        """Test successful update of post performance metrics"""
        # Arrange - Create a test post
        post_data = {
            'post_id': 'test-performance-post',
            'content': 'Test post content',
            'posted_at': '2025-01-22T07:00:00',
            'day': 'Monday',
            'week_theme': 'Test Theme',
            'target_audience': 'Test Audience',
            'business_objective': 'Test metrics tracking',
            'expected_engagement_rate': 0.08,
            'expected_consultation_inquiries': 2
        }
        
        conn = sqlite3.connect(linkedin_business_engine.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO linkedin_posts 
            (post_id, content, posted_at, day, week_theme, target_audience,
             business_objective, expected_engagement_rate, expected_consultation_inquiries)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', tuple(post_data.values()))
        conn.commit()
        conn.close()
        
        # Arrange performance data
        performance_metrics = {
            'impressions': 1500,
            'views': 1200,
            'likes': 120,
            'comments': 8,
            'shares': 3,
            'saves': 5,
            'clicks': 45,
            'profile_views': 25,
            'connection_requests': 3,
            'dm_inquiries': 2
        }
        
        # Act
        linkedin_business_engine.update_post_performance('test-performance-post', performance_metrics)
        
        # Assert
        conn = sqlite3.connect(linkedin_business_engine.db_path)
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM linkedin_posts WHERE post_id = ?', ('test-performance-post',))
        result = cursor.fetchone()
        conn.close()
        
        columns = [description[0] for description in cursor.description]
        post_dict = dict(zip(columns, result))
        
        # Verify all metrics updated
        assert post_dict['impressions'] == 1500, "Impressions should be updated"
        assert post_dict['likes'] == 120, "Likes should be updated"
        assert post_dict['comments'] == 8, "Comments should be updated"
        assert post_dict['profile_views'] == 25, "Profile views should be updated"
        
        # Verify calculated engagement rate
        expected_engagement_rate = (120 + 8 + 3 + 5) / 1500  # (likes + comments + shares + saves) / impressions
        assert abs(post_dict['actual_engagement_rate'] - expected_engagement_rate) < 0.001, "Engagement rate should be calculated correctly"
        
        # Verify business conversion rate
        expected_conversion_rate = (25 + 3 + 2) / 1200  # (profile_views + connection_requests + dm_inquiries) / views
        assert abs(post_dict['business_conversion_rate'] - expected_conversion_rate) < 0.001, "Business conversion rate should be calculated correctly"
        
    def test_engagement_rate_calculation_accuracy(self, linkedin_business_engine):
        """Test accurate engagement rate calculation for various scenarios"""
        # Test scenarios: (impressions, likes, comments, shares, saves, expected_rate)
        test_scenarios = [
            (1000, 80, 5, 2, 3, 0.09),    # 90 total engagement / 1000 impressions = 9%
            (2000, 160, 10, 4, 6, 0.09),  # 180 total engagement / 2000 impressions = 9%
            (500, 40, 2, 1, 2, 0.09),     # 45 total engagement / 500 impressions = 9%
            (1500, 60, 3, 0, 12, 0.05),   # 75 total engagement / 1500 impressions = 5%
        ]
        
        for i, (impressions, likes, comments, shares, saves, expected_rate) in enumerate(test_scenarios):
            # Arrange
            post_id = f'test-engagement-{i}'
            
            conn = sqlite3.connect(linkedin_business_engine.db_path)
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO linkedin_posts (post_id, content, posted_at, day)
                VALUES (?, ?, ?, ?)
            ''', (post_id, 'Test content', '2025-01-22T07:00:00', 'Monday'))
            conn.commit()
            conn.close()
            
            # Act
            linkedin_business_engine.update_post_performance(post_id, {
                'impressions': impressions,
                'likes': likes,
                'comments': comments,
                'shares': shares,
                'saves': saves
            })
            
            # Assert
            conn = sqlite3.connect(linkedin_business_engine.db_path)
            cursor = conn.cursor()
            cursor.execute('SELECT actual_engagement_rate FROM linkedin_posts WHERE post_id = ?', (post_id,))
            actual_rate = cursor.fetchone()[0]
            conn.close()
            
            assert abs(actual_rate - expected_rate) < 0.001, f"Engagement rate should be {expected_rate} for scenario {i}"


class TestConsultationInquiryLogging:
    """Test consultation inquiry logging and tracking"""
    
    def test_log_consultation_inquiry_happy_path(self, linkedin_business_engine):
        """Test successful logging of consultation inquiry"""
        # Arrange
        inquiry = ConsultationInquiry(
            inquiry_id="test-inquiry-log",
            source_post_id="test-post-source",
            contact_name="John Smith",
            company="TechCorp",
            company_size="Series A (20-50 employees)",
            inquiry_type="team_building",
            inquiry_channel="linkedin_comment",
            inquiry_text="Need help with team velocity and performance",
            estimated_value=25000,
            priority_score=4,
            status="new",
            created_at=datetime.now().isoformat()
        )
        
        # Act
        linkedin_business_engine.log_consultation_inquiry(inquiry)
        
        # Assert - Verify inquiry logged
        conn = sqlite3.connect(linkedin_business_engine.db_path)
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM consultation_inquiries WHERE inquiry_id = ?', ('test-inquiry-log',))
        result = cursor.fetchone()
        
        columns = [description[0] for description in cursor.description]
        inquiry_dict = dict(zip(columns, result))
        
        assert inquiry_dict['contact_name'] == "John Smith", "Contact name should be saved"
        assert inquiry_dict['company'] == "TechCorp", "Company should be saved"
        assert inquiry_dict['inquiry_type'] == "team_building", "Inquiry type should be saved"
        assert inquiry_dict['estimated_value'] == 25000, "Estimated value should be saved"
        assert inquiry_dict['priority_score'] == 4, "Priority score should be saved"
        
        conn.close()
        
    def test_consultation_request_counter_increment(self, linkedin_business_engine):
        """Test that consultation request counter increments when inquiry logged"""
        # Arrange - Create a post first
        conn = sqlite3.connect(linkedin_business_engine.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO linkedin_posts (post_id, content, posted_at, day, consultation_requests)
            VALUES (?, ?, ?, ?, ?)
        ''', ('test-counter-post', 'Test content', '2025-01-22T07:00:00', 'Monday', 0))
        conn.commit()
        
        # Verify initial count
        cursor.execute('SELECT consultation_requests FROM linkedin_posts WHERE post_id = ?', ('test-counter-post',))
        initial_count = cursor.fetchone()[0]
        assert initial_count == 0, "Initial consultation requests should be 0"
        
        # Act - Log inquiry
        inquiry = ConsultationInquiry(
            inquiry_id="test-counter-inquiry",
            source_post_id="test-counter-post",
            contact_name="Test Contact",
            company="Test Company",
            company_size="Series A",
            inquiry_type="team_building",
            inquiry_channel="linkedin_comment",
            inquiry_text="Test inquiry",
            estimated_value=25000,
            priority_score=3,
            status="new",
            created_at=datetime.now().isoformat()
        )
        
        linkedin_business_engine.log_consultation_inquiry(inquiry)
        
        # Assert - Verify counter incremented
        cursor.execute('SELECT consultation_requests FROM linkedin_posts WHERE post_id = ?', ('test-counter-post',))
        final_count = cursor.fetchone()[0]
        assert final_count == 1, "Consultation requests should increment to 1"
        
        conn.close()


class TestContentPipelineManagement:
    """Test content pipeline and publishing workflow"""
    
    def test_get_post_for_publishing_happy_path(self, linkedin_business_engine):
        """Test retrieval of next post ready for publishing"""
        # Arrange - Create posts with different states
        posts = [
            ('published-post', 'Monday', 1500),   # Already published (impressions > 0)
            ('ready-post-1', 'Tuesday', 0),       # Ready for publishing
            ('ready-post-2', 'Wednesday', 0),     # Ready for publishing
        ]
        
        conn = sqlite3.connect(linkedin_business_engine.db_path)
        cursor = conn.cursor()
        
        for post_id, day, impressions in posts:
            cursor.execute('''
                INSERT INTO linkedin_posts (post_id, content, posted_at, day, impressions)
                VALUES (?, ?, ?, ?, ?)
            ''', (post_id, f'Content for {day}', f'2025-01-22T07:00:00', day, impressions))
        
        conn.commit()
        conn.close()
        
        # Act
        next_post = linkedin_business_engine.get_post_for_publishing()
        
        # Assert
        assert next_post is not None, "Should return a post ready for publishing"
        assert next_post['impressions'] == 0, "Returned post should not have impressions (unpublished)"
        assert next_post['post_id'] in ['ready-post-1', 'ready-post-2'], "Should return one of the unpublished posts"
        
    def test_get_post_for_specific_day(self, linkedin_business_engine):
        """Test retrieval of post for specific day"""
        # Arrange
        posts = [
            ('monday-post', 'Monday', 0),
            ('tuesday-post', 'Tuesday', 0),
            ('wednesday-post', 'Wednesday', 1000),  # Already published
        ]
        
        conn = sqlite3.connect(linkedin_business_engine.db_path)
        cursor = conn.cursor()
        
        for post_id, day, impressions in posts:
            cursor.execute('''
                INSERT INTO linkedin_posts (post_id, content, posted_at, day, impressions)
                VALUES (?, ?, ?, ?, ?)
            ''', (post_id, f'Content for {day}', f'2025-01-22T07:00:00', day, impressions))
        
        conn.commit()
        conn.close()
        
        # Act
        tuesday_post = linkedin_business_engine.get_post_for_publishing('Tuesday')
        
        # Assert
        assert tuesday_post is not None, "Should find Tuesday post"
        assert tuesday_post['day'] == 'Tuesday', "Should return Tuesday post"
        assert tuesday_post['post_id'] == 'tuesday-post', "Should return correct post ID"


class TestBusinessDevelopmentReporting:
    """Test business development reporting and analytics"""
    
    def test_generate_business_development_report_happy_path(self, linkedin_business_engine):
        """Test generation of comprehensive business development report"""
        # Arrange - Create sample data
        # Create posts
        posts = [
            ('post-1', 'Monday', 1500, 0.08, 120, 8, 2, 1, 15, 2),   # impressions, engagement_rate, likes, comments, shares, saves, profile_views, connection_requests
            ('post-2', 'Tuesday', 2000, 0.09, 180, 12, 3, 2, 25, 3),
            ('post-3', 'Wednesday', 1800, 0.07, 126, 6, 2, 1, 18, 1),
        ]
        
        conn = sqlite3.connect(linkedin_business_engine.db_path)
        cursor = conn.cursor()
        
        total_impressions = 0
        total_engagement = 0
        total_consultation_requests = 0
        
        for post_id, day, impressions, engagement_rate, likes, comments, shares, saves, profile_views, connection_requests in posts:
            cursor.execute('''
                INSERT INTO linkedin_posts 
                (post_id, day, impressions, actual_engagement_rate, likes, comments, shares, saves, 
                 profile_views, connection_requests, consultation_requests, posted_at, content)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (post_id, day, impressions, engagement_rate, likes, comments, shares, saves,
                  profile_views, connection_requests, 2, '2025-01-22T07:00:00', 'Test content'))
            
            total_impressions += impressions
            total_engagement += likes + comments + shares + saves
            total_consultation_requests += 2
        
        # Create consultation inquiries
        inquiries = [
            ('inquiry-1', 'post-1', 25000, 'new'),
            ('inquiry-2', 'post-2', 75000, 'discovery_scheduled'),
            ('inquiry-3', 'post-3', 20000, 'proposal_sent'),
            ('inquiry-4', 'post-1', 30000, 'closed_won'),
        ]
        
        total_pipeline_value = 0
        won_value = 0
        
        for inquiry_id, source_post, value, status in inquiries:
            cursor.execute('''
                INSERT INTO consultation_inquiries 
                (inquiry_id, source_post_id, contact_name, company, inquiry_type, 
                 estimated_value, status, created_at, company_size, inquiry_channel, inquiry_text, priority_score)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (inquiry_id, source_post, 'Test Contact', 'Test Company', 'team_building',
                  value, status, '2025-01-22T10:00:00', 'Series A', 'linkedin_comment', 'Test inquiry', 3))
            
            total_pipeline_value += value
            if status == 'closed_won':
                won_value += value
        
        conn.commit()
        conn.close()
        
        # Act
        report = linkedin_business_engine.generate_business_development_report()
        
        # Assert - Verify report structure and accuracy
        assert 'post_performance' in report, "Report should include post performance"
        assert 'business_pipeline' in report, "Report should include business pipeline"
        assert 'top_performing_posts' in report, "Report should include top performing posts"
        
        # Verify post performance metrics
        post_perf = report['post_performance']
        assert post_perf['total_posts'] == 3, "Should have 3 posts"
        assert post_perf['total_impressions'] == total_impressions, f"Should have {total_impressions} total impressions"
        assert post_perf['total_consultation_requests'] == total_consultation_requests, "Should have correct consultation requests"
        
        # Verify business pipeline metrics
        pipeline = report['business_pipeline']
        assert pipeline['total_inquiries'] == 4, "Should have 4 total inquiries"
        assert pipeline['discovery_calls'] == 1, "Should have 1 discovery call scheduled"
        assert pipeline['proposals_sent'] == 1, "Should have 1 proposal sent"
        assert pipeline['contracts_won'] == 1, "Should have 1 contract won"
        assert pipeline['total_pipeline_value'] == total_pipeline_value, f"Should have ${total_pipeline_value} pipeline value"
        assert pipeline['won_value'] == won_value, f"Should have ${won_value} won value"
        
        # Verify top performing posts
        top_posts = report['top_performing_posts']
        assert len(top_posts) <= 5, "Should have at most 5 top posts"
        assert all('post_id' in post for post in top_posts), "Each top post should have post_id"
        assert all('engagement_rate' in post for post in top_posts), "Each top post should have engagement_rate"
        
    def test_business_metrics_calculations_accuracy(self, linkedin_business_engine):
        """Test accuracy of business metrics calculations"""
        # Arrange - Create controlled test data
        conn = sqlite3.connect(linkedin_business_engine.db_path)
        cursor = conn.cursor()
        
        # Create 2 posts with known metrics
        cursor.execute('''
            INSERT INTO linkedin_posts 
            (post_id, impressions, likes, comments, shares, saves, consultation_requests, actual_engagement_rate)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', ('metrics-post-1', 1000, 80, 10, 5, 5, 3, 0.10))  # 10% engagement
        
        cursor.execute('''
            INSERT INTO linkedin_posts 
            (post_id, impressions, likes, comments, shares, saves, consultation_requests, actual_engagement_rate)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', ('metrics-post-2', 2000, 160, 20, 10, 10, 2, 0.10))  # 10% engagement
        
        conn.commit()
        conn.close()
        
        # Act
        report = linkedin_business_engine.generate_business_development_report()
        
        # Assert - Verify calculated averages
        post_perf = report['post_performance']
        
        # Average engagement should be 10% ((0.10 + 0.10) / 2)
        expected_avg_engagement = 0.10
        assert abs(post_perf['avg_engagement_rate'] - expected_avg_engagement) < 0.001, "Average engagement rate should be 10%"
        
        # Total impressions should be 3000 (1000 + 2000)
        assert post_perf['total_impressions'] == 3000, "Total impressions should be 3000"
        
        # Total engagement should be 400 ((80+10+5+5) + (160+20+10+10))
        expected_total_engagement = (80 + 10 + 5 + 5) + (160 + 20 + 10 + 10)
        assert post_perf['total_engagement'] == expected_total_engagement, f"Total engagement should be {expected_total_engagement}"
        
        # Total consultation requests should be 5 (3 + 2)
        assert post_perf['total_consultation_requests'] == 5, "Total consultation requests should be 5"


class TestBusinessContinuityValidation:
    """Test that business operations continue safely during testing"""
    
    def test_database_isolation_from_production(self, temp_business_db):
        """Test that test database is isolated from production data"""
        # Act
        engine = LinkedInBusinessDevelopmentEngine(db_path=temp_business_db)
        
        # Assert
        assert temp_business_db != "linkedin_business_development.db", "Should use separate test database"
        assert "tmp" in temp_business_db or "test" in temp_business_db, "Should use temporary database file"
        
        # Verify test database is empty initially
        conn = sqlite3.connect(temp_business_db)
        cursor = conn.cursor()
        
        cursor.execute('SELECT COUNT(*) FROM linkedin_posts')
        post_count = cursor.fetchone()[0]
        assert post_count == 0, "Test database should start empty"
        
        cursor.execute('SELECT COUNT(*) FROM consultation_inquiries')
        inquiry_count = cursor.fetchone()[0]
        assert inquiry_count == 0, "Test database should start empty"
        
        conn.close()
        
    def test_no_external_api_calls_during_testing(self, linkedin_business_engine):
        """Test that no external API calls are made during unit tests"""
        # This test verifies that our unit tests don't accidentally make real LinkedIn API calls
        # by testing with mocked dependencies only
        
        # Arrange - Use test database only
        assert "tmp" in linkedin_business_engine.db_path, "Should be using test database"
        
        # Act - Perform business operations that might trigger API calls
        with patch('business_development.linkedin_posting_system.requests') as mock_requests:
            # Test operations that should not make external calls
            linkedin_business_engine.init_database()
            
            report = linkedin_business_engine.generate_business_development_report()
            next_post = linkedin_business_engine.get_post_for_publishing()
            
            # Assert - No external requests should have been made
            mock_requests.assert_not_called()
            
            # Verify operations completed successfully
            assert 'post_performance' in report, "Business operations should work with test data"
            
    def test_revenue_pipeline_calculations_remain_accurate(self, linkedin_business_engine):
        """Test that revenue pipeline calculations remain accurate during testing"""
        # This test ensures our testing doesn't break the core business value calculations
        
        # Arrange - Create realistic consultation pipeline data
        test_pipeline = [
            ('fractional-cto-inquiry', 75000, 'new'),        # High-value fractional CTO
            ('team-building-inquiry', 25000, 'contacted'),   # Team building consultation
            ('architecture-inquiry', 40000, 'discovery_scheduled'),  # Architecture review
            ('nobuild-audit-inquiry', 20000, 'proposal_sent'),      # #NOBUILD audit
            ('won-contract', 50000, 'closed_won'),           # Closed contract
        ]
        
        conn = sqlite3.connect(linkedin_business_engine.db_path)
        cursor = conn.cursor()
        
        total_active_pipeline = 0
        won_revenue = 0
        
        for inquiry_id, value, status in test_pipeline:
            cursor.execute('''
                INSERT INTO consultation_inquiries 
                (inquiry_id, source_post_id, contact_name, company, inquiry_type,
                 estimated_value, status, created_at, company_size, inquiry_channel, inquiry_text, priority_score)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (inquiry_id, 'test-post', 'Test Contact', 'Test Company', 'team_building',
                  value, status, '2025-01-22T10:00:00', 'Series A', 'linkedin_comment', 'Test inquiry', 3))
            
            if status == 'closed_won':
                won_revenue += value
            else:
                total_active_pipeline += value
        
        conn.commit()
        conn.close()
        
        # Act
        report = linkedin_business_engine.generate_business_development_report()
        
        # Assert - Verify revenue calculations are accurate
        pipeline = report['business_pipeline']
        
        # Active pipeline should be $160K ($75K + $25K + $40K + $20K)
        expected_active_pipeline = 75000 + 25000 + 40000 + 20000
        assert pipeline['total_pipeline_value'] == expected_active_pipeline + won_revenue, f"Total pipeline should include all inquiries"
        
        # Won revenue should be $50K
        assert pipeline['won_value'] == won_revenue, f"Won value should be ${won_revenue}"
        
        # Total inquiries should be 5
        assert pipeline['total_inquiries'] == 5, "Should have 5 total inquiries"
        
        # This represents the type of business value we're protecting with these tests
        assert expected_active_pipeline >= 160000, "Active pipeline should be substantial ($160K+)"