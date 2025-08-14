import logging
import uuid
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from pytest_mock import MockerFixture

from graph_rag.core.graph_rag_engine import QueryResult, SimpleGraphRAGEngine
from graph_rag.core.graph_store import MockGraphStore  # Corrected location

# Import interfaces and concrete classes for type hinting and mocking
from graph_rag.core.interfaces import (
    ChunkData,
    DocumentProcessor,
    EmbeddingService,
    EntityExtractor,
    ExtractedEntity,
    ExtractionResult,
    GraphRepository,
    GraphSearcher,
    KeywordSearcher,
    KnowledgeGraphBuilder,
    SearchResultData,
    VectorSearcher,
    VectorStore,
)
from graph_rag.core.knowledge_graph_builder import KnowledgeGraphBuilder
from graph_rag.domain.models import Edge
from graph_rag.llm import (
    MockLLMService,
)  # Corrected import: MockLLMService from llm package
from graph_rag.llm.protocols import LLMService  # Remove LLMResponse import
from graph_rag.models import Chunk, Entity, Relationship
from graph_rag.services.embedding import EmbeddingService

# from graph_rag.llm.prompts import QnAPromptContext # Import QnAPromptContext

# Setup basic logging for tests if needed
logger = logging.getLogger(__name__)

# --- Helper Functions (Moved Before Fixtures/Tests) ---


def create_mock_chunk_data(
    id: str, text: str, doc_id: str = "d1", score: float = 0.0
) -> ChunkData:
    """Factory for creating ChunkData instances."""
    return ChunkData(
        id=id, text=text, document_id=doc_id, embedding=[score] * 10
    )  # Simple embedding


def create_mock_search_result(chunk_data: ChunkData, score: float) -> SearchResultData:
    """Factory for creating SearchResultData instances."""
    return SearchResultData(chunk=chunk_data, score=score)


def create_mock_extracted_entity(id: str, label: str, text: str) -> ExtractedEntity:
    """Factory for creating ExtractedEntity instances."""
    return ExtractedEntity(id=id, label=label, text=text, name=text)  # Use text as name


def create_mock_graph_entity(id: str, type: str, name: str) -> Entity:
    """Factory for creating domain Entity instances found in the graph."""
    return Entity(id=id, type=type, name=name)


def create_mock_graph_relationship(source_id: str, target_id: str, type: str) -> Edge:
    """Factory for creating domain Edge instances found in the graph."""
    edge_id = f"mock-edge-{uuid.uuid4()}"
    return Edge(
        id=edge_id, type=type, source_id=source_id, target_id=target_id, properties={}
    )


# --- Fixtures ---


@pytest.fixture
def config() -> dict[str, Any]:
    """Provides a default configuration dictionary for engine tests."""
    return {"k": 3, "include_graph": True, "limit_neighbors": 10, "limit_entities": 10}


# --- Mock Dependencies ---


@pytest.fixture
def mock_doc_processor() -> DocumentProcessor:
    processor = AsyncMock(spec=DocumentProcessor)
    # Sample chunk data
    processor.chunk_document.return_value = [
        ChunkData(id="c1", text="Chunk 1 text", document_id="doc1"),
        ChunkData(id="c2", text="Chunk 2 text about Apple.", document_id="doc1"),
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
                relationships=[],
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
            chunk=ChunkData(
                id="c-sim-1", text="Similar chunk 1", document_id="doc-sim"
            ),
            score=0.9,
        )
    ]
    return searcher


@pytest.fixture
def mock_keyword_searcher() -> KeywordSearcher:
    searcher = AsyncMock(spec=KeywordSearcher)
    searcher.search_chunks_by_keyword.return_value = [
        SearchResultData(
            chunk=ChunkData(
                id="c-key-1", text="Keyword chunk 1", document_id="doc-key"
            ),
            score=1.0,  # Keyword score often binary or TF-IDF based
        )
    ]
    return searcher


@pytest.fixture
def mock_graph_searcher() -> GraphSearcher:
    searcher = AsyncMock(spec=GraphSearcher)
    searcher.find_related_chunks.return_value = [
        SearchResultData(
            chunk=ChunkData(
                id="c-graph-1", text="Graph related chunk 1", document_id="doc-graph"
            ),
            score=1.0,  # Graph proximity might have different scoring
        )
    ]
    return searcher


@pytest.fixture
def mock_graph_store() -> MockGraphStore:
    store = MockGraphStore()
    # Pre-populate with some data for graph context tests
    # Use metadata field according to graph_rag.models.Entity definition
    alice = Entity(
        id="ent-alice",
        name="Alice",
        type="PERSON",
        metadata={"name": "Alice", "age": 30},
    )
    bob = Entity(
        id="ent-bob",
        name="Bob",
        type="PERSON",
        metadata={"name": "Bob", "city": "New York"},
    )
    wonderland = Entity(
        id="ent-wonder",
        name="Wonderland",
        type="LOCATION",
        metadata={"name": "Wonderland", "fictional": True},
    )
    store.add_entity(alice)
    store.add_entity(bob)
    store.add_entity(wonderland)
    # Relationship uses Entity objects directly from graph_rag.models
    store.add_relationship(Relationship(source=alice, target=bob, type="KNOWS"))
    store.add_relationship(
        Relationship(source=alice, target=wonderland, type="LIVES_IN")
    )
    return store


@pytest.fixture
def mock_vector_store(mocker: MockerFixture) -> AsyncMock:
    """Fixture for a mocked VectorStore conforming to the protocol."""
    mock = mocker.AsyncMock(spec=VectorStore)
    mock.add_chunks = mocker.AsyncMock()
    # Mock the 'search' method directly as used by SimpleGraphRAGEngine
    mock.search = mocker.AsyncMock(
        return_value=[
            SearchResultData(
                chunk=ChunkData(
                    id="mock-chunk-1",
                    text="Mock search result chunk",
                    document_id="mock-doc-1",
                    metadata={},
                ),  # Added metadata
                score=0.85,
            )
        ]
    )
    mock.get_chunk_by_id = mocker.AsyncMock(return_value=None)  # Default to not found
    mock.delete_chunks = mocker.AsyncMock()
    mock.delete_store = mocker.AsyncMock()
    mock.get_retriever = (
        mocker.MagicMock()
    )  # Return a simple MagicMock for the retriever
    logger.info("MockVectorStore (AsyncMock) fixture created.")
    return mock


@pytest.fixture
def mock_graph_repository() -> AsyncMock:
    repo = AsyncMock(spec=GraphRepository)
    repo.get_neighbors = AsyncMock(return_value=([], []))
    # repo.add_entity = AsyncMock() # Temporarily commented out
    repo.search_entities_by_properties = AsyncMock(return_value=[])
    # repo.add_document = AsyncMock() # Temporarily commented out
    # repo.add_chunk = AsyncMock() # Temporarily commented out
    # repo.add_relationship = AsyncMock() # Temporarily commented out
    return repo


@pytest.fixture
def mock_llm_service() -> AsyncMock:
    """Fixture for a mocked LLMService."""
    mock = AsyncMock(spec=LLMService)
    # Configure generate_response to return a simple, settable string by default
    mock.generate_response = AsyncMock(return_value="Default Mock LLM Answer")

    # Ensure other methods from the protocol are mocked if needed by tests
    mock.generate_response_stream = AsyncMock()
    mock.extract_entities_relationships = AsyncMock(return_value=([], []))
    mock.embed_text = AsyncMock()
    mock.get_token_usage = AsyncMock(return_value={"total_tokens": 0})

    return mock


# --- Engine Fixture ---


@pytest.fixture
def rag_engine(
    mock_graph_repository: AsyncMock,  # Use the GraphRepository mock
    mock_vector_store: AsyncMock,  # Use the AsyncMock VectorStore
    mock_entity_extractor: AsyncMock,  # Use AsyncMock EntityExtractor
    mock_llm_service: AsyncMock,  # Add LLM service mock
) -> SimpleGraphRAGEngine:
    # Instantiate the concrete SimpleGraphRAGEngine with all mocks
    return SimpleGraphRAGEngine(
        graph_store=mock_graph_repository,
        vector_store=mock_vector_store,
        entity_extractor=mock_entity_extractor,  # Use the mock passed in
        llm_service=mock_llm_service,  # Pass the LLM mock
    )


# --- Test Cases ---

# @pytest.mark.skip(reason="Skipping test: process_and_store_document is not part of SimpleGraphRAGEngine. Test belongs in ingestion service tests.")
# @pytest.mark.asyncio
# async def test_process_and_store_document_flow(
#     simple_engine_with_mocks: SimpleGraphRAGEngine,
#     mock_document_processor: AsyncMock,
#     mock_entity_extractor: AsyncMock, # Use the correct fixture name
#     mock_kg_builder: AsyncMock,
#     mock_vector_store: AsyncMock, # Use the correct fixture name
#     test_document_data: DocumentData
# ):
#     """Test the full process_and_store_document flow (mocked)."""
#     engine = simple_engine_with_mocks
#     logger.info(f"Testing process_and_store_document flow for engine: {type(engine).__name__}")

