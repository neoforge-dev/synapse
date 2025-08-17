"""API router for brand safety and risk assessment (Epic 7.2)."""

import asyncio
import logging
from typing import Any, Dict, List, Optional
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from graph_rag.api.dependencies import get_concept_extractor
from graph_rag.core.brand_safety_analyzer import (
    BrandSafetyAnalyzer, BrandSafetyAssessment, BrandProfile, BrandSafetyLevel,
    ContentClassification, StakeholderImpact, RiskDimension, MitigationStrategy,
    assess_content_safety, quick_safety_check, get_risk_mitigation_strategy
)
from graph_rag.core.viral_prediction_engine import Platform, ViralPredictionEngine
from graph_rag.core.concept_extractor import ConceptualEntity, EnhancedConceptExtractor

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/brand-safety", tags=["brand-safety"])


# Request/Response Models
class BrandSafetyRequest(BaseModel):
    """Request model for brand safety assessment."""
    text: str = Field(..., description="Content text to assess for brand safety")
    platform: str = Field(default="general", description="Platform: general, linkedin, twitter")
    brand_profile: str = Field(default="moderate", description="Brand profile: conservative, moderate, aggressive")
    content_id: Optional[str] = Field(None, description="Optional content identifier")
    context: Dict[str, Any] = Field(default_factory=dict, description="Additional context")
    include_viral_analysis: bool = Field(default=True, description="Include viral prediction analysis")


class BrandSafetyResponse(BaseModel):
    """Response model for brand safety assessment."""
    content_id: str = Field(..., description="Content identifier")
    safety_level: str = Field(..., description="Overall safety level")
    content_classification: str = Field(..., description="Content classification")
    
    # Risk scores
    risk_score: Dict[str, float] = Field(..., description="Multi-dimensional risk scores")
    confidence: float = Field(..., description="Assessment confidence")
    
    # Analysis results
    stakeholder_analysis: Dict[str, Any] = Field(..., description="Stakeholder impact analysis")
    toxicity_assessment: Dict[str, float] = Field(..., description="Content toxicity scores")
    controversy_analysis: Dict[str, Any] = Field(..., description="Controversy analysis")
    crisis_risk: Dict[str, Any] = Field(..., description="Crisis escalation risk")
    
    # Brand alignment
    brand_alignment_score: float = Field(..., description="Brand value alignment")
    message_consistency_score: float = Field(..., description="Brand message consistency")
    
    # Recommendations
    risk_factors: List[str] = Field(..., description="Identified risk factors")
    red_flags: List[str] = Field(..., description="Content red flags")
    mitigation_strategy: Dict[str, Any] = Field(..., description="Risk mitigation strategy")
    content_modifications: List[str] = Field(..., description="Suggested content changes")
    approval_workflow: List[str] = Field(..., description="Required approval steps")
    
    # Viral integration
    viral_prediction: Optional[Dict[str, Any]] = Field(None, description="Viral prediction data")
    risk_adjusted_viral_score: float = Field(..., description="Risk-adjusted viral potential")
    
    # Monitoring
    monitoring_keywords: List[str] = Field(..., description="Keywords to monitor")
    alert_thresholds: Dict[str, float] = Field(..., description="Alert threshold settings")
    
    assessment_time_ms: float = Field(..., description="Assessment processing time")
    created_at: str = Field(..., description="Assessment timestamp")


class QuickSafetyCheckRequest(BaseModel):
    """Request model for quick safety check."""
    text: str = Field(..., description="Content text to check")
    brand_profile: str = Field(default="moderate", description="Brand profile")


class QuickSafetyCheckResponse(BaseModel):
    """Response model for quick safety check."""
    safety_level: str = Field(..., description="Safety level")
    is_safe: bool = Field(..., description="Whether content is safe to publish")
    requires_review: bool = Field(..., description="Whether manual review is needed")
    check_time_ms: float = Field(..., description="Check processing time")


class ViralSafetyRequest(BaseModel):
    """Request model for viral content safety assessment."""
    text: str = Field(..., description="Content text to assess")
    platform: str = Field(default="general", description="Platform for viral prediction")
    brand_profile: str = Field(default="moderate", description="Brand safety profile")
    context: Dict[str, Any] = Field(default_factory=dict, description="Additional context")


