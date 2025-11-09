"""Comprehensive tests for MetadataEnhancer service."""

from unittest.mock import Mock, patch

import pytest

from graph_rag.services.organization.metadata_enhancer import MetadataEnhancer


@pytest.fixture
def metadata_enhancer():
    """Create MetadataEnhancer instance for testing."""
    return MetadataEnhancer()


class TestMetadataEnhancement:
    """Tests for automatic metadata enhancement from document content."""

    def test_enhance_metadata_with_technical_content(self, metadata_enhancer):
        """Test metadata enhancement for technical document."""
        document_data = {
            "id": "doc-001",
            "title": "FastAPI REST API Guide",
            "content": """
            Building a REST API with FastAPI requires authentication and database integration.
            We use PostgreSQL for data persistence and Docker for deployment.
            The API endpoints follow REST principles with proper HTTP methods.
            """
        }

        enhanced = metadata_enhancer.enhance_metadata(document_data)

        # Original data should be preserved
        assert enhanced["id"] == "doc-001"
        assert enhanced["title"] == "FastAPI REST API Guide"
        assert "content" in enhanced

        # New metadata should be added
        assert "tags" in enhanced
        assert "category" in enhanced
        assert "topics" in enhanced
        assert "tag_confidence" in enhanced

        # Category should be technical
        assert enhanced["category"] == "technical"

        # Should contain relevant tags
        assert isinstance(enhanced["tags"], list)
        assert len(enhanced["tags"]) > 0
        assert "api" in enhanced["tags"]

        # Topics should be extracted
        assert isinstance(enhanced["topics"], list)
        assert len(enhanced["topics"]) > 0

        # Tag confidence should be a dict
        assert isinstance(enhanced["tag_confidence"], dict)

    def test_enhance_metadata_with_business_content(self, metadata_enhancer):
        """Test metadata enhancement for business document."""
        document_data = {
            "id": "doc-002",
            "title": "Quarterly Planning",
            "content": """
            Quarterly planning meeting to discuss project roadmap and goals.
            Team stakeholders will review the budget and resource allocation.
            Action items include milestone tracking and deadline management.
            """
        }

        enhanced = metadata_enhancer.enhance_metadata(document_data)

        assert enhanced["category"] == "business"
        assert "quarterly" in enhanced["tags"] or "planning" in enhanced["tags"]
        assert len(enhanced["topics"]) > 0

    def test_enhance_metadata_with_research_content(self, metadata_enhancer):
        """Test metadata enhancement for research document."""
        document_data = {
            "id": "doc-003",
            "title": "Machine Learning Research",
            "content": """
            Research methodology for machine learning algorithms in NLP.
            The study analyzes data from various experiments and evaluates model performance.
            Academic paper presents hypothesis and conclusion based on training results.
            """
        }

        enhanced = metadata_enhancer.enhance_metadata(document_data)

        assert enhanced["category"] == "research"
        assert "research" in enhanced["tags"] or "machine" in enhanced["tags"]
        assert len(enhanced["topics"]) > 0

    def test_enhance_metadata_preserves_existing_fields(self, metadata_enhancer):
        """Test that existing document fields are preserved."""
        document_data = {
            "id": "doc-004",
            "title": "Test Document",
            "content": "API development with FastAPI",
            "author": "John Doe",
            "created_at": "2024-01-01",
            "custom_field": "custom_value"
        }

        enhanced = metadata_enhancer.enhance_metadata(document_data)

        # Original fields should remain
        assert enhanced["id"] == "doc-004"
        assert enhanced["author"] == "John Doe"
        assert enhanced["created_at"] == "2024-01-01"
        assert enhanced["custom_field"] == "custom_value"

        # New metadata should be added
        assert "tags" in enhanced
        assert "category" in enhanced

    def test_enhance_metadata_with_title_only(self, metadata_enhancer):
        """Test metadata enhancement when only title is available."""
        document_data = {
            "id": "doc-005",
            "title": "FastAPI PostgreSQL Docker Deployment Guide",
            "content": ""
        }

        enhanced = metadata_enhancer.enhance_metadata(document_data)

        # Should extract tags from title even without content
        assert len(enhanced["tags"]) > 0
        assert enhanced["category"] == "technical"

    def test_enhance_metadata_with_content_only(self, metadata_enhancer):
        """Test metadata enhancement when only content is available."""
        document_data = {
            "id": "doc-006",
            "content": "Machine learning research with Python and TensorFlow"
        }

        enhanced = metadata_enhancer.enhance_metadata(document_data)

        # Should extract tags from content even without title
        assert len(enhanced["tags"]) > 0
        assert "category" in enhanced

    def test_enhance_metadata_combines_title_and_content(self, metadata_enhancer):
        """Test that both title and content are analyzed together."""
        document_data = {
            "id": "doc-007",
            "title": "FastAPI Tutorial",
            "content": "PostgreSQL database integration with Docker deployment"
        }

        enhanced = metadata_enhancer.enhance_metadata(document_data)

        # Should find tags from both title and content
        assert "fastapi" in enhanced["tags"] or "api" in enhanced["tags"]
        assert "postgresql" in enhanced["tags"]
        assert "docker" in enhanced["tags"]

    def test_enhance_metadata_with_empty_document(self, metadata_enhancer):
        """Test metadata enhancement with empty document."""
        document_data = {
            "id": "doc-008",
            "title": "",
            "content": ""
        }

        enhanced = metadata_enhancer.enhance_metadata(document_data)

        # Should return default values for empty content
        assert enhanced["tags"] == []
        assert enhanced["category"] == "general"
        assert enhanced["topics"] == []
        assert enhanced["tag_confidence"] == {}

    def test_enhance_metadata_with_no_content_field(self, metadata_enhancer):
        """Test metadata enhancement when content field is missing."""
        document_data = {
            "id": "doc-009",
            "title": ""
        }

        enhanced = metadata_enhancer.enhance_metadata(document_data)

        assert enhanced["tags"] == []
        assert enhanced["category"] == "general"

    def test_enhance_metadata_topics_unique(self, metadata_enhancer):
        """Test that duplicate topics are removed."""
        document_data = {
            "id": "doc-010",
            "title": "API API API",
            "content": "API development API testing API design"
        }

        enhanced = metadata_enhancer.enhance_metadata(document_data)

        # Topics should be unique (no duplicates)
        assert len(enhanced["topics"]) == len(set(enhanced["topics"]))

    def test_enhance_metadata_tag_confidence_scores(self, metadata_enhancer):
        """Test that tag confidence scores are valid."""
        document_data = {
            "id": "doc-011",
            "title": "FastAPI Development",
            "content": "REST API with PostgreSQL database"
        }

        enhanced = metadata_enhancer.enhance_metadata(document_data)

        # Each confidence score should be between 0 and 1
        for tag, confidence in enhanced["tag_confidence"].items():
            assert isinstance(tag, str)
            assert isinstance(confidence, float)
            assert 0.0 <= confidence <= 1.0


