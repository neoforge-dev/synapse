"""Technical knowledge base for content generation."""

import logging
import random
from typing import Dict, List, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class TechnicalContext:
    """Context for technical leadership topics."""
    professional_role: str
    key_insight: str
    common_mistake: str
    contrarian_truth: str
    context: str
    example: str
    framework: List[str]
    situation: str
    outcome: str


class TechnicalKnowledgeBase:
    """
    Knowledge base containing proven technical leadership insights.
    
    Based on successful content that generated €290K in consultation pipeline.
    """
    
    def __init__(self):
        self.knowledge_database = self._build_knowledge_database()
        
    def get_context_for_topic(self, topic: str) -> Dict:
        """Get relevant context for a technical topic."""
        # Find best matching context
        topic_lower = topic.lower()
        
        # Direct topic matches
        for key, context in self.knowledge_database.items():
            if key in topic_lower or any(keyword in topic_lower for keyword in key.split('_')):
                return self._context_to_dict(context)
        
        # Default to general technical leadership context
        general_context = self.knowledge_database.get('technical_leadership')
        if general_context:
            return self._context_to_dict(general_context)
        
        # Fallback context
        return self._get_fallback_context(topic)
    
    def _context_to_dict(self, context: TechnicalContext) -> Dict:
        """Convert TechnicalContext to dictionary."""
        return {
            'professional_role': context.professional_role,
            'key_insight': context.key_insight,
            'common_mistake': context.common_mistake,
            'contrarian_truth': context.contrarian_truth,
            'context': context.context,
            'example': context.example,
            'framework': context.framework,
            'situation': context.situation,
            'outcome': context.outcome
        }
    
    def _get_fallback_context(self, topic: str) -> Dict:
        """Generate fallback context for unknown topics."""
        return {
            'professional_role': 'CTO',
            'key_insight': f"{topic} success comes from focus, not complexity",
            'common_mistake': f"overengineering {topic} solutions",
            'contrarian_truth': f"most companies overthink {topic}",
            'context': f"I've seen companies spend months on {topic} when weeks would suffice",
            'example': f"Recently helped a client simplify their {topic} approach, saving 6 months of development",
            'framework': [
                f"1. Define clear {topic} requirements",
                f"2. Choose the simplest solution that works",
                f"3. Implement incrementally", 
                f"4. Measure and optimize"
            ],
            'situation': f"evaluating complex {topic} solutions",
            'outcome': "simplified approach that delivered faster results"
        }
    
    def _build_knowledge_database(self) -> Dict[str, TechnicalContext]:
        """Build comprehensive knowledge database of technical leadership insights."""
        return {
            'technical_leadership': TechnicalContext(
                professional_role='CTO',
                key_insight='Technical leadership is 80% people, 20% technology',
                common_mistake='focusing on tools instead of team outcomes',
                contrarian_truth='the best technical leaders write less code',
                context='Most technical leaders get promoted for coding skills but need leadership skills',
                example='Transformed a team from 2 features/month to 8 features/month by focusing on process, not tools',
                framework=[
                    '1. Hire for attitude, train for skills',
                    '2. Remove blockers before adding features',
                    '3. Measure team velocity, not individual output',
                    '4. Invest in developer experience infrastructure'
                ],
                situation='joining as fractional CTO at a struggling startup',
                outcome='team velocity increased 4x in 3 months'
            ),

            'microservices_architecture': TechnicalContext(
                professional_role='Principal Architect',
                key_insight='Microservices solve organizational problems, not technical ones',
                common_mistake='breaking up monoliths before solving team communication',
                contrarian_truth='most companies need better monoliths, not microservices',
                context='The microservices trend has created more problems than it solved',
                example='Helped a client consolidate 47 microservices into 8, reducing complexity by 80%',
                framework=[
                    '1. Start with a well-structured monolith',
                    '2. Extract services only when team boundaries require it',
                    '3. Focus on data consistency and service contracts',
                    '4. Monitor service health and dependencies closely'
                ],
                situation='architecting a new platform for a Series B company',
                outcome='delivered 6 months faster than the microservices approach they were considering'
            ),

            'technical_debt': TechnicalContext(
                professional_role='Engineering VP',
                key_insight='Technical debt is a feature prioritization problem, not an engineering problem',
                common_mistake='treating all technical debt as equally important',
                contrarian_truth='some technical debt should never be fixed',
                context='Teams often want to rewrite everything when they should be strategic about debt',
                example='Created a technical debt scoring system that helped prioritize $2M worth of improvements',
                framework=[
                    '1. Score debt by business impact × development friction',
                    '2. Fix debt that blocks new feature development first', 
                    '3. Leave debt that doesn\'t impact velocity or reliability',
                    '4. Prevent new debt with architecture reviews'
                ],
                situation='consulting on a legacy codebase with 5 years of accumulated debt',
                outcome='reduced development time by 40% while shipping new features'
            ),

            'team_scaling': TechnicalContext(
                professional_role='VP Engineering',
                key_insight='Team scaling fails when you hire too fast, not too slow',
                common_mistake='hiring for headcount instead of specific skills',
                contrarian_truth='smaller, well-coordinated teams often outperform large teams',
                context='Most startups destroy their engineering culture by scaling too aggressively',
                example='Helped a startup scale from 5 to 25 engineers while maintaining velocity',
                framework=[
                    '1. Define clear role expectations before hiring',
                    '2. Hire one senior person for every 2-3 junior people',
                    '3. Establish team communication patterns early',
                    '4. Create clear career progression paths'
                ],
                situation='scaling engineering team from 8 to 40 people in 12 months',
                outcome='maintained team velocity and reduced turnover to 5%'
            ),

            'nobuild_philosophy': TechnicalContext(
                professional_role='Fractional CTO',
                key_insight='#NOBUILD: Building custom software should be your last resort, not your first instinct',
                common_mistake='building everything in-house because "we\'re special"',
                contrarian_truth='your competitive advantage isn\'t in your auth system',
                context='Companies waste millions building commodity software they should buy',
                example='Saved a client $1.2M by choosing SaaS solutions instead of building custom tools',
                framework=[
                    '1. Buy for commodity functions (auth, payments, email)',
                    '2. Build only for core business differentiation',
                    '3. Evaluate total cost of ownership, not just development cost',
                    '4. Consider opportunity cost of engineering time'
                ],
                situation='evaluating build vs buy decisions for a fintech startup',
                outcome='launched 4 months faster by focusing engineering on core business logic'
            ),

            'startup_architecture': TechnicalContext(
                professional_role='Startup CTO',
                key_insight='Startup architecture should optimize for learning speed, not scale',
                common_mistake='over-architecting for scale you may never reach',
                contrarian_truth='premature architecture optimization kills more startups than technical debt',
                context='Startups need to move fast and learn, not build perfect systems',
                example='Helped a pre-seed startup build their MVP in 6 weeks with a simple, scalable architecture',
                framework=[
                    '1. Choose boring, proven technologies',
                    '2. Build for 10x scale, not 100x scale initially',
                    '3. Optimize for developer velocity over performance',
                    '4. Plan for architecture evolution, not perfection'
                ],
                situation='joining as founding CTO at an early-stage startup',
                outcome='achieved product-market fit 3 months faster than projected'
            ),

            'remote_team_management': TechnicalContext(
                professional_role='Remote Engineering Manager',
                key_insight='Remote team success depends on asynchronous communication, not tools',
                common_mistake='trying to recreate in-person interactions online',
                contrarian_truth='remote teams can be more productive than in-person teams',
                context='The shift to remote exposed fundamental communication problems in most teams',
                example='Transformed a struggling remote team into the highest-performing team in the company',
                framework=[
                    '1. Document everything - decisions, processes, rationale',
                    '2. Create overlap hours for real-time collaboration',
                    '3. Use asynchronous communication as the default',
                    '4. Invest in team social connections and culture'
                ],
                situation='managing a globally distributed team of 15 engineers',
                outcome='achieved 95% team satisfaction and 25% velocity improvement'
            ),

            'database_scaling': TechnicalContext(
                professional_role='Database Architect',
                key_insight='Database scaling problems are usually query optimization problems in disguise',
                common_mistake='sharding databases before optimizing queries',
                contrarian_truth='a well-tuned single database can handle most scale requirements',
                context='Teams often jump to complex scaling solutions when simple optimizations would work',
                example='Improved database performance 20x through query optimization and indexing strategy',
                framework=[
                    '1. Profile queries to find actual bottlenecks',
                    '2. Optimize indexes for your query patterns',
                    '3. Use read replicas before considering sharding',
                    '4. Consider caching layers for frequently accessed data'
                ],
                situation='consulting on database performance issues at a high-traffic SaaS company',
                outcome='eliminated the need for a $500K database migration project'
            )
        }