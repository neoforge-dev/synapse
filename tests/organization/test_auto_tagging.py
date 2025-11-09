"""Test automatic document tagging functionality using TDD approach."""



def test_content_based_tag_extraction():
    """Test that tags are automatically extracted from document content."""
    from graph_rag.services.organization.auto_tagger import AutoTagger

    tagger = AutoTagger()

    # Test technical document
    tech_content = """
    This document explains how to implement a REST API using FastAPI and PostgreSQL.
    We'll cover authentication, database migrations, and deployment strategies.
    The API will handle user management and data validation using Pydantic models.
    """

    tags = tagger.extract_tags(tech_content)

    # Should extract relevant technical tags
    assert isinstance(tags, list)
    assert len(tags) > 0

    expected_tech_tags = {"api", "fastapi", "postgresql", "authentication", "database", "deployment"}
    found_tags = {tag.lower() for tag in tags}

    # Should find at least some expected tags
    assert len(expected_tech_tags.intersection(found_tags)) >= 3


def test_tag_confidence_scoring():
    """Test that tags have confidence scores for quality filtering."""
    from graph_rag.services.organization.auto_tagger import AutoTagger

    tagger = AutoTagger()

    content = "This is a detailed guide about machine learning algorithms and data science."

    tags_with_scores = tagger.extract_tags_with_confidence(content)

    # Should return list of (tag, confidence) tuples
    assert isinstance(tags_with_scores, list)
    assert all(isinstance(item, tuple) and len(item) == 2 for item in tags_with_scores)
    assert all(isinstance(tag, str) and isinstance(score, float) for tag, score in tags_with_scores)

    # Confidence scores should be between 0 and 1
    for _tag, confidence in tags_with_scores:
        assert 0.0 <= confidence <= 1.0

    # Should find high-confidence tags for clear content
    high_confidence_tags = [tag for tag, conf in tags_with_scores if conf > 0.7]
    assert len(high_confidence_tags) > 0


def test_category_classification():
    """Test that documents are classified into broad categories."""
    from graph_rag.services.organization.auto_tagger import AutoTagger

    tagger = AutoTagger()

    # Test different types of content
    technical_doc = "API documentation for REST endpoints and authentication flows."
    meeting_notes = "Meeting notes from Q1 planning session with action items and deadlines."
    research_paper = "Analysis of natural language processing techniques and their applications."

    tech_category = tagger.classify_category(technical_doc)
    meeting_category = tagger.classify_category(meeting_notes)
    research_category = tagger.classify_category(research_paper)

    # Should return meaningful categories
    assert tech_category in ["technical", "documentation", "development"]
    assert meeting_category in ["meeting", "planning", "business"]
    assert research_category in ["research", "academic", "analysis"]


def test_tag_normalization():
    """Test that tags are normalized for consistency."""
    from graph_rag.services.organization.auto_tagger import AutoTagger

    tagger = AutoTagger()

    # Content with variations of similar concepts
    content = """
    This covers APIs, api-design, API_development, and RESTful web services.
    Also includes HTTP methods and web-api best practices.
    """

    tags = tagger.extract_tags(content, normalize=True)

    # Should normalize variations to consistent forms
    normalized_tags = [tag.lower().replace("-", "_") for tag in tags]

    # Should consolidate similar tags
    api_related = [tag for tag in normalized_tags if "api" in tag]
    assert len(api_related) >= 1  # Should consolidate API-related tags

    # Should not have excessive duplicates
    unique_tags = set(tags)
    assert len(unique_tags) / len(tags) > 0.5  # At least 50% unique


def test_document_metadata_enhancement():
    """Test that document metadata is enhanced with organizational info."""
    from graph_rag.services.organization.metadata_enhancer import MetadataEnhancer

    enhancer = MetadataEnhancer()

    document_data = {
        "id": "doc123",
        "content": "Guide to implementing microservices with Docker and Kubernetes.",
        "title": "Microservices Architecture Guide",
        "created_at": "2024-01-15T10:00:00Z"
    }

    enhanced = enhancer.enhance_metadata(document_data)

    # Should add organizational metadata
    assert "tags" in enhanced
    assert "category" in enhanced
    assert "topics" in enhanced

    # Original data should be preserved
    assert enhanced["id"] == document_data["id"]
    assert enhanced["title"] == document_data["title"]

    # Should have meaningful enhancements
    assert len(enhanced["tags"]) > 0
    assert enhanced["category"] is not None
    assert isinstance(enhanced["topics"], list)


def test_tag_hierarchy_support():
    """Test that tags support hierarchical organization."""
    from graph_rag.services.organization.auto_tagger import AutoTagger

    tagger = AutoTagger()

    content = "Python programming tutorial covering Flask web framework and SQLAlchemy ORM."

    hierarchical_tags = tagger.extract_hierarchical_tags(content)

    # Should return nested tag structure
    assert isinstance(hierarchical_tags, dict)

    # Should have technology hierarchy
    if "technology" in hierarchical_tags:
        tech_tags = hierarchical_tags["technology"]
        assert isinstance(tech_tags, list)

        # Should include specific technologies
        tech_set = {tag.lower() for tag in tech_tags}
        expected_tech = {"python", "flask", "sqlalchemy"}
        assert len(expected_tech.intersection(tech_set)) >= 2
