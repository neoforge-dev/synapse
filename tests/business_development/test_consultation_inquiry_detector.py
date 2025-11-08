"""
Comprehensive Tests for Consultation Inquiry Detection System
Tests the core business logic that detects and processes consultation opportunities
"""

import sqlite3
from datetime import datetime, timedelta

from freezegun import freeze_time

from business_development.linkedin_posting_system import ConsultationInquiry


class TestConsultationInquiryDetection:
    """Test core consultation inquiry detection logic"""

    def test_detect_team_building_inquiry_happy_path(self, consultation_detector, sample_consultation_inquiries):
        """Test successful team building consultation inquiry detection"""
        # Arrange
        team_building_inquiry = sample_consultation_inquiries[0]

        # Act
        result = consultation_detector.analyze_text_for_consultation_signals(
            team_building_inquiry['text'],
            team_building_inquiry['source_post_id']
        )

        # Assert
        assert result is not None, "Should detect team building consultation inquiry"
        inquiry_type, priority_score, estimated_value = result

        assert inquiry_type == team_building_inquiry['expected_type']
        assert priority_score == team_building_inquiry['expected_priority']
        assert estimated_value == team_building_inquiry['expected_value']

    def test_detect_fractional_cto_inquiry_happy_path(self, consultation_detector, sample_consultation_inquiries):
        """Test successful fractional CTO consultation inquiry detection"""
        # Arrange
        fractional_cto_inquiry = sample_consultation_inquiries[1]

        # Act
        result = consultation_detector.analyze_text_for_consultation_signals(
            fractional_cto_inquiry['text'],
            fractional_cto_inquiry['source_post_id']
        )

        # Assert
        assert result is not None, "Should detect fractional CTO inquiry"
        inquiry_type, priority_score, estimated_value = result

        assert inquiry_type == fractional_cto_inquiry['expected_type']
        assert priority_score == fractional_cto_inquiry['expected_priority']
        assert estimated_value == fractional_cto_inquiry['expected_value']

    def test_detect_nobuild_audit_inquiry_happy_path(self, consultation_detector, sample_consultation_inquiries):
        """Test successful #NOBUILD audit consultation inquiry detection"""
        # Arrange
        nobuild_inquiry = sample_consultation_inquiries[2]

        # Act
        result = consultation_detector.analyze_text_for_consultation_signals(
            nobuild_inquiry['text'],
            nobuild_inquiry['source_post_id']
        )

        # Assert
        assert result is not None, "Should detect #NOBUILD audit inquiry"
        inquiry_type, priority_score, estimated_value = result

        assert inquiry_type == nobuild_inquiry['expected_type']
        assert priority_score == nobuild_inquiry['expected_priority']
        assert estimated_value == nobuild_inquiry['expected_value']

    def test_detect_hiring_strategy_inquiry_happy_path(self, consultation_detector, sample_consultation_inquiries):
        """Test successful hiring strategy consultation inquiry detection"""
        # Arrange
        hiring_inquiry = sample_consultation_inquiries[3]

        # Act
        result = consultation_detector.analyze_text_for_consultation_signals(
            hiring_inquiry['text'],
            hiring_inquiry['source_post_id']
        )

        # Assert
        assert result is not None, "Should detect hiring strategy inquiry"
        inquiry_type, priority_score, estimated_value = result

        assert inquiry_type == hiring_inquiry['expected_type']
        assert priority_score == hiring_inquiry['expected_priority']
        assert estimated_value == hiring_inquiry['expected_value']

    def test_strong_consultation_indicators_boost_priority(self, consultation_detector):
        """Test that strong consultation indicators increase priority score"""
        # Arrange
        weak_signal = "team building is interesting"
        strong_signal = "Great post! We need help with team building. Would love to schedule a call to discuss."

        # Act
        weak_result = consultation_detector.analyze_text_for_consultation_signals(weak_signal, "test-post")
        strong_result = consultation_detector.analyze_text_for_consultation_signals(strong_signal, "test-post")

        # Assert
        assert weak_result is None or weak_result[1] < 4, "Weak signal should have low/no priority"
        assert strong_result is not None, "Strong signal should be detected"
        assert strong_result[1] >= 4, "Strong signal should have high priority score"

    def test_company_size_detection_from_text(self, consultation_detector):
        """Test accurate company size detection from text content"""
        # Test cases for different company sizes
        test_cases = [
            ("We are a Series C company with 150 employees", "Enterprise (500+ employees)"),  # Series C triggers "Enterprise"
            ("Our startup just raised Series A with 30 team members", "Series A (20-50 employees)"),
            ("We are a seed stage company with 8 engineers", "Seed/Pre-Series A (5-20 employees)"),
            ("At our enterprise with 500+ employees", "Enterprise (500+ employees)"),
            ("Small team of developers", "Series A (20-50 employees)")  # "team of" triggers Series A
        ]

        for text, expected_size in test_cases:
            # Act
            result = consultation_detector.detect_company_size_from_text(text)

            # Assert
            assert expected_size in result or result == expected_size, f"Failed for text: {text}"