class TestSuggestOrganizationImprovements:
    """Tests for organization improvement suggestions."""

    def test_suggest_missing_title(self, metadata_enhancer):
        """Test suggestion when title is missing."""
        document_data = {
            "content": "Some document content about API development"
        }

        suggestions = metadata_enhancer.suggest_organization_improvements(document_data)

        assert len(suggestions) > 0
        assert any("title" in s.lower() for s in suggestions)

    def test_suggest_missing_title_empty_string(self, metadata_enhancer):
        """Test suggestion when title is empty string."""
        document_data = {
            "title": "",
            "content": "API development content"
        }

        suggestions = metadata_enhancer.suggest_organization_improvements(document_data)

        assert any("title" in s.lower() for s in suggestions)

    def test_suggest_tags_for_long_document_without_tags(self, metadata_enhancer):
        """Test suggestion for long document without tags."""
        # Create content longer than 1000 characters
        long_content = "API development with FastAPI. " * 50
        document_data = {
            "title": "Test Document",
            "content": long_content,
            "tags": []
        }

        suggestions = metadata_enhancer.suggest_organization_improvements(document_data)

        assert len(suggestions) > 0
        assert any("tag" in s.lower() for s in suggestions)

    def test_suggest_tags_for_document_without_tags(self, metadata_enhancer):
        """Test suggestion when document has content but no tags."""
        document_data = {
            "title": "FastAPI Tutorial",
            "content": "Building REST APIs with FastAPI and PostgreSQL database",
            "tags": []
        }

        suggestions = metadata_enhancer.suggest_organization_improvements(document_data)

        # Should suggest tags
        assert len(suggestions) > 0
        assert any("tag" in s.lower() for s in suggestions)
        # Should list suggested tags
        assert any("fastapi" in s.lower() or "api" in s.lower() for s in suggestions)

    def test_suggest_category_for_technical_document(self, metadata_enhancer):
        """Test category suggestion for technical document."""
        document_data = {
            "title": "API Development",
            "content": "FastAPI REST API with PostgreSQL database and Docker deployment"
        }

        suggestions = metadata_enhancer.suggest_organization_improvements(document_data)

        # Should suggest technical category
        assert any("technical" in s.lower() for s in suggestions)

    def test_suggest_category_for_business_document(self, metadata_enhancer):
        """Test category suggestion for business document."""
        document_data = {
            "title": "Quarterly Planning",
            "content": "Project roadmap and team goals with milestone tracking"
        }

        suggestions = metadata_enhancer.suggest_organization_improvements(document_data)

        # Should suggest business category
        assert any("business" in s.lower() for s in suggestions)

    def test_suggest_no_category_for_general_document(self, metadata_enhancer):
        """Test that general documents don't get category suggestions."""
        document_data = {
            "title": "Random Notes",
            "content": "Some random thoughts and personal notes"
        }

        suggestions = metadata_enhancer.suggest_organization_improvements(document_data)

        # Should not suggest category for general documents
        # (only suggest category if it's not "general")
        category_suggestions = [s for s in suggestions if "technical" in s or "business" in s or "research" in s]
        assert len(category_suggestions) == 0

    def test_suggest_limits_tag_suggestions(self, metadata_enhancer):
        """Test that tag suggestions are limited to reasonable number."""
        document_data = {
            "title": "Technical Document",
            "content": "API FastAPI REST HTTP PostgreSQL MySQL Docker Kubernetes Python JavaScript",
            "tags": []
        }

        suggestions = metadata_enhancer.suggest_organization_improvements(document_data)

        # Find suggestion with tags
        tag_suggestion = [s for s in suggestions if "Suggested tags:" in s]

        if tag_suggestion:
            # Should limit to 5 tags as per implementation
            tag_count = len(tag_suggestion[0].split(":")[1].split(","))
            assert tag_count <= 5

    def test_suggest_with_existing_tags(self, metadata_enhancer):
        """Test that documents with existing tags don't get tag suggestions."""
        document_data = {
            "title": "API Development",
            "content": "FastAPI REST API development",
            "tags": ["api", "fastapi", "rest"]
        }

        suggestions = metadata_enhancer.suggest_organization_improvements(document_data)

        # Should not suggest tags if document already has tags
        assert not any("Suggested tags:" in s for s in suggestions)

    def test_suggest_empty_list_for_well_organized_document(self, metadata_enhancer):
        """Test minimal suggestions for well-organized short document."""
        document_data = {
            "title": "Well Organized",
            "content": "Short content",
            "tags": ["well", "organized"]
        }

        suggestions = metadata_enhancer.suggest_organization_improvements(document_data)

        # Should have minimal or no suggestions
        assert isinstance(suggestions, list)


