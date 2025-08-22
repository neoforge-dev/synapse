"""Content templates for technical leadership content generation."""

from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional


class ContentType(Enum):
    """Types of technical leadership content."""
    TECHNICAL_INSIGHT = "technical_insight"
    LEADERSHIP_STORY = "leadership_story"
    CONTROVERSIAL_TAKE = "controversial_take"
    CAREER_ADVICE = "career_advice"
    NOBUILD_PHILOSOPHY = "nobuild_philosophy"
    ARCHITECTURE_REVIEW = "architecture_review"
    TEAM_BUILDING = "team_building"
    STARTUP_SCALING = "startup_scaling"


@dataclass
class ContentTemplate:
    """Template for generating specific type of content."""
    content_type: ContentType
    structure: List[str]  # Ordered list of content sections
    engagement_drivers: List[str]  # Psychological triggers for engagement
    consultation_hooks: List[str]  # Phrases that drive consultation inquiries
    optimal_length_range: tuple[int, int]  # Character count range for optimal performance
    target_audience: str
    example_topics: List[str]


def get_template_library() -> Dict[ContentType, ContentTemplate]:
    """Get the complete library of proven content templates."""
    return {
        ContentType.TECHNICAL_INSIGHT: ContentTemplate(
            content_type=ContentType.TECHNICAL_INSIGHT,
            structure=["hook", "context", "insight", "example", "framework", "cta"],
            engagement_drivers=[
                "counter_intuitive_truth",
                "industry_experience",
                "concrete_examples",
                "actionable_framework"
            ],
            consultation_hooks=[
                "This is exactly what I help my clients with",
                "I've guided 50+ teams through this transition",
                "Happy to share the detailed framework if you're interested",
                "If your team is facing this challenge, let's chat"
            ],
            optimal_length_range=(280, 400),
            target_audience="technical_leaders",
            example_topics=[
                "microservices architecture decisions",
                "technical debt prioritization",
                "API design principles",
                "database scaling strategies"
            ]
        ),

        ContentType.LEADERSHIP_STORY: ContentTemplate(
            content_type=ContentType.LEADERSHIP_STORY,
            structure=["hook", "situation", "challenge", "decision", "outcome", "lesson", "cta"],
            engagement_drivers=[
                "personal_vulnerability",
                "dramatic_transformation",
                "specific_numbers",
                "universal_lesson"
            ],
            consultation_hooks=[
                "This transformation took 6 months with the right approach",
                "I now help other CTOs navigate similar situations",
                "The framework I developed is what I use with all my clients",
                "If you're in a similar position, I'd love to help"
            ],
            optimal_length_range=(400, 600),
            target_audience="engineering_leaders",
            example_topics=[
                "team velocity improvement",
                "architecture migration stories",
                "hiring and scaling challenges",
                "cultural transformation"
            ]
        ),

        ContentType.CONTROVERSIAL_TAKE: ContentTemplate(
            content_type=ContentType.CONTROVERSIAL_TAKE,
            structure=["provocative_hook", "common_belief", "contrarian_position", "evidence", "cta"],
            engagement_drivers=[
                "challenges_conventional_wisdom", 
                "industry_contrarian_view",
                "data_backed_argument",
                "discussion_catalyst"
            ],
            consultation_hooks=[
                "Most companies get this completely wrong",
                "I help clients avoid this expensive mistake",
                "This misconception costs companies millions",
                "Happy to explain why this approach works better"
            ],
            optimal_length_range=(200, 350),
            target_audience="technical_leaders",
            example_topics=[
                "microservices are overrated",
                "premature optimization myths",
                "agile methodology limitations",
                "open source vs proprietary"
            ]
        ),

        ContentType.CAREER_ADVICE: ContentTemplate(
            content_type=ContentType.CAREER_ADVICE,
            structure=["relatable_hook", "common_mistake", "better_approach", "actionable_steps", "cta"],
            engagement_drivers=[
                "career_transformation",
                "mentor_wisdom", 
                "practical_steps",
                "immediate_application"
            ],
            consultation_hooks=[
                "I help technical leaders navigate exactly these decisions",
                "This is the roadmap I share with all my mentees",
                "If you're at this crossroads, let's talk",
                "I've helped 100+ engineers make this transition"
            ],
            optimal_length_range=(350, 500),
            target_audience="aspiring_leaders",
            example_topics=[
                "IC to manager transition",
                "startup vs enterprise decisions",
                "compensation negotiation",
                "technical skill development"
            ]
        ),

        ContentType.NOBUILD_PHILOSOPHY: ContentTemplate(
            content_type=ContentType.NOBUILD_PHILOSOPHY,
            structure=["hook", "expensive_mistake", "nobuild_principle", "real_example", "savings", "cta"],
            engagement_drivers=[
                "cost_savings_focus",
                "build_vs_buy_wisdom",
                "time_to_market",
                "resource_optimization"
            ],
            consultation_hooks=[
                "I specialize in #NOBUILD audits that save companies millions",
                "This is the exact framework I use with all my consulting clients", 
                "If you're evaluating build vs buy decisions, I can help",
                "I've saved companies $50M+ with this approach"
            ],
            optimal_length_range=(300, 450),
            target_audience="startup_founders",
            example_topics=[
                "authentication systems",
                "payment processing",
                "email delivery",
                "monitoring and alerting"
            ]
        ),

        ContentType.ARCHITECTURE_REVIEW: ContentTemplate(
            content_type=ContentType.ARCHITECTURE_REVIEW,
            structure=["problem_hook", "architecture_overview", "pain_points", "solution", "results", "cta"],
            engagement_drivers=[
                "technical_deep_dive",
                "architecture_patterns",
                "performance_improvements",
                "scalability_solutions"
            ],
            consultation_hooks=[
                "Architecture reviews are one of my core services",
                "I've helped 200+ companies optimize their technical architecture",
                "This is exactly the type of analysis I do for clients",
                "If your architecture needs optimization, let's discuss"
            ],
            optimal_length_range=(400, 550),
            target_audience="technical_leaders",
            example_topics=[
                "monolith to microservices migration",
                "database optimization strategies", 
                "API architecture patterns",
                "caching layer design"
            ]
        ),

        ContentType.TEAM_BUILDING: ContentTemplate(
            content_type=ContentType.TEAM_BUILDING,
            structure=["team_challenge", "impact", "intervention", "framework", "results", "cta"],
            engagement_drivers=[
                "team_transformation",
                "velocity_improvements",
                "cultural_change",
                "measurable_outcomes"
            ],
            consultation_hooks=[
                "Team building is what I do for 90% of my clients",
                "I've helped build 50+ high-performance engineering teams",
                "This framework has transformed teams at companies like...",
                "If your team velocity is stagnating, I can help"
            ],
            optimal_length_range=(350, 500),
            target_audience="engineering_managers", 
            example_topics=[
                "remote team collaboration",
                "code review processes",
                "sprint planning optimization",
                "cross-team communication"
            ]
        ),

        ContentType.STARTUP_SCALING: ContentTemplate(
            content_type=ContentType.STARTUP_SCALING,
            structure=["scaling_challenge", "common_approach", "better_way", "case_study", "outcomes", "cta"],
            engagement_drivers=[
                "growth_story",
                "startup_journey",
                "scaling_challenges",
                "proven_solutions"
            ],
            consultation_hooks=[
                "Startup scaling is my specialty - I've helped 100+ companies",
                "This is the exact playbook I use with Series A-B clients",
                "If you're scaling past 50 engineers, we should talk", 
                "I help startups avoid the common scaling pitfalls"
            ],
            optimal_length_range=(400, 550),
            target_audience="startup_founders",
            example_topics=[
                "engineering team scaling",
                "technical infrastructure growth",
                "development process evolution", 
                "architecture for scale"
            ]
        )
    }