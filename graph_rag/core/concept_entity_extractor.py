"""Concept-aware entity extractor that bridges concept extraction with the GraphRAG system."""

import asyncio
import logging
from typing import Any

from graph_rag.core.concept_extractor import (
    ConceptualEntity,
    EnhancedConceptExtractor,
    LinkedInConceptExtractor,
    NotionConceptExtractor,
)
from graph_rag.core.interfaces import ExtractedEntity, ExtractedRelationship, ExtractionResult
from graph_rag.models import Document, Entity, ProcessedDocument, Relationship

logger = logging.getLogger(__name__)


class ConceptEntityExtractor:
    """Enhanced entity extractor that combines traditional NER with concept extraction."""

    def __init__(self, traditional_extractor=None, use_advanced_concepts: bool = True):
        """Initialize the concept-aware entity extractor.
        
        Args:
            traditional_extractor: Optional traditional entity extractor (spaCy, etc.)
            use_advanced_concepts: Whether to use advanced concept extraction
        """
        self.traditional_extractor = traditional_extractor
        self.use_advanced_concepts = use_advanced_concepts

        # Initialize concept extractors
        self.general_extractor = EnhancedConceptExtractor(use_advanced_nlp=True)
        self.linkedin_extractor = LinkedInConceptExtractor(use_advanced_nlp=True)
        self.notion_extractor = NotionConceptExtractor(use_advanced_nlp=True)

        logger.info("ConceptEntityExtractor initialized with advanced concept extraction")

    async def extract_from_text(
        self, text: str, context: dict[str, Any] | None = None
    ) -> ExtractionResult:
        """Extract both traditional entities and conceptual entities from text.
        
        Args:
            text: The input text
            context: Optional context (source platform, document metadata, etc.)
            
        Returns:
            ExtractionResult containing both traditional and conceptual entities
        """
        entities = []
        relationships = []

        # Extract traditional entities if extractor is available
        if self.traditional_extractor and hasattr(self.traditional_extractor, 'extract_from_text'):
            try:
                traditional_result = await self.traditional_extractor.extract_from_text(text, context)
                entities.extend(traditional_result.entities)
                relationships.extend(traditional_result.relationships)
                logger.debug(f"Extracted {len(traditional_result.entities)} traditional entities")
            except Exception as e:
                logger.warning(f"Traditional entity extraction failed: {e}")

        # Extract conceptual entities if enabled
        if self.use_advanced_concepts:
            try:
                concept_entities = await self._extract_conceptual_entities(text, context)
                concept_extracted_entities = self._convert_concepts_to_extracted_entities(concept_entities)
                entities.extend(concept_extracted_entities)
                logger.debug(f"Extracted {len(concept_entities)} conceptual entities")

                # Extract relationships between concepts
                if len(concept_entities) > 1:
                    concept_relationships = await self._extract_concept_relationships(concept_entities, text)
                    concept_extracted_relationships = self._convert_relationships_to_extracted(concept_relationships)
                    relationships.extend(concept_extracted_relationships)
                    logger.debug(f"Extracted {len(concept_relationships)} concept relationships")

            except Exception as e:
                logger.warning(f"Concept extraction failed: {e}")

        logger.info(f"Total extraction result: {len(entities)} entities, {len(relationships)} relationships")
        return ExtractionResult(entities=entities, relationships=relationships)

    async def extract(self, document: Document) -> ProcessedDocument:
        """Extract entities and concepts from all chunks in a document.
        
        Args:
            document: The document to process
            
        Returns:
            ProcessedDocument with extracted entities and relationships
        """
        if not hasattr(document, "chunks") or not document.chunks:
            logger.warning(f"Document {document.id} has no chunks. Cannot extract entities.")
            return ProcessedDocument(
                id=document.id,
                content=document.content,
                metadata=document.metadata.copy(),
                chunks=[],
                entities=[],
                relationships=[],
            )

        logger.info(f"Starting concept-aware extraction for document {document.id} ({len(document.chunks)} chunks)")

        # Prepare context from document metadata
        doc_context = {
            "doc_id": document.id,
            "metadata": document.metadata,
            "source": self._determine_source_platform(document)
        }

        # Process chunks concurrently
        tasks = []
        for i, chunk in enumerate(document.chunks):
            if chunk.text and not chunk.text.isspace():
                chunk_context = {**doc_context, "chunk_id": chunk.id, "chunk_index": i}
                tasks.append(self.extract_from_text(chunk.text, chunk_context))

        # Run extraction tasks concurrently
        extraction_results = await asyncio.gather(*tasks)

        # Collect and deduplicate entities
        all_entities: dict[str, Entity] = {}
        all_relationships: dict[str, Relationship] = {}

        for result in extraction_results:
            # Convert ExtractedEntity to domain Entity
            for extracted_entity in result.entities:
                entity_id = extracted_entity.id
                if entity_id not in all_entities:
                    all_entities[entity_id] = Entity(
                        id=entity_id,
                        name=extracted_entity.name or extracted_entity.text,
                        type=extracted_entity.label,
                        properties=extracted_entity.metadata or {}
                    )

            # Convert ExtractedRelationship to domain Relationship
            for extracted_rel in result.relationships:
                rel_id = f"{extracted_rel.source_entity_id}:{extracted_rel.label}:{extracted_rel.target_entity_id}"
                if rel_id not in all_relationships:
                    # Create relationship - need to handle source/target entities
                    source_entity = all_entities.get(extracted_rel.source_entity_id)
                    target_entity = all_entities.get(extracted_rel.target_entity_id)

                    if source_entity and target_entity:
                        all_relationships[rel_id] = Relationship(
                            source=source_entity,
                            target=target_entity,
                            type=extracted_rel.label
                        )

        final_entities = list(all_entities.values())
        final_relationships = list(all_relationships.values())

        logger.info(
            f"Completed concept-aware extraction for document {document.id}. "
            f"Found {len(final_entities)} unique entities and {len(final_relationships)} relationships."
        )

        return ProcessedDocument(
            id=document.id,
            content=document.content,
            metadata=document.metadata.copy(),
            chunks=document.chunks,
            entities=final_entities,
            relationships=final_relationships,
        )

    async def _extract_conceptual_entities(
        self, text: str, context: dict[str, Any] | None = None
    ) -> list[ConceptualEntity]:
        """Extract conceptual entities using appropriate extractor based on context."""
        if not context:
            context = {}

        # Determine which extractor to use based on source platform
        source = context.get("source", "").lower()

        if source == "linkedin":
            extractor = self.linkedin_extractor
        elif source == "notion":
            extractor = self.notion_extractor
        else:
            extractor = self.general_extractor

        # Extract concepts
        concepts = await extractor.extract_concepts(text, context)

        logger.debug(f"Used {extractor.__class__.__name__} to extract {len(concepts)} concepts")
        return concepts

    async def _extract_concept_relationships(
        self, concepts: list[ConceptualEntity], text: str
    ) -> list:
        """Extract relationships between concepts using the general extractor."""
        try:
            relationships = await self.general_extractor.extract_idea_relationships(concepts, text)
            return relationships
        except Exception as e:
            logger.warning(f"Failed to extract concept relationships: {e}")
            return []

    def _convert_concepts_to_extracted_entities(
        self, concepts: list[ConceptualEntity]
    ) -> list[ExtractedEntity]:
        """Convert ConceptualEntity objects to ExtractedEntity for interface compatibility."""
        extracted_entities = []

        for concept in concepts:
            # Create metadata combining concept properties and additional info
            metadata = concept.properties.copy() if concept.properties else {}
            metadata.update({
                "concept_type": concept.concept_type,
                "confidence": concept.confidence,
                "context_window": concept.context_window,
                "sentiment": concept.sentiment,
                "extraction_method": "concept_extraction"
            })

            # Add temporal markers and related concepts if available
            if hasattr(concept, 'temporal_markers') and concept.temporal_markers:
                metadata["temporal_markers"] = concept.temporal_markers
            if hasattr(concept, 'related_concepts') and concept.related_concepts:
                metadata["related_concepts"] = concept.related_concepts

            extracted_entity = ExtractedEntity(
                id=concept.id,
                label=concept.concept_type,  # Use concept_type as label
                text=concept.text,
                name=concept.name,
                metadata=metadata
            )
            extracted_entities.append(extracted_entity)

        return extracted_entities

    def _convert_relationships_to_extracted(
        self, relationships: list
    ) -> list[ExtractedRelationship]:
        """Convert concept relationships to ExtractedRelationship objects."""
        extracted_relationships = []

        for rel in relationships:
            if hasattr(rel, 'source_concept') and hasattr(rel, 'target_concept'):
                extracted_rel = ExtractedRelationship(
                    source_entity_id=rel.source_concept,
                    target_entity_id=rel.target_concept,
                    label=rel.relationship_type
                )
                extracted_relationships.append(extracted_rel)

        return extracted_relationships

    def _determine_source_platform(self, document: Document) -> str:
        """Determine the source platform from document metadata."""
        metadata = document.metadata or {}

        # Check for explicit source indicator
        if "source" in metadata:
            return metadata["source"].lower()

        # Check for platform-specific indicators
        if any(key in metadata for key in ["linkedin_post_id", "linkedin_url"]):
            return "linkedin"

        if any(key in metadata for key in ["notion_page_id", "notion_url"]):
            return "notion"

        # Check file path or name for hints
        file_path = metadata.get("file_path", "").lower()
        if "linkedin" in file_path:
            return "linkedin"
        if "notion" in file_path:
            return "notion"

        # Default to general
        return "general"


class BeliefPreferenceExtractor(ConceptEntityExtractor):
    """Specialized extractor focused on beliefs and preferences for Epic 6."""

    def __init__(self, traditional_extractor=None):
        super().__init__(traditional_extractor, use_advanced_concepts=True)
        logger.info("BeliefPreferenceExtractor initialized for Epic 6")

    async def extract_beliefs_and_preferences(
        self, text: str, context: dict[str, Any] | None = None
    ) -> dict[str, list[ConceptualEntity]]:
        """Extract beliefs and preferences specifically.
        
        Returns:
            Dict with 'beliefs' and 'preferences' keys containing respective concepts
        """
        concepts = await self._extract_conceptual_entities(text, context)

        # Filter concepts by type
        beliefs = [c for c in concepts if c.concept_type == "BELIEF"]
        preferences = [c for c in concepts if c.concept_type == "PREFERENCE"]
        hot_takes = [c for c in concepts if c.concept_type == "HOT_TAKE"]

        logger.info(f"Extracted {len(beliefs)} beliefs, {len(preferences)} preferences, {len(hot_takes)} hot takes")

        return {
            "beliefs": beliefs,
            "preferences": preferences,
            "hot_takes": hot_takes,
            "all_concepts": concepts
        }