class ViralSafetyResponse(BaseModel):
    """Response model for viral content safety assessment."""
    content_id: str = Field(..., description="Content identifier")
    safety_assessment: Dict[str, Any] = Field(..., description="Brand safety assessment")
    viral_prediction: Dict[str, Any] = Field(..., description="Viral prediction results")
    combined_recommendation: str = Field(..., description="Combined recommendation")
    risk_vs_reward_analysis: Dict[str, Any] = Field(..., description="Risk vs reward analysis")
    publication_decision: str = Field(..., description="Recommended publication decision")


class BatchSafetyRequest(BaseModel):
    """Request model for batch safety assessment."""
    content_items: List[Dict[str, str]] = Field(..., description="List of content items with text and platform")
    brand_profile: str = Field(default="moderate", description="Brand safety profile")
    context: Dict[str, Any] = Field(default_factory=dict, description="Shared context")


class BatchSafetyResponse(BaseModel):
    """Response model for batch safety assessment."""
    assessments: List[Dict[str, Any]] = Field(..., description="Individual assessments")
    summary: Dict[str, Any] = Field(..., description="Batch processing summary")
    processing_time_ms: float = Field(..., description="Total processing time")


@router.post("/assess", response_model=BrandSafetyResponse)
async def assess_brand_safety(
    request: BrandSafetyRequest,
    concept_extractor: EnhancedConceptExtractor = Depends(get_concept_extractor)
) -> BrandSafetyResponse:
    """Comprehensive brand safety assessment for content."""
    try:
        start_time = asyncio.get_event_loop().time()
        
        logger.info(f"Epic 7.2: Assessing brand safety for {request.platform} content")
        
        # Parse enums
        platform = Platform(request.platform.lower()) if request.platform.lower() in [p.value for p in Platform] else Platform.GENERAL
        brand_profile = BrandProfile(request.brand_profile.lower()) if request.brand_profile.lower() in [p.value for p in BrandProfile] else BrandProfile.MODERATE
        
        # Extract concepts for enhanced analysis
        concepts = await concept_extractor.extract_concepts(
            request.text, 
            {**request.context, "platform": request.platform}
        )
        
        # Perform brand safety assessment
        analyzer = BrandSafetyAnalyzer(brand_profile)
        assessment = await analyzer.assess_brand_safety(
            text=request.text,
            platform=platform,
            content_id=request.content_id,
            concepts=concepts,
            context=request.context
        )
        
        end_time = asyncio.get_event_loop().time()
        assessment_time_ms = (end_time - start_time) * 1000
        
        # Convert to response format
        def stakeholder_to_dict(analysis):
            return {
                "customers": analysis.customers.value,
                "employees": analysis.employees.value,
                "investors": analysis.investors.value,
                "partners": analysis.partners.value,
                "general_public": analysis.general_public.value,
                "sentiment_confidence": analysis.sentiment_confidence
            }
        
        def toxicity_to_dict(toxicity):
            return {
                "toxicity_score": toxicity.toxicity_score,
                "hate_speech_score": toxicity.hate_speech_score,
                "harassment_score": toxicity.harassment_score,
                "profanity_score": toxicity.profanity_score,
                "threat_score": toxicity.threat_score,
                "identity_attack_score": toxicity.identity_attack_score,
                "severe_toxicity_score": toxicity.severe_toxicity_score
            }
        
        def controversy_to_dict(controversy):
            return {
                "controversy_score": controversy.controversy_score,
                "controversy_type": controversy.controversy_type,
                "polarization_risk": controversy.polarization_risk,
                "backlash_potential": controversy.backlash_potential,
                "divisive_topics": controversy.divisive_topics,
                "sensitivity_areas": controversy.sensitivity_areas
            }
        
        def crisis_to_dict(crisis):
            return {
                "escalation_probability": crisis.escalation_probability,
                "viral_amplification_risk": crisis.viral_amplification_risk,
                "media_attention_risk": crisis.media_attention_risk,
                "response_urgency": crisis.response_urgency,
                "crisis_triggers": crisis.crisis_triggers,
                "mitigation_window_hours": crisis.mitigation_window.total_seconds() / 3600
            }
        
        def mitigation_to_dict(mitigation):
            return {
                "priority": mitigation.priority,
                "actions": mitigation.actions,
                "approval_required": mitigation.approval_required,
                "monitoring_required": mitigation.monitoring_required,
                "alternative_approaches": mitigation.alternative_approaches,
                "decision_deadline": mitigation.decision_deadline.isoformat() if mitigation.decision_deadline else None
            }
        
        def viral_to_dict(viral):
            if not viral:
                return None
            return {
                "content_id": viral.content_id,
                "platform": viral.platform.value,
                "content_type": viral.content_type.value,
                "engagement_score": viral.engagement_score,
                "reach_potential": viral.reach_potential,
                "viral_velocity": viral.viral_velocity,
                "controversy_score": viral.controversy_score,
                "overall_viral_score": viral.overall_viral_score,
                "risk_level": viral.risk_level.value,
                "confidence": viral.confidence,
                "key_features": viral.key_features,
                "improvement_suggestions": viral.improvement_suggestions
            }
        
        response = BrandSafetyResponse(
            content_id=assessment.content_id,
            safety_level=assessment.safety_level.value,
            content_classification=assessment.content_classification.value,
            risk_score={
                "reputational": assessment.risk_score.reputational,
                "legal": assessment.risk_score.legal,
                "financial": assessment.risk_score.financial,
                "operational": assessment.risk_score.operational,
                "overall": assessment.risk_score.overall
            },
            confidence=assessment.confidence,
            stakeholder_analysis=stakeholder_to_dict(assessment.stakeholder_analysis),
            toxicity_assessment=toxicity_to_dict(assessment.toxicity_assessment),
            controversy_analysis=controversy_to_dict(assessment.controversy_analysis),
            crisis_risk=crisis_to_dict(assessment.crisis_risk),
            brand_alignment_score=assessment.brand_alignment_score,
            message_consistency_score=assessment.message_consistency_score,
            risk_factors=assessment.risk_factors,
            red_flags=assessment.red_flags,
            mitigation_strategy=mitigation_to_dict(assessment.mitigation_strategy),
            content_modifications=assessment.content_modifications,
            approval_workflow=assessment.approval_workflow,
            viral_prediction=viral_to_dict(assessment.viral_prediction),
            risk_adjusted_viral_score=assessment.risk_adjusted_viral_score,
            monitoring_keywords=assessment.monitoring_keywords,
            alert_thresholds=assessment.alert_thresholds,
            assessment_time_ms=assessment_time_ms,
            created_at=assessment.created_at.isoformat()
        )
        
        logger.info(f"Epic 7.2: Brand safety assessment completed - Safety Level: {assessment.safety_level.value}, "
                   f"Risk Score: {assessment.risk_score.overall:.3f}, Time: {assessment_time_ms:.1f}ms")
        
        return response
        
    except Exception as e:
        logger.error(f"Epic 7.2: Error in brand safety assessment: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Brand safety assessment failed: {str(e)}")


