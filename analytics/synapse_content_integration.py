#!/usr/bin/env python3
"""
Synapse-Content Strategy Integration
Leverage existing Synapse RAG system for enhanced content intelligence
"""

import json
import logging
import sqlite3
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

# Add graph_rag to path for Synapse integration
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from graph_rag.config import get_settings
    from graph_rag.core.graph_rag_engine import GraphRAGEngine
    from graph_rag.infrastructure.graph_stores.memgraph_store import MemgraphGraphRepository
    from graph_rag.services.search import SearchService
    SYNAPSE_AVAILABLE = True
except ImportError:
    SYNAPSE_AVAILABLE = False
    logging.warning("Synapse components not available - running in standalone mode")

# Add business_development to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'business_development'))

from linkedin_posting_system import LinkedInBusinessDevelopmentEngine

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class SynapseContentIntelligence:
    """Integration between Synapse RAG system and content strategy"""

    def __init__(self):
        self.business_engine = LinkedInBusinessDevelopmentEngine()
        self.synapse_available = SYNAPSE_AVAILABLE
        self.db_path = "synapse_content_intelligence.db"

        if self.synapse_available:
            self._init_synapse_connection()

        self.init_database()

    def _init_synapse_connection(self):
        """Initialize connection to Synapse RAG system"""
        try:
            settings = get_settings()
            self.search_service = SearchService()

            # Initialize graph repository if Memgraph is available
            try:
                self.graph_repository = MemgraphGraphRepository()
                self.graph_available = True
                logger.info("Synapse graph repository initialized")
            except Exception:
                self.graph_available = False
                logger.warning("Memgraph not available - using vector search only")

            logger.info("Synapse content intelligence initialized")

        except Exception as e:
            logger.error(f"Failed to initialize Synapse connection: {e}")
            self.synapse_available = False

    def init_database(self):
        """Initialize content intelligence database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Content intelligence insights
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS content_insights (
                insight_id TEXT PRIMARY KEY,
                post_id TEXT,
                insight_type TEXT,
                insight_data TEXT,  -- JSON
                confidence_score REAL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Audience intelligence
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS audience_intelligence (
                analysis_id TEXT PRIMARY KEY,
                audience_segment TEXT,
                content_preferences TEXT,  -- JSON
                engagement_patterns TEXT,  -- JSON
                business_potential REAL,
                recommendations TEXT,  -- JSON
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Content recommendations
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS content_recommendations (
                recommendation_id TEXT PRIMARY KEY,
                recommendation_type TEXT,
                content_topic TEXT,
                target_audience TEXT,
                expected_performance TEXT,  -- JSON
                reasoning TEXT,
                priority_score REAL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        conn.commit()
        conn.close()
        logger.info("Content intelligence database initialized")

    def analyze_content_with_synapse(self, post_id: str, content: str) -> dict[str, Any]:
        """Use Synapse to analyze content and generate insights"""
        if not self.synapse_available:
            return self._fallback_content_analysis(content)

        try:
            # Search for similar content in knowledge base
            similar_content = self.search_service.search(
                query=content[:200],  # First 200 chars as query
                limit=5
            )

            # Analyze content themes and concepts
            insights = {
                'content_themes': self._extract_themes_from_search(similar_content),
                'similar_content_count': len(similar_content.chunks),
                'knowledge_base_relevance': self._calculate_relevance_score(similar_content),
                'content_gaps': self._identify_content_gaps(content, similar_content),
                'audience_alignment': self._analyze_audience_alignment(content)
            }

            # Save insights
            self._save_content_insight(post_id, 'synapse_analysis', insights)

            return insights

        except Exception as e:
            logger.error(f"Synapse analysis failed: {e}")
            return self._fallback_content_analysis(content)

    def _fallback_content_analysis(self, content: str) -> dict[str, Any]:
        """Fallback analysis when Synapse is not available"""
        return {
            'content_themes': ['general_technical'],
            'similar_content_count': 0,
            'knowledge_base_relevance': 0.5,
            'content_gaps': ['synapse_not_available'],
            'audience_alignment': 0.6,
            'fallback_mode': True
        }

    def _extract_themes_from_search(self, search_results) -> list[str]:
        """Extract themes from Synapse search results"""
        themes = []

        if hasattr(search_results, 'chunks'):
            for chunk in search_results.chunks:
                # Simple theme extraction based on chunk content
                content = chunk.text.lower()

                if any(term in content for term in ['team', 'leadership', 'culture']):
                    themes.append('team_building')
                elif any(term in content for term in ['architecture', 'system', 'design']):
                    themes.append('technical_architecture')
                elif any(term in content for term in ['startup', 'scaling', 'growth']):
                    themes.append('startup_scaling')
                elif any(term in content for term in ['performance', 'optimization']):
                    themes.append('performance_optimization')

        return list(set(themes)) if themes else ['general_technical']

    def _calculate_relevance_score(self, search_results) -> float:
        """Calculate how relevant the content is to existing knowledge base"""
        if not hasattr(search_results, 'chunks') or not search_results.chunks:
            return 0.0

        # Simple relevance scoring based on number and quality of matches
        num_chunks = len(search_results.chunks)
        avg_score = sum(chunk.score for chunk in search_results.chunks) / num_chunks

        # Normalize to 0-1 scale
        return min(avg_score / 100, 1.0)

    def _identify_content_gaps(self, content: str, search_results) -> list[str]:
        """Identify gaps in content coverage"""
        gaps = []

        # Analyze if content covers areas not well represented in knowledge base
        content_lower = content.lower()

        technical_topics = [
            'microservices', 'kubernetes', 'docker', 'devops', 'ci/cd',
            'database', 'redis', 'elasticsearch', 'monitoring', 'logging'
        ]

        business_topics = [
            'pricing', 'negotiation', 'contracts', 'client management',
            'project management', 'agile', 'scrum', 'remote work'
        ]

        # Check for technical gaps
        covered_technical = [topic for topic in technical_topics if topic in content_lower]
        if len(covered_technical) < 2:
            gaps.append('needs_more_technical_depth')

        # Check for business gaps
        covered_business = [topic for topic in business_topics if topic in content_lower]
        if len(covered_business) < 1:
            gaps.append('needs_more_business_context')

        return gaps if gaps else ['well_covered']

    def _analyze_audience_alignment(self, content: str) -> float:
        """Analyze how well content aligns with target audience"""
        content_lower = content.lower()

        # Score based on audience-relevant terms
        founder_terms = ['startup', 'founder', 'ceo', 'business', 'growth']
        cto_terms = ['cto', 'technical', 'architecture', 'team', 'leadership']
        developer_terms = ['code', 'development', 'programming', 'api', 'framework']

        founder_score = sum(1 for term in founder_terms if term in content_lower)
        cto_score = sum(1 for term in cto_terms if term in content_lower)
        developer_score = sum(1 for term in developer_terms if term in content_lower)

        # Balanced content scores higher
        total_score = founder_score + cto_score + developer_score
        balance_bonus = 1.0 if min(founder_score, cto_score) > 0 else 0.5

        return min((total_score / 10) * balance_bonus, 1.0)

    def generate_content_recommendations(self, business_goals: dict[str, Any]) -> list[dict]:
        """Generate content recommendations based on Synapse analysis"""
        recommendations = []

        if self.synapse_available:
            # Use Synapse to identify content opportunities
            try:
                # Search for gaps in content coverage
                technical_query = "technical architecture scaling performance"
                business_query = "startup founder business development consulting"

                tech_results = self.search_service.search(technical_query, limit=10)
                business_results = self.search_service.search(business_query, limit=10)

                # Identify underrepresented topics
                tech_gaps = self._identify_topic_gaps(tech_results)
                business_gaps = self._identify_topic_gaps(business_results)

                # Generate recommendations
                for gap in tech_gaps[:3]:  # Top 3 technical gaps
                    recommendations.append({
                        'type': 'content_gap',
                        'topic': gap,
                        'reasoning': f"Technical topic '{gap}' underrepresented in knowledge base",
                        'target_audience': 'technical_leaders',
                        'expected_engagement': 0.08,
                        'priority': 0.8
                    })

                for gap in business_gaps[:2]:  # Top 2 business gaps
                    recommendations.append({
                        'type': 'business_opportunity',
                        'topic': gap,
                        'reasoning': f"Business topic '{gap}' has consultation potential",
                        'target_audience': 'startup_founders',
                        'expected_engagement': 0.07,
                        'priority': 0.9
                    })

            except Exception as e:
                logger.error(f"Failed to generate Synapse-based recommendations: {e}")

        # Fallback recommendations based on business goals
        if not recommendations:
            recommendations = self._generate_fallback_recommendations(business_goals)

        # Save recommendations
        for rec in recommendations:
            self._save_content_recommendation(rec)

        return recommendations

    def _identify_topic_gaps(self, search_results) -> list[str]:
        """Identify underrepresented topics from search results"""
        if not hasattr(search_results, 'chunks') or not search_results.chunks:
            return ['general_topic_gap']

        # Simple gap identification - topics with low representation
        topic_counts = {}

        for chunk in search_results.chunks:
            content = chunk.text.lower()

            # Count topic occurrences
            topics = [
                'devops', 'security', 'database', 'api_design', 'testing',
                'monitoring', 'deployment', 'scaling', 'performance',
                'team_management', 'hiring', 'mentoring', 'consulting'
            ]

            for topic in topics:
                if topic.replace('_', ' ') in content or topic in content:
                    topic_counts[topic] = topic_counts.get(topic, 0) + 1

        # Return topics with low counts (gaps)
        total_chunks = len(search_results.chunks)
        gaps = [topic for topic, count in topic_counts.items()
                if count < total_chunks * 0.1]  # Less than 10% coverage

        return gaps[:5]  # Top 5 gaps

    def _generate_fallback_recommendations(self, business_goals: dict[str, Any]) -> list[dict]:
        """Generate fallback recommendations when Synapse is not available"""
        return [
            {
                'type': 'high_engagement_topic',
                'topic': 'controversial_technical_takes',
                'reasoning': 'Controversial content drives 40% higher engagement',
                'target_audience': 'technical_community',
                'expected_engagement': 0.10,
                'priority': 0.9
            },
            {
                'type': 'business_development',
                'topic': 'fractional_cto_case_studies',
                'reasoning': 'Case studies demonstrate expertise and drive consultations',
                'target_audience': 'startup_founders',
                'expected_engagement': 0.06,
                'priority': 0.95
            },
            {
                'type': 'community_building',
                'topic': 'technical_leadership_stories',
                'reasoning': 'Personal stories build authority and trust',
                'target_audience': 'aspiring_technical_leaders',
                'expected_engagement': 0.07,
                'priority': 0.7
            }
        ]

    def _save_content_insight(self, post_id: str, insight_type: str, insight_data: dict):
        """Save content insight to database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        insight_id = f"insight_{post_id}_{insight_type}_{datetime.now().strftime('%Y%m%d%H%M%S')}"

        cursor.execute('''
            INSERT INTO content_insights 
            (insight_id, post_id, insight_type, insight_data, confidence_score)
            VALUES (?, ?, ?, ?, ?)
        ''', (
            insight_id, post_id, insight_type,
            json.dumps(insight_data),
            insight_data.get('knowledge_base_relevance', 0.5)
        ))

        conn.commit()
        conn.close()

    def _save_content_recommendation(self, recommendation: dict):
        """Save content recommendation to database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        rec_id = f"rec_{recommendation['type']}_{datetime.now().strftime('%Y%m%d%H%M%S')}"

        cursor.execute('''
            INSERT INTO content_recommendations 
            (recommendation_id, recommendation_type, content_topic, target_audience,
             expected_performance, reasoning, priority_score)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            rec_id, recommendation['type'], recommendation['topic'],
            recommendation['target_audience'],
            json.dumps({'expected_engagement': recommendation['expected_engagement']}),
            recommendation['reasoning'], recommendation['priority']
        ))

        conn.commit()
        conn.close()

    def get_intelligence_dashboard(self) -> dict:
        """Get comprehensive intelligence dashboard"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Get recent insights
        cursor.execute('''
            SELECT insight_type, COUNT(*) as count, AVG(confidence_score) as avg_confidence
            FROM content_insights 
            WHERE created_at >= datetime('now', '-30 days')
            GROUP BY insight_type
        ''')
        insights_summary = cursor.fetchall()

        # Get recommendations by priority
        cursor.execute('''
            SELECT recommendation_type, content_topic, target_audience, priority_score, reasoning
            FROM content_recommendations 
            ORDER BY priority_score DESC, created_at DESC
            LIMIT 10
        ''')
        top_recommendations = cursor.fetchall()

        conn.close()

        return {
            'synapse_available': self.synapse_available,
            'insights_summary': [
                {
                    'type': row[0],
                    'count': row[1],
                    'avg_confidence': row[2]
                } for row in insights_summary
            ],
            'top_recommendations': [
                {
                    'type': row[0],
                    'topic': row[1],
                    'audience': row[2],
                    'priority': row[3],
                    'reasoning': row[4]
                } for row in top_recommendations
            ]
        }

