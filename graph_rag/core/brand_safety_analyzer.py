"""Brand Safety and Risk Assessment Framework for Epic 7.2 - Comprehensive risk analysis for content safety."""

import asyncio
import hashlib
import logging
import re
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

from graph_rag.core.concept_extractor import ConceptualEntity
from graph_rag.core.viral_prediction_engine import (
    Platform,
    ViralPrediction,
    ViralPredictionEngine,
)

logger = logging.getLogger(__name__)


class BrandSafetyLevel(Enum):
    """Brand safety risk levels."""
    SAFE = "safe"           # Content is brand-safe and appropriate
    CAUTION = "caution"     # Minor concerns, review recommended
    RISK = "risk"           # Significant risks, approval required
    DANGER = "danger"       # High risk, likely requires rejection


class ContentClassification(Enum):
    """Content type classifications for brand safety."""
    PROFESSIONAL = "professional"      # Business/professional content
    PERSONAL = "personal"              # Personal stories/experiences
    OPINION = "opinion"                # Opinion pieces and viewpoints
    CONTROVERSIAL = "controversial"    # Potentially divisive content
    TOXIC = "toxic"                   # Harmful or inappropriate content


class StakeholderImpact(Enum):
    """Stakeholder impact levels."""
    POSITIVE = "positive"      # Enhances stakeholder perception
    NEUTRAL = "neutral"        # Minimal stakeholder impact
    NEGATIVE = "negative"      # May harm stakeholder perception
    CRISIS = "crisis"          # Could trigger stakeholder crisis


class RiskDimension(Enum):
    """Risk assessment dimensions."""
    REPUTATIONAL = "reputational"    # Brand reputation risks
    LEGAL = "legal"                  # Legal compliance risks
    FINANCIAL = "financial"          # Financial impact risks
    OPERATIONAL = "operational"      # Business operations risks


class BrandProfile(Enum):
    """Brand safety profiles with different risk tolerances."""
    CONSERVATIVE = "conservative"    # Very low risk tolerance
    MODERATE = "moderate"           # Moderate risk tolerance
    AGGRESSIVE = "aggressive"       # Higher risk tolerance for engagement


@dataclass
class RiskScore:
    """Multi-dimensional risk score."""
    reputational: float     # 0.0 - 1.0
    legal: float           # 0.0 - 1.0
    financial: float       # 0.0 - 1.0
    operational: float     # 0.0 - 1.0
    overall: float         # 0.0 - 1.0 (weighted average)


@dataclass
class StakeholderAnalysis:
    """Analysis of impact on different stakeholder groups."""
    customers: StakeholderImpact
    employees: StakeholderImpact
    investors: StakeholderImpact
    partners: StakeholderImpact
    general_public: StakeholderImpact
    sentiment_confidence: float  # 0.0 - 1.0


@dataclass
class ToxicityAssessment:
    """Content toxicity assessment results."""
    toxicity_score: float           # 0.0 - 1.0
    hate_speech_score: float        # 0.0 - 1.0
    harassment_score: float         # 0.0 - 1.0
    profanity_score: float         # 0.0 - 1.0
    threat_score: float            # 0.0 - 1.0
    identity_attack_score: float    # 0.0 - 1.0
    severe_toxicity_score: float    # 0.0 - 1.0


@dataclass
class ControversyAnalysis:
    """Controversy detection and classification."""
    controversy_score: float        # 0.0 - 1.0
    controversy_type: str          # political, social, business, cultural
    polarization_risk: float       # 0.0 - 1.0
    backlash_potential: float      # 0.0 - 1.0
    divisive_topics: list[str]     # Identified divisive topics
    sensitivity_areas: list[str]   # Sensitive subject areas


@dataclass
class CrisisRiskAssessment:
    """Crisis escalation risk assessment."""
    escalation_probability: float   # 0.0 - 1.0
    viral_amplification_risk: float # 0.0 - 1.0
    media_attention_risk: float     # 0.0 - 1.0
    response_urgency: str          # immediate, within_hours, within_days
    crisis_triggers: list[str]     # Potential crisis triggers
    mitigation_window: timedelta   # Time to respond before escalation


@dataclass
class MitigationStrategy:
    """Risk mitigation strategy recommendations."""
    priority: str                   # critical, high, medium, low
    actions: list[str]             # Specific mitigation actions
    approval_required: bool        # Whether approval is needed
    monitoring_required: bool      # Whether monitoring is needed
    alternative_approaches: list[str] # Alternative content approaches
    decision_deadline: datetime | None # When decision must be made


class BrandSafetyAssessment(BaseModel):
    """Comprehensive brand safety assessment result."""
    content_id: str
    platform: Platform
    brand_profile: BrandProfile

    # Overall safety classification
    safety_level: BrandSafetyLevel
    content_classification: ContentClassification

    # Risk scoring
    risk_score: RiskScore
    confidence: float = Field(ge=0.0, le=1.0, description="Assessment confidence")

    # Stakeholder analysis
    stakeholder_analysis: StakeholderAnalysis

    # Content analysis
    toxicity_assessment: ToxicityAssessment
    controversy_analysis: ControversyAnalysis

    # Crisis assessment
    crisis_risk: CrisisRiskAssessment

    # Brand alignment
    brand_alignment_score: float = Field(ge=0.0, le=1.0, description="Brand value alignment")
    message_consistency_score: float = Field(ge=0.0, le=1.0, description="Brand message consistency")

    # Risk factors and triggers
    risk_factors: list[str] = Field(default_factory=list, description="Identified risk factors")
    crisis_triggers: list[str] = Field(default_factory=list, description="Potential crisis triggers")
    red_flags: list[str] = Field(default_factory=list, description="Content red flags")

    # Integration with viral prediction
    viral_prediction: ViralPrediction | None = Field(default=None, description="Associated viral prediction")
    risk_adjusted_viral_score: float = Field(ge=0.0, le=1.0, description="Viral score adjusted for brand safety")

    # Mitigation and recommendations
    mitigation_strategy: MitigationStrategy
    content_modifications: list[str] = Field(default_factory=list, description="Suggested content changes")
    approval_workflow: list[str] = Field(default_factory=list, description="Required approval steps")

    # Monitoring and alerts
    monitoring_keywords: list[str] = Field(default_factory=list, description="Keywords to monitor")
    alert_thresholds: dict[str, float] = Field(default_factory=dict, description="Alert threshold settings")

    created_at: datetime = Field(default_factory=datetime.utcnow)