class TestEdgeCases:
    """Tests for edge cases and boundary conditions."""

    def test_very_large_document(self, metadata_enhancer):
        """Test handling of very large documents."""
        # Create a large document with repeated content
        large_content = " ".join(["API development with FastAPI and PostgreSQL"] * 1000)
        document_data = {
            "id": "doc-large",
            "title": "Large Document",
            "content": large_content
        }

        enhanced = metadata_enhancer.enhance_metadata(document_data)

        # Should handle without errors
        assert "tags" in enhanced
        assert "category" in enhanced
        assert len(enhanced["tags"]) <= 10

    def test_special_characters_in_content(self, metadata_enhancer):
        """Test handling of special characters and unicode."""
        document_data = {
            "id": "doc-special",
            "title": "API™ Development ©",
            "content": "Symbols: @#$%^&* and unicode: café résumé naïve"
        }

        enhanced = metadata_enhancer.enhance_metadata(document_data)

        # Should handle without errors
        assert isinstance(enhanced["tags"], list)
        assert isinstance(enhanced["category"], str)

    def test_null_values_in_document(self, metadata_enhancer):
        """Test handling of null values in document fields."""
        document_data = {
            "id": "doc-null",
            "title": None,
            "content": None
        }

        enhanced = metadata_enhancer.enhance_metadata(document_data)

        # Should handle None values gracefully
        # Note: None gets converted to string "None" and may appear as tag
        assert isinstance(enhanced["tags"], list)
        assert enhanced["category"] == "general"

    def test_numeric_content(self, metadata_enhancer):
        """Test handling of numeric content."""
        document_data = {
            "id": "doc-numeric",
            "title": "API v2.0",
            "content": "HTTP 404 errors and Python 3.11 features with 100% coverage"
        }

        enhanced = metadata_enhancer.enhance_metadata(document_data)

        # Should extract meaningful words while handling numbers
        assert isinstance(enhanced["tags"], list)
        assert "category" in enhanced

    def test_document_with_only_id(self, metadata_enhancer):
        """Test minimal document with only ID field."""
        document_data = {
            "id": "doc-minimal"
        }

        enhanced = metadata_enhancer.enhance_metadata(document_data)

        # Should provide default metadata
        assert enhanced["tags"] == []
        assert enhanced["category"] == "general"
        assert enhanced["topics"] == []

    def test_mixed_case_and_whitespace(self, metadata_enhancer):
        """Test handling of mixed case and whitespace variations."""
        document_data = {
            "id": "doc-mixed",
            "title": "  FastAPI   REST  ",
            "content": "API\n\ndevelopment\t\twith\r\nPOSTGRESQL  "
        }

        enhanced = metadata_enhancer.enhance_metadata(document_data)

        # Should normalize and extract tags properly
        assert len(enhanced["tags"]) > 0
        assert enhanced["category"] == "technical"

    def test_document_dict_not_modified(self, metadata_enhancer):
        """Test that original document dict is not modified."""
        original_data = {
            "id": "doc-original",
            "title": "Test",
            "content": "API development"
        }

        # Create a copy to compare
        import copy
        original_copy = copy.deepcopy(original_data)

        enhanced = metadata_enhancer.enhance_metadata(original_data)

        # Original should remain unchanged
        assert original_data == original_copy
        # Enhanced should have new fields
        assert "tags" in enhanced
        assert "tags" not in original_data