def main():
    """Demonstrate Synapse-Content integration"""
    intelligence = SynapseContentIntelligence()

    print("🧠 SYNAPSE-CONTENT INTELLIGENCE INTEGRATION")
    print("=" * 60)
    print(f"Synapse Available: {intelligence.synapse_available}")

    # Generate content recommendations
    business_goals = {
        'target_consultations': 10,
        'focus_areas': ['technical_architecture', 'team_building'],
        'audience_priorities': ['startup_founders', 'technical_leaders']
    }

    print("\nGenerating content recommendations...")
    recommendations = intelligence.generate_content_recommendations(business_goals)

    print(f"\n📝 CONTENT RECOMMENDATIONS ({len(recommendations)}):")
    for i, rec in enumerate(recommendations, 1):
        print(f"{i}. {rec['topic'].replace('_', ' ').title()}")
        print(f"   Type: {rec['type']}")
        print(f"   Audience: {rec['target_audience']}")
        print(f"   Priority: {rec['priority']:.1f}")
        print(f"   Expected Engagement: {rec['expected_engagement']*100:.1f}%")
        print(f"   Reasoning: {rec['reasoning']}")
        print()

    # Test content analysis
    sample_content = "Building scalable microservices architecture for startup teams"
    print("Testing content analysis...")
    insights = intelligence.analyze_content_with_synapse("test_post", sample_content)

    print("\n🔍 CONTENT ANALYSIS RESULTS:")
    for key, value in insights.items():
        print(f"• {key}: {value}")

    # Show intelligence dashboard
    dashboard = intelligence.get_intelligence_dashboard()
    print("\n📊 INTELLIGENCE DASHBOARD:")
    print(f"• Synapse Integration: {'✅ Active' if dashboard['synapse_available'] else '❌ Fallback Mode'}")
    print(f"• Recent Insights: {len(dashboard['insights_summary'])}")
    print(f"• Active Recommendations: {len(dashboard['top_recommendations'])}")

    print("\n✅ Synapse-Content Integration Ready!")
    print(f"Database: {intelligence.db_path}")

if __name__ == "__main__":
    main()
