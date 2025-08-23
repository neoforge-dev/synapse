"""
Lead scoring system for consultation opportunity evaluation.

Provides advanced scoring algorithms that complement the lead detection engine.
"""

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from enum import Enum

from .lead_detector import ConsultationLead, InquiryType

logger = logging.getLogger(__name__)


class ScoreFactor(Enum):
    """Factors that influence lead scoring."""
    INQUIRY_TYPE = "inquiry_type"
    COMPANY_SIZE = "company_size"
    AUTHOR_SENIORITY = "author_seniority"
    TECHNICAL_COMPLEXITY = "technical_complexity"
    URGENCY = "urgency"
    ENGAGEMENT_QUALITY = "engagement_quality"
    BUSINESS_CONTEXT = "business_context"


@dataclass
class LeadScore:
    """Comprehensive lead score with breakdown by factors."""
    total_score: int  # 1-10 scale
    confidence: float  # 0.0-1.0
    estimated_value: int  # Euros
    priority: str  # "low", "medium", "high", "critical"
    score_breakdown: Dict[ScoreFactor, int]
    reasoning: List[str]
    calculated_at: datetime


class LeadScorer:
    """
    Advanced lead scoring system for consultation opportunities.
    
    Provides detailed scoring breakdown and reasoning to help prioritize
    consultation opportunities effectively.
    """
    
    def __init__(self):
        """Initialize the lead scorer with scoring weights and thresholds."""
        self.factor_weights = {
            ScoreFactor.INQUIRY_TYPE: 0.25,
            ScoreFactor.COMPANY_SIZE: 0.20,
            ScoreFactor.AUTHOR_SENIORITY: 0.20,
            ScoreFactor.TECHNICAL_COMPLEXITY: 0.10,
            ScoreFactor.URGENCY: 0.15,
            ScoreFactor.ENGAGEMENT_QUALITY: 0.10
        }
        
        self.inquiry_type_scores = {
            InquiryType.FRACTIONAL_CTO: 10,
            InquiryType.TECHNICAL_ARCHITECTURE: 8,
            InquiryType.STARTUP_SCALING: 7,
            InquiryType.NOBUILD_AUDIT: 6,
            InquiryType.TEAM_BUILDING: 5,
            InquiryType.HIRING_STRATEGY: 4,
            InquiryType.ENGINEERING_EFFICIENCY: 5,
            InquiryType.GENERAL_CONSULTATION: 3
        }
        
        logger.info("Lead scorer initialized with weighted scoring model")
    
    def score_lead(self, lead: ConsultationLead) -> LeadScore:
        """
        Generate comprehensive score for a consultation lead.
        
        Args:
            lead: ConsultationLead to score
            
        Returns:
            LeadScore with detailed breakdown and reasoning
        """
        score_breakdown = {}
        reasoning = []
        
        # Score by inquiry type
        inquiry_score = self._score_inquiry_type(lead.inquiry_type)
        score_breakdown[ScoreFactor.INQUIRY_TYPE] = inquiry_score
        reasoning.append(f"Inquiry type '{lead.inquiry_type.value}' scored {inquiry_score}/10")
        
        # Score by company size
        company_score = self._score_company_size(lead.company_size, lead.author_info)
        score_breakdown[ScoreFactor.COMPANY_SIZE] = company_score
        reasoning.append(f"Company size '{lead.company_size}' scored {company_score}/10")
        
        # Score by author seniority
        seniority_score = self._score_author_seniority(lead.author_info)
        score_breakdown[ScoreFactor.AUTHOR_SENIORITY] = seniority_score
        reasoning.append(f"Author seniority scored {seniority_score}/10")
        
        # Score by technical complexity
        complexity_score = self._score_technical_complexity(lead.technical_complexity)
        score_breakdown[ScoreFactor.TECHNICAL_COMPLEXITY] = complexity_score
        reasoning.append(f"Technical complexity '{lead.technical_complexity}' scored {complexity_score}/10")
        
        # Score by urgency indicators
        urgency_score = self._score_urgency(lead.urgency_indicators)
        score_breakdown[ScoreFactor.URGENCY] = urgency_score
        reasoning.append(f"Urgency indicators ({len(lead.urgency_indicators)}) scored {urgency_score}/10")
        
        # Score by engagement quality
        engagement_score = self._score_engagement_quality(lead.content_text)
        score_breakdown[ScoreFactor.ENGAGEMENT_QUALITY] = engagement_score
        reasoning.append(f"Engagement quality scored {engagement_score}/10")
        
        # Calculate weighted total score
        total_score = self._calculate_weighted_score(score_breakdown)
        
        # Calculate confidence based on available data quality
        confidence = self._calculate_confidence(lead, score_breakdown)
        
        # Estimate business value
        estimated_value = self._estimate_business_value(lead, total_score)
        
        # Determine priority
        priority = self._determine_priority(total_score, lead.inquiry_type, urgency_score)
        
        reasoning.append(f"Final weighted score: {total_score}/10 (confidence: {confidence:.2f})")
        
        return LeadScore(
            total_score=total_score,
            confidence=confidence,
            estimated_value=estimated_value,
            priority=priority,
            score_breakdown=score_breakdown,
            reasoning=reasoning,
            calculated_at=datetime.now()
        )
    
    def _score_inquiry_type(self, inquiry_type: InquiryType) -> int:
        """Score based on the type of consultation inquiry."""
        return self.inquiry_type_scores.get(inquiry_type, 3)
    
    def _score_company_size(self, company_size: str, author_info: Dict) -> int:
        """Score based on company size and growth stage."""
        if "Enterprise" in company_size:
            return 9
        elif "Growth Stage" in company_size:
            return 7
        elif "Early Stage" in company_size:
            return 6
        elif "Startup" in company_size:
            return 5
        else:
            # Try to infer from author info
            title = author_info.get('title', '').lower()
            company = author_info.get('company', '').lower()
            
            if any(term in title + company for term in ['enterprise', 'corp', 'inc']):
                return 8
            elif any(term in title + company for term in ['startup', 'co-founder']):
                return 5
            else:
                return 3
    
    def _score_author_seniority(self, author_info: Dict) -> int:
        """Score based on author's seniority and decision-making power."""
        title = author_info.get('title', '').lower()
        
        # C-level executives
        if any(role in title for role in ['cto', 'ceo', 'cio', 'chief']):
            return 10
        
        # VP level
        elif any(role in title for role in ['vp', 'vice president']):
            return 9
        
        # Director/Head level
        elif any(role in title for role in ['director', 'head of', 'principal']):
            return 8
        
        # Founder/Owner
        elif any(role in title for role in ['founder', 'co-founder', 'owner']):
            return 9
        
        # Senior manager
        elif any(role in title for role in ['senior manager', 'engineering manager', 'technical manager']):
            return 7
        
        # Lead/Senior Engineer
        elif any(role in title for role in ['tech lead', 'senior engineer', 'staff engineer']):
            return 6
        
        # Mid-level
        elif any(role in title for role in ['engineer', 'developer', 'analyst']):
            return 4
        
        else:
            return 3
    
    def _score_technical_complexity(self, complexity: str) -> int:
        """Score based on technical complexity of the challenge."""
        complexity_scores = {
            "High": 8,
            "Medium": 6,
            "Low": 4,
            "Unknown": 5
        }
        return complexity_scores.get(complexity, 5)
    
    def _score_urgency(self, urgency_indicators: List[str]) -> int:
        """Score based on urgency indicators found in content."""
        if len(urgency_indicators) >= 3:
            return 9
        elif len(urgency_indicators) == 2:
            return 7
        elif len(urgency_indicators) == 1:
            return 5
        else:
            return 3
    
    def _score_engagement_quality(self, content: str) -> int:
        """Score based on the quality and depth of engagement."""
        content_lower = content.lower()
        
        score = 5  # Base score
        
        # Length indicates thoughtfulness
        if len(content) > 200:
            score += 2
        elif len(content) > 100:
            score += 1
        
        # Specific questions indicate genuine interest
        question_count = content.count('?')
        score += min(question_count, 2)
        
        # Business context indicates serious inquiry
        business_terms = ['budget', 'timeline', 'team', 'company', 'project', 'challenge']
        business_mentions = sum(1 for term in business_terms if term in content_lower)
        score += min(business_mentions, 2)
        
        # Personal pronouns indicate direct engagement
        if any(pronoun in content_lower for pronoun in ['we', 'our', 'us', 'i am', "we're"]):
            score += 1
        
        return min(score, 10)
    
    def _calculate_weighted_score(self, score_breakdown: Dict[ScoreFactor, int]) -> int:
        """Calculate weighted total score from individual factor scores."""
        weighted_sum = 0.0
        
        for factor, score in score_breakdown.items():
            weight = self.factor_weights.get(factor, 0.1)
            weighted_sum += score * weight
        
        return max(1, min(10, round(weighted_sum)))
    
    def _calculate_confidence(self, lead: ConsultationLead, score_breakdown: Dict[ScoreFactor, int]) -> float:
        """Calculate confidence level based on data quality and completeness."""
        confidence = 0.6  # Base confidence
        
        # More data = higher confidence
        if lead.author_info.get('title'):
            confidence += 0.1
        if lead.author_info.get('company'):
            confidence += 0.1
        if lead.company_size != "Unknown":
            confidence += 0.1
        if lead.technical_complexity != "Unknown":
            confidence += 0.1
        if len(lead.urgency_indicators) > 0:
            confidence += 0.1
        
        # High scores with good data = higher confidence
        avg_score = sum(score_breakdown.values()) / len(score_breakdown)
        if avg_score >= 7:
            confidence += 0.1
        elif avg_score >= 5:
            confidence += 0.05
        
        return min(confidence, 1.0)
    
    def _estimate_business_value(self, lead: ConsultationLead, total_score: int) -> int:
        """Estimate potential business value of the lead."""
        # Base value from inquiry type
        base_value = {
            InquiryType.FRACTIONAL_CTO: 75000,
            InquiryType.TECHNICAL_ARCHITECTURE: 40000,
            InquiryType.STARTUP_SCALING: 35000,
            InquiryType.NOBUILD_AUDIT: 20000,
            InquiryType.TEAM_BUILDING: 25000,
            InquiryType.HIRING_STRATEGY: 15000,
            InquiryType.ENGINEERING_EFFICIENCY: 20000,
            InquiryType.GENERAL_CONSULTATION: 10000
        }.get(lead.inquiry_type, 10000)
        
        # Apply score multiplier
        score_multiplier = max(0.3, total_score / 10.0)
        
        # Company size multiplier
        company_multiplier = 1.0
        if "Enterprise" in lead.company_size:
            company_multiplier = 1.5
        elif "Growth Stage" in lead.company_size:
            company_multiplier = 1.2
        
        # Urgency multiplier
        urgency_multiplier = 1.0 + (len(lead.urgency_indicators) * 0.1)
        
        final_value = int(base_value * score_multiplier * company_multiplier * urgency_multiplier)
        return final_value
    
    def _determine_priority(self, total_score: int, inquiry_type: InquiryType, urgency_score: int) -> str:
        """Determine priority level for the lead."""
        if total_score >= 9 or inquiry_type == InquiryType.FRACTIONAL_CTO:
            return "critical"
        elif total_score >= 7 or urgency_score >= 7:
            return "high"
        elif total_score >= 5:
            return "medium"
        else:
            return "low"
    
    def compare_leads(self, leads: List[ConsultationLead]) -> List[Tuple[ConsultationLead, LeadScore]]:
        """
        Score and rank multiple leads by priority.
        
        Args:
            leads: List of ConsultationLead objects to score and rank
            
        Returns:
            List of (lead, score) tuples sorted by priority
        """
        scored_leads = [(lead, self.score_lead(lead)) for lead in leads]
        
        # Sort by total score descending, then by estimated value
        scored_leads.sort(key=lambda x: (x[1].total_score, x[1].estimated_value), reverse=True)
        
        logger.info(f"Scored and ranked {len(leads)} leads")
        return scored_leads
    
    def get_scoring_explanation(self, lead_score: LeadScore) -> str:
        """
        Generate human-readable explanation of the scoring.
        
        Args:
            lead_score: LeadScore to explain
            
        Returns:
            Formatted explanation string
        """
        explanation = f"Lead Score: {lead_score.total_score}/10 ({lead_score.priority} priority)\n"
        explanation += f"Confidence: {lead_score.confidence:.2%}\n"
        explanation += f"Estimated Value: €{lead_score.estimated_value:,}\n\n"
        
        explanation += "Scoring Breakdown:\n"
        for factor, score in lead_score.score_breakdown.items():
            explanation += f"  {factor.value.replace('_', ' ').title()}: {score}/10\n"
        
        explanation += "\nReasoning:\n"
        for reason in lead_score.reasoning:
            explanation += f"  • {reason}\n"
        
        return explanation