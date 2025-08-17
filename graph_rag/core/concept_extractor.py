"""Enhanced concept and idea extraction system for advanced knowledge mapping."""

import asyncio
import logging
import re
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Set, Tuple
from dataclasses import dataclass, field
from datetime import datetime

from graph_rag.core.interfaces import ExtractedEntity, ExtractionResult
from graph_rag.models import Document, Entity, ProcessedDocument, Relationship

logger = logging.getLogger(__name__)


@dataclass
class ConceptualEntity(ExtractedEntity):
    """Extended entity for conceptual ideas and themes."""
    concept_type: str = "IDEA"  # IDEA, THEME, STRATEGY, PRINCIPLE, etc.
    confidence: float = 0.0
    context_window: str = ""
    temporal_markers: List[str] = field(default_factory=list)
    related_concepts: List[str] = field(default_factory=list)
    sentiment: Optional[str] = None
    
    
@dataclass 
class IdeaRelationship:
    """Represents relationships between ideas/concepts."""
    source_concept: str
    target_concept: str
    relationship_type: str  # BUILDS_UPON, CONTRADICTS, INFLUENCES, EVOLVES_TO
    confidence: float = 0.0
    evidence_text: str = ""
    temporal_order: Optional[int] = None


class ConceptExtractor(ABC):
    """Abstract base class for extracting concepts and ideas from text."""

    @abstractmethod
    async def extract_concepts(self, text: str, context: Dict[str, Any] = None) -> List[ConceptualEntity]:
        """Extract conceptual ideas and themes from text."""
        pass

    @abstractmethod 
    async def extract_idea_relationships(self, concepts: List[ConceptualEntity], text: str) -> List[IdeaRelationship]:
        """Extract relationships between identified concepts."""
        pass