class ToxicityDetector:
    """Advanced toxicity detection system."""

    def __init__(self):
        # Toxicity patterns and keywords
        self.hate_speech_patterns = [
            r'\b(?:hate|despise|loathe|disgusting)\s+(?:people|group|community)\b',
            r'\b(?:racist|sexist|homophobic|bigoted)\b',
            r'\b(?:genocide|ethnic\s+cleansing|supremacy)\b',
            r'\b(?:inferior|subhuman|vermin|scum)\b'
        ]

        self.harassment_patterns = [
            r'\b(?:stalking|harassing|threatening|intimidating)\b',
            r'\b(?:kill\s+yourself|kys|go\s+die)\b',
            r'\b(?:worthless|pathetic|loser|failure)\s+(?:person|human)\b',
            r'\b(?:shut\s+up|nobody\s+cares|stupid\s+idiot)\b'
        ]

        self.profanity_words = {
            'mild': ['damn', 'hell', 'crap', 'piss'],
            'moderate': ['shit', 'bitch', 'ass', 'bastard'],
            'severe': ['fuck', 'cunt', 'nigger', 'faggot']
        }

        self.threat_patterns = [
            r'\b(?:will\s+kill|going\s+to\s+hurt|make\s+you\s+pay)\b',
            r'\b(?:find\s+where\s+you\s+live|track\s+you\s+down)\b',
            r'\b(?:bomb|shoot|stab|attack)\s+(?:you|them|everyone)\b',
            r'\b(?:revenge|retaliation|payback)\b'
        ]

        self.identity_attack_patterns = [
            r'\b(?:because\s+you\'re|all\s+(?:women|men|gays|blacks|whites))\s+are\b',
            r'\b(?:typical|stereotypical)\s+(?:woman|man|gay|black|white|asian)\b',
            r'\b(?:gender|race|religion|sexuality)\s+(?:makes\s+you|defines\s+you)\b'
        ]

    async def assess_toxicity(self, text: str) -> ToxicityAssessment:
        """Assess content toxicity across multiple dimensions."""
        text_lower = text.lower()

        # Hate speech detection
        hate_speech_score = self._calculate_hate_speech_score(text_lower)

        # Harassment detection
        harassment_score = self._calculate_harassment_score(text_lower)

        # Profanity detection
        profanity_score = self._calculate_profanity_score(text_lower)

        # Threat detection
        threat_score = self._calculate_threat_score(text_lower)

        # Identity attack detection
        identity_attack_score = self._calculate_identity_attack_score(text_lower)

        # Overall toxicity (weighted combination)
        toxicity_score = (
            hate_speech_score * 0.25 +
            harassment_score * 0.20 +
            threat_score * 0.20 +
            identity_attack_score * 0.20 +
            profanity_score * 0.15
        )

        # Severe toxicity (high threshold)
        severe_toxicity_score = max(hate_speech_score, threat_score, identity_attack_score)

        return ToxicityAssessment(
            toxicity_score=toxicity_score,
            hate_speech_score=hate_speech_score,
            harassment_score=harassment_score,
            profanity_score=profanity_score,
            threat_score=threat_score,
            identity_attack_score=identity_attack_score,
            severe_toxicity_score=severe_toxicity_score
        )

    def _calculate_hate_speech_score(self, text: str) -> float:
        """Calculate hate speech score."""
        score = 0.0
        for pattern in self.hate_speech_patterns:
            matches = len(re.findall(pattern, text, re.IGNORECASE))
            score += matches * 0.3
        return min(1.0, score)

    def _calculate_harassment_score(self, text: str) -> float:
        """Calculate harassment score."""
        score = 0.0
        for pattern in self.harassment_patterns:
            matches = len(re.findall(pattern, text, re.IGNORECASE))
            score += matches * 0.25
        return min(1.0, score)

    def _calculate_profanity_score(self, text: str) -> float:
        """Calculate profanity score."""
        score = 0.0
        words = text.split()

        for word in words:
            if word in self.profanity_words['severe']:
                score += 0.4
            elif word in self.profanity_words['moderate']:
                score += 0.2
            elif word in self.profanity_words['mild']:
                score += 0.1

        return min(1.0, score)

    def _calculate_threat_score(self, text: str) -> float:
        """Calculate threat score."""
        score = 0.0
        for pattern in self.threat_patterns:
            matches = len(re.findall(pattern, text, re.IGNORECASE))
            score += matches * 0.35
        return min(1.0, score)

    def _calculate_identity_attack_score(self, text: str) -> float:
        """Calculate identity attack score."""
        score = 0.0
        for pattern in self.identity_attack_patterns:
            matches = len(re.findall(pattern, text, re.IGNORECASE))
            score += matches * 0.3
        return min(1.0, score)


