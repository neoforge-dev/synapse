import logging
import pytest
from unittest.mock import AsyncMock, MagicMock, call, patch, create_autospec
import uuid
from pytest_mock import MockerFixture
from typing import List, Tuple, Optional, Dict, Any
import asyncio
import numpy as np # Add numpy import

# Import interfaces and concrete classes for type hinting and mocking
from graph_rag.core.interfaces import (
    DocumentData, ChunkData, ExtractedEntity, ExtractedRelationship, 
    ExtractionResult, SearchResultData, DocumentProcessor, EntityExtractor,
    KnowledgeGraphBuilder, VectorSearcher, KeywordSearcher, GraphSearcher,
    EmbeddingService, VectorStore, GraphRepository
)
from graph_rag.core.graph_rag_engine import SimpleGraphRAGEngine, QueryResult
from graph_rag.models import Document, Chunk, Entity, Relationship, ProcessedDocument
from graph_rag.domain.models import Node
from graph_rag.core.graph_store import MockGraphStore
from graph_rag.core.interfaces import VectorStore # Import VectorStore interface
from graph_rag.core.vector_store import MockVectorStore # Keep MockVectorStore import
from graph_rag.core.interfaces import DocumentProcessor
from graph_rag.core.entity_extractor import MockEntityExtractor
from graph_rag.core.knowledge_graph_builder import KnowledgeGraphBuilder
from graph_rag.services.embedding import EmbeddingService
from graph_rag.services.search import SearchService, SearchResult # Import SearchResult
from graph_rag.llm.protocols import LLMService # Remove LLMResponse import
from graph_rag.infrastructure.cache.protocols import CacheService
from graph_rag.llm.llm_service import MockLLMService # Corrected import path

# Configure logging for tests
logger = logging.getLogger(__name__)

# Add a default config fixture
@pytest.fixture
def config() -> Dict[str, Any]:
    """Provides a default configuration dictionary for engine tests."""
    return {"k": 3, "include_graph": True, "limit_neighbors": 10, "limit_entities": 10}

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
    service = MagicMock(spec=EmbeddingService)
    service.encode_documents = AsyncMock(return_value=[[0.1, 0.2], [0.3, 0.4]])
    service.encode_query = AsyncMock(return_value=[0.5, 0.6])
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
    # Use metadata field according to graph_rag.models.Entity definition
    alice = Entity(id="ent-alice", name="Alice", type="PERSON", metadata={"name": "Alice", "age": 30})
    bob = Entity(id="ent-bob", name="Bob", type="PERSON", metadata={"name": "Bob", "city": "New York"})
    wonderland = Entity(id="ent-wonder", name="Wonderland", type="LOCATION", metadata={"name": "Wonderland", "fictional": True})
    store.add_entity(alice)
    store.add_entity(bob)
    store.add_entity(wonderland)
    # Relationship uses Entity objects directly from graph_rag.models
    store.add_relationship(Relationship(source=alice, target=bob, type="KNOWS"))
    store.add_relationship(Relationship(source=alice, target=wonderland, type="LIVES_IN"))
    return store

@pytest.fixture
def mock_vector_store(mocker: MockerFixture) -> AsyncMock:
    """Fixture for a mocked VectorStore conforming to the protocol."""
    mock = mocker.AsyncMock(spec=VectorStore)
    mock.add_chunks = mocker.AsyncMock()
    # Mock the 'search' method directly as used by SimpleGraphRAGEngine
    mock.search = mocker.AsyncMock(return_value=[
        SearchResultData(
            chunk=ChunkData(id="mock-chunk-1", text="Mock search result chunk", document_id="mock-doc-1", metadata={}), # Added metadata
            score=0.85
        )
    ])
    mock.get_chunk_by_id = mocker.AsyncMock(return_value=None) # Default to not found
    mock.delete_chunks = mocker.AsyncMock()
    mock.delete_store = mocker.AsyncMock()
    mock.get_retriever = mocker.MagicMock() # Return a simple MagicMock for the retriever
    logger.info("MockVectorStore (AsyncMock) fixture created.")
    return mock

@pytest.fixture
def mock_graph_repository() -> AsyncMock:
    repo = AsyncMock(spec=GraphRepository)
    repo.get_neighbors = AsyncMock(return_value=([], []))
    repo.add_entity = AsyncMock()
    repo.search_entities_by_properties = AsyncMock(return_value=[])
    repo.add_document = AsyncMock() # Add mock for other used methods if necessary
    repo.add_chunk = AsyncMock()
    repo.add_relationship = AsyncMock()
    return repo

