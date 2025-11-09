"""
Comprehensive Tests for Automation Dashboard
Tests the central monitoring and control system for the $435K business pipeline
"""

import sqlite3
from unittest.mock import Mock, patch

import pytest
from freezegun import freeze_time

from business_development.automation_dashboard import AutomationDashboard


class TestAutomationDashboardInitialization:
    """Test automation dashboard initialization and dependency management"""

    @patch('business_development.automation_dashboard.LinkedInAPIClient')
    @patch('business_development.automation_dashboard.ContentAutomationPipeline')
    @patch('business_development.automation_dashboard.LinkedInContentGenerator')
    def test_dashboard_startup_happy_path(self, mock_generator, mock_pipeline, mock_api):
        """Test dashboard initializes without dependency errors"""
        # Arrange - Configure mocks to simulate successful initialization
        mock_api.return_value.api_available = True
        mock_pipeline.return_value.get_automation_status.return_value = {
            'automation_active': True,
            'scheduled_posts': 5,
            'next_post_time': '2025-01-22T06:30:00'
        }
        mock_generator.return_value = Mock()

        # Act
        dashboard = AutomationDashboard()

        # Assert
        assert dashboard.api_client.api_available, "LinkedIn API should be available"
        assert hasattr(dashboard, 'business_engine'), "Should initialize business engine"
        assert hasattr(dashboard, 'inquiry_detector'), "Should initialize inquiry detector"
        assert hasattr(dashboard, 'automation_pipeline'), "Should initialize automation pipeline"
        assert hasattr(dashboard, 'content_generator'), "Should initialize content generator"

    def test_dashboard_handles_dependency_failures_gracefully(self):
        """Test dashboard handles dependency initialization failures gracefully"""
        # This test ensures the dashboard doesn't break the entire system if external dependencies fail

        with patch('business_development.automation_dashboard.LinkedInAPIClient', side_effect=Exception("API init failed")):
            # Act & Assert - Should not raise exception
            try:
                AutomationDashboard()
                # If we get here, the exception was handled gracefully
                assert True, "Dashboard should handle dependency failures gracefully"
            except Exception as e:
                pytest.fail(f"Dashboard should not fail on dependency errors: {e}")


