"""Enhanced concept and idea extraction system for advanced knowledge mapping."""

import logging
import re
from abc import ABC, abstractmethod
from typing import Any

from pydantic import Field

from graph_rag.domain.models import Entity

logger = logging.getLogger(__name__)


class ConceptualEntity(Entity):
    """Extended entity for conceptual ideas and themes."""
    type: str = "ConceptualEntity"
    concept_type: str = Field(default="IDEA", description="Type of concept: IDEA, THEME, STRATEGY, etc.")
    confidence: float = Field(default=0.0, description="Confidence score for extracted concept")
    context_window: str = Field(default="", description="Text context where concept was found")
    temporal_markers: list[str] = Field(default_factory=list, description="Time-related indicators")
    related_concepts: list[str] = Field(default_factory=list, description="Related concept IDs")
    sentiment: str | None = Field(default=None, description="Sentiment of the concept")
    text: str = Field(..., description="Original text span of the concept")


class IdeaRelationship:
    """Represents relationships between ideas/concepts."""
    def __init__(self, source_concept: str, target_concept: str,
                 relationship_type: str, confidence: float = 0.0,
                 evidence_text: str = "", temporal_order: int | None = None):
        self.source_concept = source_concept
        self.target_concept = target_concept
        self.relationship_type = relationship_type  # BUILDS_UPON, CONTRADICTS, INFLUENCES, EVOLVES_TO
        self.confidence = confidence
        self.evidence_text = evidence_text
        self.temporal_order = temporal_order


