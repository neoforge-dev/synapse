import pytest
from datetime import datetime
from typing import Any, Dict
from graph_rag.infrastructure.repositories.graph_repository import MemgraphRepository
from graph_rag.infrastructure.graph_stores.memgraph_store import MemgraphGraphRepository

from graph_rag.domain.models import Document, Chunk, Edge


@pytest.mark.asyncio
async def test_save_and_retrieve_document(
    memgraph_repo: MemgraphGraphRepository,
    sample_document: dict[str, Any]
) -> None:
    """Test saving and retrieving a document."""
    # Create document
    document = Document(**sample_document)
    
    # Save document
    doc_id = await memgraph_repo.save_document(document)
    assert doc_id == document.id
    
    # Retrieve document
    retrieved_doc = await memgraph_repo.get_document(doc_id)
    assert retrieved_doc is not None
    assert retrieved_doc.id == document.id
    assert retrieved_doc.content == document.content
    assert retrieved_doc.metadata == document.metadata


@pytest.mark.asyncio
async def test_save_and_retrieve_chunk(
    memgraph_repo: MemgraphGraphRepository,
    sample_chunk: dict[str, Any]
) -> None:
    """Test saving and retrieving a chunk."""
    # Create chunk
    chunk = Chunk(**sample_chunk)
    
    # Save chunk
    chunk_id = await memgraph_repo.save_chunk(chunk)
    assert chunk_id == chunk.id
    
    # Retrieve chunks by document
    chunks = await memgraph_repo.get_chunks_by_document(chunk.document_id)
    assert len(chunks) == 1
    assert chunks[0].id == chunk.id
    assert chunks[0].content == chunk.content
    assert chunks[0].embedding == chunk.embedding


@pytest.mark.asyncio
async def test_create_relationship(
    memgraph_repo: MemgraphGraphRepository,
    sample_document: dict[str, Any],
    sample_chunk: dict[str, Any]
) -> None:
    """Test creating a relationship between nodes."""
    # Create and save document and chunk
    document = Document(**sample_document)
    chunk = Chunk(**sample_chunk)
    
    await memgraph_repo.save_document(document)
    await memgraph_repo.save_chunk(chunk)
    
    # Create relationship
    edge = Edge(
        id="edge1",
        type="CONTAINS",
        source_id=document.id,
        target_id=chunk.id
    )
    
    edge_id = await memgraph_repo.create_relationship(edge)
    assert edge_id == edge.id


@pytest.mark.asyncio
async def test_nonexistent_document(
    memgraph_repo: MemgraphGraphRepository
) -> None:
    """Test retrieving a nonexistent document."""
    retrieved_doc = await memgraph_repo.get_document("nonexistent")
    assert retrieved_doc is None


@pytest.mark.asyncio
async def test_nonexistent_chunks(
    memgraph_repo: MemgraphGraphRepository
) -> None:
    """Test retrieving chunks for a nonexistent document."""
    chunks = await memgraph_repo.get_chunks_by_document("nonexistent")
    assert len(chunks) == 0


@pytest.mark.asyncio
async def test_delete_document(
    memgraph_repo: MemgraphGraphRepository,
    sample_document: dict[str, Any]
) -> None:
    """Test deleting a document."""
    # Create document
    document = Document(**sample_document)
    
    # Save document
    doc_id = await memgraph_repo.save_document(document)
    assert doc_id == document.id
    
    # Delete document
    await memgraph_repo.delete_document(doc_id)
    
    # Retrieve document
    retrieved_doc = await memgraph_repo.get_document(doc_id)
    assert retrieved_doc is None 