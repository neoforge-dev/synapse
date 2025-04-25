import uuid
import re
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
import logging

from graph_rag.domain.models import Document, Chunk, Edge, Entity, Relationship
from graph_rag.core.interfaces import (
    GraphRepository,
    VectorStore,
    EntityExtractor,
    DocumentProcessor,
    EmbeddingService,
    KnowledgeGraphBuilder
)
from graph_rag.infrastructure.document_processor.simple_processor import ChunkSplitter
from graph_rag.models import ProcessedDocument

logger = logging.getLogger(__name__)

class IngestionResult(BaseModel):
    """Result of document ingestion process."""
    document_id: str
    chunk_ids: List[str]
    
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
        vector_store: VectorStore
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
        metadata: Dict[str, Any],
        max_tokens_per_chunk: Optional[int] = None,
        generate_embeddings: bool = True # Add flag to control embedding generation
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
        logger.info(f"Starting ingestion for document {document_id} with metadata: {metadata}")
        # 1. Create and save document using the provided ID
        document = Document(
            id=document_id,
            content=content,
            metadata=metadata
        )
        try:
            # Use the specific add_document method for Document objects
            print(f"DEBUG: About to call graph_store.add_document for doc {document_id}")
            await self.graph_store.add_document(document) 
            print(f"DEBUG: Finished graph_store.add_document for doc {document_id}")
            # add_document doesn't return the ID, we already have it
            # if saved_doc_id != document_id:
            #      # Log a warning if the returned ID is different (unexpected)
            #      logger.warning(f"Saved document ID '{saved_doc_id}' differs from provided ID '{document_id}'. Using provided ID.")
            logger.info(f"Saved document with ID: {document_id}")
        except Exception as e:
            logger.error(f"Failed to save document {document_id}: {e}", exc_info=True)
            raise # Re-raise to signal failure
        
        # 2. Split content into chunks
        chunk_objects = await self._split_into_chunks(document, max_tokens_per_chunk)
        logger.info(f"Split document {document_id} into {len(chunk_objects)} chunks.")
        
        # 3. Generate embeddings (if requested)
        if self.embedding_service and generate_embeddings:
            logger.info(f"Generating embeddings for {len(chunk_objects)} chunks...")
            chunk_texts = [c.text for c in chunk_objects]
            try:
                # Ensure the call to encode is awaited
                embeddings = await self.embedding_service.encode(chunk_texts)
                # Check if the lengths match before assigning embeddings
                if embeddings and len(embeddings) == len(chunk_objects):
                    for i, chunk in enumerate(chunk_objects):
                        chunk.embedding = embeddings[i]
                        # Ensure metadata exists and add document_id to it safely
                        if not hasattr(chunk, 'metadata') or chunk.metadata is None:
                            chunk.metadata = {}
                        chunk.metadata["document_id"] = document_id
                    logger.info("Embeddings generated successfully.")
                    
                    # Add chunks to vector store *after* embeddings are assigned (if generated)
                    try:
                        await self.vector_store.add_chunks(chunk_objects)
                        logger.info(f"Added {len(chunk_objects)} chunks to vector store.")
                    except Exception as vs_e:
                        logger.error(f"Failed to add chunks to vector store: {vs_e}", exc_info=True)
                        # Decide handling: maybe continue without vector store addition?
                        # For now, log and continue.
                        
                else:
                    logger.error(f"Mismatch between number of chunks ({len(chunk_objects)}) and generated embeddings ({len(embeddings) if embeddings else 0}). Skipping embedding assignment.")
            except AttributeError as ae:
                logger.error(f"Failed to generate embeddings for document {document_id}: Embedding service missing 'encode' method or similar error: {ae}", exc_info=True)
                # Decide how to handle: skip embeddings, raise error?
                # For now, log error and continue without embeddings
            except Exception as e:
                logger.error(f"Failed to generate embeddings for document {document_id}: {e}", exc_info=True)
                # Decide how to handle: skip embeddings, raise error?
                # For now, log error and continue without embeddings
        
        # 4. Save chunks and create relationships
        chunk_ids = []
        for chunk in chunk_objects:
            try:
                # Ensure embedding field exists even if generation failed/skipped
                if not hasattr(chunk, 'embedding'):
                     chunk.embedding = None
                     
                # --- Add debug print here ---
                print(f"DEBUG: Before save_chunk - Chunk ID: {chunk.id}, Embedding is None: {chunk.embedding is None}")
                if chunk.embedding is not None:
                    # Limit printing large embeddings
                    embedding_preview = str(chunk.embedding[:5]) + ('...' if len(chunk.embedding) > 5 else '') 
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
                    target_id=chunk.id # Use chunk.id
                )
                await self.graph_store.add_relationship(rel)
            except Exception as e:
                logger.error(f"Failed to save chunk {chunk.id} or its relationship for document {document_id}: {e}", exc_info=True)
                # Optionally collect failed chunk IDs or raise immediately
                # For now, continue processing other chunks
        
        logger.info(f"Ingestion complete for document {document_id}. Saved {len(chunk_ids)} chunks.")
        # 5. Return result
        return IngestionResult(
            document_id=document_id,
            chunk_ids=chunk_ids
        )
    
    async def _split_into_chunks(self, document: Document, max_tokens_per_chunk: int | None = None) -> list[Chunk]:
        """Helper method to split document content into chunks."""
        try:
            chunks: list[Chunk] = await self.document_processor.chunk_document( # Await here
                document.content,
                document_id=document.id,
                metadata=document.metadata,
                max_tokens_per_chunk=max_tokens_per_chunk # Pass the override
            )
            # logger.info(f"Document {document.id} split into {len(chunks)} chunks.") # This line caused the error
            logger.info(f"Document {document.id} split into {len(chunks)} chunks.") # Log after awaiting
            return chunks
        except Exception as e:
            logger.error(f"Error splitting document {document.id}: {e}")
            # Depending on desired behavior, might re-raise or return empty list
            return []
    
    def _split_into_chunks_old(
        self, 
        content: str, 
        document_id: str,
        max_tokens_per_chunk: Optional[int] = None
    ) -> List[Chunk]:
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
            paragraphs = re.split(r'\n\s*\n', content)
            paragraphs = [p.strip() for p in paragraphs if p.strip()]
            
            for paragraph in paragraphs:
                chunks.append(Chunk(
                    id=str(uuid.uuid4()),
                    content=paragraph,
                    document_id=document_id
                    # embedding added later
                ))
        
        # Option 2: Split by token count
        else:
            # Simple word-based token splitting for now
            # In a real implementation, we'd use a proper tokenizer
            words = content.split()
            
            for i in range(0, len(words), max_tokens_per_chunk):
                chunk_content = ' '.join(words[i:i + max_tokens_per_chunk])
                chunks.append(Chunk(
                    id=str(uuid.uuid4()),
                    content=chunk_content,
                    document_id=document_id
                    # embedding added later
                ))
        
        return chunks 