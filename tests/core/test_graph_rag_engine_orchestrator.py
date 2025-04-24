import asyncio
from unittest.mock import AsyncMock, MagicMock, patch, call

import pytest

from graph_rag.core.document_processor import DocumentProcessor
from graph_rag.core.graph_rag_engine import GraphRAGEngineOrchestrator
from graph_rag.domain.models import Document, Entity, Relationship, Chunk
from graph_rag.core.interfaces import (
    DocumentData,
    DocumentProcessor, EntityExtractor, KnowledgeGraphBuilder, EmbeddingService, GraphRepository, ChunkData,
    VectorStore
)


@pytest.fixture
def mock_document_processor():
    mock = AsyncMock(spec=DocumentProcessor)
    mock.chunk_document.return_value = [
        Chunk(id="chunk1", text="Chunk 1 text.", document_id="doc1"),
        Chunk(id="chunk2", text="Chunk 2 text.", document_id="doc1"),
    ]
    return mock

@pytest.fixture
def mock_embedding_service():
    mock = AsyncMock(spec=EmbeddingService)
    mock.generate_embedding.side_effect = lambda text: [0.1] * 10
    mock.get_embedding_dimension.return_value = 10
    return mock

@pytest.fixture
def mock_entity_extractor() -> AsyncMock:
    extractor = AsyncMock(spec=EntityExtractor)
    def side_effect(text):
        # Create some valid ExtractedEntity objects
        entities = [
            ExtractedEntity(id=f"e_{text[:5]}", label="TEST_LABEL", text=text[:5]),
            ExtractedEntity(id="e_other", label="OTHER", text="other")
        ]
        # Return an ExtractionResult with valid entities and NO relationships
        # to avoid Pydantic validation issues with Relationship model in the test setup
        return ExtractionResult(entities=entities, relationships=[])
        
    extractor.extract.side_effect = side_effect
    return extractor

@pytest.fixture
def mock_kg_builder():
    mock = AsyncMock(spec=KnowledgeGraphBuilder)
    return mock

@pytest.fixture
def mock_graph_repository():
    mock = AsyncMock(spec=GraphRepository)
    return mock

@pytest.fixture
def mock_vector_store():
    """Provides an AsyncMock for the VectorStore interface."""
    mock = AsyncMock(spec=VectorStore)
    # Configure specific return values or side effects if needed for tests
    # Example: mock.add_chunks.return_value = None 
    # Example: mock.search.return_value = [...] 
    return mock

@pytest.fixture
def graph_rag_engine(
    mock_document_processor,
    mock_embedding_service,
    mock_entity_extractor,
    mock_kg_builder,
    mock_graph_repository,
    mock_vector_store
):
    # Assuming VectorStore dependency needs mocking if used directly in process_and_store_document
    # For now, let's assume it's handled within kg_builder or repo
    return GraphRAGEngineOrchestrator(
        document_processor=mock_document_processor,
        embedding_service=mock_embedding_service,
        entity_extractor=mock_entity_extractor,
        kg_builder=mock_kg_builder,
        graph_repo=mock_graph_repository,
        vector_store=mock_vector_store,
        graph_store=mock_graph_repository
    )

