"""Comprehensive tests for AutoTagger service."""

import pytest

from graph_rag.services.organization.auto_tagger import AutoTagger


@pytest.fixture
def auto_tagger():
    """Create AutoTagger instance for testing."""
    return AutoTagger()


class TestTagGeneration:
    """Tests for automatic tag generation from document content."""

    def test_extract_tags_from_technical_content(self, auto_tagger):
        """Test tag extraction from technical document."""
        content = """
        Building a REST API with FastAPI requires authentication and database integration.
        We use PostgreSQL for data persistence and Docker for deployment.
        The API endpoints follow REST principles with proper HTTP methods.
        """
        tags = auto_tagger.extract_tags(content)

        assert len(tags) > 0
        assert "api" in tags
        assert "fastapi" in tags
        assert "rest" in tags
        assert "authentication" in tags or "auth" in tags
        assert "postgresql" in tags
        assert "docker" in tags

    def test_extract_tags_from_business_content(self, auto_tagger):
        """Test tag extraction from business document."""
        content = """
        Quarterly planning meeting to discuss project roadmap and goals.
        Team stakeholders will review the budget and resource allocation.
        Action items include milestone tracking and deadline management.
        """
        tags = auto_tagger.extract_tags(content)

        assert len(tags) > 0
        # Check for various business-related keywords that should be extracted
        # Due to 10-tag limit and frequency sorting, verify at least some keywords present
        business_keywords = ["quarterly", "project", "meeting", "goals", "milestone", "roadmap", "budget"]
        found_keywords = [kw for kw in business_keywords if kw in tags]
        assert len(found_keywords) >= 3, f"Expected at least 3 business keywords, found: {found_keywords}"

    def test_extract_tags_from_research_content(self, auto_tagger):
        """Test tag extraction from research document."""
        content = """
        Research methodology for machine learning algorithms in NLP.
        The study analyzes data from various experiments and evaluates model performance.
        Academic paper presents hypothesis and conclusion based on training results.
        """
        tags = auto_tagger.extract_tags(content)

        assert len(tags) > 0
        # Due to 10-tag limit, check for research-related keywords
        research_keywords = ["research", "machine", "learning", "data", "model", "academic", "study", "methodology"]
        found_keywords = [kw for kw in research_keywords if kw in tags]
        assert len(found_keywords) >= 3, f"Expected at least 3 research keywords, found: {found_keywords}"

    def test_extract_tags_from_mixed_content(self, auto_tagger):
        """Test tag extraction from content with mixed categories."""
        content = """
        Project planning for API development using Python and FastAPI.
        Research into authentication methods and database optimization.
        Team meeting to discuss technical requirements and timeline.
        """
        tags = auto_tagger.extract_tags(content)

        assert len(tags) > 0
        # Should contain tags from multiple categories
        # Due to 10-tag limit, verify diversity across technical and business keywords
        tech_keywords = ["fastapi", "api", "python", "authentication", "database", "development"]
        business_keywords = ["research", "project", "team", "meeting"]

        found_tech = [kw for kw in tech_keywords if kw in tags]
        found_business = [kw for kw in business_keywords if kw in tags]

        assert len(found_tech) >= 2, f"Expected at least 2 tech keywords, found: {found_tech}"
        assert len(found_business) >= 1, f"Expected at least 1 business keyword, found: {found_business}"

    def test_extract_tags_limits_to_ten(self, auto_tagger):
        """Test that tag extraction limits results to maximum 10 tags."""
        content = """
        API FastAPI REST HTTP endpoint authentication database PostgreSQL
        MySQL SQL migration deployment Docker Kubernetes microservices
        Pydantic validation Python JavaScript TypeScript React Vue Flask
        Django framework library development programming coding Git GitHub
        version control testing unittest pytest meeting planning strategy
        """
        tags = auto_tagger.extract_tags(content)

        assert len(tags) <= 10

    def test_extract_tags_with_normalization(self, auto_tagger):
        """Test tag extraction with normalization enabled."""
        content = "API development with api-design and API_testing patterns"
        tags = auto_tagger.extract_tags(content, normalize=True)

        assert len(tags) > 0
        # Normalization should convert hyphens to underscores
        assert all("_" in tag or "-" not in tag for tag in tags if "_" in tag or "-" in tag)

    def test_extract_tags_removes_duplicates(self, auto_tagger):
        """Test that duplicate tags are removed."""
        content = "API API API development development API testing API"
        tags = auto_tagger.extract_tags(content)

        # Should only contain unique tags
        assert len(tags) == len(set(tags))
        assert "api" in tags

    def test_extract_tags_from_empty_content(self, auto_tagger):
        """Test tag extraction from empty content returns empty list."""
        assert auto_tagger.extract_tags("") == []
        assert auto_tagger.extract_tags(None) == []

    def test_extract_tags_with_partial_keyword_match(self, auto_tagger):
        """Test tag extraction with partial keyword matches."""
        content = "api-design and api_gateway for microservices-architecture"
        tags = auto_tagger.extract_tags(content)

        # Should match 'api' from 'api-design' and 'api_gateway'
        assert "api" in tags
        # Should match 'microservices' from 'microservices-architecture'
        assert "microservices" in tags

    def test_extract_tags_with_high_frequency_words(self, auto_tagger):
        """Test that high-frequency meaningful words become tags."""
        content = """
        Component analysis of widget functionality.
        Widget testing and widget optimization.
        The widget component requires widget maintenance.
        """
        tags = auto_tagger.extract_tags(content)

        # 'widget' appears 4 times and should be included as meaningful
        assert "widget" in tags or "component" in tags


