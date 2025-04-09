import pytest
from unittest.mock import AsyncMock, MagicMock, call, patch
import uuid

# Import interfaces and concrete classes for type hinting and mocking
from graph_rag.core.interfaces import (
    DocumentData, ChunkData, ExtractedEntity, ExtractedRelationship, 
    ExtractionResult, SearchResultData, DocumentProcessor, EntityExtractor,
    KnowledgeGraphBuilder, VectorSearcher, KeywordSearcher, GraphSearcher
)
from graph_rag.core.graph_rag_engine import GraphRAGEngine, SimpleGraphRAGEngine, QueryResult
from graph_rag.models import Chunk, Entity, Relationship
from graph_rag.core.graph_store import MockGraphStore
from graph_rag.core.vector_store import MockVectorStore

# --- Mock Dependencies --- 

@pytest.fixture
def mock_doc_processor() -> DocumentProcessor:
    processor = AsyncMock(spec=DocumentProcessor)
    # Sample chunk data
    processor.chunk_document.return_value = [
        ChunkData(id="c1", text="Chunk 1 text", document_id="doc1"),
        ChunkData(id="c2", text="Chunk 2 text about Apple.", document_id="doc1")
    ]
    return processor

@pytest.fixture
def mock_entity_extractor() -> EntityExtractor:
    extractor = AsyncMock(spec=EntityExtractor)
    # Sample extraction results
    def mock_extract_side_effect(text):
        if "Apple" in text:
            return ExtractionResult(
                entities=[ExtractedEntity(id="apple", label="ORG", text="Apple")],
                relationships=[]
            )
        return ExtractionResult(entities=[], relationships=[])
    extractor.extract.side_effect = mock_extract_side_effect
    return extractor

@pytest.fixture
def mock_kg_builder() -> KnowledgeGraphBuilder:
    return AsyncMock(spec=KnowledgeGraphBuilder)

@pytest.fixture
def mock_embedding_service() -> MagicMock:
    # Mocking the service used internally by the engine (likely)
    # Assuming it has an encode method
    service = MagicMock()
    service.encode.return_value = [0.1] * 384 # Example embedding
    return service

@pytest.fixture
def mock_vector_searcher() -> VectorSearcher:
    searcher = AsyncMock(spec=VectorSearcher)
    searcher.search_similar_chunks.return_value = [
        SearchResultData(
            chunk=ChunkData(id="c-sim-1", text="Similar chunk 1", document_id="doc-sim"),
            score=0.9
        )
    ]
    return searcher

@pytest.fixture
def mock_keyword_searcher() -> KeywordSearcher:
    searcher = AsyncMock(spec=KeywordSearcher)
    searcher.search_chunks_by_keyword.return_value = [
         SearchResultData(
            chunk=ChunkData(id="c-key-1", text="Keyword chunk 1", document_id="doc-key"),
            score=1.0 # Keyword score often binary or TF-IDF based
        )
    ]
    return searcher

@pytest.fixture
def mock_graph_searcher() -> GraphSearcher:
    searcher = AsyncMock(spec=GraphSearcher)
    searcher.find_related_chunks.return_value = [
        SearchResultData(
            chunk=ChunkData(id="c-graph-1", text="Graph related chunk 1", document_id="doc-graph"),
            score=1.0 # Graph proximity might have different scoring
        )
    ]
    return searcher

@pytest.fixture
def mock_graph_store() -> MockGraphStore:
    store = MockGraphStore()
    # Pre-populate with some data for graph context tests
    alice = Entity(id="ent-alice", name="Alice", type="PERSON", metadata={"age": 30})
    bob = Entity(id="ent-bob", name="Bob", type="PERSON", metadata={"city": "New York"})
    wonderland = Entity(id="ent-wonder", name="Wonderland", type="LOCATION", metadata={"fictional": True})
    store.add_entity(alice)
    store.add_entity(bob)
    store.add_entity(wonderland)
    store.add_relationship(Relationship(source=alice, target=bob, type="KNOWS"))
    store.add_relationship(Relationship(source=alice, target=wonderland, type="LIVES_IN"))
    return store

