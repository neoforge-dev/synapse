import logging
from datetime import datetime, timezone

from graph_rag.core.interfaces import (
    ChunkData,
    DocumentData,
    ExtractedEntity,
    ExtractedRelationship,
    KnowledgeGraphBuilder,
)  # Added GraphRepository
from graph_rag.infrastructure.graph_stores.memgraph_store import (
    MemgraphGraphRepository,
)  # Corrected class name

logger = logging.getLogger(__name__)


class PersistentKnowledgeGraphBuilder(KnowledgeGraphBuilder):
    """Builds the knowledge graph using a persistent MemgraphStore."""

    def __init__(self, graph_store: MemgraphGraphRepository):
        self.graph_store = graph_store
        logger.info("Initialized PersistentKnowledgeGraphBuilder")

    async def add_document(self, doc: DocumentData) -> None:
        logger.debug(f"Adding/merging document node {doc.id} to persistent store.")
        try:
            # Prepare properties suitable for MemgraphStore.add_node
            # Ensure timestamps are strings, metadata is dict (will be handled by store's mapping later)
            doc_props = {
                "id": doc.id,
                "content": doc.content,
                "metadata": doc.metadata,  # Pass the dict directly
                "created_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }
            await self.graph_store.add_node(label="Document", properties=doc_props)
        except Exception as e:
            logger.error(
                f"Failed to add document {doc.id} to graph store: {e}", exc_info=True
            )
            raise  # Re-raise to signal failure

    async def add_chunk(self, chunk: ChunkData) -> None:
        logger.debug(
            f"Adding/merging chunk node {chunk.id} for doc {chunk.document_id} to persistent store."
        )
        try:
            chunk_props = {
                "id": chunk.id,
                "text": chunk.text,
                "document_id": chunk.document_id,
                "embedding": chunk.embedding,  # Pass embedding list directly
                "created_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }
            await self.graph_store.add_node(label="Chunk", properties=chunk_props)

            # Add relationship from Document to Chunk
            if chunk.document_id:
                await self.graph_store.add_relationship(
                    source_node_id=chunk.document_id,
                    target_node_id=chunk.id,
                    rel_type="CONTAINS",  # Define relationship type
                    properties={"created_at": datetime.now(timezone.utc).isoformat()},
                )
                logger.debug(
                    f"Linked Document {chunk.document_id} -[:CONTAINS]-> Chunk {chunk.id}"
                )
        except Exception as e:
            logger.error(
                f"Failed to add chunk {chunk.id} or link to document: {e}",
                exc_info=True,
            )
            raise

    async def add_entity(self, entity: ExtractedEntity) -> None:
        logger.debug(
            f"Adding/merging entity node {entity.id} ({entity.label}) to persistent store."
        )
        try:
            entity_props = {
                "id": entity.id,
                "label": entity.label,
                "text": entity.text,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }
            # Use the entity's label (e.g., PER, ORG) as the graph node label
            await self.graph_store.add_node(label=entity.label, properties=entity_props)
        except Exception as e:
            logger.error(f"Failed to add entity {entity.id}: {e}", exc_info=True)
            raise

    async def add_relationship(self, relationship: ExtractedRelationship) -> None:
        logger.debug(
            f"Adding relationship {relationship.source_entity_id} -[:{relationship.label}]-> {relationship.target_entity_id}"
        )
        try:
            rel_props = {
                "created_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat(),
                # Add any other properties from the relationship object if needed
            }
            await self.graph_store.add_relationship(
                source_node_id=relationship.source_entity_id,
                target_node_id=relationship.target_entity_id,
                rel_type=relationship.label,
                properties=rel_props,
            )
        except Exception as e:
            # Catch potential errors if source/target nodes don't exist (depends on graph_store implementation)
            logger.error(
                f"Failed to add relationship {relationship.label} between {relationship.source_entity_id} and {relationship.target_entity_id}: {e}",
                exc_info=True,
            )
            raise

    async def link_chunk_to_entities(
        self, chunk_id: str, entity_ids: list[str]
    ) -> None:
        logger.debug(f"Linking chunk {chunk_id} to entities: {entity_ids}")
        link_props = {"created_at": datetime.now(timezone.utc).isoformat()}
        errors = []
        for entity_id in entity_ids:
            try:
                await self.graph_store.add_relationship(
                    source_node_id=chunk_id,
                    target_node_id=entity_id,
                    rel_type="MENTIONS",  # Define relationship type
                    properties=link_props,
                )
                logger.debug(
                    f"Linked Chunk {chunk_id} -[:MENTIONS]-> Entity {entity_id}"
                )
            except Exception as e:
                # Log error and continue trying to link other entities
                logger.error(
                    f"Failed to link chunk {chunk_id} to entity {entity_id}: {e}",
                    exc_info=False,
                )
                errors.append(entity_id)

        if errors:
            # Optionally raise a summary error or just log
            logger.warning(
                f"Failed to link chunk {chunk_id} to some entities: {errors}"
            )
            # raise RuntimeError(f"Failed to link chunk {chunk_id} to entities: {errors}")