class TestComprehensiveStatusReporting:
    """Test comprehensive status reporting functionality"""

    def test_get_comprehensive_status_happy_path(self, automation_dashboard, mock_business_database):
        """Test comprehensive status retrieval with all systems operational"""
        # Ensure all components use the same test database
        automation_dashboard.inquiry_detector.business_engine.db_path = automation_dashboard.business_engine.db_path

        # Arrange - Set up test data in database
        conn = sqlite3.connect(automation_dashboard.business_engine.db_path)
        cursor = conn.cursor()

        # Clear existing data to ensure test isolation
        cursor.execute('DELETE FROM consultation_inquiries')
        cursor.execute('DELETE FROM linkedin_posts')
        conn.commit()

        # Insert test posts
        for post in mock_business_database['linkedin_posts']:
            cursor.execute('''
                INSERT INTO linkedin_posts
                (post_id, content, posted_at, week_theme, day, target_audience, business_objective,
                 expected_engagement_rate, expected_consultation_inquiries, impressions, likes, comments,
                 consultation_requests, actual_engagement_rate)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                post['post_id'], post['content'], post['posted_at'], post['week_theme'], post['day'],
                post['target_audience'], post['business_objective'], post['expected_engagement_rate'],
                post['expected_consultation_inquiries'], post['impressions'], post['likes'],
                post['comments'], post['consultation_requests'], post['actual_engagement_rate']
            ))

        # Insert test inquiries
        for inquiry in mock_business_database['consultation_inquiries']:
            cursor.execute('''
                INSERT INTO consultation_inquiries
                (inquiry_id, source_post_id, contact_name, company, company_size, inquiry_type,
                 inquiry_channel, inquiry_text, estimated_value, priority_score, status, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                inquiry['inquiry_id'], inquiry['source_post_id'], inquiry['contact_name'],
                inquiry['company'], inquiry['company_size'], inquiry['inquiry_type'],
                inquiry['inquiry_channel'], inquiry['inquiry_text'], inquiry['estimated_value'],
                inquiry['priority_score'], inquiry['status'], inquiry['created_at']
            ))

        conn.commit()
        conn.close()

        # Act
        status = automation_dashboard.get_comprehensive_status()

        # Assert - Verify status structure and data
        assert 'timestamp' in status, "Status should include timestamp"
        assert 'systems_status' in status, "Status should include systems status"
        assert 'business_metrics' in status, "Status should include business metrics"
        assert 'pending_inquiries' in status, "Status should include pending inquiries"
        assert 'content_pipeline' in status, "Status should include content pipeline"

        # Verify systems status
        systems = status['systems_status']
        assert systems['linkedin_api'] is True, "LinkedIn API should be active"
        assert systems['automation_pipeline'] is True, "Automation pipeline should be active"
        assert systems['inquiry_detection'] is True, "Inquiry detection should be active"
        assert systems['business_tracking'] is True, "Business tracking should be active"

        # Verify business metrics
        metrics = status['business_metrics']
        assert 'post_performance' in metrics, "Should include post performance"
        assert 'business_pipeline' in metrics, "Should include business pipeline"

        # Verify pending inquiries
        pending = status['pending_inquiries']
        assert pending['count'] == 3, "Should have 3 pending inquiries"
        expected_total_value = 25000 + 75000 + 20000  # Sum of test inquiry values
        assert pending['total_value'] == expected_total_value, f"Total value should be ${expected_total_value}"
        assert pending['high_priority'] == 2, "Should have 2 high priority inquiries (score >= 4)"

    def test_pipeline_value_calculation_happy_path(self, automation_dashboard, pipeline_value_scenarios):
        """Test accurate business pipeline value calculation"""
        # Test with high-value scenario
        high_value_inquiries = pipeline_value_scenarios['high_value']

        conn = sqlite3.connect(automation_dashboard.business_engine.db_path)
        cursor = conn.cursor()

        total_pipeline_value = 0

        for i, inquiry_data in enumerate(high_value_inquiries):
            cursor.execute('''
                INSERT INTO consultation_inquiries
                (inquiry_id, source_post_id, contact_name, company, inquiry_type,
                 estimated_value, status, created_at, company_size, inquiry_channel, inquiry_text, priority_score)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                f'pipeline-test-{i}', 'test-post', f'Contact {i}', f'Company {i}', 'team_building',
                inquiry_data['estimated_value'], inquiry_data['status'], '2025-01-22T10:00:00',
                'Series A', 'linkedin_comment', 'Test inquiry', 4
            ))
            total_pipeline_value += inquiry_data['estimated_value']

        conn.commit()
        conn.close()

        # Act
        status = automation_dashboard.get_comprehensive_status()

        # Assert
        pipeline = status['business_metrics']['business_pipeline']
        assert pipeline['total_pipeline_value'] == total_pipeline_value, f"Pipeline value should be ${total_pipeline_value}"

        # Verify won value is tracked separately
        won_value = sum(inq['estimated_value'] for inq in high_value_inquiries if inq['status'] == 'closed_won')
        assert pipeline['won_value'] == won_value, f"Won value should be ${won_value}"


class TestDailyReportGeneration:
    """Test daily business development report generation"""

    def test_generate_daily_report_happy_path(self, automation_dashboard, business_metrics_sample):
        """Test generation of comprehensive daily report"""
        # Arrange - Set up mock data for comprehensive report
        mock_status = {
            'timestamp': '2025-01-22T10:30:00',
            'systems_status': {
                'linkedin_api': True,
                'automation_pipeline': True,
                'inquiry_detection': True,
                'business_tracking': True
            },
            'business_metrics': {
                'post_performance': {
                    'total_posts': business_metrics_sample['total_posts'],
                    'avg_engagement_rate': business_metrics_sample['avg_engagement_rate'],
                    'total_consultation_requests': business_metrics_sample['total_consultation_requests']
                },
                'business_pipeline': {
                    'total_pipeline_value': business_metrics_sample['pipeline_value'],
                    'won_value': business_metrics_sample['won_value'],
                    'discovery_calls': business_metrics_sample['discovery_calls'],
                    'contracts_won': business_metrics_sample['contracts_won']
                }
            },
            'pending_inquiries': {
                'count': 11,
                'total_value': 435000,
                'high_priority': 6
            },
            'content_pipeline': {
                'total_posts': 7,
                'scheduled': 3,
                'posted_no_inquiries': 1,
                'posted_with_inquiries': 3
            },
            'recent_trends': [
                {'date': '2025-01-21', 'engagement_rate': 0.09, 'inquiries': 3},
                {'date': '2025-01-20', 'engagement_rate': 0.08, 'inquiries': 2},
                {'date': '2025-01-19', 'engagement_rate': 0.085, 'inquiries': 2}
            ],
            'posts_detail': []
        }

        with patch.object(automation_dashboard, 'get_comprehensive_status', return_value=mock_status):
            # Act
            report = automation_dashboard.generate_daily_report()

            # Assert
            assert "DAILY BUSINESS DEVELOPMENT REPORT" in report, "Should have report header"
            assert "SYSTEM STATUS" in report, "Should include system status"
            assert "KEY METRICS" in report, "Should include key metrics"
            assert "CONTENT PIPELINE" in report, "Should include content pipeline status"
            assert "PENDING BUSINESS DEVELOPMENT" in report, "Should include pending business dev"
            assert "ACTION ITEMS" in report, "Should include action items"

            # Verify key business metrics are included
            assert "Total Posts Published: 7" in report, "Should show total posts"
            assert "Pipeline Value: $435,000" in report, "Should show pipeline value"
            assert "Total Inquiries: 11" in report, "Should show inquiry count"
            assert "High Priority: 6" in report, "Should show high priority count"

            # Verify system health indicators
            assert "✅" in report, "Should show healthy systems with check marks"

    def test_business_metrics_display_happy_path(self, automation_dashboard):
        """Test real-time business metrics display matches actual business state"""
        # Ensure all components use the same test database
        automation_dashboard.inquiry_detector.business_engine.db_path = automation_dashboard.business_engine.db_path

        # Arrange - Create realistic business scenario matching current $435K pipeline
        conn = sqlite3.connect(automation_dashboard.business_engine.db_path)
        cursor = conn.cursor()

        # Clear existing data to ensure test isolation
        cursor.execute('DELETE FROM consultation_inquiries')
        cursor.execute('DELETE FROM linkedin_posts')
        conn.commit()

        # Create posts with realistic performance
        posts_data = [
            ('week3-monday', 'Monday', 1800, 0.085, 3),    # High-performing Monday post
            ('week3-tuesday', 'Tuesday', 2200, 0.092, 2),  # Optimal time Tuesday post
            ('week3-wednesday', 'Wednesday', 1600, 0.078, 2),
            ('week3-thursday', 'Thursday', 2100, 0.088, 1),  # Optimal time Thursday post
            ('week3-friday', 'Friday', 1400, 0.071, 1),
            ('week3-saturday', 'Saturday', 1200, 0.063, 1),
            ('week3-sunday', 'Sunday', 1300, 0.069, 1),
        ]

        for post_id, day, impressions, engagement_rate, consultation_requests in posts_data:
            cursor.execute('''
                INSERT INTO linkedin_posts
                (post_id, day, impressions, actual_engagement_rate, consultation_requests,
                 posted_at, content, business_objective)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (post_id, day, impressions, engagement_rate, consultation_requests,
                  '2025-01-22T07:00:00', f'{day} team building content',
                  'Generate consultation inquiries'))

        # Create realistic consultation inquiries totaling $435K
        inquiries_data = [
            ('high-value-cto-1', 75000, 5, 'fractional_cto'),
            ('high-value-cto-2', 75000, 5, 'fractional_cto'),
            ('architecture-1', 45000, 4, 'technical_architecture'),
            ('architecture-2', 40000, 4, 'technical_architecture'),
            ('team-building-1', 30000, 4, 'team_building'),
            ('team-building-2', 25000, 4, 'team_building'),
            ('team-building-3', 25000, 3, 'team_building'),
            ('nobuild-1', 25000, 3, 'nobuild_audit'),
            ('nobuild-2', 20000, 3, 'nobuild_audit'),
            ('hiring-1', 35000, 3, 'hiring_strategy'),
            ('hiring-2', 40000, 3, 'hiring_strategy')
        ]

        total_expected_value = 0
        high_priority_count = 0

        for inquiry_id, value, priority, inquiry_type in inquiries_data:
            cursor.execute('''
                INSERT INTO consultation_inquiries
                (inquiry_id, source_post_id, contact_name, company, inquiry_type,
                 estimated_value, priority_score, status, created_at, company_size,
                 inquiry_channel, inquiry_text)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (inquiry_id, 'week3-monday', f'Contact {inquiry_id}', f'Company {inquiry_id}',
                  inquiry_type, value, priority, 'new', '2025-01-22T10:00:00', 'Series A',
                  'linkedin_comment', f'{inquiry_type} consultation needed'))

            total_expected_value += value
            if priority >= 4:
                high_priority_count += 1

        conn.commit()
        conn.close()

        # Act
        status = automation_dashboard.get_comprehensive_status()

        # Assert - Verify metrics match current business reality
        pending = status['pending_inquiries']
        assert pending['count'] == 11, "Should have 11 pending inquiries"
        assert pending['total_value'] == total_expected_value, f"Total pipeline should be ${total_expected_value}"
        assert pending['total_value'] == 435000, "Should match actual $435K pipeline"
        assert pending['high_priority'] == high_priority_count, f"Should have {high_priority_count} high priority inquiries"

        # Verify post performance metrics
        post_perf = status['business_metrics']['post_performance']
        assert post_perf['total_posts'] == 7, "Should have 7 Week 3 posts"
        assert post_perf['total_consultation_requests'] == 11, "Should have 11 total consultation requests"


class TestCriticalAlertsMonitoring:
    """Test critical alerts and monitoring system"""

    @freeze_time("2025-01-22 10:30:00")
    def test_monitor_critical_alerts_happy_path(self, automation_dashboard, high_priority_inquiries):
        """Test detection of critical alerts requiring immediate attention"""
        # Ensure all components use the same test database
        automation_dashboard.inquiry_detector.business_engine.db_path = automation_dashboard.business_engine.db_path

        # Arrange - Create high priority inquiries that are overdue
        conn = sqlite3.connect(automation_dashboard.business_engine.db_path)
        cursor = conn.cursor()

        # Clear existing data to ensure test isolation
        cursor.execute('DELETE FROM consultation_inquiries')
        cursor.execute('DELETE FROM linkedin_posts')
        conn.commit()

        for inquiry in high_priority_inquiries:
            cursor.execute('''
                INSERT INTO consultation_inquiries
                (inquiry_id, source_post_id, contact_name, company, inquiry_type,
                 estimated_value, priority_score, status, created_at, company_size,
                 inquiry_channel, inquiry_text)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                inquiry['inquiry_id'], 'test-post', inquiry['contact_name'], inquiry['company'],
                inquiry['inquiry_type'], inquiry['estimated_value'], inquiry['priority_score'],
                inquiry['status'], inquiry['created_at'], 'Series A', 'linkedin_comment', 'Urgent help needed'
            ))

        conn.commit()
        conn.close()

        # Act
        alerts = automation_dashboard.monitor_critical_alerts()

        # Assert
        assert len(alerts) >= 2, "Should detect multiple critical alerts"

        # Verify specific alert content
        alert_text = ' '.join(alerts)
        assert "Alex Johnson" in alert_text, "Should alert about Alex Johnson's overdue inquiry"
        assert "Maria Garcia" in alert_text, "Should alert about Maria Garcia's overdue inquiry"
        assert "CRITICAL" in alert_text, "Should mark alerts as critical"
        assert "pending" in alert_text.lower(), "Should mention pending status"

    def test_engagement_rate_critical_threshold_detection(self, automation_dashboard):
        """Test detection of critically low engagement rates"""
        # Arrange - Create posts with critically low engagement
        conn = sqlite3.connect(automation_dashboard.business_engine.db_path)
        cursor = conn.cursor()

        # Clear existing data to ensure test isolation
        cursor.execute('DELETE FROM consultation_inquiries')
        cursor.execute('DELETE FROM linkedin_posts')
        conn.commit()

        # Create posts from last 3 days with low engagement (below 3% threshold)
        low_engagement_posts = [
            ('low-eng-1', '2025-01-20T07:00:00', 1000, 0.025),  # 2.5% engagement
            ('low-eng-2', '2025-01-21T07:00:00', 1500, 0.020),  # 2.0% engagement
            ('low-eng-3', '2025-01-22T07:00:00', 2000, 0.015),  # 1.5% engagement
        ]

        for post_id, posted_at, impressions, engagement_rate in low_engagement_posts:
            cursor.execute('''
                INSERT INTO linkedin_posts
                (post_id, posted_at, impressions, actual_engagement_rate, content, day)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (post_id, posted_at, impressions, engagement_rate, 'Test content', 'Monday'))

        conn.commit()
        conn.close()

        # Act
        alerts = automation_dashboard.monitor_critical_alerts()

        # Assert
        alert_text = ' '.join(alerts)
        assert "WARNING" in alert_text or "CRITICAL" in alert_text, "Should generate engagement alert"
        assert "engagement rate" in alert_text.lower(), "Should mention engagement rate"
        assert "low" in alert_text.lower(), "Should indicate low performance"

    def test_failed_post_publication_detection(self, automation_dashboard):
        """Test detection of posts that failed to publish"""
        # Arrange - Create posts that should have been published but have no impressions
        conn = sqlite3.connect(automation_dashboard.business_engine.db_path)
        cursor = conn.cursor()

        # Create posts from yesterday that should be published (impressions = 0 means failed)
        yesterday = '2025-01-21T07:00:00'
        failed_posts = [
            ('failed-post-1', yesterday, 'Monday'),
            ('failed-post-2', yesterday, 'Tuesday'),
        ]

        for post_id, posted_at, day in failed_posts:
            cursor.execute('''
                INSERT INTO linkedin_posts
                (post_id, posted_at, day, impressions, content, business_objective)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (post_id, posted_at, day, 0, 'Test content', 'Test objective'))

        conn.commit()
        conn.close()

        # Act
        alerts = automation_dashboard.monitor_critical_alerts()

        # Assert
        alert_text = ' '.join(alerts)
        assert "CRITICAL" in alert_text, "Should generate critical alert for failed posts"
        assert "failed to publish" in alert_text, "Should mention publication failure"
        assert "2 posts" in alert_text, "Should count failed posts correctly"


