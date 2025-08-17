"""Viral Prediction ML Engine for Epic 7.1 - Predicting engagement and viral potential of content."""

import logging
import re
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

from graph_rag.core.concept_extractor import ConceptualEntity, LinkedInConceptExtractor

logger = logging.getLogger(__name__)


class Platform(Enum):
    """Supported social media platforms."""
    LINKEDIN = "linkedin"
    TWITTER = "twitter"
    GENERAL = "general"


class ContentType(Enum):
    """Types of content for viral prediction."""
    HOT_TAKE = "hot_take"
    BELIEF = "belief"
    INSIGHT = "insight"
    STORY = "story"
    QUESTION = "question"
    ADVICE = "advice"
    CONTROVERSY = "controversy"


class RiskLevel(Enum):
    """Risk levels for viral content."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    EXTREME = "extreme"


@dataclass
class ViralMetrics:
    """Core metrics for viral prediction."""
    engagement_score: float  # 0.0 - 1.0
    reach_potential: float   # 0.0 - 1.0
    viral_velocity: float    # 0.0 - 1.0
    controversy_score: float # 0.0 - 1.0
    sentiment_strength: float # -1.0 to 1.0
    platform_fit: float     # 0.0 - 1.0


@dataclass
class TemporalFactors:
    """Time-based factors affecting virality."""
    trending_topic_boost: float  # 0.0 - 1.0
    time_of_day_score: float    # 0.0 - 1.0
    day_of_week_score: float    # 0.0 - 1.0
    seasonal_relevance: float   # 0.0 - 1.0
    recency_factor: float       # 0.0 - 1.0


class ViralPrediction(BaseModel):
    """Complete viral prediction result."""
    content_id: str
    platform: Platform
    content_type: ContentType

    # Core metrics
    engagement_score: float = Field(ge=0.0, le=1.0, description="Predicted engagement rate")
    reach_potential: float = Field(ge=0.0, le=1.0, description="Potential audience reach")
    viral_velocity: float = Field(ge=0.0, le=1.0, description="Speed of content spread")
    controversy_score: float = Field(ge=0.0, le=1.0, description="Controversial content score")

    # Combined scores
    overall_viral_score: float = Field(ge=0.0, le=1.0, description="Overall viral potential")
    risk_adjusted_score: float = Field(ge=0.0, le=1.0, description="Viral score adjusted for risk")
    confidence: float = Field(ge=0.0, le=1.0, description="Prediction confidence")

    # Risk assessment
    risk_level: RiskLevel
    risk_factors: list[str] = Field(default_factory=list, description="Identified risk factors")

    # Temporal factors
    temporal_boost: float = Field(ge=0.0, le=1.0, description="Time-based boost factor")
    optimal_posting_time: datetime | None = Field(default=None, description="Suggested posting time")

    # Feature insights
    key_features: list[str] = Field(default_factory=list, description="Key features driving prediction")
    improvement_suggestions: list[str] = Field(default_factory=list, description="Content improvement suggestions")

    # Platform-specific metrics
    platform_optimization_score: float = Field(ge=0.0, le=1.0, description="Platform optimization score")
    expected_engagement_rate: float = Field(ge=0.0, le=1.0, description="Expected engagement rate")

    created_at: datetime = Field(default_factory=datetime.utcnow)


class ViralFeatureExtractor:
    """Extracts features for viral prediction from content."""

    def __init__(self):
        self.concept_extractor = LinkedInConceptExtractor()

    async def extract_features(self, text: str, platform: Platform = Platform.GENERAL,
                             context: dict[str, Any] = None) -> dict[str, Any]:
        """Extract comprehensive features for viral prediction."""
        features = {}

        # Basic text features
        features.update(self._extract_text_features(text))

        # Linguistic features
        features.update(self._extract_linguistic_features(text))

        # Emotional features
        features.update(self._extract_emotional_features(text))

        # Concept features
        concepts = await self.concept_extractor.extract_concepts(text, context)
        features.update(self._extract_concept_features(concepts))

        # Platform-specific features
        features.update(self._extract_platform_features(text, platform))

        # Engagement features
        features.update(self._extract_engagement_features(text))

        # Temporal features
        features.update(self._extract_temporal_features(text, context))

        # Content type classification
        features['content_type'] = self._classify_content_type(text, concepts)

        return features

    def _extract_text_features(self, text: str) -> dict[str, Any]:
        """Extract basic text statistics."""
        words = text.split()
        sentences = text.split('.')

        return {
            'text_length': len(text),
            'word_count': len(words),
            'sentence_count': len(sentences),
            'avg_word_length': sum(len(word) for word in words) / max(len(words), 1),
            'avg_sentence_length': len(words) / max(len(sentences), 1),
            'readability_score': self._calculate_readability_score(text),
            'exclamation_count': text.count('!'),
            'question_count': text.count('?'),
            'uppercase_ratio': sum(1 for c in text if c.isupper()) / max(len(text), 1),
            'emoji_count': self._count_emojis(text),
            'hashtag_count': text.count('#'),
            'mention_count': text.count('@'),
            'url_count': len(re.findall(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', text))
        }

    def _extract_linguistic_features(self, text: str) -> dict[str, Any]:
        """Extract linguistic patterns that influence virality."""
        text_lower = text.lower()

        # Power words and trigger phrases
        power_words = [
            'secret', 'proven', 'guaranteed', 'amazing', 'incredible', 'shocking',
            'revolutionary', 'breakthrough', 'exclusive', 'insider', 'banned',
            'forbidden', 'controversial', 'truth', 'exposed', 'revealed'
        ]

        urgency_words = [
            'now', 'today', 'immediately', 'urgent', 'hurry', 'limited',
            'expires', 'deadline', 'last chance', 'act fast', 'don\'t wait'
        ]

        social_proof_phrases = [
            'everyone is', 'most people', 'thousands of', 'millions of',
            'studies show', 'experts agree', 'scientists confirm', 'proven by'
        ]

        curiosity_gaps = [
            'you won\'t believe', 'what happened next', 'the result will',
            'here\'s why', 'the reason', 'what nobody tells you',
            'the truth about', 'what really happens'
        ]

        return {
            'power_word_count': sum(1 for word in power_words if word in text_lower),
            'urgency_word_count': sum(1 for word in urgency_words if word in text_lower),
            'social_proof_count': sum(1 for phrase in social_proof_phrases if phrase in text_lower),
            'curiosity_gap_count': sum(1 for phrase in curiosity_gaps if phrase in text_lower),
            'personal_pronoun_count': len(re.findall(r'\b(i|me|my|we|us|our|you|your)\b', text_lower)),
            'superlative_count': len(re.findall(r'\b(best|worst|most|least|biggest|smallest|fastest|slowest)\b', text_lower)),
            'number_count': len(re.findall(r'\b\d+\b', text)),
            'list_indicators': len(re.findall(r'\b(\d+\s*(reasons|ways|tips|secrets|steps|methods))\b', text_lower))
        }

    def _extract_emotional_features(self, text: str) -> dict[str, Any]:
        """Extract emotional content indicators."""
        text_lower = text.lower()

        # Emotion word categories
        positive_emotions = [
            'happy', 'excited', 'amazing', 'fantastic', 'wonderful', 'brilliant',
            'thrilled', 'grateful', 'blessed', 'inspired', 'motivated', 'proud'
        ]

        negative_emotions = [
            'angry', 'frustrated', 'disappointed', 'terrible', 'awful', 'horrible',
            'disgusted', 'outraged', 'furious', 'devastated', 'heartbroken', 'shocked'
        ]

        controversial_emotions = [
            'controversial', 'provocative', 'divisive', 'polarizing', 'debatable',
            'contentious', 'disputed', 'questionable', 'radical', 'extreme'
        ]

        fear_uncertainty = [
            'scared', 'worried', 'concerned', 'afraid', 'anxious', 'nervous',
            'uncertain', 'confused', 'doubt', 'hesitant', 'skeptical', 'wary'
        ]

        return {
            'positive_emotion_count': sum(1 for word in positive_emotions if word in text_lower),
            'negative_emotion_count': sum(1 for word in negative_emotions if word in text_lower),
            'controversial_emotion_count': sum(1 for word in controversial_emotions if word in text_lower),
            'fear_uncertainty_count': sum(1 for word in fear_uncertainty if word in text_lower),
            'emotion_intensity': self._calculate_emotion_intensity(text),
            'sentiment_polarity': self._calculate_sentiment_polarity(text),
            'emotional_volatility': self._calculate_emotional_volatility(text)
        }

    def _extract_concept_features(self, concepts: list[ConceptualEntity]) -> dict[str, Any]:
        """Extract features from conceptual entities."""
        if not concepts:
            return {
                'concept_count': 0,
                'hot_take_count': 0,
                'belief_count': 0,
                'avg_concept_confidence': 0.0,
                'max_engagement_potential': 0.0,
                'controversy_concept_count': 0
            }

        hot_takes = [c for c in concepts if c.concept_type == 'HOT_TAKE']
        beliefs = [c for c in concepts if c.concept_type == 'BELIEF']
        controversial = [c for c in concepts if c.sentiment == 'controversial']

        engagement_potentials = [
            float(c.properties.get('engagement_potential', 0.0))
            for c in concepts
            if 'engagement_potential' in c.properties
        ]

        return {
            'concept_count': len(concepts),
            'hot_take_count': len(hot_takes),
            'belief_count': len(beliefs),
            'avg_concept_confidence': sum(c.confidence for c in concepts) / len(concepts),
            'max_engagement_potential': max(engagement_potentials) if engagement_potentials else 0.0,
            'avg_engagement_potential': sum(engagement_potentials) / len(engagement_potentials) if engagement_potentials else 0.0,
            'controversy_concept_count': len(controversial),
            'unique_concept_types': len(set(c.concept_type for c in concepts))
        }

    def _extract_platform_features(self, text: str, platform: Platform) -> dict[str, Any]:
        """Extract platform-specific features."""
        features = {'platform': platform.value}

        if platform == Platform.LINKEDIN:
            features.update(self._extract_linkedin_features(text))
        elif platform == Platform.TWITTER:
            features.update(self._extract_twitter_features(text))

        return features

    def _extract_linkedin_features(self, text: str) -> dict[str, Any]:
        """Extract LinkedIn-specific features."""
        text_lower = text.lower()

        professional_terms = [
            'leadership', 'career', 'business', 'professional', 'industry',
            'networking', 'growth', 'success', 'strategy', 'innovation',
            'experience', 'insights', 'lessons', 'skills', 'expertise'
        ]

        linkedin_engagement_patterns = [
            'what do you think', 'share your thoughts', 'comment below',
            'tag someone', 'agree or disagree', 'your experience',
            'thoughts on this', 'what\'s your take'
        ]

        return {
            'professional_term_count': sum(1 for term in professional_terms if term in text_lower),
            'linkedin_engagement_pattern_count': sum(1 for pattern in linkedin_engagement_patterns if pattern in text_lower),
            'story_format': 1 if any(phrase in text_lower for phrase in ['story time', 'here\'s what happened', 'experience taught me']) else 0,
            'lesson_format': 1 if any(phrase in text_lower for phrase in ['lesson learned', 'key takeaway', 'what i learned']) else 0,
            'poll_potential': 1 if '?' in text and any(word in text_lower for word in ['opinion', 'think', 'prefer', 'choose']) else 0
        }

    def _extract_twitter_features(self, text: str) -> dict[str, Any]:
        """Extract Twitter-specific features."""
        return {
            'thread_potential': 1 if len(text) > 280 else 0,
            'retweet_potential': self._calculate_retweet_potential(text),
            'trending_hashtag_score': self._calculate_trending_hashtag_score(text),
            'meme_potential': self._calculate_meme_potential(text)
        }

    def _extract_engagement_features(self, text: str) -> dict[str, Any]:
        """Extract features that drive engagement."""
        text_lower = text.lower()

        # Call-to-action patterns
        cta_patterns = [
            'what do you think', 'share your', 'tell me', 'comment below',
            'let me know', 'your thoughts', 'what\'s your', 'do you agree',
            'have you ever', 'anyone else', 'am i wrong', 'change my mind'
        ]

        # Question patterns
        question_patterns = [
            'how do you', 'what would you', 'why do you think', 'when was the last time',
            'where do you', 'which do you prefer', 'who else', 'what if'
        ]

        # Relatability patterns
        relatability_patterns = [
            'anyone else', 'we\'ve all', 'you know that feeling', 'happens to everyone',
            'can relate', 'we all know', 'everyone has', 'we\'ve been there'
        ]

        return {
            'cta_count': sum(1 for pattern in cta_patterns if pattern in text_lower),
            'question_pattern_count': sum(1 for pattern in question_patterns if pattern in text_lower),
            'relatability_score': sum(1 for pattern in relatability_patterns if pattern in text_lower),
            'controversy_potential': self._calculate_controversy_potential(text),
            'shareability_score': self._calculate_shareability_score(text),
            'discussion_potential': self._calculate_discussion_potential(text)
        }

    def _extract_temporal_features(self, text: str, context: dict[str, Any] = None) -> dict[str, Any]:
        """Extract time-sensitive features."""
        current_time = datetime.utcnow()

        # Time-sensitive words
        time_sensitive_words = [
            'today', 'now', 'currently', 'this week', 'lately', 'recently',
            'just happened', 'breaking', 'update', 'latest', 'new'
        ]

        return {
            'time_sensitivity': sum(1 for word in time_sensitive_words if word in text.lower()),
            'optimal_hour': self._calculate_optimal_posting_hour(current_time),
            'day_of_week_score': self._calculate_day_of_week_score(current_time),
            'trending_topic_relevance': self._calculate_trending_topic_relevance(text, context)
        }

    def _classify_content_type(self, text: str, concepts: list[ConceptualEntity]) -> ContentType:
        """Classify the type of content for targeted prediction."""
        text_lower = text.lower()

        # Check concepts first
        if any(c.concept_type == 'HOT_TAKE' for c in concepts):
            return ContentType.HOT_TAKE

        if any(c.concept_type == 'BELIEF' for c in concepts):
            return ContentType.BELIEF

        # Pattern-based classification
        if any(phrase in text_lower for phrase in ['unpopular opinion', 'hot take', 'controversial']):
            return ContentType.CONTROVERSY

        if '?' in text and any(word in text_lower for word in ['what', 'how', 'why', 'when', 'where']):
            return ContentType.QUESTION

        if any(phrase in text_lower for phrase in ['story time', 'happened to me', 'experience']):
            return ContentType.STORY

        if any(phrase in text_lower for phrase in ['tip', 'advice', 'should', 'recommend']):
            return ContentType.ADVICE

        if any(phrase in text_lower for phrase in ['insight', 'learned', 'realized', 'discovery']):
            return ContentType.INSIGHT

        return ContentType.INSIGHT  # Default

    # Helper methods for feature calculation
    def _calculate_readability_score(self, text: str) -> float:
        """Simple readability score (0-1, higher = more readable)."""
        words = text.split()
        if not words:
            return 0.0

        avg_word_length = sum(len(word) for word in words) / len(words)
        sentences = text.split('.')
        avg_sentence_length = len(words) / max(len(sentences), 1)

        # Simplified readability (inverse of complexity)
        complexity = (avg_word_length * 0.5) + (avg_sentence_length * 0.1)
        return max(0.0, min(1.0, 1.0 - (complexity / 20.0)))

    def _count_emojis(self, text: str) -> int:
        """Count emoji characters in text."""
        # Simple emoji detection - in a real implementation, use proper Unicode categories
        emoji_pattern = re.compile(r'[\U0001F600-\U0001F64F]|[\U0001F300-\U0001F5FF]|[\U0001F680-\U0001F6FF]|[\U0001F1E0-\U0001F1FF]')
        return len(emoji_pattern.findall(text))

    def _calculate_emotion_intensity(self, text: str) -> float:
        """Calculate overall emotional intensity of text."""
        # Simplified implementation
        intensity_markers = ['!', '!!', '!!!', 'very', 'extremely', 'incredibly', 'absolutely']
        score = sum(text.count(marker) for marker in intensity_markers)
        return min(1.0, score / 10.0)

    def _calculate_sentiment_polarity(self, text: str) -> float:
        """Calculate sentiment polarity (-1 to 1)."""
        # Simplified sentiment analysis
        positive_words = ['good', 'great', 'amazing', 'excellent', 'wonderful', 'fantastic', 'love', 'happy']
        negative_words = ['bad', 'terrible', 'awful', 'horrible', 'hate', 'angry', 'frustrated', 'disappointed']

        text_lower = text.lower()
        positive_count = sum(1 for word in positive_words if word in text_lower)
        negative_count = sum(1 for word in negative_words if word in text_lower)

        total = positive_count + negative_count
        if total == 0:
            return 0.0

        return (positive_count - negative_count) / total

    def _calculate_emotional_volatility(self, text: str) -> float:
        """Calculate emotional volatility (rapid emotional changes)."""
        # Simplified implementation - in reality, would analyze emotional transitions
        mixed_indicators = ['but', 'however', 'although', 'despite', 'yet', 'still']
        text_lower = text.lower()
        return min(1.0, sum(1 for indicator in mixed_indicators if indicator in text_lower) / 5.0)

    def _calculate_controversy_potential(self, text: str) -> float:
        """Calculate how controversial the content might be."""
        controversial_markers = [
            'disagree', 'wrong', 'shouldn\'t', 'never', 'always', 'all',
            'everyone', 'nobody', 'controversial', 'unpopular', 'against'
        ]
        text_lower = text.lower()
        score = sum(1 for marker in controversial_markers if marker in text_lower)
        return min(1.0, score / 5.0)

    def _calculate_shareability_score(self, text: str) -> float:
        """Calculate how likely content is to be shared."""
        shareable_elements = [
            'share', 'repost', 'spread the word', 'tell everyone', 'everyone needs to know',
            'quote', 'wisdom', 'truth', 'important', 'must read'
        ]
        text_lower = text.lower()
        score = sum(1 for element in shareable_elements if element in text_lower)
        return min(1.0, score / 3.0)

    def _calculate_discussion_potential(self, text: str) -> float:
        """Calculate potential for generating discussion."""
        discussion_triggers = [
            '?', 'what do you think', 'opinions', 'debate', 'discuss',
            'thoughts', 'experience', 'perspective', 'view', 'take on this'
        ]
        text_lower = text.lower()
        score = sum(1 for trigger in discussion_triggers if trigger in text_lower)
        return min(1.0, score / 3.0)

    def _calculate_retweet_potential(self, text: str) -> float:
        """Calculate Twitter retweet potential."""
        # Simplified Twitter-specific shareability
        return min(1.0, (self._calculate_shareability_score(text) + self._calculate_controversy_potential(text)) / 2.0)

    def _calculate_trending_hashtag_score(self, text: str) -> float:
        """Calculate score based on trending hashtags (mock implementation)."""
        hashtags = re.findall(r'#\w+', text)
        # In real implementation, would check against current trending hashtags
        return min(1.0, len(hashtags) / 3.0)

    def _calculate_meme_potential(self, text: str) -> float:
        """Calculate meme potential."""
        meme_indicators = [
            'when you', 'that moment when', 'me:', 'nobody:', 'everyone:',
            'meanwhile', 'pov:', 'imagine', 'be like'
        ]
        text_lower = text.lower()
        score = sum(1 for indicator in meme_indicators if indicator in text_lower)
        return min(1.0, score / 2.0)

    def _calculate_optimal_posting_hour(self, current_time: datetime) -> float:
        """Calculate optimal posting hour score (0-1)."""
        hour = current_time.hour
        # Peak engagement hours: 8-10 AM, 12-2 PM, 5-7 PM
        peak_hours = [8, 9, 10, 12, 13, 14, 17, 18, 19]
        return 1.0 if hour in peak_hours else 0.5

    def _calculate_day_of_week_score(self, current_time: datetime) -> float:
        """Calculate day of week engagement score."""
        # Tuesday-Thursday typically have higher engagement
        weekday = current_time.weekday()  # 0=Monday, 6=Sunday
        if weekday in [1, 2, 3]:  # Tuesday, Wednesday, Thursday
            return 1.0
        elif weekday in [0, 4]:  # Monday, Friday
            return 0.8
        else:  # Weekend
            return 0.6

    def _calculate_trending_topic_relevance(self, text: str, context: dict[str, Any] = None) -> float:
        """Calculate relevance to trending topics (mock implementation)."""
        # In real implementation, would check against current trending topics API
        trending_keywords = ['AI', 'climate', 'remote work', 'startup', 'innovation']
        text_lower = text.lower()
        score = sum(1 for keyword in trending_keywords if keyword.lower() in text_lower)
        return min(1.0, score / 2.0)


class ViralPredictionModel:
    """Mock ML model for viral prediction."""

    def __init__(self):
        # In a real implementation, these would be trained model weights
        self.engagement_weights = {
            'cta_count': 0.15,
            'question_pattern_count': 0.12,
            'personal_pronoun_count': 0.08,
            'emotion_intensity': 0.10,
            'controversy_potential': 0.13,
            'shareability_score': 0.11,
            'hot_take_count': 0.09,
            'avg_engagement_potential': 0.12,
            'professional_term_count': 0.05,
            'relatability_score': 0.05
        }

        self.reach_weights = {
            'shareability_score': 0.20,
            'controversy_potential': 0.15,
            'trending_topic_relevance': 0.15,
            'social_proof_count': 0.10,
            'power_word_count': 0.10,
            'hashtag_count': 0.08,
            'mention_count': 0.07,
            'platform_optimization_score': 0.15
        }

        self.velocity_weights = {
            'urgency_word_count': 0.18,
            'time_sensitivity': 0.15,
            'emotion_intensity': 0.12,
            'controversy_potential': 0.12,
            'curiosity_gap_count': 0.10,
            'hot_take_count': 0.10,
            'trending_topic_relevance': 0.13,
            'discussion_potential': 0.10
        }

        self.controversy_weights = {
            'controversial_emotion_count': 0.20,
            'controversy_potential': 0.18,
            'hot_take_count': 0.15,
            'negative_emotion_count': 0.12,
            'superlative_count': 0.10,
            'emotional_volatility': 0.10,
            'fear_uncertainty_count': 0.08,
            'controversy_concept_count': 0.07
        }

    def predict_engagement(self, features: dict[str, Any]) -> float:
        """Predict engagement score based on features."""
        score = 0.0
        total_weight = 0.0

        for feature, weight in self.engagement_weights.items():
            if feature in features:
                value = features[feature]
                if isinstance(value, (int, float)):
                    # Normalize feature values
                    normalized_value = min(1.0, float(value) / 10.0) if feature.endswith('_count') else float(value)
                    score += normalized_value * weight
                    total_weight += weight

        # Normalize by total weight used
        return min(1.0, score / max(total_weight, 0.1))

    def predict_reach(self, features: dict[str, Any]) -> float:
        """Predict reach potential based on features."""
        score = 0.0
        total_weight = 0.0

        for feature, weight in self.reach_weights.items():
            if feature in features:
                value = features[feature]
                if isinstance(value, (int, float)):
                    normalized_value = min(1.0, float(value) / 5.0) if feature.endswith('_count') else float(value)
                    score += normalized_value * weight
                    total_weight += weight

        return min(1.0, score / max(total_weight, 0.1))

    def predict_velocity(self, features: dict[str, Any]) -> float:
        """Predict viral velocity based on features."""
        score = 0.0
        total_weight = 0.0

        for feature, weight in self.velocity_weights.items():
            if feature in features:
                value = features[feature]
                if isinstance(value, (int, float)):
                    normalized_value = min(1.0, float(value) / 3.0) if feature.endswith('_count') else float(value)
                    score += normalized_value * weight
                    total_weight += weight

        return min(1.0, score / max(total_weight, 0.1))

    def predict_controversy(self, features: dict[str, Any]) -> float:
        """Predict controversy score based on features."""
        score = 0.0
        total_weight = 0.0

        for feature, weight in self.controversy_weights.items():
            if feature in features:
                value = features[feature]
                if isinstance(value, (int, float)):
                    normalized_value = min(1.0, float(value) / 3.0) if feature.endswith('_count') else float(value)
                    score += normalized_value * weight
                    total_weight += weight

        return min(1.0, score / max(total_weight, 0.1))


class ViralPredictionEngine:
    """Main engine for predicting viral potential of content."""

    def __init__(self):
        self.feature_extractor = ViralFeatureExtractor()
        self.model = ViralPredictionModel()

        # Configuration parameters
        self.platform_weights = {
            Platform.LINKEDIN: {'engagement': 1.0, 'reach': 0.8, 'velocity': 0.7, 'controversy': 0.6},
            Platform.TWITTER: {'engagement': 0.9, 'reach': 1.0, 'velocity': 1.0, 'controversy': 0.9},
            Platform.GENERAL: {'engagement': 0.8, 'reach': 0.8, 'velocity': 0.8, 'controversy': 0.7}
        }

        self.risk_thresholds = {
            RiskLevel.LOW: 0.3,
            RiskLevel.MEDIUM: 0.6,
            RiskLevel.HIGH: 0.8,
            RiskLevel.EXTREME: 1.0
        }

    async def predict_viral_potential(self, text: str, platform: Platform = Platform.GENERAL,
                                    content_id: str = None, context: dict[str, Any] = None) -> ViralPrediction:
        """Main method to predict viral potential of content."""
        try:
            # Generate unique content ID if not provided
            if content_id is None:
                content_id = f"content_{hash(text[:100])}_{int(datetime.utcnow().timestamp())}"

            # Extract features
            features = await self.feature_extractor.extract_features(text, platform, context)

            # Get base predictions from model
            engagement_score = self.model.predict_engagement(features)
            reach_potential = self.model.predict_reach(features)
            viral_velocity = self.model.predict_velocity(features)
            controversy_score = self.model.predict_controversy(features)

            # Apply platform-specific adjustments
            platform_weights = self.platform_weights[platform]
            engagement_score *= platform_weights['engagement']
            reach_potential *= platform_weights['reach']
            viral_velocity *= platform_weights['velocity']
            controversy_score *= platform_weights['controversy']

            # Calculate temporal factors
            temporal_factors = self._calculate_temporal_factors(features, context)
            temporal_boost = temporal_factors.trending_topic_boost * 0.3 + temporal_factors.time_of_day_score * 0.2 + \
                           temporal_factors.day_of_week_score * 0.2 + temporal_factors.seasonal_relevance * 0.2 + \
                           temporal_factors.recency_factor * 0.1

            # Calculate overall viral score
            overall_viral_score = self._calculate_overall_score(
                engagement_score, reach_potential, viral_velocity, controversy_score, temporal_boost
            )

            # Risk assessment
            risk_level, risk_factors = self._assess_risk(features, controversy_score)
            risk_adjusted_score = self._apply_risk_adjustment(overall_viral_score, risk_level)

            # Calculate confidence
            confidence = self._calculate_confidence(features)

            # Platform optimization
            platform_optimization_score = self._calculate_platform_optimization(features, platform)

            # Expected engagement rate
            expected_engagement_rate = self._calculate_expected_engagement_rate(
                engagement_score, platform, features
            )

            # Key features and suggestions
            key_features = self._identify_key_features(features)
            improvement_suggestions = self._generate_improvement_suggestions(features, platform)

            # Optimal posting time
            optimal_posting_time = self._calculate_optimal_posting_time(temporal_factors)

            return ViralPrediction(
                content_id=content_id,
                platform=platform,
                content_type=features['content_type'],
                engagement_score=engagement_score,
                reach_potential=reach_potential,
                viral_velocity=viral_velocity,
                controversy_score=controversy_score,
                overall_viral_score=overall_viral_score,
                risk_adjusted_score=risk_adjusted_score,
                confidence=confidence,
                risk_level=risk_level,
                risk_factors=risk_factors,
                temporal_boost=temporal_boost,
                optimal_posting_time=optimal_posting_time,
                key_features=key_features,
                improvement_suggestions=improvement_suggestions,
                platform_optimization_score=platform_optimization_score,
                expected_engagement_rate=expected_engagement_rate
            )

        except Exception as e:
            logger.error(f"Error in viral prediction: {str(e)}")
            # Return safe default prediction
            return self._create_default_prediction(content_id or "unknown", platform, text)

    async def batch_predict(self, content_items: list[tuple[str, Platform, str]],
                          context: dict[str, Any] = None) -> list[ViralPrediction]:
        """Predict viral potential for multiple content items."""
        predictions = []

        for text, platform, content_id in content_items:
            try:
                prediction = await self.predict_viral_potential(text, platform, content_id, context)
                predictions.append(prediction)
            except Exception as e:
                logger.error(f"Error predicting for content {content_id}: {str(e)}")
                predictions.append(self._create_default_prediction(content_id, platform, text))

        return predictions

    async def optimize_for_platform(self, text: str, target_platform: Platform,
                                  context: dict[str, Any] = None) -> dict[str, Any]:
        """Provide platform-specific optimization recommendations."""
        features = await self.feature_extractor.extract_features(text, target_platform, context)

        if target_platform == Platform.LINKEDIN:
            return self._generate_linkedin_optimizations(text, features)
        elif target_platform == Platform.TWITTER:
            return self._generate_twitter_optimizations(text, features)
        else:
            return self._generate_general_optimizations(text, features)

    def _calculate_temporal_factors(self, features: dict[str, Any],
                                  context: dict[str, Any] = None) -> TemporalFactors:
        """Calculate temporal factors affecting virality."""
        return TemporalFactors(
            trending_topic_boost=features.get('trending_topic_relevance', 0.0),
            time_of_day_score=features.get('optimal_hour', 0.5),
            day_of_week_score=features.get('day_of_week_score', 0.7),
            seasonal_relevance=0.7,  # Mock seasonal relevance
            recency_factor=1.0  # Assume current content
        )

    def _calculate_overall_score(self, engagement: float, reach: float, velocity: float,
                               controversy: float, temporal_boost: float) -> float:
        """Calculate overall viral score from component scores."""
        # Weighted combination of scores
        base_score = (engagement * 0.3 + reach * 0.25 + velocity * 0.25 + controversy * 0.2)

        # Apply temporal boost
        boosted_score = base_score * (1.0 + temporal_boost * 0.3)

        return min(1.0, boosted_score)

    def _assess_risk(self, features: dict[str, Any], controversy_score: float) -> tuple[RiskLevel, list[str]]:
        """Assess risk level and identify risk factors."""
        risk_factors = []
        risk_score = 0.0

        # Controversy-based risk
        if controversy_score > 0.7:
            risk_factors.append("High controversy potential")
            risk_score += 0.3

        # Emotional volatility risk
        if features.get('emotional_volatility', 0.0) > 0.6:
            risk_factors.append("High emotional volatility")
            risk_score += 0.2

        # Negative emotion risk
        if features.get('negative_emotion_count', 0) > 3:
            risk_factors.append("High negative emotion content")
            risk_score += 0.2

        # Fear/uncertainty risk
        if features.get('fear_uncertainty_count', 0) > 2:
            risk_factors.append("Fear and uncertainty content")
            risk_score += 0.15

        # Hot take risk
        if features.get('hot_take_count', 0) > 1:
            risk_factors.append("Multiple hot takes")
            risk_score += 0.15

        # Determine risk level
        if risk_score >= 0.8:
            risk_level = RiskLevel.EXTREME
        elif risk_score >= 0.6:
            risk_level = RiskLevel.HIGH
        elif risk_score >= 0.3:
            risk_level = RiskLevel.MEDIUM
        else:
            risk_level = RiskLevel.LOW

        return risk_level, risk_factors

    def _apply_risk_adjustment(self, viral_score: float, risk_level: RiskLevel) -> float:
        """Apply risk adjustment to viral score."""
        risk_multipliers = {
            RiskLevel.LOW: 1.0,
            RiskLevel.MEDIUM: 0.9,
            RiskLevel.HIGH: 0.7,
            RiskLevel.EXTREME: 0.5
        }

        return viral_score * risk_multipliers[risk_level]

    def _calculate_confidence(self, features: dict[str, Any]) -> float:
        """Calculate prediction confidence based on feature quality."""
        # Confidence based on feature completeness and strength
        feature_count = len([v for v in features.values() if isinstance(v, (int, float)) and v > 0])
        total_features = len(features)

        completeness = feature_count / max(total_features, 1)

        # Higher confidence for strong signals
        strong_signals = [
            features.get('hot_take_count', 0) > 0,
            features.get('cta_count', 0) > 1,
            features.get('controversy_potential', 0.0) > 0.5,
            features.get('shareability_score', 0.0) > 0.5,
            features.get('avg_engagement_potential', 0.0) > 0.7
        ]

        signal_strength = sum(strong_signals) / len(strong_signals)

        return min(1.0, (completeness * 0.6 + signal_strength * 0.4))

    def _calculate_platform_optimization(self, features: dict[str, Any], platform: Platform) -> float:
        """Calculate how well content is optimized for the platform."""
        if platform == Platform.LINKEDIN:
            return min(1.0, (
                features.get('professional_term_count', 0) / 5.0 * 0.3 +
                features.get('linkedin_engagement_pattern_count', 0) / 3.0 * 0.3 +
                features.get('story_format', 0) * 0.2 +
                features.get('lesson_format', 0) * 0.2
            ))
        elif platform == Platform.TWITTER:
            return min(1.0, (
                (1.0 if features.get('text_length', 0) <= 280 else 0.5) * 0.4 +
                features.get('hashtag_count', 0) / 3.0 * 0.3 +
                features.get('meme_potential', 0.0) * 0.3
            ))
        else:
            return 0.7  # Default platform optimization

    def _calculate_expected_engagement_rate(self, engagement_score: float, platform: Platform,
                                          features: dict[str, Any]) -> float:
        """Calculate expected engagement rate percentage."""
        # Base rates by platform
        base_rates = {
            Platform.LINKEDIN: 0.02,  # 2% base engagement rate
            Platform.TWITTER: 0.015,  # 1.5% base engagement rate
            Platform.GENERAL: 0.01    # 1% base engagement rate
        }

        base_rate = base_rates[platform]

        # Apply engagement score multiplier
        multiplier = 1.0 + (engagement_score * 4.0)  # Can multiply up to 5x

        return min(0.15, base_rate * multiplier)  # Cap at 15% engagement rate

    def _identify_key_features(self, features: dict[str, Any]) -> list[str]:
        """Identify the key features driving the prediction."""
        key_features = []

        # Check for high-impact features
        if features.get('hot_take_count', 0) > 0:
            key_features.append("Contains hot takes")

        if features.get('cta_count', 0) > 1:
            key_features.append("Multiple call-to-action elements")

        if features.get('controversy_potential', 0.0) > 0.6:
            key_features.append("High controversy potential")

        if features.get('question_pattern_count', 0) > 0:
            key_features.append("Engaging question patterns")

        if features.get('emotion_intensity', 0.0) > 0.7:
            key_features.append("High emotional intensity")

        if features.get('shareability_score', 0.0) > 0.6:
            key_features.append("High shareability score")

        if features.get('trending_topic_relevance', 0.0) > 0.5:
            key_features.append("Relevant to trending topics")

        return key_features[:5]  # Return top 5 features

    def _generate_improvement_suggestions(self, features: dict[str, Any],
                                        platform: Platform) -> list[str]:
        """Generate content improvement suggestions."""
        suggestions = []

        # General suggestions
        if features.get('cta_count', 0) == 0:
            suggestions.append("Add a call-to-action to encourage engagement")

        if features.get('question_count', 0) == 0:
            suggestions.append("Consider adding a thought-provoking question")

        if features.get('emotion_intensity', 0.0) < 0.3:
            suggestions.append("Increase emotional appeal with stronger language")

        if features.get('personal_pronoun_count', 0) == 0:
            suggestions.append("Make it more personal by using 'I', 'you', or 'we'")

        # Platform-specific suggestions
        if platform == Platform.LINKEDIN:
            if features.get('professional_term_count', 0) < 2:
                suggestions.append("Include more professional terminology")

            if features.get('story_format', 0) == 0:
                suggestions.append("Consider framing as a professional story or experience")

        elif platform == Platform.TWITTER:
            if features.get('hashtag_count', 0) == 0:
                suggestions.append("Add relevant hashtags to increase discoverability")

            if features.get('text_length', 0) > 280:
                suggestions.append("Consider breaking into a thread for Twitter")

        return suggestions[:4]  # Return top 4 suggestions

    def _calculate_optimal_posting_time(self, temporal_factors: TemporalFactors) -> datetime | None:
        """Calculate optimal posting time based on temporal factors."""
        current_time = datetime.utcnow()

        # Find next optimal hour (mock implementation)
        optimal_hours = [9, 13, 18]  # 9 AM, 1 PM, 6 PM UTC

        for hour in optimal_hours:
            optimal_time = current_time.replace(hour=hour, minute=0, second=0, microsecond=0)
            if optimal_time > current_time:
                return optimal_time

        # Next day's first optimal time
        next_day = current_time + timedelta(days=1)
        return next_day.replace(hour=9, minute=0, second=0, microsecond=0)

    def _generate_linkedin_optimizations(self, text: str, features: dict[str, Any]) -> dict[str, Any]:
        """Generate LinkedIn-specific optimizations."""
        return {
            'platform': 'LinkedIn',
            'optimizations': [
                'Add professional context or industry relevance',
                'Include a clear call-to-action for comments',
                'Consider adding a relevant professional story',
                'Use industry-specific hashtags',
                'Mention your experience or credentials'
            ],
            'ideal_length': '1300-1600 characters',
            'best_posting_times': ['8-10 AM', '12-2 PM', '5-7 PM'],
            'engagement_tactics': [
                'Ask for others\' experiences',
                'Share a professional lesson learned',
                'Tag relevant colleagues or mentors',
                'Create a poll for engagement'
            ]
        }

    def _generate_twitter_optimizations(self, text: str, features: dict[str, Any]) -> dict[str, Any]:
        """Generate Twitter-specific optimizations."""
        return {
            'platform': 'Twitter',
            'optimizations': [
                'Keep under 280 characters or create a thread',
                'Add 2-3 relevant hashtags',
                'Include visual elements if possible',
                'Use Twitter-friendly language and tone',
                'Consider timing for your audience timezone'
            ],
            'ideal_length': '71-100 characters (optimal) or thread',
            'best_posting_times': ['9 AM', '12 PM', '3 PM', '6 PM'],
            'engagement_tactics': [
                'Ask a direct question',
                'Use controversial but respectful takes',
                'Reply to trending conversations',
                'Create quotable moments'
            ]
        }

    def _generate_general_optimizations(self, text: str, features: dict[str, Any]) -> dict[str, Any]:
        """Generate general platform optimizations."""
        return {
            'platform': 'General',
            'optimizations': [
                'Strengthen emotional appeal',
                'Add clear value proposition',
                'Include social proof elements',
                'Make content more shareable',
                'Optimize for your target audience'
            ],
            'ideal_length': 'Platform-dependent',
            'best_posting_times': ['Peak audience hours'],
            'engagement_tactics': [
                'Create interactive content',
                'Use storytelling techniques',
                'Provide actionable insights',
                'Encourage user-generated content'
            ]
        }

    def _create_default_prediction(self, content_id: str, platform: Platform, text: str) -> ViralPrediction:
        """Create a safe default prediction when errors occur."""
        return ViralPrediction(
            content_id=content_id,
            platform=platform,
            content_type=ContentType.INSIGHT,
            engagement_score=0.3,
            reach_potential=0.3,
            viral_velocity=0.2,
            controversy_score=0.2,
            overall_viral_score=0.25,
            risk_adjusted_score=0.25,
            confidence=0.1,
            risk_level=RiskLevel.LOW,
            risk_factors=["Insufficient data for analysis"],
            temporal_boost=0.5,
            key_features=["Basic content analysis"],
            improvement_suggestions=["Add more engaging elements", "Include call-to-action"],
            platform_optimization_score=0.5,
            expected_engagement_rate=0.01
        )


# Example usage functions
async def analyze_hot_take(text: str, platform: Platform = Platform.LINKEDIN) -> ViralPrediction:
    """Quick function to analyze a hot take's viral potential."""
    engine = ViralPredictionEngine()
    return await engine.predict_viral_potential(text, platform)


async def optimize_content_for_platform(text: str, platform: Platform) -> dict[str, Any]:
    """Quick function to get platform optimization recommendations."""
    engine = ViralPredictionEngine()
    return await engine.optimize_for_platform(text, platform)


# For integration with existing systems
async def predict_viral_engagement(concepts: list[ConceptualEntity],
                                 platform: Platform = Platform.GENERAL) -> float:
    """Predict viral engagement from existing conceptual entities."""
    if not concepts:
        return 0.0

    # Convert concepts to text for analysis
    text = " ".join([c.context_window or c.text for c in concepts])

    engine = ViralPredictionEngine()
    prediction = await engine.predict_viral_potential(text, platform)

    return prediction.overall_viral_score
