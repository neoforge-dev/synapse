"""Test advanced query capabilities using TDD approach."""

import pytest


def test_boolean_query_builder():
    """Test that complex Boolean queries can be constructed and executed."""
    from graph_rag.services.query.advanced_query_builder import AdvancedQueryBuilder

    builder = AdvancedQueryBuilder()

    # Test AND operation
    query = (builder
             .field("content").contains("API")
             .AND()
             .field("tags").contains("python")
             .build())

    assert query is not None
    assert query.get_query_string() is not None
    assert "AND" in query.get_query_string()

    # Test OR operation
    query2 = (builder
              .field("title").contains("machine learning")
              .OR()
              .field("content").contains("artificial intelligence")
              .build())

    assert query2 is not None
    assert "OR" in query2.get_query_string()

    # Test complex nested query
    complex_query = (builder
                     .group_start()
                     .field("category").equals("technical")
                     .AND()
                     .field("tags").contains("database")
                     .group_end()
                     .OR()
                     .field("content").contains("SQL")
                     .build())

    assert complex_query is not None
    assert complex_query.validate()


def test_field_specific_search():
    """Test that queries can target specific document fields."""
    from graph_rag.services.query.advanced_query_builder import AdvancedQueryBuilder

    builder = AdvancedQueryBuilder()

    # Test exact field matching
    title_query = builder.field("title").equals("API Documentation").build()
    assert title_query.get_field_filters()["title"]["equals"] == "API Documentation"

    # Test field range queries
    date_query = (builder
                  .field("created_at").after("2024-01-01")
                  .AND()
                  .field("created_at").before("2024-12-31")
                  .build())

    date_filters = date_query.get_field_filters()
    assert "created_at" in date_filters
    assert "after" in date_filters["created_at"]
    assert "before" in date_filters["created_at"]

    # Test field existence check
    has_tags_query = builder.field("tags").exists().build()
    assert has_tags_query.get_field_filters()["tags"]["exists"] is True


def test_query_templates():
    """Test that common query patterns can be saved and reused as templates."""
    from graph_rag.services.query.query_templates import QueryTemplateManager

    template_manager = QueryTemplateManager()

    # Create a technical documentation template
    tech_doc_template = {
        "name": "technical_documentation",
        "description": "Find technical documentation with specific tags",
        "query_pattern": {
            "field_filters": {
                "category": {"equals": "technical"},
                "tags": {"contains": "{technology}"}
            },
            "content_search": "{search_term}"
        },
        "parameters": ["technology", "search_term"]
    }

    # Save template
    template_manager.save_template(tech_doc_template)

    # Retrieve and use template
    saved_template = template_manager.get_template("technical_documentation")
    assert saved_template is not None
    assert saved_template["name"] == "technical_documentation"
    assert "technology" in saved_template["parameters"]

    # Apply template with parameters
    applied_query = template_manager.apply_template(
        "technical_documentation",
        {"technology": "python", "search_term": "flask"}
    )

    assert applied_query is not None
    assert applied_query.get_field_filters()["tags"]["contains"] == "python"
    assert applied_query.get_content_search() == "flask"


def test_query_expansion():
    """Test that queries are automatically enhanced using graph relationships."""
    from unittest.mock import AsyncMock

    from graph_rag.services.query.smart_query_expander import SmartQueryExpander

    # Mock graph repository
    mock_graph_repo = AsyncMock()
    mock_graph_repo.get_related_entities.return_value = [
        {"name": "FastAPI", "type": "framework", "relationship": "related_to"},
        {"name": "Pydantic", "type": "library", "relationship": "used_with"},
        {"name": "REST", "type": "architecture", "relationship": "implements"}
    ]

    expander = SmartQueryExpander(mock_graph_repo)

    original_query = "python web development"

    # Test expansion
    expanded_terms = expander.expand_query_terms(original_query)

    assert isinstance(expanded_terms, list)
    assert len(expanded_terms) > 0

    # Should include original terms plus related concepts
    expanded_text = " ".join(expanded_terms)
    assert "python" in expanded_text.lower()
    assert "web" in expanded_text.lower()
    assert "development" in expanded_text.lower()


