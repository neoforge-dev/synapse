import asyncio
import logging
import re  # Added import
from abc import ABC, abstractmethod
from typing import Any

from graph_rag.core.interfaces import ExtractedEntity, ExtractionResult
from graph_rag.models import Document, Entity, ProcessedDocument, Relationship

logger = logging.getLogger(__name__)


class EntityExtractor(ABC):
    """Abstract base class for extracting entities and relationships from text."""

    @abstractmethod
    async def extract(self, document: Document) -> ProcessedDocument:
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

    async def extract(self, document: Document) -> ProcessedDocument:
        logger.info(
            f"Mock extracting entities/relationships for document {document.id}"
        )
        entities = []
        relationships = []

        # Example: Simple extraction based on specific text in chunks
        for chunk in document.chunks:
            if "Alice" in chunk.text and "Bob" in chunk.text:
                alice = Entity(id="ent-alice", name="Alice", type="PERSON")
                bob = Entity(id="ent-bob", name="Bob", type="PERSON")
                relation = Relationship(source=alice, target=bob, type="KNOWS")

                # Avoid duplicates if processing multiple chunks with same entities
                if alice not in entities:
                    entities.append(alice)
                if bob not in entities:
                    entities.append(bob)
                if relation not in relationships:
                    relationships.append(relation)

            elif "GraphRAG" in chunk.text:
                graphrag_ent = Entity(id="ent-graphrag", name="GraphRAG", type="SYSTEM")
                if graphrag_ent not in entities:
                    entities.append(graphrag_ent)

        logger.info(
            f"Mock extracted {len(entities)} entities and {len(relationships)} relationships."
        )

        # Create the ProcessedDocument, copying necessary fields
        processed_doc = ProcessedDocument(
            id=document.id,
            content=document.content,
            metadata=document.metadata.copy(),
            chunks=document.chunks,  # Keep original chunks
            entities=entities,
            relationships=relationships,
        )
        return processed_doc