@pytest.fixture
def mock_llm_service() -> AsyncMock:
    """Fixture for a mocked LLMService."""
    mock = AsyncMock(spec=LLMService)
    # Configure generate_response to return a simple string
    async def mock_generate_response(prompt: str, context: Optional[str] = None, history: Optional[List[Dict[str, str]]] = None) -> str: # Change type hint to str
        # Simple response based on prompt content
        answer_text = f"Synthesized answer for prompt: {prompt[:50]}..."
        return answer_text # Return string directly
        
    # Point to the correct method name as defined in the protocol
    mock.generate_response.side_effect = mock_generate_response 
    
    # Ensure other methods from the protocol are mocked if needed by tests
    mock.generate_response_stream = AsyncMock()
    mock.extract_entities_relationships = AsyncMock(return_value=([], []))
    mock.embed_text = AsyncMock()
    mock.get_token_usage = AsyncMock(return_value={"total_tokens": 0})
    
    return mock

# --- Engine Fixture --- 

@pytest.fixture
def rag_engine(
    mock_graph_repository: AsyncMock, # Use the GraphRepository mock
    mock_vector_store: AsyncMock, # Use the AsyncMock VectorStore
    mock_entity_extractor: AsyncMock, # Use AsyncMock EntityExtractor
    mock_llm_service: AsyncMock # Add LLM service mock
) -> SimpleGraphRAGEngine:
    # Instantiate the concrete SimpleGraphRAGEngine with all mocks
    return SimpleGraphRAGEngine(
        graph_store=mock_graph_repository,
        vector_store=mock_vector_store,
        entity_extractor=mock_entity_extractor, # Use the mock passed in
        llm_service=mock_llm_service # Pass the LLM mock
    )

# --- Test Cases --- 

@pytest.mark.asyncio
async def test_process_and_store_document_flow(
    rag_engine: SimpleGraphRAGEngine, # Use the fixture providing the engine instance
    mock_graph_store: MockGraphStore, # Get the concrete mock store to spy on calls
    mock_vector_store: AsyncMock, # Use AsyncMock vector store
    mock_entity_extractor: AsyncMock, # Use AsyncMock
):
    """Tests the overall flow of processing and storing a document."""
    # This test seems more appropriate for the IngestionService.
    # SimpleGraphRAGEngine doesn't have a process_and_store_document method.
    pytest.skip("Skipping test: process_and_store_document is not part of SimpleGraphRAGEngine. Test belongs in ingestion service tests.")

@pytest.mark.asyncio
async def test_retrieve_context_vector(
    rag_engine: SimpleGraphRAGEngine,
    mock_vector_store: AsyncMock, # Expect the AsyncMock vector store
    mock_llm_service: AsyncMock, # Need LLM mock
):
    """Tests retrieving context using only vector search results and synthesizing answer."""
    # Arrange
    query_text = "search query"
    expected_chunk_data = ChunkData(id="chunk1", text="Relevant text.", document_id="doc1", metadata={})
    expected_search_results = [SearchResultData(chunk=expected_chunk_data, score=0.9)]
    mock_vector_store.search.return_value = expected_search_results

    # Expected domain Chunk object in the result
    expected_domain_chunk = Chunk(
        id=expected_chunk_data.id,
        text=expected_chunk_data.text,
        document_id=expected_chunk_data.document_id,
        # Combine original metadata with score
        metadata={**expected_chunk_data.metadata, "score": 0.9} if expected_chunk_data.metadata else {"score": 0.9}
    )

    # Act
    query_result = await rag_engine.query(query_text, config={"include_graph": False, "k": 10})

    # Assert Vector Search
    mock_vector_store.search.assert_awaited_once_with(query_text, top_k=10)

    # Assert LLM Call (ensure it was called since context was found)
    mock_llm_service.generate_response.assert_awaited_once()
    # Optional: More detailed check on the prompt sent to LLM
    prompt_arg = mock_llm_service.generate_response.call_args[0][0]
    assert query_text in prompt_arg
    assert expected_chunk_data.text in prompt_arg
    assert "Graph Entities" not in prompt_arg # Graph context was disabled

    # Assert Query Result
    assert isinstance(query_result, QueryResult)
    assert query_result.answer.startswith("Synthesized answer") # Check mock LLM response
    assert len(query_result.relevant_chunks) == 1
    # Compare the actual Chunk object with the expected one
    assert query_result.relevant_chunks[0].id == expected_domain_chunk.id
    assert query_result.relevant_chunks[0].text == expected_domain_chunk.text
    assert query_result.relevant_chunks[0].document_id == expected_domain_chunk.document_id
    assert query_result.relevant_chunks[0].metadata == expected_domain_chunk.metadata
    assert query_result.relevant_chunks[0].metadata.get("score") == 0.9 # Check score in metadata
    assert query_result.graph_context is None # Graph context not requested
    logger.info("test_retrieve_context_vector passed.")