class ConceptExtractor(ABC):
    """Abstract base class for extracting concepts and ideas from text."""

    @abstractmethod
    async def extract_concepts(self, text: str, context: dict[str, Any] = None) -> list[ConceptualEntity]:
        """Extract conceptual ideas and themes from text."""
        pass

    @abstractmethod
    async def extract_idea_relationships(self, concepts: list[ConceptualEntity], text: str) -> list[IdeaRelationship]:
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

    async def extract_concepts(self, text: str, context: dict[str, Any] = None) -> list[ConceptualEntity]:
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

    async def _extract_rule_based_concepts(self, text: str, context: dict[str, Any] = None) -> list[ConceptualEntity]:
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

        # Belief/preference patterns
        belief_patterns = [
            r'\bI\s+(?:believe|think|feel|prefer|value)\b',
            r'\b(?:in\s+my\s+opinion|personally|I\s+am\s+convinced)\b',
            r'\b(?:we\s+should|it\'s\s+important|what\s+matters)\b',
            r'\b(?:fundamental|core|essential|critical)\s+(?:principle|value|belief)\b',
            r'\b(?:strongly\s+believe|deeply\s+value|firm\s+belief)\b'
        ]

        # Hot take patterns (controversial/provocative statements)
        hot_take_patterns = [
            r'\b(?:unpopular\s+opinion|hot\s+take|controversial)\b',
            r'\b(?:everyone\s+is\s+wrong|nobody\s+talks\s+about)\b',
            r'\b(?:the\s+truth\s+is|let\'s\s+be\s+honest|real\s+talk)\b',
            r'\b(?:most\s+people\s+don\'t|why\s+(?:nobody|everyone))\b',
            r'\b(?:stop\s+saying|enough\s+with|tired\s+of\s+hearing)\b'
        ]

        all_patterns = {
            "STRATEGY": strategy_patterns,
            "INNOVATION": innovation_patterns,
            "PROCESS": process_patterns,
            "BELIEF": belief_patterns,
            "HOT_TAKE": hot_take_patterns
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

                    # Analyze sentiment and engagement potential
                    sentiment = self._analyze_sentiment(context_window, concept_type)
                    engagement_potential = self._calculate_engagement_potential(context_window, concept_type)

                    # Adjust confidence based on concept type
                    confidence = 0.7  # Base confidence
                    if concept_type in ["HOT_TAKE", "BELIEF"]:
                        confidence = 0.8  # Higher confidence for explicit beliefs/hot takes

                    concept = ConceptualEntity(
                        id=f"{concept_type}:{concept_text.lower().replace(' ', '_')}",
                        name=concept_text,
                        text=concept_text,
                        concept_type=concept_type,
                        confidence=confidence,
                        context_window=context_window,
                        sentiment=sentiment,
                        properties={
                            **(context or {}),
                            "engagement_potential": engagement_potential,
                            "extraction_method": "rule_based"
                        }
                    )
                    concepts.append(concept)

        return concepts

    async def _extract_nlp_concepts(self, text: str, context: dict[str, Any] = None) -> list[ConceptualEntity]:
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
                        concept_type=concept_type,
                        confidence=0.6,
                        context_window=str(chunk.sent) if chunk.sent else "",
                        properties=context or {}
                    )
                    concepts.append(concept)

        return concepts

    async def _extract_domain_concepts(self, text: str, context: dict[str, Any] = None) -> list[ConceptualEntity]:
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

    async def _extract_linkedin_concepts(self, text: str, context: dict[str, Any]) -> list[ConceptualEntity]:
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
                        concept_type=concept_type,
                        confidence=0.8,  # High confidence for platform-specific patterns
                        properties={**context, "platform": "linkedin"}
                    )
                    concepts.append(concept)

        return concepts

    async def _extract_notion_concepts(self, text: str, context: dict[str, Any]) -> list[ConceptualEntity]:
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
                    concept_type="KNOWLEDGE",
                    confidence=0.7,
                    properties={**context, "platform": "notion"}
                )
                concepts.append(concept)

        return concepts

    def _classify_concept_type(self, text: str, chunk=None) -> str | None:
        """Classify the type of concept based on linguistic patterns."""
        text_lower = text.lower()

        # Belief/preference indicators
        belief_indicators = ["believe", "think", "feel", "prefer", "value", "opinion", "personally", "important", "matters"]
        if any(word in text_lower for word in belief_indicators):
            return "BELIEF"

        # Hot take indicators
        hot_take_indicators = ["unpopular", "controversial", "truth is", "real talk", "everyone is wrong", "nobody talks"]
        if any(phrase in text_lower for phrase in hot_take_indicators):
            return "HOT_TAKE"

        # Strategy-related concepts
        if any(word in text_lower for word in ["strategy", "approach", "method", "plan"]):
            return "STRATEGY"

        # Innovation concepts
        if any(word in text_lower for word in ["innovation", "technology", "digital", "transformation"]):
            return "INNOVATION"

        # Process concepts
        if any(word in text_lower for word in ["process", "workflow", "system", "framework"]):
            return "PROCESS"

        # Preference indicators
        preference_indicators = ["prefer", "like", "use", "follow", "method", "approach", "system", "tool"]
        if any(word in text_lower for word in preference_indicators):
            return "PREFERENCE"

        # Generic concept if it looks conceptual
        if chunk and chunk.root.pos_ in ["NOUN"] and len(text.split()) >= 2:
            return "CONCEPT"

        return None

    def _deduplicate_concepts(self, concepts: list[ConceptualEntity]) -> list[ConceptualEntity]:
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

    async def extract_idea_relationships(self, concepts: list[ConceptualEntity], text: str) -> list[IdeaRelationship]:
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
                                   text: str, patterns: dict[str, list[str]]) -> str | None:
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

    def _analyze_sentiment(self, text: str, concept_type: str) -> str:
        """Analyze sentiment of a concept based on linguistic indicators."""
        text_lower = text.lower()

        # Strong positive indicators
        positive_words = ["amazing", "breakthrough", "incredible", "outstanding", "excellent", "fantastic", "revolutionary"]
        # Strong negative indicators
        negative_words = ["terrible", "awful", "horrible", "worst", "failed", "disaster", "broken"]
        # Controversial indicators
        controversial_words = ["controversial", "unpopular", "against", "wrong", "disagree", "challenge"]

        positive_count = sum(1 for word in positive_words if word in text_lower)
        negative_count = sum(1 for word in negative_words if word in text_lower)
        controversial_count = sum(1 for word in controversial_words if word in text_lower)

        if concept_type == "HOT_TAKE":
            return "controversial" if controversial_count > 0 else "provocative"
        elif positive_count > negative_count:
            return "positive"
        elif negative_count > positive_count:
            return "negative"
        else:
            return "neutral"

    def _calculate_engagement_potential(self, text: str, concept_type: str) -> float:
        """Calculate potential engagement score based on content analysis."""
        text_lower = text.lower()
        score = 0.5  # Base score

        # Hot takes and beliefs tend to drive more engagement
        if concept_type in ["HOT_TAKE", "BELIEF"]:
            score += 0.3

        # Question format increases engagement
        if "?" in text:
            score += 0.2

        # Personal pronouns increase engagement
        personal_pronouns = ["i", "my", "me", "we", "us", "our"]
        personal_count = sum(1 for pronoun in personal_pronouns if f" {pronoun} " in f" {text_lower} ")
        score += min(personal_count * 0.1, 0.3)

        # Call to action increases engagement
        cta_phrases = ["what do you think", "share your", "tell me", "comment below", "your thoughts", "agree or disagree"]
        if any(phrase in text_lower for phrase in cta_phrases):
            score += 0.3

        # Emotional words increase engagement
        emotional_words = ["love", "hate", "excited", "frustrated", "amazing", "terrible", "shocked", "surprised"]
        emotional_count = sum(1 for word in emotional_words if word in text_lower)
        score += min(emotional_count * 0.1, 0.2)

        return min(score, 1.0)  # Cap at 1.0


