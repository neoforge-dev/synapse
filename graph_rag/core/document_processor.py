from graph_rag.core.interfaces import DocumentProcessor, DocumentData, ChunkData
from typing import List, Literal
import re
import uuid
import logging
from abc import ABC, abstractmethod

from graph_rag.models import Document, Chunk

try:
    import nltk
except ImportError:
    nltk = None # Handle case where nltk is not installed

logger = logging.getLogger(__name__)

ChunkingStrategy = Literal["paragraph", "token"]

class ChunkSplitter(ABC):
    """Abstract base class for document chunk splitting strategies."""

    @abstractmethod
    def split(self, document: Document) -> List[Chunk]:
        """Splits a document into chunks."""
        pass

class SentenceSplitter(ChunkSplitter):
    """Splits a document into chunks based on sentences using NLTK."""
    
    def __init__(self):
        """Initializes the splitter and ensures NLTK data is available."""
        self._ensure_nltk_punkt()
        
    def _ensure_nltk_punkt(self):
        """Checks for NLTK and the 'punkt' tokenizer, downloading if necessary."""
        if not nltk:
            logger.warning("'nltk' library not found. Sentence splitting will not work.")
            return # Cannot proceed without nltk
        
        try:
            nltk.data.find('tokenizers/punkt')
            logger.debug("NLTK 'punkt' tokenizer found.")
        except LookupError:
            logger.info("NLTK 'punkt' resource not found. Attempting download...")
            try:
                nltk.download('punkt', quiet=True)
                logger.info("NLTK 'punkt' downloaded successfully.")
            except Exception as e:
                logger.error(f"Error downloading NLTK 'punkt': {e}. Sentence splitting may fail.", exc_info=True)
                # Consider raising a more specific error if punkt is absolutely essential

    def split(self, document: Document) -> List[Chunk]:
        """Splits the document content into sentences."""
        if not nltk:
            logger.error("NLTK is not available. Cannot perform sentence splitting.")
            return [] 
        
        if not document.content or not document.content.strip():
            logger.info(f"Document {document.id} has no content to split.")
            return []

        try:
            sentences = nltk.sent_tokenize(document.content)
        except Exception as e:
            logger.error(f"NLTK sentence tokenization failed for doc {document.id}: {e}", exc_info=True)
            return [] # Return empty list on tokenization error

        chunks = []
        for i, sentence in enumerate(sentences):
            sentence = sentence.strip()
            if not sentence: # Skip empty strings resulting from tokenization
                continue
                
            chunk_id = f"{document.id}-s{i}" # Simple ID generation
            chunk_metadata = document.metadata.copy() # Inherit metadata
            chunk_metadata["sentence_index"] = i
            
            chunks.append(Chunk(
                id=str(uuid.uuid4()), # Use UUID for unique IDs
                text=sentence,
                document_id=document.id,
                metadata=chunk_metadata
            ))
            logger.debug(f"Created chunk {chunk_id} for document {document.id}")
            
        logger.info(f"Split document {document.id} into {len(chunks)} sentence chunks.")
        return chunks

class SimpleDocumentProcessor(DocumentProcessor):
    """A basic implementation of DocumentProcessor with simple chunking."""

    def __init__(
        self, 
        chunk_strategy: ChunkingStrategy = "paragraph", 
        tokens_per_chunk: int = 200 # Default if token strategy used
    ):
        if chunk_strategy not in ("paragraph", "token"):
            raise ValueError(f"Invalid chunk_strategy: {chunk_strategy}. Must be 'paragraph' or 'token'.")
        if chunk_strategy == "token" and tokens_per_chunk <= 0:
            raise ValueError("tokens_per_chunk must be positive when strategy is 'token'.")
            
        self.chunk_strategy = chunk_strategy
        self.tokens_per_chunk = tokens_per_chunk
        logger.info(f"Initialized SimpleDocumentProcessor with strategy: {self.chunk_strategy}, tokens_per_chunk: {self.tokens_per_chunk}")

    @property
    def chunk_splitter(self) -> ChunkSplitter:
        # Return a default splitter for compatibility with tests
        return SentenceSplitter()

    async def chunk_document(self, doc: DocumentData) -> List[ChunkData]:
        """Splits document content based on the configured strategy."""
        logger.debug(f"Chunking document {doc.id} using strategy: {self.chunk_strategy}")
        chunks = []
        content = doc.content.strip() # Remove leading/trailing whitespace

        if not content:
            logger.debug(f"Document {doc.id} has no content after stripping whitespace, returning 0 chunks.")
            return []

        if self.chunk_strategy == "paragraph":
            # Split by one or more newline characters, potentially surrounded by whitespace
            paragraphs = re.split(r'\s*\n\s*', content)
            current_chunk_index = 0
            for paragraph in paragraphs:
                paragraph_text = paragraph.strip()
                if paragraph_text: # Ignore empty paragraphs
                    chunk_id = f"{doc.id}-chunk-{current_chunk_index}"
                    chunks.append(ChunkData(
                        id=chunk_id,
                        text=paragraph_text,
                        document_id=doc.id
                    ))
                    current_chunk_index += 1
                    
        elif self.chunk_strategy == "token":
            # Simple whitespace splitting for "tokens" (words)
            words = content.split()
            current_chunk_index = 0
            for i in range(0, len(words), self.tokens_per_chunk):
                chunk_text = " ".join(words[i:i + self.tokens_per_chunk])
                if chunk_text:
                    chunk_id = f"{doc.id}-chunk-{current_chunk_index}"
                    chunks.append(ChunkData(
                        id=chunk_id,
                        text=chunk_text,
                        document_id=doc.id
                    ))
                    current_chunk_index += 1
        
        logger.debug(f"Generated {len(chunks)} chunks for document {doc.id}")
        return chunks 