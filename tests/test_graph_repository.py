import pytest
from datetime import datetime
from typing import Any

from graph_rag.domain.models import Document, Chunk, Edge


@pytest.mark.asyncio
async def test_save_and_retrieve_document(
    graph_repository: MemgraphRepository,
    sample_document: dict[str, Any]
) -> None:
    """Test saving and retrieving a document."""
    # Create document
    document = Document(**sample_document)
    
    # Save document
    doc_id = await graph_repository.save_document(document)
    assert doc_id == document.id
    
    # Retrieve document
    retrieved_doc = await graph_repository.get_document(doc_id)
    assert retrieved_doc is not None
    assert retrieved_doc.id == document.id
    assert retrieved_doc.content == document.content
    assert retrieved_doc.metadata == document.metadata


@pytest.mark.asyncio
async def test_save_and_retrieve_chunk(
    graph_repository: MemgraphRepository,
    sample_chunk: dict[str, Any]
) -> None:
    """Test saving and retrieving a chunk."""
    # Create chunk
    chunk = Chunk(**sample_chunk)
    
    # Save chunk
    chunk_id = await graph_repository.save_chunk(chunk)
    assert chunk_id == chunk.id
    
    # Retrieve chunks by document
    chunks = await graph_repository.get_chunks_by_document(chunk.document_id)
    assert len(chunks) == 1
    assert chunks[0].id == chunk.id
    assert chunks[0].content == chunk.content
    assert chunks[0].embedding == chunk.embedding


@pytest.mark.asyncio
async def test_create_relationship(
    graph_repository: MemgraphRepository,
    sample_document: dict[str, Any],
    sample_chunk: dict[str, Any]
) -> None:
    """Test creating a relationship between nodes."""
    # Create and save document and chunk
    document = Document(**sample_document)
    chunk = Chunk(**sample_chunk)
    
    await graph_repository.save_document(document)
    await graph_repository.save_chunk(chunk)
    
    # Create relationship
    edge = Edge(
        id="edge1",
        type="CONTAINS",
        source_id=document.id,
        target_id=chunk.id
    )
    
    edge_id = await graph_repository.create_relationship(edge)
    assert edge_id == edge.id


@pytest.mark.asyncio
async def test_nonexistent_document(
    graph_repository: MemgraphRepository
) -> None:
    """Test retrieving a nonexistent document."""
    retrieved_doc = await graph_repository.get_document("nonexistent")
    assert retrieved_doc is None


@pytest.mark.asyncio
async def test_nonexistent_chunks(
    graph_repository: MemgraphRepository
) -> None:
    """Test retrieving chunks for a nonexistent document."""
    chunks = await graph_repository.get_chunks_by_document("nonexistent")
    assert len(chunks) == 0 