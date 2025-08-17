"""Audience Segmentation and Demographic Analysis Engine for Epic 8.1.

This module provides comprehensive audience intelligence capabilities including:
- Demographic segmentation (age, location, industry, job role, experience level)
- Behavioral segmentation (engagement patterns, content preferences, platform usage)
- Psychographic segmentation (values, interests, personality traits)
- Audience personas with detailed characteristics and preferences
- Segmentation scoring and confidence metrics
- Cross-platform audience analysis
- Temporal audience evolution tracking
"""

import asyncio
import logging
import math
import statistics
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Set, Tuple, Union
from dataclasses import dataclass, field
from enum import Enum
from uuid import uuid4

from pydantic import BaseModel, Field, validator

from graph_rag.core.concept_extractor import ConceptualEntity, LinkedInConceptExtractor
from graph_rag.core.viral_prediction_engine import Platform, ViralPrediction

logger = logging.getLogger(__name__)


# Enums for audience segmentation
class AgeGroup(Enum):
    """Age group segments."""
    GEN_Z = "gen_z"          # 18-24
    MILLENNIALS = "millennials"  # 25-40
    GEN_X = "gen_x"          # 41-56
    BOOMERS = "boomers"      # 57-75
    SILENT = "silent"        # 76+


class ExperienceLevel(Enum):
    """Professional experience levels."""
    ENTRY = "entry"          # 0-2 years
    JUNIOR = "junior"        # 3-5 years
    MID = "mid"              # 6-10 years
    SENIOR = "senior"        # 11-15 years
    EXECUTIVE = "executive"  # 16+ years


class Industry(Enum):
    """Industry classifications."""
    TECHNOLOGY = "technology"
    FINANCE = "finance"
    HEALTHCARE = "healthcare"
    EDUCATION = "education"
    MARKETING = "marketing"
    CONSULTING = "consulting"
    RETAIL = "retail"
    MANUFACTURING = "manufacturing"
    GOVERNMENT = "government"
    NONPROFIT = "nonprofit"
    STARTUP = "startup"
    FREELANCE = "freelance"
    OTHER = "other"


class EngagementType(Enum):
    """Types of content engagement."""
    LIKE = "like"
    COMMENT = "comment"
    SHARE = "share"
    SAVE = "save"
    CLICK = "click"
    VIEW = "view"
    FOLLOW = "follow"


class ContentPreference(Enum):
    """Content preference categories."""
    EDUCATIONAL = "educational"
    ENTERTAINMENT = "entertainment"
    NEWS = "news"
    INSPIRATIONAL = "inspirational"
    PROFESSIONAL = "professional"
    PERSONAL = "personal"
    CONTROVERSIAL = "controversial"
    TRENDING = "trending"


class PersonalityTrait(Enum):
    """Personality trait classifications."""
    ANALYTICAL = "analytical"
    CREATIVE = "creative"
    SOCIAL = "social"
    COMPETITIVE = "competitive"
    COLLABORATIVE = "collaborative"
    INNOVATIVE = "innovative"
    TRADITIONAL = "traditional"
    RISK_TAKING = "risk_taking"


# Data Models
@dataclass
class DemographicProfile:
    """Comprehensive demographic profile for audience segmentation."""
    age_group: Optional[AgeGroup] = None
    age_range: Optional[Tuple[int, int]] = None
    location: Optional[str] = None
    region: Optional[str] = None
    country: Optional[str] = None
    industry: Optional[Industry] = None
    job_title: Optional[str] = None
    job_level: Optional[ExperienceLevel] = None
    company_size: Optional[str] = None
    education_level: Optional[str] = None
    income_range: Optional[str] = None
    languages: List[str] = field(default_factory=list)
    confidence: float = 0.0


@dataclass
class BehaviorProfile:
    """Behavioral patterns and engagement preferences."""
    engagement_patterns: Dict[EngagementType, float] = field(default_factory=dict)
    content_preferences: Dict[ContentPreference, float] = field(default_factory=dict)
    platform_usage: Dict[Platform, float] = field(default_factory=dict)
    posting_frequency: float = 0.0  # posts per week
    engagement_frequency: float = 0.0  # engagements per day
    optimal_posting_times: List[int] = field(default_factory=list)  # hours of day
    content_length_preference: Optional[str] = None  # short, medium, long
    media_preferences: Dict[str, float] = field(default_factory=dict)  # text, image, video
    interaction_style: Optional[str] = None  # lurker, commenter, sharer, creator
    response_time: Optional[float] = None  # average response time in hours
    confidence: float = 0.0


@dataclass
class PsychographicProfile:
    """Psychological and value-based characteristics."""
    personality_traits: Dict[PersonalityTrait, float] = field(default_factory=dict)
    values: Dict[str, float] = field(default_factory=dict)
    interests: Dict[str, float] = field(default_factory=dict)
    motivations: Dict[str, float] = field(default_factory=dict)
    pain_points: List[str] = field(default_factory=list)
    goals: List[str] = field(default_factory=list)
    lifestyle: Dict[str, Any] = field(default_factory=dict)
    communication_style: Optional[str] = None
    decision_making_style: Optional[str] = None
    risk_tolerance: Optional[str] = None
    confidence: float = 0.0


class AudienceSegment(BaseModel):
    """Comprehensive audience segment representation."""
    id: str = Field(default_factory=lambda: str(uuid4()))
    name: str
    description: str
    
    # Core profiles
    demographic_profile: DemographicProfile
    behavior_profile: BehaviorProfile
    psychographic_profile: PsychographicProfile
    
    # Segment metrics
    size_estimate: int = Field(ge=0, description="Estimated segment size")
    confidence_score: float = Field(ge=0.0, le=1.0, description="Segment confidence")
    quality_score: float = Field(ge=0.0, le=1.0, description="Segment quality")
    
    # Engagement metrics
    engagement_potential: float = Field(ge=0.0, le=1.0, description="Predicted engagement")
    viral_potential: float = Field(ge=0.0, le=1.0, description="Viral content potential")
    conversion_likelihood: float = Field(ge=0.0, le=1.0, description="Conversion probability")
    
    # Content preferences
    preferred_content_types: List[ContentPreference] = Field(default_factory=list)
    preferred_platforms: List[Platform] = Field(default_factory=list)
    content_resonance_scores: Dict[str, float] = Field(default_factory=dict)
    
    # Temporal factors
    peak_activity_hours: List[int] = Field(default_factory=list)
    peak_activity_days: List[str] = Field(default_factory=list)
    seasonal_patterns: Dict[str, float] = Field(default_factory=dict)
    
    # Evolution tracking
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_updated: datetime = Field(default_factory=datetime.utcnow)
    evolution_trend: Optional[str] = None
    
    # Metadata
    tags: List[str] = Field(default_factory=list)
    source_data: Dict[str, Any] = Field(default_factory=dict)


class AudiencePersona(BaseModel):
    """Detailed audience persona with rich characteristics."""
    id: str = Field(default_factory=lambda: str(uuid4()))
    name: str
    avatar_description: str
    background_story: str
    
    # Core characteristics
    demographic_profile: DemographicProfile
    behavior_profile: BehaviorProfile
    psychographic_profile: PsychographicProfile
    
    # Persona details
    quote: Optional[str] = None
    day_in_life: List[str] = Field(default_factory=list)
    typical_challenges: List[str] = Field(default_factory=list)
    success_metrics: List[str] = Field(default_factory=list)
    
    # Content preferences
    content_consumption_habits: Dict[str, Any] = Field(default_factory=dict)
    preferred_communication_channels: List[str] = Field(default_factory=list)
    content_creation_behavior: Dict[str, Any] = Field(default_factory=dict)
    
    # Engagement patterns
    engagement_triggers: List[str] = Field(default_factory=list)
    content_sharing_motivations: List[str] = Field(default_factory=list)
    brand_interaction_preferences: List[str] = Field(default_factory=list)
    
    # Segment association
    primary_segment_id: Optional[str] = None
    segment_overlap_scores: Dict[str, float] = Field(default_factory=dict)
    
    # Confidence and quality
    persona_confidence: float = Field(ge=0.0, le=1.0, description="Persona accuracy")
    data_richness_score: float = Field(ge=0.0, le=1.0, description="Data completeness")
    
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_updated: datetime = Field(default_factory=datetime.utcnow)