@pytest.fixture
def mock_vector_store() -> MockVectorStore:
    # Pre-populate with some chunks
    store = MockVectorStore()
    store.add_chunks([
        Chunk(id="c1", text="Alice is a person.", document_id="doc1", metadata={}),
        Chunk(id="c2", text="Alice works at Foo Corp and knows Bob.", document_id="doc1", metadata={}),
        Chunk(id="c3", text="Bob lives in New York.", document_id="doc2", metadata={})
    ])
    return store

# --- Engine Fixture --- 

@pytest.fixture
def rag_engine(
    mock_doc_processor,
    mock_entity_extractor,
    mock_kg_builder,
    mock_embedding_service, # Assuming engine uses embedding service directly
    mock_vector_searcher,
    mock_keyword_searcher,
    mock_graph_searcher
) -> GraphRAGEngine:
    # Inject mocked dependencies
    return GraphRAGEngine(
        document_processor=mock_doc_processor,
        entity_extractor=mock_entity_extractor,
        kg_builder=mock_kg_builder,
        embedding_service=mock_embedding_service, 
        vector_searcher=mock_vector_searcher,
        keyword_searcher=mock_keyword_searcher,
        graph_searcher=mock_graph_searcher
    )

@pytest.fixture
def engine(mock_graph_store, mock_vector_store) -> SimpleGraphRAGEngine:
    """Provides a SimpleGraphRAGEngine instance with mock stores."""
    return SimpleGraphRAGEngine(graph_store=mock_graph_store, vector_store=mock_vector_store)

# --- Test Cases --- 

@pytest.mark.asyncio
async def test_process_and_store_document_flow(
    rag_engine: GraphRAGEngine,
    mock_doc_processor: DocumentProcessor,
    mock_entity_extractor: EntityExtractor,
    mock_kg_builder: KnowledgeGraphBuilder,
    mock_embedding_service: MagicMock
):
    """Test the full ingestion pipeline orchestration."""
    doc_content = "Chunk 1 text. Chunk 2 text about Apple."
    metadata = {"source": "test_engine"}
    
    await rag_engine.process_and_store_document(doc_content, metadata)
    
    # 1. Verify Document Processor called
    mock_doc_processor.chunk_document.assert_called_once()
    doc_data_arg = mock_doc_processor.chunk_document.call_args[0][0]
    assert isinstance(doc_data_arg, DocumentData)
    assert doc_data_arg.content == doc_content
    assert doc_data_arg.metadata == metadata
    
    # 2. Verify KG Builder adds document
    mock_kg_builder.add_document.assert_called_once_with(doc_data_arg)
    
    # 3. Verify Embeddings generated for chunks
    chunk_texts = ["Chunk 1 text", "Chunk 2 text about Apple."]
    mock_embedding_service.encode.assert_called_once_with(chunk_texts)
    
    # 4. Verify Entity Extractor called for each chunk
    assert mock_entity_extractor.extract.call_count == 2
    mock_entity_extractor.extract.assert_any_call("Chunk 1 text")
    mock_entity_extractor.extract.assert_any_call("Chunk 2 text about Apple.")
    
    # 5. Verify KG Builder adds chunks (with embeddings)
    assert mock_kg_builder.add_chunk.call_count == 2
    chunk1_call = mock_kg_builder.add_chunk.call_args_list[0][0][0]
    chunk2_call = mock_kg_builder.add_chunk.call_args_list[1][0][0]
    assert chunk1_call.text == "Chunk 1 text"
    assert chunk1_call.embedding is not None # Embedding should have been added
    assert chunk2_call.text == "Chunk 2 text about Apple."
    assert chunk2_call.embedding is not None
    
    # 6. Verify KG Builder adds entities (only Apple expected)
    mock_kg_builder.add_entity.assert_called_once()
    entity_arg = mock_kg_builder.add_entity.call_args[0][0]
    assert entity_arg.id == "apple"
    
    # 7. Verify KG Builder links chunks to entities
    mock_kg_builder.link_chunk_to_entities.assert_called_once_with(
        chunk_id="c2", # ID from mock_doc_processor
        entity_ids=["apple"] # ID from mock_entity_extractor
    )
    # Note: Chunk c1 had no entities, so link shouldn't be called for it