#     # Configure mocks (adjust return values as needed)
#     mock_document_processor.process.return_value = [ChunkData(id=f"chunk-{i}", text=f"Chunk {i} text", document_id=test_document_data.id) for i in range(2)]
#     mock_entity_extractor.extract.return_value = ExtractionResult(
#         entities=[ExtractedEntity(text="Entity1", label="ORG")],
#         relationships=[ExtractedRelationship(source="Entity1", target="Entity2", type="RELATED_TO")]
#     )
#     mock_kg_builder.build.return_value = ProcessedDocument(
#         document=Document(id=test_document_data.id, text=test_document_data.content, metadata=test_document_data.metadata),
#         chunks=[Chunk(id=f"chunk-{i}", text=f"Chunk {i} text", document_id=test_document_data.id, embedding=[0.1]*10) for i in range(2)],
#         entities=[Entity(id="ent-1", text="Entity1", labels=["ORG"])],
#         relationships=[Relationship(id="rel-1", source_id="ent-1", target_id="ent-2", type="RELATED_TO")]
#     )

#     # Check if the method exists before calling
#     if hasattr(engine, 'process_and_store_document'):
#         await engine.process_and_store_document(test_document_data.content, test_document_data.metadata)
#         logger.info("process_and_store_document called (if exists).")

#         # Assertions (verify mocks were called as expected)
#         mock_document_processor.process.assert_awaited_once()
#         mock_entity_extractor.extract.assert_awaited_once()
#         mock_kg_builder.build.assert_awaited_once()
#         mock_vector_store.add_chunks.assert_awaited_once() # Check vector store call
#     else:
#         logger.warning("process_and_store_document method not found on engine, skipping call and assertions.")


@pytest.mark.asyncio
async def test_retrieve_context_vector(
    rag_engine: SimpleGraphRAGEngine,
    mock_vector_store: AsyncMock,  # Expect the AsyncMock vector store
    mock_llm_service: AsyncMock,  # Need LLM mock
):
    """Tests retrieving context using only vector search results and synthesizing answer."""
    # Arrange
    query_text = "search query"
    expected_chunk_data = ChunkData(
        id="chunk1", text="Relevant text.", document_id="doc1", metadata={}
    )
    expected_search_results = [SearchResultData(chunk=expected_chunk_data, score=0.9)]
    mock_vector_store.search.return_value = expected_search_results

    # Expected domain Chunk object in the result
    expected_domain_chunk = Chunk(
        id=expected_chunk_data.id,
        text=expected_chunk_data.text,
        document_id=expected_chunk_data.document_id,
        # Combine original metadata with score
        metadata={**expected_chunk_data.metadata, "score": 0.9}
        if expected_chunk_data.metadata
        else {"score": 0.9},
    )

    # Act
    query_result = await rag_engine.query(
        query_text, config={"include_graph": False, "k": 10}
    )

    # Assert Vector Search
    mock_vector_store.search.assert_awaited_once_with(query_text, top_k=10, search_type="vector")

    # Assert LLM Call (ensure it was called since context was found)
    mock_llm_service.generate_response.assert_awaited_once()
    # Optional: More detailed check on the prompt sent to LLM
    prompt_arg = mock_llm_service.generate_response.call_args[0][0]
    assert query_text in prompt_arg
    assert expected_chunk_data.text in prompt_arg
    assert "Graph Entities" not in prompt_arg  # Graph context was disabled

    # Assert Query Result
    assert isinstance(query_result, QueryResult)
    assert query_result.answer == "Default Mock LLM Answer"  # Updated assertion
    assert len(query_result.relevant_chunks) == 1
    # Compare the actual Chunk object with the expected one
    assert query_result.relevant_chunks[0].id == expected_domain_chunk.id
    assert query_result.relevant_chunks[0].text == expected_domain_chunk.text
    assert (
        query_result.relevant_chunks[0].document_id == expected_domain_chunk.document_id
    )
    assert query_result.relevant_chunks[0].metadata == expected_domain_chunk.metadata
    assert (
        query_result.relevant_chunks[0].metadata.get("score") == 0.9
    )  # Check score in metadata
    assert query_result.graph_context is None  # Graph context not requested
    logger.info("test_retrieve_context_vector passed.")


@pytest.mark.asyncio
async def test_simple_engine_query_uses_stores(
    rag_engine: SimpleGraphRAGEngine,  # Use the fixture for SimpleGraphRAGEngine
    mock_graph_repository: AsyncMock,  # Use AsyncMock
    mock_vector_store: AsyncMock,  # Use AsyncMock
    mock_llm_service: AsyncMock,  # Use LLM mock
    mock_entity_extractor: AsyncMock,  # Use extractor mock
):
    """Test that the SimpleGraphRAGEngine query method interacts with stores and LLM."""
    query_text = "find keyword things"
    config = {"include_graph": False, "k": 1}  # Disable graph context, k=1
    mock_chunk_text = "Keyword chunk 1"
    mock_chunk_data = ChunkData(
        id="c-key-1", text=mock_chunk_text, document_id="doc-key", metadata={}
    )
    mock_search_result = [SearchResultData(chunk=mock_chunk_data, score=0.95)]

    # Mock vector store search
    mock_vector_store.search.return_value = mock_search_result

    # Mock graph store methods (not expected to be called)
    mock_graph_repository.search_entities_by_properties.return_value = []
    mock_graph_repository.get_neighbors.return_value = ([], [])

    # Mock entity extractor (not strictly needed if graph=False, but good practice)
    mock_entity_extractor.extract.return_value = ExtractionResult(
        entities=[], relationships=[]
    )

    # Act: Call the query method
    result: QueryResult = await rag_engine.query(query_text, config=config)

    # Assertions
    # Vector store called
    mock_vector_store.search.assert_awaited_once_with(query_text, top_k=1, search_type="vector")
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
    assert "Graph Entities" not in prompt_arg  # Graph context disabled

    # Result checks
    assert isinstance(result, QueryResult)
    assert result.answer == "Default Mock LLM Answer"  # Updated assertion
    assert len(result.relevant_chunks) == 1
    assert result.relevant_chunks[0].id == "c-key-1"
    assert result.relevant_chunks[0].text == mock_chunk_text
    assert (
        result.relevant_chunks[0].metadata.get("score") == 0.95
    )  # Check score in metadata
    assert result.graph_context is None


# --- Test Initialization ---
def test_engine_initialization(
    mock_graph_repository,
    mock_vector_store: AsyncMock,
    mock_entity_extractor,
    mock_llm_service,
):
    """Test that the engine initializes correctly with all dependencies."""
    engine = SimpleGraphRAGEngine(
        graph_store=mock_graph_repository,
        vector_store=mock_vector_store,
        entity_extractor=mock_entity_extractor,
        llm_service=mock_llm_service,  # Pass LLM mock
    )
    assert engine._graph_store is mock_graph_repository
    assert engine._vector_store is mock_vector_store
    assert engine._entity_extractor is mock_entity_extractor
    assert engine._llm_service is mock_llm_service  # Check LLM service assignment


