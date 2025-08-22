"""Test for citation style None handling fix."""

from unittest.mock import Mock

from graph_rag.api.dependencies import create_graph_rag_engine
from graph_rag.config import Settings
from graph_rag.services.citation import CitationStyle


def test_citation_style_none_handling():
    """Test that citation style handling works when citation_style is None."""
    # Create mock settings with citation_style as None
    mock_settings = Mock(spec=Settings)
    mock_settings.citation_style = None

    # Create mock dependencies
    mock_graph_repository = Mock()
    mock_vector_store = Mock()
    mock_entity_extractor = Mock()
    mock_llm_service = Mock()

    # This should not raise an AttributeError: 'NoneType' object has no attribute 'lower'
    engine = create_graph_rag_engine(
        graph_repository=mock_graph_repository,
        vector_store=mock_vector_store,
        entity_extractor=mock_entity_extractor,
        llm_service=mock_llm_service,
        settings=mock_settings
    )

    # Verify the engine was created successfully
    assert engine is not None
    # Verify the default citation style was used
    assert engine._citation_service.citation_style == CitationStyle.NUMERIC


def test_citation_style_empty_string_handling():
    """Test that citation style handling works when citation_style is empty string."""
    # Create mock settings with citation_style as empty string
    mock_settings = Mock(spec=Settings)
    mock_settings.citation_style = ""

    # Create mock dependencies
    mock_graph_repository = Mock()
    mock_vector_store = Mock()
    mock_entity_extractor = Mock()
    mock_llm_service = Mock()

    # This should not raise an error and should default to numeric
    engine = create_graph_rag_engine(
        graph_repository=mock_graph_repository,
        vector_store=mock_vector_store,
        entity_extractor=mock_entity_extractor,
        llm_service=mock_llm_service,
        settings=mock_settings
    )

    # Verify the engine was created successfully
    assert engine is not None
    # Verify the default citation style was used
    assert engine._citation_service.citation_style == CitationStyle.NUMERIC


def test_citation_style_valid_value():
    """Test that citation style handling works with valid values."""
    # Create mock settings with valid citation_style
    mock_settings = Mock(spec=Settings)
    mock_settings.citation_style = "apa"

    # Create mock dependencies
    mock_graph_repository = Mock()
    mock_vector_store = Mock()
    mock_entity_extractor = Mock()
    mock_llm_service = Mock()

    # This should work normally
    engine = create_graph_rag_engine(
        graph_repository=mock_graph_repository,
        vector_store=mock_vector_store,
        entity_extractor=mock_entity_extractor,
        llm_service=mock_llm_service,
        settings=mock_settings
    )

    # Verify the engine was created successfully
    assert engine is not None
    # Verify the correct citation style was used
    assert engine._citation_service.citation_style == CitationStyle.APA


def test_citation_style_invalid_value():
    """Test that citation style handling works with invalid values."""
    # Create mock settings with invalid citation_style
    mock_settings = Mock(spec=Settings)
    mock_settings.citation_style = "invalid_style"

    # Create mock dependencies
    mock_graph_repository = Mock()
    mock_vector_store = Mock()
    mock_entity_extractor = Mock()
    mock_llm_service = Mock()

    # This should fall back to numeric without error
    engine = create_graph_rag_engine(
        graph_repository=mock_graph_repository,
        vector_store=mock_vector_store,
        entity_extractor=mock_entity_extractor,
        llm_service=mock_llm_service,
        settings=mock_settings
    )

    # Verify the engine was created successfully
    assert engine is not None
    # Verify the default citation style was used as fallback
    assert engine._citation_service.citation_style == CitationStyle.NUMERIC