class ControversyDetector:
    """Advanced controversy and divisiveness detection."""

    def __init__(self):
        # Political controversy patterns
        self.political_keywords = [
            'trump', 'biden', 'democrat', 'republican', 'liberal', 'conservative',
            'socialism', 'capitalism', 'immigration', 'healthcare', 'abortion',
            'gun control', 'climate change', 'taxation', 'welfare'
        ]

        # Social controversy patterns
        self.social_keywords = [
            'gender', 'lgbtq', 'transgender', 'feminism', 'masculinity',
            'race', 'racism', 'privilege', 'inequality', 'discrimination',
            'cancel culture', 'woke', 'diversity', 'inclusion'
        ]

        # Business controversy patterns
        self.business_keywords = [
            'layoffs', 'union', 'strike', 'exploitation', 'monopoly',
            'wealth gap', 'ceo pay', 'corporate greed', 'tax avoidance'
        ]

        # Cultural controversy patterns
        self.cultural_keywords = [
            'religion', 'atheism', 'tradition', 'modernization',
            'cultural appropriation', 'heritage', 'values', 'morality'
        ]

        self.polarizing_phrases = [
            'controversial opinion', 'unpopular truth', 'nobody talks about',
            'everyone is wrong about', 'the real problem with',
            'why [group] is', 'all [group] are', 'never trust [group]'
        ]

        self.divisive_language = [
            'us vs them', 'real [group]', 'fake [group]', 'traitor',
            'enemy of', 'destroy', 'eliminate', 'purge', 'cleanse'
        ]

    async def analyze_controversy(self, text: str, concepts: list[ConceptualEntity] = None) -> ControversyAnalysis:
        """Analyze controversy potential in content."""
        text_lower = text.lower()

        # Identify controversy types and scores
        political_score = self._calculate_political_controversy(text_lower)
        social_score = self._calculate_social_controversy(text_lower)
        business_score = self._calculate_business_controversy(text_lower)
        cultural_score = self._calculate_cultural_controversy(text_lower)

        # Determine primary controversy type
        controversy_scores = {
            'political': political_score,
            'social': social_score,
            'business': business_score,
            'cultural': cultural_score
        }
        controversy_type = max(controversy_scores, key=controversy_scores.get)

        # Overall controversy score
        controversy_score = max(controversy_scores.values())

        # Polarization risk
        polarization_risk = self._calculate_polarization_risk(text_lower)

        # Backlash potential
        backlash_potential = self._calculate_backlash_potential(text_lower, concepts)

        # Identify divisive topics
        divisive_topics = self._identify_divisive_topics(text_lower)

        # Identify sensitivity areas
        sensitivity_areas = self._identify_sensitivity_areas(text_lower)

        return ControversyAnalysis(
            controversy_score=controversy_score,
            controversy_type=controversy_type,
            polarization_risk=polarization_risk,
            backlash_potential=backlash_potential,
            divisive_topics=divisive_topics,
            sensitivity_areas=sensitivity_areas
        )

    def _calculate_political_controversy(self, text: str) -> float:
        """Calculate political controversy score."""
        score = 0.0
        for keyword in self.political_keywords:
            if keyword in text:
                score += 0.15
        return min(1.0, score)

    def _calculate_social_controversy(self, text: str) -> float:
        """Calculate social controversy score."""
        score = 0.0
        for keyword in self.social_keywords:
            if keyword in text:
                score += 0.12
        return min(1.0, score)

    def _calculate_business_controversy(self, text: str) -> float:
        """Calculate business controversy score."""
        score = 0.0
        for keyword in self.business_keywords:
            if keyword in text:
                score += 0.1
        return min(1.0, score)

    def _calculate_cultural_controversy(self, text: str) -> float:
        """Calculate cultural controversy score."""
        score = 0.0
        for keyword in self.cultural_keywords:
            if keyword in text:
                score += 0.1
        return min(1.0, score)

    def _calculate_polarization_risk(self, text: str) -> float:
        """Calculate polarization risk."""
        score = 0.0
        for phrase in self.polarizing_phrases:
            if phrase.replace('[group]', r'\w+') in text:
                score += 0.2
        for phrase in self.divisive_language:
            if phrase.replace('[group]', r'\w+') in text:
                score += 0.25
        return min(1.0, score)

    def _calculate_backlash_potential(self, text: str, concepts: list[ConceptualEntity] = None) -> float:
        """Calculate potential for public backlash."""
        score = 0.0

        # High controversy + negative sentiment = higher backlash risk
        negative_indicators = ['wrong', 'stupid', 'idiotic', 'ridiculous', 'pathetic']
        for indicator in negative_indicators:
            if indicator in text:
                score += 0.1

        # Hot takes increase backlash risk
        if concepts:
            hot_takes = [c for c in concepts if c.concept_type == 'HOT_TAKE']
            score += len(hot_takes) * 0.15

        return min(1.0, score)

    def _identify_divisive_topics(self, text: str) -> list[str]:
        """Identify specific divisive topics mentioned."""
        topics = []
        all_keywords = (self.political_keywords + self.social_keywords +
                       self.business_keywords + self.cultural_keywords)

        for keyword in all_keywords:
            if keyword in text:
                topics.append(keyword)

        return topics[:5]  # Return top 5 topics

    def _identify_sensitivity_areas(self, text: str) -> list[str]:
        """Identify sensitive subject areas."""
        sensitivity_patterns = {
            'Mental Health': ['depression', 'suicide', 'anxiety', 'mental illness'],
            'Violence': ['violence', 'assault', 'murder', 'terrorism'],
            'Discrimination': ['racism', 'sexism', 'homophobia', 'discrimination'],
            'Children': ['child abuse', 'exploitation', 'minors', 'underage'],
            'Health': ['pandemic', 'vaccine', 'medical advice', 'treatment']
        }

        areas = []
        for area, keywords in sensitivity_patterns.items():
            if any(keyword in text for keyword in keywords):
                areas.append(area)

        return areas


