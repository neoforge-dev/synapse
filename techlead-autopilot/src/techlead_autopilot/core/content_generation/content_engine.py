"""
Content Generation Engine - Core business logic extracted from Synapse system.

This engine leverages proven content generation algorithms that have produced
€290K in consultation pipeline through technical leadership content.
"""

import logging
import random
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional
from enum import Enum

from .content_templates import ContentTemplate, ContentType, get_template_library
from .technical_knowledge import TechnicalKnowledgeBase

logger = logging.getLogger(__name__)


@dataclass
class GeneratedContent:
    """Generated technical leadership content with metadata."""
    content_type: ContentType
    hook: str
    body: str
    call_to_action: str
    hashtags: str
    full_post: str
    engagement_prediction: float
    generation_metadata: Dict
    
    @property
    def character_count(self) -> int:
        """Get character count for the full post."""
        return len(self.full_post)
    
    @property
    def estimated_read_time_seconds(self) -> int:
        """Estimate reading time in seconds (average 200 words/minute)."""
        word_count = len(self.full_post.split())
        return int((word_count / 200) * 60)


class ContentGenerationEngine:
    """
    Core content generation engine using proven algorithms from Synapse system.
    
    Generates technical leadership content optimized for consultation pipeline generation.
    Based on analysis of 474 posts with 10,841 reactions and 3,131 comments.
    """
    
    def __init__(self):
        self.template_library = get_template_library()
        self.knowledge_base = TechnicalKnowledgeBase()
        
        # Proven engagement patterns from €290K pipeline analysis
        self.proven_patterns = {
            'high_engagement_hooks': [
                "After {years} years as a {role}, I've learned that {insight}",
                "The biggest mistake I see {audience} making is {mistake}",
                "Here's what nobody tells you about {topic}: {truth}",
                "I used to think {old_belief}. I was wrong.",
                "Three months ago, {situation}. Today, {outcome}."
            ],
            'consultation_triggers': [
                "If your team is struggling with this, let's chat.",
                "I help companies solve exactly this problem.",
                "This is what I do for my clients every day.",
                "Happy to share more details if you're facing this.",
                "I've guided 50+ teams through this transition."
            ],
            'engagement_drivers': [
                "controversial_opinion",
                "personal_story",
                "counter_intuitive_truth", 
                "time_bound_experience",
                "industry_observation"
            ]
        }
        
        # Content performance data from Synapse analysis
        self.performance_data = {
            'optimal_length': {
                'technical_insights': (280, 400),
                'leadership_stories': (400, 600),
                'controversial_takes': (200, 350),
                'career_advice': (350, 500)
            },
            'best_posting_times': {
                'technical_leadership': "Tuesday 7:00 AM",
                'architecture_content': "Thursday 8:30 AM", 
                'career_development': "Monday 6:30 AM",
                'startup_scaling': "Wednesday 7:30 AM"
            },
            'hashtag_performance': {
                'high_engagement': ["#TechnicalLeadership", "#SoftwareArchitecture", "#EngineeringManagement"],
                'niche_authority': ["#NOBUILD", "#TechDebt", "#FractionalCTO"],
                'consultation_driving': ["#TechConsulting", "#StartupAdvice", "#CTOServices"]
            }
        }

    def generate_content(
        self,
        content_type: ContentType,
        topic: str,
        target_audience: str = "technical_leaders",
        consultation_focused: bool = True,
        target_engagement_rate: float = 0.035
    ) -> GeneratedContent:
        """
        Generate optimized technical leadership content.
        
        Args:
            content_type: Type of content to generate
            topic: Main topic/theme for the content
            target_audience: Primary audience (technical_leaders, startup_founders, etc.)
            consultation_focused: Whether to optimize for consultation inquiries
            target_engagement_rate: Target engagement rate (default 3.5% based on proven data)
        
        Returns:
            GeneratedContent with all components and metadata
        """
        logger.info(f"Generating {content_type.value} content for topic: {topic}")
        
        # Get template for content type
        template = self.template_library.get(content_type)
        if not template:
            raise ValueError(f"No template available for content type: {content_type}")
        
        # Get relevant technical knowledge
        knowledge_context = self.knowledge_base.get_context_for_topic(topic)
        
        # Generate content components
        hook = self._generate_hook(template, topic, knowledge_context, target_audience)
        body = self._generate_body(template, topic, knowledge_context, target_audience)
        cta = self._generate_cta(template, consultation_focused, target_audience)
        hashtags = self._select_hashtags(content_type, topic, consultation_focused)
        
        # Assemble full post
        full_post = self._assemble_post(hook, body, cta, hashtags)
        
        # Predict engagement based on proven patterns
        engagement_prediction = self._predict_engagement(
            content_type, len(full_post), knowledge_context, target_engagement_rate
        )
        
        # Generate metadata
        metadata = {
            'generation_timestamp': datetime.now().isoformat(),
            'topic': topic,
            'target_audience': target_audience,
            'consultation_focused': consultation_focused,
            'template_used': content_type.value,
            'character_count': len(full_post),
            'estimated_read_time': f"{len(full_post.split()) / 200:.1f} minutes",
            'engagement_drivers': template.engagement_drivers,
            'consultation_triggers_included': consultation_focused,
            'optimal_posting_time': self.performance_data['best_posting_times'].get(
                content_type.value, "Tuesday 7:00 AM"
            )
        }
        
        return GeneratedContent(
            content_type=content_type,
            hook=hook,
            body=body,
            call_to_action=cta,
            hashtags=hashtags,
            full_post=full_post,
            engagement_prediction=engagement_prediction,
            generation_metadata=metadata
        )

    def _generate_hook(
        self,
        template: ContentTemplate,
        topic: str,
        knowledge_context: Dict,
        target_audience: str
    ) -> str:
        """Generate engaging hook using proven patterns."""
        hook_patterns = self.proven_patterns['high_engagement_hooks']
        
        # Select hook pattern based on content type and available context
        selected_pattern = random.choice(hook_patterns)
        
        # Fill in variables based on knowledge context
        replacements = {
            '{years}': str(random.choice([3, 5, 8, 10, 12])),
            '{role}': knowledge_context.get('professional_role', 'CTO'),
            '{insight}': knowledge_context.get('key_insight', f"{topic} isn't what most people think"),
            '{audience}': 'technical leaders' if target_audience == 'technical_leaders' else 'startups',
            '{mistake}': knowledge_context.get('common_mistake', f"overcomplicating {topic}"),
            '{topic}': topic,
            '{truth}': knowledge_context.get('contrarian_truth', f"{topic} is simpler than you think"),
            '{old_belief}': knowledge_context.get('old_belief', f"{topic} was all about technology"),
            '{situation}': knowledge_context.get('situation', f"I was consulting on a complex {topic} project"),
            '{outcome}': knowledge_context.get('outcome', "the client saved 60% on development costs")
        }
        
        hook = selected_pattern
        for placeholder, replacement in replacements.items():
            hook = hook.replace(placeholder, replacement)
            
        return hook

    def _generate_body(
        self,
        template: ContentTemplate,
        topic: str,
        knowledge_context: Dict,
        target_audience: str
    ) -> str:
        """Generate content body using template structure."""
        # Use template structure to build compelling narrative
        body_parts = []
        
        # Context/Problem section
        if 'context' in template.structure:
            context = knowledge_context.get(
                'context',
                f"Most {target_audience} approach {topic} backwards."
            )
            body_parts.append(context)
        
        # Solution/Insight section
        if 'insight' in template.structure:
            insight = knowledge_context.get(
                'insight',
                f"The key to {topic} isn't adding complexity—it's removing it."
            )
            body_parts.append(f"\nHere's what I've learned:\n{insight}")
        
        # Evidence/Example section
        if 'example' in template.structure:
            example = knowledge_context.get(
                'example',
                f"Last month, I helped a Series B startup reduce their {topic} costs by 40% using this approach."
            )
            body_parts.append(f"\n{example}")
        
        # Action/Framework section
        if 'framework' in template.structure:
            framework = knowledge_context.get('framework', [
                f"1. Audit your current {topic} setup",
                f"2. Identify the 20% causing 80% of problems", 
                f"3. Eliminate unnecessary complexity",
                f"4. Measure and iterate"
            ])
            if isinstance(framework, list):
                framework_text = "\n".join(framework)
            else:
                framework_text = str(framework)
            body_parts.append(f"\nMy framework:\n{framework_text}")
        
        return "\n".join(body_parts)

    def _generate_cta(
        self,
        template: ContentTemplate,
        consultation_focused: bool,
        target_audience: str
    ) -> str:
        """Generate call-to-action optimized for consultation inquiries."""
        if consultation_focused:
            consultation_ctas = self.proven_patterns['consultation_triggers']
            return random.choice(consultation_ctas)
        else:
            # Engagement-focused CTAs
            engagement_ctas = [
                "What's been your experience with this?",
                "Agree or disagree? Share your thoughts below.",
                "What would you add to this list?",
                "How do you handle this at your company?"
            ]
            return random.choice(engagement_ctas)

    def _select_hashtags(
        self,
        content_type: ContentType,
        topic: str,
        consultation_focused: bool
    ) -> str:
        """Select optimal hashtags based on performance data."""
        hashtag_pool = []
        
        # Add high-engagement hashtags
        hashtag_pool.extend(self.performance_data['hashtag_performance']['high_engagement'])
        
        # Add niche authority hashtags
        hashtag_pool.extend(self.performance_data['hashtag_performance']['niche_authority'])
        
        # Add consultation-driving hashtags if focused on business development
        if consultation_focused:
            hashtag_pool.extend(self.performance_data['hashtag_performance']['consultation_driving'])
        
        # Add topic-specific hashtags
        topic_hashtags = {
            'architecture': ['#SoftwareArchitecture', '#SystemDesign', '#TechDebt'],
            'team_building': ['#TeamBuilding', '#EngineeringManagement', '#TeamVelocity'],
            'startup_scaling': ['#StartupScaling', '#TechStrategy', '#FractionalCTO'],
            'nobuild': ['#NOBUILD', '#BuildVsBuy', '#TechDecisions']
        }
        
        for key, hashtags in topic_hashtags.items():
            if key.lower() in topic.lower():
                hashtag_pool.extend(hashtags)
        
        # Select optimal number of hashtags (3-5 performs best)
        selected = list(set(hashtag_pool))[:4]  # Remove duplicates and limit
        return " ".join(selected)

    def _assemble_post(self, hook: str, body: str, cta: str, hashtags: str) -> str:
        """Assemble final post with optimal formatting."""
        components = []
        
        if hook:
            components.append(hook)
        
        if body:
            components.append(body)
        
        if cta:
            components.append(f"\n{cta}")
        
        if hashtags:
            components.append(f"\n\n{hashtags}")
        
        return "\n".join(components)

    def _predict_engagement(
        self,
        content_type: ContentType,
        content_length: int,
        knowledge_context: Dict,
        target_rate: float
    ) -> float:
        """Predict engagement rate based on historical performance data."""
        base_rate = 0.025  # 2.5% baseline engagement rate
        
        # Content type multipliers (based on Synapse performance data)
        type_multipliers = {
            ContentType.TECHNICAL_INSIGHT: 1.2,
            ContentType.LEADERSHIP_STORY: 1.4,
            ContentType.CONTROVERSIAL_TAKE: 1.6,
            ContentType.CAREER_ADVICE: 1.1,
            ContentType.NOBUILD_PHILOSOPHY: 1.3
        }
        
        # Length optimization (based on performance analysis)
        optimal_range = self.performance_data['optimal_length'].get(
            content_type.value, (300, 500)
        )
        if optimal_range[0] <= content_length <= optimal_range[1]:
            length_multiplier = 1.1
        else:
            length_multiplier = 0.9
        
        # Knowledge context quality boost
        context_quality = len(knowledge_context) * 0.05  # 5% per context element
        
        predicted_rate = (
            base_rate * 
            type_multipliers.get(content_type, 1.0) * 
            length_multiplier * 
            (1 + context_quality)
        )
        
        return min(predicted_rate, target_rate * 1.5)  # Cap at 150% of target