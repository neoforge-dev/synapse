"""
LinkedIn Content Templates
Based on analysis of 460 posts with proven engagement patterns
"""

from enum import Enum
from typing import Dict, List, Optional
from dataclasses import dataclass

class ContentType(Enum):
    """Content types based on high-performing patterns"""
    CONTROVERSIAL_TAKE = "controversial_take"
    PERSONAL_STORY = "personal_story" 
    TECHNICAL_INSIGHT = "technical_insight"
    CAREER_ADVICE = "career_advice"
    PRODUCT_MANAGEMENT = "product_management"
    STARTUP_LESSONS = "startup_lessons"
    INDUSTRY_OBSERVATION = "industry_observation"

@dataclass
class ContentTemplate:
    """Template structure for content generation"""
    content_type: ContentType
    hook_patterns: List[str]
    structure: List[str]
    cta_patterns: List[str]
    hashtag_groups: List[str]
    engagement_drivers: List[str]
    synapse_query_keywords: List[str]

class ContentTemplates:
    """Repository of proven content templates"""
    
    def __init__(self):
        self.templates = {
            ContentType.CONTROVERSIAL_TAKE: ContentTemplate(
                content_type=ContentType.CONTROVERSIAL_TAKE,
                hook_patterns=[
                    "Unpopular opinion: {controversial_statement}",
                    "Everyone talks about {topic}, but here's what they're missing:",
                    "After {years} years in tech, I think {controversial_opinion}",
                    "Hot take: {statement} is actually {counter_argument}",
                    "Most {industry_professionals} get {topic} completely wrong. Here's why:"
                ],
                structure=[
                    "📌 Hook with controversial statement",
                    "🎯 Personal experience/credibility",
                    "💡 Why conventional wisdom is wrong",
                    "🔍 3-4 supporting arguments with examples",
                    "✨ Practical implications",
                    "❓ Question to drive engagement"
                ],
                cta_patterns=[
                    "What's your take on {topic}?",
                    "Do you agree or disagree? Let me know in the comments.",
                    "Have you experienced this differently?",
                    "Which approach has worked for you?"
                ],
                hashtag_groups=[
                    "#productmanagement #techleadership #softwaredevelopment",
                    "#startupgrowth #techprofessionals #productdevelopment", 
                    "#programming #backenddevelopment #careerdevelopment"
                ],
                engagement_drivers=[
                    "strong_opinion",
                    "personal_experience", 
                    "counter_narrative",
                    "actionable_insights"
                ],
                synapse_query_keywords=[
                    "product management pitfalls",
                    "technical architecture decisions", 
                    "startup challenges",
                    "software development practices"
                ]
            ),
            
            ContentType.PERSONAL_STORY: ContentTemplate(
                content_type=ContentType.PERSONAL_STORY,
                hook_patterns=[
                    "{time_period} ago, I found myself {situation}",
                    "Last week at {event}, I discovered something that changed my perspective",
                    "Three years ago, I made a decision that {outcome}",
                    "Recently, I {action} and learned {lesson}",
                    "When I first started {activity}, I thought {assumption}. I was wrong."
                ],
                structure=[
                    "🎬 Set the scene with specific time/place",
                    "⚡ The challenge or turning point", 
                    "🔄 What you tried/learned",
                    "💡 Key insights or lessons",
                    "🚀 How it applies to others",
                    "❓ Relatable question for audience"
                ],
                cta_patterns=[
                    "What's been your experience with {topic}?",
                    "Have you faced similar challenges?",
                    "What would you have done differently?",
                    "What's your {topic} story?"
                ],
                hashtag_groups=[
                    "#careerdevelopment #techjourney #continuouslearning",
                    "#startuplife #entrepreneurship #techleadership",
                    "#softwaredevelopment #programming #professionalgrowth"
                ],
                engagement_drivers=[
                    "vulnerability",
                    "relatable_struggle",
                    "specific_details",
                    "universal_lesson"
                ],
                synapse_query_keywords=[
                    "career crossroads", 
                    "learning journey",
                    "professional challenges",
                    "startup experiences"
                ]
            ),
            
            ContentType.TECHNICAL_INSIGHT: ContentTemplate(
                content_type=ContentType.TECHNICAL_INSIGHT,
                hook_patterns=[
                    "Here's a {technology} pattern that changed how I {activity}",
                    "Most developers overlook this {technology} best practice:",
                    "After building {number} {projects}, here's what I learned about {technology}",
                    "The difference between junior and senior {role} isn't what you think",
                    "Everyone's talking about {trend}, but here's what really matters:"
                ],
                structure=[
                    "🎯 Technical hook with specific claim",
                    "📋 Context of the problem",
                    "⚡ The insight or solution",
                    "🔧 Practical implementation details",
                    "📈 Results or benefits",
                    "💭 Broader implications for development"
                ],
                cta_patterns=[
                    "What's your experience with {technology}?", 
                    "Have you tried this approach?",
                    "What patterns have worked for you?",
                    "Thoughts on {technical_concept}?"
                ],
                hashtag_groups=[
                    "#python #backenddevelopment #softwaredevelopment",
                    "#django #fastapi #webdevelopment",
                    "#softwarearchitecture #programming #coding"
                ],
                engagement_drivers=[
                    "actionable_code",
                    "practical_experience",
                    "specific_examples", 
                    "measurable_results"
                ],
                synapse_query_keywords=[
                    "Python ecosystem",
                    "backend development",
                    "software architecture",
                    "clean code practices"
                ]
            ),
            
            ContentType.CAREER_ADVICE: ContentTemplate(
                content_type=ContentType.CAREER_ADVICE,
                hook_patterns=[
                    "The best career advice I wish I'd known {time_period} ago:",
                    "Here's how to {achieve_goal} in {timeframe} (from my experience)",
                    "Stop doing {bad_practice}. Start doing {good_practice} instead.",
                    "The {number} habits that accelerated my career growth:",
                    "If you're struggling with {problem}, try this approach:"
                ],
                structure=[
                    "💡 Clear value proposition hook",
                    "📖 Personal credibility/background",
                    "📝 Numbered list of actionable advice",
                    "✅ Specific examples or results",
                    "⚡ Why this matters now",
                    "🎯 Call to action for implementation"
                ],
                cta_patterns=[
                    "Which of these resonates most with your experience?",
                    "What career advice would you add?",
                    "Have you tried any of these approaches?",
                    "What's worked best for your career growth?"
                ],
                hashtag_groups=[
                    "#careerdevelopment #techprofessionals #professionalgrowth",
                    "#techleadership #softwaredevelopment #continuouslearning",
                    "#careeradvice #techcareer #programming"
                ],
                engagement_drivers=[
                    "numbered_lists",
                    "actionable_steps",
                    "personal_results",
                    "universal_relevance"
                ],
                synapse_query_keywords=[
                    "career growth",
                    "professional development", 
                    "specialization benefits",
                    "tech career advice"
                ]
            ),
            
            ContentType.PRODUCT_MANAGEMENT: ContentTemplate(
                content_type=ContentType.PRODUCT_MANAGEMENT,
                hook_patterns=[
                    "Most product managers make this {number} critical mistake:",
                    "Having navigated both coding and product management, here's what I learned:",
                    "Are your product management practices holding you back?",
                    "The difference between good and great product management:",
                    "Here's why {common_practice} is actually hurting your product:"
                ],
                structure=[
                    "🎯 Problem identification hook",
                    "🔍 Why this matters (impact/consequences)",
                    "📋 Common pitfalls or mistakes",
                    "✅ Better approach or solution",
                    "📈 Expected outcomes",
                    "💼 Call for consultation or discussion"
                ],
                cta_patterns=[
                    "What product management challenges are you facing?",
                    "Have you seen these patterns in your organization?",
                    "Which of these resonates with your experience?",
                    "Need help with product strategy? Let's discuss."
                ],
                hashtag_groups=[
                    "#productmanagement #techprofessionals #productdevelopment",
                    "#startupgrowth #techleadership #softwaredevelopment",
                    "#fractionalcto #productmanager #productowner"
                ],
                engagement_drivers=[
                    "problem_solution_format",
                    "authority_positioning",
                    "consultation_hooks",
                    "actionable_frameworks"
                ],
                synapse_query_keywords=[
                    "product management pitfalls",
                    "product development challenges",
                    "startup product strategy",
                    "technical leadership"
                ]
            ),
            
            ContentType.STARTUP_LESSONS: ContentTemplate(
                content_type=ContentType.STARTUP_LESSONS,
                hook_patterns=[
                    "After attending {event}, here's what I learned about startup growth:",
                    "The {number} startup lessons that changed my perspective:",
                    "Most startups fail because they ignore this one thing:",
                    "What {successful_company} gets right that others miss:",
                    "The hard truth about startup success no one talks about:"
                ],
                structure=[
                    "📍 Context or trigger event",
                    "💡 Key observation or insight",
                    "📊 Supporting evidence or examples",
                    "⚡ Actionable implications",
                    "🎯 Application for audience",
                    "💼 Subtle consultation opportunity"
                ],
                cta_patterns=[
                    "What startup lessons have shaped your approach?",
                    "Have you experienced this in your startup journey?",
                    "What would you add to this list?",
                    "Struggling with startup challenges? Let's connect."
                ],
                hashtag_groups=[
                    "#startupgrowth #entrepreneurship #startuplife",
                    "#techstartups #businessdevelopment #innovation",
                    "#fractionalcto #startupadvice #techleadership"
                ],
                engagement_drivers=[
                    "event_triggered_insights",
                    "startup_community_relevance",
                    "practical_business_advice",
                    "networking_opportunities"
                ],
                synapse_query_keywords=[
                    "startup challenges",
                    "entrepreneurial journey",
                    "business development",
                    "startup ecosystem events"
                ]
            )
        }
    
    def get_template(self, content_type: ContentType) -> ContentTemplate:
        """Get specific content template"""
        return self.templates.get(content_type)
    
    def get_all_templates(self) -> Dict[ContentType, ContentTemplate]:
        """Get all available templates"""
        return self.templates
    
    def get_hook_patterns(self, content_type: ContentType) -> List[str]:
        """Get hook patterns for specific content type"""
        template = self.get_template(content_type)
        return template.hook_patterns if template else []
    
    def get_engagement_drivers(self, content_type: ContentType) -> List[str]:
        """Get engagement drivers for content type"""
        template = self.get_template(content_type)
        return template.engagement_drivers if template else []
    
    def get_synapse_keywords(self, content_type: ContentType) -> List[str]:
        """Get Synapse query keywords for content enrichment"""
        template = self.get_template(content_type)
        return template.synapse_query_keywords if template else []