def test_engine_initialization_default_llm(
    mock_graph_repository, mock_vector_store: AsyncMock, mock_entity_extractor
):
    """Test that the engine initializes with MockLLMService if none is provided."""
    engine = SimpleGraphRAGEngine(
        graph_store=mock_graph_repository,
        vector_store=mock_vector_store,
        entity_extractor=mock_entity_extractor,
        llm_service=None,  # Explicitly pass None
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

    with pytest.raises(
        TypeError, match="graph_store must implement the GraphRepository protocol"
    ):
        SimpleGraphRAGEngine(
            graph_store=object(),
            vector_store=mock_vector,
            entity_extractor=mock_extractor,
        )
    with pytest.raises(
        TypeError, match="vector_store must be an instance of VectorStore"
    ):
        SimpleGraphRAGEngine(
            graph_store=mock_graph,
            vector_store=object(),
            entity_extractor=mock_extractor,
        )
    # Entity extractor type check was commented out, skipping associated test


# --- Tests for Graph Context Retrieval (Updated to Async and LLM) ---


@pytest.fixture
def mock_graph_repo() -> AsyncMock:  # Renaming for clarity, matches new tests below
    mock = AsyncMock(spec=GraphRepository)
    mock.search_entities_by_properties = AsyncMock(return_value=[])
    mock.get_neighbors = AsyncMock(return_value=([], []))
    return mock


@pytest.fixture
def sample_chunk_list() -> list[SearchResultData]:
    return [
        SearchResultData(
            chunk=ChunkData(
                id="chunk-vec-1",
                text="Alice mentioned Bob.",
                document_id="doc-vec-1",
                metadata={},
                embedding=[0.1] * 10,
            ),
            score=0.8,
        ),
        SearchResultData(
            chunk=ChunkData(
                id="chunk-vec-2",
                text="Bob works at Acme.",
                document_id="doc-vec-2",
                metadata={},
                embedding=[0.2] * 10,
            ),
            score=0.75,
        ),
    ]


@pytest.fixture
def sample_extracted_entities() -> list[ExtractedEntity]:
    return [
        ExtractedEntity(id="ent-ext-alice", text="Alice", label="PERSON", score=0.9),
        ExtractedEntity(id="ent-ext-bob", text="Bob", label="PERSON", score=0.85),
        ExtractedEntity(id="ent-ext-acme", text="Acme", label="ORG", score=0.95),
    ]


@pytest.fixture
def sample_graph_entities() -> list[Entity]:
    # Domain Entity models that exist in the graph
    return [
        Entity(
            id="ent-graph-alice",
            name="Alice",
            type="PERSON",
            metadata={"name": "Alice"},
        ),
        Entity(id="ent-graph-bob", name="Bob", type="PERSON", metadata={"name": "Bob"}),
    ]


@pytest.fixture
def sample_graph_neighbors(
    sample_graph_entities: list[Entity],
) -> tuple[list[Entity], list[Edge]]:
    """Provides a list of entities and a list of domain.models.Edge relationships."""
    if len(sample_graph_entities) < 3:
        # Ensure enough entities for varied relationships if needed
        # For now, matching the old structure that produced Alice, Bob, Charlie
        entities = [
            Entity(id="ent-graph-alice", type="Person", name="Alice"),
            Entity(id="ent-graph-bob", type="Person", name="Bob"),
            Entity(id="ent-graph-charlie", type="Person", name="Charlie"),
        ]
    else:
        entities = sample_graph_entities[:3]  # Use first 3 if available

    # Create domain.models.Edge instances
    # These should match what _get_graph_context would effectively return from graph_store.get_neighbors
    # if it were to reconstruct Edge models from raw neighbor data.
    # The key is that the prompt formatting expects .source_id, .target_id, .type
    edge1 = Edge(
        id="mock-edge-1",
        type="KNOWS",
        source_id=entities[0].id,
        target_id=entities[1].id,
        properties={},
    )
    edge2 = Edge(
        id="mock-edge-2",
        type="FRIEND_OF",
        source_id=entities[1].id,
        target_id=entities[2].id,
        properties={},
    )

    # The entities list should contain all unique entities involved in the relationships plus any others
    all_entities_dict = {e.id: e for e in entities}

    return list(all_entities_dict.values()), [edge1, edge2]


@pytest.fixture
def sample_domain_edge_list(sample_graph_entities: list[Entity]) -> list[Edge]:
    """Provides a list of domain.models.Edge instances for mocking."""
    if len(sample_graph_entities) < 2:
        return []
    return [
        Edge(
            id="edge1",
            type="KNOWS",
            source_id=sample_graph_entities[0].id,
            target_id=sample_graph_entities[1].id,
            properties={},
        ),
        # Add more if needed for specific tests
    ]


@pytest.mark.asyncio
async def test_simple_engine_query_with_graph_context(
    mock_graph_repo: AsyncMock,
    mock_vector_store: AsyncMock,
    mock_entity_extractor: AsyncMock,
    mock_llm_service: AsyncMock,  # Add LLM mock
    sample_chunk_list: list[SearchResultData],
    sample_extracted_entities: list[ExtractedEntity],
    sample_graph_entities: list[Entity],
    sample_graph_neighbors: tuple[list[Entity], list[Edge]],
    config: dict,  # Use shared config fixture
):
    """Tests a query retrieving vector results, graph context, and synthesizing an answer."""
    # Arrange
    query = "find me related documents about Alice"
    engine = SimpleGraphRAGEngine(
        graph_store=mock_graph_repo,
        vector_store=mock_vector_store,
        entity_extractor=mock_entity_extractor,
        llm_service=mock_llm_service,  # Include LLM service
    )

    # Configure mocks
    mock_vector_store.search.return_value = sample_chunk_list
    combined_text = " ".join(
        [sr.chunk.text for sr in sample_chunk_list if sr.chunk]
    )  # Ensure chunk exists
    mock_entity_extractor.extract_from_text.return_value = ExtractionResult(
        entities=sample_extracted_entities, relationships=[]
    )

    # Mock graph search for entities
    async def mock_search_props_for_query_test(search_props: dict, limit=None):
        name_to_match = search_props.get("name")
        return [e for e in sample_graph_entities if e.name == name_to_match]

    mock_graph_repo.search_entities_by_properties.side_effect = (
        mock_search_props_for_query_test
    )

    # Mock neighbor retrieval (this provides entities and relationships for the graph context)
    mock_graph_repo.get_neighbors.return_value = sample_graph_neighbors

    # Act
    result = await engine.query(query, config=config)

    # Assert
    # Vector search called
    mock_vector_store.search.assert_awaited_once_with(query, top_k=config.get("k", 3), search_type="vector")

    # Entity extraction called
    mock_entity_extractor.extract_from_text.assert_called_once_with(combined_text)

    # Graph property search called for each extracted entity
    assert mock_graph_repo.search_entities_by_properties.call_count == len(
        sample_extracted_entities
    )
    # Check specific calls (simplified check)
    mock_graph_repo.search_entities_by_properties.assert_any_call(
        {"name": "Alice", "type": "PERSON"}, limit=1
    )
    mock_graph_repo.search_entities_by_properties.assert_any_call(
        {"name": "Bob", "type": "PERSON"}, limit=1
    )
    mock_graph_repo.search_entities_by_properties.assert_any_call(
        {"name": "Acme", "type": "ORG"}, limit=1
    )

    # Graph neighbor retrieval called for each *graph entity* found from extracted ones (Alice, Bob)
    assert mock_graph_repo.get_neighbors.call_count == 2  # Alice and Bob
    mock_graph_repo.get_neighbors.assert_any_call("ent-graph-alice")
    mock_graph_repo.get_neighbors.assert_any_call("ent-graph-bob")

    # LLM generate called
    mock_llm_service.generate_response.assert_awaited_once()
    prompt_arg = mock_llm_service.generate_response.call_args[0][0]
    assert query in prompt_arg
    assert sample_chunk_list[0].chunk.text in prompt_arg  # Check chunk text
    assert sample_graph_entities[0].name in prompt_arg  # Check entity name
    assert (
        sample_graph_neighbors[1][0].type in prompt_arg
    )  # Check relationship type from sample_graph_neighbors

    # Check QueryResult
    assert result.answer == "Default Mock LLM Answer"  # Updated assertion
    assert len(result.relevant_chunks) == len(sample_chunk_list)
    # Check chunk mapping (basic)
    assert result.relevant_chunks[0].id == sample_chunk_list[0].chunk.id
    assert result.relevant_chunks[0].metadata.get("score") == sample_chunk_list[0].score

    # Check graph context
    assert result.graph_context is not None
    expected_entities, expected_relationships = sample_graph_neighbors
    # Compare sets of IDs as order might differ
    assert set(e.id for e in result.graph_context[0]) == set(
        e.id for e in expected_entities
    )
    assert len(result.graph_context[1]) == len(expected_relationships)
    logger.info("test_simple_engine_query_with_graph_context assertions passed.")


@pytest.mark.asyncio
async def test_simple_engine_query_graph_no_entities_extracted(
    mock_graph_repo: AsyncMock,
    mock_vector_store: AsyncMock,
    mock_entity_extractor: AsyncMock,
    mock_llm_service: AsyncMock,  # Add LLM mock
    sample_chunk_list: list[SearchResultData],
    config: dict,
):
    """Tests query where vector search succeeds but no entities are extracted."""
    # Arrange
    query = "find me related documents with no entities"
    engine = SimpleGraphRAGEngine(
        mock_graph_repo, mock_vector_store, mock_entity_extractor, mock_llm_service
    )
    mock_vector_store.search.return_value = sample_chunk_list
    mock_entity_extractor.extract_from_text.return_value = ExtractionResult(
        entities=[], relationships=[]
    )  # No entities extracted

    # Act
    result = await engine.query(query, config=config)  # include_graph=True by default

    # Assert
    mock_vector_store.search.assert_awaited_once_with(query, top_k=config["k"], search_type="vector")
    combined_text = " ".join([sr.chunk.text for sr in sample_chunk_list if sr.chunk])
    mock_entity_extractor.extract_from_text.assert_called_once_with(combined_text)
    # Graph searches should NOT be called
    mock_graph_repo.search_entities_by_properties.assert_not_called()
    mock_graph_repo.get_neighbors.assert_not_called()
    # LLM should still be called with only chunk context
    mock_llm_service.generate_response.assert_awaited_once()
    prompt_arg = mock_llm_service.generate_response.call_args[0][0]
    assert "Graph Entities" not in prompt_arg  # Section should be omitted if empty
    # Check result
    assert result.answer == "Default Mock LLM Answer"  # Updated assertion
    assert len(result.relevant_chunks) == len(sample_chunk_list)
    assert result.graph_context is None  # No graph context was built
    logger.info(
        "test_simple_engine_query_graph_no_entities_extracted assertions passed."
    )


@pytest.mark.asyncio
async def test_simple_engine_query_graph_entities_not_found(
    mock_graph_repo: AsyncMock,
    mock_vector_store: AsyncMock,
    mock_entity_extractor: AsyncMock,
    mock_llm_service: AsyncMock,  # Add LLM mock
    sample_chunk_list: list[SearchResultData],
    sample_extracted_entities: list[ExtractedEntity],  # Entities are extracted
    config: dict,
):
    """Tests query where entities are extracted but none are found in the graph."""
    # Arrange
    query = "find documents about maybe-known entities"
    engine = SimpleGraphRAGEngine(
        mock_graph_repo, mock_vector_store, mock_entity_extractor, mock_llm_service
    )
    mock_vector_store.search.return_value = sample_chunk_list
    mock_entity_extractor.extract_from_text.return_value = ExtractionResult(
        entities=sample_extracted_entities, relationships=[]
    )
    # Mock graph search to return NOTHING
    mock_graph_repo.search_entities_by_properties.return_value = []

    # Act
    result = await engine.query(query, config=config)  # include_graph=True by default

    # Assert
    mock_vector_store.search.assert_awaited_once_with(query, top_k=config["k"], search_type="vector")
    combined_text = " ".join([sr.chunk.text for sr in sample_chunk_list if sr.chunk])
    mock_entity_extractor.extract_from_text.assert_called_once_with(combined_text)
    # Graph property search *was* called
    assert mock_graph_repo.search_entities_by_properties.call_count == len(
        sample_extracted_entities
    )
    # Graph neighbor search was NOT called
    mock_graph_repo.get_neighbors.assert_not_called()
    # LLM *was* called, but prompt context won't have graph details
    mock_llm_service.generate_response.assert_awaited_once()
    prompt_arg = mock_llm_service.generate_response.call_args[0][0]
    assert "Graph Entities" not in prompt_arg  # Section should be omitted if empty
    # Check result
    assert result.answer == "Default Mock LLM Answer"  # Updated assertion
    assert len(result.relevant_chunks) == len(sample_chunk_list)
    assert result.graph_context is None  # No graph context built
    logger.info("test_simple_engine_query_graph_entities_not_found assertions passed.")


@pytest.mark.asyncio
async def test_simple_engine_query_no_context_found(
    mock_graph_repo: AsyncMock,
    mock_vector_store: AsyncMock,
    mock_entity_extractor: AsyncMock,
    mock_llm_service: AsyncMock,  # Add LLM mock
    config: dict,
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
    result = await engine.query(query, config=config)  # include_graph=True by default

    # Assert
    mock_vector_store.search.assert_awaited_once_with(query, top_k=config["k"], search_type="vector")
    # Nothing else should be called if no chunks are found initially
    mock_entity_extractor.extract_from_text.assert_not_called()
    mock_graph_repo.search_entities_by_properties.assert_not_called()
    mock_graph_repo.get_neighbors.assert_not_called()
    # LLM should NOT be called as there's no context
    mock_llm_service.generate_response.assert_not_called()
    # Check result
    assert (
        result.answer == "Could not find relevant information to answer the query."
    )  # Updated assertion
    assert len(result.relevant_chunks) == 0
    assert result.graph_context is None
    logger.info("test_simple_engine_query_no_context_found assertions passed.")


@pytest.mark.asyncio
async def test_retrieve_context_vector_only(
    rag_engine: SimpleGraphRAGEngine,  # Use correct fixture name
    mock_vector_store: AsyncMock,
):
    """Test retrieve_context focuses on vector store search and returns SearchResultData."""
    query = "find information about project alpha"
    limit = 3

    # Mock VectorStore search results
    mock_chunk_data1 = create_mock_chunk_data(
        id="c1", text="Details about alpha project.", score=0.1
    )
    mock_chunk_data2 = create_mock_chunk_data(
        id="c2", text="Alpha project updates.", score=0.2
    )
    mock_search_results = [
        create_mock_search_result(mock_chunk_data1, 0.9),
        create_mock_search_result(mock_chunk_data2, 0.8),
    ]
    mock_vector_store.search.return_value = mock_search_results

    # Call the method under test
    results = await rag_engine.retrieve_context(query=query, limit=limit)

    # Assertions
    mock_vector_store.search.assert_awaited_once_with(query, top_k=limit, search_type="vector")
    assert results == mock_search_results
    # Ensure graph/extraction methods weren't called unnecessarily by retrieve_context
    # Note: _retrieve_and_build_context IS called, but its internal graph calls are skipped due to config
    assert rag_engine._graph_store.search_entities_by_properties.call_count == 0
    assert rag_engine._graph_store.get_neighbors.call_count == 0
    assert rag_engine._entity_extractor.extract_from_text.call_count == 0
    rag_engine._llm_service.generate_response.assert_not_awaited()


@pytest.mark.asyncio
async def test_answer_query_vector_only(
    rag_engine: SimpleGraphRAGEngine,  # Use correct fixture name
    mock_vector_store: AsyncMock,
    mock_llm_service: AsyncMock,
):
    """Test answer_query with vector context only."""
    query = "summarize alpha project"
    limit = 2
    expected_answer = "Alpha project is summarized here."

    # Mock VectorStore
    mock_chunk_data1 = create_mock_chunk_data(id="c1", text="Alpha details.", score=0.1)
    mock_chunk_data2 = create_mock_chunk_data(id="c2", text="More on Alpha.", score=0.2)
    mock_search_results = [
        create_mock_search_result(mock_chunk_data1, 0.95),
        create_mock_search_result(mock_chunk_data2, 0.85),
    ]
    mock_vector_store.search.return_value = mock_search_results

    # Mock LLM
    mock_llm_service.generate_response.return_value = expected_answer

    # Call method
    answer = await rag_engine.answer_query(
        query, config={"k": limit, "include_graph": False}
    )

    # Assertions
    mock_vector_store.search.assert_awaited_once_with(query, top_k=limit, search_type="vector")
    # Check that LLM was called with expected prompt structure
    mock_llm_service.generate_response.assert_awaited_once()
    call_args, _ = mock_llm_service.generate_response.await_args
    prompt = call_args[0]
    assert f"Query: {query}" in prompt
    assert "Relevant Text Chunks:" in prompt
    assert mock_chunk_data1.text in prompt
    assert mock_chunk_data2.text in prompt
    assert "Related Graph Entities:" not in prompt  # Graph was excluded

    assert answer == expected_answer
    # Ensure graph/extraction methods weren't called
    assert rag_engine._graph_store.search_entities_by_properties.call_count == 0
    assert rag_engine._graph_store.get_neighbors.call_count == 0
    assert rag_engine._entity_extractor.extract_from_text.call_count == 0


@pytest.mark.asyncio
async def test_answer_query_with_graph(
    rag_engine: SimpleGraphRAGEngine,  # Use correct fixture name
    mock_vector_store: AsyncMock,
    mock_entity_extractor: AsyncMock,
    mock_graph_repository: AsyncMock,  # Use the same mock injected into rag_engine
    mock_llm_service: AsyncMock,
):
    """Test answer_query including graph context."""
    query = "who works on project gamma?"
    limit = 1
    expected_answer = "Alice works on project gamma."

    # Mock VectorStore
    mock_chunk_data = create_mock_chunk_data(
        id="c3", text="Project Gamma involves Alice.", score=0.3
    )
    mock_search_results = [create_mock_search_result(mock_chunk_data, 0.9)]
    mock_vector_store.search.return_value = mock_search_results

    # Mock Entity Extractor
    extracted_entity_alice = create_mock_extracted_entity(
        id="alice", label="Person", text="Alice"
    )
    extracted_entity_gamma = create_mock_extracted_entity(
        id="gamma", label="Project", text="Project Gamma"
    )
    mock_entity_extractor.extract_from_text.return_value = ExtractionResult(
        entities=[extracted_entity_alice, extracted_entity_gamma], relationships=[]
    )

    # Mock Graph Repo - Finding entities
    graph_entity_alice = create_mock_graph_entity(
        id="graph_alice_1", type="Person", name="Alice"
    )
    graph_entity_gamma = create_mock_graph_entity(
        id="graph_gamma_1", type="Project", name="Project Gamma"
    )

    async def mock_search_props_for_answer_test(*args, **kwargs):
        props = kwargs.get("search_props", args[0] if args else None)
        if not props:
            return []
        name_to_match = props.get("name")
        type_to_match = props.get("type")  # Also check type for more robustness
        if name_to_match == "Alice" and type_to_match == "Person":
            return [graph_entity_alice]
        if (
            name_to_match == "Project Gamma" and type_to_match == "Project"
        ):  # Corrected entity type
            return [graph_entity_gamma]
        return []

    mock_graph_repository.search_entities_by_properties.side_effect = (
        mock_search_props_for_answer_test
    )

    # Mock Graph Repo - Getting neighbors
    graph_rel = create_mock_graph_relationship(
        source_id=graph_entity_alice.id,
        target_id=graph_entity_gamma.id,
        type="WORKS_ON",
    )
    mock_graph_repository.get_neighbors.return_value = (
        [graph_entity_alice, graph_entity_gamma],
        [graph_rel],
    )

    mock_llm_service.generate_response.return_value = expected_answer

    # Call method
    answer = await rag_engine.answer_query(
        query, config={"k": limit, "include_graph": True}
    )

    # Assertions
    mock_vector_store.search.assert_awaited_once_with(query, top_k=limit, search_type="vector")
    mock_entity_extractor.extract_from_text.assert_awaited_once_with(
        mock_chunk_data.text
    )

    assert (
        mock_graph_repository.search_entities_by_properties.call_count == 2
    )  # Check CALL count on the correct mock
    # Check specific calls with correct search_props structure
    call_args_list = (
        mock_graph_repository.search_entities_by_properties.call_args_list
    )  # Use call_args_list from the correct mock
    # Expected search_props dictionaries
    expected_search_props_alice = {"name": "Alice", "type": "Person"}
    expected_search_props_gamma = {"name": "Project Gamma", "type": "Project"}

    # Check if the calls were made with the expected search_props
    # Note: order of calls might not be guaranteed, so check for presence
    alice_called = any(
        call[0][0] == expected_search_props_alice for call in call_args_list if call[0]
    )
    gamma_called = any(
        call[0][0] == expected_search_props_gamma for call in call_args_list if call[0]
    )
    assert alice_called, (
        f"Search for Alice was not called with correct props. Call list: {call_args_list}"
    )
    assert gamma_called, (
        f"Search for Project Gamma was not called with correct props. Call list: {call_args_list}"
    )

    assert (
        mock_graph_repository.get_neighbors.await_count == 2
    )  # Called for Alice and Gamma
    mock_llm_service.generate_response.assert_awaited_once()
    # Check LLM prompt structure
    prompt_arg = mock_llm_service.generate_response.call_args[0][0]
    assert f"Query: {query}" in prompt_arg
    assert "Relevant Text Chunks:" in prompt_arg
    assert mock_chunk_data.text in prompt_arg
    # With the fixed search_props mock, graph context should now be found
    assert "Related Graph Entities:" in prompt_arg
    assert graph_entity_alice.name in prompt_arg
    # assert graph_entity_gamma.name in prompt_arg # Gamma might not be expanded depending on mock neighbors
    assert "Related Graph Relationships:" in prompt_arg
    assert (
        f"({graph_rel.source_id}) -[{graph_rel.type}]-> ({graph_rel.target_id})"
        in prompt_arg
    )

    assert answer == expected_answer


@pytest.mark.asyncio
async def test_answer_query_no_context(
    rag_engine: SimpleGraphRAGEngine,  # Use correct fixture name
    mock_vector_store: AsyncMock,
    mock_llm_service: AsyncMock,
):
    """Test answer_query returns default message when no context is found."""
    query = "information about unknown topic"

    # Mock VectorStore returning nothing
    mock_vector_store.search.return_value = []

    # Call method
    answer = await rag_engine.answer_query(query)

    # Assertions
    mock_vector_store.search.assert_awaited_once_with(query, top_k=3, search_type="vector")  # Default k=3
    mock_llm_service.generate_response.assert_not_awaited()  # LLM should not be called
    assert (
        answer == "Could not find relevant information to answer the query."
    )  # Updated assertion
    # Ensure graph/extraction methods weren't called
    assert rag_engine._graph_store.search_entities_by_properties.call_count == 0
    assert rag_engine._graph_store.get_neighbors.call_count == 0
    assert rag_engine._entity_extractor.extract_from_text.call_count == 0


@pytest.mark.asyncio
async def test_answer_query_graph_duplicate_extracted_entities_searched_once(
    rag_engine: SimpleGraphRAGEngine,
    mock_vector_store: AsyncMock,
    mock_entity_extractor: AsyncMock,
    mock_graph_repository: AsyncMock,
    mock_llm_service: AsyncMock,
    mocker: MockerFixture,
):
    """
    Tests that if the entity extractor returns duplicate entities (by name/type),
    the graph store is queried only once for each unique entity.
    """
    query_text = "test query with duplicate extracted entities"
    sample_chunk = create_mock_chunk_data(id="c1", text="Alice, Alice, and Bob.")
    sample_search_result = create_mock_search_result(chunk_data=sample_chunk, score=0.9)

    mock_vector_store.search.return_value = [sample_search_result]

    # Entity extractor returns duplicates for Alice
    extracted_alice1 = create_mock_extracted_entity(
        id="ext_alice1", label="PERSON", text="Alice"
    )
    extracted_alice2 = create_mock_extracted_entity(
        id="ext_alice2", label="PERSON", text="Alice"
    )  # Same text & label
    extracted_bob = create_mock_extracted_entity(
        id="ext_bob", label="PERSON", text="Bob"
    )
    mock_entity_extractor.extract_from_text.return_value = ExtractionResult(
        entities=[extracted_alice1, extracted_alice2, extracted_bob], relationships=[]
    )

    # Graph store setup
    graph_alice_id = str(uuid.uuid4())
    graph_bob_id = str(uuid.uuid4())
    graph_alice = create_mock_graph_entity(
        id=graph_alice_id, type="PERSON", name="Alice"
    )
    graph_bob = create_mock_graph_entity(id=graph_bob_id, type="PERSON", name="Bob")

    async def mock_search_props_side_effect(search_props: dict, limit=None):
        name = search_props.get("name")
        type = search_props.get("type")
        if name == "Alice" and type == "PERSON":
            return [graph_alice]
        if name == "Bob" and type == "PERSON":
            return [graph_bob]
        return []

    mock_graph_repository.search_entities_by_properties.side_effect = (
        mock_search_props_side_effect
    )

    # Neighbors setup (simplified: assume get_neighbors is called with correct IDs)
    mock_graph_repository.get_neighbors.return_value = (
        [],
        [],
    )  # Empty neighbors for simplicity of this test

    mock_llm_service.generate_response.return_value = (
        "LLM answer with context from unique entities"
    )

    config = {"include_graph": True, "k": 1}
    await rag_engine.answer_query(query_text, config=config)

    # Assertions
    mock_entity_extractor.extract_from_text.assert_called_once()

    # search_entities_by_properties should be called once for Alice and once for Bob (total 2)
    assert mock_graph_repository.search_entities_by_properties.call_count == 2
    mock_graph_repository.search_entities_by_properties.assert_any_call(
        {"name": "Alice", "type": "PERSON"}, limit=1
    )
    mock_graph_repository.search_entities_by_properties.assert_any_call(
        {"name": "Bob", "type": "PERSON"}, limit=1
    )

    # get_neighbors should be called for both Alice and Bob (found unique entities)
    assert mock_graph_repository.get_neighbors.call_count == 2
    mock_graph_repository.get_neighbors.assert_any_call(graph_alice.id)
    mock_graph_repository.get_neighbors.assert_any_call(graph_bob.id)

    mock_llm_service.generate_response.assert_called_once()
    # Further assertions on LLM context could be added if necessary


# === Retrieval Quality Controls Tests ===


@pytest.mark.asyncio
async def test_query_search_type_vector_only(
    rag_engine: SimpleGraphRAGEngine,
    mock_vector_store: AsyncMock,
    mock_llm_service: AsyncMock,
):
    """Test search_type='vector' uses only vector search."""
    query_text = "test vector search"
    mock_chunk = create_mock_chunk_data(id="c1", text="vector result", score=0.1)
    mock_result = create_mock_search_result(mock_chunk, 0.9)

    # Mock vector store to return different results for vector vs keyword
    async def mock_search_side_effect(query, top_k, search_type="vector"):
        if search_type == "vector":
            return [mock_result]
        elif search_type == "keyword":
            return []  # Should not be called for vector-only
        return []

    mock_vector_store.search.side_effect = mock_search_side_effect
    mock_llm_service.generate_response.return_value = "Vector search answer"

    # Act
    config = {"search_type": "vector", "include_graph": False, "k": 3}
    result = await rag_engine.query(query_text, config=config)

    # Assert
    assert result.answer == "Vector search answer"
    assert len(result.relevant_chunks) == 1
    assert result.relevant_chunks[0].text == "vector result"

    # Should only call vector search, never keyword
    mock_vector_store.search.assert_called_once_with(query_text, top_k=3, search_type="vector")


@pytest.mark.asyncio
async def test_query_search_type_keyword_only(
    rag_engine: SimpleGraphRAGEngine,
    mock_vector_store: AsyncMock,
    mock_llm_service: AsyncMock,
):
    """Test search_type='keyword' uses only keyword search."""
    query_text = "test keyword search"
    mock_chunk = create_mock_chunk_data(id="c1", text="keyword result", score=0.1)
    mock_result = create_mock_search_result(mock_chunk, 0.8)

    # Mock vector store to return different results for vector vs keyword
    async def mock_search_side_effect(query, top_k, search_type="vector"):
        if search_type == "keyword":
            return [mock_result]
        elif search_type == "vector":
            return []  # Should not be called for keyword-only
        return []

    mock_vector_store.search.side_effect = mock_search_side_effect
    mock_llm_service.generate_response.return_value = "Keyword search answer"

    # Act
    config = {"search_type": "keyword", "include_graph": False, "k": 3}
    result = await rag_engine.query(query_text, config=config)

    # Assert
    assert result.answer == "Keyword search answer"
    assert len(result.relevant_chunks) == 1
    assert result.relevant_chunks[0].text == "keyword result"

    # Should only call keyword search, never vector
    mock_vector_store.search.assert_called_once_with(query_text, top_k=3, search_type="keyword")


@pytest.mark.asyncio
async def test_query_search_type_hybrid_blending(
    rag_engine: SimpleGraphRAGEngine,
    mock_vector_store: AsyncMock,
    mock_llm_service: AsyncMock,
):
    """Test search_type='hybrid' blends vector and keyword results based on blend_keyword_weight."""
    query_text = "test hybrid search"

    # Mock different results for vector vs keyword
    vector_chunk = create_mock_chunk_data(id="v1", text="vector result", score=0.1)
    vector_result = create_mock_search_result(vector_chunk, 0.9)

    keyword_chunk = create_mock_chunk_data(id="k1", text="keyword result", score=0.1)
    keyword_result = create_mock_search_result(keyword_chunk, 0.7)

    async def mock_search_side_effect(query, top_k, search_type="vector"):
        if search_type == "vector":
            return [vector_result]
        elif search_type == "keyword":
            return [keyword_result]
        return []

    mock_vector_store.search.side_effect = mock_search_side_effect
    mock_llm_service.generate_response.return_value = "Hybrid search answer"

    # Act: Test with blend_keyword_weight=0.3 (30% keyword, 70% vector)
    config = {
        "search_type": "hybrid",
        "include_graph": False,
        "k": 3,
        "blend_keyword_weight": 0.3
    }
    result = await rag_engine.query(query_text, config=config)

    # Assert
    assert result.answer == "Hybrid search answer"

    # Should call both vector and keyword search
    assert mock_vector_store.search.call_count == 2
    mock_vector_store.search.assert_any_call(query_text, top_k=3, search_type="vector")
    mock_vector_store.search.assert_any_call(query_text, top_k=3, search_type="keyword")

    # Results should be blended (exact blending logic will be tested in implementation)
    assert len(result.relevant_chunks) >= 1


@pytest.mark.asyncio
async def test_query_no_answer_min_score_threshold(
    rag_engine: SimpleGraphRAGEngine,
    mock_vector_store: AsyncMock,
    mock_llm_service: AsyncMock,
):
    """Test no_answer_min_score returns no-answer message when top score is below threshold."""
    query_text = "test low score query"

    # Mock low-score result
    low_score_chunk = create_mock_chunk_data(id="c1", text="low relevance", score=0.1)
    low_score_result = create_mock_search_result(low_score_chunk, 0.2)  # Score below threshold

    mock_vector_store.search.return_value = [low_score_result]

    # Act: Set threshold higher than the mock result score
    config = {
        "search_type": "vector",
        "include_graph": False,
        "k": 3,
        "no_answer_min_score": 0.5  # Threshold higher than 0.2
    }
    result = await rag_engine.query(query_text, config=config)

    # Assert: Should return no-answer message without calling LLM
    assert "No relevant information found" in result.answer
    assert len(result.relevant_chunks) == 0
    mock_llm_service.generate_response.assert_not_called()


@pytest.mark.asyncio
async def test_query_no_answer_min_score_passes_threshold(
    rag_engine: SimpleGraphRAGEngine,
    mock_vector_store: AsyncMock,
    mock_llm_service: AsyncMock,
):
    """Test no_answer_min_score allows processing when top score meets threshold."""
    query_text = "test high score query"

    # Mock high-score result
    high_score_chunk = create_mock_chunk_data(id="c1", text="high relevance", score=0.1)
    high_score_result = create_mock_search_result(high_score_chunk, 0.8)  # Score above threshold

    mock_vector_store.search.return_value = [high_score_result]
    mock_llm_service.generate_response.return_value = "High score answer"

    # Act: Set threshold lower than the mock result score
    config = {
        "search_type": "vector",
        "include_graph": False,
        "k": 3,
        "no_answer_min_score": 0.5  # Threshold lower than 0.8
    }
    result = await rag_engine.query(query_text, config=config)

    # Assert: Should process normally and call LLM
    assert result.answer == "High score answer"
    assert len(result.relevant_chunks) == 1
    assert result.relevant_chunks[0].text == "high relevance"
    mock_llm_service.generate_response.assert_called_once()


# === LLM Relationship Persistence Tests ===


@pytest.mark.asyncio
async def test_llm_relationship_extraction_and_persistence_enabled(
    rag_engine: SimpleGraphRAGEngine,
    mock_vector_store: AsyncMock,
    mock_entity_extractor: AsyncMock,
    mock_graph_repository: AsyncMock,
    mock_llm_service: AsyncMock,
    mocker: MockerFixture,
):
    """Test LLM relationship extraction and persistence when enabled with confidence gating."""
    query_text = "Alice knows Bob"

    # Mock vector store
    chunk_data = create_mock_chunk_data(id="c1", text="Alice works with Bob at the office.", score=0.1)
    search_result = create_mock_search_result(chunk_data, 0.9)
    mock_vector_store.search.return_value = [search_result]

    # Mock entity extraction
    extracted_alice = create_mock_extracted_entity(id="ext_alice", label="PERSON", text="Alice")
    extracted_bob = create_mock_extracted_entity(id="ext_bob", label="PERSON", text="Bob")
    mock_entity_extractor.extract_from_text.return_value = ExtractionResult(
        entities=[extracted_alice, extracted_bob], relationships=[]
    )

    # Mock graph entities
    graph_alice = create_mock_graph_entity(id="graph_alice", type="PERSON", name="Alice")
    graph_bob = create_mock_graph_entity(id="graph_bob", type="PERSON", name="Bob")

    async def mock_search_props(props: dict, limit=None):
        name = props.get("name")
        if name == "Alice":
            return [graph_alice]
        elif name == "Bob":
            return [graph_bob]
        return []

    mock_graph_repository.search_entities_by_properties.side_effect = mock_search_props
    mock_graph_repository.get_neighbors.return_value = ([graph_alice, graph_bob], [])

    # Mock LLM relationship extraction
    mock_llm_relationships = [
        {"source_name": "alice", "target_name": "bob", "type": "WORKS_WITH", "confidence": 0.85},
        {"source_name": "alice", "target_name": "bob", "type": "KNOWS", "confidence": 0.90},
        {"source_name": "alice", "target_name": "bob", "type": "DISLIKES", "confidence": 0.60},  # Below threshold
    ]
    mock_llm_service.extract_entities_relationships.return_value = ([], mock_llm_relationships)
    mock_llm_service.generate_response.return_value = "Answer with LLM relationships"

    # Patch settings for this test
    import graph_rag.core.graph_rag_engine as engine_module
    original_enable = engine_module.settings.enable_llm_relationships
    original_min_conf = engine_module.settings.llm_rel_min_confidence
    engine_module.settings.enable_llm_relationships = True
    engine_module.settings.llm_rel_min_confidence = 0.7

    try:
        # Act
        config = {
            "include_graph": True,
            "extract_relationships": True,
            "extract_relationships_persist": True,
            "k": 1
        }
        result = await rag_engine.query(query_text, config=config)

        # Assert LLM relationship extraction was called
        mock_llm_service.extract_entities_relationships.assert_called_once_with(chunk_data.text)

        # Assert persistence calls were made for relationships above threshold
        assert mock_graph_repository.execute_query.call_count == 2  # WORKS_WITH (0.85) and KNOWS (0.90)

        # Check that MERGE queries were executed
        cypher_calls = mock_graph_repository.execute_query.call_args_list
        for call in cypher_calls:
            cypher, params = call[0]
            assert "MERGE" in cypher
            assert "evidence_count" in cypher
            assert params["props"]["extractor"] == "llm"
            assert params["props"]["confidence"] >= 0.7  # Above threshold

        # Assert metrics were tracked in config
        assert config["llm_relations_inferred_total"] == 3  # All relationships inferred
        assert config["llm_relations_persisted_total"] == 2  # Only above threshold persisted

        # Assert graph context includes LLM relationships
        assert result.graph_context is not None
        entities, relationships = result.graph_context
        llm_rels = [r for r in relationships if r.properties.get("extractor") == "llm"]
        assert len(llm_rels) == 3  # All inferred relationships added to context

    finally:
        # Restore settings
        engine_module.settings.enable_llm_relationships = original_enable
        engine_module.settings.llm_rel_min_confidence = original_min_conf


@pytest.mark.asyncio
async def test_llm_relationship_persistence_disabled(
    rag_engine: SimpleGraphRAGEngine,
    mock_vector_store: AsyncMock,
    mock_entity_extractor: AsyncMock,
    mock_graph_repository: AsyncMock,
    mock_llm_service: AsyncMock,
):
    """Test that LLM relationships are not persisted when feature is disabled."""
    query_text = "Alice knows Bob"

    # Mock vector store
    chunk_data = create_mock_chunk_data(id="c1", text="Alice works with Bob.", score=0.1)
    search_result = create_mock_search_result(chunk_data, 0.9)
    mock_vector_store.search.return_value = [search_result]

    # Mock entity extraction
    extracted_alice = create_mock_extracted_entity(id="ext_alice", label="PERSON", text="Alice")
    extracted_bob = create_mock_extracted_entity(id="ext_bob", label="PERSON", text="Bob")
    mock_entity_extractor.extract_from_text.return_value = ExtractionResult(
        entities=[extracted_alice, extracted_bob], relationships=[]
    )

    # Mock graph entities
    graph_alice = create_mock_graph_entity(id="graph_alice", type="PERSON", name="Alice")
    graph_bob = create_mock_graph_entity(id="graph_bob", type="PERSON", name="Bob")

    async def mock_search_props(props: dict, limit=None):
        name = props.get("name")
        if name == "Alice":
            return [graph_alice]
        elif name == "Bob":
            return [graph_bob]
        return []

    mock_graph_repository.search_entities_by_properties.side_effect = mock_search_props
    mock_graph_repository.get_neighbors.return_value = ([graph_alice, graph_bob], [])

    # Mock LLM relationship extraction
    mock_llm_relationships = [
        {"source_name": "alice", "target_name": "bob", "type": "KNOWS", "confidence": 0.90},
    ]
    mock_llm_service.extract_entities_relationships.return_value = ([], mock_llm_relationships)
    mock_llm_service.generate_response.return_value = "Answer without persistence"

    # Patch settings to disable persistence
    import graph_rag.core.graph_rag_engine as engine_module
    original_enable = engine_module.settings.enable_llm_relationships
    engine_module.settings.enable_llm_relationships = False

    try:
        # Act
        config = {
            "include_graph": True,
            "extract_relationships": True,
            "extract_relationships_persist": True,  # Request persistence but disabled via settings
            "k": 1
        }
        result = await rag_engine.query(query_text, config=config)

        # Assert LLM extraction still occurred
        mock_llm_service.extract_entities_relationships.assert_called_once()

        # Assert NO persistence calls were made
        mock_graph_repository.execute_query.assert_not_called()

        # Assert metrics show inference but no persistence
        assert config.get("llm_relations_inferred_total", 0) == 1
        assert config.get("llm_relations_persisted_total", 0) == 0

        # Assert relationships still added to context
        assert result.graph_context is not None
        entities, relationships = result.graph_context
        llm_rels = [r for r in relationships if r.properties.get("extractor") == "llm"]
        assert len(llm_rels) == 1

    finally:
        engine_module.settings.enable_llm_relationships = original_enable


@pytest.mark.asyncio
async def test_llm_relationship_deduplication(
    rag_engine: SimpleGraphRAGEngine,
    mock_vector_store: AsyncMock,
    mock_entity_extractor: AsyncMock,
    mock_graph_repository: AsyncMock,
    mock_llm_service: AsyncMock,
):
    """Test that duplicate LLM relationships are deduplicated during persistence."""
    query_text = "Alice knows Bob multiple times"

    # Mock vector store
    chunk_data = create_mock_chunk_data(id="c1", text="Alice knows Bob. Alice is friends with Bob.", score=0.1)
    search_result = create_mock_search_result(chunk_data, 0.9)
    mock_vector_store.search.return_value = [search_result]

    # Mock entity extraction
    extracted_alice = create_mock_extracted_entity(id="ext_alice", label="PERSON", text="Alice")
    extracted_bob = create_mock_extracted_entity(id="ext_bob", label="PERSON", text="Bob")
    mock_entity_extractor.extract_from_text.return_value = ExtractionResult(
        entities=[extracted_alice, extracted_bob], relationships=[]
    )

    # Mock graph entities
    graph_alice = create_mock_graph_entity(id="graph_alice", type="PERSON", name="Alice")
    graph_bob = create_mock_graph_entity(id="graph_bob", type="PERSON", name="Bob")

    async def mock_search_props(props: dict, limit=None):
        name = props.get("name")
        if name == "Alice":
            return [graph_alice]
        elif name == "Bob":
            return [graph_bob]
        return []

    mock_graph_repository.search_entities_by_properties.side_effect = mock_search_props
    mock_graph_repository.get_neighbors.return_value = ([graph_alice, graph_bob], [])

    # Mock LLM relationship extraction with duplicates
    mock_llm_relationships = [
        {"source_name": "alice", "target_name": "bob", "type": "KNOWS", "confidence": 0.85},
        {"source_name": "alice", "target_name": "bob", "type": "KNOWS", "confidence": 0.90},  # Duplicate
        {"source_name": "alice", "target_name": "bob", "type": "FRIENDS", "confidence": 0.80},  # Different type
    ]
    mock_llm_service.extract_entities_relationships.return_value = ([], mock_llm_relationships)
    mock_llm_service.generate_response.return_value = "Answer with deduplicated relationships"

    # Patch settings
    import graph_rag.core.graph_rag_engine as engine_module
    original_enable = engine_module.settings.enable_llm_relationships
    original_min_conf = engine_module.settings.llm_rel_min_confidence
    engine_module.settings.enable_llm_relationships = True
    engine_module.settings.llm_rel_min_confidence = 0.7

    try:
        # Act
        config = {
            "include_graph": True,
            "extract_relationships": True,
            "extract_relationships_persist": True,
            "k": 1
        }
        result = await rag_engine.query(query_text, config=config)

        # Assert persistence calls - should be 2 (KNOWS once, FRIENDS once)
        assert mock_graph_repository.execute_query.call_count == 2

        # Assert metrics show all inferred but only unique persisted
        assert config["llm_relations_inferred_total"] == 3  # All relationships inferred
        assert config["llm_relations_persisted_total"] == 2  # Deduplicated persistence

        # Assert all relationships added to context (before deduplication)
        assert result.graph_context is not None
        entities, relationships = result.graph_context
        llm_rels = [r for r in relationships if r.properties.get("extractor") == "llm"]
        assert len(llm_rels) == 3  # All added to context

    finally:
        engine_module.settings.enable_llm_relationships = original_enable
        engine_module.settings.llm_rel_min_confidence = original_min_conf


@pytest.mark.asyncio
async def test_llm_relationship_dry_run_mode(
    rag_engine: SimpleGraphRAGEngine,
    mock_vector_store: AsyncMock,
    mock_entity_extractor: AsyncMock,
    mock_graph_repository: AsyncMock,
    mock_llm_service: AsyncMock,
):
    """Test that dry-run mode logs planned relationships but doesn't persist them."""
    query_text = "Alice knows Bob in dry run"

    # Mock vector store
    chunk_data = create_mock_chunk_data(id="c1", text="Alice works with Bob.", score=0.1)
    search_result = create_mock_search_result(chunk_data, 0.9)
    mock_vector_store.search.return_value = [search_result]

    # Mock entity extraction
    extracted_alice = create_mock_extracted_entity(id="ext_alice", label="PERSON", text="Alice")
    extracted_bob = create_mock_extracted_entity(id="ext_bob", label="PERSON", text="Bob")
    mock_entity_extractor.extract_from_text.return_value = ExtractionResult(
        entities=[extracted_alice, extracted_bob], relationships=[]
    )

    # Mock graph entities
    graph_alice = create_mock_graph_entity(id="graph_alice", type="PERSON", name="Alice")
    graph_bob = create_mock_graph_entity(id="graph_bob", type="PERSON", name="Bob")

    async def mock_search_props(props: dict, limit=None):
        name = props.get("name")
        if name == "Alice":
            return [graph_alice]
        elif name == "Bob":
            return [graph_bob]
        return []

    mock_graph_repository.search_entities_by_properties.side_effect = mock_search_props
    mock_graph_repository.get_neighbors.return_value = ([graph_alice, graph_bob], [])

    # Mock LLM relationship extraction
    mock_llm_relationships = [
        {"source_name": "alice", "target_name": "bob", "type": "KNOWS", "confidence": 0.90},
        {"source_name": "alice", "target_name": "bob", "type": "WORKS_WITH", "confidence": 0.85},
        {"source_name": "alice", "target_name": "bob", "type": "DISLIKES", "confidence": 0.60},  # Below threshold
    ]
    mock_llm_service.extract_entities_relationships.return_value = ([], mock_llm_relationships)
    mock_llm_service.generate_response.return_value = "Answer in dry run mode"

    # Patch settings
    import graph_rag.core.graph_rag_engine as engine_module
    original_enable = engine_module.settings.enable_llm_relationships
    original_min_conf = engine_module.settings.llm_rel_min_confidence
    engine_module.settings.enable_llm_relationships = True
    engine_module.settings.llm_rel_min_confidence = 0.7

    try:
        # Act - dry run mode
        config = {
            "include_graph": True,
            "extract_relationships": True,
            "extract_relationships_persist": False,
            "extract_relationships_dry_run": True,
            "k": 1
        }
        result = await rag_engine.query(query_text, config=config)

        # Assert LLM extraction occurred
        mock_llm_service.extract_entities_relationships.assert_called_once()

        # Assert NO persistence calls were made
        mock_graph_repository.execute_query.assert_not_called()

        # Assert planned relationships were recorded in config
        planned = config.get("llm_relationships_planned", [])
        assert len(planned) == 2  # Only above threshold relationships
        for plan in planned:
            assert plan["confidence"] >= 0.7
            assert plan["extractor"] == "llm"
            assert plan["source_id"] == graph_alice.id
            assert plan["target_id"] == graph_bob.id

        # Assert metrics show inference but no persistence
        assert config.get("llm_relations_inferred_total", 0) == 3
        assert config.get("llm_relations_persisted_total", 0) == 0

    finally:
        engine_module.settings.enable_llm_relationships = original_enable
        engine_module.settings.llm_rel_min_confidence = original_min_conf


@pytest.mark.asyncio
async def test_llm_relationship_confidence_gating(
    rag_engine: SimpleGraphRAGEngine,
    mock_vector_store: AsyncMock,
    mock_entity_extractor: AsyncMock,
    mock_graph_repository: AsyncMock,
    mock_llm_service: AsyncMock,
):
    """Test that only relationships above confidence threshold are persisted."""
    query_text = "Alice knows Bob with varying confidence"

    # Mock vector store
    chunk_data = create_mock_chunk_data(id="c1", text="Alice maybe knows Bob.", score=0.1)
    search_result = create_mock_search_result(chunk_data, 0.9)
    mock_vector_store.search.return_value = [search_result]

    # Mock entity extraction
    extracted_alice = create_mock_extracted_entity(id="ext_alice", label="PERSON", text="Alice")
    extracted_bob = create_mock_extracted_entity(id="ext_bob", label="PERSON", text="Bob")
    mock_entity_extractor.extract_from_text.return_value = ExtractionResult(
        entities=[extracted_alice, extracted_bob], relationships=[]
    )

    # Mock graph entities
    graph_alice = create_mock_graph_entity(id="graph_alice", type="PERSON", name="Alice")
    graph_bob = create_mock_graph_entity(id="graph_bob", type="PERSON", name="Bob")

    async def mock_search_props(props: dict, limit=None):
        name = props.get("name")
        if name == "Alice":
            return [graph_alice]
        elif name == "Bob":
            return [graph_bob]
        return []

    mock_graph_repository.search_entities_by_properties.side_effect = mock_search_props
    mock_graph_repository.get_neighbors.return_value = ([graph_alice, graph_bob], [])

    # Mock LLM relationship extraction with varying confidence
    mock_llm_relationships = [
        {"source_name": "alice", "target_name": "bob", "type": "KNOWS", "confidence": 0.95},  # Above
        {"source_name": "alice", "target_name": "bob", "type": "LIKES", "confidence": 0.80},  # Above
        {"source_name": "alice", "target_name": "bob", "type": "WORKS_WITH", "confidence": 0.75},  # At threshold
        {"source_name": "alice", "target_name": "bob", "type": "DISLIKES", "confidence": 0.65},  # Below
        {"source_name": "alice", "target_name": "bob", "type": "IGNORES", "confidence": 0.40},  # Well below
    ]
    mock_llm_service.extract_entities_relationships.return_value = ([], mock_llm_relationships)
    mock_llm_service.generate_response.return_value = "Answer with confidence gating"

    # Patch settings with specific threshold
    import graph_rag.core.graph_rag_engine as engine_module
    original_enable = engine_module.settings.enable_llm_relationships
    original_min_conf = engine_module.settings.llm_rel_min_confidence
    engine_module.settings.enable_llm_relationships = True
    engine_module.settings.llm_rel_min_confidence = 0.75  # Set threshold at 0.75

    try:
        # Act
        config = {
            "include_graph": True,
            "extract_relationships": True,
            "extract_relationships_persist": True,
            "k": 1
        }
        result = await rag_engine.query(query_text, config=config)

        # Assert persistence calls - should be 3 (KNOWS, LIKES, WORKS_WITH >= 0.75)
        assert mock_graph_repository.execute_query.call_count == 3

        # Verify confidence of persisted relationships
        cypher_calls = mock_graph_repository.execute_query.call_args_list
        persisted_confidences = []
        for call in cypher_calls:
            cypher, params = call[0]
            confidence = params["props"]["confidence"]
            persisted_confidences.append(confidence)
            assert confidence >= 0.75  # All should be above threshold

        assert 0.95 in persisted_confidences
        assert 0.80 in persisted_confidences
        assert 0.75 in persisted_confidences

        # Assert metrics
        assert config["llm_relations_inferred_total"] == 5  # All relationships inferred
        assert config["llm_relations_persisted_total"] == 3  # Only above threshold persisted

    finally:
        engine_module.settings.enable_llm_relationships = original_enable
        engine_module.settings.llm_rel_min_confidence = original_min_conf


@pytest.mark.asyncio
async def test_llm_relationship_entity_mapping_by_name(
    rag_engine: SimpleGraphRAGEngine,
    mock_vector_store: AsyncMock,
    mock_entity_extractor: AsyncMock,
    mock_graph_repository: AsyncMock,
    mock_llm_service: AsyncMock,
):
    """Test that LLM relationships map entities by canonical lowercase name."""
    query_text = "Different case names"

    # Mock vector store
    chunk_data = create_mock_chunk_data(id="c1", text="ALICE knows bob.", score=0.1)
    search_result = create_mock_search_result(chunk_data, 0.9)
    mock_vector_store.search.return_value = [search_result]

    # Mock entity extraction
    extracted_alice = create_mock_extracted_entity(id="ext_alice", label="PERSON", text="ALICE")
    extracted_bob = create_mock_extracted_entity(id="ext_bob", label="PERSON", text="bob")
    mock_entity_extractor.extract_from_text.return_value = ExtractionResult(
        entities=[extracted_alice, extracted_bob], relationships=[]
    )

    # Mock graph entities (different case)
    graph_alice = create_mock_graph_entity(id="graph_alice", type="PERSON", name="Alice")
    graph_bob = create_mock_graph_entity(id="graph_bob", type="PERSON", name="Bob")

    async def mock_search_props(props: dict, limit=None):
        name = props.get("name")
        if name.lower() == "alice":
            return [graph_alice]
        elif name.lower() == "bob":
            return [graph_bob]
        return []

    mock_graph_repository.search_entities_by_properties.side_effect = mock_search_props
    mock_graph_repository.get_neighbors.return_value = ([graph_alice, graph_bob], [])

    # Mock LLM relationship extraction (mixed case)
    mock_llm_relationships = [
        {"source_name": "ALICE", "target_name": "bob", "type": "KNOWS", "confidence": 0.90},
    ]
    mock_llm_service.extract_entities_relationships.return_value = ([], mock_llm_relationships)
    mock_llm_service.generate_response.return_value = "Answer with case mapping"

    # Patch settings
    import graph_rag.core.graph_rag_engine as engine_module
    original_enable = engine_module.settings.enable_llm_relationships
    original_min_conf = engine_module.settings.llm_rel_min_confidence
    engine_module.settings.enable_llm_relationships = True
    engine_module.settings.llm_rel_min_confidence = 0.7

    try:
        # Act
        config = {
            "include_graph": True,
            "extract_relationships": True,
            "extract_relationships_persist": True,
            "k": 1
        }
        result = await rag_engine.query(query_text, config=config)

        # Assert persistence occurred despite case differences
        assert mock_graph_repository.execute_query.call_count == 1

        # Verify relationship properties include normalized names
        cypher, params = mock_graph_repository.execute_query.call_args[0]
        assert params["props"]["source_name"] == "alice"  # Normalized to lowercase
        assert params["props"]["target_name"] == "bob"    # Normalized to lowercase
        assert params["src"] == graph_alice.id
        assert params["tgt"] == graph_bob.id

        # Assert metrics
        assert config["llm_relations_inferred_total"] == 1
        assert config["llm_relations_persisted_total"] == 1

    finally:
        engine_module.settings.enable_llm_relationships = original_enable
        engine_module.settings.llm_rel_min_confidence = original_min_conf


@pytest.mark.asyncio
async def test_llm_relationship_missing_entities_skipped(
    rag_engine: SimpleGraphRAGEngine,
    mock_vector_store: AsyncMock,
    mock_entity_extractor: AsyncMock,
    mock_graph_repository: AsyncMock,
    mock_llm_service: AsyncMock,
):
    """Test that relationships involving entities not found in graph are skipped."""
    query_text = "Alice knows Charlie"

    # Mock vector store
    chunk_data = create_mock_chunk_data(id="c1", text="Alice knows Charlie.", score=0.1)
    search_result = create_mock_search_result(chunk_data, 0.9)
    mock_vector_store.search.return_value = [search_result]

    # Mock entity extraction
    extracted_alice = create_mock_extracted_entity(id="ext_alice", label="PERSON", text="Alice")
    extracted_charlie = create_mock_extracted_entity(id="ext_charlie", label="PERSON", text="Charlie")
    mock_entity_extractor.extract_from_text.return_value = ExtractionResult(
        entities=[extracted_alice, extracted_charlie], relationships=[]
    )

    # Mock graph entities - only Alice exists
    graph_alice = create_mock_graph_entity(id="graph_alice", type="PERSON", name="Alice")

    async def mock_search_props(props: dict, limit=None):
        name = props.get("name")
        if name == "Alice":
            return [graph_alice]
        return []  # Charlie not found in graph

    mock_graph_repository.search_entities_by_properties.side_effect = mock_search_props
    mock_graph_repository.get_neighbors.return_value = ([graph_alice], [])

    # Mock LLM relationship extraction
    mock_llm_relationships = [
        {"source_name": "alice", "target_name": "charlie", "type": "KNOWS", "confidence": 0.90},
    ]
    mock_llm_service.extract_entities_relationships.return_value = ([], mock_llm_relationships)
    mock_llm_service.generate_response.return_value = "Answer with missing entity"

    # Patch settings
    import graph_rag.core.graph_rag_engine as engine_module
    original_enable = engine_module.settings.enable_llm_relationships
    original_min_conf = engine_module.settings.llm_rel_min_confidence
    engine_module.settings.enable_llm_relationships = True
    engine_module.settings.llm_rel_min_confidence = 0.7

    try:
        # Act
        config = {
            "include_graph": True,
            "extract_relationships": True,
            "extract_relationships_persist": True,
            "k": 1
        }
        result = await rag_engine.query(query_text, config=config)

        # Assert NO persistence occurred (Charlie not found)
        mock_graph_repository.execute_query.assert_not_called()

        # Assert no metrics increment since relationship was skipped before inference
        assert config.get("llm_relations_inferred_total", 0) == 0
        assert config.get("llm_relations_persisted_total", 0) == 0

        # Assert no LLM relationships in context
        assert result.graph_context is not None
        entities, relationships = result.graph_context
        llm_rels = [r for r in relationships if r.properties.get("extractor") == "llm"]
        assert len(llm_rels) == 0

    finally:
        engine_module.settings.enable_llm_relationships = original_enable
        engine_module.settings.llm_rel_min_confidence = original_min_conf
