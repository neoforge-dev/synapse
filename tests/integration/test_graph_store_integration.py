"""Integration tests for the graph store implementation."""

import pytest
from typing import AsyncGenerator
import pytest_asyncio
import logging
import uuid
import mgclient
import asyncio
import numpy as np

from graph_rag.infrastructure.graph_stores.memgraph_store import MemgraphGraphRepository
from graph_rag.domain.models import Document, Chunk, Entity, Relationship
from tests.utils.test_data import (
    create_test_document_data,
    create_test_chunk_data,
    SAMPLE_DOCUMENTS,
    SAMPLE_CHUNKS,
    SAMPLE_ENTITIES,
    SAMPLE_RELATIONSHIPS
)

logger = logging.getLogger(__name__)

@pytest.mark.integration
@pytest.mark.graph
class TestMemgraphGraphRepositoryIntegration:
    """Integration tests for MemgraphGraphRepository."""

    @pytest_asyncio.fixture
    async def repo(self, memgraph_connection) -> AsyncGenerator[MemgraphGraphRepository, None]:
        """Creates a MemgraphGraphRepository instance with a persistent connection for the test scope."""
        # Instantiate using default config which reads from settings
        repo = MemgraphGraphRepository()
        await repo.connect() # Establish connection
        
        # Ensure the database is clean before the test, using the persistent connection
        try:
            # Use execute_query, which will now use the repo's established connection
            await repo.execute_query("MATCH (n) DETACH DELETE n") 
            logger.info("Database cleaned successfully using persistent connection.")
        except Exception as e:
            logger.error(f"Failed to clean database in repo fixture setup: {e}", exc_info=True)
            await repo.close() # Ensure connection is closed even if setup fails
            pytest.fail(f"Database cleaning failed: {e}")

        yield repo # Provide the connected repo to the test
        
        # Clean up: close the persistent connection
        await repo.close()
        logger.debug("Finished repo fixture scope and closed connection.")

    @pytest.mark.asyncio
    async def test_document_operations(self, repo):
        """Tests document operations with a real database."""
        # Verify initial state is implicitly handled by the repo fixture cleaning
        # await verify_graph_state(repo._get_driver, expected_nodes=0, expected_relationships=0) # verify_graph_state needs definition or removal

        # Add document using the data factory
        doc_data = create_test_document_data()
        doc = Document(**doc_data.model_dump())
        
        # await repo.begin_transaction() # REMOVE: Rely on execute_query commit
        await repo.add_document(doc)
        # await repo.commit_transaction() # REMOVE: Rely on execute_query commit
        
        # DEBUG: Manually check if the document exists immediately after add_document completes
        # try:
        #     manual_check_results = await repo.execute_query(
        #         "MATCH (d:Document {id: $doc_id}) RETURN d.id as id, d.content as content", 
        #         params={"doc_id": doc.id}
        #     )
        #     print(f"\nDEBUG: Manual check for doc {doc.id} after commit: {manual_check_results}\n")
        #     # Optionally commit again after the manual check if needed, though read shouldn't require it
        #     # await repo.commit_transaction() 
        # except Exception as e:
        #     print(f"\nDEBUG: Error during manual check for doc {doc.id}: {e}\n")

        # Add a small delay (revert from large diagnostic sleep)
        await asyncio.sleep(0.1) 
        
        retrieved_doc = await repo.get_document_by_id(doc.id)
        assert retrieved_doc is not None
        assert retrieved_doc.id == doc.id
        assert retrieved_doc.content == doc.content

        # Add chunk using the data factory
        chunk_data = create_test_chunk_data(document_id=doc.id)
        # FIX: Add metadata=None when creating Chunk from data factory output
        chunk_data_dict = chunk_data.model_dump()
        chunk_data_dict["metadata"] = chunk_data_dict.get("metadata", None) # Ensure metadata exists
        chunk = Chunk(**chunk_data_dict)
        await repo.add_chunk(chunk)

        # Verify chunk creation
        # Use get_node_by_id and check type/properties, or use a specific get_chunk_by_id if implemented
        # retrieved_chunk = await repo.get_chunk_by_id(chunk.id) # Assuming get_chunk_by_id exists
        retrieved_node = await repo.get_node_by_id(chunk.id) # Using get_node_by_id
        assert retrieved_node is not None, f"Chunk {chunk.id} not found using get_node_by_id"
        assert isinstance(retrieved_node, Chunk), f"Node {chunk.id} is not a Chunk object"
        assert retrieved_node.id == chunk.id
        assert retrieved_node.text == chunk.text
        # Compare embeddings if they are stored and retrieved correctly
        # assert retrieved_node.embedding == chunk.embedding # Might fail due to float precision
        if chunk.embedding:
            assert np.allclose(retrieved_node.embedding, chunk.embedding), "Chunk embeddings do not match"

        # Delete document
        # await repo.begin_transaction() # REMOVE
        success = await repo.delete_document(doc.id)
        # await repo.commit_transaction() # REMOVE
        assert success is True

        # Verify deletion
        # await asyncio.sleep(0.1) # Small delay just in case
        assert await repo.get_document_by_id(doc.id) is None
        # Verify chunk is also deleted (due to DETACH DELETE)
        assert await repo.get_node_by_id(chunk.id) is None

    @pytest.mark.asyncio
    async def test_entity_operations(self, repo):
        """Tests entity operations with a real database."""
        # Verify initial state (handled by fixture)
        # await verify_graph_state(repo._get_driver, expected_nodes=0, expected_relationships=0)

        # Add entities (assuming create_test_entity works similarly or is defined)
        # Use direct instantiation for now
        entity1 = Entity(id="entity_1", name="Entity One", type="TEST_ENTITY")
        entity2 = Entity(id="entity_2", name="Entity Two", type="TEST_ENTITY")
        
        await repo.add_entity(entity1)
        await repo.add_entity(entity2)
        # await verify_graph_state(repo._get_driver, expected_nodes=2, expected_relationships=0)
        retrieved_entity1 = await repo.get_entity_by_id(entity1.id)
        assert retrieved_entity1 is not None
        assert retrieved_entity1.id == entity1.id

        # Add relationship (assuming create_test_relationship works)
        # Use direct instantiation for now
        relationship = Relationship(
             id=str(uuid.uuid4()), 
             source_id=entity1.id, 
             target_id=entity2.id, 
             type="RELATED_TO"
        )
        await repo.add_relationship(relationship)
        # TODO: Add verification for relationship retrieval

    @pytest.mark.asyncio
    async def test_bulk_operations(self, repo):
        """Tests bulk operations with a real database."""
        # Verify initial state (handled by fixture)
        # await verify_graph_state(repo._get_driver, expected_nodes=0, expected_relationships=0)

        # Add multiple documents
        docs_to_add = []
        for doc_data_dict in SAMPLE_DOCUMENTS:
            doc_data_obj = create_test_document_data(**doc_data_dict)
            docs_to_add.append(Document(**doc_data_obj.model_dump()))
        
        for doc in docs_to_add:
             await repo.add_document(doc)
        # await repo.commit_transaction() # REMOVE: Method no longer exists

        # Add a small delay (revert from large diagnostic sleep)
        await asyncio.sleep(0.1) 

        # Add multiple chunks
        chunks_to_add = []
        for chunk_data_dict in SAMPLE_CHUNKS:
            # Use the data factory
            chunk_data_obj = create_test_chunk_data(**chunk_data_dict)
            # FIX: Add metadata=None when creating Chunk from data factory output
            chunk_model_dict = chunk_data_obj.model_dump()
            chunk_model_dict["metadata"] = chunk_model_dict.get("metadata", None) # Ensure metadata exists
            chunks_to_add.append(Chunk(**chunk_model_dict))
        
        # Add chunks individually (bulk method needs review/implementation)
        for chunk in chunks_to_add:
            # Ensure parent document exists before adding chunk
            parent_doc = await repo.get_document_by_id(chunk.document_id)
            if parent_doc:
                await repo.add_chunk(chunk)
            else:
                 logger.warning(f"Skipping chunk {chunk.id} because parent doc {chunk.document_id} not found")

        # Verify final state
        # await verify_graph_state(
        #     repo._get_driver,
        #     expected_nodes=len(SAMPLE_DOCUMENTS) + len(SAMPLE_CHUNKS),
        #     expected_relationships=len(SAMPLE_CHUNKS)
        # )
        # Add specific checks for added nodes/rels
        # await repo.commit_transaction() # REMOVE: Method no longer exists
        assert await repo.get_document_by_id(SAMPLE_DOCUMENTS[0]['id']) is not None
        # Add more checks as needed

        # Add a small delay
        await asyncio.sleep(0.1)

        # Verify chunks exist
        for chunk in chunks_to_add:
            retrieved_chunk = await repo.get_node_by_id(chunk.id)
            assert retrieved_chunk is not None, f"Chunk {chunk.id} not retrieved after bulk add."
            assert isinstance(retrieved_chunk, Chunk)
            assert retrieved_chunk.text == chunk.text

    @pytest.mark.asyncio
    async def test_error_handling(self, repo):
        """Tests error handling with a real database."""
        # Try to add a chunk without its document - THIS SHOULD FAIL
        chunk_data = {
            "id": str(uuid.uuid4()),
            "document_id": "nonexistent_doc",
            "text": "Chunk without a parent.",
            "metadata": {"type": "orphan"}
        }
        chunk = Chunk(**chunk_data)
        with pytest.raises(Exception): # Expecting mgclient.DatabaseError or similar
            await repo.add_chunk(chunk)
            pytest.fail("Adding chunk with non-existent document ID should have failed")

        # Try to add a relationship with nonexistent entities - THIS WON'T FAIL in Cypher
        entity1 = Entity(id="nonexistent_1", name="Nonexistent One", type="TEST")
        entity2 = Entity(id="nonexistent_2", name="Nonexistent Two", type="TEST")

        relationship = Relationship(
             id=str(uuid.uuid4()),
             source_id=entity1.id, 
             target_id=entity2.id, 
             type="BAD_REL",
             metadata={"reason": "test"}
        )
        # Don't expect an exception here, the MERGE won't execute
        try:
            await repo.add_relationship(relationship)
        except Exception as e:
            pytest.fail(f"Adding relationship with non-existent nodes raised an unexpected exception: {e}")

        # Optional: Verify relationship was not created (if needed)
        # result = await repo.get_relationship_by_id(relationship.id)
        # assert result is None

# Add dummy factories for test_error_handling if not imported
def create_test_entity(**kwargs):
    return Entity(**kwargs)

def create_test_relationship(source, target, **kwargs):
    return Relationship(source_id=source.id, target_id=target.id, **kwargs) 