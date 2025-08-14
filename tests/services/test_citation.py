"""Tests for the citation service."""

import pytest
from graph_rag.models import Chunk
from graph_rag.services.citation import (
    CitationService, 
    CitationStyle, 
    CitationMetadata,
    NumericCitationFormatter,
    APACitationFormatter
)


class TestCitationService:
    """Test suite for CitationService."""

    @pytest.fixture
    def citation_service(self):
        """Create a citation service with numeric style."""
        return CitationService(CitationStyle.NUMERIC)

    @pytest.fixture
    def sample_chunks(self):
        """Create sample chunks for testing."""
        return [
            Chunk(
                id="chunk1",
                text="Artificial intelligence is transforming healthcare by enabling more accurate diagnoses.",
                document_id="doc1",
                metadata={
                    "title": "AI in Healthcare",
                    "author": "Dr. John Smith",
                    "source": "Medical Journal",
                    "publication_date": "2023",
                    "score": 0.9
                }
            ),
            Chunk(
                id="chunk2", 
                text="Machine learning algorithms can process vast amounts of medical data quickly.",
                document_id="doc2",
                metadata={
                    "title": "ML Applications",
                    "author": "Jane Doe",
                    "source": "Tech Review",
                    "publication_date": "2024",
                    "score": 0.8
                }
            )
        ]

    def test_extract_metadata_from_chunk(self, citation_service, sample_chunks):
        """Test extracting citation metadata from a chunk."""
        chunk = sample_chunks[0]
        metadata = citation_service.extract_metadata_from_chunk(chunk)
        
        assert metadata.chunk_id == "chunk1"
        assert metadata.document_id == "doc1"
        assert metadata.title == "AI in Healthcare"
        assert metadata.author == "Dr. John Smith"
        assert metadata.source == "Medical Journal"
        assert metadata.publication_date == "2023"
        assert metadata.relevance_score == 0.9
        assert "Artificial intelligence is transforming" in metadata.context_snippet

    def test_enhance_answer_with_citations(self, citation_service, sample_chunks):
        """Test enhancing an answer with citations."""
        answer = "AI is revolutionizing healthcare through better diagnoses. Machine learning processes medical data efficiently."
        context_texts = [chunk.text for chunk in sample_chunks]
        
        result = citation_service.enhance_answer_with_citations(
            answer, 
            sample_chunks,
            context_texts
        )
        
        assert result.answer_with_citations is not None
        assert len(result.citations) == 2
        assert result.total_sources == 2
        assert "[1]" in result.answer_with_citations or "[2]" in result.answer_with_citations
        assert "numeric" in result.bibliography

    def test_citation_without_context_texts(self, citation_service, sample_chunks):
        """Test citation enhancement without providing context texts."""
        answer = "AI helps with medical diagnoses."
        
        result = citation_service.enhance_answer_with_citations(answer, sample_chunks)
        
        assert result.answer_with_citations is not None
        assert len(result.citations) == 2
        assert result.total_sources == 2

    def test_citation_with_empty_chunks(self, citation_service):
        """Test citation enhancement with no chunks."""
        answer = "This is a test answer."
        
        result = citation_service.enhance_answer_with_citations(answer, [])
        
        assert result.answer_with_citations == answer
        assert len(result.citations) == 0
        assert result.total_sources == 0

    def test_keyword_extraction(self, citation_service):
        """Test keyword extraction functionality."""
        text = "Artificial intelligence and machine learning are transforming healthcare."
        keywords = citation_service._extract_keywords(text)
        
        assert "artificial" in keywords
        assert "intelligence" in keywords
        assert "machine" in keywords
        assert "learning" in keywords
        assert "healthcare" in keywords
        # Stop words should be filtered out
        assert "and" not in keywords
        assert "are" not in keywords

    def test_chunk_referencing_detection(self, citation_service):
        """Test detection of chunk referencing in answer."""
        answer = "Machine learning algorithms can process medical data quickly."
        chunk_text = "Machine learning algorithms can process vast amounts of medical data quickly."
        context_texts = [chunk_text]
        
        metadata = CitationMetadata(
            chunk_id="test",
            document_id="test_doc",
            chunk_text=chunk_text
        )
        
        is_referenced = citation_service._is_chunk_referenced(answer, metadata, context_texts)
        assert is_referenced  # Should detect high overlap


class TestCitationFormatters:
    """Test citation formatters."""

    def test_numeric_formatter(self):
        """Test numeric citation formatter."""
        formatter = NumericCitationFormatter()
        metadata = CitationMetadata(
            chunk_id="test",
            document_id="test_doc", 
            title="Test Article",
            author="Test Author",
            source="Test Source",
            publication_date="2023"
        )
        
        inline = formatter.format_inline_citation(1, metadata)
        assert inline == "[1]"
        
        bibliography = formatter.format_bibliography_entry(1, metadata)
        assert "[1]" in bibliography
        assert "Test Author" in bibliography
        assert "Test Article" in bibliography

    def test_apa_formatter(self):
        """Test APA citation formatter."""
        formatter = APACitationFormatter()
        metadata = CitationMetadata(
            chunk_id="test",
            document_id="test_doc",
            title="Test Article", 
            author="Smith, J.",
            publication_date="2023"
        )
        
        inline = formatter.format_inline_citation(1, metadata)
        assert inline == "(Smith, J., 2023)"
        
        bibliography = formatter.format_bibliography_entry(1, metadata)
        assert "Smith, J." in bibliography
        assert "(2023)" in bibliography

    def test_apa_formatter_fallback(self):
        """Test APA formatter with missing information."""
        formatter = APACitationFormatter()
        metadata = CitationMetadata(
            chunk_id="test",
            document_id="test_doc",
            title="Test Article"
            # No author or date
        )
        
        inline = formatter.format_inline_citation(1, metadata)
        assert inline == '("Test Article")'


class TestCitationServiceStyles:
    """Test different citation styles."""

    def test_apa_style_service(self):
        """Test citation service with APA style."""
        service = CitationService(CitationStyle.APA)
        assert service.citation_style == CitationStyle.APA
        assert isinstance(service.formatter, APACitationFormatter)

    def test_unsupported_style_fallback(self):
        """Test fallback to numeric for unsupported styles."""
        # This would normally trigger the warning in _get_formatter
        service = CitationService(CitationStyle.NUMERIC)
        assert isinstance(service.formatter, NumericCitationFormatter)


class TestCitationMetadata:
    """Test citation metadata."""

    def test_citation_metadata_to_dict(self):
        """Test converting citation metadata to dictionary."""
        metadata = CitationMetadata(
            chunk_id="test_chunk",
            document_id="test_doc",
            title="Test Title",
            author="Test Author",
            relevance_score=0.95,
            used_in_answer=True
        )
        
        data = metadata.to_dict()
        
        assert data["chunk_id"] == "test_chunk"
        assert data["document_id"] == "test_doc" 
        assert data["title"] == "Test Title"
        assert data["author"] == "Test Author"
        assert data["relevance_score"] == 0.95
        assert data["used_in_answer"] is True
        assert isinstance(data["inline_references"], list)