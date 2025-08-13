import pytest

# Skip entire module if mgclient (Memgraph client) isn’t available
try:
    import mgclient  # type: ignore
except Exception:
    pytest.skip("mgclient not available; skipping Memgraph-dependent tests", allow_module_level=True)

pytestmark = pytest.mark.integration
import uuid
from typing import Optional
from unittest.mock import ANY, AsyncMock, MagicMock, call

import pytest

from graph_rag.core.interfaces import (
    ChunkData,
    DocumentData,
    ExtractedEntity,
    ExtractedRelationship,
    GraphRepository,
)
from graph_rag.core.persistent_kg_builder import PersistentKnowledgeGraphBuilder

# Domain models for creating test data that might be inputs to services using the builder


# Helper to create mock DocumentData
def create_mock_document_data(
    id: str, content: str, metadata: Optional[dict] = None
) -> DocumentData:
    return DocumentData(id=id, content=content, metadata=metadata or {})


# Helper to create mock ChunkData
def create_mock_chunk_data(
    id: str,
    text: str,
    doc_id: str,
    embedding: Optional[list[float]] = None,
    metadata: Optional[dict] = None,
) -> ChunkData:
    return ChunkData(
        id=id,
        text=text,
        document_id=doc_id,
        embedding=embedding or [0.1, 0.2],
        metadata=metadata or {},
    )


# Helper to create mock ExtractedEntity
def create_mock_extracted_entity(
    id: str, text: str, label: str, **kwargs
) -> ExtractedEntity:
    # ExtractedEntity is a Pydantic BaseModel, so we create an instance
    return ExtractedEntity(id=id, text=text, label=label, **kwargs)


# Helper to create mock ExtractedRelationship
def create_mock_extracted_relationship(
    source_id: str, target_id: str, label: str, **kwargs
) -> ExtractedRelationship:
    # ExtractedRelationship is a Pydantic BaseModel
    return ExtractedRelationship(
        source_entity_id=source_id, target_entity_id=target_id, label=label, **kwargs
    )


@pytest.fixture
def mock_graph_repo() -> AsyncMock:
    """Provides a mock GraphRepository."""
    # Ensure the mock spec includes all methods called by the builder
    repo = AsyncMock(spec=GraphRepository)
    repo.add_node = AsyncMock()
    repo.add_relationship = AsyncMock()
    return repo


@pytest.fixture
def builder(mock_graph_repo: AsyncMock):  # Ensure mock_graph_repo is passed
    return PersistentKnowledgeGraphBuilder(
        graph_store=mock_graph_repo  # Pass the AsyncMock directly
    )


@pytest.mark.asyncio
async def test_persistent_builder_initialization(
    mock_graph_repo: AsyncMock,
):  # Use AsyncMock type hint
    """Test that the builder initializes correctly with mocked dependencies."""
    b = PersistentKnowledgeGraphBuilder(graph_store=mock_graph_repo)
    assert b.graph_store == mock_graph_repo


@pytest.mark.asyncio
async def test_add_document_and_chunk(
    builder: PersistentKnowledgeGraphBuilder, mock_graph_repo: AsyncMock
):
    """Test adding a document and a chunk, and linking them."""
    doc_id = f"doc-{uuid.uuid4()}"
    chunk_id = f"chunk-{uuid.uuid4()}"

    doc_data = create_mock_document_data(
        id=doc_id, content="Document content.", metadata={"source": "test"}
    )
    chunk_data = create_mock_chunk_data(
        id=chunk_id, text="Chunk text.", doc_id=doc_id, metadata={"order": 1}
    )

    await builder.add_document(doc_data)
    await builder.add_chunk(chunk_data)

    # Assert document node creation
    # Check properties passed to add_node, specifically metadata
    # Note: builder adds created_at/updated_at, so we use mock.ANY for those if not checking exact time
    doc_node_call = mock_graph_repo.add_node.call_args_list[0]
    assert doc_node_call == call(
        label="Document",
        properties={
            "id": doc_id,
            "content": "Document content.",
            "metadata": {"source": "test"},
            "created_at": ANY,  # Use ANY from unittest.mock
            "updated_at": ANY,  # Use ANY from unittest.mock
        },
    )

    # Assert chunk node creation
    chunk_node_call = mock_graph_repo.add_node.call_args_list[1]
    assert chunk_node_call == call(
        label="Chunk",
        properties={
            "id": chunk_id,
            "text": "Chunk text.",
            "document_id": doc_id,
            "embedding": [0.1, 0.2],
            "created_at": ANY,  # Use ANY from unittest.mock
            "updated_at": ANY,  # Use ANY from unittest.mock
        },
    )

    # Assert relationship from Document to Chunk
    doc_chunk_rel_call = mock_graph_repo.add_relationship.call_args_list[0]
    assert doc_chunk_rel_call == call(
        source_node_id=doc_id,
        target_node_id=chunk_id,
        rel_type="CONTAINS",
        properties={"created_at": ANY},  # Corrected to ANY
    )