class StakeholderImpactAnalyzer:
    """Analyze impact on different stakeholder groups."""

    def __init__(self):
        self.stakeholder_sensitivities = {
            'customers': {
                'positive': ['quality', 'value', 'service', 'innovation', 'trust'],
                'negative': ['defect', 'overpriced', 'poor service', 'misleading', 'breach']
            },
            'employees': {
                'positive': ['culture', 'growth', 'opportunity', 'fair', 'support'],
                'negative': ['layoffs', 'overwork', 'toxic', 'discrimination', 'unsafe']
            },
            'investors': {
                'positive': ['profit', 'growth', 'market share', 'efficiency', 'strategy'],
                'negative': ['loss', 'decline', 'risk', 'lawsuit', 'scandal']
            },
            'partners': {
                'positive': ['collaboration', 'mutual benefit', 'reliable', 'transparent'],
                'negative': ['conflict', 'breach', 'unreliable', 'unfair terms']
            }
        }

    async def analyze_stakeholder_impact(self, text: str, concepts: list[ConceptualEntity] = None) -> StakeholderAnalysis:
        """Analyze impact on different stakeholder groups."""
        text_lower = text.lower()

        # Analyze impact for each stakeholder group
        customers_impact = self._analyze_customer_impact(text_lower)
        employees_impact = self._analyze_employee_impact(text_lower)
        investors_impact = self._analyze_investor_impact(text_lower)
        partners_impact = self._analyze_partner_impact(text_lower)
        public_impact = self._analyze_public_impact(text_lower, concepts)

        # Calculate confidence based on signal strength
        confidence = self._calculate_sentiment_confidence(text_lower)

        return StakeholderAnalysis(
            customers=customers_impact,
            employees=employees_impact,
            investors=investors_impact,
            partners=partners_impact,
            general_public=public_impact,
            sentiment_confidence=confidence
        )

    def _analyze_customer_impact(self, text: str) -> StakeholderImpact:
        """Analyze impact on customers."""
        positive_score = sum(1 for word in self.stakeholder_sensitivities['customers']['positive'] if word in text)
        negative_score = sum(1 for word in self.stakeholder_sensitivities['customers']['negative'] if word in text)

        if negative_score > 2:
            return StakeholderImpact.CRISIS
        elif negative_score > positive_score:
            return StakeholderImpact.NEGATIVE
        elif positive_score > negative_score:
            return StakeholderImpact.POSITIVE
        else:
            return StakeholderImpact.NEUTRAL

    def _analyze_employee_impact(self, text: str) -> StakeholderImpact:
        """Analyze impact on employees."""
        positive_score = sum(1 for word in self.stakeholder_sensitivities['employees']['positive'] if word in text)
        negative_score = sum(1 for word in self.stakeholder_sensitivities['employees']['negative'] if word in text)

        if negative_score > 2:
            return StakeholderImpact.CRISIS
        elif negative_score > positive_score:
            return StakeholderImpact.NEGATIVE
        elif positive_score > negative_score:
            return StakeholderImpact.POSITIVE
        else:
            return StakeholderImpact.NEUTRAL

    def _analyze_investor_impact(self, text: str) -> StakeholderImpact:
        """Analyze impact on investors."""
        positive_score = sum(1 for word in self.stakeholder_sensitivities['investors']['positive'] if word in text)
        negative_score = sum(1 for word in self.stakeholder_sensitivities['investors']['negative'] if word in text)

        if negative_score > 2:
            return StakeholderImpact.CRISIS
        elif negative_score > positive_score:
            return StakeholderImpact.NEGATIVE
        elif positive_score > negative_score:
            return StakeholderImpact.POSITIVE
        else:
            return StakeholderImpact.NEUTRAL

    def _analyze_partner_impact(self, text: str) -> StakeholderImpact:
        """Analyze impact on partners."""
        positive_score = sum(1 for word in self.stakeholder_sensitivities['partners']['positive'] if word in text)
        negative_score = sum(1 for word in self.stakeholder_sensitivities['partners']['negative'] if word in text)

        if negative_score > 1:
            return StakeholderImpact.NEGATIVE
        elif positive_score > negative_score:
            return StakeholderImpact.POSITIVE
        else:
            return StakeholderImpact.NEUTRAL

    def _analyze_public_impact(self, text: str, concepts: list[ConceptualEntity] = None) -> StakeholderImpact:
        """Analyze impact on general public."""
        # Public impact is heavily influenced by controversy and hot takes
        controversial_indicators = ['controversial', 'divisive', 'polarizing', 'offensive']
        controversy_score = sum(1 for indicator in controversial_indicators if indicator in text)

        if concepts:
            hot_takes = [c for c in concepts if c.concept_type == 'HOT_TAKE']
            controversy_score += len(hot_takes)

        if controversy_score > 2:
            return StakeholderImpact.CRISIS
        elif controversy_score > 1:
            return StakeholderImpact.NEGATIVE
        else:
            return StakeholderImpact.NEUTRAL

    def _calculate_sentiment_confidence(self, text: str) -> float:
        """Calculate confidence in sentiment analysis."""
        # Simple heuristic based on text length and signal strength
        word_count = len(text.split())
        if word_count < 10:
            return 0.3
        elif word_count < 50:
            return 0.6
        else:
            return 0.8