@pytest.mark.asyncio
async def test_retrieve_context_vector(rag_engine: GraphRAGEngine, mock_vector_searcher: VectorSearcher, mock_embedding_service: MagicMock):
    """Test vector search retrieval path."""
    query = "find similar things"
    results = await rag_engine.retrieve_context(query, search_type="vector", limit=3)
    
    mock_embedding_service.encode.assert_called_once_with(query)
    mock_vector_searcher.search_similar_chunks.assert_called_once_with(
        query_vector=[0.1]*384, # From mock_embedding_service
        limit=3
    )
    assert len(results) == 1
    assert results[0].chunk.id == "c-sim-1"

@pytest.mark.asyncio
async def test_retrieve_context_keyword(rag_engine: GraphRAGEngine, mock_keyword_searcher: KeywordSearcher, mock_embedding_service: MagicMock):
    """Test keyword search retrieval path."""
    query = "find keyword things"
    results = await rag_engine.retrieve_context(query, search_type="keyword", limit=7)
    
    mock_keyword_searcher.search_chunks_by_keyword.assert_called_once_with(query=query, limit=7)
    mock_embedding_service.encode.assert_not_called() # No embedding needed for keyword
    assert len(results) == 1
    assert results[0].chunk.id == "c-key-1"

# TODO: Add test for graph search path
# TODO: Add test for invalid search_type
# TODO: Add test for answer_query (will require LLM mocking or placeholder) 

def test_engine_initialization(mock_graph_store, mock_vector_store):
    """Test that the engine initializes correctly with stores."""
    engine = SimpleGraphRAGEngine(graph_store=mock_graph_store, vector_store=mock_vector_store)
    assert engine._graph_store is mock_graph_store
    assert engine._vector_store is mock_vector_store

def test_engine_requires_stores():
    """Test that initialization fails if stores are not the correct type."""
    with pytest.raises(TypeError):
        SimpleGraphRAGEngine(graph_store=object(), vector_store=MockVectorStore())
    with pytest.raises(TypeError):
        SimpleGraphRAGEngine(graph_store=MockGraphStore(), vector_store=object())

def test_engine_query_calls_vector_store(engine, mock_vector_store):
    """Test that the query method calls the vector store's search method."""
    query_text = "Tell me about Alice."
    k = 5
    # Mock the search method on the specific instance
    mock_vector_store.search = MagicMock(return_value=mock_vector_store.chunks) # Return all chunks for simplicity
    
    result = engine.query(query_text, config={"k": k})

    # Verify search was called correctly
    mock_vector_store.search.assert_called_once_with(query_text, k=k)
    
    # Verify the result structure (basic checks)
    assert isinstance(result, QueryResult)
    assert len(result.relevant_chunks) > 0 # Should find some mock chunks
    assert "Alice is a person." in result.answer # Check if answer is derived
    # Graph context might be found due to simple entity extraction from chunks
    # assert result.graph_context is not None 
    assert result.metadata["query"] == query_text

def test_engine_query_no_results(engine, mock_vector_store):
    """Test query handling when vector store returns no results."""
    query_text = "Unknown topic?"
    # Configure mock to return empty list
    mock_vector_store.search = MagicMock(return_value=[])

    result = engine.query(query_text)

    mock_vector_store.search.assert_called_once_with(query_text, k=3) # Default k
    assert len(result.relevant_chunks) == 0
    assert "Could not find relevant information" in result.answer
    assert result.graph_context is None