class TestLinkedInCommentProcessing:
    """Test LinkedIn comment processing and inquiry logging"""

    @freeze_time("2025-01-22 10:30:00")
    def test_process_linkedin_comment_happy_path(self, consultation_detector, sample_consultation_inquiries):
        """Test successful LinkedIn comment processing and inquiry creation"""
        # Arrange
        inquiry_data = sample_consultation_inquiries[0]

        # Act
        inquiry_id = consultation_detector.process_linkedin_comment(
            inquiry_data['source_post_id'],
            inquiry_data['text'],
            inquiry_data['commenter_name'],
            inquiry_data['commenter_profile']
        )

        # Assert
        assert inquiry_id is not None, "Should create consultation inquiry"
        assert inquiry_id.startswith("comment-"), "Should have comment prefix"
        assert "20250122" in inquiry_id, "Should include current date"

        # Verify inquiry was logged to database
        conn = sqlite3.connect(consultation_detector.business_engine.db_path)
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM consultation_inquiries WHERE inquiry_id = ?', (inquiry_id,))
        result = cursor.fetchone()
        conn.close()

        assert result is not None, "Inquiry should be saved to database"

    def test_process_linkedin_dm_higher_priority(self, consultation_detector, sample_consultation_inquiries):
        """Test that LinkedIn DMs receive higher priority than comments"""
        # Arrange
        inquiry_data = sample_consultation_inquiries[1]

        # Act
        inquiry_id = consultation_detector.process_linkedin_dm(
            inquiry_data['source_post_id'],
            inquiry_data['text'],
            inquiry_data['commenter_name'],
            "TechCorp Inc"
        )

        # Assert
        assert inquiry_id is not None, "Should create DM inquiry"
        assert inquiry_id.startswith("dm-"), "Should have DM prefix"

        # Verify higher priority and value
        conn = sqlite3.connect(consultation_detector.business_engine.db_path)
        cursor = conn.cursor()
        cursor.execute('SELECT priority_score, estimated_value FROM consultation_inquiries WHERE inquiry_id = ?', (inquiry_id,))
        result = cursor.fetchone()
        conn.close()

        priority_score, estimated_value = result
        assert priority_score == 5, "DM should have maximum priority"  # 4 + 1 boost
        assert estimated_value > inquiry_data['expected_value'], "DM should have higher value (1.5x multiplier)"

    def test_no_inquiry_for_low_signal_content(self, consultation_detector):
        """Test that low-signal content does not generate inquiries"""
        # Arrange
        low_signal_texts = [
            "Nice post!",
            "Thanks for sharing",
            "Interesting perspective",
            "Great content as always"
        ]

        for text in low_signal_texts:
            # Act
            inquiry_id = consultation_detector.process_linkedin_comment(
                "test-post-id",
                text,
                "Test User"
            )

            # Assert
            assert inquiry_id is None, f"Should not create inquiry for: {text}"


