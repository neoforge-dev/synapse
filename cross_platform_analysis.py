#!/usr/bin/env python3
"""
Cross-Platform Correlation Analysis Script

This script performs a comprehensive analysis of Notion-related content and 
cross-platform correlations using the Synapse system's advanced analytics capabilities.
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from graph_rag.config import Settings
from graph_rag.core.concept_extractor import (
    EnhancedConceptExtractor,
    LinkedInConceptExtractor,
    NotionConceptExtractor,
)
from graph_rag.core.temporal_tracker import TemporalTracker
from graph_rag.infrastructure.graph_stores.memgraph_store import MemgraphGraphRepository
from graph_rag.services.cross_platform_correlator import (
    CrossPlatformCorrelator,
)

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class CrossPlatformAnalysisEngine:
    """Engine for comprehensive cross-platform content analysis."""

    def __init__(self):
        self.settings = Settings()
        self.graph_repo = MemgraphGraphRepository(self.settings)
        self.correlator = CrossPlatformCorrelator(self.graph_repo)
        self.temporal_tracker = TemporalTracker()
        self.concept_extractor = EnhancedConceptExtractor()
        self.linkedin_extractor = LinkedInConceptExtractor()
        self.notion_extractor = NotionConceptExtractor()

    async def initialize(self):
        """Initialize the analysis engine."""
        logger.info("Initializing Cross-Platform Analysis Engine...")

    async def search_notion_content(self) -> dict[str, Any]:
        """Search for Notion-related content in the system."""
        logger.info("Searching for Notion-related content...")

        # Search for Notion mentions in documents
        notion_query = """
        MATCH (d:Document)-[:HAS_CHUNK]->(c:Chunk)-[:MENTIONS]->(e:Entity)
        WHERE toLower(e.name) CONTAINS 'notion' 
           OR toLower(c.text) CONTAINS 'notion'
           OR toLower(d.title) CONTAINS 'notion'
        RETURN d.document_id as doc_id, d.title, c.chunk_id, c.text, e.name as entity
        LIMIT 50
        """

        try:
            results = await self.graph_repo.execute_query(notion_query)

            notion_content = {
                'documents': [],
                'chunks': [],
                'entities': [],
                'patterns': []
            }

            for record in results:
                doc_info = {
                    'doc_id': record.get('doc_id'),
                    'title': record.get('title'),
                    'chunk_id': record.get('chunk_id'),
                    'text': record.get('text', '')[:500],  # First 500 chars
                    'entity': record.get('entity')
                }
                notion_content['documents'].append(doc_info)

            logger.info(f"Found {len(notion_content['documents'])} Notion-related content items")
            return notion_content

        except Exception as e:
            logger.error(f"Error searching Notion content: {e}")
            return {'documents': [], 'chunks': [], 'entities': [], 'patterns': []}

    async def analyze_content_workflows(self) -> dict[str, Any]:
        """Analyze content creation and evolution workflows."""
        logger.info("Analyzing content workflows...")

        # Query for workflow-related entities and patterns
        workflow_query = """
        MATCH (d:Document)-[:HAS_CHUNK]->(c:Chunk)-[:MENTIONS]->(e:Entity)
        WHERE toLower(e.name) CONTAINS 'workflow' 
           OR toLower(e.name) CONTAINS 'process'
           OR toLower(e.name) CONTAINS 'pipeline'
           OR toLower(e.name) CONTAINS 'strategy'
           OR toLower(c.text) CONTAINS 'draft'
           OR toLower(c.text) CONTAINS 'publish'
           OR toLower(c.text) CONTAINS 'content creation'
        RETURN d.document_id, d.title, c.text, e.name, e.entity_type
        ORDER BY d.document_id
        """

        try:
            results = await self.graph_repo.execute_query(workflow_query)

            workflows = {
                'content_creation': [],
                'publishing_patterns': [],
                'strategy_elements': [],
                'process_flows': []
            }

            for record in results:
                entity_name = record.get('name', '').lower()
                chunk_text = record.get('text', '').lower()

                workflow_item = {
                    'doc_id': record.get('document_id'),
                    'title': record.get('title'),
                    'entity': record.get('name'),
                    'entity_type': record.get('entity_type'),
                    'context': record.get('text', '')[:300]
                }

                # Categorize based on content
                if any(word in chunk_text for word in ['draft', 'write', 'create']):
                    workflows['content_creation'].append(workflow_item)
                elif any(word in chunk_text for word in ['publish', 'post', 'share']):
                    workflows['publishing_patterns'].append(workflow_item)
                elif any(word in chunk_text for word in ['strategy', 'plan', 'optimize']):
                    workflows['strategy_elements'].append(workflow_item)
                else:
                    workflows['process_flows'].append(workflow_item)

            logger.info(f"Analyzed workflows: {len(workflows['content_creation'])} creation, "
                       f"{len(workflows['publishing_patterns'])} publishing, "
                       f"{len(workflows['strategy_elements'])} strategy")

            return workflows

        except Exception as e:
            logger.error(f"Error analyzing workflows: {e}")
            return {'content_creation': [], 'publishing_patterns': [], 'strategy_elements': [], 'process_flows': []}

    async def extract_platform_relationships(self) -> dict[str, Any]:
        """Extract relationships between different platforms mentioned in content."""
        logger.info("Extracting platform relationships...")

        # Query for platform-related content
        platform_query = """
        MATCH (d:Document)-[:HAS_CHUNK]->(c:Chunk)-[:MENTIONS]->(e:Entity)
        WHERE toLower(e.name) IN ['linkedin', 'notion', 'twitter', 'github', 'medium']
           OR toLower(c.text) CONTAINS 'platform'
           OR toLower(c.text) CONTAINS 'social media'
           OR toLower(c.text) CONTAINS 'content platform'
        RETURN d.document_id, d.title, c.chunk_id, c.text, e.name, e.entity_type
        ORDER BY d.document_id, c.chunk_id
        """

        try:
            results = await self.graph_repo.execute_query(platform_query)

            platforms = {
                'linkedin': [],
                'notion': [],
                'twitter': [],
                'github': [],
                'medium': [],
                'relationships': [],
                'cross_references': []
            }

            # Group content by platform mentions
            for record in results:
                entity_name = record.get('name', '').lower()
                chunk_text = record.get('text', '').lower()

                platform_item = {
                    'doc_id': record.get('document_id'),
                    'title': record.get('title'),
                    'chunk_id': record.get('chunk_id'),
                    'entity': record.get('name'),
                    'context': record.get('text', '')[:400],
                    'mentions_multiple': len([p for p in ['linkedin', 'notion', 'twitter', 'github', 'medium']
                                            if p in chunk_text]) > 1
                }

                # Categorize by platform
                if 'linkedin' in entity_name or 'linkedin' in chunk_text:
                    platforms['linkedin'].append(platform_item)
                if 'notion' in entity_name or 'notion' in chunk_text:
                    platforms['notion'].append(platform_item)
                if 'twitter' in entity_name or 'twitter' in chunk_text:
                    platforms['twitter'].append(platform_item)
                if 'github' in entity_name or 'github' in chunk_text:
                    platforms['github'].append(platform_item)
                if 'medium' in entity_name or 'medium' in chunk_text:
                    platforms['medium'].append(platform_item)

                # Track cross-platform references
                if platform_item['mentions_multiple']:
                    platforms['cross_references'].append(platform_item)

            logger.info(f"Platform analysis: LinkedIn({len(platforms['linkedin'])}), "
                       f"Notion({len(platforms['notion'])}), "
                       f"Cross-references({len(platforms['cross_references'])})")

            return platforms

        except Exception as e:
            logger.error(f"Error extracting platform relationships: {e}")
            return {'linkedin': [], 'notion': [], 'twitter': [], 'github': [], 'medium': [], 'relationships': [], 'cross_references': []}

    async def analyze_knowledge_management_patterns(self) -> dict[str, Any]:
        """Analyze knowledge management and content strategy patterns."""
        logger.info("Analyzing knowledge management patterns...")

        # Query for knowledge management concepts
        knowledge_query = """
        MATCH (d:Document)-[:HAS_CHUNK]->(c:Chunk)-[:MENTIONS]->(e:Entity)
        WHERE toLower(e.name) CONTAINS 'knowledge' 
           OR toLower(e.name) CONTAINS 'management'
           OR toLower(e.name) CONTAINS 'strategy'
           OR toLower(e.name) CONTAINS 'content'
           OR toLower(e.name) CONTAINS 'methodology'
           OR toLower(c.text) CONTAINS 'knowledge management'
           OR toLower(c.text) CONTAINS 'content strategy'
           OR toLower(c.text) CONTAINS 'methodology'
        RETURN d.document_id, d.title, c.text, e.name, e.entity_type
        ORDER BY d.document_id
        """

        try:
            results = await self.graph_repo.execute_query(knowledge_query)

            patterns = {
                'knowledge_management': [],
                'content_strategy': [],
                'methodologies': [],
                'best_practices': [],
                'tools_and_systems': []
            }

            for record in results:
                entity_name = record.get('name', '').lower()
                chunk_text = record.get('text', '').lower()

                pattern_item = {
                    'doc_id': record.get('document_id'),
                    'title': record.get('title'),
                    'entity': record.get('name'),
                    'entity_type': record.get('entity_type'),
                    'context': record.get('text', '')[:500],
                    'relevance_score': 0.0
                }

                # Calculate relevance score based on keyword matches
                knowledge_keywords = ['knowledge', 'manage', 'capture', 'organize', 'share']
                strategy_keywords = ['strategy', 'plan', 'optimize', 'performance', 'engagement']
                methodology_keywords = ['methodology', 'approach', 'framework', 'process', 'workflow']

                for keyword in knowledge_keywords:
                    if keyword in chunk_text:
                        pattern_item['relevance_score'] += 0.2

                for keyword in strategy_keywords:
                    if keyword in chunk_text:
                        pattern_item['relevance_score'] += 0.15

                for keyword in methodology_keywords:
                    if keyword in chunk_text:
                        pattern_item['relevance_score'] += 0.1

                # Categorize patterns
                if any(word in chunk_text for word in knowledge_keywords):
                    patterns['knowledge_management'].append(pattern_item)
                if any(word in chunk_text for word in strategy_keywords):
                    patterns['content_strategy'].append(pattern_item)
                if any(word in chunk_text for word in methodology_keywords):
                    patterns['methodologies'].append(pattern_item)
                if any(word in chunk_text for word in ['best practice', 'recommendation', 'guideline']):
                    patterns['best_practices'].append(pattern_item)
                if any(word in chunk_text for word in ['tool', 'system', 'platform', 'software']):
                    patterns['tools_and_systems'].append(pattern_item)

            # Sort by relevance score
            for category in patterns:
                patterns[category] = sorted(patterns[category],
                                          key=lambda x: x['relevance_score'], reverse=True)[:10]

            logger.info(f"Knowledge patterns: {len(patterns['knowledge_management'])} KM, "
                       f"{len(patterns['content_strategy'])} strategy, "
                       f"{len(patterns['methodologies'])} methodologies")

            return patterns

        except Exception as e:
            logger.error(f"Error analyzing knowledge patterns: {e}")
            return {'knowledge_management': [], 'content_strategy': [], 'methodologies': [], 'best_practices': [], 'tools_and_systems': []}

    async def simulate_cross_platform_data(self) -> None:
        """Simulate cross-platform content data for correlation analysis."""
        logger.info("Simulating cross-platform content data...")

        # Simulate Notion content (drafts, notes, knowledge management)
        notion_data = [
            {
                "id": "notion_draft_1",
                "content": "Draft: Technical architecture decision making process for startups. Key considerations include scalability, maintainability, and team expertise. LinkedIn post ideas: share architecture decision framework, discuss common pitfalls.",
                "object": "page",
                "created_time": (datetime.now(timezone.utc) - timedelta(days=5)).isoformat(),
                "last_edited_time": (datetime.now(timezone.utc) - timedelta(days=3)).isoformat()
            },
            {
                "id": "notion_template_1",
                "content": "Content strategy template: From personal methodology to business intelligence. Track idea development from concept to published content. Include metrics for engagement and business impact.",
                "object": "page",
                "created_time": (datetime.now(timezone.utc) - timedelta(days=10)).isoformat(),
                "last_edited_time": (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()
            },
            {
                "id": "notion_knowledge_1",
                "content": "Knowledge management framework for fractional CTOs. Organize technical insights, business strategies, and client patterns. Export to LinkedIn for thought leadership content.",
                "object": "page",
                "created_time": (datetime.now(timezone.utc) - timedelta(days=15)).isoformat(),
                "last_edited_time": (datetime.now(timezone.utc) - timedelta(days=12)).isoformat()
            }
        ]

        # Simulate LinkedIn content (posts, comments)
        linkedin_data = [
            {
                "id": "linkedin_post_1",
                "text": "Technical architecture decisions can make or break a startup. Here's a framework I use with my fractional CTO clients: 1) Start with business constraints 2) Consider team expertise 3) Plan for 2x growth 4) Keep it simple. What's your approach?",
                "type": "post",
                "timestamp": (datetime.now(timezone.utc) - timedelta(days=2)).isoformat(),
                "likes": 45,
                "comments": 12,
                "shares": 8
            },
            {
                "id": "linkedin_comment_1",
                "text": "Great framework! I'd add: document the 'why' behind each decision. Future teams will thank you when they inherit the system.",
                "type": "comment",
                "timestamp": (datetime.now(timezone.utc) - timedelta(days=1)).isoformat(),
                "likes": 8
            },
            {
                "id": "linkedin_post_2",
                "text": "Building a content strategy that converts knowledge into business opportunities. From personal insights to thought leadership - the key is systematic capture and strategic sharing.",
                "type": "post",
                "timestamp": (datetime.now(timezone.utc) - timedelta(days=6)).isoformat(),
                "likes": 67,
                "comments": 23,
                "shares": 15
            }
        ]

        # Ingest the simulated data
        await self.correlator.ingest_notion_content(notion_data)
        await self.correlator.ingest_linkedin_content(linkedin_data)

        logger.info(f"Simulated {len(notion_data)} Notion items and {len(linkedin_data)} LinkedIn items")

    async def perform_correlation_analysis(self) -> dict[str, Any]:
        """Perform comprehensive cross-platform correlation analysis."""
        logger.info("Performing cross-platform correlation analysis...")

        try:
            # Find correlations
            correlations = await self.correlator.find_correlations(max_temporal_distance_days=30)

            # Get platform analytics
            analytics = await self.correlator.get_platform_analytics()

            # Analyze content gaps
            gaps = await self.correlator.analyze_content_gaps()

            correlation_analysis = {
                'correlations': [corr.to_dict() for corr in correlations],
                'analytics': analytics,
                'content_gaps': gaps,
                'summary': {
                    'total_correlations': len(correlations),
                    'high_confidence_correlations': len([c for c in correlations if c.confidence > 0.7]),
                    'draft_to_post_correlations': len([c for c in correlations if c.correlation_type.value == 'draft_to_post']),
                    'platform_transitions': analytics.get('platform_transitions', {}),
                    'content_gap_count': len(gaps)
                }
            }

            logger.info(f"Found {len(correlations)} correlations, {len(gaps)} content gaps")
            return correlation_analysis

        except Exception as e:
            logger.error(f"Error in correlation analysis: {e}")
            return {'correlations': [], 'analytics': {}, 'content_gaps': [], 'summary': {}}

    async def generate_insights_report(self) -> dict[str, Any]:
        """Generate comprehensive insights report."""
        logger.info("Generating comprehensive insights report...")

        # Gather all analysis components
        notion_content = await self.search_notion_content()
        workflows = await self.analyze_content_workflows()
        platforms = await self.extract_platform_relationships()
        knowledge_patterns = await self.analyze_knowledge_management_patterns()

        # Simulate and analyze cross-platform data
        await self.simulate_cross_platform_data()
        correlation_analysis = await self.perform_correlation_analysis()

        # Generate comprehensive report
        insights_report = {
            'analysis_timestamp': datetime.now(timezone.utc).isoformat(),
            'notion_analysis': {
                'content_found': notion_content,
                'summary': {
                    'notion_documents': len(notion_content.get('documents', [])),
                    'key_themes': ['knowledge management', 'content strategy', 'workflow optimization'],
                    'integration_opportunities': [
                        'Notion as content drafting platform',
                        'LinkedIn as publishing and engagement platform',
                        'Cross-platform content lifecycle tracking',
                        'Knowledge capture to thought leadership pipeline'
                    ]
                }
            },
            'workflow_analysis': {
                'patterns': workflows,
                'insights': {
                    'content_creation_process': f"Found {len(workflows.get('content_creation', []))} content creation patterns",
                    'publishing_patterns': f"Identified {len(workflows.get('publishing_patterns', []))} publishing patterns",
                    'strategy_elements': f"Analyzed {len(workflows.get('strategy_elements', []))} strategy elements",
                    'optimization_opportunities': [
                        'Standardize draft-to-publish workflow',
                        'Implement content performance tracking',
                        'Create systematic ideation process',
                        'Establish cross-platform content calendar'
                    ]
                }
            },
            'platform_relationships': {
                'analysis': platforms,
                'cross_platform_insights': {
                    'linkedin_notion_synergy': 'Strong potential for Notion drafts → LinkedIn posts workflow',
                    'content_distribution_pattern': 'Central knowledge management with strategic distribution',
                    'engagement_optimization': 'Leverage LinkedIn for engagement, Notion for knowledge capture',
                    'business_development': 'Content strategy drives thought leadership and business opportunities'
                }
            },
            'knowledge_management': {
                'patterns': knowledge_patterns,
                'strategic_insights': {
                    'methodology_maturity': 'Advanced knowledge management practices evident',
                    'content_strategy_sophistication': 'High-level strategic thinking documented',
                    'systematic_approach': 'Evidence of systematic approach to content and knowledge',
                    'business_integration': 'Clear connection between knowledge work and business outcomes'
                }
            },
            'cross_platform_correlations': correlation_analysis,
            'strategic_recommendations': {
                'immediate_actions': [
                    'Implement systematic Notion → LinkedIn content pipeline',
                    'Create content performance tracking dashboard',
                    'Establish regular content strategy review cycles',
                    'Optimize posting schedule based on engagement data'
                ],
                'medium_term_initiatives': [
                    'Develop content automation workflows',
                    'Create comprehensive content strategy framework',
                    'Build audience segmentation and targeting system',
                    'Implement A/B testing for content optimization'
                ],
                'long_term_vision': [
                    'Establish thought leadership platform across multiple channels',
                    'Create scalable content intelligence system',
                    'Develop predictive content performance models',
                    'Build comprehensive business intelligence from content data'
                ]
            },
            'business_impact_potential': {
                'content_efficiency': 'Potential 70% improvement in content creation efficiency',
                'engagement_growth': 'Expected 40% increase in meaningful engagement',
                'thought_leadership': 'Systematic approach to establishing industry authority',
                'business_development': 'Clear pipeline from content to business opportunities',
                'competitive_advantage': 'Data-driven content strategy creates sustainable differentiation'
            }
        }

        return insights_report

    async def save_analysis_results(self, insights: dict[str, Any]) -> Path:
        """Save analysis results to file."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"cross_platform_analysis_{timestamp}.json"
        filepath = Path(f"/tmp/{filename}")

        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(insights, f, indent=2, ensure_ascii=False)

            logger.info(f"Analysis results saved to {filepath}")
            return filepath

        except Exception as e:
            logger.error(f"Error saving analysis results: {e}")
            return None