class BrandSafetyAnalyzer:
    """Main brand safety and risk assessment engine."""

    def __init__(self, brand_profile: BrandProfile = BrandProfile.MODERATE):
        self.brand_profile = brand_profile
        self.viral_engine = ViralPredictionEngine()
        self.toxicity_detector = ToxicityDetector()
        self.controversy_detector = ControversyDetector()
        self.stakeholder_analyzer = StakeholderImpactAnalyzer()

        # Risk thresholds by brand profile
        self.safety_thresholds = {
            BrandProfile.CONSERVATIVE: {
                BrandSafetyLevel.SAFE: 0.2,
                BrandSafetyLevel.CAUTION: 0.4,
                BrandSafetyLevel.RISK: 0.6,
                BrandSafetyLevel.DANGER: 1.0
            },
            BrandProfile.MODERATE: {
                BrandSafetyLevel.SAFE: 0.3,
                BrandSafetyLevel.CAUTION: 0.5,
                BrandSafetyLevel.RISK: 0.7,
                BrandSafetyLevel.DANGER: 1.0
            },
            BrandProfile.AGGRESSIVE: {
                BrandSafetyLevel.SAFE: 0.4,
                BrandSafetyLevel.CAUTION: 0.6,
                BrandSafetyLevel.RISK: 0.8,
                BrandSafetyLevel.DANGER: 1.0
            }
        }

        # Risk dimension weights
        self.risk_weights = {
            RiskDimension.REPUTATIONAL: 0.35,
            RiskDimension.LEGAL: 0.25,
            RiskDimension.FINANCIAL: 0.25,
            RiskDimension.OPERATIONAL: 0.15
        }

    async def assess_brand_safety(self, text: str, platform: Platform = Platform.GENERAL,
                                 content_id: str = None, concepts: list[ConceptualEntity] = None,
                                 context: dict[str, Any] = None) -> BrandSafetyAssessment:
        """Comprehensive brand safety assessment."""
        try:
            # Generate content ID if not provided
            if content_id is None:
                content_id = f"safety_{hashlib.md5(text.encode()).hexdigest()[:12]}_{int(datetime.utcnow().timestamp())}"

            # Run parallel assessments
            toxicity_task = self.toxicity_detector.assess_toxicity(text)
            controversy_task = self.controversy_detector.analyze_controversy(text, concepts)
            stakeholder_task = self.stakeholder_analyzer.analyze_stakeholder_impact(text, concepts)
            viral_task = self.viral_engine.predict_viral_potential(text, platform, content_id, context)

            # Await all assessments
            toxicity_assessment, controversy_analysis, stakeholder_analysis, viral_prediction = await asyncio.gather(
                toxicity_task, controversy_task, stakeholder_task, viral_task
            )

            # Calculate multi-dimensional risk scores
            risk_score = self._calculate_risk_scores(
                text, toxicity_assessment, controversy_analysis, stakeholder_analysis, viral_prediction
            )

            # Determine safety level
            safety_level = self._determine_safety_level(risk_score.overall)

            # Classify content type
            content_classification = self._classify_content_safety(
                text, toxicity_assessment, controversy_analysis
            )

            # Crisis risk assessment
            crisis_risk = self._assess_crisis_risk(
                text, toxicity_assessment, controversy_analysis, viral_prediction
            )

            # Brand alignment analysis
            brand_alignment_score = self._calculate_brand_alignment(text, concepts)
            message_consistency_score = self._calculate_message_consistency(text, context)

            # Risk-adjusted viral score
            risk_adjusted_viral_score = self._calculate_risk_adjusted_viral_score(
                viral_prediction.overall_viral_score, risk_score.overall
            )

            # Identify risk factors and red flags
            risk_factors = self._identify_risk_factors(
                toxicity_assessment, controversy_analysis, stakeholder_analysis
            )
            crisis_triggers = self._identify_crisis_triggers(text, controversy_analysis)
            red_flags = self._identify_red_flags(toxicity_assessment, controversy_analysis)

            # Generate mitigation strategy
            mitigation_strategy = self._generate_mitigation_strategy(
                safety_level, risk_score, crisis_risk
            )

            # Content modification suggestions
            content_modifications = self._suggest_content_modifications(
                text, toxicity_assessment, controversy_analysis
            )

            # Approval workflow
            approval_workflow = self._determine_approval_workflow(safety_level, risk_score)

            # Monitoring setup
            monitoring_keywords = self._generate_monitoring_keywords(text, concepts)
            alert_thresholds = self._set_alert_thresholds(safety_level)

            # Calculate assessment confidence
            confidence = self._calculate_assessment_confidence(
                toxicity_assessment, controversy_analysis, stakeholder_analysis
            )

            return BrandSafetyAssessment(
                content_id=content_id,
                platform=platform,
                brand_profile=self.brand_profile,
                safety_level=safety_level,
                content_classification=content_classification,
                risk_score=risk_score,
                confidence=confidence,
                stakeholder_analysis=stakeholder_analysis,
                toxicity_assessment=toxicity_assessment,
                controversy_analysis=controversy_analysis,
                crisis_risk=crisis_risk,
                brand_alignment_score=brand_alignment_score,
                message_consistency_score=message_consistency_score,
                risk_factors=risk_factors,
                crisis_triggers=crisis_triggers,
                red_flags=red_flags,
                viral_prediction=viral_prediction,
                risk_adjusted_viral_score=risk_adjusted_viral_score,
                mitigation_strategy=mitigation_strategy,
                content_modifications=content_modifications,
                approval_workflow=approval_workflow,
                monitoring_keywords=monitoring_keywords,
                alert_thresholds=alert_thresholds
            )

        except Exception as e:
            logger.error(f"Error in brand safety assessment: {str(e)}")
            return self._create_default_assessment(content_id or "unknown", platform, text)

    def _calculate_risk_scores(self, text: str, toxicity: ToxicityAssessment,
                              controversy: ControversyAnalysis, stakeholders: StakeholderAnalysis,
                              viral: ViralPrediction) -> RiskScore:
        """Calculate multi-dimensional risk scores."""

        # Reputational risk
        reputational_risk = (
            toxicity.toxicity_score * 0.3 +
            controversy.controversy_score * 0.3 +
            controversy.backlash_potential * 0.2 +
            (1.0 if stakeholders.general_public == StakeholderImpact.CRISIS else 0.0) * 0.2
        )

        # Legal risk
        legal_risk = (
            toxicity.hate_speech_score * 0.4 +
            toxicity.threat_score * 0.3 +
            toxicity.harassment_score * 0.2 +
            controversy.polarization_risk * 0.1
        )

        # Financial risk
        financial_risk = (
            (1.0 if stakeholders.customers == StakeholderImpact.CRISIS else 0.0) * 0.3 +
            (1.0 if stakeholders.investors == StakeholderImpact.CRISIS else 0.0) * 0.3 +
            controversy.backlash_potential * 0.2 +
            viral.controversy_score * 0.2
        )

        # Operational risk
        operational_risk = (
            (1.0 if stakeholders.employees == StakeholderImpact.CRISIS else 0.0) * 0.4 +
            (1.0 if stakeholders.partners == StakeholderImpact.NEGATIVE else 0.0) * 0.3 +
            controversy.controversy_score * 0.3
        )

        # Overall risk (weighted average)
        overall_risk = (
            reputational_risk * self.risk_weights[RiskDimension.REPUTATIONAL] +
            legal_risk * self.risk_weights[RiskDimension.LEGAL] +
            financial_risk * self.risk_weights[RiskDimension.FINANCIAL] +
            operational_risk * self.risk_weights[RiskDimension.OPERATIONAL]
        )

        return RiskScore(
            reputational=min(1.0, reputational_risk),
            legal=min(1.0, legal_risk),
            financial=min(1.0, financial_risk),
            operational=min(1.0, operational_risk),
            overall=min(1.0, overall_risk)
        )

    def _determine_safety_level(self, overall_risk: float) -> BrandSafetyLevel:
        """Determine safety level based on overall risk score."""
        thresholds = self.safety_thresholds[self.brand_profile]

        if overall_risk <= thresholds[BrandSafetyLevel.SAFE]:
            return BrandSafetyLevel.SAFE
        elif overall_risk <= thresholds[BrandSafetyLevel.CAUTION]:
            return BrandSafetyLevel.CAUTION
        elif overall_risk <= thresholds[BrandSafetyLevel.RISK]:
            return BrandSafetyLevel.RISK
        else:
            return BrandSafetyLevel.DANGER

    def _classify_content_safety(self, text: str, toxicity: ToxicityAssessment,
                               controversy: ControversyAnalysis) -> ContentClassification:
        """Classify content type for brand safety."""

        if toxicity.toxicity_score > 0.7:
            return ContentClassification.TOXIC
        elif controversy.controversy_score > 0.6:
            return ContentClassification.CONTROVERSIAL
        elif self._is_opinion_content(text):
            return ContentClassification.OPINION
        elif self._is_personal_content(text):
            return ContentClassification.PERSONAL
        else:
            return ContentClassification.PROFESSIONAL

    def _is_opinion_content(self, text: str) -> bool:
        """Check if content is opinion-based."""
        opinion_indicators = [
            'i think', 'i believe', 'in my opinion', 'i feel', 'personally',
            'my view', 'my perspective', 'i would argue', 'hot take'
        ]
        text_lower = text.lower()
        return any(indicator in text_lower for indicator in opinion_indicators)

    def _is_personal_content(self, text: str) -> bool:
        """Check if content is personal in nature."""
        personal_indicators = [
            'my experience', 'happened to me', 'my story', 'personal journey',
            'my life', 'my family', 'when i was', 'i remember'
        ]
        text_lower = text.lower()
        return any(indicator in text_lower for indicator in personal_indicators)

    def _assess_crisis_risk(self, text: str, toxicity: ToxicityAssessment,
                          controversy: ControversyAnalysis, viral: ViralPrediction) -> CrisisRiskAssessment:
        """Assess crisis escalation risk."""

        # Escalation probability
        escalation_factors = [
            toxicity.severe_toxicity_score,
            controversy.backlash_potential,
            controversy.polarization_risk,
            viral.controversy_score
        ]
        escalation_probability = max(escalation_factors)

        # Viral amplification risk
        viral_amplification_risk = viral.overall_viral_score * controversy.controversy_score

        # Media attention risk
        media_attention_risk = min(1.0,
            controversy.controversy_score * 0.5 +
            viral.reach_potential * 0.3 +
            escalation_probability * 0.2
        )

        # Response urgency
        if escalation_probability > 0.8:
            response_urgency = "immediate"
            mitigation_window = timedelta(hours=1)
        elif escalation_probability > 0.6:
            response_urgency = "within_hours"
            mitigation_window = timedelta(hours=6)
        else:
            response_urgency = "within_days"
            mitigation_window = timedelta(days=1)

        # Crisis triggers
        crisis_triggers = []
        if toxicity.hate_speech_score > 0.5:
            crisis_triggers.append("Hate speech content")
        if controversy.polarization_risk > 0.7:
            crisis_triggers.append("Highly polarizing content")
        if viral.controversy_score > 0.6:
            crisis_triggers.append("Controversial viral potential")

        return CrisisRiskAssessment(
            escalation_probability=escalation_probability,
            viral_amplification_risk=viral_amplification_risk,
            media_attention_risk=media_attention_risk,
            response_urgency=response_urgency,
            crisis_triggers=crisis_triggers,
            mitigation_window=mitigation_window
        )

    def _calculate_brand_alignment(self, text: str, concepts: list[ConceptualEntity] = None) -> float:
        """Calculate brand value alignment score."""
        # Simplified brand alignment based on positive indicators
        positive_brand_indicators = [
            'innovation', 'quality', 'trust', 'integrity', 'excellence',
            'customer', 'value', 'service', 'responsibility', 'transparency'
        ]

        negative_brand_indicators = [
            'scandal', 'controversy', 'problem', 'failure', 'issue',
            'complaint', 'criticism', 'negative', 'poor', 'bad'
        ]

        text_lower = text.lower()
        positive_score = sum(1 for indicator in positive_brand_indicators if indicator in text_lower)
        negative_score = sum(1 for indicator in negative_brand_indicators if indicator in text_lower)

        # Normalize to 0-1 scale
        total_indicators = positive_score + negative_score
        if total_indicators == 0:
            return 0.7  # Neutral alignment

        return positive_score / total_indicators

    def _calculate_message_consistency(self, text: str, context: dict[str, Any] = None) -> float:
        """Calculate brand message consistency."""
        # Simplified consistency check - in reality would compare against brand guidelines
        consistency_indicators = [
            'professional', 'reliable', 'trustworthy', 'innovative',
            'customer-focused', 'quality', 'excellence'
        ]

        text_lower = text.lower()
        matches = sum(1 for indicator in consistency_indicators if indicator in text_lower)

        return min(1.0, matches / 3.0)  # Normalize based on expected indicators

    def _calculate_risk_adjusted_viral_score(self, viral_score: float, risk_score: float) -> float:
        """Calculate viral score adjusted for brand safety risks."""
        # Apply risk penalty to viral score
        risk_penalty = risk_score * 0.5  # 50% penalty at maximum risk
        return max(0.0, viral_score * (1.0 - risk_penalty))

    def _identify_risk_factors(self, toxicity: ToxicityAssessment,
                              controversy: ControversyAnalysis,
                              stakeholders: StakeholderAnalysis) -> list[str]:
        """Identify specific risk factors."""
        risk_factors = []

        if toxicity.toxicity_score > 0.5:
            risk_factors.append("High toxicity content")
        if toxicity.hate_speech_score > 0.3:
            risk_factors.append("Potential hate speech")
        if toxicity.threat_score > 0.3:
            risk_factors.append("Threatening language")
        if controversy.controversy_score > 0.6:
            risk_factors.append("Highly controversial content")
        if controversy.polarization_risk > 0.5:
            risk_factors.append("Polarizing content")
        if stakeholders.general_public == StakeholderImpact.CRISIS:
            risk_factors.append("Public relations crisis risk")

        return risk_factors[:10]  # Return top 10 risk factors

    def _identify_crisis_triggers(self, text: str, controversy: ControversyAnalysis) -> list[str]:
        """Identify potential crisis triggers."""
        triggers = []

        crisis_patterns = [
            'scandal', 'corruption', 'fraud', 'lawsuit', 'investigation',
            'boycott', 'protest', 'outrage', 'backlash', 'controversy'
        ]

        text_lower = text.lower()
        for pattern in crisis_patterns:
            if pattern in text_lower:
                triggers.append(f"Contains '{pattern}' reference")

        if controversy.divisive_topics:
            triggers.extend([f"Mentions divisive topic: {topic}" for topic in controversy.divisive_topics[:3]])

        return triggers[:5]  # Return top 5 triggers

    def _identify_red_flags(self, toxicity: ToxicityAssessment, controversy: ControversyAnalysis) -> list[str]:
        """Identify content red flags."""
        red_flags = []

        if toxicity.severe_toxicity_score > 0.5:
            red_flags.append("Severe toxicity detected")
        if toxicity.hate_speech_score > 0.4:
            red_flags.append("Hate speech indicators")
        if toxicity.threat_score > 0.4:
            red_flags.append("Threatening content")
        if controversy.backlash_potential > 0.7:
            red_flags.append("High backlash potential")
        if controversy.polarization_risk > 0.7:
            red_flags.append("Extreme polarization risk")

        return red_flags

    def _generate_mitigation_strategy(self, safety_level: BrandSafetyLevel,
                                    risk_score: RiskScore,
                                    crisis_risk: CrisisRiskAssessment) -> MitigationStrategy:
        """Generate risk mitigation strategy."""

        if safety_level == BrandSafetyLevel.DANGER:
            return MitigationStrategy(
                priority="critical",
                actions=[
                    "Immediate content review required",
                    "Senior management approval needed",
                    "Legal team consultation",
                    "Crisis communication plan activation"
                ],
                approval_required=True,
                monitoring_required=True,
                alternative_approaches=[
                    "Rewrite content completely",
                    "Consider alternative messaging",
                    "Postpone publication until review"
                ],
                decision_deadline=datetime.utcnow() + timedelta(hours=1)
            )
        elif safety_level == BrandSafetyLevel.RISK:
            return MitigationStrategy(
                priority="high",
                actions=[
                    "Content modification required",
                    "Management approval needed",
                    "Monitor for early warning signs",
                    "Prepare response strategy"
                ],
                approval_required=True,
                monitoring_required=True,
                alternative_approaches=[
                    "Tone down controversial elements",
                    "Add disclaimers or context",
                    "Focus on positive messaging"
                ],
                decision_deadline=datetime.utcnow() + timedelta(hours=6)
            )
        elif safety_level == BrandSafetyLevel.CAUTION:
            return MitigationStrategy(
                priority="medium",
                actions=[
                    "Review content for improvements",
                    "Monitor engagement closely",
                    "Be prepared to respond quickly"
                ],
                approval_required=False,
                monitoring_required=True,
                alternative_approaches=[
                    "Minor content adjustments",
                    "Add positive framing",
                    "Include balanced perspective"
                ],
                decision_deadline=datetime.utcnow() + timedelta(days=1)
            )
        else:  # SAFE
            return MitigationStrategy(
                priority="low",
                actions=[
                    "Standard monitoring",
                    "Normal publication process"
                ],
                approval_required=False,
                monitoring_required=False,
                alternative_approaches=[],
                decision_deadline=None
            )

    def _suggest_content_modifications(self, text: str, toxicity: ToxicityAssessment,
                                     controversy: ControversyAnalysis) -> list[str]:
        """Suggest specific content modifications."""
        modifications = []

        if toxicity.profanity_score > 0.3:
            modifications.append("Remove or replace profanity")
        if toxicity.harassment_score > 0.3:
            modifications.append("Reduce negative emotional language")
        if controversy.polarization_risk > 0.5:
            modifications.append("Add balanced perspective or disclaimers")
        if controversy.controversy_score > 0.5:
            modifications.append("Consider less controversial framing")

        # General improvements
        if not any(phrase in text.lower() for phrase in ['in my opinion', 'i believe', 'perspective']):
            modifications.append("Add personal perspective framing")

        return modifications[:5]  # Return top 5 modifications

    def _determine_approval_workflow(self, safety_level: BrandSafetyLevel, risk_score: RiskScore) -> list[str]:
        """Determine required approval workflow steps."""
        workflow = []

        if safety_level == BrandSafetyLevel.DANGER:
            workflow = [
                "Legal team review",
                "Senior management approval",
                "Board notification",
                "Crisis team standby"
            ]
        elif safety_level == BrandSafetyLevel.RISK:
            workflow = [
                "Management approval",
                "Legal review if applicable",
                "Communication team review"
            ]
        elif safety_level == BrandSafetyLevel.CAUTION:
            workflow = [
                "Supervisor review",
                "Communication team consultation"
            ]
        else:  # SAFE
            workflow = ["Standard approval process"]

        return workflow

    def _generate_monitoring_keywords(self, text: str, concepts: list[ConceptualEntity] = None) -> list[str]:
        """Generate keywords for monitoring mentions and sentiment."""
        keywords = []

        # Extract key terms from text
        words = text.lower().split()
        important_words = [word for word in words if len(word) > 4 and word.isalpha()]
        keywords.extend(important_words[:5])

        # Add concept-based keywords
        if concepts:
            for concept in concepts[:3]:
                if concept.text:
                    keywords.append(concept.text.lower())

        # Add brand safety keywords
        safety_keywords = ['controversy', 'backlash', 'criticism', 'negative', 'scandal']
        keywords.extend(safety_keywords)

        return list(set(keywords))[:10]  # Return unique keywords, max 10

    def _set_alert_thresholds(self, safety_level: BrandSafetyLevel) -> dict[str, float]:
        """Set alert thresholds based on safety level."""
        base_thresholds = {
            "negative_sentiment": 0.7,
            "mention_volume": 100,
            "engagement_spike": 2.0,
            "controversy_score": 0.6
        }

        # Adjust thresholds based on safety level
        if safety_level == BrandSafetyLevel.DANGER:
            multiplier = 0.5  # More sensitive alerts
        elif safety_level == BrandSafetyLevel.RISK:
            multiplier = 0.7
        elif safety_level == BrandSafetyLevel.CAUTION:
            multiplier = 0.8
        else:  # SAFE
            multiplier = 1.0

        return {key: value * multiplier for key, value in base_thresholds.items()}

    def _calculate_assessment_confidence(self, toxicity: ToxicityAssessment,
                                       controversy: ControversyAnalysis,
                                       stakeholders: StakeholderAnalysis) -> float:
        """Calculate overall assessment confidence."""
        # Base confidence on signal strength and completeness
        toxicity_signals = sum([
            toxicity.toxicity_score > 0.1,
            toxicity.hate_speech_score > 0.1,
            toxicity.harassment_score > 0.1,
            toxicity.profanity_score > 0.1
        ])

        controversy_signals = sum([
            controversy.controversy_score > 0.1,
            len(controversy.divisive_topics) > 0,
            controversy.polarization_risk > 0.1
        ])

        stakeholder_signals = sum([
            stakeholders.customers != StakeholderImpact.NEUTRAL,
            stakeholders.employees != StakeholderImpact.NEUTRAL,
            stakeholders.general_public != StakeholderImpact.NEUTRAL
        ])

        total_signals = toxicity_signals + controversy_signals + stakeholder_signals
        max_signals = 10  # Maximum possible signals

        signal_strength = total_signals / max_signals
        base_confidence = 0.6  # Base confidence level

        return min(1.0, base_confidence + (signal_strength * 0.4))

    def _create_default_assessment(self, content_id: str, platform: Platform, text: str) -> BrandSafetyAssessment:
        """Create a safe default assessment when errors occur."""
        return BrandSafetyAssessment(
            content_id=content_id,
            platform=platform,
            brand_profile=self.brand_profile,
            safety_level=BrandSafetyLevel.CAUTION,
            content_classification=ContentClassification.PROFESSIONAL,
            risk_score=RiskScore(
                reputational=0.5,
                legal=0.3,
                financial=0.3,
                operational=0.3,
                overall=0.4
            ),
            confidence=0.1,
            stakeholder_analysis=StakeholderAnalysis(
                customers=StakeholderImpact.NEUTRAL,
                employees=StakeholderImpact.NEUTRAL,
                investors=StakeholderImpact.NEUTRAL,
                partners=StakeholderImpact.NEUTRAL,
                general_public=StakeholderImpact.NEUTRAL,
                sentiment_confidence=0.1
            ),
            toxicity_assessment=ToxicityAssessment(
                toxicity_score=0.0,
                hate_speech_score=0.0,
                harassment_score=0.0,
                profanity_score=0.0,
                threat_score=0.0,
                identity_attack_score=0.0,
                severe_toxicity_score=0.0
            ),
            controversy_analysis=ControversyAnalysis(
                controversy_score=0.0,
                controversy_type="unknown",
                polarization_risk=0.0,
                backlash_potential=0.0,
                divisive_topics=[],
                sensitivity_areas=[]
            ),
            crisis_risk=CrisisRiskAssessment(
                escalation_probability=0.3,
                viral_amplification_risk=0.2,
                media_attention_risk=0.2,
                response_urgency="within_days",
                crisis_triggers=["Insufficient analysis data"],
                mitigation_window=timedelta(days=1)
            ),
            brand_alignment_score=0.5,
            message_consistency_score=0.5,
            risk_factors=["Insufficient data for full analysis"],
            crisis_triggers=["Error in assessment process"],
            red_flags=["Analysis incomplete"],
            risk_adjusted_viral_score=0.3,
            mitigation_strategy=MitigationStrategy(
                priority="medium",
                actions=["Manual review required", "Complete analysis before publication"],
                approval_required=True,
                monitoring_required=True,
                alternative_approaches=["Delay publication until proper analysis"],
                decision_deadline=datetime.utcnow() + timedelta(hours=24)
            ),
            content_modifications=["Complete brand safety analysis before proceeding"],
            approval_workflow=["Manual review required"],
            monitoring_keywords=["error", "analysis", "review"],
            alert_thresholds={"manual_review": 1.0}
        )