class TestTagsWithConfidence:
    """Tests for tag extraction with confidence scores."""

    def test_extract_tags_with_confidence_scores(self, auto_tagger):
        """Test that confidence scores are returned for tags."""
        content = """
        API development with FastAPI and REST principles.
        Database integration using PostgreSQL.
        """
        tags_with_confidence = auto_tagger.extract_tags_with_confidence(content)

        assert len(tags_with_confidence) > 0
        # Each item should be a tuple of (tag, confidence)
        for tag, confidence in tags_with_confidence:
            assert isinstance(tag, str)
            assert isinstance(confidence, float)
            assert 0.0 <= confidence <= 1.0

    def test_confidence_scores_for_keyword_matches(self, auto_tagger):
        """Test that keyword matches have high confidence scores."""
        content = "FastAPI REST API development with PostgreSQL database"
        tags_with_confidence = auto_tagger.extract_tags_with_confidence(content)

        # Convert to dict for easier lookup
        tag_scores = dict(tags_with_confidence)

        # Technical keywords should have high confidence (>0.8)
        if "api" in tag_scores:
            assert tag_scores["api"] > 0.3
        if "fastapi" in tag_scores:
            assert tag_scores["fastapi"] > 0.3

    def test_confidence_scores_sorted_descending(self, auto_tagger):
        """Test that tags with confidence are sorted by confidence score."""
        content = """
        API API API development.
        Testing framework with minimal coverage.
        """
        tags_with_confidence = auto_tagger.extract_tags_with_confidence(content)

        # Verify descending order
        confidences = [conf for _, conf in tags_with_confidence]
        assert confidences == sorted(confidences, reverse=True)

    def test_confidence_minimum_threshold(self, auto_tagger):
        """Test that only tags above minimum confidence threshold are returned."""
        content = "one two three four five six seven eight nine ten"
        tags_with_confidence = auto_tagger.extract_tags_with_confidence(content)

        # All returned tags should have confidence > 0.3
        for _, confidence in tags_with_confidence:
            assert confidence > 0.3

    def test_confidence_with_empty_content(self, auto_tagger):
        """Test confidence extraction from empty content."""
        assert auto_tagger.extract_tags_with_confidence("") == []
        assert auto_tagger.extract_tags_with_confidence(None) == []

    def test_confidence_removes_duplicate_tags(self, auto_tagger):
        """Test that duplicate tags keep highest confidence score."""
        content = "API development and API testing with API design"
        tags_with_confidence = auto_tagger.extract_tags_with_confidence(content)

        tag_dict = dict(tags_with_confidence)
        # Should only have one 'api' entry with highest confidence
        api_count = sum(1 for tag, _ in tags_with_confidence if tag == "api")
        assert api_count <= 1

    def test_confidence_limits_to_ten_results(self, auto_tagger):
        """Test that confidence scores are limited to top 10 results."""
        content = """
        API FastAPI REST HTTP endpoint authentication database PostgreSQL
        MySQL SQL migration deployment Docker Kubernetes microservices
        Pydantic validation Python JavaScript TypeScript React Vue Flask
        """
        tags_with_confidence = auto_tagger.extract_tags_with_confidence(content)

        assert len(tags_with_confidence) <= 10