class TestIntegrationWithAutoTagger:
    """Tests for integration with AutoTagger service."""

    def test_auto_tagger_initialization(self, metadata_enhancer):
        """Test that AutoTagger is properly initialized."""
        assert metadata_enhancer.auto_tagger is not None
        assert hasattr(metadata_enhancer.auto_tagger, 'extract_tags')
        assert hasattr(metadata_enhancer.auto_tagger, 'classify_category')

    @patch('graph_rag.services.organization.metadata_enhancer.AutoTagger')
    def test_auto_tagger_extract_tags_called(self, mock_auto_tagger_class):
        """Test that AutoTagger.extract_tags is called correctly."""
        mock_auto_tagger = Mock()
        mock_auto_tagger.extract_tags.return_value = ["api", "fastapi"]
        mock_auto_tagger.classify_category.return_value = "technical"
        mock_auto_tagger.extract_hierarchical_tags.return_value = {"technology": ["api"]}
        mock_auto_tagger.extract_tags_with_confidence.return_value = [("api", 0.9)]
        mock_auto_tagger_class.return_value = mock_auto_tagger

        enhancer = MetadataEnhancer()
        document_data = {
            "title": "FastAPI",
            "content": "API development"
        }

        enhancer.enhance_metadata(document_data)

        # Verify extract_tags was called with combined text and normalize=True
        mock_auto_tagger.extract_tags.assert_called_once()
        call_args = mock_auto_tagger.extract_tags.call_args
        assert "FastAPI" in call_args[0][0]
        assert "API development" in call_args[0][0]
        assert call_args[1]["normalize"] is True

    @patch('graph_rag.services.organization.metadata_enhancer.AutoTagger')
    def test_auto_tagger_classify_category_called(self, mock_auto_tagger_class):
        """Test that AutoTagger.classify_category is called correctly."""
        mock_auto_tagger = Mock()
        mock_auto_tagger.extract_tags.return_value = ["api"]
        mock_auto_tagger.classify_category.return_value = "technical"
        mock_auto_tagger.extract_hierarchical_tags.return_value = {"technology": ["api"]}
        mock_auto_tagger.extract_tags_with_confidence.return_value = [("api", 0.9)]
        mock_auto_tagger_class.return_value = mock_auto_tagger

        enhancer = MetadataEnhancer()
        document_data = {
            "title": "FastAPI",
            "content": "API development"
        }

        enhancer.enhance_metadata(document_data)

        # Verify classify_category was called
        mock_auto_tagger.classify_category.assert_called_once()

    @patch('graph_rag.services.organization.metadata_enhancer.AutoTagger')
    def test_auto_tagger_hierarchical_tags_called(self, mock_auto_tagger_class):
        """Test that AutoTagger.extract_hierarchical_tags is called correctly."""
        mock_auto_tagger = Mock()
        mock_auto_tagger.extract_tags.return_value = ["api"]
        mock_auto_tagger.classify_category.return_value = "technical"
        mock_auto_tagger.extract_hierarchical_tags.return_value = {
            "technology": ["api", "fastapi"],
            "business": ["project"]
        }
        mock_auto_tagger.extract_tags_with_confidence.return_value = [("api", 0.9)]
        mock_auto_tagger_class.return_value = mock_auto_tagger

        enhancer = MetadataEnhancer()
        document_data = {
            "title": "FastAPI Project",
            "content": "API development"
        }

        enhanced = enhancer.enhance_metadata(document_data)

        # Verify hierarchical tags are flattened into topics
        assert "topics" in enhanced
        assert "api" in enhanced["topics"]
        assert "fastapi" in enhanced["topics"]
        assert "project" in enhanced["topics"]
