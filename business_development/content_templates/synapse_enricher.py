"""
Synapse Content Enricher
Integrates with Synapse Graph-RAG system to enrich content with insights
"""

import json
import logging
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

# Add project root to path for imports
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

try:
    from graph_rag.infrastructure.graph_stores.memgraph_store import MemgraphGraphRepository
    from graph_rag.infrastructure.vector_stores.simple_vector_store import SimpleVectorStore
    from graph_rag.services.embedding_service import EmbeddingService
    from graph_rag.services.search import SearchResult, SearchService
except ImportError as e:
    logging.warning(f"Could not import Synapse components: {e}")
    SearchResult = None
    SearchService = None
    SimpleVectorStore = None
    MemgraphGraphRepository = None
    EmbeddingService = None

logger = logging.getLogger(__name__)

@dataclass
class EnrichedContent:
    """Enriched content with Synapse insights"""
    original_query: str
    relevant_beliefs: list[str]
    personal_stories: list[str]
    technical_insights: list[str]
    engagement_patterns: list[str]
    synapse_search_results: list[dict]
    confidence_score: float

class SynapseContentEnricher:
    """Enriches content using Synapse Graph-RAG system"""

    def __init__(self):
        self.linkedin_data_path = Path(project_root) / "data" / "linkedin_processed"
        self.search_service = self._initialize_search_service()

        # Load processed LinkedIn insights
        self.linkedin_insights = self._load_linkedin_insights()

    def _initialize_search_service(self) -> Any | None:
        """Initialize Synapse search service if available"""
        try:
            # Check if classes are available
            if not all([SimpleVectorStore, MemgraphGraphRepository, EmbeddingService, SearchService]):
                logger.warning("Synapse components not available, will use CLI fallback")
                return None

            # Try to initialize search service components
            vector_store = SimpleVectorStore()
            graph_store = MemgraphGraphRepository()
            embedding_service = EmbeddingService()

            return SearchService(
                vector_store=vector_store,
                graph_store=graph_store,
                embedding_service=embedding_service
            )
        except Exception as e:
            logger.warning(f"Could not initialize Synapse search service: {e}")
            return None

    def _load_linkedin_insights(self) -> dict:
        """Load processed LinkedIn insights data"""
        insights = {
            'beliefs': [],
            'stories': [],
            'high_performing_ideas': [],
            'engagement_patterns': []
        }

        try:
            # Load extracted content
            content_file = self.linkedin_data_path / "linkedin_complete_extracted_content.json"
            if content_file.exists():
                with open(content_file) as f:
                    content_data = json.load(f)

                for post in content_data:
                    extracted = post.get('extracted_content', {})

                    # Collect beliefs
                    insights['beliefs'].extend(extracted.get('beliefs', []))

                    # Collect personal stories
                    stories = extracted.get('personal_stories', [])
                    for story in stories:
                        if isinstance(story, dict):
                            insights['stories'].append(story.get('story_snippet', ''))
                        else:
                            insights['stories'].append(str(story))

                    # Collect high-performing ideas
                    insights['high_performing_ideas'].extend(extracted.get('ideas', []))

            # Load performance analysis
            performance_file = self.linkedin_data_path / "linkedin_performance_analysis.json"
            if performance_file.exists():
                with open(performance_file) as f:
                    performance_data = json.load(f)

                insights['high_performing_ideas'].extend(
                    performance_data.get('top_performing_ideas', [])
                )

                stories = performance_data.get('top_performing_stories', [])
                for story in stories:
                    if isinstance(story, dict):
                        insights['stories'].append(story.get('story_snippet', ''))

        except Exception as e:
            logger.error(f"Error loading LinkedIn insights: {e}")

        return insights

    def enrich_content(self, topic: str, content_type: str, keywords: list[str]) -> EnrichedContent:
        """Enrich content with Synapse search and LinkedIn insights"""

        # Search Synapse system for relevant content
        synapse_results = self._search_synapse(topic, keywords)

        # Find relevant LinkedIn insights
        relevant_beliefs = self._find_relevant_beliefs(topic, keywords)
        relevant_stories = self._find_relevant_stories(topic, keywords)
        relevant_ideas = self._find_relevant_ideas(topic, keywords)

        # Calculate confidence score based on available data
        confidence_score = self._calculate_confidence_score(
            synapse_results, relevant_beliefs, relevant_stories, relevant_ideas
        )

        return EnrichedContent(
            original_query=topic,
            relevant_beliefs=relevant_beliefs,
            personal_stories=relevant_stories,
            technical_insights=relevant_ideas,
            engagement_patterns=self._get_engagement_patterns(content_type),
            synapse_search_results=synapse_results,
            confidence_score=confidence_score
        )

    def _search_synapse(self, query: str, keywords: list[str]) -> list[dict]:
        """Search Synapse system for relevant content"""
        results = []

        if self.search_service:
            try:
                # Use Synapse search service directly
                search_query = f"{query} {' '.join(keywords)}"
                search_results = self.search_service.search(search_query, limit=5)

                for result in search_results:
                    results.append({
                        'content': result.content,
                        'score': result.score,
                        'source': result.metadata.get('source', 'synapse'),
                        'type': 'direct_search'
                    })

            except Exception as e:
                logger.warning(f"Direct Synapse search failed: {e}")

        # Fallback to CLI search if direct search fails
        if not results:
            results = self._search_synapse_cli(query, keywords)

        return results

    def _search_synapse_cli(self, query: str, keywords: list[str]) -> list[dict]:
        """Fallback: Use Synapse CLI for search"""
        results = []

        try:
            # Use the synapse CLI command
            search_query = f"{query} {' '.join(keywords)}"
            cmd = ['uv', 'run', 'synapse', 'search', search_query, '--limit', '5']

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                cwd=project_root,
                timeout=30
            )

            if result.returncode == 0:
                # Parse CLI output (this would need to be adapted based on actual CLI output format)
                lines = result.stdout.strip().split('\n')
                for line in lines:
                    if line.strip() and not line.startswith('['):
                        results.append({
                            'content': line,
                            'score': 0.5,  # Default score for CLI results
                            'source': 'synapse_cli',
                            'type': 'cli_search'
                        })

        except Exception as e:
            logger.warning(f"Synapse CLI search failed: {e}")

        return results

    def _find_relevant_beliefs(self, topic: str, keywords: list[str]) -> list[str]:
        """Find relevant beliefs from LinkedIn data"""
        relevant = []

        # Simple keyword matching for now - could be enhanced with embeddings
        f"{topic} {' '.join(keywords)}".lower()

        for belief in self.linkedin_insights['beliefs']:
            if belief and any(keyword.lower() in belief.lower() for keyword in keywords):
                relevant.append(belief)

        return relevant[:3]  # Limit to top 3 most relevant

    def _find_relevant_stories(self, topic: str, keywords: list[str]) -> list[str]:
        """Find relevant personal stories from LinkedIn data"""
        relevant = []

        f"{topic} {' '.join(keywords)}".lower()

        for story in self.linkedin_insights['stories']:
            if story and any(keyword.lower() in story.lower() for keyword in keywords):
                relevant.append(story)

        return relevant[:2]  # Limit to top 2 most relevant stories

    def _find_relevant_ideas(self, topic: str, keywords: list[str]) -> list[str]:
        """Find relevant high-performing ideas from LinkedIn data"""
        relevant = []

        for idea in self.linkedin_insights['high_performing_ideas']:
            if idea and any(keyword.lower() in idea.lower() for keyword in keywords):
                relevant.append(idea)

        return relevant[:5]  # Limit to top 5 relevant ideas

    def _get_engagement_patterns(self, content_type: str) -> list[str]:
        """Get engagement patterns for content type"""
        patterns = {
            'controversial_take': [
                "Strong opinions drive 25% higher engagement",
                "Questions at the end increase comments by 40%",
                "Personal experience adds credibility"
            ],
            'personal_story': [
                "Vulnerability increases relatability",
                "Specific details make stories memorable",
                "Time-based hooks perform well"
            ],
            'technical_insight': [
                "Code examples drive technical engagement",
                "Problem-solution format works best",
                "Practical applications get shared more"
            ],
            'career_advice': [
                "Numbered lists increase readability",
                "Personal results add credibility",
                "Actionable advice gets saved"
            ],
            'product_management': [
                "Problem identification hooks work well",
                "Framework-based content performs better",
                "Consultation hooks drive business inquiries"
            ]
        }

        return patterns.get(content_type, [])

    def _calculate_confidence_score(self, synapse_results: list[dict],
                                  beliefs: list[str], stories: list[str],
                                  ideas: list[str]) -> float:
        """Calculate confidence score for enriched content"""

        score = 0.0

        # Base score for available data
        if synapse_results:
            score += 0.3
        if beliefs:
            score += 0.2
        if stories:
            score += 0.25
        if ideas:
            score += 0.25

        # Bonus for multiple sources
        sources_count = sum([
            1 if synapse_results else 0,
            1 if beliefs else 0,
            1 if stories else 0,
            1 if ideas else 0
        ])

        if sources_count >= 3:
            score += 0.1

        return min(score, 1.0)  # Cap at 1.0

    def get_content_suggestions(self, enriched_content: EnrichedContent) -> dict[str, list[str]]:
        """Generate content suggestions based on enriched data"""

        suggestions = {
            'hooks': [],
            'supporting_points': [],
            'personal_examples': [],
            'call_to_actions': []
        }

        # Generate hooks from stories
        for story in enriched_content.personal_stories:
            if story:
                # Extract potential hook patterns
                if "years ago" in story.lower():
                    suggestions['hooks'].append(f"Hook: Reference timing from story - '{story[:50]}...'")
                elif "found myself" in story.lower():
                    suggestions['hooks'].append(f"Hook: Use discovery moment - '{story[:50]}...'")

        # Generate supporting points from technical insights
        for insight in enriched_content.technical_insights:
            if insight and len(insight) > 20:
                suggestions['supporting_points'].append(f"• {insight}")

        # Generate examples from beliefs
        for belief in enriched_content.relevant_beliefs:
            if belief:
                suggestions['personal_examples'].append(f"Example: {belief}")

        # Generate CTAs based on engagement patterns
        for pattern in enriched_content.engagement_patterns:
            if "questions" in pattern.lower():
                suggestions['call_to_actions'].append("End with an engaging question")
            elif "comments" in pattern.lower():
                suggestions['call_to_actions'].append("Encourage discussion in comments")

        return suggestions