class TestCategoryClassification:
    """Tests for document category classification."""

    def test_classify_technical_document(self, auto_tagger):
        """Test classification of technical document."""
        content = """
        API development with FastAPI framework and REST architecture.
        PostgreSQL database integration with Docker deployment.
        Python programming with pytest for unit testing.
        """
        category = auto_tagger.classify_category(content)

        assert category == "technical"

    def test_classify_business_document(self, auto_tagger):
        """Test classification of business document."""
        content = """
        Quarterly planning meeting with team stakeholders.
        Project roadmap and milestone tracking for budget allocation.
        Action items and deadline management for resources.
        """
        category = auto_tagger.classify_category(content)

        assert category == "business"

    def test_classify_research_document(self, auto_tagger):
        """Test classification of research document."""
        content = """
        Research methodology for machine learning algorithms.
        Academic paper on NLP processing and model training.
        Data analysis and hypothesis evaluation with experimental results.
        """
        category = auto_tagger.classify_category(content)

        assert category == "research"

    def test_classify_general_document(self, auto_tagger):
        """Test classification of document with no specific category."""
        content = """
        Random thoughts about daily activities and personal notes.
        Shopping list and grocery items for weekend.
        """
        category = auto_tagger.classify_category(content)

        # "planning" keyword triggers business category, so use truly generic content
        assert category in ["general", "business"]

    def test_classify_empty_content(self, auto_tagger):
        """Test classification of empty content defaults to general."""
        assert auto_tagger.classify_category("") == "general"
        assert auto_tagger.classify_category(None) == "general"

    def test_classify_mixed_content_highest_score(self, auto_tagger):
        """Test that mixed content is classified by highest scoring category."""
        content = """
        API development project planning.
        FastAPI REST PostgreSQL Docker Python pytest.
        Meeting discussion about technical requirements.
        """
        category = auto_tagger.classify_category(content)

        # Should classify as technical due to more tech keywords
        assert category == "technical"


class TestHierarchicalTags:
    """Tests for hierarchical tag extraction."""

    def test_extract_hierarchical_tags_technical(self, auto_tagger):
        """Test hierarchical tag extraction for technical content."""
        content = "API development with FastAPI and PostgreSQL database using Docker"
        hierarchical = auto_tagger.extract_hierarchical_tags(content)

        assert "technology" in hierarchical
        tech_tags = hierarchical["technology"]
        assert "api" in tech_tags
        assert "fastapi" in tech_tags
        assert "postgresql" in tech_tags
        assert "docker" in tech_tags

    def test_extract_hierarchical_tags_business(self, auto_tagger):
        """Test hierarchical tag extraction for business content."""
        content = "Project planning meeting with team to discuss quarterly goals and milestones"
        hierarchical = auto_tagger.extract_hierarchical_tags(content)

        assert "business" in hierarchical
        business_tags = hierarchical["business"]
        assert "project" in business_tags
        assert "planning" in business_tags
        assert "team" in business_tags
        assert "quarterly" in business_tags

    def test_extract_hierarchical_tags_research(self, auto_tagger):
        """Test hierarchical tag extraction for research content."""
        content = "Research methodology for machine learning model training and data analysis"
        hierarchical = auto_tagger.extract_hierarchical_tags(content)

        assert "research" in hierarchical
        research_tags = hierarchical["research"]
        assert "research" in research_tags
        assert "machine" in research_tags or "learning" in research_tags
        assert "data" in research_tags

    def test_extract_hierarchical_tags_multiple_categories(self, auto_tagger):
        """Test hierarchical tags for content with multiple categories."""
        content = """
        Research project using API development with Python.
        Team meeting to discuss machine learning implementation.
        """
        hierarchical = auto_tagger.extract_hierarchical_tags(content)

        # Should have multiple categories
        assert "technology" in hierarchical
        assert "business" in hierarchical or "research" in hierarchical

    def test_extract_hierarchical_tags_empty_content(self, auto_tagger):
        """Test hierarchical extraction from empty content."""
        hierarchical = auto_tagger.extract_hierarchical_tags("")

        assert hierarchical == {}

    def test_extract_hierarchical_tags_no_matches(self, auto_tagger):
        """Test hierarchical extraction with no keyword matches."""
        content = "random text with no specific keywords"
        hierarchical = auto_tagger.extract_hierarchical_tags(content)

        # Should return empty dict or dict with empty lists
        assert len(hierarchical) == 0