class EnhancedConceptExtractor(ConceptExtractor):
    """Enhanced concept extraction using multiple NLP techniques."""
    
    def __init__(self, use_advanced_nlp: bool = True):
        self.use_advanced_nlp = use_advanced_nlp
        self.nlp = None
        self._init_models()
        
    def _init_models(self):
        """Initialize NLP models."""
        try:
            if self.use_advanced_nlp:
                import spacy
                # Try to load a larger model if available
                try:
                    self.nlp = spacy.load("en_core_web_lg")
                except OSError:
                    self.nlp = spacy.load("en_core_web_sm")
                logger.info(f"Loaded spaCy model: {self.nlp.meta['name']}")
        except ImportError:
            logger.warning("spaCy not available, using rule-based extraction")
            self.nlp = None

    async def extract_concepts(self, text: str, context: Dict[str, Any] = None) -> List[ConceptualEntity]:
        """Extract conceptual ideas using multiple strategies."""
        concepts = []
        
        # Strategy 1: Rule-based concept patterns
        rule_based_concepts = await self._extract_rule_based_concepts(text, context)
        concepts.extend(rule_based_concepts)
        
        # Strategy 2: NLP-based concept extraction
        if self.nlp:
            nlp_concepts = await self._extract_nlp_concepts(text, context)
            concepts.extend(nlp_concepts)
            
        # Strategy 3: Domain-specific patterns
        domain_concepts = await self._extract_domain_concepts(text, context)
        concepts.extend(domain_concepts)
        
        # Deduplicate and rank concepts
        unique_concepts = self._deduplicate_concepts(concepts)
        
        return unique_concepts

    async def _extract_rule_based_concepts(self, text: str, context: Dict[str, Any] = None) -> List[ConceptualEntity]:
        """Extract concepts using predefined patterns."""
        concepts = []
        
        # Business strategy patterns
        strategy_patterns = [
            r'\b(?:business\s+)?strategy\b',
            r'\b(?:growth|expansion|scaling)\s+(?:strategy|plan|approach)\b',
            r'\b(?:competitive\s+)?advantage\b',
            r'\b(?:market\s+)?positioning\b',
            r'\b(?:revenue|monetization)\s+(?:model|strategy)\b'
        ]
        
        # Innovation patterns  
        innovation_patterns = [
            r'\b(?:digital\s+)?transformation\b',
            r'\b(?:innovation|disruption|breakthrough)\b',
            r'\b(?:emerging|new)\s+(?:technology|trend|approach)\b',
            r'\b(?:automation|AI|machine\s+learning)\b'
        ]
        
        # Process/methodology patterns
        process_patterns = [
            r'\b(?:agile|lean|design\s+thinking)\b',
            r'\b(?:best\s+)?practice\b',
            r'\b(?:framework|methodology|approach)\b',
            r'\b(?:process\s+)?optimization\b'
        ]
        
        all_patterns = {
            "STRATEGY": strategy_patterns,
            "INNOVATION": innovation_patterns, 
            "PROCESS": process_patterns
        }
        
        for concept_type, patterns in all_patterns.items():
            for pattern in patterns:
                matches = re.finditer(pattern, text, re.IGNORECASE)
                for match in matches:
                    concept_text = match.group(0)
                    
                    # Extract context window
                    start = max(0, match.start() - 100)
                    end = min(len(text), match.end() + 100)
                    context_window = text[start:end]
                    
                    concept = ConceptualEntity(
                        id=f"{concept_type}:{concept_text.lower().replace(' ', '_')}",
                        name=concept_text,
                        text=concept_text,
                        label=concept_type,
                        concept_type=concept_type,
                        confidence=0.7,  # Rule-based gets medium confidence
                        context_window=context_window,
                        metadata=context or {}
                    )
                    concepts.append(concept)
                    
        return concepts

    async def _extract_nlp_concepts(self, text: str, context: Dict[str, Any] = None) -> List[ConceptualEntity]:
        """Extract concepts using NLP techniques."""
        if not self.nlp:
            return []
            
        concepts = []
        doc = self.nlp(text)
        
        # Extract noun phrases that might represent concepts
        for chunk in doc.noun_chunks:
            if len(chunk.text.split()) >= 2:  # Multi-word concepts
                concept_type = self._classify_concept_type(chunk.text, chunk)
                if concept_type:
                    concept = ConceptualEntity(
                        id=f"{concept_type}:{chunk.text.lower().replace(' ', '_')}",
                        name=chunk.text,
                        text=chunk.text,
                        label=concept_type,
                        concept_type=concept_type,
                        confidence=0.6,
                        context_window=str(chunk.sent) if chunk.sent else "",
                        metadata=context or {}
                    )
                    concepts.append(concept)
                    
        return concepts

    async def _extract_domain_concepts(self, text: str, context: Dict[str, Any] = None) -> List[ConceptualEntity]:
        """Extract domain-specific concepts based on context."""
        concepts = []
        
        # LinkedIn post-specific concepts
        if context and context.get("source") == "linkedin":
            linkedin_concepts = await self._extract_linkedin_concepts(text, context)
            concepts.extend(linkedin_concepts)
            
        # Notion document-specific concepts
        if context and context.get("source") == "notion":
            notion_concepts = await self._extract_notion_concepts(text, context)
            concepts.extend(notion_concepts)
            
        return concepts

    async def _extract_linkedin_concepts(self, text: str, context: Dict[str, Any]) -> List[ConceptualEntity]:
        """Extract LinkedIn-specific concepts."""
        concepts = []
        
        # Professional insights patterns
        insight_patterns = [
            r'\b(?:lesson|insight|takeaway|learning)\b',
            r'\b(?:tip|advice|recommendation)\b',
            r'\b(?:experience|observation|finding)\b'
        ]
        
        # Career/professional patterns
        career_patterns = [
            r'\b(?:career|professional)\s+(?:development|growth|advice)\b',
            r'\b(?:leadership|management|mentorship)\b',
            r'\b(?:networking|relationship\s+building)\b'
        ]
        
        all_patterns = {
            "INSIGHT": insight_patterns,
            "CAREER_CONCEPT": career_patterns
        }
        
        for concept_type, patterns in all_patterns.items():
            for pattern in patterns:
                matches = re.finditer(pattern, text, re.IGNORECASE)
                for match in matches:
                    concept_text = match.group(0)
                    concept = ConceptualEntity(
                        id=f"linkedin_{concept_type}:{concept_text.lower().replace(' ', '_')}",
                        name=concept_text,
                        text=concept_text,
                        label=concept_type,
                        concept_type=concept_type,
                        confidence=0.8,  # High confidence for platform-specific patterns
                        metadata={**context, "platform": "linkedin"}
                    )
                    concepts.append(concept)
                    
        return concepts

    async def _extract_notion_concepts(self, text: str, context: Dict[str, Any]) -> List[ConceptualEntity]:
        """Extract Notion-specific concepts."""
        concepts = []
        
        # Note-taking/knowledge patterns
        knowledge_patterns = [
            r'\b(?:note|idea|thought|concept)\b',
            r'\b(?:research|study|analysis)\b',
            r'\b(?:hypothesis|theory|principle)\b'
        ]
        
        for pattern in knowledge_patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                concept_text = match.group(0)
                concept = ConceptualEntity(
                    id=f"notion_KNOWLEDGE:{concept_text.lower().replace(' ', '_')}",
                    name=concept_text,
                    text=concept_text,
                    label="KNOWLEDGE",
                    concept_type="KNOWLEDGE",
                    confidence=0.7,
                    metadata={**context, "platform": "notion"}
                )
                concepts.append(concept)
                
        return concepts

    def _classify_concept_type(self, text: str, chunk=None) -> Optional[str]:
        """Classify the type of concept based on linguistic patterns."""
        text_lower = text.lower()
        
        # Strategy-related concepts
        if any(word in text_lower for word in ["strategy", "approach", "method", "plan"]):
            return "STRATEGY"
            
        # Innovation concepts
        if any(word in text_lower for word in ["innovation", "technology", "digital", "transformation"]):
            return "INNOVATION"
            
        # Process concepts
        if any(word in text_lower for word in ["process", "workflow", "system", "framework"]):
            return "PROCESS"
            
        # Generic concept if it looks conceptual
        if chunk and chunk.root.pos_ in ["NOUN"] and len(text.split()) >= 2:
            return "CONCEPT"
            
        return None

    def _deduplicate_concepts(self, concepts: List[ConceptualEntity]) -> List[ConceptualEntity]:
        """Remove duplicate concepts and rank by confidence."""
        seen = set()
        unique_concepts = []
        
        # Sort by confidence descending
        sorted_concepts = sorted(concepts, key=lambda c: c.confidence, reverse=True)
        
        for concept in sorted_concepts:
            # Create a canonical key for deduplication
            key = f"{concept.concept_type}:{concept.name.lower().strip()}"
            if key not in seen:
                seen.add(key)
                unique_concepts.append(concept)
                
        return unique_concepts

    async def extract_idea_relationships(self, concepts: List[ConceptualEntity], text: str) -> List[IdeaRelationship]:
        """Extract relationships between concepts."""
        relationships = []
        
        # Look for relationship indicators between concepts
        relationship_patterns = {
            "BUILDS_UPON": [r"builds?\s+(?:on|upon)", r"extends?", r"improves?"],
            "CONTRADICTS": [r"contradicts?", r"opposes?", r"conflicts?\s+with"],
            "INFLUENCES": [r"influences?", r"affects?", r"impacts?"],
            "ENABLES": [r"enables?", r"allows?", r"facilitates?"]
        }
        
        # Find co-occurring concepts in text
        for i, concept1 in enumerate(concepts):
            for j, concept2 in enumerate(concepts[i+1:], i+1):
                # Check if concepts appear near each other
                if self._concepts_are_related(concept1, concept2, text):
                    rel_type = self._determine_relationship_type(concept1, concept2, text, relationship_patterns)
                    if rel_type:
                        relationship = IdeaRelationship(
                            source_concept=concept1.id,
                            target_concept=concept2.id,
                            relationship_type=rel_type,
                            confidence=0.6,
                            evidence_text=self._extract_relationship_evidence(concept1, concept2, text)
                        )
                        relationships.append(relationship)
                        
        return relationships

    def _concepts_are_related(self, concept1: ConceptualEntity, concept2: ConceptualEntity, text: str) -> bool:
        """Determine if two concepts are related based on proximity in text."""
        # Simple proximity check - concepts within 200 characters
        pos1 = text.lower().find(concept1.text.lower())
        pos2 = text.lower().find(concept2.text.lower())
        
        if pos1 != -1 and pos2 != -1:
            return abs(pos1 - pos2) <= 200
            
        return False

    def _determine_relationship_type(self, concept1: ConceptualEntity, concept2: ConceptualEntity, 
                                   text: str, patterns: Dict[str, List[str]]) -> Optional[str]:
        """Determine the type of relationship between concepts."""
        # Find the text segment between concepts
        pos1 = text.lower().find(concept1.text.lower())
        pos2 = text.lower().find(concept2.text.lower())
        
        if pos1 == -1 or pos2 == -1:
            return None
            
        start = min(pos1, pos2)
        end = max(pos1 + len(concept1.text), pos2 + len(concept2.text))
        segment = text[start:end].lower()
        
        # Check for relationship patterns
        for rel_type, pattern_list in patterns.items():
            for pattern in pattern_list:
                if re.search(pattern, segment, re.IGNORECASE):
                    return rel_type
                    
        # Default to generic relationship if concepts are close
        return "RELATED_TO"

    def _extract_relationship_evidence(self, concept1: ConceptualEntity, concept2: ConceptualEntity, text: str) -> str:
        """Extract the text evidence for a relationship."""
        pos1 = text.lower().find(concept1.text.lower())
        pos2 = text.lower().find(concept2.text.lower())
        
        if pos1 == -1 or pos2 == -1:
            return ""
            
        # Extract a broader context around both concepts
        start = max(0, min(pos1, pos2) - 50)
        end = min(len(text), max(pos1 + len(concept1.text), pos2 + len(concept2.text)) + 50)
        
        return text[start:end].strip()


