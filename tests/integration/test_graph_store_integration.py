"""Integration tests for the graph store implementation."""

import pytest
from typing import AsyncGenerator

from graph_rag.infrastructure.graph_stores.memgraph_store import MemgraphGraphRepository
from tests.utils.test_helpers import (
    create_test_document,
    create_test_chunk,
    create_test_entity,
    create_test_relationship,
    verify_graph_state
)
from tests.utils.test_data import SAMPLE_DOCUMENTS, SAMPLE_CHUNKS, SAMPLE_ENTITIES, SAMPLE_RELATIONSHIPS

@pytest.mark.integration
@pytest.mark.graph
class TestMemgraphGraphRepositoryIntegration:
    """Integration tests for MemgraphGraphRepository."""

    @pytest.fixture
    async def repo(self, memgraph_connection) -> AsyncGenerator[MemgraphGraphRepository, None]:
        """Creates a MemgraphGraphRepository instance with a real connection."""
        repo = MemgraphGraphRepository(driver=memgraph_connection)
        await repo.connect()
        yield repo
        await repo.close()

    async def test_document_operations(self, repo, clean_memgraph):
        """Tests document operations with a real database."""
        # Verify initial state
        await verify_graph_state(repo._get_driver, expected_nodes=0, expected_relationships=0)

        # Add document
        doc = create_test_document()
        await repo.add_document(doc)
        await verify_graph_state(repo._get_driver, expected_nodes=1, expected_relationships=0)

        # Add chunk
        chunk = create_test_chunk(document_id=doc.id)
        await repo.add_chunk(chunk)
        await verify_graph_state(repo._get_driver, expected_nodes=2, expected_relationships=1)

    async def test_entity_operations(self, repo, clean_memgraph):
        """Tests entity operations with a real database."""
        # Verify initial state
        await verify_graph_state(repo._get_driver, expected_nodes=0, expected_relationships=0)

        # Add entities
        entity1 = create_test_entity(entity_id="entity_1")
        entity2 = create_test_entity(entity_id="entity_2")
        await repo.add_entity(entity1)
        await repo.add_entity(entity2)
        await verify_graph_state(repo._get_driver, expected_nodes=2, expected_relationships=0)

        # Add relationship
        relationship = create_test_relationship(entity1, entity2)
        await repo.add_relationship(relationship)
        await verify_graph_state(repo._get_driver, expected_nodes=2, expected_relationships=1)

    async def test_bulk_operations(self, repo, clean_memgraph):
        """Tests bulk operations with a real database."""
        # Verify initial state
        await verify_graph_state(repo._get_driver, expected_nodes=0, expected_relationships=0)

        # Add multiple documents
        for doc_data in SAMPLE_DOCUMENTS:
            doc = create_test_document(
                doc_id=doc_data["id"],
                content=doc_data["content"],
                metadata=doc_data["metadata"]
            )
            await repo.add_document(doc)

        # Add multiple chunks
        for chunk_data in SAMPLE_CHUNKS:
            chunk = create_test_chunk(
                chunk_id=chunk_data["id"],
                text=chunk_data["text"],
                doc_id=chunk_data["document_id"],
                embedding=chunk_data["embedding"]
            )
            await repo.add_chunk(chunk)

        # Verify final state
        await verify_graph_state(
            repo._get_driver,
            expected_nodes=len(SAMPLE_DOCUMENTS) + len(SAMPLE_CHUNKS),
            expected_relationships=len(SAMPLE_CHUNKS)
        )

    async def test_error_handling(self, repo, clean_memgraph):
        """Tests error handling with a real database."""
        # Try to add a chunk without its document
        chunk = create_test_chunk(document_id="nonexistent_doc")
        with pytest.raises(Exception):
            await repo.add_chunk(chunk)

        # Try to add a relationship with nonexistent entities
        entity1 = create_test_entity(entity_id="nonexistent_1")
        entity2 = create_test_entity(entity_id="nonexistent_2")
        relationship = create_test_relationship(entity1, entity2)
        with pytest.raises(Exception):
            await repo.add_relationship(relationship) 