class LinkedInConceptExtractor(EnhancedConceptExtractor):
    """Specialized concept extractor for LinkedIn content."""

    async def extract_concepts(self, text: str, context: dict[str, Any] = None) -> list[ConceptualEntity]:
        """Extract LinkedIn-specific concepts."""
        if context is None:
            context = {}
        context["source"] = "linkedin"

        concepts = await super().extract_concepts(text, context)

        # Add LinkedIn-specific concept extraction
        linkedin_specific = await self._extract_engagement_concepts(text, context)
        concepts.extend(linkedin_specific)

        # Extract professional beliefs and hot takes
        professional_beliefs = await self._extract_professional_beliefs(text, context)
        concepts.extend(professional_beliefs)

        linkedin_hot_takes = await self._extract_linkedin_hot_takes(text, context)
        concepts.extend(linkedin_hot_takes)

        return self._deduplicate_concepts(concepts)

    async def _extract_engagement_concepts(self, text: str, context: dict[str, Any]) -> list[ConceptualEntity]:
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
                    concept_type="ENGAGEMENT",
                    confidence=0.9,
                    properties={**context, "platform": "linkedin", "type": "engagement"}
                )
                concepts.append(concept)

        return concepts

    async def _extract_professional_beliefs(self, text: str, context: dict[str, Any]) -> list[ConceptualEntity]:
        """Extract professional beliefs and values from LinkedIn content."""
        concepts = []

        # Professional belief patterns specific to LinkedIn
        professional_belief_patterns = [
            r'\b(?:leadership|management)\s+(?:is|means|requires)\b',
            r'\b(?:success|growth|innovation)\s+(?:comes from|depends on|requires)\b',
            r'\b(?:the\s+key\s+to|what\s+makes|why)\s+(?:great|successful|effective)\b',
            r'\b(?:always|never)\s+(?:hire|work with|trust|believe in)\b',
            r'\b(?:culture|values|principles)\s+(?:matter|define|drive)\b'
        ]

        for pattern in professional_belief_patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                # Extract the full sentence or extended context
                start = max(0, match.start() - 50)
                end = min(len(text), match.end() + 100)
                full_context = text[start:end]

                sentiment = self._analyze_sentiment(full_context, "BELIEF")
                engagement_potential = self._calculate_engagement_potential(full_context, "BELIEF")

                concept = ConceptualEntity(
                    id=f"linkedin_BELIEF:{match.group(0).lower().replace(' ', '_')}",
                    name=match.group(0),
                    text=match.group(0),
                    concept_type="BELIEF",
                    confidence=0.85,  # High confidence for LinkedIn professional beliefs
                    context_window=full_context,
                    sentiment=sentiment,
                    properties={
                        **context,
                        "platform": "linkedin",
                        "type": "professional_belief",
                        "engagement_potential": engagement_potential
                    }
                )
                concepts.append(concept)

        return concepts

    async def _extract_linkedin_hot_takes(self, text: str, context: dict[str, Any]) -> list[ConceptualEntity]:
        """Extract hot takes and controversial opinions from LinkedIn content."""
        concepts = []

        # LinkedIn-specific hot take patterns
        linkedin_hot_take_patterns = [
            r'\b(?:most\s+(?:companies|leaders|people))\s+(?:don\'t|won\'t|can\'t)\b',
            r'\b(?:why\s+(?:nobody|everyone))\s+(?:talks about|ignores|misses)\b',
            r'\b(?:the\s+problem\s+with|what\'s\s+wrong\s+with)\s+(?:corporate|business|leadership)\b',
            r'\b(?:stop\s+(?:saying|doing|believing)|enough\s+with)\b',
            r'\b(?:unpopular\s+opinion|controversial\s+take|let\'s\s+be\s+honest)\b'
        ]

        for pattern in linkedin_hot_take_patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                # Extract broader context for hot takes
                start = max(0, match.start() - 30)
                end = min(len(text), match.end() + 150)
                full_context = text[start:end]

                sentiment = self._analyze_sentiment(full_context, "HOT_TAKE")
                engagement_potential = self._calculate_engagement_potential(full_context, "HOT_TAKE")

                concept = ConceptualEntity(
                    id=f"linkedin_HOT_TAKE:{match.group(0).lower().replace(' ', '_')}",
                    name=match.group(0),
                    text=match.group(0),
                    concept_type="HOT_TAKE",
                    confidence=0.9,  # Very high confidence for explicit hot take markers
                    context_window=full_context,
                    sentiment=sentiment,
                    properties={
                        **context,
                        "platform": "linkedin",
                        "type": "professional_hot_take",
                        "engagement_potential": engagement_potential,
                        "viral_potential": "high" if engagement_potential > 0.8 else "medium"
                    }
                )
                concepts.append(concept)

        return concepts