class SpacyEntityExtractor(EntityExtractor):
    """Extracts named entities using a spaCy model."""

    def __init__(self, model_name: str = "en_core_web_sm"):
        self.model_name = model_name
        self.nlp = None
        try:
            # Import spacy only when the class is instantiated
            import spacy

            self.nlp = spacy.load(self.model_name)
            logger.info(f"spaCy model '{self.model_name}' loaded successfully.")
        except ImportError:
            error_msg = (
                f"Failed to load spaCy model '{self.model_name}'. Please install spaCy."
            )
            logger.error(error_msg)
            self.nlp = None  # Ensure nlp is None if loading fails

    def _normalize_entity_text(self, text: str) -> str:
        """Normalizes entity text to create a more stable ID (simple example)."""
        # Lowercase, replace whitespace with underscore, remove common punctuation
        text = text.lower().strip()
        text = re.sub(r"\s+", "_", text)
        text = re.sub(r'[.,!?;:\'"()]$', "", text)  # Escaped single quote
        text = re.sub(
            r'^["(]', "", text
        )  # Simplified: Removed single quote from leading char set
        return text

    def _canonicalize(self, name: str) -> str:
        """Return a canonical form for entity merging (basic heuristics)."""
        base = name.lower().strip()
        base = re.sub(r"\s+", " ", base)
        # Remove common suffixes/prefixes
        base = re.sub(r"\b(inc\.|co\.|ltd\.|gmbh|s\.r\.?l\.|corp\.)\b", "", base)
        return base.strip()

    # Implement the new interface method
    async def extract_from_text(
        self, text: str, context: dict[str, Any] | None = None
    ) -> ExtractionResult:
        """Extracts entities from a text string using spaCy NER."""
        if not self.nlp:
            logger.error(
                f"spaCy model '{self.model_name}' is not loaded. Cannot extract entities."
            )
            return ExtractionResult(entities=[], relationships=[])

        entities: dict[str, ExtractedEntity] = {}
        if not text or text.isspace():
            return ExtractionResult(entities=[], relationships=[])

        try:
            spacy_doc = self.nlp(text)
        except Exception as e:
            logger.error(f"spaCy processing failed for text: {e}", exc_info=True)
            return ExtractionResult(
                entities=[], relationships=[]
            )  # Return empty on error

        # Canonicalization map: canonical_name -> assigned id
        canon_map: dict[str, str] = {}
        for ent in spacy_doc.ents:
            normalized_text = self._normalize_entity_text(ent.text)
            canonical = self._canonicalize(ent.text)
            entity_id = f"{ent.label_}:{normalized_text}"
            # If canonical already assigned, reuse the earlier ID
            if canonical in canon_map:
                reuse_id = canon_map[canonical]
                # Update map to one canonical id
                if reuse_id in entities:
                    # Append alias
                    aliases = entities[reuse_id].metadata.get("aliases", []) if entities[reuse_id].metadata else []
                    aliases = list({*aliases, ent.text})
                    if entities[reuse_id].metadata is None:
                        entities[reuse_id].metadata = {}
                    entities[reuse_id].metadata["aliases"] = aliases
                continue
            # New canonical
            canon_map[canonical] = entity_id
            if entity_id not in entities:
                entities[entity_id] = ExtractedEntity(
                    id=entity_id,
                    name=ent.text,
                    text=ent.text,
                    label=ent.label_,
                    # Add context if provided
                    metadata=context.copy() if context else {},
                )

        extracted_entities = list(entities.values())
        logger.debug(f"Extracted {len(extracted_entities)} entities from text.")
        return ExtractionResult(
            entities=extracted_entities, relationships=[]
        )  # No relationship extraction

    # Keep the old method but make it use the new one for consistency
    # It might be removed later if not needed elsewhere
    async def extract(self, document: Document) -> ProcessedDocument:
        """Extracts entities from all chunks in a document using spaCy NER.
        Processes chunk by chunk using extract_from_text.
        Relationships are not extracted by this implementation.
        """
        if not self.nlp:
            logger.error(
                f"spaCy model '{self.model_name}' is not loaded. Cannot extract entities."
            )
            # Return a ProcessedDocument with empty lists
            return ProcessedDocument(
                id=document.id,
                content=document.content,
                metadata=document.metadata.copy(),
                chunks=document.chunks,  # Keep original chunks
                entities=[],
                relationships=[],
            )

        all_entities: dict[str, Entity] = {}
        # The original extract method expected document.chunks, ensure it exists or handle error
        # For robustness, check if document has chunks attribute
        if not hasattr(document, "chunks") or not document.chunks:
            logger.warning(
                f"Document {document.id} has no chunks attribute or empty chunks list. Cannot extract entities."
            )
            return ProcessedDocument(
                id=document.id,
                content=document.content,
                metadata=document.metadata.copy(),
                chunks=[],  # Return empty chunks list
                entities=[],
                relationships=[],
            )

        logger.info(
            f"Starting spaCy entity extraction for document {document.id} ({len(document.chunks)} chunks)"
        )

        tasks = []
        for i, chunk in enumerate(document.chunks):
            logger.debug(
                f"Scheduling chunk {i + 1}/{len(document.chunks)} (id: {chunk.id}) for entity extraction."
            )
            if chunk.text and not chunk.text.isspace():
                context = {"chunk_id": chunk.id, "doc_id": document.id}
                tasks.append(self.extract_from_text(chunk.text, context))

        # Run extraction tasks concurrently using gather
        extraction_results = await asyncio.gather(*tasks)

        # Collect unique entities from all results
        for result in extraction_results:
            for extracted_entity in result.entities:
                # Convert ExtractedEntity back to domain Entity for ProcessedDocument
                # Use the generated ID (label:normalized_text) from extract_from_text
                entity_id = extracted_entity.id
                if entity_id not in all_entities:
                    all_entities[entity_id] = Entity(
                        id=entity_id,
                        name=extracted_entity.name,
                        type=extracted_entity.label,
                        metadata=extracted_entity.metadata,  # Use metadata instead of properties
                    )

        final_entities = list(all_entities.values())
        logger.info(
            f"Completed extraction for document {document.id}. Found {len(final_entities)} unique entities."
        )

        # Create ProcessedDocument, keeping original doc info and adding entities
        processed_doc = ProcessedDocument(
            id=document.id,
            content=document.content,
            metadata=document.metadata.copy(),
            chunks=document.chunks,
            entities=final_entities,
            relationships=[],  # No relationships extracted here
        )
        return processed_doc