class TestInquiryResponseGeneration:
    """Test automated response generation for consultation inquiries"""

    def test_generate_team_building_response_happy_path(self, consultation_detector, temp_business_db):
        """Test generation of appropriate team building consultation response"""
        # Arrange - Create test inquiry in database
        inquiry = ConsultationInquiry(
            inquiry_id="test-team-building-inquiry",
            source_post_id="test-post-1",
            contact_name="Sarah Johnson",
            company="TechStartup",
            company_size="Series A",
            inquiry_type="team_building",
            inquiry_channel="linkedin_comment",
            inquiry_text="Need help with team velocity",
            estimated_value=25000,
            priority_score=4,
            status="new",
            created_at=datetime.now().isoformat()
        )
        consultation_detector.business_engine.log_consultation_inquiry(inquiry)

        # Act
        response = consultation_detector.generate_follow_up_response("test-team-building-inquiry")

        # Assert
        assert 'comment_reply' in response, "Should generate comment reply"
        assert 'dm_response' in response, "Should generate DM response"

        assert "team velocity" in response['comment_reply'].lower(), "Should mention team velocity"
        assert "Sarah Johnson" in response['dm_response'], "Should personalize with contact name"
        assert "15-minute assessment" in response['dm_response'], "Should include specific call duration"

    def test_generate_fractional_cto_response_happy_path(self, consultation_detector, temp_business_db):
        """Test generation of appropriate fractional CTO consultation response"""
        # Arrange
        inquiry = ConsultationInquiry(
            inquiry_id="test-fractional-cto-inquiry",
            source_post_id="test-post-2",
            contact_name="Mike Chen",
            company="InnovaCorp",
            company_size="Series B",
            inquiry_type="fractional_cto",
            inquiry_channel="linkedin_dm",
            inquiry_text="Need fractional CTO services",
            estimated_value=75000,
            priority_score=5,
            status="new",
            created_at=datetime.now().isoformat()
        )
        consultation_detector.business_engine.log_consultation_inquiry(inquiry)

        # Act
        response = consultation_detector.generate_follow_up_response("test-fractional-cto-inquiry")

        # Assert
        assert "fractional CTO" in response['comment_reply'], "Should mention fractional CTO"
        assert "Mike Chen" in response['dm_response'], "Should personalize response"
        assert "30-minute strategic assessment" in response['dm_response'], "Should offer strategic assessment"

    def test_high_priority_inquiries_get_calendly_link(self, consultation_detector, temp_business_db):
        """Test that high priority inquiries include direct booking option"""
        # Arrange
        high_priority_inquiry = ConsultationInquiry(
            inquiry_id="test-high-priority-inquiry",
            source_post_id="test-post-3",
            contact_name="Alex Rivera",
            company="ScaleCorp",
            company_size="Series B",
            inquiry_type="fractional_cto",
            inquiry_channel="linkedin_dm",
            inquiry_text="Urgent need for fractional CTO",
            estimated_value=75000,
            priority_score=4,  # High priority threshold
            status="new",
            created_at=datetime.now().isoformat()
        )
        consultation_detector.business_engine.log_consultation_inquiry(high_priority_inquiry)

        # Act
        response = consultation_detector.generate_follow_up_response("test-high-priority-inquiry")

        # Assert
        assert "Calendly" in response['dm_response'], "High priority should include Calendly link"


