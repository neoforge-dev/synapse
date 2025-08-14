"""Mock graph store implementation for development and graceful fallbacks."""

import logging
from typing import Any

from graph_rag.core.graph_store import GraphStore
from graph_rag.core.interfaces import ExtractedEntity, GraphRepository
from graph_rag.models import Chunk, Document, Entity, Relationship

logger = logging.getLogger(__name__)


class MockGraphRepository(GraphStore, GraphRepository):
    """Mock implementation of GraphStore and GraphRepository for graceful fallbacks."""

    def __init__(self):
        """Initialize mock repository with in-memory storage."""
        self._documents: dict[str, Document] = {}
        self._chunks: dict[str, Chunk] = {}
        self._entities: dict[str, Entity] = {}
        self._relationships: dict[str, Relationship] = {}
        logger.info("MockGraphRepository initialized (graph operations will be no-ops)")

    async def connect(self) -> None:
        """Connect to repository (no-op for mock)."""
        logger.debug("MockGraphRepository: Connecting (no-op)")

    async def add_document(self, document: Document) -> None:
        """Store document in memory."""
        self._documents[document.id] = document
        logger.debug(f"MockGraphRepository: Stored document {document.id}")

    async def get_document(self, document_id: str) -> Document | None:
        """Retrieve document from memory."""
        doc = self._documents.get(document_id)
        logger.debug(f"MockGraphRepository: Retrieved document {document_id}: {'found' if doc else 'not found'}")
        return doc

    async def get_documents(
        self, limit: int | None = None, offset: int = 0
    ) -> list[Document]:
        """Get all documents with pagination."""
        docs = list(self._documents.values())
        if limit:
            docs = docs[offset:offset + limit]
        else:
            docs = docs[offset:]
        logger.debug(f"MockGraphRepository: Retrieved {len(docs)} documents")
        return docs

    async def delete_document(self, document_id: str) -> bool:
        """Delete document and related chunks."""
        if document_id not in self._documents:
            return False

        # Delete document
        del self._documents[document_id]

        # Delete related chunks
        chunks_to_delete = [
            chunk_id for chunk_id, chunk in self._chunks.items()
            if chunk.document_id == document_id
        ]
        for chunk_id in chunks_to_delete:
            del self._chunks[chunk_id]

        logger.debug(f"MockGraphRepository: Deleted document {document_id} and {len(chunks_to_delete)} chunks")
        return True

    async def update_document_metadata(
        self, document_id: str, metadata: dict[str, Any]
    ) -> bool:
        """Update document metadata."""
        if document_id not in self._documents:
            return False

        doc = self._documents[document_id]
        if doc.metadata:
            doc.metadata.update(metadata)
        else:
            doc.metadata = metadata.copy()

        logger.debug(f"MockGraphRepository: Updated metadata for document {document_id}")
        return True

    async def add_chunk(self, chunk: Chunk) -> None:
        """Store chunk in memory."""
        self._chunks[chunk.id] = chunk
        logger.debug(f"MockGraphRepository: Stored chunk {chunk.id}")

    async def get_chunk(self, chunk_id: str) -> Chunk | None:
        """Retrieve chunk from memory."""
        chunk = self._chunks.get(chunk_id)
        logger.debug(f"MockGraphRepository: Retrieved chunk {chunk_id}: {'found' if chunk else 'not found'}")
        return chunk

    async def get_chunks_by_document(self, document_id: str) -> list[Chunk]:
        """Get all chunks for a document."""
        chunks = [
            chunk for chunk in self._chunks.values()
            if chunk.document_id == document_id
        ]
        logger.debug(f"MockGraphRepository: Found {len(chunks)} chunks for document {document_id}")
        return chunks

    async def delete_chunks_by_document(self, document_id: str) -> int:
        """Delete all chunks for a document."""
        chunks_to_delete = [
            chunk_id for chunk_id, chunk in self._chunks.items()
            if chunk.document_id == document_id
        ]

        for chunk_id in chunks_to_delete:
            del self._chunks[chunk_id]

        logger.debug(f"MockGraphRepository: Deleted {len(chunks_to_delete)} chunks for document {document_id}")
        return len(chunks_to_delete)

    async def add_entity(self, entity: Entity) -> None:
        """Store entity in memory (no-op for mock)."""
        self._entities[entity.id] = entity
        logger.debug(f"MockGraphRepository: Stored entity {entity.id} (no-op)")

    async def get_entity(self, entity_id: str) -> Entity | None:
        """Retrieve entity from memory."""
        entity = self._entities.get(entity_id)
        logger.debug(f"MockGraphRepository: Retrieved entity {entity_id}: {'found' if entity else 'not found'}")
        return entity

    async def search_entities_by_properties(
        self, entities: list[ExtractedEntity], limit: int = 10
    ) -> list[Entity]:
        """Search entities by properties (returns empty for mock)."""
        logger.debug(f"MockGraphRepository: Entity search for {len(entities)} entities (returning empty)")
        return []

    async def add_relationship(self, relationship: Relationship) -> None:
        """Store relationship in memory (no-op for mock)."""
        self._relationships[relationship.id] = relationship
        logger.debug(f"MockGraphRepository: Stored relationship {relationship.id} (no-op)")

    async def get_relationship(self, relationship_id: str) -> Relationship | None:
        """Retrieve relationship from memory."""
        rel = self._relationships.get(relationship_id)
        logger.debug(f"MockGraphRepository: Retrieved relationship {relationship_id}: {'found' if rel else 'not found'}")
        return rel

    async def get_neighbors(
        self, entity_ids: list[str], limit: int = 10
    ) -> tuple[list[Entity], list[Relationship]]:
        """Get neighboring entities and relationships (returns empty for mock)."""
        logger.debug(f"MockGraphRepository: Neighbor search for {len(entity_ids)} entities (returning empty)")
        return [], []

    async def link_chunk_to_entities(
        self, chunk_id: str, entity_ids: list[str]
    ) -> None:
        """Link chunk to entities (no-op for mock)."""
        logger.debug(f"MockGraphRepository: Linking chunk {chunk_id} to {len(entity_ids)} entities (no-op)")

    async def close(self) -> None:
        """Close repository (no-op for mock)."""
        logger.debug("MockGraphRepository: Closing connection (no-op)")

    async def health_check(self) -> dict[str, Any]:
        """Return health status."""
        return {
            "status": "healthy",
            "type": "mock",
            "documents": len(self._documents),
            "chunks": len(self._chunks),
            "entities": len(self._entities),
            "relationships": len(self._relationships),
        }

    # GraphStore interface methods (synchronous)
    def add_entity(self, entity: Entity):
        """Adds or updates an entity (node) in the graph."""
        self._entities[entity.id] = entity
        logger.debug(f"MockGraphRepository: Added entity {entity.id} (sync)")

    def add_relationship(self, relationship: Relationship):
        """Adds a relationship (edge) between two entities."""
        async def _add_relationship():
            self._relationships[relationship.id] = relationship
            logger.debug(f"MockGraphRepository: Added relationship {relationship.id} (sync->async)")
        return _add_relationship()

    def add_entities_and_relationships(
        self, entities: list[Entity], relationships: list[Relationship]
    ):
        """Adds multiple entities and relationships."""
        for entity in entities:
            self.add_entity(entity)
        for relationship in relationships:
            self.add_relationship(relationship)
        logger.debug(f"MockGraphRepository: Added {len(entities)} entities and {len(relationships)} relationships (sync)")

    # Removed sync add_document - conflicts with async version

    # Removed sync add_chunk - conflicts with async version

    def get_entity_by_id(self, entity_id: str) -> Entity | None:
        """Retrieves a single entity by its unique ID."""
        entity = self._entities.get(entity_id)
        logger.debug(f"MockGraphRepository: Retrieved entity {entity_id}: {'found' if entity else 'not found'} (sync)")
        return entity

    def get_document_by_id(self, document_id: str):
        """Retrieves a document by its ID (sync version for GraphStore interface)."""
        # Note: This conflicts with async version, but GraphStore interface requires it
        doc = self._documents.get(document_id)
        logger.debug(f"MockGraphRepository: Retrieved document {document_id}: {'found' if doc else 'not found'} (sync)")
        return doc

    def get_neighbors(
        self,
        entity_id: str,
        relationship_types: list[str] | None = None,
        direction: str = "both",
    ) -> tuple[list[Entity], list[Relationship]]:
        """Retrieves direct neighbors (entities and relationships) of a given entity."""
        logger.debug(f"MockGraphRepository: Getting neighbors for {entity_id} (returning empty lists) (sync)")
        return [], []

    def search_entities_by_properties(
        self, properties: dict[str, Any], limit: int | None = None
    ) -> list[Entity]:
        """Searches for entities matching specific properties."""
        matching_entities = []
        if "name" in properties:
            name_query = properties["name"].lower()
            for entity in self._entities.values():
                if name_query in entity.name.lower():
                    matching_entities.append(entity)
        if limit:
            matching_entities = matching_entities[:limit]
        logger.debug(f"MockGraphRepository: Found {len(matching_entities)} entities matching properties (sync)")
        return matching_entities