@router.post("/quick-check", response_model=QuickSafetyCheckResponse)
async def quick_brand_safety_check(
    request: QuickSafetyCheckRequest
) -> QuickSafetyCheckResponse:
    """Quick brand safety check for immediate decisions."""
    try:
        start_time = asyncio.get_event_loop().time()
        
        logger.info(f"Epic 7.2: Quick safety check requested")
        
        # Parse brand profile
        brand_profile = BrandProfile(request.brand_profile.lower()) if request.brand_profile.lower() in [p.value for p in BrandProfile] else BrandProfile.MODERATE
        
        # Quick safety assessment
        analyzer = BrandSafetyAnalyzer(brand_profile)
        assessment = await analyzer.assess_brand_safety(request.text)
        
        end_time = asyncio.get_event_loop().time()
        check_time_ms = (end_time - start_time) * 1000
        
        # Determine safety decisions
        is_safe = assessment.safety_level in [BrandSafetyLevel.SAFE, BrandSafetyLevel.CAUTION]
        requires_review = assessment.safety_level in [BrandSafetyLevel.CAUTION, BrandSafetyLevel.RISK, BrandSafetyLevel.DANGER]
        
        response = QuickSafetyCheckResponse(
            safety_level=assessment.safety_level.value,
            is_safe=is_safe,
            requires_review=requires_review,
            check_time_ms=check_time_ms
        )
        
        logger.info(f"Epic 7.2: Quick check completed - Safe: {is_safe}, Review Required: {requires_review}")
        
        return response
        
    except Exception as e:
        logger.error(f"Epic 7.2: Error in quick safety check: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Quick safety check failed: {str(e)}")


