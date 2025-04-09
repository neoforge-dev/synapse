from graph_rag.core.interfaces import EntityExtractor, ExtractionResult, ExtractedEntity
import logging
import spacy
from spacy.language import Language # For type hinting
import re
from abc import ABC, abstractmethod
from typing import List, Tuple, Dict
import uuid # Added for ID generation

from graph_rag.models import Chunk, Entity, Relationship, ProcessedDocument, Document

logger = logging.getLogger(__name__)

class EntityExtractor(ABC):
    """Abstract base class for extracting entities and relationships from text."""

    @abstractmethod
    def extract(self, document: Document) -> ProcessedDocument:
        """Extracts entities and relationships from the document's chunks.
        
        Args:
            document: The input Document object containing chunks.
            
        Returns:
            A ProcessedDocument object containing the original document info
            plus extracted entities and relationships.
        """
        pass

class MockEntityExtractor(EntityExtractor):
    """A mock implementation that returns predefined entities/relationships for testing."""
    
    def extract(self, document: Document) -> ProcessedDocument:
        logger.info(f"Mock extracting entities/relationships for document {document.id}")
        entities = []
        relationships = []
        
        # Example: Simple extraction based on specific text in chunks
        for chunk in document.chunks:
            if "Alice" in chunk.text and "Bob" in chunk.text:
                alice = Entity(id="ent-alice", name="Alice", type="PERSON")
                bob = Entity(id="ent-bob", name="Bob", type="PERSON")
                relation = Relationship(source=alice, target=bob, type="KNOWS")
                
                # Avoid duplicates if processing multiple chunks with same entities
                if alice not in entities: entities.append(alice)
                if bob not in entities: entities.append(bob)
                if relation not in relationships: relationships.append(relation)
                
            elif "GraphRAG" in chunk.text:
                graphrag_ent = Entity(id="ent-graphrag", name="GraphRAG", type="SYSTEM")
                if graphrag_ent not in entities: entities.append(graphrag_ent)

        logger.info(f"Mock extracted {len(entities)} entities and {len(relationships)} relationships.")
        
        # Create the ProcessedDocument, copying necessary fields
        processed_doc = ProcessedDocument(
            id=document.id,
            content=document.content,
            metadata=document.metadata.copy(),
            chunks=document.chunks, # Keep original chunks
            entities=entities,
            relationships=relationships
        )
        return processed_doc

class SpacyEntityExtractor(EntityExtractor):
    """Extracts named entities using a spaCy model."""
    _nlp: Language | None = None
    _model_name: str

    def __init__(self, model_name: str = "en_core_web_sm"):
        self._model_name = model_name
        self._load_model() # Load model on initialization
        
    def _load_model(self) -> None:
        """Loads the spaCy model."""
        if self._nlp is not None:
            return
            
        logger.info(f"Loading spaCy model: {self._model_name}")
        try:
            self._nlp = spacy.load(self._model_name, disable=["parser", "lemmatizer"]) # Disable unused pipes
            logger.info(f"spaCy model '{self._model_name}' loaded successfully.")
        except OSError:
            error_msg = f"spaCy model '{self._model_name}' not found. " \
                         f"Please download it: python -m spacy download {self._model_name}"
            logger.error(error_msg, exc_info=True)
            raise RuntimeError(f"Failed to load spaCy model: {self._model_name}. Please download it.")
        except Exception as e:
            error_msg = f"Failed to load spaCy model '{self._model_name}': {e}"
            logger.error(error_msg, exc_info=True)
            raise RuntimeError(error_msg)

    def _normalize_entity_text(self, text: str) -> str:
        """Normalizes entity text to create a more stable ID (simple example)."""
        # Lowercase, replace whitespace with underscore, remove common punctuation
        text = text.lower().strip()
        text = re.sub(r'\s+', '_', text)
        text = re.sub(r'[.,!?;:'"()]$', '', text) # Remove trailing punctuation
        text = re.sub(r'^['"(]', '', text) # Remove leading punctuation
        return text
        
    def extract(self, document: Document) -> ProcessedDocument:
        """Extracts entities from all chunks in a document using spaCy NER.
           Relationships are not extracted by this implementation.
        """
        if self._nlp is None:
             # This shouldn't happen if __init__ loaded correctly, but check defensively
             raise RuntimeError("spaCy model is not loaded.")

        all_entities: Dict[str, Entity] = {}
        logger.info(f"Starting spaCy entity extraction for document {document.id} ({len(document.chunks)} chunks)")
        
        for i, chunk in enumerate(document.chunks):
            logger.debug(f"Processing chunk {i+1}/{len(document.chunks)} (id: {chunk.id}) for entities.")
            if not chunk.text or chunk.text.isspace():
                continue
            
            try:
                spacy_doc = self._nlp(chunk.text)
            except Exception as e:
                 logger.error(f"spaCy processing failed for chunk {chunk.id}: {e}", exc_info=True)
                 continue # Skip chunk on error

            for ent in spacy_doc.ents:
                # Use normalized text + label for a more stable (but not perfect) ID
                normalized_text = self._normalize_entity_text(ent.text)
                entity_id = f"{ent.label_}:{normalized_text}" 
                # If the entity hasn't been seen before in this document, add it
                if entity_id not in all_entities:
                    all_entities[entity_id] = Entity(
                        id=entity_id, # Generate a more robust ID? Use UUID? Use hash?
                                        # Using label:normalized_text for now
                        name=ent.text, # Store original text as name
                        type=ent.label_, 
                        metadata={ # Add chunk info to metadata? Optional.
                            # "found_in_chunk_id": chunk.id,
                            # "start_char": ent.start_char,
                            # "end_char": ent.end_char
                        } 
                    )
                # else: Handle updates? Merge metadata?

        extracted_entities = list(all_entities.values())
        logger.info(f"Completed extraction for document {document.id}. Found {len(extracted_entities)} unique entities.")
        
        # Create ProcessedDocument, keeping original doc info and adding entities
        processed_doc = ProcessedDocument(
            id=document.id,
            content=document.content,
            metadata=document.metadata.copy(),
            chunks=document.chunks,
            entities=extracted_entities,
            relationships=[] # No relationships extracted here
        )
        return processed_doc 