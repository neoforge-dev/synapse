import asyncio
import logging
import re
import time
import uuid
from typing import Any

from pydantic import BaseModel

from graph_rag.api.errors import (
    EmbeddingServiceError,
    MemgraphConnectionError,
    VectorStoreError,
    handle_ingestion_error,
)
from graph_rag.api.metrics import (
    inc_ingested_chunks,
    inc_ingested_vectors,
    observe_ingest_latency,
)
from graph_rag.core.interfaces import (
    DocumentProcessor,
    EmbeddingService,
    EntityExtractor,
    ExtractedEntity,
    GraphRepository,
    VectorStore,
)
from graph_rag.core.interfaces import (
    ImageProcessor as ImageProcessorProtocol,
)
from graph_rag.core.interfaces import (
    PDFAnalyzer as PDFAnalyzerProtocol,
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
        image_processor: ImageProcessorProtocol | None = None,
        pdf_analyzer: PDFAnalyzerProtocol | None = None,
    ):
        """
        Initializes the IngestionService.

        Args:
            document_processor: An instance of DocumentProcessor for processing documents.
            entity_extractor: An instance of EntityExtractor for extracting entities from documents.
            graph_store: An instance of GraphRepository for storing entities and relationships.
            embedding_service: An instance of EmbeddingService for generating embeddings.
            vector_store: An instance of VectorStore for storing chunk vectors.
            image_processor: Optional ImageProcessor for OCR text extraction from images.
            pdf_analyzer: Optional PDFAnalyzer for extracting content from PDFs with images.
        """
        self.document_processor = document_processor
        self.entity_extractor = entity_extractor
        self.graph_store = graph_store
        self.embedding_service = embedding_service
        self.vector_store = vector_store
        self.image_processor = image_processor
        self.pdf_analyzer = pdf_analyzer
        vision_info = ""
        if self.image_processor:
            vision_info += f", image_processor: {type(image_processor).__name__}"
        if self.pdf_analyzer:
            vision_info += f", pdf_analyzer: {type(pdf_analyzer).__name__}"

        logger.info(
            f"IngestionService initialized with processor: {type(document_processor).__name__}, "
            f"extractor: {type(entity_extractor).__name__}, store: {type(graph_store).__name__}, "
            f"vector_store: {type(vector_store).__name__}{vision_info}"
        )

    async def ingest_document(
        self,
        document_id: str,
        content: str,
        metadata: dict[str, Any],
        max_tokens_per_chunk: int | None = None,
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
        logger.debug(
            "IngestionService.ingest_document called for doc %s", document_id
        )
        start_ts = time.monotonic()
        id_source = None
        try:
            if isinstance(metadata, dict):
                id_source = metadata.get("id_source")
        except Exception:
            id_source = None
        logger.info(
            ("Starting ingestion for document %s | id_source=%s | replace_existing=%s"),
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
        vectors_deleted_attempted = 0
        if replace_existing:
            try:
                existing_chunks = await self.graph_store.get_chunks_by_document_id(
                    document_id
                )
                if existing_chunks:
                    old_chunk_ids = [c.id for c in existing_chunks]
                    vectors_deleted_attempted = len(old_chunk_ids)
                    logger.info(
                        "Pre-delete: doc_id=%s id_source=%s existing_chunks=%d",
                        document_id,
                        id_source,
                        len(old_chunk_ids),
                    )
                    # Delete chunks in graph by relationship, leaving the Document node
                    try:
                        # Use repository method if available; otherwise direct query via execute_query
                        await self._retry(
                            lambda: self.graph_store.execute_query(
                                """
                                MATCH (d:Document {id: $doc_id})-[:CONTAINS]->(c:Chunk)
                                DETACH DELETE c
                                """,
                                {"doc_id": document_id},
                            ),
                            attempts=3,
                            base_delay=0.2,
                        )
                    except Exception:
                        logger.debug(
                            "Graph chunk deletion step failed or unsupported; continuing"
                        )
                    # Delete from vector store best-effort with retry/backoff
                    try:
                        await self._retry(
                            lambda: self.vector_store.delete_chunks(old_chunk_ids),
                            attempts=3,
                            base_delay=0.2,
                        )
                        logger.info(
                            "Vector delete: doc_id=%s id_source=%s deleted_chunks=%d",
                            document_id,
                            id_source,
                            len(old_chunk_ids),
                        )
                    except Exception as vs_del_err:
                        logger.warning(
                            "Vector delete failed: doc_id=%s id_source=%s error=%s",
                            document_id,
                            id_source,
                            vs_del_err,
                        )
            except Exception as pre_err:
                logger.debug(
                    f"Pre-ingestion replace_existing probe failed for {document_id}: {pre_err}"
                )

        # 0. Enhance content with vision processing if applicable
        enhanced_content, enhanced_metadata = await self._process_vision_content(
            content, metadata, document_id
        )

        # 1. Create and save document using the provided ID
        document = Document(id=document_id, content=enhanced_content, metadata=enhanced_metadata)
        try:
            # Use the specific add_document method for Document objects
            logger.debug(
                "About to call graph_store.add_document for doc %s", document_id
            )
            await self._retry(
                lambda: self.graph_store.add_document(document),
                attempts=3,
                base_delay=0.2,
            )
            logger.debug(
                "Finished graph_store.add_document for doc %s", document_id
            )
            # add_document doesn't return the ID, we already have it
            # if saved_doc_id != document_id:
            #      # Log a warning if the returned ID is different (unexpected)
            #      logger.warning(f"Saved document ID '{saved_doc_id}' differs from provided ID '{document_id}'. Using provided ID.")
            logger.info(f"Saved document with ID: {document_id}")
        except Exception as e:
            logger.error(f"Failed to save document {document_id}: {e}", exc_info=True)
            # Classify and enhance the error
            if "connection" in str(e).lower() or "memgraph" in str(e).lower():
                raise MemgraphConnectionError(reason=f"Failed to save document: {e}") from e
            else:
                handle_ingestion_error(e, document_id, "document_storage")

        # 2. Split content into chunks
        chunk_objects = await self._split_into_chunks(document, max_tokens_per_chunk)
        logger.info(
            "Chunking result for %s: %d chunks",
            document_id,
            len(chunk_objects),
        )

        # 3. Generate embeddings (if requested)
        vectors_added_expected = 0
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
                    # Count how many will be added to vector store
                    vectors_added_expected = sum(
                        1 for c in chunk_objects if c.embedding is not None
                    )

                    # Add chunks to vector store *after* embeddings are assigned (if generated)
                    try:
                        await self._retry(
                            lambda: self.vector_store.add_chunks(chunk_objects),
                            attempts=3,
                            base_delay=0.2,
                        )
                        logger.info(
                            "Vector store: added %d chunks for %s",
                            len(chunk_objects),
                            document_id,
                        )
                        # Metrics: vectors attempted added
                        try:
                            inc_ingested_vectors(vectors_added_expected)
                        except Exception:
                            pass
                    except Exception as vs_e:
                        logger.error(
                            f"Failed to add chunks to vector store: {vs_e}",
                            exc_info=True,
                        )
                        # Check if this is a critical vector store error
                        error_msg = str(vs_e).lower()
                        if any(keyword in error_msg for keyword in ["disk", "space", "memory", "faiss"]):
                            raise VectorStoreError(operation="add_chunks", reason=str(vs_e)) from vs_e
                        else:
                            # Log warning and continue - vector search won't work but graph search will
                            logger.warning(f"Vector store unavailable, continuing with graph-only mode: {vs_e}")

                else:
                    logger.error(
                        f"Mismatch between number of chunks ({len(chunk_objects)}) and generated embeddings ({len(embeddings) if embeddings else 0}). Skipping embedding assignment."
                    )
            except AttributeError as ae:
                logger.error(
                    f"Failed to generate embeddings for document {document_id}: Embedding service missing 'encode' method or similar error: {ae}",
                    exc_info=True,
                )
                # Raise specific embedding service error with recovery suggestions
                raise EmbeddingServiceError(reason=f"Embedding service configuration error: {ae}") from ae
            except Exception as e:
                logger.error(
                    f"Failed to generate embeddings for document {document_id}: {e}",
                    exc_info=True,
                )
                # Check if this is a recoverable embedding error
                error_msg = str(e).lower()
                if any(keyword in error_msg for keyword in ["memory", "cuda", "torch", "model"]):
                    raise EmbeddingServiceError(reason=str(e)) from e
                else:
                    # For other errors, continue without embeddings but warn user
                    logger.warning(f"Continuing ingestion without embeddings due to error: {e}")

        # 4. Extract entities from chunks and store them
        await self._extract_and_store_entities(chunk_objects, document_id)

        # 5. Save chunks and create relationships
        chunk_ids = []
        for chunk in chunk_objects:
            try:
                # Ensure embedding field exists even if generation failed/skipped
                if not hasattr(chunk, "embedding"):
                    chunk.embedding = None

                # --- Debug logging (no stdout noise) ---
                logger.debug(
                    "Before save_chunk id=%s embedding_is_none=%s",
                    chunk.id,
                    chunk.embedding is None,
                )

                # Use add_chunk for Chunk objects
                await self._retry(
                    lambda: self.graph_store.add_chunk(chunk),
                    attempts=3,
                    base_delay=0.2,
                )
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
                await self._retry(
                    lambda: self.graph_store.add_relationship(rel),
                    attempts=3,
                    base_delay=0.2,
                )
            except Exception as e:
                logger.error(
                    f"Failed to save chunk {chunk.id} or its relationship for document {document_id}: {e}",
                    exc_info=True,
                )
                # Classify the error
                error_msg = str(e).lower()
                if "connection" in error_msg or "memgraph" in error_msg:
                    raise MemgraphConnectionError(reason=f"Failed to save chunk: {e}") from e
                else:
                    # For other errors, continue processing but warn
                    logger.warning(f"Skipping chunk {chunk.id} due to error: {e}")

        # 4b. Project topics as nodes and link to document and chunks
        try:
            topics_in_meta = []
            if document.metadata and isinstance(document.metadata.get("topics"), list):
                topics_in_meta = [
                    str(t).strip()
                    for t in document.metadata["topics"]
                    if str(t).strip()
                ]
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
                        from graph_rag.domain.models import Entity as DomainEntity

                        await self.graph_store.add_entity(
                            DomainEntity(
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
                        logger.debug(
                            "Skipping HAS_TOPIC relationship failure for %s", topic_id
                        )

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
        # Emit compact metrics line for observability
        duration_ms = int((time.monotonic() - start_ts) * 1000)
        try:
            # Prometheus histograms are observed in seconds
            observe_ingest_latency(duration_ms / 1000.0)
        except Exception:
            pass
        try:
            logger.info(
                "IngestMetrics doc_id=%s id_source=%s chunks=%d vectors_deleted=%d vectors_added_expected=%d duration_ms=%d",
                document_id,
                id_source,
                len(chunk_ids),
                vectors_deleted_attempted,
                vectors_added_expected,
                duration_ms,
            )
        except Exception:
            # Never fail on metrics logging
            pass
        try:
            inc_ingested_chunks(len(chunk_ids))
        except Exception:
            pass
        # 6. Return result
        return IngestionResult(document_id=document_id, chunk_ids=chunk_ids)

    async def _retry(
        self,
        func: callable,  # returns Awaitable
        attempts: int = 3,
        base_delay: float = 0.1,
        factor: float = 2.0,
    ) -> None:
        """Retry an async operation with exponential backoff.

        Args:
            func: Zero-arg callable returning an awaitable
            attempts: Max attempts
            base_delay: Initial delay in seconds
            factor: Backoff multiplier
        """
        last_err: Exception | None = None
        delay = base_delay
        for i in range(1, attempts + 1):
            try:
                await func()
                return
            except Exception as e:  # noqa: BLE001
                last_err = e
                if i >= attempts:
                    break
                await asyncio.sleep(delay)
                delay *= factor
        if last_err is not None:
            raise last_err

    def _extract_topics(self, content: str, metadata: dict[str, Any]) -> list[str]:
        """Derive topics from metadata or content heuristics.

        Priority:
        1) If metadata already contains topics (list or str), normalize and return
        2) Else, use the first Markdown heading (# or ##) as a single topic
        3) Else, return empty list
        """
        # From metadata
        if metadata is not None:
            meta_topics = (
                metadata.get("topics") or metadata.get("Tags") or metadata.get("tags")
            )
            if meta_topics:
                if isinstance(meta_topics, list):
                    return [
                        str(t).strip().lstrip("#")
                        for t in meta_topics
                        if str(t).strip()
                    ]
                if isinstance(meta_topics, str):
                    # Split by comma or hashtag-separated words
                    if "," in meta_topics:
                        return [
                            s.strip().lstrip("#")
                            for s in meta_topics.split(",")
                            if s.strip()
                        ]
                    if "#" in meta_topics:
                        return [
                            s.strip().lstrip("#")
                            for s in meta_topics.split()
                            if s.strip()
                        ]
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
        self, content: str, document_id: str, max_tokens_per_chunk: int | None = None
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

    async def _process_vision_content(
        self, content: str, metadata: dict[str, Any], document_id: str
    ) -> tuple[str, dict[str, Any]]:
        """Process content with vision processing capabilities if available.

        Args:
            content: Original document content
            metadata: Document metadata
            document_id: Document ID for logging

        Returns:
            Tuple of (enhanced_content, enhanced_metadata)
        """
        enhanced_content = content
        enhanced_metadata = dict(metadata) if metadata else {}

        # Check if this is a PDF document and we have PDF analyzer
        source_path = metadata.get("source_path") or metadata.get("file_path")
        is_pdf = False

        if source_path:
            is_pdf = (
                source_path.lower().endswith('.pdf') or
                enhanced_metadata.get("type") == "pdf" or
                enhanced_metadata.get("content_type") == "application/pdf"
            )

        # Process PDF with vision capabilities
        if is_pdf and self.pdf_analyzer and source_path:
            try:
                logger.info(f"Processing PDF with vision analysis: {source_path}")
                pdf_result = await self.pdf_analyzer.extract_content(source_path)

                if pdf_result:
                    # Combine original content with PDF extracted content
                    pdf_text = pdf_result.get("text", "")
                    images_text = pdf_result.get("images_text", [])
                    pdf_metadata = pdf_result.get("metadata", {})

                    # Enhance content with PDF text if available
                    if pdf_text.strip():
                        if enhanced_content.strip():
                            enhanced_content = f"{enhanced_content}\n\n--- PDF Content ---\n{pdf_text}"
                        else:
                            enhanced_content = pdf_text

                    # Add image text if available
                    if images_text:
                        image_content = "\n\n--- Text from Images ---\n" + "\n".join(images_text)
                        enhanced_content = f"{enhanced_content}{image_content}"
                        enhanced_metadata["images_text_count"] = len(images_text)

                    # Add PDF metadata
                    enhanced_metadata["pdf_metadata"] = pdf_metadata
                    enhanced_metadata["vision_processed"] = True

                    logger.info(
                        f"PDF vision processing complete for {document_id}: "
                        f"extracted {len(pdf_text)} text chars, {len(images_text)} image texts"
                    )

            except Exception as e:
                logger.warning(f"PDF vision processing failed for {document_id}: {e}")

        # Process individual images if image processor is available
        elif self.image_processor and source_path:
            try:
                if self.image_processor.is_supported_format(source_path):
                    logger.info(f"Processing image with OCR: {source_path}")
                    ocr_text = await self.image_processor.extract_text_from_image(source_path)

                    if ocr_text.strip():
                        if enhanced_content.strip():
                            enhanced_content = f"{enhanced_content}\n\n--- OCR Text ---\n{ocr_text}"
                        else:
                            enhanced_content = ocr_text

                        enhanced_metadata["ocr_text_length"] = len(ocr_text)
                        enhanced_metadata["vision_processed"] = True

                        logger.info(f"Image OCR complete for {document_id}: extracted {len(ocr_text)} characters")

            except Exception as e:
                logger.warning(f"Image OCR processing failed for {document_id}: {e}")

        return enhanced_content, enhanced_metadata

    async def _extract_and_store_entities(self, chunk_objects: list[Chunk], document_id: str) -> None:
        """Extract entities from chunks and store them in the graph with relationships."""
        if not self.entity_extractor:
            logger.debug("No entity extractor configured, skipping entity extraction")
            return

        logger.info(
            f"Starting entity extraction for document {document_id} with {len(chunk_objects)} chunks"
        )

        # Extract entities from all chunks
        all_entities: dict[str, ExtractedEntity] = {}
        entity_chunk_mentions: list[tuple[str, str]] = []  # (entity_id, chunk_id) pairs

        for chunk in chunk_objects:
            if not chunk.text or chunk.text.isspace():
                continue

            try:
                # Add context for better entity extraction
                context = {
                    "chunk_id": chunk.id,
                    "document_id": document_id,
                }

                # Extract entities from chunk text
                extraction_result = await self.entity_extractor.extract_from_text(
                    chunk.text, context
                )

                # Collect unique entities and track chunk-entity relationships
                for extracted_entity in extraction_result.entities:
                    entity_id = extracted_entity.id
                    if entity_id not in all_entities:
                        all_entities[entity_id] = extracted_entity

                    # Track that this chunk mentions this entity
                    entity_chunk_mentions.append((entity_id, chunk.id))

            except Exception as e:
                logger.warning(
                    f"Entity extraction failed for chunk {chunk.id} in document {document_id}: {e}"
                )
                continue

        if not all_entities:
            logger.info(f"No entities extracted from document {document_id}")
            return

        logger.info(
            f"Extracted {len(all_entities)} unique entities from document {document_id}"
        )

        # Store entities in the graph
        from graph_rag.domain.models import Entity as DomainEntity

        for extracted_entity in all_entities.values():
            try:
                # Convert ExtractedEntity to domain Entity
                domain_entity = DomainEntity(
                    id=extracted_entity.id,
                    name=extracted_entity.name or extracted_entity.text,
                    type=extracted_entity.label,
                    properties=extracted_entity.metadata or {},
                )

                await self._retry(
                    lambda: self.graph_store.add_entity(domain_entity),
                    attempts=3,
                    base_delay=0.1,
                )

            except Exception as e:
                logger.warning(
                    f"Failed to store entity {extracted_entity.id} for document {document_id}: {e}"
                )
                continue

        # Create MENTIONS relationships between chunks and entities
        for entity_id, chunk_id in entity_chunk_mentions:
            try:
                mentions_relationship = Relationship(
                    id=str(uuid.uuid4()),
                    type="MENTIONS",
                    source_id=chunk_id,
                    target_id=entity_id,
                )

                await self._retry(
                    lambda: self.graph_store.add_relationship(mentions_relationship),
                    attempts=3,
                    base_delay=0.1,
                )

            except Exception as e:
                logger.warning(
                    f"Failed to create MENTIONS relationship between chunk {chunk_id} and entity {entity_id}: {e}"
                )
                continue

        logger.info(
            f"Successfully stored {len(all_entities)} entities and {len(entity_chunk_mentions)} MENTIONS relationships for document {document_id}"
        )