# Analysis Engines
class DemographicAnalyzer:
    """Analyzes demographic characteristics from content and interactions."""
    
    def __init__(self):
        self.age_indicators = {
            AgeGroup.GEN_Z: [
                "tiktok", "snapchat", "vibe", "slay", "no cap", "periodt", "stan",
                "college", "university", "student", "first job", "entry level"
            ],
            AgeGroup.MILLENNIALS: [
                "avocado toast", "side hustle", "work-life balance", "millennial",
                "instagram", "facebook", "startup", "netflix", "student loans"
            ],
            AgeGroup.GEN_X: [
                "mortgage", "kids", "teenagers", "gen x", "middle management",
                "linkedin", "facebook", "career change", "experience"
            ],
            AgeGroup.BOOMERS: [
                "retirement", "grandchildren", "pension", "medicare", "boomer",
                "traditional", "established", "senior", "executive"
            ]
        }
        
        self.industry_keywords = {
            Industry.TECHNOLOGY: [
                "software", "tech", "coding", "programming", "ai", "ml", "data",
                "cloud", "devops", "engineering", "developer", "startup"
            ],
            Industry.FINANCE: [
                "finance", "banking", "investment", "trading", "fintech", "crypto",
                "accounting", "audit", "financial", "wall street"
            ],
            Industry.HEALTHCARE: [
                "healthcare", "medical", "hospital", "nursing", "doctor", "physician",
                "patient", "treatment", "therapy", "pharmaceutical"
            ],
            Industry.EDUCATION: [
                "education", "teaching", "teacher", "professor", "school", "university",
                "learning", "curriculum", "student", "academic"
            ],
            Industry.MARKETING: [
                "marketing", "advertising", "brand", "campaign", "social media",
                "content", "digital", "seo", "analytics", "creative"
            ]
        }
        
        self.experience_keywords = {
            ExperienceLevel.ENTRY: [
                "entry level", "junior", "new grad", "first job", "internship",
                "recent graduate", "starting out", "learning"
            ],
            ExperienceLevel.JUNIOR: [
                "junior", "associate", "2-3 years", "early career", "developing"
            ],
            ExperienceLevel.MID: [
                "mid-level", "experienced", "5+ years", "specialist", "lead"
            ],
            ExperienceLevel.SENIOR: [
                "senior", "expert", "10+ years", "principal", "architect"
            ],
            ExperienceLevel.EXECUTIVE: [
                "executive", "director", "vp", "ceo", "cto", "manager", "leadership"
            ]
        }
    
    async def analyze_demographics(self, text: str, context: Dict[str, Any] = None) -> DemographicProfile:
        """Analyze demographic characteristics from text content."""
        try:
            profile = DemographicProfile()
            text_lower = text.lower()
            
            # Analyze age group
            age_scores = {}
            for age_group, indicators in self.age_indicators.items():
                score = sum(1 for indicator in indicators if indicator in text_lower)
                if score > 0:
                    age_scores[age_group] = score
            
            if age_scores:
                profile.age_group = max(age_scores, key=age_scores.get)
                profile.age_range = self._get_age_range(profile.age_group)
            
            # Analyze industry
            industry_scores = {}
            for industry, keywords in self.industry_keywords.items():
                score = sum(1 for keyword in keywords if keyword in text_lower)
                if score > 0:
                    industry_scores[industry] = score
            
            if industry_scores:
                profile.industry = max(industry_scores, key=industry_scores.get)
            
            # Analyze experience level
            experience_scores = {}
            for level, keywords in self.experience_keywords.items():
                score = sum(1 for keyword in keywords if keyword in text_lower)
                if score > 0:
                    experience_scores[level] = score
            
            if experience_scores:
                profile.job_level = max(experience_scores, key=experience_scores.get)
            
            # Extract location information
            profile.location = self._extract_location(text, context)
            
            # Calculate confidence based on available data
            profile.confidence = self._calculate_demographic_confidence(profile)
            
            logger.debug(f"Demographic analysis completed with confidence: {profile.confidence}")
            return profile
            
        except Exception as e:
            logger.error(f"Error in demographic analysis: {str(e)}")
            return DemographicProfile(confidence=0.0)
    
    def _get_age_range(self, age_group: AgeGroup) -> Tuple[int, int]:
        """Get age range for age group."""
        age_ranges = {
            AgeGroup.GEN_Z: (18, 24),
            AgeGroup.MILLENNIALS: (25, 40),
            AgeGroup.GEN_X: (41, 56),
            AgeGroup.BOOMERS: (57, 75),
            AgeGroup.SILENT: (76, 95)
        }
        return age_ranges.get(age_group, (25, 40))
    
    def _extract_location(self, text: str, context: Dict[str, Any] = None) -> Optional[str]:
        """Extract location information from text and context."""
        # Simple location extraction - in production, use NER or geo-tagging
        location_indicators = [
            "in ", "from ", "located in ", "based in ", "working in ",
            "living in ", "visiting ", "traveling to "
        ]
        
        text_lower = text.lower()
        for indicator in location_indicators:
            if indicator in text_lower:
                # Extract location after indicator
                start = text_lower.find(indicator) + len(indicator)
                location_text = text[start:start+50]
                # Simple extraction - take first few words
                words = location_text.split()[:3]
                potential_location = " ".join(words).strip(".,!?")
                if len(potential_location) > 2:
                    return potential_location
        
        return None
    
    def _calculate_demographic_confidence(self, profile: DemographicProfile) -> float:
        """Calculate confidence score for demographic profile."""
        factors = [
            1.0 if profile.age_group else 0.0,
            1.0 if profile.industry else 0.0,
            1.0 if profile.job_level else 0.0,
            1.0 if profile.location else 0.0
        ]
        return sum(factors) / len(factors)


class BehaviorAnalyzer:
    """Analyzes behavioral patterns and engagement preferences."""
    
    def __init__(self):
        self.engagement_indicators = {
            EngagementType.LIKE: ["like", "love", "heart", "appreciate", "agree"],
            EngagementType.COMMENT: ["comment", "discuss", "thoughts", "opinion", "feedback"],
            EngagementType.SHARE: ["share", "repost", "spread", "tell others", "everyone needs"],
            EngagementType.SAVE: ["save", "bookmark", "remember", "keep", "reference"],
            EngagementType.CLICK: ["link", "click", "read more", "learn more", "check out"],
            EngagementType.VIEW: ["watch", "see", "view", "look", "examine"]
        }
        
        self.content_preference_indicators = {
            ContentPreference.EDUCATIONAL: [
                "learn", "education", "tutorial", "how to", "guide", "tips",
                "knowledge", "insight", "lesson", "study", "research"
            ],
            ContentPreference.ENTERTAINMENT: [
                "fun", "funny", "humor", "entertainment", "meme", "joke",
                "amusing", "hilarious", "laugh", "enjoy"
            ],
            ContentPreference.NEWS: [
                "news", "update", "announcement", "breaking", "latest",
                "current", "today", "happening", "development"
            ],
            ContentPreference.INSPIRATIONAL: [
                "inspire", "motivation", "success", "achievement", "goal",
                "dream", "overcome", "challenge", "growth", "journey"
            ],
            ContentPreference.PROFESSIONAL: [
                "career", "business", "professional", "work", "industry",
                "leadership", "management", "strategy", "growth", "development"
            ]
        }
        
        self.interaction_styles = {
            "lurker": ["read", "browse", "follow", "watch", "observe"],
            "commenter": ["comment", "discuss", "engage", "respond", "feedback"],
            "sharer": ["share", "repost", "spread", "recommend", "tag"],
            "creator": ["create", "post", "publish", "write", "produce"]
        }
    
    async def analyze_behavior(self, text: str, context: Dict[str, Any] = None) -> BehaviorProfile:
        """Analyze behavioral patterns from text content."""
        try:
            profile = BehaviorProfile()
            text_lower = text.lower()
            
            # Analyze engagement patterns
            for engagement_type, indicators in self.engagement_indicators.items():
                score = sum(1 for indicator in indicators if indicator in text_lower)
                if score > 0:
                    profile.engagement_patterns[engagement_type] = min(1.0, score / 3.0)
            
            # Analyze content preferences
            for preference, indicators in self.content_preference_indicators.items():
                score = sum(1 for indicator in indicators if indicator in text_lower)
                if score > 0:
                    profile.content_preferences[preference] = min(1.0, score / 3.0)
            
            # Analyze interaction style
            style_scores = {}
            for style, indicators in self.interaction_styles.items():
                score = sum(1 for indicator in indicators if indicator in text_lower)
                if score > 0:
                    style_scores[style] = score
            
            if style_scores:
                profile.interaction_style = max(style_scores, key=style_scores.get)
            
            # Extract platform usage patterns
            profile.platform_usage = self._extract_platform_usage(text)
            
            # Analyze posting frequency indicators
            profile.posting_frequency = self._estimate_posting_frequency(text)
            
            # Extract content length preference
            profile.content_length_preference = self._analyze_content_length_preference(text)
            
            # Calculate confidence
            profile.confidence = self._calculate_behavior_confidence(profile)
            
            logger.debug(f"Behavior analysis completed with confidence: {profile.confidence}")
            return profile
            
        except Exception as e:
            logger.error(f"Error in behavior analysis: {str(e)}")
            return BehaviorProfile(confidence=0.0)
    
    def _extract_platform_usage(self, text: str) -> Dict[Platform, float]:
        """Extract platform usage patterns from text."""
        platform_indicators = {
            Platform.LINKEDIN: ["linkedin", "professional network", "career", "business"],
            Platform.TWITTER: ["twitter", "tweet", "thread", "trending", "hashtag"],
            Platform.GENERAL: ["social media", "platform", "online", "digital"]
        }
        
        usage = {}
        text_lower = text.lower()
        
        for platform, indicators in platform_indicators.items():
            score = sum(1 for indicator in indicators if indicator in text_lower)
            if score > 0:
                usage[platform] = min(1.0, score / 2.0)
        
        return usage
    
    def _estimate_posting_frequency(self, text: str) -> float:
        """Estimate posting frequency from text content."""
        frequency_indicators = {
            "daily": 7.0,
            "every day": 7.0,
            "weekly": 1.0,
            "often": 3.0,
            "regularly": 2.0,
            "occasionally": 0.5,
            "rarely": 0.1
        }
        
        text_lower = text.lower()
        for indicator, frequency in frequency_indicators.items():
            if indicator in text_lower:
                return frequency
        
        return 1.0  # Default weekly
    
    def _analyze_content_length_preference(self, text: str) -> str:
        """Analyze preferred content length."""
        length = len(text)
        if length < 100:
            return "short"
        elif length < 500:
            return "medium"
        else:
            return "long"
    
    def _calculate_behavior_confidence(self, profile: BehaviorProfile) -> float:
        """Calculate confidence score for behavior profile."""
        factors = [
            1.0 if profile.engagement_patterns else 0.0,
            1.0 if profile.content_preferences else 0.0,
            1.0 if profile.platform_usage else 0.0,
            1.0 if profile.interaction_style else 0.0
        ]
        return sum(factors) / len(factors)


