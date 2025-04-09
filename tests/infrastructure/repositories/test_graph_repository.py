from graph_rag.domain.models import Document, Chunk, Edge

@pytest.mark.asyncio
async def test_delete_document(graph_repository: MemgraphRepository, sample_document):
    """Test deleting a document and associated chunks."""
    # 1. Arrange: Create a document and a chunk linked to it
    doc = Document(**sample_document)
    chunk = Chunk(
        id="chunk_for_delete",
        content="This chunk belongs to the document to be deleted.",
        document_id=doc.id
    )
    edge = Edge(
        id="edge_for_delete",
        type="CONTAINS",
        source_id=doc.id,
        target_id=chunk.id
    )
    
    await graph_repository.save_document(doc)
    await graph_repository.save_chunk(chunk)
    await graph_repository.create_relationship(edge)
    
    # Verify creation (optional but good practice)
    retrieved_doc = await graph_repository.get_document(doc.id)
    assert retrieved_doc is not None
    retrieved_chunks = await graph_repository.get_chunks_by_document(doc.id)
    assert len(retrieved_chunks) == 1
    
    # 2. Act: Delete the document
    deleted = await graph_repository.delete_document(doc.id)
    assert deleted is True
    
    # 3. Assert: Document and associated chunk should be gone
    retrieved_doc_after_delete = await graph_repository.get_document(doc.id)
    assert retrieved_doc_after_delete is None
    
    retrieved_chunks_after_delete = await graph_repository.get_chunks_by_document(doc.id)
    assert len(retrieved_chunks_after_delete) == 0
    
    # Optional: Verify chunk cannot be fetched directly (might require get_chunk_by_id method)
    # chunk_exists = await graph_repository.get_chunk(chunk.id) # Assuming get_chunk exists
    # assert chunk_exists is None

@pytest.mark.asyncio
async def test_delete_nonexistent_document(graph_repository: MemgraphRepository):
    """Test deleting a document that does not exist."""
    document_id = "nonexistent-doc-id"
    
    # Act: Attempt to delete
    deleted = await graph_repository.delete_document(document_id)
    
    # Assert: Should return False or indicate not found without error
    assert deleted is False

@pytest.mark.asyncio
async def test_update_document_metadata(graph_repository: MemgraphRepository, sample_document):
    """Test updating only the metadata of a document."""
    # 1. Arrange: Create a document
    doc = Document(**sample_document)
    await graph_repository.save_document(doc)
    retrieved_doc_before = await graph_repository.get_document(doc.id)
    assert retrieved_doc_before is not None
    assert retrieved_doc_before.metadata == sample_document["metadata"]
    
    # 2. Act: Update the metadata
    new_metadata = {"source": "updated_test", "status": "processed", "nested": {"key": 1}}
    updated_doc = await graph_repository.update_document_properties(
        document_id=doc.id, 
        properties_to_update={"metadata": new_metadata}
    )
    
    # 3. Assert: Returned doc has new metadata, other fields unchanged
    assert updated_doc is not None
    assert updated_doc.id == doc.id
    assert updated_doc.content == doc.content # Content should not change
    assert updated_doc.metadata == new_metadata
    assert updated_doc.updated_at is not None
    assert updated_doc.updated_at > retrieved_doc_before.created_at
    
    # 4. Assert: Verify by fetching again
    retrieved_doc_after = await graph_repository.get_document(doc.id)
    assert retrieved_doc_after is not None
    assert retrieved_doc_after.metadata == new_metadata
    assert retrieved_doc_after.updated_at == updated_doc.updated_at

@pytest.mark.asyncio
async def test_update_document_nonexistent(graph_repository: MemgraphRepository):
    """Test updating a document that does not exist."""
    updated_doc = await graph_repository.update_document_properties(
        document_id="nonexistent-doc-for-update",
        properties_to_update={"metadata": {"new": "data"}}
    )
    assert updated_doc is None

@pytest.mark.asyncio
async def test_update_document_no_properties(graph_repository: MemgraphRepository, sample_document):
    """Test updating with no properties specified should ideally not change anything or error."""
    doc = Document(**sample_document)
    await graph_repository.save_document(doc)
    retrieved_doc_before = await graph_repository.get_document(doc.id)
    
    # Act: Update with empty dict
    updated_doc = await graph_repository.update_document_properties(
        document_id=doc.id, 
        properties_to_update={}
    )
    
    # Assert: Should return the doc, potentially unchanged or with updated 'updated_at'
    assert updated_doc is not None
    assert updated_doc.id == doc.id
    assert updated_doc.metadata == retrieved_doc_before.metadata
    # updated_at might or might not change depending on implementation, 
    # but verifying it exists is reasonable.
    assert updated_doc.updated_at is not None 