class NotionConceptExtractor(EnhancedConceptExtractor):
    """Specialized concept extractor for Notion content."""

    async def extract_concepts(self, text: str, context: dict[str, Any] = None) -> list[ConceptualEntity]:
        """Extract Notion-specific concepts."""
        if context is None:
            context = {}
        context["source"] = "notion"

        concepts = await super().extract_concepts(text, context)

        # Add Notion-specific concept extraction
        notion_specific = await self._extract_knowledge_concepts(text, context)
        concepts.extend(notion_specific)

        # Extract personal beliefs and preferences in knowledge management context
        personal_beliefs = await self._extract_notion_beliefs(text, context)
        concepts.extend(personal_beliefs)

        # Extract knowledge preferences and methodologies
        knowledge_prefs = await self._extract_knowledge_preferences(text, context)
        concepts.extend(knowledge_prefs)

        return self._deduplicate_concepts(concepts)

    async def _extract_knowledge_concepts(self, text: str, context: dict[str, Any]) -> list[ConceptualEntity]:
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
                    concept_type="KNOWLEDGE",
                    confidence=0.8,
                    properties={**context, "platform": "notion", "type": "knowledge"}
                )
                concepts.append(concept)

        return concepts

    async def _extract_notion_beliefs(self, text: str, context: dict[str, Any]) -> list[ConceptualEntity]:
        """Extract personal beliefs and values from Notion content."""
        concepts = []

        # Personal belief patterns in knowledge management context
        notion_belief_patterns = [
            r'\b(?:I\s+(?:believe|think|feel|prefer))\s+(?:that\s+)?(?:\w+\s+){1,10}(?:is|are|should|will)\b',
            r'\b(?:my\s+(?:philosophy|approach|method|preference))\s+(?:is|for|on)\b',
            r'\b(?:what\s+works\s+for\s+me|my\s+experience\s+shows)\b',
            r'\b(?:I\'ve\s+learned\s+that|it\'s\s+important\s+to)\b',
            r'\b(?:personally|in\s+my\s+opinion|from\s+my\s+perspective)\b'
        ]

        for pattern in notion_belief_patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                # Extract the full sentence containing the belief
                start = max(0, match.start() - 20)
                end = min(len(text), match.end() + 80)
                full_context = text[start:end]

                sentiment = self._analyze_sentiment(full_context, "BELIEF")

                concept = ConceptualEntity(
                    id=f"notion_BELIEF:{match.group(0).lower().replace(' ', '_')[:50]}",
                    name=match.group(0),
                    text=match.group(0),
                    concept_type="BELIEF",
                    confidence=0.8,  # High confidence for personal beliefs in Notion
                    context_window=full_context,
                    sentiment=sentiment,
                    properties={
                        **context,
                        "platform": "notion",
                        "type": "personal_belief",
                        "knowledge_domain": "personal_methodology"
                    }
                )
                concepts.append(concept)

        return concepts

    async def _extract_knowledge_preferences(self, text: str, context: dict[str, Any]) -> list[ConceptualEntity]:
        """Extract knowledge management preferences and methodologies."""
        concepts = []

        # Knowledge preference patterns
        knowledge_pref_patterns = [
            r'\b(?:prefer|like|use|follow)\s+(?:to\s+)?(?:\w+\s+){1,5}(?:method|approach|system|tool)\b',
            r'\b(?:best\s+way\s+to|effective\s+method\s+for|how\s+I\s+organize)\b',
            r'\b(?:workflow|process|routine)\s+(?:that\s+works|I\s+use|for)\b',
            r'\b(?:template|framework|structure)\s+(?:I\s+(?:use|prefer|like))\b',
            r'\b(?:note-taking|research|learning)\s+(?:strategy|method|approach)\b'
        ]

        for pattern in knowledge_pref_patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                # Extract context around the preference
                start = max(0, match.start() - 30)
                end = min(len(text), match.end() + 70)
                full_context = text[start:end]

                concept = ConceptualEntity(
                    id=f"notion_PREFERENCE:{match.group(0).lower().replace(' ', '_')[:50]}",
                    name=match.group(0),
                    text=match.group(0),
                    concept_type="PREFERENCE",
                    confidence=0.75,  # Medium-high confidence for preferences
                    context_window=full_context,
                    properties={
                        **context,
                        "platform": "notion",
                        "type": "knowledge_preference",
                        "domain": "personal_knowledge_management"
                    }
                )
                concepts.append(concept)

        return concepts