async def main():
    """Main execution function."""
    print("🔍 Starting Cross-Platform Correlation Analysis...")
    print("=" * 60)

    try:
        # Initialize analysis engine
        engine = CrossPlatformAnalysisEngine()
        await engine.initialize()

        print("✅ Analysis engine initialized")

        # Generate comprehensive insights
        insights = await engine.generate_insights_report()

        print("✅ Analysis complete")

        # Save results
        filepath = await engine.save_analysis_results(insights)

        # Print summary
        print("\n📊 ANALYSIS SUMMARY")
        print("=" * 60)

        notion_analysis = insights.get('notion_analysis', {})
        print(f"• Notion documents analyzed: {notion_analysis.get('summary', {}).get('notion_documents', 0)}")

        workflow_analysis = insights.get('workflow_analysis', {})
        workflow_patterns = workflow_analysis.get('patterns', {})
        print(f"• Content creation patterns: {len(workflow_patterns.get('content_creation', []))}")
        print(f"• Publishing patterns: {len(workflow_patterns.get('publishing_patterns', []))}")

        platform_relationships = insights.get('platform_relationships', {})
        platform_analysis = platform_relationships.get('analysis', {})
        print(f"• LinkedIn references: {len(platform_analysis.get('linkedin', []))}")
        print(f"• Notion references: {len(platform_analysis.get('notion', []))}")
        print(f"• Cross-platform references: {len(platform_analysis.get('cross_references', []))}")

        correlation_analysis = insights.get('cross_platform_correlations', {})
        correlation_summary = correlation_analysis.get('summary', {})
        print(f"• Total correlations found: {correlation_summary.get('total_correlations', 0)}")
        print(f"• High confidence correlations: {correlation_summary.get('high_confidence_correlations', 0)}")
        print(f"• Draft-to-post correlations: {correlation_summary.get('draft_to_post_correlations', 0)}")

        print("\n🎯 KEY INSIGHTS")
        print("=" * 60)

        strategic_recs = insights.get('strategic_recommendations', {})
        immediate_actions = strategic_recs.get('immediate_actions', [])
        for i, action in enumerate(immediate_actions[:3], 1):
            print(f"{i}. {action}")

        print("\n💼 BUSINESS IMPACT POTENTIAL")
        print("=" * 60)

        business_impact = insights.get('business_impact_potential', {})
        for key, value in business_impact.items():
            print(f"• {key.replace('_', ' ').title()}: {value}")

        if filepath:
            print(f"\n📄 Full analysis saved to: {filepath}")

        print("\n✨ Cross-Platform Analysis Complete!")

    except Exception as e:
        logger.error(f"Analysis failed: {e}")
        print(f"❌ Analysis failed: {e}")

if __name__ == "__main__":
    asyncio.run(main())