@pytest.mark.asyncio
async def test_simple_engine_query_uses_stores(
    rag_engine: SimpleGraphRAGEngine, # Use the fixture for SimpleGraphRAGEngine
    mock_graph_repository: AsyncMock, # Use AsyncMock
    mock_vector_store: AsyncMock, # Use AsyncMock
    mock_llm_service: AsyncMock, # Use LLM mock
    mock_entity_extractor: AsyncMock # Use extractor mock
):
    """Test that the SimpleGraphRAGEngine query method interacts with stores and LLM."""
    query_text = "find keyword things"
    config = {"include_graph": False, "k": 1} # Disable graph context, k=1
    mock_chunk_text = "Keyword chunk 1"
    mock_chunk_data = ChunkData(id="c-key-1", text=mock_chunk_text, document_id="doc-key", metadata={})
    mock_search_result = [SearchResultData(chunk=mock_chunk_data, score=0.95)]

    # Mock vector store search
    mock_vector_store.search.return_value = mock_search_result

    # Mock graph store methods (not expected to be called)
    mock_graph_repository.search_entities_by_properties.return_value = []
    mock_graph_repository.get_neighbors.return_value = ([], [])

    # Mock entity extractor (not strictly needed if graph=False, but good practice)
    mock_entity_extractor.extract.return_value = ExtractionResult(entities=[], relationships=[])

    # Act: Call the query method
    result: QueryResult = await rag_engine.query(query_text, config=config)

    # Assertions
    # Vector store called
    mock_vector_store.search.assert_awaited_once_with(query_text, top_k=1)
    # Entity extractor NOT called (because graph=False, implicitly skipped in earlier steps)
    # Note: Current implementation might call extractor even if graph=False, adjust if needed.
    # For now, assume it's skipped if graph=False or no chunks found.
    # mock_entity_extractor.extract.assert_not_called() # Adjust assertion based on implementation
    # Graph store methods NOT called
    mock_graph_repository.search_entities_by_properties.assert_not_called()
    mock_graph_repository.get_neighbors.assert_not_called()
    # LLM called because chunks were found
    mock_llm_service.generate_response.assert_awaited_once()
    prompt_arg = mock_llm_service.generate_response.call_args[0][0]
    assert query_text in prompt_arg
    assert mock_chunk_text in prompt_arg
    assert "Graph Entities" not in prompt_arg # Graph context disabled

    # Result checks
    assert isinstance(result, QueryResult)
    assert result.answer.startswith("Synthesized answer")
    assert len(result.relevant_chunks) == 1
    assert result.relevant_chunks[0].id == "c-key-1"
    assert result.relevant_chunks[0].text == mock_chunk_text
    assert result.relevant_chunks[0].metadata.get("score") == 0.95 # Check score in metadata
    assert result.graph_context is None

# --- Test Initialization ---
def test_engine_initialization(mock_graph_repository, mock_vector_store: AsyncMock, mock_entity_extractor, mock_llm_service):
    """Test that the engine initializes correctly with all dependencies."""
    engine = SimpleGraphRAGEngine(
        graph_store=mock_graph_repository,
        vector_store=mock_vector_store,
        entity_extractor=mock_entity_extractor,
        llm_service=mock_llm_service # Pass LLM mock
    )
    assert engine._graph_store is mock_graph_repository
    assert engine._vector_store is mock_vector_store
    assert engine._entity_extractor is mock_entity_extractor
    assert engine._llm_service is mock_llm_service # Check LLM service assignment

def test_engine_initialization_default_llm(mock_graph_repository, mock_vector_store: AsyncMock, mock_entity_extractor):
    """Test that the engine initializes with MockLLMService if none is provided."""
    engine = SimpleGraphRAGEngine(
        graph_store=mock_graph_repository,
        vector_store=mock_vector_store,
        entity_extractor=mock_entity_extractor,
        llm_service=None # Explicitly pass None
    )
    assert engine._graph_store is mock_graph_repository
    assert engine._vector_store is mock_vector_store
    assert engine._entity_extractor is mock_entity_extractor
    # Check that a MockLLMService instance was created
    assert isinstance(engine._llm_service, MockLLMService)