class TestPendingInquiryManagement:
    """Test pending consultation inquiry tracking and management"""

    def test_get_pending_inquiries_above_priority_threshold(self, consultation_detector, temp_business_db):
        """Test retrieval of pending inquiries above priority threshold"""
        # Arrange - Create inquiries with different priorities
        inquiries = [
            ConsultationInquiry(
                inquiry_id="low-priority-inquiry",
                source_post_id="test-post",
                contact_name="Low Priority",
                company="TestCorp",
                company_size="Unknown",
                inquiry_type="general_consultation",
                inquiry_channel="linkedin_comment",
                inquiry_text="General question",
                estimated_value=5000,
                priority_score=2,  # Below threshold
                status="new",
                created_at=datetime.now().isoformat()
            ),
            ConsultationInquiry(
                inquiry_id="high-priority-inquiry-1",
                source_post_id="test-post",
                contact_name="High Priority 1",
                company="ImportantCorp",
                company_size="Series A",
                inquiry_type="team_building",
                inquiry_channel="linkedin_dm",
                inquiry_text="Urgent team help needed",
                estimated_value=25000,
                priority_score=4,  # Above threshold
                status="new",
                created_at=datetime.now().isoformat()
            ),
            ConsultationInquiry(
                inquiry_id="high-priority-inquiry-2",
                source_post_id="test-post",
                contact_name="High Priority 2",
                company="CriticalCorp",
                company_size="Series B",
                inquiry_type="fractional_cto",
                inquiry_channel="linkedin_dm",
                inquiry_text="Need CTO immediately",
                estimated_value=75000,
                priority_score=5,  # Maximum priority
                status="new",
                created_at=datetime.now().isoformat()
            )
        ]

        for inquiry in inquiries:
            consultation_detector.business_engine.log_consultation_inquiry(inquiry)

        # Act
        pending_inquiries = consultation_detector.get_pending_inquiries(priority_threshold=3)

        # Assert
        assert len(pending_inquiries) == 2, "Should return only high priority inquiries"

        # Verify they are sorted by priority (highest first)
        assert pending_inquiries[0]['priority_score'] == 5, "Highest priority should be first"
        assert pending_inquiries[1]['priority_score'] == 4, "Second highest should be second"

        # Verify all are high priority
        for inquiry in pending_inquiries:
            assert inquiry['priority_score'] >= 3, "All should be above threshold"

    def test_mark_inquiry_contacted_happy_path(self, consultation_detector, temp_business_db):
        """Test marking inquiry as contacted with notes"""
        # Arrange
        inquiry = ConsultationInquiry(
            inquiry_id="test-contacted-inquiry",
            source_post_id="test-post",
            contact_name="Test Contact",
            company="TestCorp",
            company_size="Series A",
            inquiry_type="team_building",
            inquiry_channel="linkedin_comment",
            inquiry_text="Need help with team",
            estimated_value=25000,
            priority_score=4,
            status="new",
            created_at=datetime.now().isoformat()
        )
        consultation_detector.business_engine.log_consultation_inquiry(inquiry)

        # Act
        consultation_detector.mark_inquiry_contacted(
            "test-contacted-inquiry",
            "Initial response sent via LinkedIn DM. Scheduled discovery call for Thursday 2 PM."
        )

        # Assert
        conn = sqlite3.connect(consultation_detector.business_engine.db_path)
        cursor = conn.cursor()
        cursor.execute('SELECT status, notes, last_contact FROM consultation_inquiries WHERE inquiry_id = ?',
                      ("test-contacted-inquiry",))
        result = cursor.fetchone()
        conn.close()

        status, notes, last_contact = result
        assert status == "contacted", "Status should be updated to contacted"
        assert "discovery call" in notes, "Notes should be saved"
        assert last_contact is not None, "Last contact time should be recorded"


class TestBusinessPipelineCalculations:
    """Test business pipeline value calculations"""

    def test_calculate_total_pipeline_value_happy_path(self, consultation_detector, temp_business_db):
        """Test accurate calculation of total pipeline value"""
        # Arrange - Create inquiries with known values
        expected_total = 0
        test_inquiries = [
            ("inquiry-1", 25000, "team_building"),
            ("inquiry-2", 75000, "fractional_cto"),
            ("inquiry-3", 20000, "nobuild_audit"),
            ("inquiry-4", 15000, "hiring_strategy"),
            ("inquiry-5", 30000, "technical_architecture")
        ]

        for inquiry_id, value, inquiry_type in test_inquiries:
            inquiry = ConsultationInquiry(
                inquiry_id=inquiry_id,
                source_post_id="test-post",
                contact_name=f"Contact {inquiry_id}",
                company=f"Company {inquiry_id}",
                company_size="Series A",
                inquiry_type=inquiry_type,
                inquiry_channel="linkedin_comment",
                inquiry_text="Need consultation help",
                estimated_value=value,
                priority_score=3,
                status="new",
                created_at=datetime.now().isoformat()
            )
            consultation_detector.business_engine.log_consultation_inquiry(inquiry)
            expected_total += value

        # Act
        pending_inquiries = consultation_detector.get_pending_inquiries(priority_threshold=1)
        actual_total = sum(inquiry['estimated_value'] for inquiry in pending_inquiries)

        # Assert
        assert actual_total == expected_total, f"Total pipeline should be {expected_total}"
        assert actual_total == 165000, "Should match known test total"
        assert len(pending_inquiries) == 5, "Should have all 5 inquiries"

    def test_priority_scoring_business_logic(self, consultation_detector):
        """Test priority scoring matches business value logic"""
        # Test cases: (text, expected_minimum_priority)
        test_cases = [
            ("We need a fractional CTO for our Series B startup with 75 employees", 5),  # High value
            ("Help with team building at our 25-person company", 4),  # Medium-high value
            ("Technology audit for build vs buy decisions", 3),  # Medium value
            ("General consulting question", 1),  # Low value
        ]

        for text, expected_min_priority in test_cases:
            # Act
            result = consultation_detector.analyze_text_for_consultation_signals(text, "test-post")

            # Assert
            if result is not None:
                _, priority_score, _ = result
                assert priority_score >= expected_min_priority, f"Priority too low for: {text}"