class PsychographicAnalyzer:
    """Analyzes psychological and value-based characteristics."""
    
    def __init__(self):
        self.personality_indicators = {
            PersonalityTrait.ANALYTICAL: [
                "data", "analysis", "research", "logic", "evidence", "study",
                "metrics", "statistics", "objective", "rational"
            ],
            PersonalityTrait.CREATIVE: [
                "creative", "artistic", "design", "innovative", "imagination",
                "original", "unique", "artistic", "inspiration", "beauty"
            ],
            PersonalityTrait.SOCIAL: [
                "social", "community", "people", "relationship", "connect",
                "collaborate", "team", "together", "networking", "friendship"
            ],
            PersonalityTrait.COMPETITIVE: [
                "compete", "win", "best", "achieve", "success", "performance",
                "goal", "challenge", "overcome", "excel"
            ],
            PersonalityTrait.INNOVATIVE: [
                "innovation", "new", "future", "technology", "disrupt",
                "change", "transform", "revolution", "breakthrough", "pioneer"
            ]
        }
        
        self.value_indicators = {
            "authenticity": ["authentic", "genuine", "real", "honest", "true"],
            "growth": ["growth", "learn", "develop", "improve", "progress"],
            "impact": ["impact", "difference", "change", "influence", "contribute"],
            "freedom": ["freedom", "independence", "autonomy", "choice", "flexible"],
            "security": ["security", "stable", "safe", "reliable", "consistent"],
            "recognition": ["recognition", "appreciated", "acknowledged", "valued"],
            "excellence": ["excellence", "quality", "best", "perfect", "superior"]
        }
        
        self.motivation_indicators = {
            "achievement": ["achieve", "accomplish", "success", "goal", "target"],
            "affiliation": ["belong", "connect", "relationship", "community", "team"],
            "power": ["influence", "control", "lead", "authority", "power"],
            "learning": ["learn", "knowledge", "understand", "discover", "explore"],
            "helping": ["help", "support", "assist", "serve", "contribute"]
        }
    
    async def analyze_psychographics(self, text: str, context: Dict[str, Any] = None) -> PsychographicProfile:
        """Analyze psychographic characteristics from text content."""
        try:
            profile = PsychographicProfile()
            text_lower = text.lower()
            
            # Analyze personality traits
            for trait, indicators in self.personality_indicators.items():
                score = sum(1 for indicator in indicators if indicator in text_lower)
                if score > 0:
                    profile.personality_traits[trait] = min(1.0, score / 3.0)
            
            # Analyze values
            for value, indicators in self.value_indicators.items():
                score = sum(1 for indicator in indicators if indicator in text_lower)
                if score > 0:
                    profile.values[value] = min(1.0, score / 2.0)
            
            # Analyze motivations
            for motivation, indicators in self.motivation_indicators.items():
                score = sum(1 for indicator in indicators if indicator in text_lower)
                if score > 0:
                    profile.motivations[motivation] = min(1.0, score / 2.0)
            
            # Extract interests from topics and keywords
            profile.interests = self._extract_interests(text)
            
            # Analyze communication style
            profile.communication_style = self._analyze_communication_style(text)
            
            # Extract pain points and goals
            profile.pain_points = self._extract_pain_points(text)
            profile.goals = self._extract_goals(text)
            
            # Calculate confidence
            profile.confidence = self._calculate_psychographic_confidence(profile)
            
            logger.debug(f"Psychographic analysis completed with confidence: {profile.confidence}")
            return profile
            
        except Exception as e:
            logger.error(f"Error in psychographic analysis: {str(e)}")
            return PsychographicProfile(confidence=0.0)
    
    def _extract_interests(self, text: str) -> Dict[str, float]:
        """Extract interests from text content."""
        interest_keywords = {
            "technology": ["tech", "ai", "software", "digital", "innovation"],
            "business": ["business", "entrepreneurship", "startup", "finance"],
            "leadership": ["leadership", "management", "team", "strategy"],
            "personal_development": ["growth", "learning", "skills", "development"],
            "health": ["health", "fitness", "wellness", "exercise", "nutrition"],
            "travel": ["travel", "explore", "adventure", "culture", "world"],
            "creativity": ["art", "design", "creative", "music", "writing"]
        }
        
        interests = {}
        text_lower = text.lower()
        
        for interest, keywords in interest_keywords.items():
            score = sum(1 for keyword in keywords if keyword in text_lower)
            if score > 0:
                interests[interest] = min(1.0, score / 3.0)
        
        return interests
    
    def _analyze_communication_style(self, text: str) -> str:
        """Analyze communication style from text."""
        formal_indicators = ["therefore", "furthermore", "however", "consequently"]
        casual_indicators = ["hey", "cool", "awesome", "totally", "yeah"]
        professional_indicators = ["expertise", "experience", "professional", "industry"]
        
        text_lower = text.lower()
        
        formal_score = sum(1 for indicator in formal_indicators if indicator in text_lower)
        casual_score = sum(1 for indicator in casual_indicators if indicator in text_lower)
        professional_score = sum(1 for indicator in professional_indicators if indicator in text_lower)
        
        if professional_score >= max(formal_score, casual_score):
            return "professional"
        elif formal_score > casual_score:
            return "formal"
        else:
            return "casual"
    
    def _extract_pain_points(self, text: str) -> List[str]:
        """Extract pain points from text."""
        pain_indicators = [
            "struggle", "difficult", "challenge", "problem", "issue",
            "frustration", "obstacle", "barrier", "pain", "concern"
        ]
        
        pain_points = []
        text_lower = text.lower()
        sentences = text.split('.')
        
        for sentence in sentences:
            if any(indicator in sentence.lower() for indicator in pain_indicators):
                pain_points.append(sentence.strip())
        
        return pain_points[:3]  # Return top 3
    
    def _extract_goals(self, text: str) -> List[str]:
        """Extract goals from text."""
        goal_indicators = [
            "goal", "objective", "aim", "target", "want to", "hope to",
            "aspire", "desire", "achieve", "accomplish", "plan to"
        ]
        
        goals = []
        text_lower = text.lower()
        sentences = text.split('.')
        
        for sentence in sentences:
            if any(indicator in sentence.lower() for indicator in goal_indicators):
                goals.append(sentence.strip())
        
        return goals[:3]  # Return top 3
    
    def _calculate_psychographic_confidence(self, profile: PsychographicProfile) -> float:
        """Calculate confidence score for psychographic profile."""
        factors = [
            1.0 if profile.personality_traits else 0.0,
            1.0 if profile.values else 0.0,
            1.0 if profile.motivations else 0.0,
            1.0 if profile.interests else 0.0,
            1.0 if profile.communication_style else 0.0
        ]
        return sum(factors) / len(factors)


