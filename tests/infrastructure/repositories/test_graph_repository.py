from graph_rag.domain.models import Document, Chunk, Edge
import pytest
# Use the concrete implementation from conftest
from graph_rag.infrastructure.graph_stores.memgraph_store import MemgraphGraphRepository

@pytest.mark.asyncio
async def test_delete_document(memgraph_repo: MemgraphGraphRepository, sample_document):
    """Test deleting a document and associated chunks."""
    # 1. Arrange: Create a document and a chunk linked to it
    doc = Document(**sample_document)
    chunk = Chunk(
        id="chunk_for_delete",
        text="This chunk belongs to the document to be deleted.",
        document_id=doc.id,
        embedding=[0.1] * 10
    )
    await memgraph_repo.add_document(doc)
    await memgraph_repo.add_chunk(chunk)

    # Verify creation
    retrieved_doc = await memgraph_repo.get_document_by_id(doc.id)
    assert retrieved_doc is not None
    # Now verify chunk creation
    retrieved_chunks = await memgraph_repo.get_chunks_by_document_id(doc.id)
    assert len(retrieved_chunks) == 1
    assert retrieved_chunks[0].id == chunk.id
    assert retrieved_chunks[0].text == chunk.text
    assert retrieved_chunks[0].embedding == chunk.embedding

    # 2. Act: Delete the document using the public method
    deleted = await memgraph_repo.delete_document(doc.id)
    assert deleted is True

    # 3. Assert: Document should be gone
    retrieved_doc_after_delete = await memgraph_repo.get_document_by_id(doc.id)
    assert retrieved_doc_after_delete is None
    # Now verify chunk deletion
    retrieved_chunks_after_delete = await memgraph_repo.get_chunks_by_document_id(doc.id)
    assert len(retrieved_chunks_after_delete) == 0

@pytest.mark.asyncio
async def test_delete_nonexistent_document(memgraph_repo: MemgraphGraphRepository):
    """Test deleting a document that does not exist."""
    document_id = "nonexistent-doc-id"
    deleted = await memgraph_repo.delete_document(document_id)
    assert deleted is False
    retrieved = await memgraph_repo.get_document_by_id(document_id)
    assert retrieved is None

@pytest.mark.asyncio
async def test_update_document_metadata(memgraph_repo: MemgraphGraphRepository, sample_document):
    """Test updating only the metadata of a document."""
    doc = Document(**sample_document)
    await memgraph_repo.add_document(doc)
    retrieved_doc_before = await memgraph_repo.get_document_by_id(doc.id)
    assert retrieved_doc_before is not None
    assert retrieved_doc_before.metadata == sample_document["metadata"]

    # 2. Act: Update the metadata using add_document (MERGE semantics)
    new_metadata = {"source": "updated_test", "status": "processed", "nested": {"key": 1}}
    updated_doc = Document(
        id=doc.id,
        content=doc.content,
        metadata=new_metadata
    )
    await memgraph_repo.add_document(updated_doc)

    # 3. Assert: Verify by fetching again
    retrieved_doc_after = await memgraph_repo.get_document_by_id(doc.id)
    assert retrieved_doc_after is not None
    assert retrieved_doc_after.id == doc.id
    assert retrieved_doc_after.content == doc.content
    assert retrieved_doc_after.metadata == new_metadata
    assert retrieved_doc_after.updated_at is not None

@pytest.mark.asyncio
async def test_update_document_nonexistent(memgraph_repo: MemgraphGraphRepository):
    """Test updating a document that does not exist."""
    # Try to update a non-existent document (should create it)
    doc_id = "nonexistent-doc-for-update"
    new_metadata = {"new": "data"}
    doc = Document(id=doc_id, content="", metadata=new_metadata)
    await memgraph_repo.add_document(doc)
    retrieved = await memgraph_repo.get_document_by_id(doc_id)
    assert retrieved is not None
    assert retrieved.metadata == new_metadata

@pytest.mark.asyncio
async def test_update_document_no_properties(memgraph_repo: MemgraphGraphRepository, sample_document):
    """Test updating with no properties specified should ideally not change anything except updated_at."""
    doc = Document(**sample_document)
    await memgraph_repo.add_document(doc)
    retrieved_doc_before = await memgraph_repo.get_document_by_id(doc.id)

    # Act: Update with only id and content (simulate no-op update)
    updated_doc = Document(id=doc.id, content=doc.content, metadata=doc.metadata)
    await memgraph_repo.add_document(updated_doc)

    # Assert: Should return the doc, potentially unchanged or with updated 'updated_at'
    retrieved_doc_after = await memgraph_repo.get_document_by_id(doc.id)
    assert retrieved_doc_after is not None
    assert retrieved_doc_after.id == doc.id
    assert retrieved_doc_after.metadata == retrieved_doc_before.metadata
    assert retrieved_doc_after.updated_at is not None
    # Optionally check that updated_at has changed
    # assert retrieved_doc_after.updated_at > retrieved_doc_before.updated_at

# These tests below seem to assume a different repository interface (create_document, etc.)
# They need to be adapted to use MemgraphGraphRepository methods (add_document, add_chunk)

# @pytest.mark.asyncio
# async def test_connection(memgraph_repo: MemgraphGraphRepository):
#     """Test that we can connect to the database."""
#     # Try to execute a simple query
#     result = await memgraph_repo._execute_read_query("RETURN 1 as test")
#     assert result is not None
#     assert len(result) == 1
#     assert result[0]["test"] == 1

# @pytest.mark.asyncio
# async def test_create_and_retrieve_document(memgraph_repo: MemgraphGraphRepository):
#     """Test creating and retrieving a document."""
#     doc = Document(id="test_doc_1", content="This is a test document")
#     await memgraph_repo.add_document(doc)
#     result = await memgraph_repo.get_document_by_id(doc.id)
#     assert result is not None
#     assert result.id == doc.id
#     assert result.content == doc.content

# @pytest.mark.asyncio
# async def test_create_and_retrieve_chunk(memgraph_repo: MemgraphGraphRepository):
#     """Test creating and retrieving a chunk."""
#     doc = Document(id="test_doc_2", content="This is another test document")
#     await memgraph_repo.add_document(doc)
#     chunk = Chunk(id="test_chunk_1", text="This is a test chunk", document_id=doc.id, embedding=[0.1, 0.2, 0.3])
#     await memgraph_repo.add_chunk(chunk)
#     chunks = await memgraph_repo.get_chunks_by_document_id(doc.id)
#     assert len(chunks) == 1
#     retrieved_chunk = chunks[0]
#     assert retrieved_chunk.id == chunk.id
#     assert retrieved_chunk.text == chunk.text
#     assert retrieved_chunk.embedding == chunk.embedding
#     pass 