@router.post("/viral-safety", response_model=ViralSafetyResponse)
async def assess_viral_content_safety(
    request: ViralSafetyRequest,
    concept_extractor: EnhancedConceptExtractor = Depends(get_concept_extractor)
) -> ViralSafetyResponse:
    """Combined viral prediction and brand safety assessment."""
    try:
        start_time = asyncio.get_event_loop().time()
        
        logger.info(f"Epic 7.2: Viral safety assessment for {request.platform} content")
        
        # Parse enums
        platform = Platform(request.platform.lower()) if request.platform.lower() in [p.value for p in Platform] else Platform.GENERAL
        brand_profile = BrandProfile(request.brand_profile.lower()) if request.brand_profile.lower() in [p.value for p in BrandProfile] else BrandProfile.MODERATE
        
        # Extract concepts
        concepts = await concept_extractor.extract_concepts(
            request.text, 
            {**request.context, "platform": request.platform}
        )
        
        # Run both viral prediction and brand safety in parallel
        viral_engine = ViralPredictionEngine()
        safety_analyzer = BrandSafetyAnalyzer(brand_profile)
        
        viral_task = viral_engine.predict_viral_potential(request.text, platform, context=request.context)
        safety_task = safety_analyzer.assess_brand_safety(
            request.text, platform, concepts=concepts, context=request.context
        )
        
        viral_prediction, safety_assessment = await asyncio.gather(viral_task, safety_task)
        
        # Analyze risk vs reward
        risk_vs_reward = {
            "viral_potential": viral_prediction.overall_viral_score,
            "brand_risk": safety_assessment.risk_score.overall,
            "risk_adjusted_viral": safety_assessment.risk_adjusted_viral_score,
            "risk_tolerance": brand_profile.value,
            "reward_potential": "high" if viral_prediction.overall_viral_score > 0.7 else "medium" if viral_prediction.overall_viral_score > 0.4 else "low",
            "risk_level": safety_assessment.safety_level.value,
            "net_value": safety_assessment.risk_adjusted_viral_score - safety_assessment.risk_score.overall
        }
        
        # Make publication recommendation
        if safety_assessment.safety_level == BrandSafetyLevel.DANGER:
            publication_decision = "reject"
            combined_recommendation = "Content poses significant brand safety risks and should not be published"
        elif safety_assessment.safety_level == BrandSafetyLevel.RISK:
            if viral_prediction.overall_viral_score > 0.8:
                publication_decision = "modify_and_approve"
                combined_recommendation = "High viral potential but significant risks - modify content and get approval"
            else:
                publication_decision = "reject"
                combined_recommendation = "Risks outweigh limited viral potential - recommend rejection"
        elif safety_assessment.safety_level == BrandSafetyLevel.CAUTION:
            publication_decision = "approve_with_monitoring"
            combined_recommendation = "Safe to publish with active monitoring for negative feedback"
        else:  # SAFE
            publication_decision = "approve"
            combined_recommendation = "Content is brand-safe and ready for publication"
        
        end_time = asyncio.get_event_loop().time()
        processing_time_ms = (end_time - start_time) * 1000
        
        # Generate content ID
        content_id = f"viral_safety_{hash(request.text[:100])}_{int(datetime.utcnow().timestamp())}"
        
        response = ViralSafetyResponse(
            content_id=content_id,
            safety_assessment={
                "safety_level": safety_assessment.safety_level.value,
                "risk_score": safety_assessment.risk_score.overall,
                "confidence": safety_assessment.confidence,
                "risk_factors": safety_assessment.risk_factors[:5],
                "mitigation_priority": safety_assessment.mitigation_strategy.priority
            },
            viral_prediction={
                "overall_score": viral_prediction.overall_viral_score,
                "engagement_score": viral_prediction.engagement_score,
                "reach_potential": viral_prediction.reach_potential,
                "controversy_score": viral_prediction.controversy_score,
                "key_features": viral_prediction.key_features[:3],
                "platform_optimization": viral_prediction.platform_optimization_score
            },
            combined_recommendation=combined_recommendation,
            risk_vs_reward_analysis=risk_vs_reward,
            publication_decision=publication_decision
        )
        
        logger.info(f"Epic 7.2: Viral safety assessment completed - Decision: {publication_decision}, "
                   f"Viral Score: {viral_prediction.overall_viral_score:.3f}, Risk: {safety_assessment.risk_score.overall:.3f}")
        
        return response
        
    except Exception as e:
        logger.error(f"Epic 7.2: Error in viral safety assessment: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Viral safety assessment failed: {str(e)}")