class LinkedInConceptExtractor(EnhancedConceptExtractor):
    """Specialized concept extractor for LinkedIn content."""
    
    async def extract_concepts(self, text: str, context: Dict[str, Any] = None) -> List[ConceptualEntity]:
        """Extract LinkedIn-specific concepts."""
        if context is None:
            context = {}
        context["source"] = "linkedin"
        
        concepts = await super().extract_concepts(text, context)
        
        # Add LinkedIn-specific concept extraction
        linkedin_specific = await self._extract_engagement_concepts(text, context)
        concepts.extend(linkedin_specific)
        
        return self._deduplicate_concepts(concepts)

    async def _extract_engagement_concepts(self, text: str, context: Dict[str, Any]) -> List[ConceptualEntity]:
        """Extract engagement and interaction-related concepts."""
        concepts = []
        
        engagement_patterns = [
            r'\b(?:engagement|interaction|feedback)\b',
            r'\b(?:comment|discussion|conversation)\b',
            r'\b(?:share|repost|like)\b',
            r'\b(?:community|network|connection)\b'
        ]
        
        for pattern in engagement_patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                concept_text = match.group(0)
                concept = ConceptualEntity(
                    id=f"linkedin_ENGAGEMENT:{concept_text.lower()}",
                    name=concept_text,
                    text=concept_text,
                    label="ENGAGEMENT",
                    concept_type="ENGAGEMENT",
                    confidence=0.9,
                    metadata={**context, "platform": "linkedin", "type": "engagement"}
                )
                concepts.append(concept)
                
        return concepts


