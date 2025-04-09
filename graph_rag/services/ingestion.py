import uuid
import re
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
import logging

from graph_rag.domain.models import Document, Chunk, Edge
from graph_rag.infrastructure.repositories.graph_repository import GraphRepository
from graph_rag.services.embedding import EmbeddingService

logger = logging.getLogger(__name__)

class IngestionResult(BaseModel):
    """Result of document ingestion process."""
    document_id: str
    chunk_ids: List[str]
    
    @property
    def num_chunks(self) -> int:
        return len(self.chunk_ids)


class IngestionService:
    """Service for ingesting documents, chunking them, and storing in the graph."""
    
    def __init__(self, repository: GraphRepository):
        self.repository = repository
        # Ensure embedding model is loaded on service initialization 
        # (or handle potential loading errors gracefully)
        try:
            self.embedding_service = EmbeddingService
            self.embedding_service._get_model() # Pre-load model
        except RuntimeError as e:
            logger.error(f"Failed to initialize IngestionService due to embedding model error: {e}", exc_info=True)
            # Depending on desired behavior, re-raise or set a flag indicating limited functionality
            raise
    
    async def ingest_document(
        self, 
        content: str, 
        metadata: Dict[str, Any],
        max_tokens_per_chunk: Optional[int] = None,
        generate_embeddings: bool = True # Add flag to control embedding generation
    ) -> IngestionResult:
        """
        Ingest a document: store it, chunk it, generate embeddings, and create relationships.
        
        Args:
            content: The document content
            metadata: Additional metadata about the document
            max_tokens_per_chunk: Optional max tokens per chunk (defaults to paragraph splitting)
            generate_embeddings: Whether to generate and store embeddings for chunks.
            
        Returns:
            IngestionResult with document and chunk IDs
        """
        logger.info(f"Starting ingestion for document with metadata: {metadata}")
        # 1. Create and save document
        document = Document(
            id=str(uuid.uuid4()),
            content=content,
            metadata=metadata
        )
        try:
            document_id = await self.repository.save_document(document)
            logger.info(f"Saved document with ID: {document_id}")
        except Exception as e:
            logger.error(f"Failed to save document: {e}", exc_info=True)
            raise # Re-raise to signal failure
        
        # 2. Split content into chunks
        chunk_objects = self._split_into_chunks(content, document_id, max_tokens_per_chunk)
        logger.info(f"Split document {document_id} into {len(chunk_objects)} chunks.")
        
        # 3. Generate embeddings (if requested)
        if generate_embeddings:
            try:
                chunk_texts = [chunk.content for chunk in chunk_objects]
                if chunk_texts:
                    logger.info(f"Generating embeddings for {len(chunk_texts)} chunks...")
                    embeddings = self.embedding_service.encode(chunk_texts)
                    if len(embeddings) == len(chunk_objects):
                        for i, chunk in enumerate(chunk_objects):
                            chunk.embedding = embeddings[i]
                        logger.info(f"Embeddings generated successfully.")
                    else:
                        logger.error("Mismatch between number of chunks and generated embeddings.")
                        # Decide how to handle: raise error, skip embeddings?
                        # For now, log error and proceed without embeddings for this batch
                        generate_embeddings = False 
                else:
                    logger.info("No chunk text found to generate embeddings.")
                    generate_embeddings = False # Ensure flag is false if no text
            except Exception as e:
                logger.error(f"Failed to generate embeddings for document {document_id}: {e}", exc_info=True)
                # Decide how to handle: raise error, proceed without embeddings?
                # For now, log error and proceed without embeddings
                generate_embeddings = False # Ensure flag is false on error
        
        # 4. Save chunks and create relationships
        chunk_ids = []
        for chunk in chunk_objects:
            try:
                # Ensure embedding field exists even if generation failed/skipped
                if not hasattr(chunk, 'embedding'):
                     chunk.embedding = None
                     
                chunk_id = await self.repository.save_chunk(chunk)
                chunk_ids.append(chunk_id)
                
                # Create relationship: Document CONTAINS Chunk
                edge = Edge(
                    id=str(uuid.uuid4()),
                    type="CONTAINS",
                    source_id=document_id,
                    target_id=chunk_id
                )
                await self.repository.create_relationship(edge)
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
    
    def _split_into_chunks(
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