@pytest.mark.asyncio
async def test_add_entities_and_relationships(
    builder: PersistentKnowledgeGraphBuilder, mock_graph_repo: AsyncMock
):
    """Test adding entities and relationships between them."""
    entity1_id = f"ent-{uuid.uuid4()}"
    entity2_id = f"ent-{uuid.uuid4()}"

    # Use the helper for ExtractedEntity TypedDict
    entity1_data = create_mock_extracted_entity(
        id=entity1_id, text="Alice", label="PERSON"
    )
    entity2_data = create_mock_extracted_entity(
        id=entity2_id, text="Paris", label="LOCATION"
    )

    # Use the helper for ExtractedRelationship TypedDict
    relationship_data = create_mock_extracted_relationship(
        source_id=entity1_id, target_id=entity2_id, label="VISITED"
    )

    await builder.add_entity(entity1_data)
    await builder.add_entity(entity2_data)
    await builder.add_relationship(relationship_data)

    # Assert entity1 node creation
    # Entity labels (PERSON, LOCATION) are used as node labels in the graph
    entity1_node_call = mock_graph_repo.add_node.call_args_list[0]
    assert entity1_node_call == call(
        label="PERSON",
        properties={
            "id": entity1_id,
            "label": "PERSON",  # The builder stores original label as a property
            "text": "Alice",
            "created_at": ANY,  # Use ANY from unittest.mock
            "updated_at": ANY,  # Use ANY from unittest.mock
        },
    )

    # Assert entity2 node creation
    entity2_node_call = mock_graph_repo.add_node.call_args_list[1]
    assert entity2_node_call == call(
        label="LOCATION",
        properties={
            "id": entity2_id,
            "label": "LOCATION",
            "text": "Paris",
            "created_at": ANY,  # Use ANY from unittest.mock
            "updated_at": ANY,  # Use ANY from unittest.mock
        },
    )

    # Assert relationship creation
    rel_call = mock_graph_repo.add_relationship.call_args_list[0]
    assert rel_call == call(
        source_node_id=entity1_id,
        target_node_id=entity2_id,
        rel_type="VISITED",
        properties={
            "created_at": ANY,
            "updated_at": ANY,
        },  # Corrected to ANY
    )


@pytest.mark.asyncio
async def test_link_chunk_to_entities(
    builder: PersistentKnowledgeGraphBuilder, mock_graph_repo: AsyncMock
):
    """Test linking a chunk to multiple entities."""
    chunk_id = f"chunk-{uuid.uuid4()}"
    entity1_id = f"ent-{uuid.uuid4()}"
    entity2_id = f"ent-{uuid.uuid4()}"
    entity_ids_to_link = [entity1_id, entity2_id]

    await builder.link_chunk_to_entities(chunk_id, entity_ids_to_link)

    # Assert MENTIONS relationship creations
    assert mock_graph_repo.add_relationship.call_count == 2

    link1_call = mock_graph_repo.add_relationship.call_args_list[0]
    assert link1_call == call(
        source_node_id=chunk_id,
        target_node_id=entity1_id,
        rel_type="MENTIONS",
        properties={"created_at": ANY},  # Corrected to ANY
    )

    link2_call = mock_graph_repo.add_relationship.call_args_list[1]
    assert link2_call == call(
        source_node_id=chunk_id,
        target_node_id=entity2_id,
        rel_type="MENTIONS",
        properties={"created_at": ANY},  # Corrected to ANY
    )


# The following original tests need more significant refactoring or re-evaluation
# as they were based on a non-existent `build()` method and assumed
# the builder itself would do entity extraction if not provided.
# The PersistentKnowledgeGraphBuilder's API shows it expects pre-extracted entities/relationships.

# @pytest.mark.asyncio
# async def test_persistent_builder_build_with_extraction( ... ): ...
# @pytest.mark.asyncio
# async def test_persistent_builder_build_empty_doc( ... ): ...
# @pytest.mark.asyncio
# async def test_persistent_builder_build_no_extraction_needed( ... ): ...

# For now, these tests will be effectively removed by not refactoring them.
# A new approach would be needed if testing an orchestration layer that uses this builder.
# The current tests focus on the direct API of PersistentKnowledgeGraphBuilder.