class TestActionItemGeneration:
    """Test automated action item generation and recommendations"""

    def test_generate_action_items_high_priority_inquiries(self, automation_dashboard):
        """Test action items for high priority pending inquiries"""
        # Arrange - Create mock status with high priority inquiries
        mock_status = {
            'pending_inquiries': {
                'count': 5,
                'high_priority': 3,
                'total_value': 200000
            },
            'business_metrics': {
                'post_performance': {
                    'avg_engagement_rate': 0.08,
                    'total_consultation_requests': 5
                },
                'business_pipeline': {
                    'total_pipeline_value': 200000
                }
            },
            'content_pipeline': {
                'scheduled': 2,
                'posted_no_inquiries': 1,
                'posted_with_inquiries': 4
            },
            'systems_status': {
                'linkedin_api': True
            },
            'recent_trends': [
                {'engagement_rate': 0.08},
                {'engagement_rate': 0.09},
                {'engagement_rate': 0.07}
            ]
        }

        # Act
        action_items = automation_dashboard._generate_action_items(mock_status)

        # Assert
        assert any("URGENT" in item and "high-priority" in item for item in action_items), \
               "Should generate urgent action for high priority inquiries"
        assert any("3 high-priority" in item for item in action_items), \
               "Should specify number of high priority inquiries"

    def test_generate_action_items_low_engagement(self, automation_dashboard):
        """Test action items for low engagement performance"""
        # Arrange
        mock_status = {
            'pending_inquiries': {'count': 0, 'high_priority': 0, 'total_value': 0},
            'business_metrics': {
                'post_performance': {
                    'avg_engagement_rate': 0.04,  # Below 6% target
                    'total_consultation_requests': 2
                },
                'business_pipeline': {'total_pipeline_value': 50000}
            },
            'content_pipeline': {
                'scheduled': 1,
                'posted_no_inquiries': 3,  # Multiple posts without inquiries
                'posted_with_inquiries': 1
            },
            'systems_status': {'linkedin_api': True},
            'recent_trends': [
                {'engagement_rate': 0.04},
                {'engagement_rate': 0.03},
                {'engagement_rate': 0.05}
            ]
        }

        # Act
        action_items = automation_dashboard._generate_action_items(mock_status)

        # Assert
        assert any("engagement below target" in item.lower() for item in action_items), \
               "Should identify low engagement issue"
        assert any("3 posts published without consultation inquiries" in item for item in action_items), \
               "Should identify posts without business results"

    def test_generate_action_items_pipeline_value_below_target(self, automation_dashboard):
        """Test action items for pipeline value below target"""
        # Arrange
        mock_status = {
            'pending_inquiries': {'count': 2, 'high_priority': 0, 'total_value': 30000},
            'business_metrics': {
                'post_performance': {
                    'avg_engagement_rate': 0.08,
                    'total_consultation_requests': 2
                },
                'business_pipeline': {
                    'total_pipeline_value': 30000  # Below $50K target
                }
            },
            'content_pipeline': {
                'scheduled': 0,
                'posted_no_inquiries': 0,
                'posted_with_inquiries': 2
            },
            'systems_status': {'linkedin_api': True},
            'recent_trends': []
        }

        # Act
        action_items = automation_dashboard._generate_action_items(mock_status)

        # Assert
        assert any("Pipeline value $30,000 below $50K target" in item for item in action_items), \
               "Should identify pipeline value below target"
        assert any("consultation-focused content" in item for item in action_items), \
               "Should recommend increasing consultation-focused content"