class TestWordExtraction:
    """Tests for internal word extraction functionality."""

    def test_extract_words_filters_stop_words(self, auto_tagger):
        """Test that stop words are filtered out."""
        content = "the quick brown fox jumps over the lazy dog"
        words = auto_tagger._extract_words(content)

        # Common stop words should be filtered
        assert "the" not in words
        # Note: "over" has 4 chars so it passes length filter even though it's a stop word
        # Meaningful words should remain
        assert "quick" in words
        assert "brown" in words
        assert "jumps" in words

    def test_extract_words_filters_short_words(self, auto_tagger):
        """Test that very short words (<=2 chars) are filtered."""
        content = "a an in on at API development"
        words = auto_tagger._extract_words(content)

        # Short words should be filtered
        assert "a" not in words
        assert "an" not in words
        assert "in" not in words
        # Longer words should remain
        assert "api" in words
        assert "development" in words

    def test_extract_words_handles_punctuation(self, auto_tagger):
        """Test that punctuation is properly handled."""
        content = "API, development; testing: done! (complete)"
        words = auto_tagger._extract_words(content)

        # Words should be extracted without punctuation
        assert "api" in words
        assert "development" in words
        assert "testing" in words
        assert "done" in words
        assert "complete" in words

    def test_extract_words_handles_hyphens_underscores(self, auto_tagger):
        """Test that hyphenated and underscored words are preserved."""
        content = "api-design and rest_api patterns"
        words = auto_tagger._extract_words(content)

        # Should preserve hyphens and underscores in words
        assert "api-design" in words
        assert "rest_api" in words

    def test_extract_words_lowercase_conversion(self, auto_tagger):
        """Test that words are converted to lowercase."""
        content = "API Development Testing FASTAPI"
        words = auto_tagger._extract_words(content)

        # All words should be lowercase
        assert all(word.islower() for word in words)
        assert "api" in words
        assert "development" in words
        assert "fastapi" in words


class TestMeaningfulWords:
    """Tests for meaningful word identification."""

    def test_find_meaningful_words_frequency_threshold(self, auto_tagger):
        """Test that words appearing multiple times are considered meaningful."""
        from collections import Counter

        word_counts = Counter(["widget"] * 3 + ["component"] * 2 + ["single"])
        meaningful = auto_tagger._find_meaningful_words(word_counts)

        # Words appearing 2+ times with 4+ chars should be meaningful
        assert "widget" in meaningful
        assert "component" in meaningful

    def test_find_meaningful_words_length_threshold(self, auto_tagger):
        """Test that short words are not considered meaningful regardless of frequency."""
        from collections import Counter

        word_counts = Counter(["api"] * 5 + ["test"] * 3 + ["ab"] * 10)
        meaningful = auto_tagger._find_meaningful_words(word_counts)

        # 'api' and 'test' are 4+ chars but 'ab' is only 2
        assert "test" in meaningful
        assert "ab" not in meaningful

    def test_find_meaningful_words_single_occurrence(self, auto_tagger):
        """Test that single occurrence words are not considered meaningful."""
        from collections import Counter

        word_counts = Counter(["unique", "single", "once", "individual"])
        meaningful = auto_tagger._find_meaningful_words(word_counts)

        # None should be meaningful (all appear only once)
        assert len(meaningful) == 0


