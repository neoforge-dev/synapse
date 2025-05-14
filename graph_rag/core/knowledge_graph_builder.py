import logging
from abc import ABC, abstractmethod
from collections import defaultdict
from typing import Optional

from graph_rag.core.graph_store import GraphStore
from graph_rag.core.interfaces import (
    ChunkData,
    DocumentData,
    ExtractedEntity,
    ExtractedRelationship,
    KnowledgeGraphBuilder,
)
from graph_rag.models import ProcessedDocument

logger = logging.getLogger(__name__)


class KnowledgeGraphBuilder(ABC):
    """Abstract base class for building and updating the knowledge graph."""

    @abstractmethod
    def build(self, processed_document: ProcessedDocument):
        """Builds or updates the graph based on a processed document."""
        pass


class SimpleKnowledgeGraphBuilder(KnowledgeGraphBuilder):
    """A simple implementation that adds entities and relationships to a GraphStore."""

    def __init__(self, graph_store: GraphStore):
        if not isinstance(graph_store, GraphStore):
            raise TypeError("graph_store must be an instance of GraphStore")
        self._graph_store = graph_store
        logger.info(
            f"KnowledgeGraphBuilder initialized with graph store: {type(graph_store).__name__}"
        )

    async def build(self, processed_document: ProcessedDocument):
        """Adds the document's entities and relationships to the graph store."""
        doc_id = processed_document.id
        entities = processed_document.entities
        relationships = processed_document.relationships

        if not entities and not relationships:
            logger.info(
                f"No entities or relationships found in ProcessedDocument {doc_id}, nothing to add to graph."
            )
            return

        logger.info(
            f"Building graph for document {doc_id}: adding {len(entities)} entities and {len(relationships)} relationships."
        )

        try:
            # Use the bulk add method for efficiency
            await self._graph_store.add_entities_and_relationships(
                entities, relationships
            )
            logger.info(
                f"Successfully added entities/relationships from document {doc_id} to graph store."
            )
        except Exception as e:
            logger.error(
                f"Failed to add entities/relationships from document {doc_id} to graph store: {e}",
                exc_info=True,
            )
            # Depending on requirements, might re-raise or handle differently
            raise  # Re-raise the exception for now


class InMemoryKnowledgeGraphBuilder(KnowledgeGraphBuilder):
    """Stores graph elements purely in memory (dictionaries and sets)."""

    def __init__(self):
        self.documents: dict[str, DocumentData] = {}
        self.chunks: dict[str, ChunkData] = {}
        self.entities: dict[str, ExtractedEntity] = {}
        # Store relationships using a tuple key: (source_id, target_id, label)
        self.relationships: dict[tuple[str, str, str], ExtractedRelationship] = {}

        # Link structures
        self.doc_chunk_links: dict[str, set[str]] = defaultdict(set)
        self.chunk_doc_links: dict[str, Optional[str]] = {}
        self.chunk_entity_links: dict[str, set[str]] = defaultdict(set)
        self.entity_chunk_links: dict[str, set[str]] = defaultdict(set)

        logger.info("Initialized InMemoryKnowledgeGraphBuilder")

    async def add_document(self, doc: DocumentData) -> None:
        if doc.id in self.documents:
            logger.warning(f"Overwriting existing document {doc.id}")
        else:
            logger.debug(f"Adding document {doc.id}")
        self.documents[doc.id] = doc

    async def add_chunk(self, chunk: ChunkData) -> None:
        if chunk.id in self.chunks:
            logger.warning(f"Overwriting existing chunk {chunk.id}")
        else:
            logger.debug(f"Adding chunk {chunk.id} for document {chunk.document_id}")

        self.chunks[chunk.id] = chunk
        # Link chunk to its document
        if chunk.document_id:
            self.doc_chunk_links[chunk.document_id].add(chunk.id)
            self.chunk_doc_links[chunk.id] = chunk.document_id
        else:
            logger.warning(f"Chunk {chunk.id} added without a document_id.")

    async def add_entity(self, entity: ExtractedEntity) -> None:
        if entity.id in self.entities:
            # Simple overwrite for now. Could implement merging logic later.
            logger.debug(f"Updating existing entity {entity.id}")
        else:
            logger.debug(f"Adding entity {entity.id} ({entity.label})")
        self.entities[entity.id] = entity

    async def add_relationship(self, relationship: ExtractedRelationship) -> None:
        # Check if source/target entities exist (optional, depends on desired strictness)
        if relationship.source_entity_id not in self.entities:
            logger.warning(
                f"Source entity {relationship.source_entity_id} not found for relationship."
            )
            # Decide: skip or raise error?
            # return
        if relationship.target_entity_id not in self.entities:
            logger.warning(
                f"Target entity {relationship.target_entity_id} not found for relationship."
            )
            # return

        rel_key = (
            relationship.source_entity_id,
            relationship.target_entity_id,
            relationship.label,
        )
        if rel_key in self.relationships:
            logger.warning(f"Overwriting existing relationship: {rel_key}")
        else:
            logger.debug(f"Adding relationship: {rel_key}")

        self.relationships[rel_key] = relationship

    async def link_chunk_to_entities(
        self, chunk_id: str, entity_ids: list[str]
    ) -> None:
        if chunk_id not in self.chunks:
            logger.error(f"Cannot link entities to non-existent chunk {chunk_id}")
            return  # Or raise error

        valid_entity_ids = []
        for entity_id in entity_ids:
            if entity_id in self.entities:
                valid_entity_ids.append(entity_id)
                self.entity_chunk_links[entity_id].add(chunk_id)
            else:
                logger.warning(
                    f"Cannot link chunk {chunk_id} to non-existent entity {entity_id}"
                )

        if valid_entity_ids:
            self.chunk_entity_links[chunk_id].update(valid_entity_ids)
            logger.debug(f"Linked chunk {chunk_id} to entities: {valid_entity_ids}")
        else:
            logger.debug(f"No valid entities provided to link to chunk {chunk_id}")

    # Implementation of the abstract method from KnowledgeGraphBuilder ABC
    async def build(self, processed_document: ProcessedDocument):
        """Builds the in-memory graph from a processed document.
        Calls the existing async add methods.
        """
        logger.info(f"Building in-memory graph for document {processed_document.id}")

        if not processed_document.entities and not processed_document.relationships:
            logger.debug(
                f"No entities or relationships in {processed_document.id} to build."
            )
            return

        # Add entities (awaiting each call)
        for entity_model in processed_document.entities:
            # Convert graph_rag.models.Entity to interfaces.ExtractedEntity if necessary
            # Assuming they are compatible for now or handled by the caller
            # For InMemory, let's assume we store the model directly or adapt
            extracted_entity = ExtractedEntity(
                id=entity_model.id, label=entity_model.type, text=entity_model.name
            )
            await self.add_entity(extracted_entity)

        # Add relationships (awaiting each call)
        for relationship_model in processed_document.relationships:
            # Convert graph_rag.models.Relationship to interfaces.ExtractedRelationship
            extracted_relationship = ExtractedRelationship(
                source_entity_id=relationship_model.source.id,
                target_entity_id=relationship_model.target.id,
                label=relationship_model.type,
            )
            await self.add_relationship(extracted_relationship)

        # TODO: Potentially link chunks to entities if that info is in ProcessedDocument
        # chunk_links = ... # Get links from processed_document if available
        # for chunk_id, entity_ids in chunk_links.items():
        #     await self.link_chunk_to_entities(chunk_id, entity_ids)

        logger.info(
            f"Completed building in-memory graph for document {processed_document.id}"
        )