class TestBusinessContinuityProtection:
    """Test that dashboard operations don't disrupt active business pipeline"""

    def test_dashboard_operations_dont_modify_business_data(self, automation_dashboard):
        """Test that dashboard operations are read-only and don't modify business data"""
        # Arrange - Create initial business data
        conn = sqlite3.connect(automation_dashboard.business_engine.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            INSERT INTO consultation_inquiries
            (inquiry_id, source_post_id, contact_name, company, inquiry_type,
             estimated_value, priority_score, status, created_at, company_size,
             inquiry_channel, inquiry_text)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', ('readonly-test', 'test-post', 'Test Contact', 'Test Company', 'team_building',
              25000, 4, 'new', '2025-01-22T10:00:00', 'Series A', 'linkedin_comment', 'Test inquiry'))

        conn.commit()

        # Capture initial state
        cursor.execute('SELECT status, estimated_value FROM consultation_inquiries WHERE inquiry_id = ?',
                      ('readonly-test',))
        initial_state = cursor.fetchone()
        conn.close()

        # Act - Perform various dashboard operations
        automation_dashboard.get_comprehensive_status()
        automation_dashboard.generate_daily_report()
        automation_dashboard.monitor_critical_alerts()

        # Assert - Verify data unchanged
        conn = sqlite3.connect(automation_dashboard.business_engine.db_path)
        cursor = conn.cursor()
        cursor.execute('SELECT status, estimated_value FROM consultation_inquiries WHERE inquiry_id = ?',
                      ('readonly-test',))
        final_state = cursor.fetchone()
        conn.close()

        assert initial_state == final_state, "Dashboard operations should not modify business data"
        assert final_state[0] == 'new', "Inquiry status should remain unchanged"
        assert final_state[1] == 25000, "Inquiry value should remain unchanged"

    def test_dashboard_database_isolation(self, temp_business_db):
        """Test that dashboard uses isolated test database"""
        # Arrange
        dashboard = AutomationDashboard()
        dashboard.business_engine.db_path = temp_business_db

        # Act & Assert
        assert dashboard.business_engine.db_path == temp_business_db, "Should use provided test database"
        assert "tmp" in temp_business_db, "Should be using temporary database file"

        # Verify operations work with test database
        status = dashboard.get_comprehensive_status()
        assert 'business_metrics' in status, "Should work with test database"

    def test_revenue_calculations_maintain_accuracy_during_testing(self, automation_dashboard):
        """Test that revenue calculations remain accurate during dashboard operations"""
        # Arrange - Create known revenue scenario
        conn = sqlite3.connect(automation_dashboard.business_engine.db_path)
        cursor = conn.cursor()

        # Known inquiries totaling exactly $200K
        known_inquiries = [
            ('revenue-test-1', 75000),   # Fractional CTO
            ('revenue-test-2', 50000),   # Architecture review
            ('revenue-test-3', 40000),   # Team building intensive
            ('revenue-test-4', 35000),   # Hiring strategy
        ]

        expected_total = sum(value for _, value in known_inquiries)

        for inquiry_id, value in known_inquiries:
            cursor.execute('''
                INSERT INTO consultation_inquiries
                (inquiry_id, source_post_id, contact_name, company, inquiry_type,
                 estimated_value, priority_score, status, created_at, company_size,
                 inquiry_channel, inquiry_text)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (inquiry_id, 'test-post', 'Test Contact', 'Test Company', 'team_building',
                  value, 4, 'new', '2025-01-22T10:00:00', 'Series A', 'linkedin_comment', 'Test'))

        conn.commit()
        conn.close()

        # Act - Perform multiple dashboard operations
        status_1 = automation_dashboard.get_comprehensive_status()
        report = automation_dashboard.generate_daily_report()
        automation_dashboard.monitor_critical_alerts()
        status_2 = automation_dashboard.get_comprehensive_status()

        # Assert - Verify calculations remain consistent and accurate
        pipeline_value_1 = status_1['business_metrics']['business_pipeline']['total_pipeline_value']
        pipeline_value_2 = status_2['business_metrics']['business_pipeline']['total_pipeline_value']

        assert pipeline_value_1 == expected_total, f"Initial calculation should be ${expected_total}"
        assert pipeline_value_2 == expected_total, f"Final calculation should be ${expected_total}"
        assert pipeline_value_1 == pipeline_value_2, "Revenue calculations should be consistent"
        assert pipeline_value_1 == 200000, "Should total exactly $200K as designed"

        # Verify report includes accurate values
        assert f"${expected_total:,}" in report, f"Report should show ${expected_total:,} pipeline value"


class TestSystemHealthMonitoring:
    """Test system health monitoring and diagnostics"""

    def test_system_health_check_all_systems_operational(self, automation_dashboard):
        """Test system health check when all systems are operational"""
        # Act
        with patch.object(automation_dashboard, '_check_database_health', return_value=True):
            automation_dashboard._display_system_health()

        # This test primarily verifies the method executes without error
        # In a real scenario, we'd capture output and verify system status display
        assert True, "System health check should complete without errors"

    def test_database_health_check_happy_path(self, automation_dashboard):
        """Test database health check with healthy database"""
        # Act
        is_healthy = automation_dashboard._check_database_health()

        # Assert
        assert is_healthy is True, "Database should be healthy"

    def test_database_health_check_handles_failures_gracefully(self, automation_dashboard):
        """Test database health check handles connection failures gracefully"""
        # Arrange - Simulate database connection failure
        with patch('sqlite3.connect', side_effect=Exception("Database connection failed")):
            # Act
            is_healthy = automation_dashboard._check_database_health()

            # Assert
            assert is_healthy is False, "Should return False for database connection failures"