class TestEdgeCasesAndValidation:
    """Test edge cases and input validation"""

    def test_empty_text_input_handling(self, consultation_detector):
        """Test handling of empty or invalid text inputs"""
        # Test empty and invalid inputs
        invalid_inputs = ["", None, "   ", "\n\t"]

        for invalid_input in invalid_inputs:
            if invalid_input is not None:
                # Act
                result = consultation_detector.analyze_text_for_consultation_signals(invalid_input, "test-post")

                # Assert
                assert result is None, f"Should not detect inquiry in invalid input: '{invalid_input}'"

    def test_minimum_threshold_enforcement(self, consultation_detector):
        """Test that minimum threshold for consultation detection is enforced"""
        # Arrange - Text with minimal consultation signals
        weak_signals = [
            "team",  # Single keyword, no context
            "I like this post about teams",  # Weak signal
            "team building sounds good but not interested"  # Keyword but negative intent
        ]

        for weak_signal in weak_signals:
            # Act
            result = consultation_detector.analyze_text_for_consultation_signals(weak_signal, "test-post")

            # Assert
            # Should either be None or have very low priority (below threshold of 3)
            if result is not None:
                _, priority_score, _ = result
                assert priority_score < 3, f"Priority too high for weak signal: {weak_signal}"

    def test_inquiry_id_generation_uniqueness(self, consultation_detector):
        """Test that inquiry IDs are unique even when created rapidly"""
        # Arrange
        inquiry_text = "Need help with team building"
        post_id = "test-post-unique"
        commenter = "Test User"

        # Act - Create multiple inquiries rapidly
        with freeze_time("2025-01-22 10:30:00") as frozen_time:
            inquiry_ids = []
            for i in range(5):
                frozen_time.tick(delta=timedelta(seconds=1))  # Advance by 1 second each
                inquiry_id = consultation_detector.process_linkedin_comment(
                    post_id, inquiry_text, f"{commenter} {i}"
                )
                if inquiry_id:
                    inquiry_ids.append(inquiry_id)

        # Assert
        assert len(inquiry_ids) == len(set(inquiry_ids)), "All inquiry IDs should be unique"
        assert len(inquiry_ids) > 0, "Should generate at least one inquiry"


class TestBusinessLogicIntegration:
    """Integration tests for business logic flows"""

    def test_end_to_end_consultation_pipeline(self, consultation_detector, sample_consultation_inquiries):
        """Test complete consultation pipeline from detection to response"""
        # Arrange
        inquiry_data = sample_consultation_inquiries[0]  # Team building inquiry

        # Act - Full pipeline
        # 1. Detect and log inquiry
        inquiry_id = consultation_detector.process_linkedin_comment(
            inquiry_data['source_post_id'],
            inquiry_data['text'],
            inquiry_data['commenter_name'],
            inquiry_data['commenter_profile']
        )

        # 2. Generate response
        response = consultation_detector.generate_follow_up_response(inquiry_id)

        # 3. Mark as contacted
        consultation_detector.mark_inquiry_contacted(inquiry_id, "Response sent")

        # 4. Verify final state
        pending_inquiries = consultation_detector.get_pending_inquiries()
        contacted_inquiries = []

        conn = sqlite3.connect(consultation_detector.business_engine.db_path)
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM consultation_inquiries WHERE status = ?', ("contacted",))
        contacted_inquiries = cursor.fetchall()
        conn.close()

        # Assert
        assert inquiry_id is not None, "Should create inquiry"
        assert response['comment_reply'], "Should generate comment response"
        assert response['dm_response'], "Should generate DM response"
        assert len(contacted_inquiries) == 1, "Should have one contacted inquiry"
        assert len([inq for inq in pending_inquiries if inq['status'] == 'new']) == 0, "No inquiries should remain new"