# Integration functions for API and existing systems
async def assess_content_safety(text: str, platform: Platform = Platform.GENERAL,
                              brand_profile: BrandProfile = BrandProfile.MODERATE,
                              concepts: list[ConceptualEntity] = None) -> BrandSafetyAssessment:
    """Quick function to assess content brand safety."""
    analyzer = BrandSafetyAnalyzer(brand_profile)
    return await analyzer.assess_brand_safety(text, platform, concepts=concepts)


async def quick_safety_check(text: str) -> BrandSafetyLevel:
    """Quick safety level check for content."""
    analyzer = BrandSafetyAnalyzer()
    assessment = await analyzer.assess_brand_safety(text)
    return assessment.safety_level


async def get_risk_mitigation_strategy(text: str, platform: Platform = Platform.GENERAL) -> MitigationStrategy:
    """Get risk mitigation strategy for content."""
    analyzer = BrandSafetyAnalyzer()
    assessment = await analyzer.assess_brand_safety(text, platform)
    return assessment.mitigation_strategy


# For integration with viral prediction engine
async def assess_viral_content_safety(viral_prediction: ViralPrediction,
                                    text: str, concepts: list[ConceptualEntity] = None) -> BrandSafetyAssessment:
    """Assess brand safety for content that has viral prediction."""
    analyzer = BrandSafetyAnalyzer()
    assessment = await analyzer.assess_brand_safety(
        text, viral_prediction.platform, viral_prediction.content_id, concepts
    )
    # Update with existing viral prediction
    assessment.viral_prediction = viral_prediction
    return assessment