@router.post("/batch-assess", response_model=BatchSafetyResponse)
async def batch_brand_safety_assessment(
    request: BatchSafetyRequest,
    concept_extractor: EnhancedConceptExtractor = Depends(get_concept_extractor)
) -> BatchSafetyResponse:
    """Batch brand safety assessment for multiple content items."""
    try:
        start_time = asyncio.get_event_loop().time()
        
        logger.info(f"Epic 7.2: Batch safety assessment for {len(request.content_items)} items")
        
        brand_profile = BrandProfile(request.brand_profile.lower()) if request.brand_profile.lower() in [p.value for p in BrandProfile] else BrandProfile.MODERATE
        analyzer = BrandSafetyAnalyzer(brand_profile)
        
        # Process all items in parallel
        assessment_tasks = []
        for i, item in enumerate(request.content_items):
            text = item.get("text", "")
            platform_str = item.get("platform", "general")
            platform = Platform(platform_str.lower()) if platform_str.lower() in [p.value for p in Platform] else Platform.GENERAL
            
            # Extract concepts for each item
            concepts_task = concept_extractor.extract_concepts(text, {**request.context, "platform": platform_str})
            assessment_tasks.append((i, text, platform, concepts_task))
        
        # Wait for all concept extractions
        assessments = []
        for i, text, platform, concepts_task in assessment_tasks:
            concepts = await concepts_task
            assessment = await analyzer.assess_brand_safety(text, platform, concepts=concepts, context=request.context)
            
            assessments.append({
                "index": i,
                "content_id": assessment.content_id,
                "safety_level": assessment.safety_level.value,
                "risk_score": assessment.risk_score.overall,
                "confidence": assessment.confidence,
                "requires_review": assessment.safety_level in [BrandSafetyLevel.CAUTION, BrandSafetyLevel.RISK, BrandSafetyLevel.DANGER],
                "approval_required": assessment.mitigation_strategy.approval_required,
                "top_risk_factors": assessment.risk_factors[:3],
                "text_preview": text[:100] + "..." if len(text) > 100 else text
            })
        
        end_time = asyncio.get_event_loop().time()
        processing_time_ms = (end_time - start_time) * 1000
        
        # Generate summary statistics
        safety_levels = [a["safety_level"] for a in assessments]
        risk_scores = [a["risk_score"] for a in assessments]
        
        summary = {
            "total_items": len(assessments),
            "safety_distribution": {
                "safe": safety_levels.count("safe"),
                "caution": safety_levels.count("caution"),
                "risk": safety_levels.count("risk"),
                "danger": safety_levels.count("danger")
            },
            "average_risk_score": sum(risk_scores) / len(risk_scores) if risk_scores else 0.0,
            "items_requiring_review": sum(1 for a in assessments if a["requires_review"]),
            "items_requiring_approval": sum(1 for a in assessments if a["approval_required"]),
            "processing_time_ms": processing_time_ms,
            "brand_profile": brand_profile.value
        }
        
        response = BatchSafetyResponse(
            assessments=assessments,
            summary=summary,
            processing_time_ms=processing_time_ms
        )
        
        logger.info(f"Epic 7.2: Batch assessment completed - {summary['items_requiring_review']}/{summary['total_items']} "
                   f"items need review, avg risk: {summary['average_risk_score']:.3f}")
        
        return response
        
    except Exception as e:
        logger.error(f"Epic 7.2: Error in batch safety assessment: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Batch safety assessment failed: {str(e)}")