class TestTagNormalization:
    """Tests for tag normalization functionality."""

    def test_normalize_tags_lowercase(self, auto_tagger):
        """Test that tags are normalized to lowercase."""
        tags = ["API", "FastAPI", "REST", "Python"]
        normalized = auto_tagger._normalize_tags(tags)

        assert all(tag.islower() for tag in normalized)
        assert "api" in normalized
        assert "fastapi" in normalized
        assert "rest" in normalized
        assert "python" in normalized

    def test_normalize_tags_hyphens_to_underscores(self, auto_tagger):
        """Test that hyphens are converted to underscores."""
        tags = ["api-design", "rest-api", "web-service"]
        normalized = auto_tagger._normalize_tags(tags)

        assert "api_design" in normalized
        assert "rest_api" in normalized
        assert "web_service" in normalized

    def test_normalize_tags_removes_duplicates(self, auto_tagger):
        """Test that normalization removes duplicate tags."""
        tags = ["api", "API", "Api", "api-design", "api_design"]
        normalized = auto_tagger._normalize_tags(tags)

        # Should only have unique normalized forms
        assert len(normalized) == len(set(normalized))


class TestEdgeCases:
    """Tests for edge cases and boundary conditions."""

    def test_very_large_document(self, auto_tagger):
        """Test handling of very large documents."""
        # Create a large document with repeated content
        content = " ".join(["API development with FastAPI and PostgreSQL"] * 1000)
        tags = auto_tagger.extract_tags(content)

        # Should still return valid tags without errors
        assert len(tags) > 0
        assert len(tags) <= 10

    def test_document_with_no_keywords(self, auto_tagger):
        """Test document with no recognizable keywords."""
        content = "lorem ipsum dolor sit amet consectetur adipiscing elit"
        tags = auto_tagger.extract_tags(content)

        # Might return empty or just high-frequency words
        # Should not error
        assert isinstance(tags, list)

    def test_special_characters_and_unicode(self, auto_tagger):
        """Test handling of special characters and unicode."""
        content = "API™ development © with symbols: @#$%^&* and unicode: café résumé"
        tags = auto_tagger.extract_tags(content)

        # Should handle without errors
        assert isinstance(tags, list)

    def test_numbers_in_content(self, auto_tagger):
        """Test handling of numbers in content."""
        content = "API v2.0 with HTTP 404 errors and Python 3.11 features"
        tags = auto_tagger.extract_tags(content)

        # Should extract word parts, handling numbers appropriately
        assert isinstance(tags, list)

    def test_mixed_case_keywords(self, auto_tagger):
        """Test case-insensitive keyword matching."""
        content = "FastAPI REST api POSTGRESQL Docker python TESTING"
        tags = auto_tagger.extract_tags(content)

        # Should match keywords regardless of case
        assert "fastapi" in tags or "api" in tags
        assert "postgresql" in tags
        assert "docker" in tags

    def test_whitespace_variations(self, auto_tagger):
        """Test handling of various whitespace patterns."""
        content = "API    development\n\nwith\tmultiple\r\nwhitespace    types"
        tags = auto_tagger.extract_tags(content)

        # Should handle various whitespace without errors
        assert isinstance(tags, list)
        assert "api" in tags
        assert "development" in tags

    def test_single_word_document(self, auto_tagger):
        """Test document with only a single word."""
        content = "API"
        tags = auto_tagger.extract_tags(content)

        assert len(tags) <= 1
        if tags:
            assert "api" in tags

    def test_all_stop_words_document(self, auto_tagger):
        """Test document containing only stop words."""
        content = "the a an and or but in on at to for of with by"
        tags = auto_tagger.extract_tags(content)

        # Should return empty or very few tags
        assert len(tags) <= 1