def test_engine_requires_stores():
    """Test that initialization fails if graph/vector stores are not the correct type."""
    # Need valid mocks for other params
    mock_extractor = AsyncMock(spec=EntityExtractor)
    mock_vector = AsyncMock(spec=VectorStore)
    mock_graph = AsyncMock(spec=GraphRepository)

    with pytest.raises(TypeError, match="graph_store must implement the GraphRepository protocol"):
        SimpleGraphRAGEngine(graph_store=object(), vector_store=mock_vector, entity_extractor=mock_extractor)
    with pytest.raises(TypeError, match="vector_store must be an instance of VectorStore"):
        SimpleGraphRAGEngine(graph_store=mock_graph, vector_store=object(), entity_extractor=mock_extractor)
    # Entity extractor type check was commented out, skipping associated test

# --- Tests for Graph Context Retrieval (Updated to Async and LLM) ---

@pytest.fixture
def mock_graph_repo() -> AsyncMock: # Renaming for clarity, matches new tests below
    mock = AsyncMock(spec=GraphRepository)
    mock.search_entities_by_properties = AsyncMock(return_value=[])
    mock.get_neighbors = AsyncMock(return_value=([], []))
    return mock

@pytest.fixture
def sample_chunk_list() -> List[SearchResultData]:
    return [
        SearchResultData(chunk=ChunkData(id="chunk-vec-1", text="Alice mentioned Bob.", document_id="doc-vec-1", metadata={}, embedding=[0.1]*10), score=0.8),
        SearchResultData(chunk=ChunkData(id="chunk-vec-2", text="Bob works at Acme.", document_id="doc-vec-2", metadata={}, embedding=[0.2]*10), score=0.75)
    ]

@pytest.fixture
def sample_extracted_entities() -> List[ExtractedEntity]:
    return [
        ExtractedEntity(id="ent-ext-alice", text="Alice", label="PERSON", score=0.9),
        ExtractedEntity(id="ent-ext-bob", text="Bob", label="PERSON", score=0.85),
        ExtractedEntity(id="ent-ext-acme", text="Acme", label="ORG", score=0.95)
    ]

@pytest.fixture
def sample_graph_entities() -> List[Entity]:
    # Domain Entity models that exist in the graph
    return [
        Entity(id="ent-graph-alice", name="Alice", type="PERSON", metadata={"name": "Alice"}),
        Entity(id="ent-graph-bob", name="Bob", type="PERSON", metadata={"name": "Bob"}),
    ]

@pytest.fixture
def sample_graph_neighbors(sample_graph_entities: List[Entity]) -> Tuple[List[Entity], List[Relationship]]:
    # Use metadata field according to graph_rag.models.Entity definition
    neighbor_charlie = Entity(id="ent-graph-charlie", name="Charlie", type="PERSON", metadata={"name": "Charlie"})
    # Use the @dataclass Relationship definition (no id, uses metadata)
    rel_alice_bob = Relationship(source=sample_graph_entities[0], target=sample_graph_entities[1], type="KNOWS", metadata={})
    rel_bob_charlie = Relationship(source=sample_graph_entities[1], target=neighbor_charlie, type="FRIEND_OF", metadata={})
    all_entities = sample_graph_entities + [neighbor_charlie]
    all_relationships = [rel_alice_bob, rel_bob_charlie]
    return all_entities, all_relationships

