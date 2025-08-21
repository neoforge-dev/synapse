"""
LinkedIn Content Generator
Main engine for generating LinkedIn content using Synapse enrichment
"""

import random
import logging
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass

from .templates import ContentTemplates, ContentType, ContentTemplate
from .synapse_enricher import SynapseContentEnricher, EnrichedContent

logger = logging.getLogger(__name__)

@dataclass
class GeneratedContent:
    """Generated LinkedIn content with metadata"""
    content_type: ContentType
    hook: str
    body: str
    call_to_action: str
    hashtags: str
    full_post: str
    enrichment_data: EnrichedContent
    engagement_prediction: float
    generation_metadata: Dict

class LinkedInContentGenerator:
    """Main content generation engine"""
    
    def __init__(self):
        self.templates = ContentTemplates()
        self.enricher = SynapseContentEnricher()
        
        # High-performing engagement patterns from analysis
        self.proven_patterns = {
            'hooks': [
                "question_based",
                "controversial_statement", 
                "time_reference",
                "personal_experience",
                "industry_observation"
            ],
            'structure': [
                "hook_context_insight_action_cta",
                "story_lesson_application_question",
                "problem_solution_result_discussion"
            ],
            'cta_types': [
                "discussion_starter",
                "experience_sharing",
                "advice_request",
                "consultation_hook"
            ]
        }
    
    def generate_content(self, 
                        content_type: ContentType,
                        topic: str,
                        specific_angle: Optional[str] = None,
                        target_engagement: float = 0.06) -> GeneratedContent:
        """Generate LinkedIn content for specified type and topic"""
        
        logger.info(f"Generating {content_type.value} content for topic: {topic}")
        
        # Get template for content type
        template = self.templates.get_template(content_type)
        if not template:
            raise ValueError(f"No template found for content type: {content_type}")
        
        # Enrich content with Synapse insights
        enriched_content = self.enricher.enrich_content(
            topic=topic,
            content_type=content_type.value,
            keywords=template.synapse_query_keywords
        )
        
        # Generate content components
        hook = self._generate_hook(template, topic, enriched_content, specific_angle)
        body = self._generate_body(template, topic, enriched_content, specific_angle)
        cta = self._generate_cta(template, topic, enriched_content)
        hashtags = self._select_hashtags(template, content_type)
        
        # Assemble full post
        full_post = self._assemble_post(hook, body, cta, hashtags)
        
        # Predict engagement based on patterns
        engagement_prediction = self._predict_engagement(
            content_type, enriched_content, len(full_post), target_engagement
        )
        
        # Generate metadata
        metadata = {
            'generation_time': datetime.now().isoformat(),
            'topic': topic,
            'specific_angle': specific_angle,
            'template_used': content_type.value,
            'synapse_confidence': enriched_content.confidence_score,
            'content_length': len(full_post),
            'estimated_read_time': len(full_post.split()) / 200,  # words per minute
            'engagement_drivers_used': template.engagement_drivers
        }
        
        return GeneratedContent(
            content_type=content_type,
            hook=hook,
            body=body, 
            call_to_action=cta,
            hashtags=hashtags,
            full_post=full_post,
            enrichment_data=enriched_content,
            engagement_prediction=engagement_prediction,
            generation_metadata=metadata
        )
    
    def _generate_hook(self, template: ContentTemplate, topic: str, 
                      enriched_content: EnrichedContent, specific_angle: Optional[str]) -> str:
        """Generate engaging hook based on template and enriched data"""
        
        # Choose hook pattern based on available enriched content
        hook_pattern = self._select_best_hook_pattern(template, enriched_content)
        
        # Fill in hook with relevant content
        if specific_angle:
            hook = hook_pattern.replace('{topic}', topic).replace('{controversial_statement}', specific_angle)
        else:
            # Use enriched content to create compelling hook
            if enriched_content.personal_stories:
                story = enriched_content.personal_stories[0]
                if "years ago" in story.lower():
                    hook = f"Three years ago, I found myself {story.split('.')[0].lower()}."
                elif "recently" in story.lower():
                    hook = f"Recently, {story.split('.')[0].lower()}."
                else:
                    hook = hook_pattern.replace('{topic}', topic)
            elif enriched_content.relevant_beliefs:
                belief = enriched_content.relevant_beliefs[0]
                hook = f"After years in tech, I believe {belief.lower()}"
            else:
                hook = hook_pattern.replace('{topic}', topic)
                
        # Ensure hook has proper formatting
        if not hook.endswith(('?', '!', ':')):
            hook += '.'
            
        return hook
    
    def _generate_body(self, template: ContentTemplate, topic: str,
                      enriched_content: EnrichedContent, specific_angle: Optional[str]) -> str:
        """Generate main body content following template structure"""
        
        body_parts = []
        
        # Context/Background
        if enriched_content.personal_stories:
            story = enriched_content.personal_stories[0]
            body_parts.append(f"\n{story}")
        elif enriched_content.synapse_search_results:
            context = enriched_content.synapse_search_results[0]['content'][:200]
            body_parts.append(f"\n{context}...")
        
        # Main insights/content
        if enriched_content.technical_insights:
            body_parts.append("\nHere's what I've learned:")
            for i, insight in enumerate(enriched_content.technical_insights[:3], 1):
                body_parts.append(f"\n{i}️⃣ {insight}")
        elif enriched_content.relevant_beliefs:
            body_parts.append("\nKey insights:")
            for belief in enriched_content.relevant_beliefs[:3]:
                body_parts.append(f"\n• {belief}")
        
        # Results/implications
        if template.content_type == ContentType.PERSONAL_STORY:
            body_parts.append("\nThis experience taught me:")
            body_parts.append("• The importance of continuous learning")
            body_parts.append("• How specialization can accelerate growth")
            body_parts.append("• Why community matters in tech")
        elif template.content_type == ContentType.TECHNICAL_INSIGHT:
            body_parts.append("\nThe results speak for themselves:")
            body_parts.append("• Improved code quality and maintainability")
            body_parts.append("• Faster development cycles")
            body_parts.append("• Better team collaboration")
        
        # Practical application
        body_parts.append(f"\nFor anyone working in {topic}:")
        if enriched_content.engagement_patterns:
            pattern = enriched_content.engagement_patterns[0]
            body_parts.append(f"Remember that {pattern.lower()}")
        else:
            body_parts.append("Focus on continuous improvement and learning from the community.")
        
        return ''.join(body_parts)
    
    def _generate_cta(self, template: ContentTemplate, topic: str,
                     enriched_content: EnrichedContent) -> str:
        """Generate call-to-action based on template and content type"""
        
        cta_patterns = template.cta_patterns
        
        # Choose CTA based on content type and business objectives
        if template.content_type in [ContentType.PRODUCT_MANAGEMENT, ContentType.STARTUP_LESSONS]:
            # Business development focused CTAs
            ctas = [
                f"What {topic} challenges are you facing? Let's discuss how I can help.",
                f"Need strategic guidance on {topic}? I offer fractional CTO services.",
                f"Struggling with {topic}? Let's connect and explore solutions."
            ]
            return random.choice(ctas)
        elif template.content_type == ContentType.CONTROVERSIAL_TAKE:
            # Engagement focused CTAs
            ctas = [
                f"Do you agree with this take on {topic}?",
                f"What's your experience with {topic}?",
                f"Have you seen this pattern in your work?"
            ]
            return random.choice(ctas)
        else:
            # General discussion CTAs
            return random.choice(cta_patterns).replace('{topic}', topic)
    
    def _select_hashtags(self, template: ContentTemplate, content_type: ContentType) -> str:
        """Select optimal hashtags based on content type and proven performance"""
        
        hashtag_groups = template.hashtag_groups
        
        # Choose hashtag group based on content type
        if content_type in [ContentType.PRODUCT_MANAGEMENT, ContentType.STARTUP_LESSONS]:
            return "#productmanagement #techleadership #startupgrowth #fractionalcto"
        elif content_type == ContentType.TECHNICAL_INSIGHT:
            return "#python #backenddevelopment #softwaredevelopment #programming"
        elif content_type == ContentType.CAREER_ADVICE:
            return "#careerdevelopment #techprofessionals #continuouslearning"
        else:
            return random.choice(hashtag_groups)
    
    def _assemble_post(self, hook: str, body: str, cta: str, hashtags: str) -> str:
        """Assemble complete LinkedIn post"""
        
        post_parts = [hook]
        
        if body.strip():
            post_parts.append(body)
        
        post_parts.append(f"\n{cta}")
        post_parts.append(f"\n\n{hashtags}")
        
        return ''.join(post_parts).strip()
    
    def _select_best_hook_pattern(self, template: ContentTemplate, 
                                 enriched_content: EnrichedContent) -> str:
        """Select best hook pattern based on available enriched content"""
        
        patterns = template.hook_patterns
        
        # Prioritize patterns based on available content
        if enriched_content.personal_stories:
            story_patterns = [p for p in patterns if any(word in p for word in ['ago', 'recently', 'found myself'])]
            if story_patterns:
                return random.choice(story_patterns)
        
        if enriched_content.relevant_beliefs and enriched_content.confidence_score > 0.7:
            controversial_patterns = [p for p in patterns if 'opinion' in p or 'take' in p]
            if controversial_patterns:
                return random.choice(controversial_patterns)
        
        # Default to random pattern
        return random.choice(patterns)
    
    def _predict_engagement(self, content_type: ContentType, enriched_content: EnrichedContent,
                           content_length: int, target_engagement: float) -> float:
        """Predict engagement rate based on content analysis"""
        
        base_rate = 0.018  # Average engagement rate from analysis
        
        # Adjust based on content type performance
        type_multipliers = {
            ContentType.CONTROVERSIAL_TAKE: 1.4,  # Higher engagement for strong opinions
            ContentType.PERSONAL_STORY: 1.2,     # Stories perform well
            ContentType.TECHNICAL_INSIGHT: 1.1,   # Technical content has steady engagement
            ContentType.CAREER_ADVICE: 1.3,      # Advice content gets saved/shared
            ContentType.PRODUCT_MANAGEMENT: 1.5,  # Business content drives inquiries
            ContentType.STARTUP_LESSONS: 1.25    # Startup content resonates with audience
        }
        
        predicted_rate = base_rate * type_multipliers.get(content_type, 1.0)
        
        # Adjust based on enrichment quality
        if enriched_content.confidence_score > 0.7:
            predicted_rate *= 1.2  # High-quality enrichment boosts engagement
        elif enriched_content.confidence_score < 0.3:
            predicted_rate *= 0.8  # Low-quality enrichment reduces engagement
        
        # Adjust based on content length (optimal range: 150-300 words)
        word_count = len(content_length) / 5  # Rough words estimate
        if 150 <= word_count <= 300:
            predicted_rate *= 1.1  # Optimal length
        elif word_count > 500:
            predicted_rate *= 0.9  # Too long
        elif word_count < 100:
            predicted_rate *= 0.85 # Too short
        
        return min(predicted_rate, 0.25)  # Cap at 25% engagement rate
    
    def generate_content_batch(self, content_specs: List[Dict]) -> List[GeneratedContent]:
        """Generate multiple pieces of content in batch"""
        
        generated_content = []
        
        for spec in content_specs:
            try:
                content = self.generate_content(
                    content_type=ContentType(spec['content_type']),
                    topic=spec['topic'],
                    specific_angle=spec.get('specific_angle'),
                    target_engagement=spec.get('target_engagement', 0.06)
                )
                generated_content.append(content)
                
            except Exception as e:
                logger.error(f"Error generating content for spec {spec}: {e}")
        
        return generated_content
    
    def optimize_for_timing(self, content: GeneratedContent, posting_day: str) -> GeneratedContent:
        """Optimize content for specific posting day based on audience patterns"""
        
        # Optimal content types for different days based on analysis
        day_preferences = {
            'Monday': [ContentType.CAREER_ADVICE, ContentType.INDUSTRY_OBSERVATION],
            'Tuesday': [ContentType.TECHNICAL_INSIGHT, ContentType.PRODUCT_MANAGEMENT],  # Optimal day
            'Wednesday': [ContentType.PERSONAL_STORY, ContentType.STARTUP_LESSONS],
            'Thursday': [ContentType.CONTROVERSIAL_TAKE, ContentType.CAREER_ADVICE],     # Optimal day
            'Friday': [ContentType.PERSONAL_STORY, ContentType.INDUSTRY_OBSERVATION],
            'Saturday': [ContentType.STARTUP_LESSONS, ContentType.PERSONAL_STORY],
            'Sunday': [ContentType.CAREER_ADVICE, ContentType.TECHNICAL_INSIGHT]
        }
        
        preferred_types = day_preferences.get(posting_day, [])
        
        # If content type is not optimal for the day, add a note
        if content.content_type not in preferred_types:
            optimization_note = f"\nNote: {content.content_type.value} content typically performs better on other days. Consider adjusting posting schedule or content type for maximum engagement."
            content.generation_metadata['timing_optimization'] = optimization_note
        
        return content