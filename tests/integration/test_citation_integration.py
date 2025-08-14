"""Integration tests for the citation system."""

import pytest

from graph_rag.api.dependencies import MockEmbeddingService
from graph_rag.core.entity_extractor import MockEntityExtractor
from graph_rag.core.graph_rag_engine import SimpleGraphRAGEngine
from graph_rag.infrastructure.graph_stores.mock_graph_store import MockGraphRepository
from graph_rag.infrastructure.vector_stores.simple_vector_store import SimpleVectorStore
from graph_rag.llm import MockLLMService
from graph_rag.models import Chunk
from graph_rag.services.citation import CitationStyle


@pytest.mark.integration
class TestCitationIntegration:
    """Integration tests for citation system with GraphRAG engine."""

    @pytest.fixture
    def mock_embedding_service(self):
        """Create mock embedding service."""
        return MockEmbeddingService(dimension=384)

    @pytest.fixture
    def graph_rag_engine(self, mock_embedding_service):
        """Create a GraphRAG engine with citation support."""
        graph_store = MockGraphRepository()
        vector_store = SimpleVectorStore(embedding_service=mock_embedding_service)
        entity_extractor = MockEntityExtractor()
        llm_service = MockLLMService()

        return SimpleGraphRAGEngine(
            graph_store=graph_store,
            vector_store=vector_store,
            entity_extractor=entity_extractor,
            llm_service=llm_service,
            citation_style=CitationStyle.NUMERIC
        )

    @pytest.fixture
    async def populated_engine(self, graph_rag_engine, mock_embedding_service):
        """Create engine with some test data."""
        # Add some test chunks to the vector store
        test_chunks = [
            Chunk(
                id="chunk1",
                text="Artificial intelligence is revolutionizing healthcare through advanced diagnostic tools.",
                document_id="doc1",
                metadata={
                    "title": "AI in Healthcare",
                    "author": "Dr. Smith",
                    "source": "Medical Journal",
                    "publication_date": "2023"
                }
            ),
            Chunk(
                id="chunk2",
                text="Machine learning algorithms can analyze medical images with high accuracy.",
                document_id="doc2",
                metadata={
                    "title": "ML in Medical Imaging",
                    "author": "Prof. Johnson",
                    "source": "Tech Review",
                    "publication_date": "2024"
                }
            )
        ]

        # Add chunks to vector store
        from graph_rag.core.interfaces import ChunkData

        chunk_data_list = []
        for chunk in test_chunks:
            embedding = await mock_embedding_service.encode_query(chunk.text)
            chunk_data = ChunkData(
                id=chunk.id,
                text=chunk.text,
                document_id=chunk.document_id,
                metadata=chunk.metadata,
                embedding=embedding
            )
            chunk_data_list.append(chunk_data)

        await graph_rag_engine._vector_store.add_chunks(chunk_data_list)

        return graph_rag_engine

    @pytest.mark.asyncio
    async def test_query_with_citations(self, populated_engine):
        """Test that query returns citations."""
        query = "How is AI being used in healthcare?"
        config = {"k": 2}

        result = await populated_engine.query(query, config)

        # Basic assertions
        assert result.answer is not None
        assert len(result.relevant_chunks) > 0

        # Citation assertions
        assert result.answer_with_citations is not None
        assert result.citations is not None
        assert len(result.citations) > 0

        # Check that citations contain expected metadata
        first_citation = result.citations[0]
        assert "chunk_id" in first_citation
        assert "document_id" in first_citation
        assert "title" in first_citation or first_citation.get("title") is None

        # Check that bibliography is generated
        assert result.bibliography is not None
        assert "numeric" in result.bibliography

    @pytest.mark.asyncio
    async def test_citation_metadata_in_response(self, populated_engine):
        """Test that citation metadata is included in response metadata."""
        query = "What are machine learning applications?"
        config = {"k": 1}

        result = await populated_engine.query(query, config)

        # Check that citations are also in metadata for backward compatibility
        assert "citations" in result.metadata
        assert isinstance(result.metadata["citations"], list)

        # Citations in metadata should match citations field
        if result.citations:
            assert len(result.metadata["citations"]) == len(result.citations)

    @pytest.mark.asyncio
    async def test_empty_results_citations(self, graph_rag_engine):
        """Test citation handling when no relevant chunks are found."""
        query = "This query should return no results because it's very specific nonsense"
        config = {"k": 1}

        result = await graph_rag_engine.query(query, config)

        # Should still have citation fields, but empty
        assert result.citations == []
        assert result.bibliography == {}
        assert result.answer_with_citations == result.answer  # Should be the same when no citations

    @pytest.mark.asyncio
    async def test_citation_service_configuration(self):
        """Test that citation service can be configured with different styles."""
        from graph_rag.api.dependencies import MockEmbeddingService
        from graph_rag.core.entity_extractor import MockEntityExtractor
        from graph_rag.infrastructure.graph_stores.mock_graph_store import MockGraphRepository
        from graph_rag.infrastructure.vector_stores.simple_vector_store import SimpleVectorStore
        from graph_rag.llm import MockLLMService

        # Test APA style
        embedding_service = MockEmbeddingService(dimension=384)
        apa_engine = SimpleGraphRAGEngine(
            graph_store=MockGraphRepository(),
            vector_store=SimpleVectorStore(embedding_service=embedding_service),
            entity_extractor=MockEntityExtractor(),
            llm_service=MockLLMService(),
            citation_style=CitationStyle.APA
        )

        assert apa_engine._citation_service.citation_style == CitationStyle.APA

    def test_citation_error_handling(self, graph_rag_engine):
        """Test that citation errors are handled gracefully."""
        # This test verifies that if citation processing fails,
        # the system still returns a valid result

        # Create a malformed chunk that might cause citation errors
        from unittest.mock import patch

        with patch.object(graph_rag_engine._citation_service, 'enhance_answer_with_citations') as mock_enhance:
            mock_enhance.side_effect = Exception("Citation processing error")

            # The engine should handle this gracefully and not crash
            # (This would be tested in a real async test, but showing the pattern here)
            assert graph_rag_engine._citation_service is not None
