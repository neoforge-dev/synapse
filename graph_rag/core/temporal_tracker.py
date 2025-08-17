"""Temporal tracking system for idea evolution and cross-platform correlation."""

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from graph_rag.core.concept_extractor import ConceptualEntity

logger = logging.getLogger(__name__)


class IdeaStage(Enum):
    """Stages of idea development."""
    CONCEPTION = "conception"       # Initial idea formation
    DRAFT = "draft"                # Draft/planning stage
    REFINEMENT = "refinement"      # Iterative improvement
    PUBLICATION = "publication"    # Published content
    ENGAGEMENT = "engagement"      # Community interaction
    EVOLUTION = "evolution"        # Further development


class ContentPlatform(Enum):
    """Supported content platforms."""
    NOTION = "notion"
    LINKEDIN = "linkedin"
    BLOG = "blog"
    EMAIL = "email"
    OTHER = "other"


@dataclass
class TemporalConcept:
    """A concept with temporal tracking information."""
    concept: ConceptualEntity
    stage: IdeaStage
    platform: ContentPlatform
    timestamp: datetime
    content_id: str
    predecessor_id: str | None = None  # Links to earlier version
    successor_ids: list[str] = field(default_factory=list)  # Links to later versions
    engagement_metrics: dict[str, int] = field(default_factory=dict)
    content_snippet: str = ""

    def __post_init__(self):
        """Ensure timestamp has timezone info."""
        if self.timestamp.tzinfo is None:
            self.timestamp = self.timestamp.replace(tzinfo=timezone.utc)


@dataclass
class IdeaEvolution:
    """Tracks the evolution of an idea across time and platforms."""
    core_idea_id: str
    concept_versions: list[TemporalConcept] = field(default_factory=list)
    evolution_path: list[str] = field(default_factory=list)  # Ordered concept IDs
    cross_platform_links: dict[str, list[str]] = field(default_factory=dict)

    def add_concept_version(self, temporal_concept: TemporalConcept):
        """Add a new version of the concept."""
        self.concept_versions.append(temporal_concept)
        self.evolution_path.append(temporal_concept.concept.id)

        # Update cross-platform links
        platform_key = temporal_concept.platform.value
        if platform_key not in self.cross_platform_links:
            self.cross_platform_links[platform_key] = []
        self.cross_platform_links[platform_key].append(temporal_concept.concept.id)

    def get_chronological_versions(self) -> list[TemporalConcept]:
        """Get concept versions sorted by timestamp."""
        return sorted(self.concept_versions, key=lambda x: x.timestamp)

    def get_platform_progression(self) -> list[tuple[ContentPlatform, datetime]]:
        """Get the progression of the idea across platforms."""
        platform_times = []
        for version in self.get_chronological_versions():
            platform_times.append((version.platform, version.timestamp))
        return platform_times