@router.get("/mitigation/{content_id}")
async def get_mitigation_strategy(
    content_id: str,
    platform: str = Query("general", description="Platform type"),
    brand_profile: str = Query("moderate", description="Brand profile")
) -> Dict[str, Any]:
    """Get specific mitigation strategy for content."""
    try:
        logger.info(f"Epic 7.2: Retrieving mitigation strategy for content: {content_id}")
        
        # TODO: In a real implementation, would retrieve content from database
        # For now, return a general mitigation strategy framework
        
        brand_profile_enum = BrandProfile(brand_profile.lower()) if brand_profile.lower() in [p.value for p in BrandProfile] else BrandProfile.MODERATE
        
        # Generate context-appropriate mitigation strategy
        if brand_profile_enum == BrandProfile.CONSERVATIVE:
            mitigation = {
                "content_id": content_id,
                "strategy_type": "conservative",
                "immediate_actions": [
                    "Suspend publication pending review",
                    "Legal team consultation required",
                    "Senior management approval needed"
                ],
                "review_process": [
                    "Content audit by compliance team",
                    "Brand guideline alignment check",
                    "Stakeholder impact assessment"
                ],
                "approval_levels": ["supervisor", "department_head", "legal", "executive"],
                "monitoring_plan": {
                    "duration_days": 30,
                    "keywords": ["controversy", "backlash", "criticism"],
                    "alert_threshold": 0.3
                },
                "contingency_plan": [
                    "Prepared response statements",
                    "Crisis communication protocol",
                    "Stakeholder notification process"
                ]
            }
        elif brand_profile_enum == BrandProfile.AGGRESSIVE:
            mitigation = {
                "content_id": content_id,
                "strategy_type": "aggressive",
                "immediate_actions": [
                    "Review content for optimization",
                    "Prepare engagement strategy",
                    "Monitor initial response closely"
                ],
                "review_process": [
                    "Editorial review for impact",
                    "Engagement optimization check"
                ],
                "approval_levels": ["editor", "marketing_lead"],
                "monitoring_plan": {
                    "duration_days": 7,
                    "keywords": ["viral", "trending", "discussion"],
                    "alert_threshold": 0.7
                },
                "contingency_plan": [
                    "Rapid response capability",
                    "Amplification strategy ready"
                ]
            }
        else:  # MODERATE
            mitigation = {
                "content_id": content_id,
                "strategy_type": "moderate",
                "immediate_actions": [
                    "Standard editorial review",
                    "Brand alignment check",
                    "Prepare monitoring setup"
                ],
                "review_process": [
                    "Content quality assessment",
                    "Brand voice consistency check",
                    "Risk-benefit analysis"
                ],
                "approval_levels": ["editor", "marketing_manager"],
                "monitoring_plan": {
                    "duration_days": 14,
                    "keywords": ["feedback", "response", "mention"],
                    "alert_threshold": 0.5
                },
                "contingency_plan": [
                    "Response framework ready",
                    "Escalation procedure defined"
                ]
            }
        
        logger.info(f"Epic 7.2: Mitigation strategy generated for {brand_profile_enum.value} profile")
        return mitigation
        
    except Exception as e:
        logger.error(f"Epic 7.2: Error retrieving mitigation strategy: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Mitigation strategy retrieval failed: {str(e)}")