class NotionConceptExtractor(EnhancedConceptExtractor):
    """Specialized concept extractor for Notion content."""
    
    async def extract_concepts(self, text: str, context: Dict[str, Any] = None) -> List[ConceptualEntity]:
        """Extract Notion-specific concepts."""
        if context is None:
            context = {}
        context["source"] = "notion"
        
        concepts = await super().extract_concepts(text, context)
        
        # Add Notion-specific concept extraction
        notion_specific = await self._extract_knowledge_concepts(text, context)
        concepts.extend(notion_specific)
        
        return self._deduplicate_concepts(concepts)

    async def _extract_knowledge_concepts(self, text: str, context: Dict[str, Any]) -> List[ConceptualEntity]:
        """Extract knowledge management and note-taking concepts."""
        concepts = []
        
        knowledge_patterns = [
            r'\b(?:brainstorm|ideation|thinking)\b',
            r'\b(?:draft|outline|structure)\b',
            r'\b(?:research|investigation|exploration)\b',
            r'\b(?:synthesis|summary|conclusion)\b'
        ]
        
        for pattern in knowledge_patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                concept_text = match.group(0)
                concept = ConceptualEntity(
                    id=f"notion_KNOWLEDGE:{concept_text.lower()}",
                    name=concept_text,
                    text=concept_text,
                    label="KNOWLEDGE",
                    concept_type="KNOWLEDGE",
                    confidence=0.8,
                    metadata={**context, "platform": "notion", "type": "knowledge"}
                )
                concepts.append(concept)
                
        return concepts