class TemporalTracker:
    """Tracks idea evolution and cross-platform correlation."""

    def __init__(self):
        self.idea_evolutions: dict[str, IdeaEvolution] = {}
        self.concept_to_evolution: dict[str, str] = {}  # Maps concept ID to evolution ID

    async def track_concept(self, concept: ConceptualEntity, content_metadata: dict[str, Any]) -> str:
        """Track a new concept or version of an existing concept."""

        # Create temporal concept
        temporal_concept = TemporalConcept(
            concept=concept,
            stage=self._determine_stage(content_metadata),
            platform=self._determine_platform(content_metadata),
            timestamp=self._extract_timestamp(content_metadata),
            content_id=content_metadata.get("content_id", "unknown"),
            content_snippet=content_metadata.get("content_snippet", "")
        )

        # Check if this is a new version of an existing idea
        evolution_id = await self._find_or_create_evolution(temporal_concept)

        # Add to evolution
        if evolution_id not in self.idea_evolutions:
            self.idea_evolutions[evolution_id] = IdeaEvolution(core_idea_id=evolution_id)

        evolution = self.idea_evolutions[evolution_id]
        evolution.add_concept_version(temporal_concept)

        # Update mapping
        self.concept_to_evolution[concept.id] = evolution_id

        # Link to predecessors if applicable
        await self._link_to_predecessors(temporal_concept, evolution)

        return evolution_id

    async def _find_or_create_evolution(self, temporal_concept: TemporalConcept) -> str:
        """Find existing evolution or create new one."""
        concept = temporal_concept.concept

        # Look for similar concepts in existing evolutions
        for evolution_id, evolution in self.idea_evolutions.items():
            for existing_version in evolution.concept_versions:
                if self._concepts_are_similar(concept, existing_version.concept):
                    return evolution_id

        # Create new evolution ID
        return f"evolution_{concept.name.lower().replace(' ', '_')}_{temporal_concept.timestamp.isoformat()}"

    def _concepts_are_similar(self, concept1: ConceptualEntity, concept2: ConceptualEntity) -> bool:
        """Determine if two concepts represent the same idea."""
        # Simple similarity check - can be enhanced with embeddings

        # Same name (case-insensitive)
        if concept1.name.lower() == concept2.name.lower():
            return True

        # Similar concept types and overlapping text
        if (concept1.concept_type == concept2.concept_type and
            self._text_overlap(concept1.text, concept2.text) > 0.7):
            return True

        # Check for keyword overlap in names
        words1 = set(concept1.name.lower().split())
        words2 = set(concept2.name.lower().split())
        if len(words1.intersection(words2)) / len(words1.union(words2)) > 0.6:
            return True

        return False

    def _text_overlap(self, text1: str, text2: str) -> float:
        """Calculate text overlap ratio."""
        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())
        if not words1 or not words2:
            return 0.0
        return len(words1.intersection(words2)) / len(words1.union(words2))

    def _determine_stage(self, metadata: dict[str, Any]) -> IdeaStage:
        """Determine the stage of idea development from metadata."""
        content_type = metadata.get("content_type", "").lower()
        platform = metadata.get("platform", "").lower()

        # Notion content is typically draft/planning
        if platform == "notion":
            if "draft" in content_type or "note" in content_type:
                return IdeaStage.DRAFT
            elif "research" in content_type:
                return IdeaStage.CONCEPTION
            else:
                return IdeaStage.REFINEMENT

        # LinkedIn content is typically published
        elif platform == "linkedin":
            if "comment" in content_type:
                return IdeaStage.ENGAGEMENT
            else:
                return IdeaStage.PUBLICATION

        # Default staging
        if "draft" in content_type:
            return IdeaStage.DRAFT
        elif "publish" in content_type:
            return IdeaStage.PUBLICATION
        else:
            return IdeaStage.REFINEMENT

    def _determine_platform(self, metadata: dict[str, Any]) -> ContentPlatform:
        """Determine the content platform from metadata."""
        platform = metadata.get("platform", "").lower()

        if platform == "notion":
            return ContentPlatform.NOTION
        elif platform == "linkedin":
            return ContentPlatform.LINKEDIN
        elif platform in ["blog", "website"]:
            return ContentPlatform.BLOG
        elif platform == "email":
            return ContentPlatform.EMAIL
        else:
            return ContentPlatform.OTHER

    def _extract_timestamp(self, metadata: dict[str, Any]) -> datetime:
        """Extract timestamp from metadata."""
        timestamp = metadata.get("timestamp") or metadata.get("created_at") or metadata.get("published_at")

        if timestamp is None:
            return datetime.now(timezone.utc)

        if isinstance(timestamp, str):
            try:
                return datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            except ValueError:
                return datetime.now(timezone.utc)
        elif isinstance(timestamp, datetime):
            if timestamp.tzinfo is None:
                return timestamp.replace(tzinfo=timezone.utc)
            return timestamp
        else:
            return datetime.now(timezone.utc)

    async def _link_to_predecessors(self, temporal_concept: TemporalConcept, evolution: IdeaEvolution):
        """Link concept to its predecessors in the evolution."""
        chronological_versions = evolution.get_chronological_versions()

        # Find the immediate predecessor
        for i, version in enumerate(chronological_versions):
            if version.concept.id == temporal_concept.concept.id:
                if i > 0:
                    predecessor = chronological_versions[i-1]
                    temporal_concept.predecessor_id = predecessor.concept.id
                    predecessor.successor_ids.append(temporal_concept.concept.id)
                break

    async def get_idea_evolution(self, concept_id: str) -> IdeaEvolution | None:
        """Get the evolution chain for a concept."""
        evolution_id = self.concept_to_evolution.get(concept_id)
        if evolution_id:
            return self.idea_evolutions.get(evolution_id)
        return None

    async def get_cross_platform_correlations(self, evolution_id: str) -> dict[str, list[str]]:
        """Get cross-platform correlations for an idea evolution."""
        evolution = self.idea_evolutions.get(evolution_id)
        if evolution:
            return evolution.cross_platform_links
        return {}

    async def find_content_gaps(self, days_threshold: int = 30) -> list[dict[str, Any]]:
        """Find ideas that haven't been developed recently."""
        now = datetime.now(timezone.utc)
        gaps = []

        for evolution_id, evolution in self.idea_evolutions.items():
            latest_version = max(evolution.concept_versions, key=lambda x: x.timestamp)
            days_since_update = (now - latest_version.timestamp).days

            if days_since_update > days_threshold:
                gaps.append({
                    "evolution_id": evolution_id,
                    "core_idea": evolution.core_idea_id,
                    "days_since_update": days_since_update,
                    "latest_platform": latest_version.platform.value,
                    "latest_stage": latest_version.stage.value,
                    "concept_count": len(evolution.concept_versions)
                })

        return sorted(gaps, key=lambda x: x["days_since_update"], reverse=True)

    async def get_platform_transition_patterns(self) -> dict[str, dict[str, int]]:
        """Analyze patterns of how ideas move between platforms."""
        transitions = {}

        for evolution in self.idea_evolutions.values():
            platform_progression = evolution.get_platform_progression()

            for i in range(len(platform_progression) - 1):
                current_platform = platform_progression[i][0].value
                next_platform = platform_progression[i+1][0].value

                if current_platform not in transitions:
                    transitions[current_platform] = {}
                if next_platform not in transitions[current_platform]:
                    transitions[current_platform][next_platform] = 0

                transitions[current_platform][next_platform] += 1

        return transitions

    async def suggest_next_actions(self, evolution_id: str) -> list[dict[str, Any]]:
        """Suggest next actions for an idea evolution."""
        evolution = self.idea_evolutions.get(evolution_id)
        if not evolution:
            return []

        suggestions = []
        latest_version = max(evolution.concept_versions, key=lambda x: x.timestamp)

        # Suggest based on current stage
        if latest_version.stage == IdeaStage.CONCEPTION:
            suggestions.append({
                "action": "Create draft",
                "platform": "notion",
                "reason": "Move from conception to draft stage"
            })
        elif latest_version.stage == IdeaStage.DRAFT:
            suggestions.append({
                "action": "Refine and publish",
                "platform": "linkedin",
                "reason": "Share draft for feedback and engagement"
            })
        elif latest_version.stage == IdeaStage.PUBLICATION:
            suggestions.append({
                "action": "Engage with responses",
                "platform": "linkedin",
                "reason": "Build on published content with community interaction"
            })

        # Suggest cross-platform expansion
        platforms_used = set(v.platform for v in evolution.concept_versions)
        if ContentPlatform.NOTION in platforms_used and ContentPlatform.LINKEDIN not in platforms_used:
            suggestions.append({
                "action": "Share on LinkedIn",
                "platform": "linkedin",
                "reason": "Expand Notion concept to professional network"
            })

        return suggestions