class PersonaGenerator:
    """Generates detailed audience personas from segmentation data."""
    
    def __init__(self):
        self.persona_templates = {
            "tech_professional": {
                "avatar_descriptions": [
                    "A 32-year-old software engineer working at a tech startup",
                    "A 28-year-old product manager at a SaaS company",
                    "A 35-year-old engineering director at a Fortune 500 tech company"
                ],
                "background_stories": [
                    "Started coding in college, passionate about building innovative solutions",
                    "Transitioned from consulting to tech, loves solving complex problems",
                    "Self-taught developer who climbed the ranks through dedication"
                ]
            },
            "business_leader": {
                "avatar_descriptions": [
                    "A 45-year-old VP of Sales at a B2B software company",
                    "A 38-year-old marketing director at a growing startup",
                    "A 42-year-old business development manager in fintech"
                ],
                "background_stories": [
                    "MBA graduate with 15+ years of experience in sales and leadership",
                    "Former consultant who specializes in growth strategy",
                    "Experienced professional passionate about building high-performing teams"
                ]
            }
        }
        
        self.persona_quotes = {
            "tech_professional": [
                "I love building products that make a real difference in people's lives.",
                "Technology is only as good as the problems it solves.",
                "The best code is code that doesn't need to be written."
            ],
            "business_leader": [
                "Success is about building the right team and empowering them to excel.",
                "Data-driven decisions are the foundation of sustainable growth.",
                "Leadership is about serving others and creating value for everyone."
            ]
        }
    
    async def generate_persona(self, segment: AudienceSegment, 
                             concepts: List[ConceptualEntity] = None) -> AudiencePersona:
        """Generate a detailed persona from audience segment data."""
        try:
            # Determine persona archetype
            archetype = self._determine_archetype(segment)
            
            # Generate core persona details
            name = self._generate_persona_name(segment, archetype)
            avatar_description = self._generate_avatar_description(segment, archetype)
            background_story = self._generate_background_story(segment, archetype)
            quote = self._generate_quote(segment, archetype)
            
            # Generate detailed characteristics
            day_in_life = self._generate_day_in_life(segment)
            challenges = self._generate_challenges(segment, concepts)
            success_metrics = self._generate_success_metrics(segment)
            
            # Generate content preferences
            content_habits = self._generate_content_habits(segment)
            communication_channels = self._generate_communication_channels(segment)
            creation_behavior = self._generate_creation_behavior(segment)
            
            # Generate engagement patterns
            engagement_triggers = self._generate_engagement_triggers(segment, concepts)
            sharing_motivations = self._generate_sharing_motivations(segment)
            brand_preferences = self._generate_brand_preferences(segment)
            
            # Calculate persona quality scores
            confidence = self._calculate_persona_confidence(segment)
            richness = self._calculate_data_richness(segment, concepts)
            
            persona = AudiencePersona(
                name=name,
                avatar_description=avatar_description,
                background_story=background_story,
                demographic_profile=segment.demographic_profile,
                behavior_profile=segment.behavior_profile,
                psychographic_profile=segment.psychographic_profile,
                quote=quote,
                day_in_life=day_in_life,
                typical_challenges=challenges,
                success_metrics=success_metrics,
                content_consumption_habits=content_habits,
                preferred_communication_channels=communication_channels,
                content_creation_behavior=creation_behavior,
                engagement_triggers=engagement_triggers,
                content_sharing_motivations=sharing_motivations,
                brand_interaction_preferences=brand_preferences,
                primary_segment_id=segment.id,
                persona_confidence=confidence,
                data_richness_score=richness
            )
            
            logger.info(f"Generated persona '{name}' with confidence {confidence:.2f}")
            return persona
            
        except Exception as e:
            logger.error(f"Error generating persona: {str(e)}")
            # Return minimal persona
            return AudiencePersona(
                name="Unknown User",
                avatar_description="Generic audience member",
                background_story="Limited data available for detailed persona",
                demographic_profile=segment.demographic_profile,
                behavior_profile=segment.behavior_profile,
                psychographic_profile=segment.psychographic_profile,
                persona_confidence=0.1,
                data_richness_score=0.1
            )
    
    def _determine_archetype(self, segment: AudienceSegment) -> str:
        """Determine persona archetype from segment data."""
        # Simple archetype determination based on industry and role
        industry = segment.demographic_profile.industry
        job_level = segment.demographic_profile.job_level
        
        if industry == Industry.TECHNOLOGY:
            if job_level in [ExperienceLevel.EXECUTIVE, ExperienceLevel.SENIOR]:
                return "tech_leader"
            else:
                return "tech_professional"
        elif job_level == ExperienceLevel.EXECUTIVE:
            return "business_leader"
        elif industry == Industry.MARKETING:
            return "marketing_professional"
        else:
            return "business_professional"
    
    def _generate_persona_name(self, segment: AudienceSegment, archetype: str) -> str:
        """Generate a persona name."""
        # Simple name generation - in production, use more sophisticated methods
        names = {
            "tech_professional": ["Alex Chen", "Sarah Kim", "Marcus Johnson"],
            "tech_leader": ["David Rodriguez", "Lisa Wang", "Michael Brown"],
            "business_leader": ["Jennifer Smith", "Robert Taylor", "Amanda Garcia"],
            "marketing_professional": ["Emily Davis", "James Wilson", "Rachel Lee"]
        }
        
        import random
        return random.choice(names.get(archetype, ["Jordan Taylor"]))
    
    def _generate_avatar_description(self, segment: AudienceSegment, archetype: str) -> str:
        """Generate avatar description."""
        templates = self.persona_templates.get(archetype, {})
        descriptions = templates.get("avatar_descriptions", ["Professional in their field"])
        
        import random
        base_description = random.choice(descriptions)
        
        # Customize based on segment data
        if segment.demographic_profile.location:
            base_description += f", based in {segment.demographic_profile.location}"
        
        return base_description
    
    def _generate_background_story(self, segment: AudienceSegment, archetype: str) -> str:
        """Generate background story."""
        templates = self.persona_templates.get(archetype, {})
        stories = templates.get("background_stories", ["Experienced professional"])
        
        import random
        return random.choice(stories)
    
    def _generate_quote(self, segment: AudienceSegment, archetype: str) -> str:
        """Generate persona quote."""
        quotes = self.persona_quotes.get(archetype, ["I believe in continuous learning and growth."])
        
        import random
        return random.choice(quotes)
    
    def _generate_day_in_life(self, segment: AudienceSegment) -> List[str]:
        """Generate day-in-life activities."""
        activities = [
            "Starts day checking industry news and LinkedIn updates",
            "Attends team meetings and collaborative work sessions",
            "Focuses on strategic projects and problem-solving",
            "Networks with colleagues and industry peers",
            "Ends day planning priorities for tomorrow"
        ]
        
        # Customize based on behavior profile
        if segment.behavior_profile.platform_usage.get(Platform.LINKEDIN, 0) > 0.7:
            activities.insert(1, "Actively engages with LinkedIn content during breaks")
        
        return activities[:5]
    
    def _generate_challenges(self, segment: AudienceSegment, 
                           concepts: List[ConceptualEntity] = None) -> List[str]:
        """Generate typical challenges."""
        # Extract challenges from psychographic profile or use defaults
        if segment.psychographic_profile.pain_points:
            return segment.psychographic_profile.pain_points
        
        # Default challenges based on segment characteristics
        default_challenges = [
            "Staying updated with rapidly changing industry trends",
            "Balancing multiple priorities and deadlines",
            "Finding time for professional development"
        ]
        
        return default_challenges
    
    def _generate_success_metrics(self, segment: AudienceSegment) -> List[str]:
        """Generate success metrics."""
        if segment.psychographic_profile.goals:
            return segment.psychographic_profile.goals
        
        # Default success metrics
        return [
            "Career advancement and professional growth",
            "Building meaningful professional relationships",
            "Making a positive impact in their field"
        ]
    
    def _generate_content_habits(self, segment: AudienceSegment) -> Dict[str, Any]:
        """Generate content consumption habits."""
        habits = {
            "daily_content_time": "30-60 minutes",
            "preferred_content_length": segment.behavior_profile.content_length_preference or "medium",
            "peak_consumption_times": segment.behavior_profile.optimal_posting_times or [9, 13, 18],
            "content_discovery_methods": ["LinkedIn feed", "Industry newsletters", "Peer recommendations"]
        }
        
        # Add platform-specific habits
        if Platform.LINKEDIN in segment.behavior_profile.platform_usage:
            habits["linkedin_activity"] = "Daily browsing and weekly posting"
        
        return habits
    
    def _generate_communication_channels(self, segment: AudienceSegment) -> List[str]:
        """Generate preferred communication channels."""
        channels = ["Email", "LinkedIn"]
        
        if Platform.TWITTER in segment.behavior_profile.platform_usage:
            channels.append("Twitter")
        
        if segment.behavior_profile.interaction_style == "creator":
            channels.extend(["Blog posts", "Video content"])
        
        return channels
    
    def _generate_creation_behavior(self, segment: AudienceSegment) -> Dict[str, Any]:
        """Generate content creation behavior."""
        behavior = {
            "creation_frequency": "Weekly",
            "preferred_formats": ["Text posts", "Professional insights"],
            "sharing_motivation": "Professional growth and networking"
        }
        
        if segment.behavior_profile.interaction_style == "creator":
            behavior["creation_frequency"] = "Multiple times per week"
            behavior["preferred_formats"].extend(["Long-form articles", "Industry commentary"])
        
        return behavior
    
    def _generate_engagement_triggers(self, segment: AudienceSegment, 
                                    concepts: List[ConceptualEntity] = None) -> List[str]:
        """Generate engagement triggers."""
        triggers = [
            "Industry insights and trends",
            "Professional development content",
            "Peer success stories and achievements"
        ]
        
        # Add concept-based triggers
        if concepts:
            hot_takes = [c for c in concepts if c.concept_type == "HOT_TAKE"]
            if hot_takes:
                triggers.append("Thought-provoking industry opinions")
        
        return triggers
    
    def _generate_sharing_motivations(self, segment: AudienceSegment) -> List[str]:
        """Generate content sharing motivations."""
        motivations = [
            "Building thought leadership",
            "Helping peers and colleagues",
            "Contributing to industry discussions"
        ]
        
        if segment.psychographic_profile.values.get("recognition", 0) > 0.5:
            motivations.append("Gaining professional recognition")
        
        return motivations
    
    def _generate_brand_preferences(self, segment: AudienceSegment) -> List[str]:
        """Generate brand interaction preferences."""
        preferences = [
            "Authentic and transparent communication",
            "Value-driven content and insights",
            "Professional and respectful engagement"
        ]
        
        if segment.psychographic_profile.values.get("innovation", 0) > 0.5:
            preferences.append("Innovative and forward-thinking brands")
        
        return preferences
    
    def _calculate_persona_confidence(self, segment: AudienceSegment) -> float:
        """Calculate persona confidence score."""
        confidence_factors = [
            segment.demographic_profile.confidence,
            segment.behavior_profile.confidence,
            segment.psychographic_profile.confidence,
            segment.confidence_score
        ]
        
        valid_factors = [f for f in confidence_factors if f > 0]
        return sum(valid_factors) / len(valid_factors) if valid_factors else 0.1
    
    def _calculate_data_richness(self, segment: AudienceSegment, 
                               concepts: List[ConceptualEntity] = None) -> float:
        """Calculate data richness score."""
        richness_score = 0.0
        
        # Demographic richness
        demo_factors = [
            segment.demographic_profile.age_group is not None,
            segment.demographic_profile.industry is not None,
            segment.demographic_profile.job_level is not None,
            segment.demographic_profile.location is not None
        ]
        richness_score += sum(demo_factors) / len(demo_factors) * 0.3
        
        # Behavior richness
        behavior_factors = [
            bool(segment.behavior_profile.engagement_patterns),
            bool(segment.behavior_profile.content_preferences),
            bool(segment.behavior_profile.platform_usage),
            segment.behavior_profile.interaction_style is not None
        ]
        richness_score += sum(behavior_factors) / len(behavior_factors) * 0.3
        
        # Psychographic richness
        psycho_factors = [
            bool(segment.psychographic_profile.personality_traits),
            bool(segment.psychographic_profile.values),
            bool(segment.psychographic_profile.interests),
            bool(segment.psychographic_profile.motivations)
        ]
        richness_score += sum(psycho_factors) / len(psycho_factors) * 0.3
        
        # Concept data richness
        if concepts:
            richness_score += min(1.0, len(concepts) / 10.0) * 0.1
        
        return min(1.0, richness_score)