def test_engine_query_handles_vector_store_error(engine, mock_vector_store):
    """Test query handling when the vector store raises an exception."""
    query_text = "Error query"
    error_message = "Vector DB connection failed"
    mock_vector_store.search = MagicMock(side_effect=RuntimeError(error_message))

    result = engine.query(query_text)
    
    mock_vector_store.search.assert_called_once_with(query_text, k=3)
    assert isinstance(result, QueryResult)
    assert "An error occurred" in result.answer
    assert error_message in result.answer
    assert len(result.relevant_chunks) == 0 # No chunks should be returned on error
    assert result.graph_context is None

# --- Tests for Graph Context Retrieval --- 

def test_engine_query_retrieves_graph_context(engine, mock_graph_store, mock_vector_store):
    """Test that query retrieves and includes graph context based on chunk entities."""
    query_text = "Tell me about Alice and Bob"
    # Ensure vector search returns chunks mentioning Alice and Bob
    mock_vector_store.search = MagicMock(return_value=[
        Chunk(id="c2", text="Alice works at Foo Corp and knows Bob.", document_id="doc1"),
        Chunk(id="c3", text="Bob lives in New York.", document_id="doc2")
    ])
    
    # Spy on graph store methods
    mock_graph_store.get_neighbors = MagicMock(wraps=mock_graph_store.get_neighbors)

    result = engine.query(query_text, config={"k": 2, "include_graph": True})

    assert result.graph_context is not None
    entities, relationships = result.graph_context
    
    entity_names = {e.name for e in entities}
    # Expect Alice, Bob, and potentially Wonderland (neighbor of Alice)
    assert "Alice" in entity_names
    assert "Bob" in entity_names
    assert "Wonderland" in entity_names # From Alice's neighborhood
    # Verify get_neighbors was called for entities found in graph (Alice, Bob)
    # Note: This depends on the exact implementation of _find_entities_in_graph
    # Since the mock version finds Alice and Bob, we expect calls for them.
    assert mock_graph_store.get_neighbors.call_count >= 1 # At least one call expected
    calls = mock_graph_store.get_neighbors.call_args_list
    called_ids = {c[0][0] for c in calls} # Extract entity_id from call args
    assert "ent-alice" in called_ids # Check if called for Alice
    # Add check for Bob if _find_entities_in_graph finds Bob
    assert "ent-bob" in called_ids

    # Check relationships (should include Alice KNOWS Bob and Alice LIVES_IN Wonderland)
    assert len(relationships) >= 2
    rel_tuples = {(r.source.name, r.type, r.target.name) for r in relationships}
    assert ("Alice", "KNOWS", "Bob") in rel_tuples
    assert ("Alice", "LIVES_IN", "Wonderland") in rel_tuples
    
    # Check that the answer mentions graph context
    assert "Graph context includes entities like" in result.answer

def test_engine_query_graph_context_disabled(engine, mock_graph_store, mock_vector_store):
    """Test that graph context is not retrieved if config disables it."""
    query_text = "Info about Alice"
    mock_vector_store.search = MagicMock(return_value=[
         Chunk(id="c2", text="Alice works at Foo Corp and knows Bob.", document_id="doc1")
    ])
    mock_graph_store.get_neighbors = MagicMock(wraps=mock_graph_store.get_neighbors)

    result = engine.query(query_text, config={"include_graph": False})

    assert result.graph_context is None
    mock_graph_store.get_neighbors.assert_not_called()
    assert "Graph context includes entities like" not in result.answer

def test_engine_query_no_entities_found_in_graph(engine, mock_graph_store, mock_vector_store):
    """Test query when potential entities from chunks aren't found in the graph."""
    query_text = "Info about Charlie"
    # Return chunk mentioning an entity not in the mock graph store
    mock_vector_store.search = MagicMock(return_value=[
         Chunk(id="c4", text="Charlie went to the park.", document_id="doc3")
    ])
    # Make graph store return no matches for the name "Charlie"
    with patch.object(engine, '_find_entities_in_graph', return_value=[]) as mock_find:
         result = engine.query(query_text)
         mock_find.assert_called_once_with(["Charlie"]) # Verify attempt to find

    assert result.graph_context is None
    assert "Graph context includes entities like" not in result.answer 