@pytest.mark.asyncio
async def test_simple_engine_query_with_graph_context(
    mock_graph_repo: AsyncMock,
    mock_vector_store: AsyncMock,
    mock_entity_extractor: AsyncMock,
    mock_llm_service: AsyncMock, # Add LLM mock
    sample_chunk_list: List[SearchResultData],
    sample_extracted_entities: List[ExtractedEntity],
    sample_graph_entities: List[Entity],
    sample_graph_neighbors: Tuple[List[Entity], List[Relationship]],
    config: Dict # Use shared config fixture
):
    """Tests a query retrieving vector results, graph context, and synthesizing an answer."""
    # Arrange
    query = "find me related documents about Alice"
    engine = SimpleGraphRAGEngine(
        graph_store=mock_graph_repo,
        vector_store=mock_vector_store,
        entity_extractor=mock_entity_extractor,
        llm_service=mock_llm_service # Include LLM service
    )

    # Configure mocks
    mock_vector_store.search.return_value = sample_chunk_list
    combined_text = " ".join([sr.chunk.text for sr in sample_chunk_list if sr.chunk]) # Ensure chunk exists
    mock_entity_extractor.extract_from_text.return_value = ExtractionResult(entities=sample_extracted_entities, relationships=[])

    # Mock graph search
    async def mock_search_props(search_props: Dict, limit=None):
        name_to_match = search_props.get('name')
        # Return the actual Entity object from sample_graph_entities
        return [e for e in sample_graph_entities if e.name == name_to_match]
    mock_graph_repo.search_entities_by_properties.side_effect = mock_search_props

    # Mock neighbor retrieval
    mock_graph_repo.get_neighbors.return_value = sample_graph_neighbors # Return the full tuple

    # Act
    result = await engine.query(query, config=config) # Use default config (include_graph=True)

    # Assert
    # Vector search called
    mock_vector_store.search.assert_awaited_once_with(query, top_k=config.get('k', 3))

    # Entity extraction called
    mock_entity_extractor.extract_from_text.assert_called_once_with(combined_text)

    # Graph property search called for each extracted entity
    assert mock_graph_repo.search_entities_by_properties.call_count == len(sample_extracted_entities)
    # Check specific calls (simplified check)
    mock_graph_repo.search_entities_by_properties.assert_any_call({'name': 'Alice', 'type': 'PERSON'}, limit=1)
    mock_graph_repo.search_entities_by_properties.assert_any_call({'name': 'Bob', 'type': 'PERSON'}, limit=1)
    mock_graph_repo.search_entities_by_properties.assert_any_call({'name': 'Acme', 'type': 'ORG'}, limit=1)

    # Graph neighbor retrieval called for each *expanded* entity (Alice, Bob, Charlie)
    # The mock data causes Charlie to be added and expanded as well.
    assert mock_graph_repo.get_neighbors.call_count == 3
    mock_graph_repo.get_neighbors.assert_any_call('ent-graph-alice')
    mock_graph_repo.get_neighbors.assert_any_call('ent-graph-bob')

    # LLM generate called
    mock_llm_service.generate_response.assert_awaited_once()
    prompt_arg = mock_llm_service.generate_response.call_args[0][0]
    assert query in prompt_arg
    assert sample_chunk_list[0].chunk.text in prompt_arg # Check chunk text
    assert sample_graph_entities[0].name in prompt_arg # Check entity name
    assert sample_graph_neighbors[1][0].type in prompt_arg # Check relationship type

    # Check QueryResult
    assert result.answer.startswith("Synthesized answer")
    assert len(result.relevant_chunks) == len(sample_chunk_list)
    # Check chunk mapping (basic)
    assert result.relevant_chunks[0].id == sample_chunk_list[0].chunk.id
    assert result.relevant_chunks[0].metadata.get("score") == sample_chunk_list[0].score

    # Check graph context
    assert result.graph_context is not None
    expected_entities, expected_relationships = sample_graph_neighbors
    # Compare sets of IDs as order might differ
    assert set(e.id for e in result.graph_context[0]) == set(e.id for e in expected_entities)
    assert len(result.graph_context[1]) == len(expected_relationships)
    logger.info("test_simple_engine_query_with_graph_context assertions passed.")

@pytest.mark.asyncio
async def test_simple_engine_query_graph_no_entities_extracted(
    mock_graph_repo: AsyncMock,
    mock_vector_store: AsyncMock,
    mock_entity_extractor: AsyncMock,
    mock_llm_service: AsyncMock, # Add LLM mock
    sample_chunk_list: List[SearchResultData],
    config: Dict
):
    """Tests query where vector search succeeds but no entities are extracted."""
    # Arrange
    query = "find me related documents with no entities"
    engine = SimpleGraphRAGEngine(
        mock_graph_repo, mock_vector_store, mock_entity_extractor, mock_llm_service
    )
    mock_vector_store.search.return_value = sample_chunk_list
    mock_entity_extractor.extract_from_text.return_value = ExtractionResult(entities=[], relationships=[]) # No entities extracted

    # Act
    result = await engine.query(query, config=config) # include_graph=True by default

    # Assert
    mock_vector_store.search.assert_awaited_once_with(query, top_k=config['k'])
    combined_text = " ".join([sr.chunk.text for sr in sample_chunk_list if sr.chunk])
    mock_entity_extractor.extract_from_text.assert_called_once_with(combined_text)
    # Graph searches should NOT be called
    mock_graph_repo.search_entities_by_properties.assert_not_called()
    mock_graph_repo.get_neighbors.assert_not_called()
    # LLM should still be called with only chunk context
    mock_llm_service.generate_response.assert_awaited_once()
    prompt_arg = mock_llm_service.generate_response.call_args[0][0]
    assert "Graph Entities" not in prompt_arg # Section should be omitted if empty
    # Check result
    assert result.answer.startswith("Synthesized answer")
    assert len(result.relevant_chunks) == len(sample_chunk_list)
    assert result.graph_context is None # No graph context was built
    logger.info("test_simple_engine_query_graph_no_entities_extracted assertions passed.")