class AudienceSegmentationEngine:
    """Main engine for comprehensive audience segmentation and analysis."""
    
    def __init__(self):
        self.demographic_analyzer = DemographicAnalyzer()
        self.behavior_analyzer = BehaviorAnalyzer()
        self.psychographic_analyzer = PsychographicAnalyzer()
        self.persona_generator = PersonaGenerator()
        self.concept_extractor = LinkedInConceptExtractor()
        
        # Segmentation configuration
        self.min_segment_size = 10
        self.max_segments = 20
        self.confidence_threshold = 0.3
        
        logger.info("AudienceSegmentationEngine initialized")
    
    async def analyze_audience(self, text: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Perform comprehensive audience analysis on text content."""
        try:
            logger.info("Starting comprehensive audience analysis")
            
            # Extract concepts for enhanced analysis
            concepts = await self.concept_extractor.extract_concepts(text, context)
            
            # Perform multi-dimensional analysis
            demographic_profile = await self.demographic_analyzer.analyze_demographics(text, context)
            behavior_profile = await self.behavior_analyzer.analyze_behavior(text, context)
            psychographic_profile = await self.psychographic_analyzer.analyze_psychographics(text, context)
            
            # Create audience segment
            segment = await self._create_audience_segment(
                demographic_profile, behavior_profile, psychographic_profile, concepts, context
            )
            
            # Generate persona
            persona = await self.persona_generator.generate_persona(segment, concepts)
            
            # Calculate audience insights
            insights = await self._generate_audience_insights(segment, concepts)
            
            # Generate content recommendations
            recommendations = await self._generate_content_recommendations(segment, concepts)
            
            result = {
                "audience_segment": segment.dict(),
                "audience_persona": persona.dict(),
                "demographic_analysis": {
                    "profile": demographic_profile,
                    "confidence": demographic_profile.confidence,
                    "key_indicators": self._get_demographic_indicators(demographic_profile)
                },
                "behavior_analysis": {
                    "profile": behavior_profile,
                    "confidence": behavior_profile.confidence,
                    "engagement_patterns": behavior_profile.engagement_patterns,
                    "content_preferences": behavior_profile.content_preferences
                },
                "psychographic_analysis": {
                    "profile": psychographic_profile,
                    "confidence": psychographic_profile.confidence,
                    "personality_traits": psychographic_profile.personality_traits,
                    "values": psychographic_profile.values
                },
                "audience_insights": insights,
                "content_recommendations": recommendations,
                "concepts_analyzed": len(concepts),
                "overall_confidence": segment.confidence_score
            }
            
            logger.info(f"Audience analysis completed with confidence: {segment.confidence_score:.2f}")
            return result
            
        except Exception as e:
            logger.error(f"Error in audience analysis: {str(e)}")
            return {
                "error": str(e),
                "audience_segment": None,
                "audience_persona": None,
                "overall_confidence": 0.0
            }
    
    async def segment_multiple_audiences(self, content_items: List[Tuple[str, Dict[str, Any]]]) -> Dict[str, Any]:
        """Segment multiple audiences from different content pieces."""
        try:
            logger.info(f"Segmenting audiences from {len(content_items)} content items")
            
            segments = []
            personas = []
            
            for text, context in content_items:
                analysis = await self.analyze_audience(text, context)
                if analysis.get("audience_segment"):
                    segments.append(AudienceSegment(**analysis["audience_segment"]))
                if analysis.get("audience_persona"):
                    personas.append(AudiencePersona(**analysis["audience_persona"]))
            
            # Merge similar segments
            merged_segments = await self._merge_similar_segments(segments)
            
            # Generate cross-segment insights
            cross_insights = await self._generate_cross_segment_insights(merged_segments)
            
            # Identify audience overlaps
            overlaps = await self._identify_audience_overlaps(merged_segments)
            
            return {
                "segments": [s.dict() for s in merged_segments],
                "personas": [p.dict() for p in personas],
                "cross_segment_insights": cross_insights,
                "audience_overlaps": overlaps,
                "total_segments": len(merged_segments),
                "segmentation_confidence": self._calculate_segmentation_confidence(merged_segments)
            }
            
        except Exception as e:
            logger.error(f"Error in multi-audience segmentation: {str(e)}")
            return {"error": str(e), "segments": [], "personas": []}
    
    async def predict_audience_content_resonance(self, segment: AudienceSegment, 
                                               content: str, viral_prediction: ViralPrediction = None) -> float:
        """Predict how well content will resonate with a specific audience segment."""
        try:
            resonance_score = 0.0
            
            # Content preference alignment
            content_concepts = await self.concept_extractor.extract_concepts(content)
            content_preferences = await self.behavior_analyzer.analyze_behavior(content)
            
            # Calculate preference alignment
            preference_alignment = self._calculate_preference_alignment(
                segment.behavior_profile.content_preferences,
                content_preferences.content_preferences
            )
            resonance_score += preference_alignment * 0.3
            
            # Platform optimization score
            platform_scores = []
            for platform in segment.preferred_platforms:
                if viral_prediction:
                    if viral_prediction.platform == platform:
                        platform_scores.append(viral_prediction.platform_optimization_score)
                else:
                    # Estimate platform fit
                    platform_scores.append(0.7)  # Default assumption
            
            if platform_scores:
                resonance_score += statistics.mean(platform_scores) * 0.2
            
            # Demographic alignment
            demo_analysis = await self.demographic_analyzer.analyze_demographics(content)
            demo_alignment = self._calculate_demographic_alignment(
                segment.demographic_profile, demo_analysis
            )
            resonance_score += demo_alignment * 0.2
            
            # Psychographic alignment
            psycho_analysis = await self.psychographic_analyzer.analyze_psychographics(content)
            psycho_alignment = self._calculate_psychographic_alignment(
                segment.psychographic_profile, psycho_analysis
            )
            resonance_score += psycho_alignment * 0.3
            
            return min(1.0, resonance_score)
            
        except Exception as e:
            logger.error(f"Error predicting content resonance: {str(e)}")
            return 0.0
    
    async def _create_audience_segment(self, demographic_profile: DemographicProfile,
                                     behavior_profile: BehaviorProfile,
                                     psychographic_profile: PsychographicProfile,
                                     concepts: List[ConceptualEntity],
                                     context: Dict[str, Any] = None) -> AudienceSegment:
        """Create an audience segment from analysis profiles."""
        
        # Generate segment name and description
        segment_name = self._generate_segment_name(demographic_profile, behavior_profile)
        segment_description = self._generate_segment_description(
            demographic_profile, behavior_profile, psychographic_profile
        )
        
        # Calculate segment metrics
        confidence_score = self._calculate_segment_confidence(
            demographic_profile, behavior_profile, psychographic_profile
        )
        
        quality_score = self._calculate_segment_quality(
            demographic_profile, behavior_profile, psychographic_profile, concepts
        )
        
        # Estimate engagement and viral potential
        engagement_potential = await self._estimate_engagement_potential(
            behavior_profile, psychographic_profile, concepts
        )
        
        viral_potential = await self._estimate_viral_potential(
            behavior_profile, psychographic_profile, concepts
        )
        
        # Determine preferred content types and platforms
        preferred_content_types = self._determine_preferred_content_types(behavior_profile)
        preferred_platforms = self._determine_preferred_platforms(behavior_profile)
        
        # Extract temporal patterns
        peak_hours = behavior_profile.optimal_posting_times or [9, 13, 18]
        peak_days = ["Tuesday", "Wednesday", "Thursday"]  # Default business days
        
        segment = AudienceSegment(
            name=segment_name,
            description=segment_description,
            demographic_profile=demographic_profile,
            behavior_profile=behavior_profile,
            psychographic_profile=psychographic_profile,
            size_estimate=100,  # Default estimate
            confidence_score=confidence_score,
            quality_score=quality_score,
            engagement_potential=engagement_potential,
            viral_potential=viral_potential,
            conversion_likelihood=0.7,  # Default estimate
            preferred_content_types=preferred_content_types,
            preferred_platforms=preferred_platforms,
            peak_activity_hours=peak_hours,
            peak_activity_days=peak_days,
            source_data=context or {}
        )
        
        return segment
    
    def _generate_segment_name(self, demographic_profile: DemographicProfile,
                             behavior_profile: BehaviorProfile) -> str:
        """Generate a descriptive segment name."""
        name_parts = []
        
        # Add experience level
        if demographic_profile.job_level:
            name_parts.append(demographic_profile.job_level.value.title())
        
        # Add industry
        if demographic_profile.industry:
            name_parts.append(demographic_profile.industry.value.title())
        
        # Add interaction style
        if behavior_profile.interaction_style:
            name_parts.append(behavior_profile.interaction_style.title())
        
        # Default name
        if not name_parts:
            name_parts = ["Professional", "User"]
        
        return " ".join(name_parts[:3])
    
    def _generate_segment_description(self, demographic_profile: DemographicProfile,
                                    behavior_profile: BehaviorProfile,
                                    psychographic_profile: PsychographicProfile) -> str:
        """Generate segment description."""
        description_parts = []
        
        # Demographics
        if demographic_profile.age_group:
            description_parts.append(f"{demographic_profile.age_group.value} professionals")
        
        if demographic_profile.industry:
            description_parts.append(f"in the {demographic_profile.industry.value} industry")
        
        # Behavior
        if behavior_profile.interaction_style:
            description_parts.append(f"who are {behavior_profile.interaction_style}s")
        
        # Primary content preference
        if behavior_profile.content_preferences:
            top_preference = max(behavior_profile.content_preferences.items(), key=lambda x: x[1])
            description_parts.append(f"with preference for {top_preference[0].value} content")
        
        return " ".join(description_parts) or "General professional audience"
    
    def _calculate_segment_confidence(self, demographic_profile: DemographicProfile,
                                    behavior_profile: BehaviorProfile,
                                    psychographic_profile: PsychographicProfile) -> float:
        """Calculate overall segment confidence."""
        confidences = [
            demographic_profile.confidence,
            behavior_profile.confidence,
            psychographic_profile.confidence
        ]
        
        valid_confidences = [c for c in confidences if c > 0]
        return sum(valid_confidences) / len(valid_confidences) if valid_confidences else 0.1
    
    def _calculate_segment_quality(self, demographic_profile: DemographicProfile,
                                 behavior_profile: BehaviorProfile,
                                 psychographic_profile: PsychographicProfile,
                                 concepts: List[ConceptualEntity]) -> float:
        """Calculate segment quality score."""
        quality_factors = []
        
        # Data completeness
        demo_completeness = sum([
            demographic_profile.age_group is not None,
            demographic_profile.industry is not None,
            demographic_profile.job_level is not None,
            demographic_profile.location is not None
        ]) / 4
        quality_factors.append(demo_completeness)
        
        behavior_completeness = sum([
            bool(behavior_profile.engagement_patterns),
            bool(behavior_profile.content_preferences),
            bool(behavior_profile.platform_usage),
            behavior_profile.interaction_style is not None
        ]) / 4
        quality_factors.append(behavior_completeness)
        
        psycho_completeness = sum([
            bool(psychographic_profile.personality_traits),
            bool(psychographic_profile.values),
            bool(psychographic_profile.interests),
            bool(psychographic_profile.motivations)
        ]) / 4
        quality_factors.append(psycho_completeness)
        
        # Concept richness
        if concepts:
            concept_quality = min(1.0, len(concepts) / 5.0)
            quality_factors.append(concept_quality)
        
        return sum(quality_factors) / len(quality_factors)
    
    async def _estimate_engagement_potential(self, behavior_profile: BehaviorProfile,
                                           psychographic_profile: PsychographicProfile,
                                           concepts: List[ConceptualEntity]) -> float:
        """Estimate audience engagement potential."""
        engagement_score = 0.0
        
        # Base engagement from behavior patterns
        if behavior_profile.engagement_patterns:
            avg_engagement = sum(behavior_profile.engagement_patterns.values()) / len(behavior_profile.engagement_patterns)
            engagement_score += avg_engagement * 0.4
        
        # Social personality traits boost engagement
        social_traits = [PersonalityTrait.SOCIAL, PersonalityTrait.COLLABORATIVE]
        for trait in social_traits:
            if trait in psychographic_profile.personality_traits:
                engagement_score += psychographic_profile.personality_traits[trait] * 0.2
        
        # Concept-based engagement potential
        if concepts:
            hot_takes = [c for c in concepts if c.concept_type == "HOT_TAKE"]
            if hot_takes:
                engagement_score += len(hot_takes) * 0.1
        
        return min(1.0, engagement_score)
    
    async def _estimate_viral_potential(self, behavior_profile: BehaviorProfile,
                                      psychographic_profile: PsychographicProfile,
                                      concepts: List[ConceptualEntity]) -> float:
        """Estimate viral content potential for audience."""
        viral_score = 0.0
        
        # Sharing behavior increases viral potential
        if EngagementType.SHARE in behavior_profile.engagement_patterns:
            viral_score += behavior_profile.engagement_patterns[EngagementType.SHARE] * 0.3
        
        # Competitive and innovative traits boost virality
        viral_traits = [PersonalityTrait.COMPETITIVE, PersonalityTrait.INNOVATIVE]
        for trait in viral_traits:
            if trait in psychographic_profile.personality_traits:
                viral_score += psychographic_profile.personality_traits[trait] * 0.2
        
        # Content preferences that drive sharing
        viral_preferences = [ContentPreference.CONTROVERSIAL, ContentPreference.TRENDING]
        for pref in viral_preferences:
            if pref in behavior_profile.content_preferences:
                viral_score += behavior_profile.content_preferences[pref] * 0.25
        
        return min(1.0, viral_score)
    
    def _determine_preferred_content_types(self, behavior_profile: BehaviorProfile) -> List[ContentPreference]:
        """Determine preferred content types from behavior profile."""
        if not behavior_profile.content_preferences:
            return [ContentPreference.PROFESSIONAL]
        
        # Sort by preference score and return top preferences
        sorted_prefs = sorted(
            behavior_profile.content_preferences.items(),
            key=lambda x: x[1],
            reverse=True
        )
        
        return [pref for pref, score in sorted_prefs[:3] if score > 0.3]
    
    def _determine_preferred_platforms(self, behavior_profile: BehaviorProfile) -> List[Platform]:
        """Determine preferred platforms from behavior profile."""
        if not behavior_profile.platform_usage:
            return [Platform.LINKEDIN]  # Default professional platform
        
        # Sort by usage score and return top platforms
        sorted_platforms = sorted(
            behavior_profile.platform_usage.items(),
            key=lambda x: x[1],
            reverse=True
        )
        
        return [platform for platform, score in sorted_platforms if score > 0.3]
    
    async def _merge_similar_segments(self, segments: List[AudienceSegment]) -> List[AudienceSegment]:
        """Merge similar audience segments to avoid over-segmentation."""
        if len(segments) <= 1:
            return segments
        
        merged_segments = []
        processed = set()
        
        for i, segment in enumerate(segments):
            if i in processed:
                continue
            
            similar_segments = [segment]
            processed.add(i)
            
            # Find similar segments
            for j, other_segment in enumerate(segments[i+1:], i+1):
                if j in processed:
                    continue
                
                similarity = self._calculate_segment_similarity(segment, other_segment)
                if similarity > 0.7:  # High similarity threshold
                    similar_segments.append(other_segment)
                    processed.add(j)
            
            # Merge similar segments if found
            if len(similar_segments) > 1:
                merged_segment = await self._merge_segments(similar_segments)
                merged_segments.append(merged_segment)
            else:
                merged_segments.append(segment)
        
        return merged_segments
    
    def _calculate_segment_similarity(self, segment1: AudienceSegment, 
                                    segment2: AudienceSegment) -> float:
        """Calculate similarity between two segments."""
        similarity_score = 0.0
        
        # Demographic similarity
        demo_sim = self._calculate_demographic_similarity(
            segment1.demographic_profile, segment2.demographic_profile
        )
        similarity_score += demo_sim * 0.4
        
        # Behavior similarity
        behavior_sim = self._calculate_behavior_similarity(
            segment1.behavior_profile, segment2.behavior_profile
        )
        similarity_score += behavior_sim * 0.4
        
        # Psychographic similarity
        psycho_sim = self._calculate_psychographic_similarity(
            segment1.psychographic_profile, segment2.psychographic_profile
        )
        similarity_score += psycho_sim * 0.2
        
        return similarity_score
    
    def _calculate_demographic_similarity(self, profile1: DemographicProfile,
                                        profile2: DemographicProfile) -> float:
        """Calculate demographic similarity."""
        matches = 0
        total = 0
        
        # Compare categorical attributes
        if profile1.age_group is not None and profile2.age_group is not None:
            matches += 1 if profile1.age_group == profile2.age_group else 0
            total += 1
        
        if profile1.industry is not None and profile2.industry is not None:
            matches += 1 if profile1.industry == profile2.industry else 0
            total += 1
        
        if profile1.job_level is not None and profile2.job_level is not None:
            matches += 1 if profile1.job_level == profile2.job_level else 0
            total += 1
        
        return matches / total if total > 0 else 0.0
    
    def _calculate_behavior_similarity(self, profile1: BehaviorProfile,
                                     profile2: BehaviorProfile) -> float:
        """Calculate behavior similarity."""
        # Compare engagement patterns
        engagement_sim = self._compare_dict_similarity(
            profile1.engagement_patterns, profile2.engagement_patterns
        )
        
        # Compare content preferences
        content_sim = self._compare_dict_similarity(
            profile1.content_preferences, profile2.content_preferences
        )
        
        # Compare interaction style
        style_sim = 1.0 if profile1.interaction_style == profile2.interaction_style else 0.0
        
        return (engagement_sim + content_sim + style_sim) / 3
    
    def _calculate_psychographic_similarity(self, profile1: PsychographicProfile,
                                          profile2: PsychographicProfile) -> float:
        """Calculate psychographic similarity."""
        # Compare personality traits
        trait_sim = self._compare_dict_similarity(
            profile1.personality_traits, profile2.personality_traits
        )
        
        # Compare values
        value_sim = self._compare_dict_similarity(
            profile1.values, profile2.values
        )
        
        return (trait_sim + value_sim) / 2
    
    def _compare_dict_similarity(self, dict1: Dict, dict2: Dict) -> float:
        """Compare similarity between two dictionaries."""
        if not dict1 or not dict2:
            return 0.0
        
        all_keys = set(dict1.keys()) | set(dict2.keys())
        if not all_keys:
            return 1.0
        
        similarity_sum = 0.0
        for key in all_keys:
            val1 = dict1.get(key, 0.0)
            val2 = dict2.get(key, 0.0)
            # Calculate similarity for this key (1 - absolute difference)
            similarity_sum += 1.0 - abs(val1 - val2)
        
        return similarity_sum / len(all_keys)
    
    async def _merge_segments(self, segments: List[AudienceSegment]) -> AudienceSegment:
        """Merge multiple similar segments into one."""
        if len(segments) == 1:
            return segments[0]
        
        # Use the first segment as base and merge others into it
        base_segment = segments[0]
        
        # Merge names
        merged_name = f"Merged {base_segment.name}"
        
        # Merge descriptions
        merged_description = f"Combined segment including: {', '.join([s.name for s in segments])}"
        
        # Average numeric metrics
        merged_size = sum(s.size_estimate for s in segments)
        merged_confidence = sum(s.confidence_score for s in segments) / len(segments)
        merged_quality = sum(s.quality_score for s in segments) / len(segments)
        merged_engagement = sum(s.engagement_potential for s in segments) / len(segments)
        merged_viral = sum(s.viral_potential for s in segments) / len(segments)
        
        # Merge preferred content types and platforms
        all_content_types = set()
        all_platforms = set()
        for segment in segments:
            all_content_types.update(segment.preferred_content_types)
            all_platforms.update(segment.preferred_platforms)
        
        merged_segment = AudienceSegment(
            name=merged_name,
            description=merged_description,
            demographic_profile=base_segment.demographic_profile,
            behavior_profile=base_segment.behavior_profile,
            psychographic_profile=base_segment.psychographic_profile,
            size_estimate=merged_size,
            confidence_score=merged_confidence,
            quality_score=merged_quality,
            engagement_potential=merged_engagement,
            viral_potential=merged_viral,
            conversion_likelihood=base_segment.conversion_likelihood,
            preferred_content_types=list(all_content_types),
            preferred_platforms=list(all_platforms),
            peak_activity_hours=base_segment.peak_activity_hours,
            peak_activity_days=base_segment.peak_activity_days
        )
        
        return merged_segment
    
    async def _generate_audience_insights(self, segment: AudienceSegment,
                                        concepts: List[ConceptualEntity]) -> Dict[str, Any]:
        """Generate actionable audience insights."""
        insights = {
            "key_characteristics": [],
            "engagement_opportunities": [],
            "content_recommendations": [],
            "platform_strategy": [],
            "potential_challenges": [],
            "growth_opportunities": []
        }
        
        # Key characteristics
        if segment.demographic_profile.industry:
            insights["key_characteristics"].append(
                f"Primarily {segment.demographic_profile.industry.value} professionals"
            )
        
        if segment.behavior_profile.interaction_style:
            insights["key_characteristics"].append(
                f"Predominantly {segment.behavior_profile.interaction_style}s on social platforms"
            )
        
        # Engagement opportunities
        if segment.engagement_potential > 0.7:
            insights["engagement_opportunities"].append(
                "High engagement potential - audience is active and responsive"
            )
        
        top_engagement = max(segment.behavior_profile.engagement_patterns.items(), 
                           key=lambda x: x[1], default=(None, 0))
        if top_engagement[0]:
            insights["engagement_opportunities"].append(
                f"Focus on content that encourages {top_engagement[0].value} behavior"
            )
        
        # Content recommendations
        for content_type in segment.preferred_content_types[:2]:
            insights["content_recommendations"].append(
                f"Create more {content_type.value} content for better resonance"
            )
        
        # Platform strategy
        for platform in segment.preferred_platforms:
            insights["platform_strategy"].append(
                f"Optimize content for {platform.value} platform characteristics"
            )
        
        return insights
    
    async def _generate_content_recommendations(self, segment: AudienceSegment,
                                              concepts: List[ConceptualEntity]) -> List[str]:
        """Generate content recommendations for the audience segment."""
        recommendations = []
        
        # Based on content preferences
        if ContentPreference.EDUCATIONAL in segment.preferred_content_types:
            recommendations.append("Create how-to guides and educational content")
        
        if ContentPreference.PROFESSIONAL in segment.preferred_content_types:
            recommendations.append("Share industry insights and professional experiences")
        
        # Based on engagement patterns
        if EngagementType.COMMENT in segment.behavior_profile.engagement_patterns:
            recommendations.append("Ask thought-provoking questions to encourage discussions")
        
        if EngagementType.SHARE in segment.behavior_profile.engagement_patterns:
            recommendations.append("Create shareable content with strong value propositions")
        
        # Based on viral potential
        if segment.viral_potential > 0.6:
            recommendations.append("Consider controversial or trending topics for higher reach")
        
        # Based on concepts
        if concepts:
            hot_takes = [c for c in concepts if c.concept_type == "HOT_TAKE"]
            if hot_takes:
                recommendations.append("Incorporate thought leadership and opinion pieces")
        
        return recommendations[:5]  # Return top 5 recommendations
    
    async def _generate_cross_segment_insights(self, segments: List[AudienceSegment]) -> Dict[str, Any]:
        """Generate insights across multiple segments."""
        if not segments:
            return {}
        
        insights = {
            "common_characteristics": {},
            "segment_diversity": {},
            "platform_distribution": {},
            "engagement_patterns": {},
            "content_opportunities": []
        }
        
        # Common characteristics
        industries = [s.demographic_profile.industry for s in segments if s.demographic_profile.industry]
        if industries:
            industry_counts = {}
            for industry in industries:
                industry_counts[industry.value] = industry_counts.get(industry.value, 0) + 1
            insights["common_characteristics"]["industries"] = industry_counts
        
        # Platform distribution
        platform_usage = {}
        for segment in segments:
            for platform in segment.preferred_platforms:
                platform_usage[platform.value] = platform_usage.get(platform.value, 0) + 1
        insights["platform_distribution"] = platform_usage
        
        # Average engagement potential
        avg_engagement = sum(s.engagement_potential for s in segments) / len(segments)
        insights["engagement_patterns"]["average_engagement_potential"] = avg_engagement
        
        # Content opportunities
        all_content_types = set()
        for segment in segments:
            all_content_types.update(segment.preferred_content_types)
        
        for content_type in all_content_types:
            insights["content_opportunities"].append(
                f"Create {content_type.value} content to appeal to multiple segments"
            )
        
        return insights
    
    async def _identify_audience_overlaps(self, segments: List[AudienceSegment]) -> List[Dict[str, Any]]:
        """Identify overlaps between audience segments."""
        overlaps = []
        
        for i, segment1 in enumerate(segments):
            for j, segment2 in enumerate(segments[i+1:], i+1):
                similarity = self._calculate_segment_similarity(segment1, segment2)
                
                if similarity > 0.3:  # Significant overlap
                    overlap = {
                        "segment1": segment1.name,
                        "segment2": segment2.name,
                        "similarity_score": similarity,
                        "overlap_areas": []
                    }
                    
                    # Identify specific overlap areas
                    if segment1.demographic_profile.industry == segment2.demographic_profile.industry:
                        overlap["overlap_areas"].append("Same industry")
                    
                    if segment1.behavior_profile.interaction_style == segment2.behavior_profile.interaction_style:
                        overlap["overlap_areas"].append("Similar interaction style")
                    
                    common_platforms = set(segment1.preferred_platforms) & set(segment2.preferred_platforms)
                    if common_platforms:
                        overlap["overlap_areas"].append(f"Common platforms: {list(common_platforms)}")
                    
                    overlaps.append(overlap)
        
        return overlaps
    
    def _calculate_segmentation_confidence(self, segments: List[AudienceSegment]) -> float:
        """Calculate overall segmentation confidence."""
        if not segments:
            return 0.0
        
        # Average confidence across all segments
        avg_confidence = sum(s.confidence_score for s in segments) / len(segments)
        
        # Penalty for too few or too many segments
        segment_count_penalty = 1.0
        if len(segments) < 2:
            segment_count_penalty = 0.8  # Too few segments
        elif len(segments) > 10:
            segment_count_penalty = 0.9  # Too many segments
        
        return avg_confidence * segment_count_penalty
    
    def _get_demographic_indicators(self, profile: DemographicProfile) -> List[str]:
        """Get key demographic indicators."""
        indicators = []
        
        if profile.age_group:
            indicators.append(f"Age group: {profile.age_group.value}")
        
        if profile.industry:
            indicators.append(f"Industry: {profile.industry.value}")
        
        if profile.job_level:
            indicators.append(f"Experience: {profile.job_level.value}")
        
        if profile.location:
            indicators.append(f"Location: {profile.location}")
        
        return indicators
    
    def _calculate_preference_alignment(self, segment_prefs: Dict, content_prefs: Dict) -> float:
        """Calculate alignment between segment and content preferences."""
        if not segment_prefs or not content_prefs:
            return 0.0
        
        alignment_score = 0.0
        total_weight = 0.0
        
        for pref_type, segment_score in segment_prefs.items():
            content_score = content_prefs.get(pref_type, 0.0)
            # Calculate alignment as similarity between scores
            alignment = 1.0 - abs(segment_score - content_score)
            alignment_score += alignment * segment_score  # Weight by segment preference strength
            total_weight += segment_score
        
        return alignment_score / total_weight if total_weight > 0 else 0.0
    
    def _calculate_demographic_alignment(self, segment_demo: DemographicProfile,
                                       content_demo: DemographicProfile) -> float:
        """Calculate demographic alignment between segment and content."""
        alignment_score = 0.0
        factors = 0
        
        # Industry alignment
        if segment_demo.industry and content_demo.industry:
            alignment_score += 1.0 if segment_demo.industry == content_demo.industry else 0.0
            factors += 1
        
        # Experience level alignment
        if segment_demo.job_level and content_demo.job_level:
            alignment_score += 1.0 if segment_demo.job_level == content_demo.job_level else 0.0
            factors += 1
        
        # Age group alignment
        if segment_demo.age_group and content_demo.age_group:
            alignment_score += 1.0 if segment_demo.age_group == content_demo.age_group else 0.0
            factors += 1
        
        return alignment_score / factors if factors > 0 else 0.5  # Default neutral alignment
    
    def _calculate_psychographic_alignment(self, segment_psycho: PsychographicProfile,
                                         content_psycho: PsychographicProfile) -> float:
        """Calculate psychographic alignment between segment and content."""
        # Compare personality traits
        trait_alignment = self._compare_dict_similarity(
            segment_psycho.personality_traits, content_psycho.personality_traits
        )
        
        # Compare values
        value_alignment = self._compare_dict_similarity(
            segment_psycho.values, content_psycho.values
        )
        
        return (trait_alignment + value_alignment) / 2


# Example usage and integration functions
async def analyze_content_audience(text: str, platform: Platform = Platform.LINKEDIN) -> Dict[str, Any]:
    """Quick function to analyze audience for given content."""
    engine = AudienceSegmentationEngine()
    context = {"platform": platform.value}
    return await engine.analyze_audience(text, context)


async def generate_audience_persona(text: str, context: Dict[str, Any] = None) -> AudiencePersona:
    """Quick function to generate audience persona from content."""
    engine = AudienceSegmentationEngine()
    analysis = await engine.analyze_audience(text, context)
    return AudiencePersona(**analysis["audience_persona"])


async def predict_content_audience_fit(content: str, segment: AudienceSegment) -> float:
    """Predict how well content fits with audience segment."""
    engine = AudienceSegmentationEngine()
    return await engine.predict_audience_content_resonance(segment, content)