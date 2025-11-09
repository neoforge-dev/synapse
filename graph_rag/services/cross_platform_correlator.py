"""Cross-platform content correlation and analysis service."""

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any

from graph_rag.core.concept_extractor import (
    ConceptualEntity,
    LinkedInConceptExtractor,
    NotionConceptExtractor,
)
from graph_rag.core.interfaces import GraphRepository
from graph_rag.core.temporal_tracker import ContentPlatform, TemporalTracker

logger = logging.getLogger(__name__)


class CorrelationType(Enum):
    """Types of cross-platform correlations."""
    DRAFT_TO_POST = "draft_to_post"           # Notion draft → LinkedIn post
    POST_TO_COMMENT = "post_to_comment"       # LinkedIn post → LinkedIn comment
    COMMENT_TO_INSIGHT = "comment_to_insight" # LinkedIn comment → Notion insight
    ITERATION = "iteration"                   # Multiple versions of same content
    INSPIRATION = "inspiration"               # Content inspired by other content


@dataclass
class PlatformContent:
    """Represents content from a specific platform."""
    content_id: str
    platform: ContentPlatform
    content_type: str  # post, comment, draft, note, etc.
    text: str
    metadata: dict[str, Any]
    timestamp: datetime
    author: str | None = None
    engagement_metrics: dict[str, int] = field(default_factory=dict)

    def __post_init__(self):
        """Ensure timestamp has timezone info."""
        if self.timestamp.tzinfo is None:
            self.timestamp = self.timestamp.replace(tzinfo=timezone.utc)


@dataclass
class ContentCorrelation:
    """Represents a correlation between content across platforms."""
    source_content: PlatformContent
    target_content: PlatformContent
    correlation_type: CorrelationType
    confidence: float
    shared_concepts: list[str]
    evidence: dict[str, Any]
    temporal_distance: timedelta

    def to_dict(self) -> dict[str, Any]:
        """Convert correlation to dictionary for API responses."""
        return {
            "source": {
                "content_id": self.source_content.content_id,
                "platform": self.source_content.platform.value,
                "content_type": self.source_content.content_type,
                "timestamp": self.source_content.timestamp.isoformat(),
                "text_preview": self.source_content.text[:200] + "..." if len(self.source_content.text) > 200 else self.source_content.text
            },
            "target": {
                "content_id": self.target_content.content_id,
                "platform": self.target_content.platform.value,
                "content_type": self.target_content.content_type,
                "timestamp": self.target_content.timestamp.isoformat(),
                "text_preview": self.target_content.text[:200] + "..." if len(self.target_content.text) > 200 else self.target_content.text
            },
            "correlation_type": self.correlation_type.value,
            "confidence": self.confidence,
            "shared_concepts": self.shared_concepts,
            "evidence": self.evidence,
            "temporal_distance_days": self.temporal_distance.days
        }