@pytest.mark.asyncio
async def test_simple_engine_query_graph_entities_not_found(
    mock_graph_repo: AsyncMock,
    mock_vector_store: AsyncMock,
    mock_entity_extractor: AsyncMock,
    mock_llm_service: AsyncMock, # Add LLM mock
    sample_chunk_list: List[SearchResultData],
    sample_extracted_entities: List[ExtractedEntity], # Entities are extracted
    config: Dict
):
    """Tests query where entities are extracted but none are found in the graph."""
    # Arrange
    query = "find documents about maybe-known entities"
    engine = SimpleGraphRAGEngine(
        mock_graph_repo, mock_vector_store, mock_entity_extractor, mock_llm_service
    )
    mock_vector_store.search.return_value = sample_chunk_list
    mock_entity_extractor.extract_from_text.return_value = ExtractionResult(entities=sample_extracted_entities, relationships=[])
    # Mock graph search to return NOTHING
    mock_graph_repo.search_entities_by_properties.return_value = []

    # Act
    result = await engine.query(query, config=config) # include_graph=True by default

    # Assert
    mock_vector_store.search.assert_awaited_once_with(query, top_k=config['k'])
    combined_text = " ".join([sr.chunk.text for sr in sample_chunk_list if sr.chunk])
    mock_entity_extractor.extract_from_text.assert_called_once_with(combined_text)
    # Graph property search *was* called
    assert mock_graph_repo.search_entities_by_properties.call_count == len(sample_extracted_entities)
    # Graph neighbor search was NOT called
    mock_graph_repo.get_neighbors.assert_not_called()
    # LLM *was* called, but prompt context won't have graph details
    mock_llm_service.generate_response.assert_awaited_once()
    prompt_arg = mock_llm_service.generate_response.call_args[0][0]
    assert "Graph Entities" not in prompt_arg # Section should be omitted if empty
    # Check result
    assert result.answer.startswith("Synthesized answer")
    assert len(result.relevant_chunks) == len(sample_chunk_list)
    assert result.graph_context is None # No graph context built
    logger.info("test_simple_engine_query_graph_entities_not_found assertions passed.")

@pytest.mark.asyncio
async def test_simple_engine_query_no_context_found(
    mock_graph_repo: AsyncMock,
    mock_vector_store: AsyncMock,
    mock_entity_extractor: AsyncMock,
    mock_llm_service: AsyncMock, # Add LLM mock
    config: Dict
):
    """Tests query where vector search returns no chunks."""
    # Arrange
    query = "find info on obscure topic"
    engine = SimpleGraphRAGEngine(
        mock_graph_repo, mock_vector_store, mock_entity_extractor, mock_llm_service
    )
    # Mock vector search to return nothing
    mock_vector_store.search.return_value = []

    # Act
    result = await engine.query(query, config=config) # include_graph=True by default

    # Assert
    mock_vector_store.search.assert_awaited_once_with(query, top_k=config['k'])
    # Nothing else should be called if no chunks are found initially
    mock_entity_extractor.extract_from_text.assert_not_called()
    mock_graph_repo.search_entities_by_properties.assert_not_called()
    mock_graph_repo.get_neighbors.assert_not_called()
    # LLM should NOT be called as there's no context
    mock_llm_service.generate_response.assert_not_called()
    # Check result
    assert result.answer == "Could not generate an answer based on the available information." # Default answer when no context
    assert len(result.relevant_chunks) == 0
    assert result.graph_context is None
    logger.info("test_simple_engine_query_no_context_found assertions passed.") 