@pytest.mark.asyncio
async def test_query_suggestions():
    """Test that query suggestions are provided based on content analysis."""
    from unittest.mock import AsyncMock

    from graph_rag.services.query.query_suggestions import QuerySuggestionEngine

    # Mock vector store for similarity search
    mock_vector_store = AsyncMock()
    mock_vector_store.search_similar_chunks.return_value = [
        {"text": "FastAPI REST API development tutorial", "score": 0.9},
        {"text": "Python web framework comparison", "score": 0.8},
        {"text": "API authentication best practices", "score": 0.7}
    ]

    suggestion_engine = QuerySuggestionEngine(mock_vector_store)

    partial_query = "python api"

    suggestions = await suggestion_engine.get_suggestions(partial_query, limit=5)

    assert isinstance(suggestions, list)
    assert len(suggestions) <= 5
    assert all(isinstance(suggestion, str) for suggestion in suggestions)

    # Suggestions should be relevant to the input
    suggestions_text = " ".join(suggestions).lower()
    assert "python" in suggestions_text or "api" in suggestions_text


def test_query_scoring_and_ranking():
    """Test that search results can be re-ranked with custom scoring."""
    from graph_rag.services.query.result_ranker import AdvancedResultRanker

    ranker = AdvancedResultRanker()

    # Mock search results
    results = [
        {
            "content": "Python API development with FastAPI framework",
            "title": "FastAPI Tutorial",
            "tags": ["python", "api", "fastapi"],
            "category": "technical",
            "score": 0.7
        },
        {
            "content": "General programming concepts and best practices",
            "title": "Programming Basics",
            "tags": ["programming", "general"],
            "category": "educational",
            "score": 0.8
        },
        {
            "content": "Advanced Python web development patterns",
            "title": "Advanced Python",
            "tags": ["python", "web", "advanced"],
            "category": "technical",
            "score": 0.6
        }
    ]

    query_context = {
        "search_terms": ["python", "api"],
        "preferred_categories": ["technical"],
        "boost_recent": True
    }

    # Test custom ranking
    ranked_results = ranker.rank_results(results, query_context)

    assert len(ranked_results) == len(results)
    assert all("final_score" in result for result in ranked_results)

    # First result should be most relevant (Python + API + technical)
    assert ranked_results[0]["title"] == "FastAPI Tutorial"
    assert ranked_results[0]["final_score"] > ranked_results[1]["final_score"]


def test_saved_queries():
    """Test that users can save and retrieve complex queries."""
    from graph_rag.services.query.saved_queries import SavedQueryManager

    query_manager = SavedQueryManager()

    # Create a complex saved query
    complex_query = {
        "name": "recent_python_docs",
        "description": "Recent Python documentation and tutorials",
        "query": {
            "field_filters": {
                "category": {"equals": "technical"},
                "tags": {"contains": "python"},
                "created_at": {"after": "2024-01-01"}
            },
            "content_search": "tutorial OR documentation",
            "sort_by": "created_at",
            "sort_order": "desc"
        },
        "created_by": "user123",
        "is_public": True
    }

    # Save query
    query_id = query_manager.save_query(complex_query)
    assert query_id is not None

    # Retrieve query
    saved_query = query_manager.get_query(query_id)
    assert saved_query is not None
    assert saved_query["name"] == "recent_python_docs"
    assert saved_query["query"]["field_filters"]["tags"]["contains"] == "python"

    # List user queries
    user_queries = query_manager.list_user_queries("user123")
    assert len(user_queries) >= 1
    assert any(q["name"] == "recent_python_docs" for q in user_queries)

    # Test public queries
    public_queries = query_manager.list_public_queries()
    assert len(public_queries) >= 1
    assert any(q["name"] == "recent_python_docs" for q in public_queries)