@pytest.mark.asyncio
async def test_process_and_store_document_success(
    graph_rag_engine,
    mock_document_processor,
    mock_embedding_service,
    mock_entity_extractor,
    mock_kg_builder,
    mock_graph_repository
):
    """
    Test the successful processing and storing of a document.
    """
    document = Document(id="doc1", content="Full document text.", metadata={"source": "test"})

    # Call the method with doc_content and metadata as separate arguments
    await graph_rag_engine.process_and_store_document(
        doc_content=document.content, 
        metadata=document.metadata
    )

    # Assertions
    # The method internally creates DocumentData, so mocks should expect that or the original Document
    # Let's check the implementation again - it creates DocumentData(id=doc_id, content=doc_content, metadata=metadata)
    # So mocks should expect DocumentData

    # Assert DocumentProcessor call
    # Construct the expected DocumentData object (need to handle generated doc_id? No, mock can use ANY)
    from unittest.mock import ANY # Import ANY
    # expected_doc_data = DocumentData(id=ANY, content=document.content, metadata=document.metadata)
    # mock_document_processor.chunk_document.assert_awaited_once_with(expected_doc_data)
    
    # Instead of using ANY with Pydantic, assert call count and inspect args:
    mock_document_processor.chunk_document.assert_awaited_once()
    call_args, call_kwargs = mock_document_processor.chunk_document.call_args
    passed_doc_data = call_args[0] # Assuming DocumentData is the first positional arg
    assert isinstance(passed_doc_data, DocumentData)
    assert passed_doc_data.content == document.content
    assert passed_doc_data.metadata == document.metadata
    assert isinstance(passed_doc_data.id, str) # Check if ID is a string (was generated)

    # Check calls for each chunk
    assert mock_embedding_service.generate_embedding.await_count == 2
    mock_embedding_service.generate_embedding.assert_any_await("Chunk 1 text.")
    mock_embedding_service.generate_embedding.assert_any_await("Chunk 2 text.")

    assert mock_entity_extractor.extract.await_count == 2
    mock_entity_extractor.extract.assert_any_await("Chunk 1 text.")
    mock_entity_extractor.extract.assert_any_await("Chunk 2 text.")

    # Check KG builder calls
    mock_kg_builder.add_document.assert_awaited_once_with(document)

    assert mock_kg_builder.add_chunk.await_count == 2
    # Check chunk calls (order might vary due to asyncio.gather)
    expected_chunk_calls = [
        call(Chunk(id='chunk1', text='Chunk 1 text.', document_id='doc1'), [0.1] * 10),
        call(Chunk(id='chunk2', text='Chunk 2 text.', document_id='doc1'), [0.1] * 10)
    ]
    mock_kg_builder.add_chunk.assert_has_awaits(expected_chunk_calls, any_order=True)


    # Check entity/relationship calls (simplified check for any call due to complex data)
    assert mock_kg_builder.add_entity.await_count == 2 # One per chunk in this mock setup
    assert mock_kg_builder.add_relationship.await_count == 2 # One per chunk

    # Check graph repository calls (assuming KG builder uses it internally, or if engine calls it directly)
    # If the engine calls graph_repo.add_entities_and_relationships directly:
    # assert mock_graph_repository.add_entities_and_relationships.await_count == 1 # Or potentially more depending on logic

    # Example if KG builder calls repo:
    # mock_graph_repository.add_nodes.assert_awaited() # More specific checks needed
    # mock_graph_repository.add_edges.assert_awaited() # More specific checks needed

    # Note: Assertions on graph_repository depend heavily on the internal implementation
    # of KnowledgeGraphBuilder and how it interacts with the repository.
    # For now, we focus on the direct interactions of GraphRAGEngine.
    # If GraphRAGEngine calls graph_repo.add_entities_and_relationships directly:
    # mock_graph_repository.add_entities_and_relationships.assert_awaited_once() # Need to verify this interaction


# Add more tests for edge cases and error handling
# - Test with no chunks returned
# - Test with no entities/relationships extracted
# - Test with errors during embedding generation
# - Test with errors during entity extraction
# - Test with errors during knowledge graph building

    # Assert no other unexpected calls (optional, but good practice)
    # e.g., mock_graph_repo methods should not have been called if not expected

    # # 8. Assert graph_repo methods called << DELETE THIS SECTION
    # mock_graph_repo.add_document.assert_awaited_once_with(document)
    # mock_graph_repo.add_chunk.assert_awaited_count(2)
    # mock_graph_repo.add_entity.assert_awaited_count(2)
    # mock_graph_repo.add_relationship.assert_awaited_once_with(\n    #     Relationship(source_id="E1", target_id="E2", label="FRIENDS", properties={})\n    # ) 

# Sample data for testing
DOC_ID = "doc1"