class CrossPlatformCorrelator:
    """Service for correlating content across different platforms."""

    def __init__(self, graph_repository: GraphRepository):
        self.graph_repo = graph_repository
        self.temporal_tracker = TemporalTracker()
        self.linkedin_extractor = LinkedInConceptExtractor()
        self.notion_extractor = NotionConceptExtractor()
        self.content_cache: dict[str, PlatformContent] = {}
        self.correlations: list[ContentCorrelation] = []

    async def ingest_linkedin_content(self, linkedin_data: list[dict[str, Any]]) -> list[str]:
        """Ingest LinkedIn content (posts, comments, etc.)."""
        content_ids = []

        for item in linkedin_data:
            content = await self._parse_linkedin_content(item)
            if content:
                self.content_cache[content.content_id] = content
                content_ids.append(content.content_id)

                # Extract concepts and track temporally
                concepts = await self.linkedin_extractor.extract_concepts(
                    content.text,
                    {**content.metadata, "platform": "linkedin", "content_id": content.content_id}
                )

                for concept in concepts:
                    await self.temporal_tracker.track_concept(concept, {
                        "content_id": content.content_id,
                        "platform": "linkedin",
                        "content_type": content.content_type,
                        "timestamp": content.timestamp,
                        "content_snippet": content.text[:500]
                    })

        logger.info(f"Ingested {len(content_ids)} LinkedIn content items")
        return content_ids

    async def ingest_notion_content(self, notion_data: list[dict[str, Any]]) -> list[str]:
        """Ingest Notion content (pages, blocks, etc.)."""
        content_ids = []

        for item in notion_data:
            content = await self._parse_notion_content(item)
            if content:
                self.content_cache[content.content_id] = content
                content_ids.append(content.content_id)

                # Extract concepts and track temporally
                concepts = await self.notion_extractor.extract_concepts(
                    content.text,
                    {**content.metadata, "platform": "notion", "content_id": content.content_id}
                )

                for concept in concepts:
                    await self.temporal_tracker.track_concept(concept, {
                        "content_id": content.content_id,
                        "platform": "notion",
                        "content_type": content.content_type,
                        "timestamp": content.timestamp,
                        "content_snippet": content.text[:500]
                    })

        logger.info(f"Ingested {len(content_ids)} Notion content items")
        return content_ids

    async def _parse_linkedin_content(self, item: dict[str, Any]) -> PlatformContent | None:
        """Parse LinkedIn content item."""
        try:
            content_id = item.get("id") or item.get("urn") or f"linkedin_{hash(str(item))}"
            content_type = item.get("type", "post").lower()

            # Extract text content
            text = ""
            if "text" in item:
                text = item["text"]
            elif "commentary" in item:
                text = item["commentary"]
            elif "content" in item:
                text = item["content"]

            if not text:
                return None

            # Parse timestamp
            timestamp = self._parse_timestamp(item.get("timestamp") or item.get("createdAt") or item.get("publishedAt"))

            # Extract engagement metrics
            engagement = {}
            for metric in ["likes", "comments", "shares", "reactions"]:
                if metric in item:
                    engagement[metric] = item[metric]

            return PlatformContent(
                content_id=content_id,
                platform=ContentPlatform.LINKEDIN,
                content_type=content_type,
                text=text,
                metadata=item,
                timestamp=timestamp,
                author=item.get("author"),
                engagement_metrics=engagement
            )

        except Exception as e:
            logger.error(f"Error parsing LinkedIn content: {e}")
            return None

    async def _parse_notion_content(self, item: dict[str, Any]) -> PlatformContent | None:
        """Parse Notion content item."""
        try:
            content_id = item.get("id") or f"notion_{hash(str(item))}"
            content_type = item.get("object", "page").lower()

            # Extract text content
            text = ""
            if "content" in item:
                text = item["content"]
            elif "plain_text" in item:
                text = item["plain_text"]
            elif "text" in item:
                text = item["text"]
            elif "title" in item:
                text = item["title"]

            if not text:
                return None

            # Parse timestamp
            timestamp = self._parse_timestamp(item.get("created_time") or item.get("last_edited_time"))

            return PlatformContent(
                content_id=content_id,
                platform=ContentPlatform.NOTION,
                content_type=content_type,
                text=text,
                metadata=item,
                timestamp=timestamp,
                author=item.get("created_by", {}).get("name")
            )

        except Exception as e:
            logger.error(f"Error parsing Notion content: {e}")
            return None

    def _parse_timestamp(self, timestamp_str: str | None) -> datetime:
        """Parse timestamp string to datetime."""
        if not timestamp_str:
            return datetime.now(timezone.utc)

        try:
            # Handle ISO format with Z
            if timestamp_str.endswith('Z'):
                timestamp_str = timestamp_str[:-1] + '+00:00'
            return datetime.fromisoformat(timestamp_str)
        except ValueError:
            try:
                # Try common formats
                return datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S")
            except ValueError:
                return datetime.now(timezone.utc)

    async def find_correlations(self, max_temporal_distance_days: int = 30) -> list[ContentCorrelation]:
        """Find correlations between content across platforms."""
        correlations = []
        max_distance = timedelta(days=max_temporal_distance_days)

        # Get all content sorted by timestamp
        all_content = list(self.content_cache.values())
        all_content.sort(key=lambda x: x.timestamp)

        # Compare each piece of content with others
        for i, content1 in enumerate(all_content):
            for _j, content2 in enumerate(all_content[i+1:], i+1):
                # Skip if same platform and not iteration type
                if content1.platform == content2.platform:
                    continue

                # Check temporal proximity
                temporal_distance = abs(content2.timestamp - content1.timestamp)
                if temporal_distance > max_distance:
                    continue

                # Find correlation
                correlation = await self._analyze_correlation(content1, content2, temporal_distance)
                if correlation and correlation.confidence > 0.3:  # Minimum confidence threshold
                    correlations.append(correlation)

        self.correlations = correlations
        logger.info(f"Found {len(correlations)} content correlations")
        return correlations

    async def _analyze_correlation(self, content1: PlatformContent, content2: PlatformContent,
                                 temporal_distance: timedelta) -> ContentCorrelation | None:
        """Analyze correlation between two pieces of content."""

        # Determine source/target based on timestamp (earlier is source)
        if content1.timestamp <= content2.timestamp:
            source, target = content1, content2
        else:
            source, target = content2, content1

        # Extract concepts from both pieces of content
        source_concepts = await self._extract_concepts_for_platform(source)
        target_concepts = await self._extract_concepts_for_platform(target)

        # Find shared concepts
        shared_concepts = self._find_shared_concepts(source_concepts, target_concepts)

        if not shared_concepts:
            return None

        # Calculate confidence based on shared concepts and other factors
        confidence = self._calculate_correlation_confidence(
            source, target, shared_concepts, temporal_distance
        )

        # Determine correlation type
        correlation_type = self._determine_correlation_type(source, target, shared_concepts)

        # Gather evidence
        evidence = {
            "shared_concept_count": len(shared_concepts),
            "text_similarity": self._calculate_text_similarity(source.text, target.text),
            "temporal_proximity_score": self._calculate_temporal_score(temporal_distance),
            "platform_transition": f"{source.platform.value}_to_{target.platform.value}"
        }

        return ContentCorrelation(
            source_content=source,
            target_content=target,
            correlation_type=correlation_type,
            confidence=confidence,
            shared_concepts=shared_concepts,
            evidence=evidence,
            temporal_distance=temporal_distance
        )

    async def _extract_concepts_for_platform(self, content: PlatformContent) -> list[ConceptualEntity]:
        """Extract concepts based on platform."""
        context = {
            **content.metadata,
            "platform": content.platform.value,
            "content_id": content.content_id
        }

        if content.platform == ContentPlatform.LINKEDIN:
            return await self.linkedin_extractor.extract_concepts(content.text, context)
        elif content.platform == ContentPlatform.NOTION:
            return await self.notion_extractor.extract_concepts(content.text, context)
        else:
            # Use generic extractor
            from graph_rag.core.concept_extractor import EnhancedConceptExtractor
            extractor = EnhancedConceptExtractor()
            return await extractor.extract_concepts(content.text, context)

    def _find_shared_concepts(self, concepts1: list[ConceptualEntity],
                            concepts2: list[ConceptualEntity]) -> list[str]:
        """Find concepts shared between two lists."""
        shared = []

        for c1 in concepts1:
            for c2 in concepts2:
                if self._concepts_match(c1, c2):
                    shared.append(c1.name)
                    break

        return shared

    def _concepts_match(self, concept1: ConceptualEntity, concept2: ConceptualEntity) -> bool:
        """Determine if two concepts match."""
        # Exact name match
        if concept1.name.lower() == concept2.name.lower():
            return True

        # Similar concept types and text overlap
        if (concept1.concept_type == concept2.concept_type and
            self._text_overlap_ratio(concept1.text, concept2.text) > 0.7):
            return True

        return False

    def _text_overlap_ratio(self, text1: str, text2: str) -> float:
        """Calculate text overlap ratio."""
        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())
        if not words1 or not words2:
            return 0.0
        return len(words1.intersection(words2)) / len(words1.union(words2))

    def _calculate_correlation_confidence(self, source: PlatformContent, target: PlatformContent,
                                        shared_concepts: list[str], temporal_distance: timedelta) -> float:
        """Calculate correlation confidence score."""
        confidence = 0.0

        # Shared concepts contribute to confidence
        concept_score = min(len(shared_concepts) * 0.2, 0.6)  # Max 0.6 from concepts
        confidence += concept_score

        # Text similarity contributes
        text_sim = self._calculate_text_similarity(source.text, target.text)
        confidence += text_sim * 0.3  # Max 0.3 from text similarity

        # Temporal proximity contributes
        temporal_score = max(0, 1 - (temporal_distance.days / 30))  # Closer = higher score
        confidence += temporal_score * 0.1  # Max 0.1 from temporal proximity

        return min(confidence, 1.0)

    def _calculate_text_similarity(self, text1: str, text2: str) -> float:
        """Calculate text similarity using simple word overlap."""
        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())

        if not words1 or not words2:
            return 0.0

        intersection = len(words1.intersection(words2))
        union = len(words1.union(words2))

        return intersection / union if union > 0 else 0.0

    def _calculate_temporal_score(self, temporal_distance: timedelta) -> float:
        """Calculate temporal proximity score."""
        days = temporal_distance.days
        if days == 0:
            return 1.0
        elif days <= 7:
            return 0.8
        elif days <= 14:
            return 0.6
        elif days <= 30:
            return 0.4
        else:
            return 0.1

    def _determine_correlation_type(self, source: PlatformContent, target: PlatformContent,
                                  shared_concepts: list[str]) -> CorrelationType:
        """Determine the type of correlation."""

        # Notion to LinkedIn suggests draft to post
        if (source.platform == ContentPlatform.NOTION and
            target.platform == ContentPlatform.LINKEDIN and
            target.content_type == "post"):
            return CorrelationType.DRAFT_TO_POST

        # LinkedIn post to LinkedIn comment
        if (source.platform == ContentPlatform.LINKEDIN and
            target.platform == ContentPlatform.LINKEDIN and
            source.content_type == "post" and target.content_type == "comment"):
            return CorrelationType.POST_TO_COMMENT

        # LinkedIn comment to Notion insight
        if (source.platform == ContentPlatform.LINKEDIN and
            target.platform == ContentPlatform.NOTION and
            source.content_type == "comment"):
            return CorrelationType.COMMENT_TO_INSIGHT

        # Same platform suggests iteration
        if source.platform == target.platform:
            return CorrelationType.ITERATION

        # Default to inspiration
        return CorrelationType.INSPIRATION

    async def get_content_lifecycle(self, content_id: str) -> dict[str, Any] | None:
        """Get the complete lifecycle of a piece of content."""
        content = self.content_cache.get(content_id)
        if not content:
            return None

        # Find all correlations involving this content
        related_correlations = [
            corr for corr in self.correlations
            if (corr.source_content.content_id == content_id or
                corr.target_content.content_id == content_id)
        ]

        # Build lifecycle chain
        lifecycle = {
            "content": content,
            "correlations": related_correlations,
            "evolution_stages": [],
            "cross_platform_journey": []
        }

        # Get temporal evolution if available
        evolution = await self.temporal_tracker.get_idea_evolution(content_id)
        if evolution:
            lifecycle["evolution_stages"] = [
                {
                    "stage": version.stage.value,
                    "platform": version.platform.value,
                    "timestamp": version.timestamp.isoformat(),
                    "content_id": version.content_id
                }
                for version in evolution.get_chronological_versions()
            ]

        return lifecycle

    async def analyze_content_gaps(self) -> list[dict[str, Any]]:
        """Analyze gaps in content development across platforms."""
        gaps = []

        # Find Notion content that hasn't been published to LinkedIn
        notion_content = [c for c in self.content_cache.values() if c.platform == ContentPlatform.NOTION]
        [c for c in self.content_cache.values() if c.platform == ContentPlatform.LINKEDIN]

        for notion_item in notion_content:
            # Check if there's related LinkedIn content
            has_linkedin_version = False
            for correlation in self.correlations:
                if (correlation.source_content.content_id == notion_item.content_id and
                    correlation.target_content.platform == ContentPlatform.LINKEDIN):
                    has_linkedin_version = True
                    break

            if not has_linkedin_version:
                gaps.append({
                    "type": "unpublished_notion_content",
                    "content_id": notion_item.content_id,
                    "platform": "notion",
                    "age_days": (datetime.now(timezone.utc) - notion_item.timestamp).days,
                    "text_preview": notion_item.text[:200],
                    "recommendation": "Consider publishing to LinkedIn"
                })

        return gaps

    async def get_platform_analytics(self) -> dict[str, Any]:
        """Get analytics about cross-platform content patterns."""
        analytics = {
            "content_counts": {},
            "correlation_types": {},
            "platform_transitions": {},
            "temporal_patterns": {},
            "engagement_analysis": {}
        }

        # Content counts by platform
        for content in self.content_cache.values():
            platform = content.platform.value
            analytics["content_counts"][platform] = analytics["content_counts"].get(platform, 0) + 1

        # Correlation type distribution
        for correlation in self.correlations:
            corr_type = correlation.correlation_type.value
            analytics["correlation_types"][corr_type] = analytics["correlation_types"].get(corr_type, 0) + 1

        # Platform transitions
        for correlation in self.correlations:
            transition = f"{correlation.source_content.platform.value}_to_{correlation.target_content.platform.value}"
            analytics["platform_transitions"][transition] = analytics["platform_transitions"].get(transition, 0) + 1

        # Temporal patterns
        temporal_distances = [corr.temporal_distance.days for corr in self.correlations]
        if temporal_distances:
            analytics["temporal_patterns"] = {
                "average_days_between_correlations": sum(temporal_distances) / len(temporal_distances),
                "min_days": min(temporal_distances),
                "max_days": max(temporal_distances)
            }

        return analytics