@router.get("/analytics/risk-trends")
async def get_risk_trend_analytics(
    days: int = Query(30, description="Number of days for trend analysis"),
    brand_profile: str = Query("moderate", description="Brand profile filter")
) -> Dict[str, Any]:
    """Get risk trend analytics over time."""
    try:
        logger.info(f"Epic 7.2: Generating risk trend analytics for {days} days")
        
        # TODO: In a real implementation, would query actual assessment data from database
        # For now, generate mock trend data for demonstration
        
        import random
        from datetime import datetime, timedelta
        
        # Generate mock trend data
        trends = []
        base_date = datetime.utcnow() - timedelta(days=days)
        
        for i in range(days):
            current_date = base_date + timedelta(days=i)
            daily_data = {
                "date": current_date.strftime("%Y-%m-%d"),
                "total_assessments": random.randint(50, 200),
                "risk_distribution": {
                    "safe": random.randint(30, 80),
                    "caution": random.randint(10, 40),
                    "risk": random.randint(5, 20),
                    "danger": random.randint(0, 5)
                },
                "average_risk_score": random.uniform(0.2, 0.6),
                "top_risk_factors": [
                    "controversial content",
                    "negative sentiment",
                    "polarizing topics"
                ]
            }
            trends.append(daily_data)
        
        # Calculate summary statistics
        total_assessments = sum(day["total_assessments"] for day in trends)
        avg_risk_score = sum(day["average_risk_score"] for day in trends) / len(trends)
        
        risk_totals = {
            "safe": sum(day["risk_distribution"]["safe"] for day in trends),
            "caution": sum(day["risk_distribution"]["caution"] for day in trends),
            "risk": sum(day["risk_distribution"]["risk"] for day in trends),
            "danger": sum(day["risk_distribution"]["danger"] for day in trends)
        }
        
        analytics = {
            "period": {
                "start_date": trends[0]["date"],
                "end_date": trends[-1]["date"],
                "days": days
            },
            "summary": {
                "total_assessments": total_assessments,
                "average_risk_score": round(avg_risk_score, 3),
                "risk_distribution_percentage": {
                    "safe": round(risk_totals["safe"] / total_assessments * 100, 1),
                    "caution": round(risk_totals["caution"] / total_assessments * 100, 1),
                    "risk": round(risk_totals["risk"] / total_assessments * 100, 1),
                    "danger": round(risk_totals["danger"] / total_assessments * 100, 1)
                }
            },
            "daily_trends": trends,
            "insights": [
                f"Average risk score: {avg_risk_score:.3f}",
                f"{risk_totals['danger']} high-risk items detected",
                f"{round(risk_totals['safe'] / total_assessments * 100, 1)}% of content was brand-safe"
            ],
            "brand_profile": brand_profile
        }
        
        logger.info(f"Epic 7.2: Risk trend analytics generated - {total_assessments} total assessments, "
                   f"avg risk: {avg_risk_score:.3f}")
        
        return analytics
        
    except Exception as e:
        logger.error(f"Epic 7.2: Error generating risk trend analytics: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Risk trend analytics failed: {str(e)}")


@router.get("/config/thresholds")
async def get_brand_safety_configuration(
    brand_profile: str = Query("moderate", description="Brand profile")
) -> Dict[str, Any]:
    """Get brand safety configuration and thresholds."""
    try:
        logger.info(f"Epic 7.2: Retrieving brand safety configuration for {brand_profile} profile")
        
        brand_profile_enum = BrandProfile(brand_profile.lower()) if brand_profile.lower() in [p.value for p in BrandProfile] else BrandProfile.MODERATE
        
        # Create analyzer to get thresholds
        analyzer = BrandSafetyAnalyzer(brand_profile_enum)
        thresholds = analyzer.safety_thresholds[brand_profile_enum]
        
        configuration = {
            "brand_profile": brand_profile_enum.value,
            "safety_thresholds": {
                "safe": thresholds[BrandSafetyLevel.SAFE],
                "caution": thresholds[BrandSafetyLevel.CAUTION],
                "risk": thresholds[BrandSafetyLevel.RISK],
                "danger": thresholds[BrandSafetyLevel.DANGER]
            },
            "risk_weights": {
                "reputational": analyzer.risk_weights[RiskDimension.REPUTATIONAL],
                "legal": analyzer.risk_weights[RiskDimension.LEGAL],
                "financial": analyzer.risk_weights[RiskDimension.FINANCIAL],
                "operational": analyzer.risk_weights[RiskDimension.OPERATIONAL]
            },
            "content_classifications": [c.value for c in ContentClassification],
            "stakeholder_groups": [s.value for s in StakeholderImpact],
            "monitoring_defaults": {
                "keywords_limit": 10,
                "alert_sensitivity": "medium",
                "monitoring_duration_days": 14
            },
            "approval_workflows": {
                "safe": ["editor"],
                "caution": ["editor", "supervisor"],
                "risk": ["supervisor", "manager", "legal"],
                "danger": ["manager", "legal", "executive"]
            }
        }
        
        logger.info(f"Epic 7.2: Configuration retrieved for {brand_profile_enum.value} profile")
        return configuration
        
    except Exception as e:
        logger.error(f"Epic 7.2: Error retrieving brand safety configuration: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Configuration retrieval failed: {str(e)}")