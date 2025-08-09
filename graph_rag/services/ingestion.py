import logging
import re
import uuid
from typing import Any, Optional

from pydantic import BaseModel

from graph_rag.core.interfaces import (
    DocumentProcessor,
    EmbeddingService,
    EntityExtractor,
    GraphRepository,
    VectorStore,
)
from graph_rag.domain.models import Chunk, Document, Relationship

logger = logging.getLogger(__name__)


class IngestionResult(BaseModel):
    """Result of document ingestion process."""

    document_id: str
    chunk_ids: list[str]

    @property
    def num_chunks(self) -> int:
        return len(self.chunk_ids)


class IngestionService:
    """
    Service responsible for processing and ingesting documents into the graph store.
    """

    def __init__(
        self,
        document_processor: DocumentProcessor,
        entity_extractor: EntityExtractor,
        graph_store: GraphRepository,
        embedding_service: EmbeddingService,
        vector_store: VectorStore,
    ):
        """
        Initializes the IngestionService.

        Args:
            document_processor: An instance of DocumentProcessor for processing documents.
            entity_extractor: An instance of EntityExtractor for extracting entities from documents.
            graph_store: An instance of GraphRepository for storing entities and relationships.
            embedding_service: An instance of EmbeddingService for generating embeddings.
            vector_store: An instance of VectorStore for storing chunk vectors.
        """
        self.document_processor = document_processor
        self.entity_extractor = entity_extractor
        self.graph_store = graph_store
        self.embedding_service = embedding_service
        self.vector_store = vector_store
        logger.info(
            f"IngestionService initialized with processor: {type(document_processor).__name__}, \
            extractor: {type(entity_extractor).__name__}, store: {type(graph_store).__name__}, \
            vector_store: {type(vector_store).__name__}"
        )

    async def ingest_document(
        self,
        document_id: str,
        content: str,
        metadata: dict[str, Any],
        max_tokens_per_chunk: Optional[int] = None,
        generate_embeddings: bool = True,  # Add flag to control embedding generation
        replace_existing: bool = True,
    ) -> IngestionResult:
        """
        Ingest a document: store it, chunk it, generate embeddings, and create relationships.

        Args:
            document_id: The unique ID for the document.
            content: The document content
            metadata: Additional metadata about the document
            max_tokens_per_chunk: Optional max tokens per chunk (defaults to paragraph splitting)
            generate_embeddings: Whether to generate and store embeddings for chunks.

        Returns:
            IngestionResult with document and chunk IDs
        """
        print(f"DEBUG: IngestionService.ingest_document called for doc {document_id}")
        id_source = None
        try:
            if isinstance(metadata, dict):
                id_source = metadata.get("id_source")
        except Exception:
            id_source = None
        logger.info(
            (
                "Starting ingestion for document %s | id_source=%s | replace_existing=%s"
            ),
            document_id,
            id_source,
            replace_existing,
        )
        # Normalize and/or derive topics before persisting document and chunking
        topics = self._extract_topics(content=content, metadata=metadata)
        if topics:
            # Copy to avoid mutating caller's dict
            metadata = dict(metadata)
            # Deduplicate while preserving order
            seen = set()
            normalized_topics: list[str] = []
            for t in topics:
                if not t:
                    continue
                key = t.strip()
                if key and key not in seen:
                    seen.add(key)
                    normalized_topics.append(key)
            if normalized_topics:
                metadata["topics"] = normalized_topics
        # Optionally replace existing chunks and vectors for idempotent re-ingestion
        if replace_existing:
            try:
                existing_chunks = await self.graph_store.get_chunks_by_document_id(
                    document_id
                )
                if existing_chunks:
                    old_chunk_ids = [c.id for c in existing_chunks]
                    logger.info(
                        "Pre-delete for %s: deleting %d existing chunks",
                        document_id,
                        len(old_chunk_ids),
                    )
                    # Delete chunks in graph by relationship, leaving the Document node
                    try:
                        # Use repository method if available; otherwise direct query via execute_query
                        await self.graph_store.execute_query(
                            """
                            MATCH (d:Document {id: $doc_id})-[:CONTAINS]->(c:Chunk)
                            DETACH DELETE c
                            """,
                            {"doc_id": document_id},
                        )
                    except Exception:
                        logger.debug("Graph chunk deletion step failed or unsupported; continuing")
                    # Delete from vector store best-effort
                    try:
                        await self.vector_store.delete_chunks(old_chunk_ids)
                        logger.info(
                            "Vector store: deleted %d chunks for %s",
                            len(old_chunk_ids),
                            document_id,
                        )
                    except Exception as vs_del_err:
                        logger.debug(
                            f"Vector store chunk deletion skipped/failed: {vs_del_err}"
                        )
            except Exception as pre_err:
                logger.debug(
                    f"Pre-ingestion replace_existing probe failed for {document_id}: {pre_err}"
                )

        # 1. Create and save document using the provided ID
        document = Document(id=document_id, content=content, metadata=metadata)
        try:
            # Use the specific add_document method for Document objects
            print(
                f"DEBUG: About to call graph_store.add_document for doc {document_id}"
            )
            await self.graph_store.add_document(document)
            print(f"DEBUG: Finished graph_store.add_document for doc {document_id}")
            # add_document doesn't return the ID, we already have it
            # if saved_doc_id != document_id:
            #      # Log a warning if the returned ID is different (unexpected)
            #      logger.warning(f"Saved document ID '{saved_doc_id}' differs from provided ID '{document_id}'. Using provided ID.")
            logger.info(f"Saved document with ID: {document_id}")
        except Exception as e:
            logger.error(f"Failed to save document {document_id}: {e}", exc_info=True)
            raise  # Re-raise to signal failure

        # 2. Split content into chunks
        chunk_objects = await self._split_into_chunks(document, max_tokens_per_chunk)
        logger.info(
            "Chunking result for %s: %d chunks",
            document_id,
            len(chunk_objects),
        )

        # 3. Generate embeddings (if requested)
        if self.embedding_service and generate_embeddings:
            logger.info(
                "Generating embeddings for %s: %d chunks",
                document_id,
                len(chunk_objects),
            )
            chunk_texts = [c.text for c in chunk_objects]
            try:
                # Ensure the call to encode is awaited
                embeddings = await self.embedding_service.encode(chunk_texts)
                # Check if the lengths match before assigning embeddings
                if embeddings and len(embeddings) == len(chunk_objects):
                    for i, chunk in enumerate(chunk_objects):
                        chunk.embedding = embeddings[i]
                        # Ensure metadata exists and add document_id to it safely
                        if not hasattr(chunk, "metadata") or chunk.metadata is None:
                            chunk.metadata = {}
                        chunk.metadata["document_id"] = document_id
                    logger.info("Embeddings generated successfully.")

                    # Add chunks to vector store *after* embeddings are assigned (if generated)
                    try:
                        await self.vector_store.add_chunks(chunk_objects)
                        logger.info(
                            "Vector store: added %d chunks for %s",
                            len(chunk_objects),
                            document_id,
                        )
                    except Exception as vs_e:
                        logger.error(
                            f"Failed to add chunks to vector store: {vs_e}",
                            exc_info=True,
                        )
                        # Decide handling: maybe continue without vector store addition?
                        # For now, log and continue.

                else:
                    logger.error(
                        f"Mismatch between number of chunks ({len(chunk_objects)}) and generated embeddings ({len(embeddings) if embeddings else 0}). Skipping embedding assignment."
                    )
            except AttributeError as ae:
                logger.error(
                    f"Failed to generate embeddings for document {document_id}: Embedding service missing 'encode' method or similar error: {ae}",
                    exc_info=True,
                )
                # Decide how to handle: skip embeddings, raise error?
                # For now, log error and continue without embeddings
            except Exception as e:
                logger.error(
                    f"Failed to generate embeddings for document {document_id}: {e}",
                    exc_info=True,
                )
                # Decide how to handle: skip embeddings, raise error?
                # For now, log error and continue without embeddings

        # 4. Save chunks and create relationships
        chunk_ids = []
        for chunk in chunk_objects:
            try:
                # Ensure embedding field exists even if generation failed/skipped
                if not hasattr(chunk, "embedding"):
                    chunk.embedding = None

                # --- Add debug print here ---
                print(
                    f"DEBUG: Before save_chunk - Chunk ID: {chunk.id}, Embedding is None: {chunk.embedding is None}"
                )
                if chunk.embedding is not None:
                    # Limit printing large embeddings
                    embedding_preview = str(chunk.embedding[:5]) + (
                        "..." if len(chunk.embedding) > 5 else ""
                    )
                    print(f"DEBUG: Embedding value preview: {embedding_preview}")

                # Use add_chunk for Chunk objects
                await self.graph_store.add_chunk(chunk)
                # Add the chunk's ID to the list
                chunk_ids.append(chunk.id)

                # Create relationship: Document CONTAINS Chunk
                # Relationship needs source/target IDs and type
                # Use Relationship model (alias for Edge) consistent with add_relationship signature
                rel = Relationship(
                    id=str(uuid.uuid4()),
                    type="CONTAINS",
                    source_id=document_id,
                    target_id=chunk.id,  # Use chunk.id
                )
                await self.graph_store.add_relationship(rel)
            except Exception as e:
                logger.error(
                    f"Failed to save chunk {chunk.id} or its relationship for document {document_id}: {e}",
                    exc_info=True,
                )
                # Optionally collect failed chunk IDs or raise immediately
                # For now, continue processing other chunks

        # 4b. Project topics as nodes and link to document and chunks
        try:
            topics_in_meta = []
            if document.metadata and isinstance(document.metadata.get("topics"), list):
                topics_in_meta = [str(t).strip() for t in document.metadata["topics"] if str(t).strip()]
            if topics_in_meta:
                # Deduplicate topics
                seen_topic_ids: set[str] = set()
                for topic in topics_in_meta:
                    topic_id = f"topic:{topic.lower()}"
                    if topic_id in seen_topic_ids:
                        continue
                    seen_topic_ids.add(topic_id)
                    # Create/Upsert topic entity
                    try:
                        await self.graph_store.add_entity(
                            Entity(
                                id=topic_id,
                                name=topic,
                                type="Topic",
                                properties={},
                            )
                        )
                    except Exception:
                        # Continue even if topic add fails
                        logger.debug("Skipping topic add failure for %s", topic_id)

                    # Link document -> topic
                    try:
                        await self.graph_store.add_relationship(
                            Relationship(
                                id=str(uuid.uuid4()),
                                type="HAS_TOPIC",
                                source_id=document_id,
                                target_id=topic_id,
                            )
                        )
                    except Exception:
                        logger.debug("Skipping HAS_TOPIC relationship failure for %s", topic_id)

                    # Link each chunk -> topic (mentions)
                    for chunk in chunk_objects:
                        try:
                            await self.graph_store.add_relationship(
                                Relationship(
                                    id=str(uuid.uuid4()),
                                    type="MENTIONS_TOPIC",
                                    source_id=chunk.id,
                                    target_id=topic_id,
                                )
                            )
                        except Exception:
                            logger.debug(
                                "Skipping MENTIONS_TOPIC relationship failure for chunk %s -> %s",
                                chunk.id,
                                topic_id,
                            )
        except Exception as topic_err:
            logger.debug("Topic projection skipped due to error: %s", topic_err)

        logger.info(
            f"Ingestion complete for document {document_id}. Saved {len(chunk_ids)} chunks."
        )
        # 5. Return result
        return IngestionResult(document_id=document_id, chunk_ids=chunk_ids)

    def _extract_topics(self, content: str, metadata: dict[str, Any]) -> list[str]:
        """Derive topics from metadata or content heuristics.

        Priority:
        1) If metadata already contains topics (list or str), normalize and return
        2) Else, use the first Markdown heading (# or ##) as a single topic
        3) Else, return empty list
        """
        # From metadata
        if metadata is not None:
            meta_topics = metadata.get("topics") or metadata.get("Tags") or metadata.get("tags")
            if meta_topics:
                if isinstance(meta_topics, list):
                    return [str(t).strip().lstrip("#") for t in meta_topics if str(t).strip()]
                if isinstance(meta_topics, str):
                    # Split by comma or hashtag-separated words
                    if "," in meta_topics:
                        return [s.strip().lstrip("#") for s in meta_topics.split(",") if s.strip()]
                    if "#" in meta_topics:
                        return [s.strip().lstrip("#") for s in meta_topics.split() if s.strip()]
                    return [meta_topics.strip()] if meta_topics.strip() else []

        # From first heading in content
        if content:
            for line in content.splitlines():
                line = line.strip()
                if line.startswith("# ") or line.startswith("## "):
                    heading = line.lstrip("#").strip()
                    if heading:
                        return [heading]
                if line:
                    # Stop after a few non-empty lines to avoid scanning entire document
                    pass
        return []

    async def _split_into_chunks(
        self, document: Document, max_tokens_per_chunk: int | None = None
    ) -> list[Chunk]:
        """Helper method to split document content into chunks."""
        try:
            chunks: list[
                Chunk
            ] = await self.document_processor.chunk_document(  # Await here
                document.content,
                document_id=document.id,
                metadata=document.metadata,
                max_tokens_per_chunk=max_tokens_per_chunk,  # Pass the override
            )
            # logger.info(f"Document {document.id} split into {len(chunks)} chunks.") # This line caused the error
            logger.info(
                f"Document {document.id} split into {len(chunks)} chunks."
            )  # Log after awaiting
            return chunks
        except Exception as e:
            logger.error(f"Error splitting document {document.id}: {e}")
            # Depending on desired behavior, might re-raise or return empty list
            return []

    def _split_into_chunks_old(
        self, content: str, document_id: str, max_tokens_per_chunk: Optional[int] = None
    ) -> list[Chunk]:
        """
        Split document content into chunks.

        Args:
            content: The document content to split
            document_id: ID of the parent document
            max_tokens_per_chunk: Max tokens per chunk (if provided)

        Returns:
            List of Chunk objects
        """
        chunks = []

        # Option 1: Split by paragraphs (default)
        if max_tokens_per_chunk is None:
            # Simple paragraph splitting (double newlines)
            paragraphs = re.split(r"\n\s*\n", content)
            paragraphs = [p.strip() for p in paragraphs if p.strip()]

            for paragraph in paragraphs:
                chunks.append(
                    Chunk(
                        id=str(uuid.uuid4()),
                        content=paragraph,
                        document_id=document_id,
                        # embedding added later
                    )
                )

        # Option 2: Split by token count
        else:
            # Simple word-based token splitting for now
            # In a real implementation, we'd use a proper tokenizer
            words = content.split()

            for i in range(0, len(words), max_tokens_per_chunk):
                chunk_content = " ".join(words[i : i + max_tokens_per_chunk])
                chunks.append(
                    Chunk(
                        id=str(uuid.uuid4()),
                        content=chunk_content,
                        document_id=document_id,
                        # embedding added later
                    )
                )

        return chunks
