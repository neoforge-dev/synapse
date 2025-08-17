"""API router for concept mapping and idea relationship analysis."""

import asyncio
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from graph_rag.api.dependencies import (
    get_concept_extractor, get_temporal_tracker, get_cross_platform_correlator, 
    get_belief_preference_extractor, get_viral_prediction_engine, get_brand_safety_analyzer,
    get_content_strategy_optimizer, get_content_optimization_engine, get_audience_segmentation_engine
)
from graph_rag.core.concept_extractor import ConceptualEntity, IdeaRelationship, EnhancedConceptExtractor
from graph_rag.core.temporal_tracker import TemporalTracker
from graph_rag.services.cross_platform_correlator import CrossPlatformCorrelator, ContentCorrelation

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/concepts", tags=["concepts"])


# Request/Response Models
class ConceptExtractionRequest(BaseModel):
    """Request model for concept extraction."""
    text: str = Field(..., description="Text to extract concepts from")
    platform: str = Field(default="general", description="Platform type: general, linkedin, notion")
    context: Dict[str, Any] = Field(default_factory=dict, description="Additional context")


class ConceptExtractionResponse(BaseModel):
    """Response model for concept extraction."""
    concepts: List[Dict[str, Any]] = Field(..., description="Extracted concepts")
    relationships: List[Dict[str, Any]] = Field(..., description="Concept relationships")
    extraction_time_ms: float = Field(..., description="Time taken for extraction")


class ConceptQueryRequest(BaseModel):
    """Request model for concept queries."""
    concept_types: Optional[List[str]] = Field(None, description="Filter by concept types")
    platforms: Optional[List[str]] = Field(None, description="Filter by platforms")
    confidence_min: float = Field(default=0.0, description="Minimum confidence threshold")
    limit: int = Field(default=50, description="Maximum number of results")


class ConceptQueryResponse(BaseModel):
    """Response model for concept queries."""
    concepts: List[Dict[str, Any]] = Field(..., description="Matching concepts")
    total_count: int = Field(..., description="Total number of matching concepts")


class CorrelationRequest(BaseModel):
    """Request model for cross-platform correlation."""
    linkedin_content: List[Dict[str, Any]] = Field(default_factory=list, description="LinkedIn content")
    notion_content: List[Dict[str, Any]] = Field(default_factory=list, description="Notion content")
    max_days: int = Field(default=30, description="Maximum days between correlated content")


class CorrelationResponse(BaseModel):
    """Response model for correlations."""
    correlations: List[Dict[str, Any]] = Field(..., description="Found correlations")
    analysis_summary: Dict[str, Any] = Field(..., description="Analysis summary")


@router.post("/extract", response_model=ConceptExtractionResponse)
async def extract_concepts(
    request: ConceptExtractionRequest,
    extractor: EnhancedConceptExtractor = Depends(get_concept_extractor)
) -> ConceptExtractionResponse:
    """Extract concepts and relationships from text."""
    try:
        start_time = asyncio.get_event_loop().time()
        
        # Choose appropriate extractor based on platform
        if request.platform.lower() == "linkedin":
            from graph_rag.core.concept_extractor import LinkedInConceptExtractor
            platform_extractor = LinkedInConceptExtractor()
        elif request.platform.lower() == "notion":
            from graph_rag.core.concept_extractor import NotionConceptExtractor
            platform_extractor = NotionConceptExtractor()
        else:
            platform_extractor = extractor
        
        # Extract concepts
        concepts = await platform_extractor.extract_concepts(
            request.text, 
            {**request.context, "platform": request.platform}
        )
        
        # Extract relationships if multiple concepts found
        relationships = []
        if len(concepts) > 1:
            relationships = await platform_extractor.extract_idea_relationships(
                concepts, request.text
            )
        
        end_time = asyncio.get_event_loop().time()
        extraction_time_ms = (end_time - start_time) * 1000
        
        # Convert to response format
        concepts_data = []
        for concept in concepts:
            concept_dict = {
                "id": concept.id,
                "name": concept.name,
                "text": concept.text,
                "concept_type": concept.concept_type,
                "confidence": concept.confidence,
                "context_window": concept.context_window,
                "properties": concept.properties
            }
            concepts_data.append(concept_dict)
        
        relationships_data = []
        for rel in relationships:
            rel_dict = {
                "source_concept": rel.source_concept,
                "target_concept": rel.target_concept,
                "relationship_type": rel.relationship_type,
                "confidence": rel.confidence,
                "evidence_text": rel.evidence_text
            }
            relationships_data.append(rel_dict)
        
        return ConceptExtractionResponse(
            concepts=concepts_data,
            relationships=relationships_data,
            extraction_time_ms=extraction_time_ms
        )
        
    except Exception as e:
        logger.error(f"Error extracting concepts: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Concept extraction failed: {str(e)}")


@router.get("/search", response_model=ConceptQueryResponse)
async def search_concepts(
    concept_types: Optional[List[str]] = Query(None, description="Filter by concept types"),
    platforms: Optional[List[str]] = Query(None, description="Filter by platforms"),
    confidence_min: float = Query(0.0, description="Minimum confidence threshold"),
    limit: int = Query(50, description="Maximum number of results"),
    extractor: EnhancedConceptExtractor = Depends(get_concept_extractor)
) -> ConceptQueryResponse:
    """Search for concepts in the knowledge graph."""
    try:
        # For now, return a placeholder response since we need to implement 
        # concept storage and retrieval from the graph database
        logger.info(f"Searching concepts with filters: types={concept_types}, platforms={platforms}")
        
        # TODO: Implement actual concept search from graph database
        # This would involve querying Memgraph for ConceptualEntity nodes
        # with the specified filters
        
        return ConceptQueryResponse(
            concepts=[],
            total_count=0
        )
        
    except Exception as e:
        logger.error(f"Error searching concepts: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Concept search failed: {str(e)}")


@router.post("/correlate", response_model=CorrelationResponse)
async def find_correlations(
    request: CorrelationRequest,
    correlator: CrossPlatformCorrelator = Depends(get_cross_platform_correlator)
) -> CorrelationResponse:
    """Find correlations between LinkedIn and Notion content."""
    try:
        # Ingest content into correlator
        if request.linkedin_content:
            await correlator.ingest_linkedin_content(request.linkedin_content)
        
        if request.notion_content:
            await correlator.ingest_notion_content(request.notion_content)
        
        # Find correlations
        correlations = await correlator.find_correlations(request.max_days)
        
        # Convert correlations to response format
        correlations_data = []
        for corr in correlations:
            corr_dict = {
                "source_content": {
                    "content_id": corr.source_content.content_id,
                    "platform": corr.source_content.platform.value,
                    "text_preview": corr.source_content.text[:100] + "..." if len(corr.source_content.text) > 100 else corr.source_content.text,
                    "timestamp": corr.source_content.timestamp.isoformat()
                },
                "target_content": {
                    "content_id": corr.target_content.content_id,
                    "platform": corr.target_content.platform.value,
                    "text_preview": corr.target_content.text[:100] + "..." if len(corr.target_content.text) > 100 else corr.target_content.text,
                    "timestamp": corr.target_content.timestamp.isoformat()
                },
                "correlation_type": corr.correlation_type.value,
                "confidence": corr.confidence,
                "shared_concepts": corr.shared_concepts,
                "temporal_distance_days": corr.temporal_distance.days
            }
            correlations_data.append(corr_dict)
        
        # Generate analysis summary
        analytics = await correlator.get_platform_analytics()
        analysis_summary = {
            "total_correlations": len(correlations),
            "content_counts": analytics.get("content_counts", {}),
            "correlation_types": analytics.get("correlation_types", {}),
            "processing_summary": {
                "linkedin_items": len(request.linkedin_content),
                "notion_items": len(request.notion_content),
                "max_days_filter": request.max_days
            }
        }
        
        return CorrelationResponse(
            correlations=correlations_data,
            analysis_summary=analysis_summary
        )
        
    except Exception as e:
        logger.error(f"Error finding correlations: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Correlation analysis failed: {str(e)}")


@router.get("/evolution/{evolution_id}")
async def get_concept_evolution(
    evolution_id: str,
    tracker: TemporalTracker = Depends(get_temporal_tracker)
) -> Dict[str, Any]:
    """Get the evolution timeline for a specific concept."""
    try:
        evolution = tracker.idea_evolutions.get(evolution_id)
        if not evolution:
            raise HTTPException(status_code=404, detail=f"Evolution {evolution_id} not found")
        
        # Convert evolution to response format
        chronological_versions = evolution.get_chronological_versions()
        
        evolution_data = {
            "evolution_id": evolution_id,
            "core_idea": evolution.core_idea_id,
            "timeline": [],
            "platforms": list(set(v.platform.value for v in chronological_versions)),
            "stages": list(set(v.stage.value for v in chronological_versions))
        }
        
        for i, version in enumerate(chronological_versions):
            evolution_data["timeline"].append({
                "index": i,
                "timestamp": version.timestamp.isoformat(),
                "platform": version.platform.value,
                "stage": version.stage.value,
                "concept_name": version.concept.name,
                "concept_id": version.concept.id,
                "content_snippet": version.content_snippet[:200] if version.content_snippet else "",
                "engagement_metrics": version.engagement_metrics
            })
        
        return evolution_data
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting concept evolution: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get concept evolution: {str(e)}")


@router.get("/analytics/gaps")
async def analyze_content_gaps(
    days_threshold: int = Query(30, description="Days threshold for gap analysis"),
    correlator: CrossPlatformCorrelator = Depends(get_cross_platform_correlator)
) -> Dict[str, Any]:
    """Analyze content gaps and missed opportunities."""
    try:
        gaps = await correlator.analyze_content_gaps()
        
        # Filter gaps by threshold if needed
        filtered_gaps = [
            gap for gap in gaps 
            if gap.get("age_days", 0) >= days_threshold
        ]
        
        return {
            "gaps": filtered_gaps[:20],  # Limit to top 20
            "total_gaps": len(filtered_gaps),
            "days_threshold": days_threshold,
            "analysis_timestamp": asyncio.get_event_loop().time()
        }
        
    except Exception as e:
        logger.error(f"Error analyzing content gaps: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Content gap analysis failed: {str(e)}")


@router.get("/analytics/platform-transitions")
async def get_platform_transitions(
    tracker: TemporalTracker = Depends(get_temporal_tracker)
) -> Dict[str, Any]:
    """Get platform transition patterns and analytics."""
    try:
        transitions = await tracker.get_platform_transition_patterns()
        
        # Calculate transition statistics
        total_transitions = sum(
            sum(targets.values()) for targets in transitions.values()
        )
        
        most_common_transitions = []
        for source, targets in transitions.items():
            for target, count in targets.items():
                most_common_transitions.append({
                    "source": source,
                    "target": target,
                    "count": count,
                    "percentage": (count / total_transitions * 100) if total_transitions > 0 else 0
                })
        
        # Sort by count descending
        most_common_transitions.sort(key=lambda x: x["count"], reverse=True)
        
        return {
            "transitions": transitions,
            "statistics": {
                "total_transitions": total_transitions,
                "unique_paths": len(most_common_transitions),
                "most_common": most_common_transitions[:10]  # Top 10
            },
            "platforms": list(set(transitions.keys()) | set(
                target for targets in transitions.values() for target in targets.keys()
            ))
        }
        
    except Exception as e:
        logger.error(f"Error getting platform transitions: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Platform transition analysis failed: {str(e)}")


# === EPIC 6: BELIEF & PREFERENCE INTELLIGENCE ENDPOINTS ===

class BeliefExtractionRequest(BaseModel):
    """Request model for belief and preference extraction."""
    text: str = Field(..., description="Text to extract beliefs and preferences from")
    platform: str = Field(default="general", description="Platform type: general, linkedin, notion")
    context: Dict[str, Any] = Field(default_factory=dict, description="Additional context")


class BeliefExtractionResponse(BaseModel):
    """Response model for belief and preference extraction."""
    beliefs: List[Dict[str, Any]] = Field(..., description="Extracted beliefs")
    preferences: List[Dict[str, Any]] = Field(..., description="Extracted preferences") 
    hot_takes: List[Dict[str, Any]] = Field(..., description="Extracted hot takes")
    all_concepts: List[Dict[str, Any]] = Field(..., description="All extracted concepts")
    extraction_summary: Dict[str, Any] = Field(..., description="Extraction summary")


@router.post("/beliefs/extract", response_model=BeliefExtractionResponse)
async def extract_beliefs_and_preferences(
    request: BeliefExtractionRequest,
    extractor = Depends(get_belief_preference_extractor)
) -> BeliefExtractionResponse:
    """Extract beliefs, preferences, and hot takes from text (Epic 6)."""
    try:
        logger.info(f"Epic 6: Extracting beliefs and preferences from {request.platform} content")
        
        # Extract beliefs and preferences using specialized extractor
        result = await extractor.extract_beliefs_and_preferences(
            request.text,
            {**request.context, "platform": request.platform}
        )
        
        # Convert results to response format
        def concept_to_dict(concept):
            return {
                "id": concept.id,
                "name": concept.name,
                "text": concept.text,
                "concept_type": concept.concept_type,
                "confidence": concept.confidence,
                "context_window": concept.context_window,
                "sentiment": concept.sentiment,
                "properties": concept.properties
            }
        
        beliefs_data = [concept_to_dict(c) for c in result["beliefs"]]
        preferences_data = [concept_to_dict(c) for c in result["preferences"]]
        hot_takes_data = [concept_to_dict(c) for c in result["hot_takes"]]
        all_concepts_data = [concept_to_dict(c) for c in result["all_concepts"]]
        
        # Generate extraction summary
        extraction_summary = {
            "total_concepts": len(all_concepts_data),
            "beliefs_count": len(beliefs_data),
            "preferences_count": len(preferences_data),
            "hot_takes_count": len(hot_takes_data),
            "platform": request.platform,
            "high_confidence_concepts": len([c for c in result["all_concepts"] if c.confidence > 0.8]),
            "engagement_potential_high": len([c for c in result["all_concepts"] 
                                           if c.properties.get("engagement_potential", 0) > 0.7])
        }
        
        logger.info(f"Epic 6: Extracted {extraction_summary['total_concepts']} concepts including "
                   f"{extraction_summary['beliefs_count']} beliefs, "
                   f"{extraction_summary['preferences_count']} preferences, "
                   f"{extraction_summary['hot_takes_count']} hot takes")
        
        return BeliefExtractionResponse(
            beliefs=beliefs_data,
            preferences=preferences_data,
            hot_takes=hot_takes_data,
            all_concepts=all_concepts_data,
            extraction_summary=extraction_summary
        )
        
    except Exception as e:
        logger.error(f"Epic 6: Error extracting beliefs and preferences: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Belief extraction failed: {str(e)}")


@router.get("/beliefs/consistency")
async def analyze_belief_consistency(
    belief_ids: List[str] = Query(..., description="List of belief IDs to analyze for consistency"),
    extractor = Depends(get_belief_preference_extractor)
) -> Dict[str, Any]:
    """Analyze consistency between beliefs for authenticity checking (Epic 6)."""
    try:
        logger.info(f"Epic 6: Analyzing consistency for {len(belief_ids)} beliefs")
        
        # TODO: Implement belief consistency analysis
        # This would involve:
        # 1. Retrieving beliefs from graph database
        # 2. Analyzing semantic similarity and contradictions
        # 3. Identifying potential authenticity issues
        
        # Placeholder implementation
        consistency_analysis = {
            "analyzed_beliefs": belief_ids,
            "consistency_score": 0.85,  # Mock score
            "contradictions": [],
            "authenticity_warnings": [],
            "consistency_breakdown": {
                "semantic_alignment": 0.90,
                "value_alignment": 0.80,
                "temporal_consistency": 0.85
            },
            "recommendations": [
                "Beliefs show strong consistency across platforms",
                "No major contradictions detected"
            ]
        }
        
        logger.info(f"Epic 6: Consistency analysis complete with score: {consistency_analysis['consistency_score']}")
        return consistency_analysis
        
    except Exception as e:
        logger.error(f"Epic 6: Error analyzing belief consistency: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Belief consistency analysis failed: {str(e)}")


@router.get("/beliefs/timeline/{belief_id}")
async def get_belief_evolution_timeline(
    belief_id: str,
    tracker: TemporalTracker = Depends(get_temporal_tracker)
) -> Dict[str, Any]:
    """Get the evolution timeline of a specific belief across platforms (Epic 6)."""
    try:
        logger.info(f"Epic 6: Getting timeline for belief: {belief_id}")
        
        # TODO: Implement belief timeline retrieval from temporal tracker
        # This would track how a belief evolved across different content pieces
        
        # Placeholder implementation
        timeline = {
            "belief_id": belief_id,
            "evolution_stages": [
                {
                    "timestamp": "2024-01-01T00:00:00Z",
                    "platform": "notion",
                    "stage": "conception",
                    "content_snippet": "Initial thoughts on this topic...",
                    "confidence": 0.6
                },
                {
                    "timestamp": "2024-01-15T00:00:00Z", 
                    "platform": "linkedin",
                    "stage": "publication",
                    "content_snippet": "Sharing my belief that...",
                    "confidence": 0.9
                }
            ],
            "platforms_expressed": ["notion", "linkedin"],
            "consistency_over_time": 0.88,
            "engagement_correlation": {
                "highest_engagement_stage": "publication",
                "engagement_score": 85
            }
        }
        
        logger.info(f"Epic 6: Retrieved timeline with {len(timeline['evolution_stages'])} stages")
        return timeline
        
    except Exception as e:
        logger.error(f"Epic 6: Error getting belief timeline: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Belief timeline retrieval failed: {str(e)}")


@router.get("/preferences/recommendations")
async def get_preference_based_recommendations(
    user_id: Optional[str] = Query(None, description="User ID for personalized recommendations"),
    content_type: str = Query("all", description="Type of content to recommend"),
    limit: int = Query(10, description="Maximum number of recommendations")
) -> Dict[str, Any]:
    """Get content recommendations based on extracted preferences (Epic 6)."""
    try:
        logger.info(f"Epic 6: Generating preference-based recommendations for user: {user_id}")
        
        # TODO: Implement preference-based recommendation engine
        # This would analyze user preferences and suggest content strategies
        
        # Placeholder implementation
        recommendations = {
            "user_id": user_id,
            "content_recommendations": [
                {
                    "recommendation_id": "rec_001",
                    "content_type": "linkedin_post",
                    "topic": "leadership philosophy",
                    "reasoning": "Aligns with your expressed preference for authentic leadership",
                    "confidence": 0.92,
                    "expected_engagement": "high"
                },
                {
                    "recommendation_id": "rec_002", 
                    "content_type": "notion_article",
                    "topic": "process optimization",
                    "reasoning": "Matches your preference for systematic approaches",
                    "confidence": 0.85,
                    "expected_engagement": "medium"
                }
            ],
            "preference_alignment": {
                "methodology_preferences": 0.90,
                "topic_preferences": 0.88,
                "platform_preferences": 0.75
            },
            "optimization_suggestions": [
                "Consider expanding into video content based on your authentic communication style",
                "Your process-oriented thinking would resonate well in technical deep-dives"
            ]
        }
        
        logger.info(f"Epic 6: Generated {len(recommendations['content_recommendations'])} recommendations")
        return recommendations
        
    except Exception as e:
        logger.error(f"Epic 6: Error generating recommendations: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Preference-based recommendations failed: {str(e)}")


# === EPIC 7.3: HOT TAKE API ENDPOINTS WITH VIRAL PREDICTION + BRAND SAFETY ===

class HotTakeAnalysisRequest(BaseModel):
    """Request model for comprehensive hot take analysis."""
    text: str = Field(..., description="Hot take text to analyze")
    platform: str = Field(default="general", description="Platform: linkedin, twitter, general")
    brand_profile: str = Field(default="moderate", description="Brand safety profile: conservative, moderate, aggressive")
    context: Dict[str, Any] = Field(default_factory=dict, description="Additional context")


class QuickScoreRequest(BaseModel):
    """Request model for quick viral scoring."""
    text: str = Field(..., description="Content text for quick scoring")
    platform: str = Field(default="general", description="Platform for optimization")


class OptimizationRequest(BaseModel):
    """Request model for content optimization."""
    text: str = Field(..., description="Content to optimize")
    target_platform: str = Field(..., description="Target platform for optimization")
    optimization_goals: List[str] = Field(default_factory=list, description="Specific optimization goals")


class BatchAnalysisRequest(BaseModel):
    """Request model for batch hot take analysis."""
    content_items: List[Dict[str, str]] = Field(..., description="List of content items with text and platform")
    brand_profile: str = Field(default="moderate", description="Brand safety profile")


class HotTakeAnalysisResponse(BaseModel):
    """Comprehensive hot take analysis response."""
    content_id: str = Field(..., description="Unique content identifier")
    platform: str = Field(..., description="Analysis platform")
    
    # Viral prediction results
    viral_score: float = Field(..., description="Overall viral potential (0.0-1.0)")
    engagement_score: float = Field(..., description="Predicted engagement rate")
    reach_potential: float = Field(..., description="Potential audience reach")
    viral_velocity: float = Field(..., description="Speed of content spread")
    
    # Brand safety results
    safety_level: str = Field(..., description="Brand safety level: SAFE/CAUTION/RISK/DANGER")
    risk_score: float = Field(..., description="Overall risk score (0.0-1.0)")
    toxicity_score: float = Field(..., description="Content toxicity score")
    controversy_score: float = Field(..., description="Controversy potential")
    
    # Integrated analysis
    risk_adjusted_viral_score: float = Field(..., description="Viral score adjusted for safety risks")
    recommendation: str = Field(..., description="Publication recommendation")
    confidence: float = Field(..., description="Analysis confidence level")
    
    # Detailed insights
    key_features: List[str] = Field(default_factory=list, description="Key viral features identified")
    risk_factors: List[str] = Field(default_factory=list, description="Identified risk factors")
    crisis_triggers: List[str] = Field(default_factory=list, description="Potential crisis triggers")
    
    # Actionable recommendations
    improvement_suggestions: List[str] = Field(default_factory=list, description="Content improvement suggestions")
    content_modifications: List[str] = Field(default_factory=list, description="Safety-focused modifications")
    approval_workflow: List[str] = Field(default_factory=list, description="Required approval steps")
    
    # Timing and optimization
    optimal_posting_time: Optional[str] = Field(default=None, description="Suggested posting time")
    platform_optimization_score: float = Field(..., description="Platform-specific optimization score")
    
    analysis_timestamp: str = Field(..., description="Analysis timestamp")


class QuickScoreResponse(BaseModel):
    """Quick viral scoring response."""
    content_id: str = Field(..., description="Content identifier")
    viral_score: float = Field(..., description="Quick viral potential score")
    engagement_score: float = Field(..., description="Engagement prediction")
    safety_level: str = Field(..., description="Quick safety assessment")
    recommendation: str = Field(..., description="Immediate recommendation")
    confidence: float = Field(..., description="Score confidence")
    analysis_time_ms: float = Field(..., description="Analysis time in milliseconds")


class OptimizationResponse(BaseModel):
    """Content optimization response."""
    original_score: float = Field(..., description="Original viral score")
    optimized_strategies: List[Dict[str, Any]] = Field(..., description="Platform-specific optimization strategies")
    improvement_potential: float = Field(..., description="Potential score improvement")
    priority_actions: List[str] = Field(..., description="High-priority optimization actions")
    platform_insights: Dict[str, Any] = Field(default_factory=dict, description="Platform-specific insights")
    estimated_impact: Dict[str, float] = Field(default_factory=dict, description="Estimated impact of changes")


class TrendingResponse(BaseModel):
    """Trending hot take patterns response."""
    trending_patterns: List[Dict[str, Any]] = Field(..., description="Current trending patterns")
    viral_themes: List[str] = Field(..., description="Viral content themes")
    platform_trends: Dict[str, Any] = Field(default_factory=dict, description="Platform-specific trends")
    recommendation_score: float = Field(..., description="Trend alignment score")
    analysis_period: str = Field(..., description="Analysis time period")


class BatchAnalysisResponse(BaseModel):
    """Batch analysis response."""
    total_analyzed: int = Field(..., description="Total content items analyzed")
    analysis_summary: Dict[str, Any] = Field(..., description="Batch analysis summary")
    individual_results: List[HotTakeAnalysisResponse] = Field(..., description="Individual analysis results")
    comparative_insights: Dict[str, Any] = Field(default_factory=dict, description="Comparative analysis insights")
    batch_recommendations: List[str] = Field(default_factory=list, description="Batch-level recommendations")


class SafetyCheckResponse(BaseModel):
    """Brand safety validation response."""
    content_id: str = Field(..., description="Content identifier")
    safety_level: str = Field(..., description="Safety classification")
    risk_dimensions: Dict[str, float] = Field(..., description="Multi-dimensional risk scores")
    stakeholder_impact: Dict[str, str] = Field(..., description="Impact on stakeholder groups")
    crisis_risk: Dict[str, Any] = Field(..., description="Crisis escalation assessment")
    mitigation_strategy: Dict[str, Any] = Field(..., description="Risk mitigation recommendations")
    approval_required: bool = Field(..., description="Whether approval is required")
    monitoring_required: bool = Field(..., description="Whether monitoring is required")


class AnalyticsResponse(BaseModel):
    """Hot take performance analytics response."""
    performance_metrics: Dict[str, float] = Field(..., description="Overall performance metrics")
    trend_analysis: Dict[str, Any] = Field(..., description="Performance trend analysis")
    comparative_benchmarks: Dict[str, float] = Field(..., description="Industry/platform benchmarks")
    success_factors: List[str] = Field(..., description="Key success factors identified")
    optimization_opportunities: List[str] = Field(..., description="Optimization opportunities")
    predictive_insights: Dict[str, Any] = Field(default_factory=dict, description="Predictive performance insights")


@router.post("/hot-takes/analyze", response_model=HotTakeAnalysisResponse)
async def analyze_hot_take(
    request: HotTakeAnalysisRequest,
    viral_engine = Depends(get_viral_prediction_engine),
    safety_analyzer = Depends(get_brand_safety_analyzer),
    belief_extractor = Depends(get_belief_preference_extractor)
) -> HotTakeAnalysisResponse:
    """Comprehensive hot take analysis combining viral prediction and brand safety assessment (Epic 7.3)."""
    try:
        start_time = asyncio.get_event_loop().time()
        
        logger.info(f"Epic 7.3: Analyzing hot take for {request.platform} platform with {request.brand_profile} brand profile")
        
        # Extract platform enum
        from graph_rag.core.viral_prediction_engine import Platform
        platform_map = {"linkedin": Platform.LINKEDIN, "twitter": Platform.TWITTER, "general": Platform.GENERAL}
        platform = platform_map.get(request.platform.lower(), Platform.GENERAL)
        
        # Extract brand profile enum
        from graph_rag.core.brand_safety_analyzer import BrandProfile
        profile_map = {"conservative": BrandProfile.CONSERVATIVE, "moderate": BrandProfile.MODERATE, "aggressive": BrandProfile.AGGRESSIVE}
        brand_profile = profile_map.get(request.brand_profile.lower(), BrandProfile.MODERATE)
        
        # Extract concepts for context
        concept_result = await belief_extractor.extract_beliefs_and_preferences(request.text, {**request.context, "platform": request.platform})
        concepts = concept_result.get("all_concepts", [])
        hot_takes = concept_result.get("hot_takes", [])
        
        # Generate content ID
        content_id = f"hottake_{hash(request.text[:100])}_{int(start_time)}"
        
        # Run viral prediction and brand safety analysis in parallel
        viral_task = viral_engine.predict_viral_potential(request.text, platform, content_id, request.context)
        safety_task = safety_analyzer.assess_brand_safety(request.text, platform, content_id, concepts, request.context)
        
        viral_prediction, safety_assessment = await asyncio.gather(viral_task, safety_task)
        
        # Generate recommendation based on combined analysis
        recommendation = _generate_publication_recommendation(viral_prediction, safety_assessment)
        
        # Calculate risk-adjusted viral score
        risk_adjusted_score = viral_prediction.overall_viral_score * (1.0 - safety_assessment.risk_score.overall * 0.5)
        
        # Determine optimal posting time
        optimal_time = viral_prediction.optimal_posting_time.isoformat() if viral_prediction.optimal_posting_time else None
        
        # Combine improvement suggestions
        combined_suggestions = viral_prediction.improvement_suggestions + safety_assessment.content_modifications
        
        end_time = asyncio.get_event_loop().time()
        analysis_time = (end_time - start_time) * 1000
        
        logger.info(f"Epic 7.3: Analysis complete in {analysis_time:.2f}ms - Viral: {viral_prediction.overall_viral_score:.2f}, Safety: {safety_assessment.safety_level.value}, Risk-Adjusted: {risk_adjusted_score:.2f}")
        
        return HotTakeAnalysisResponse(
            content_id=content_id,
            platform=request.platform,
            viral_score=viral_prediction.overall_viral_score,
            engagement_score=viral_prediction.engagement_score,
            reach_potential=viral_prediction.reach_potential,
            viral_velocity=viral_prediction.viral_velocity,
            safety_level=safety_assessment.safety_level.value.upper(),
            risk_score=safety_assessment.risk_score.overall,
            toxicity_score=safety_assessment.toxicity_assessment.toxicity_score,
            controversy_score=safety_assessment.controversy_analysis.controversy_score,
            risk_adjusted_viral_score=risk_adjusted_score,
            recommendation=recommendation,
            confidence=min(viral_prediction.confidence, safety_assessment.confidence),
            key_features=viral_prediction.key_features,
            risk_factors=safety_assessment.risk_factors,
            crisis_triggers=safety_assessment.crisis_triggers,
            improvement_suggestions=viral_prediction.improvement_suggestions,
            content_modifications=safety_assessment.content_modifications,
            approval_workflow=safety_assessment.approval_workflow,
            optimal_posting_time=optimal_time,
            platform_optimization_score=viral_prediction.platform_optimization_score,
            analysis_timestamp=datetime.utcnow().isoformat()
        )
        
    except Exception as e:
        logger.error(f"Epic 7.3: Error analyzing hot take: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Hot take analysis failed: {str(e)}")


@router.post("/hot-takes/quick-score", response_model=QuickScoreResponse)
async def quick_score_hot_take(
    request: QuickScoreRequest,
    viral_engine = Depends(get_viral_prediction_engine),
    safety_analyzer = Depends(get_brand_safety_analyzer)
) -> QuickScoreResponse:
    """Fast viral scoring for immediate feedback (Epic 7.3)."""
    try:
        start_time = asyncio.get_event_loop().time()
        
        # Extract platform enum
        from graph_rag.core.viral_prediction_engine import Platform
        platform_map = {"linkedin": Platform.LINKEDIN, "twitter": Platform.TWITTER, "general": Platform.GENERAL}
        platform = platform_map.get(request.platform.lower(), Platform.GENERAL)
        
        content_id = f"quick_{hash(request.text[:50])}_{int(start_time)}"
        
        # Run quick predictions in parallel
        viral_task = viral_engine.predict_viral_potential(request.text, platform, content_id)
        safety_task = safety_analyzer.assess_brand_safety(request.text, platform, content_id)
        
        viral_prediction, safety_assessment = await asyncio.gather(viral_task, safety_task)
        
        # Quick recommendation
        if safety_assessment.safety_level.value == "danger":
            recommendation = "❌ DO NOT PUBLISH - High risk content"
        elif safety_assessment.safety_level.value == "risk":
            recommendation = "⚠️ REQUIRES APPROVAL - Significant risks identified"
        elif viral_prediction.overall_viral_score > 0.7 and safety_assessment.safety_level.value in ["safe", "caution"]:
            recommendation = "🚀 HIGH VIRAL POTENTIAL - Consider publishing"
        elif viral_prediction.overall_viral_score > 0.5:
            recommendation = "📈 MODERATE POTENTIAL - Good for engagement"
        else:
            recommendation = "📝 LOW VIRAL POTENTIAL - Consider optimization"
        
        end_time = asyncio.get_event_loop().time()
        analysis_time = (end_time - start_time) * 1000
        
        return QuickScoreResponse(
            content_id=content_id,
            viral_score=viral_prediction.overall_viral_score,
            engagement_score=viral_prediction.engagement_score,
            safety_level=safety_assessment.safety_level.value.upper(),
            recommendation=recommendation,
            confidence=min(viral_prediction.confidence, safety_assessment.confidence),
            analysis_time_ms=analysis_time
        )
        
    except Exception as e:
        logger.error(f"Epic 7.3: Error in quick scoring: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Quick scoring failed: {str(e)}")


@router.post("/hot-takes/optimize", response_model=OptimizationResponse)
async def optimize_hot_take(
    request: OptimizationRequest,
    viral_engine = Depends(get_viral_prediction_engine)
) -> OptimizationResponse:
    """Content optimization suggestions for hot takes (Epic 7.3)."""
    try:
        # Extract platform enum
        from graph_rag.core.viral_prediction_engine import Platform
        platform_map = {"linkedin": Platform.LINKEDIN, "twitter": Platform.TWITTER, "general": Platform.GENERAL}
        target_platform = platform_map.get(request.target_platform.lower(), Platform.GENERAL)
        
        # Get original score
        original_prediction = await viral_engine.predict_viral_potential(request.text, target_platform)
        
        # Get platform-specific optimizations
        optimization_strategies = await viral_engine.optimize_for_platform(request.text, target_platform)
        
        # Estimate improvement potential
        improvement_potential = min(0.3, (1.0 - original_prediction.overall_viral_score) * 0.6)
        
        # Priority actions based on analysis
        priority_actions = []
        if original_prediction.engagement_score < 0.5:
            priority_actions.append("Add stronger call-to-action elements")
        if original_prediction.controversy_score < 0.3:
            priority_actions.append("Consider more provocative but safe angles")
        if original_prediction.platform_optimization_score < 0.6:
            priority_actions.extend(optimization_strategies.get('optimizations', [])[:2])
        
        # Estimated impact of changes
        estimated_impact = {
            "engagement_boost": improvement_potential * 0.4,
            "reach_improvement": improvement_potential * 0.3,
            "viral_velocity_gain": improvement_potential * 0.2,
            "platform_fit_enhancement": improvement_potential * 0.1
        }
        
        return OptimizationResponse(
            original_score=original_prediction.overall_viral_score,
            optimized_strategies=[optimization_strategies],
            improvement_potential=improvement_potential,
            priority_actions=priority_actions,
            platform_insights=optimization_strategies,
            estimated_impact=estimated_impact
        )
        
    except Exception as e:
        logger.error(f"Epic 7.3: Error optimizing content: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Content optimization failed: {str(e)}")


@router.get("/hot-takes/trending", response_model=TrendingResponse)
async def get_trending_patterns() -> TrendingResponse:
    """Get trending hot take patterns and viral themes (Epic 7.3)."""
    try:
        # Mock trending analysis - in production would analyze recent viral content
        trending_patterns = [
            {
                "pattern": "contrarian_business_takes",
                "viral_score": 0.85,
                "engagement_rate": 0.12,
                "examples": ["remote work criticism", "startup bubble warnings"]
            },
            {
                "pattern": "leadership_authenticity",
                "viral_score": 0.72,
                "engagement_rate": 0.08,
                "examples": ["vulnerable leadership", "failure stories"]
            },
            {
                "pattern": "industry_disruption",
                "viral_score": 0.78,
                "engagement_rate": 0.10,
                "examples": ["AI job displacement", "traditional industry obsolescence"]
            }
        ]
        
        viral_themes = [
            "authentic leadership challenges",
            "remote work effectiveness debates",
            "AI impact on careers",
            "startup culture criticism",
            "traditional vs modern approaches"
        ]
        
        platform_trends = {
            "linkedin": {
                "top_theme": "professional authenticity",
                "engagement_peak_hours": ["9-11 AM", "1-3 PM", "6-8 PM"],
                "viral_content_types": ["personal stories", "controversial opinions", "industry insights"]
            },
            "twitter": {
                "top_theme": "tech industry takes",
                "engagement_peak_hours": ["8-10 AM", "12-2 PM", "7-9 PM"],
                "viral_content_types": ["hot takes", "threads", "contrarian views"]
            }
        }
        
        return TrendingResponse(
            trending_patterns=trending_patterns,
            viral_themes=viral_themes,
            platform_trends=platform_trends,
            recommendation_score=0.82,
            analysis_period="Last 7 days"
        )
        
    except Exception as e:
        logger.error(f"Epic 7.3: Error getting trending patterns: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Trending analysis failed: {str(e)}")


@router.post("/hot-takes/batch-analyze", response_model=BatchAnalysisResponse)
async def batch_analyze_hot_takes(
    request: BatchAnalysisRequest,
    viral_engine = Depends(get_viral_prediction_engine),
    safety_analyzer = Depends(get_brand_safety_analyzer),
    belief_extractor = Depends(get_belief_preference_extractor)
) -> BatchAnalysisResponse:
    """Batch processing for multiple hot takes (Epic 7.3)."""
    try:
        logger.info(f"Epic 7.3: Starting batch analysis of {len(request.content_items)} items")
        
        individual_results = []
        viral_scores = []
        safety_levels = []
        
        for i, item in enumerate(request.content_items):
            try:
                # Create individual analysis request
                analysis_request = HotTakeAnalysisRequest(
                    text=item.get("text", ""),
                    platform=item.get("platform", "general"),
                    brand_profile=request.brand_profile
                )
                
                # Analyze individual item
                result = await analyze_hot_take(analysis_request, viral_engine, safety_analyzer, belief_extractor)
                individual_results.append(result)
                viral_scores.append(result.viral_score)
                safety_levels.append(result.safety_level)
                
            except Exception as e:
                logger.warning(f"Epic 7.3: Error analyzing batch item {i}: {e}")
                continue
        
        # Generate batch analytics
        avg_viral_score = sum(viral_scores) / len(viral_scores) if viral_scores else 0.0
        safety_distribution = {level: safety_levels.count(level) for level in set(safety_levels)}
        
        high_potential_count = sum(1 for score in viral_scores if score > 0.7)
        risky_content_count = sum(1 for level in safety_levels if level in ["RISK", "DANGER"])
        
        analysis_summary = {
            "total_processed": len(individual_results),
            "average_viral_score": avg_viral_score,
            "high_potential_content": high_potential_count,
            "risky_content": risky_content_count,
            "safety_distribution": safety_distribution,
            "batch_processing_success_rate": len(individual_results) / len(request.content_items) if request.content_items else 0.0
        }
        
        comparative_insights = {
            "best_performing_content": max(individual_results, key=lambda x: x.viral_score, default=None),
            "highest_risk_content": max(individual_results, key=lambda x: x.risk_score, default=None),
            "platform_performance": _analyze_platform_performance(individual_results),
            "content_type_insights": _analyze_content_types(individual_results)
        }
        
        batch_recommendations = []
        if high_potential_count > 0:
            batch_recommendations.append(f"📈 {high_potential_count} items show high viral potential - prioritize these")
        if risky_content_count > 0:
            batch_recommendations.append(f"⚠️ {risky_content_count} items require safety review")
        if avg_viral_score < 0.4:
            batch_recommendations.append("🔧 Overall viral potential is low - consider content optimization strategies")
        
        logger.info(f"Epic 7.3: Batch analysis complete - {len(individual_results)}/{len(request.content_items)} processed successfully")
        
        return BatchAnalysisResponse(
            total_analyzed=len(individual_results),
            analysis_summary=analysis_summary,
            individual_results=individual_results,
            comparative_insights=comparative_insights,
            batch_recommendations=batch_recommendations
        )
        
    except Exception as e:
        logger.error(f"Epic 7.3: Error in batch analysis: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Batch analysis failed: {str(e)}")


@router.post("/hot-takes/safety-check", response_model=SafetyCheckResponse)
async def safety_check_hot_take(
    request: HotTakeAnalysisRequest,
    safety_analyzer = Depends(get_brand_safety_analyzer),
    belief_extractor = Depends(get_belief_preference_extractor)
) -> SafetyCheckResponse:
    """Brand safety validation for hot takes (Epic 7.3)."""
    try:
        # Extract platform and brand profile
        from graph_rag.core.viral_prediction_engine import Platform
        from graph_rag.core.brand_safety_analyzer import BrandProfile
        
        platform_map = {"linkedin": Platform.LINKEDIN, "twitter": Platform.TWITTER, "general": Platform.GENERAL}
        platform = platform_map.get(request.platform.lower(), Platform.GENERAL)
        
        profile_map = {"conservative": BrandProfile.CONSERVATIVE, "moderate": BrandProfile.MODERATE, "aggressive": BrandProfile.AGGRESSIVE}
        brand_profile = profile_map.get(request.brand_profile.lower(), BrandProfile.MODERATE)
        
        # Extract concepts for context
        concept_result = await belief_extractor.extract_beliefs_and_preferences(request.text, {**request.context, "platform": request.platform})
        concepts = concept_result.get("all_concepts", [])
        
        content_id = f"safety_{hash(request.text[:100])}_{int(asyncio.get_event_loop().time())}"
        
        # Perform brand safety assessment
        safety_assessment = await safety_analyzer.assess_brand_safety(request.text, platform, content_id, concepts, request.context)
        
        # Format response
        risk_dimensions = {
            "reputational": safety_assessment.risk_score.reputational,
            "legal": safety_assessment.risk_score.legal,
            "financial": safety_assessment.risk_score.financial,
            "operational": safety_assessment.risk_score.operational
        }
        
        stakeholder_impact = {
            "customers": safety_assessment.stakeholder_analysis.customers.value,
            "employees": safety_assessment.stakeholder_analysis.employees.value,
            "investors": safety_assessment.stakeholder_analysis.investors.value,
            "partners": safety_assessment.stakeholder_analysis.partners.value,
            "general_public": safety_assessment.stakeholder_analysis.general_public.value
        }
        
        crisis_risk = {
            "escalation_probability": safety_assessment.crisis_risk.escalation_probability,
            "viral_amplification_risk": safety_assessment.crisis_risk.viral_amplification_risk,
            "media_attention_risk": safety_assessment.crisis_risk.media_attention_risk,
            "response_urgency": safety_assessment.crisis_risk.response_urgency,
            "crisis_triggers": safety_assessment.crisis_risk.crisis_triggers
        }
        
        mitigation_strategy = {
            "priority": safety_assessment.mitigation_strategy.priority,
            "actions": safety_assessment.mitigation_strategy.actions,
            "alternative_approaches": safety_assessment.mitigation_strategy.alternative_approaches,
            "decision_deadline": safety_assessment.mitigation_strategy.decision_deadline.isoformat() if safety_assessment.mitigation_strategy.decision_deadline else None
        }
        
        return SafetyCheckResponse(
            content_id=content_id,
            safety_level=safety_assessment.safety_level.value.upper(),
            risk_dimensions=risk_dimensions,
            stakeholder_impact=stakeholder_impact,
            crisis_risk=crisis_risk,
            mitigation_strategy=mitigation_strategy,
            approval_required=safety_assessment.mitigation_strategy.approval_required,
            monitoring_required=safety_assessment.mitigation_strategy.monitoring_required
        )
        
    except Exception as e:
        logger.error(f"Epic 7.3: Error in safety check: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Safety check failed: {str(e)}")


@router.get("/hot-takes/analytics", response_model=AnalyticsResponse)
async def get_hot_take_analytics(
    days: int = Query(30, description="Number of days for analytics"),
    platform: Optional[str] = Query(None, description="Platform filter")
) -> AnalyticsResponse:
    """Hot take performance analytics (Epic 7.3)."""
    try:
        # Mock analytics - in production would analyze historical data
        performance_metrics = {
            "average_viral_score": 0.65,
            "average_engagement_rate": 0.08,
            "content_safety_score": 0.82,
            "approval_rate": 0.75,
            "crisis_avoidance_rate": 0.95
        }
        
        trend_analysis = {
            "viral_score_trend": "increasing",
            "engagement_trend": "stable",
            "risk_trend": "decreasing",
            "trending_topics": ["AI impact", "remote work", "leadership authenticity"],
            "optimal_posting_times": ["9-11 AM", "1-3 PM", "6-8 PM"]
        }
        
        comparative_benchmarks = {
            "industry_average_viral": 0.45,
            "platform_average_engagement": 0.06,
            "competitor_safety_score": 0.78,
            "market_controversy_tolerance": 0.55
        }
        
        success_factors = [
            "Authentic personal stories",
            "Contrarian but respectful viewpoints",
            "Industry-specific insights",
            "Timely responses to trends",
            "Strategic controversy within safety bounds"
        ]
        
        optimization_opportunities = [
            "Increase emotional intensity while maintaining safety",
            "Better timing alignment with platform peak hours",
            "Enhanced call-to-action elements",
            "Improved platform-specific optimization",
            "Strategic use of trending topics"
        ]
        
        predictive_insights = {
            "next_viral_trend": "workplace mental health discussions",
            "emerging_risk_areas": ["AI ethics debates", "economic uncertainty topics"],
            "optimal_content_mix": "60% insights, 25% hot takes, 15% personal stories",
            "predicted_engagement_growth": 0.12
        }
        
        return AnalyticsResponse(
            performance_metrics=performance_metrics,
            trend_analysis=trend_analysis,
            comparative_benchmarks=comparative_benchmarks,
            success_factors=success_factors,
            optimization_opportunities=optimization_opportunities,
            predictive_insights=predictive_insights
        )
        
    except Exception as e:
        logger.error(f"Epic 7.3: Error getting analytics: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Analytics retrieval failed: {str(e)}")


# === HELPER FUNCTIONS FOR EPIC 7.3 ===

def _generate_publication_recommendation(viral_prediction, safety_assessment) -> str:
    """Generate publication recommendation based on viral and safety analysis."""
    safety_level = safety_assessment.safety_level.value
    viral_score = viral_prediction.overall_viral_score
    risk_score = safety_assessment.risk_score.overall
    
    if safety_level == "danger":
        return "🚫 DO NOT PUBLISH - Content poses significant brand safety risks"
    elif safety_level == "risk":
        return "⚠️ REQUIRES SENIOR APPROVAL - High-risk content with potential consequences"
    elif safety_level == "caution" and viral_score > 0.8:
        return "🔍 REVIEW RECOMMENDED - High viral potential but requires careful monitoring"
    elif viral_score > 0.7 and risk_score < 0.3:
        return "🚀 PUBLISH WITH CONFIDENCE - High viral potential, low risk"
    elif viral_score > 0.5 and risk_score < 0.5:
        return "📈 GOOD TO PUBLISH - Solid viral potential with manageable risk"
    elif viral_score < 0.3:
        return "📝 CONSIDER OPTIMIZATION - Low viral potential, optimize before publishing"
    else:
        return "✅ STANDARD APPROVAL - Moderate potential, standard review process"


def _analyze_platform_performance(results: List[HotTakeAnalysisResponse]) -> Dict[str, Any]:
    """Analyze performance by platform."""
    platform_data = {}
    for result in results:
        platform = result.platform
        if platform not in platform_data:
            platform_data[platform] = {"scores": [], "safety_levels": []}
        platform_data[platform]["scores"].append(result.viral_score)
        platform_data[platform]["safety_levels"].append(result.safety_level)
    
    performance = {}
    for platform, data in platform_data.items():
        performance[platform] = {
            "average_viral_score": sum(data["scores"]) / len(data["scores"]) if data["scores"] else 0.0,
            "content_count": len(data["scores"]),
            "safety_distribution": {level: data["safety_levels"].count(level) for level in set(data["safety_levels"])}
        }
    
    return performance


def _analyze_content_types(results: List[HotTakeAnalysisResponse]) -> Dict[str, Any]:
    """Analyze performance by content characteristics."""
    high_viral = [r for r in results if r.viral_score > 0.7]
    high_risk = [r for r in results if r.risk_score > 0.6]
    
    return {
        "high_viral_characteristics": {
            "count": len(high_viral),
            "average_engagement": sum(r.engagement_score for r in high_viral) / len(high_viral) if high_viral else 0.0,
            "common_features": _extract_common_features([r.key_features for r in high_viral])
        },
        "high_risk_characteristics": {
            "count": len(high_risk),
            "common_risks": _extract_common_features([r.risk_factors for r in high_risk]),
            "average_toxicity": sum(r.toxicity_score for r in high_risk) / len(high_risk) if high_risk else 0.0
        }
    }


def _extract_common_features(feature_lists: List[List[str]]) -> List[str]:
    """Extract commonly occurring features across multiple lists."""
    if not feature_lists:
        return []
    
    feature_counts = {}
    for features in feature_lists:
        for feature in features:
            feature_counts[feature] = feature_counts.get(feature, 0) + 1
    
    # Return features that appear in at least 25% of lists
    threshold = max(1, len(feature_lists) * 0.25)
    common_features = [feature for feature, count in feature_counts.items() if count >= threshold]
    return sorted(common_features, key=lambda x: feature_counts[x], reverse=True)[:5]


# === EPIC 8.3 & 8.4: AUDIENCE INTELLIGENCE & COMPETITIVE ANALYSIS API ENDPOINTS ===

# Import additional dependencies for Epic 8
from graph_rag.core.audience_intelligence import AudienceSegmentationEngine, AudienceSegment, AudiencePersona
from graph_rag.core.competitive_analysis import CompetitiveAnalyzer, CompetitiveAnalysisResult

# === EPIC 9.3: CONTENT STRATEGY API ENDPOINTS AND AUTOMATION ===

# Import Epic 9 content strategy engines
from graph_rag.core.content_strategy_optimizer import (
    ContentStrategyOptimizer, StrategicRecommendation, ContentGap, 
    PerformancePrediction, ResourcePlan, ContentCalendar, StrategyObjective,
    CompetitivePosition, ContentFormat
)
from graph_rag.core.content_optimization_engine import (
    ContentOptimizationEngine, OptimizationRequest, OptimizationResult,
    ContentAnalysis, OptimizationType, SuggestionCategory, ImprovementPriority
)


# === EPIC 9.3: PYDANTIC MODELS FOR CONTENT STRATEGY API ===

class StrategyOptimizationRequest(BaseModel):
    """Request model for full content strategy optimization."""
    business_context: Dict[str, Any] = Field(..., description="Business objectives, target audience, brand guidelines")
    content_samples: List[str] = Field(default_factory=list, description="Sample content for analysis")
    competitive_analysis: Optional[Dict[str, Any]] = Field(None, description="Competitive landscape analysis")
    historical_performance: Optional[Dict[str, Any]] = Field(None, description="Historical content performance data")
    brand_profile: str = Field(default="moderate", description="Brand safety profile: conservative, moderate, aggressive")
    optimization_goals: List[str] = Field(default_factory=list, description="Specific optimization goals")


class StrategyOptimizationResponse(BaseModel):
    """Response model for strategy optimization."""
    strategy_id: str = Field(..., description="Unique strategy identifier")
    strategy: Dict[str, Any] = Field(..., description="Complete strategic recommendation")
    optimization_summary: Dict[str, Any] = Field(..., description="Optimization process summary")
    confidence_metrics: Dict[str, float] = Field(..., description="Various confidence scores")
    implementation_timeline: Dict[str, Any] = Field(..., description="Implementation timeline and milestones")
    resource_requirements: Dict[str, Any] = Field(..., description="Resource planning details")
    performance_predictions: Dict[str, Any] = Field(..., description="Performance forecasts")
    next_steps: List[str] = Field(..., description="Recommended next steps")


class StrategyAnalysisRequest(BaseModel):
    """Request model for content strategy analysis."""
    existing_content: List[str] = Field(..., description="Existing content to analyze")
    target_audience: str = Field(..., description="Target audience description")
    business_objectives: List[str] = Field(..., description="Business objectives")
    platform: str = Field(default="general", description="Primary platform focus")
    analysis_depth: str = Field(default="comprehensive", description="Analysis depth: basic, standard, comprehensive")


class StrategyAnalysisResponse(BaseModel):
    """Response model for strategy analysis."""
    analysis_id: str = Field(..., description="Analysis identifier")
    content_gaps: List[Dict[str, Any]] = Field(..., description="Identified content gaps")
    audience_insights: Dict[str, Any] = Field(..., description="Audience analysis insights")
    competitive_position: Dict[str, Any] = Field(..., description="Competitive positioning analysis")
    strategic_recommendations: List[str] = Field(..., description="Strategic recommendations")
    opportunity_prioritization: List[Dict[str, Any]] = Field(..., description="Prioritized opportunities")
    analysis_confidence: float = Field(..., description="Analysis confidence level")


class ContentOptimizationRequest(BaseModel):
    """Request model for individual content optimization."""
    content: str = Field(..., description="Content to optimize")
    target_audience: Optional[str] = Field(None, description="Target audience description")
    platform: str = Field(default="general", description="Target platform")
    optimization_types: List[str] = Field(default_factory=list, description="Specific optimization types to focus on")
    brand_guidelines: Optional[Dict[str, Any]] = Field(None, description="Brand guidelines and constraints")
    current_performance: Optional[Dict[str, Any]] = Field(None, description="Current content performance metrics")


class ContentOptimizationResponse(BaseModel):
    """Response model for content optimization."""
    optimization_id: str = Field(..., description="Optimization identifier")
    original_content: str = Field(..., description="Original content")
    optimized_content: str = Field(..., description="Optimized content version")
    improvement_suggestions: List[Dict[str, Any]] = Field(..., description="Specific improvement suggestions")
    quality_metrics: Dict[str, float] = Field(..., description="Content quality assessment")
    predicted_improvements: Dict[str, Any] = Field(..., description="Predicted performance improvements")
    optimization_confidence: float = Field(..., description="Optimization confidence score")
    implementation_priority: str = Field(..., description="Implementation priority level")


class ContentAnalysisRequest(BaseModel):
    """Request model for content quality analysis."""
    content: str = Field(..., description="Content to analyze")
    analysis_dimensions: List[str] = Field(default_factory=list, description="Specific analysis dimensions")
    benchmark_content: Optional[List[str]] = Field(None, description="Benchmark content for comparison")
    context: Dict[str, Any] = Field(default_factory=dict, description="Additional context for analysis")


class ContentAnalysisResponse(BaseModel):
    """Response model for content analysis."""
    analysis_id: str = Field(..., description="Analysis identifier")
    content_summary: Dict[str, Any] = Field(..., description="Content summary and characteristics")
    quality_assessment: Dict[str, float] = Field(..., description="Multi-dimensional quality scores")
    strengths: List[str] = Field(..., description="Identified content strengths")
    weaknesses: List[str] = Field(..., description="Identified areas for improvement")
    benchmark_comparison: Optional[Dict[str, Any]] = Field(None, description="Comparison with benchmark content")
    recommendations: List[str] = Field(..., description="Improvement recommendations")
    analysis_confidence: float = Field(..., description="Analysis confidence level")


class ContentVariationsRequest(BaseModel):
    """Request model for A/B testing content variations."""
    original_content: str = Field(..., description="Original content to create variations for")
    variation_count: int = Field(default=3, description="Number of variations to generate")
    variation_goals: List[str] = Field(default_factory=list, description="Goals for variations (e.g., higher engagement, different tone)")
    platform: str = Field(default="general", description="Target platform for variations")
    audience_segments: List[str] = Field(default_factory=list, description="Target audience segments")


class ContentVariationsResponse(BaseModel):
    """Response model for content variations."""
    original_content: str = Field(..., description="Original content")
    variations: List[Dict[str, Any]] = Field(..., description="Generated content variations")
    variation_analysis: Dict[str, Any] = Field(..., description="Analysis of variation differences")
    testing_recommendations: List[str] = Field(..., description="A/B testing recommendations")
    predicted_performance: Dict[str, Any] = Field(..., description="Predicted performance for each variation")


class PerformancePredictionRequest(BaseModel):
    """Request model for content performance prediction."""
    content: str = Field(..., description="Content to analyze for performance prediction")
    platform: str = Field(default="general", description="Target platform")
    audience_data: Optional[Dict[str, Any]] = Field(None, description="Target audience data")
    publishing_context: Dict[str, Any] = Field(default_factory=dict, description="Publishing context (timing, campaign, etc.)")
    historical_context: Optional[Dict[str, Any]] = Field(None, description="Historical performance context")


class PerformancePredictionResponse(BaseModel):
    """Response model for performance prediction."""
    content_id: str = Field(..., description="Content identifier")
    performance_forecast: Dict[str, Any] = Field(..., description="Detailed performance predictions")
    confidence_intervals: Dict[str, Tuple[float, float, float]] = Field(..., description="Min, expected, max predictions")
    key_performance_drivers: List[str] = Field(..., description="Factors driving predicted performance")
    risk_factors: List[str] = Field(..., description="Potential performance risk factors")
    optimization_suggestions: List[str] = Field(..., description="Suggestions for performance improvement")
    prediction_confidence: float = Field(..., description="Prediction confidence level")


class BatchOptimizationRequest(BaseModel):
    """Request model for batch content optimization."""
    content_items: List[Dict[str, Any]] = Field(..., description="List of content items to optimize")
    optimization_criteria: Dict[str, Any] = Field(..., description="Shared optimization criteria")
    priority_order: Optional[List[str]] = Field(None, description="Priority order for optimization")
    resource_constraints: Optional[Dict[str, Any]] = Field(None, description="Resource constraints for optimization")


class BatchOptimizationResponse(BaseModel):
    """Response model for batch optimization."""
    batch_id: str = Field(..., description="Batch optimization identifier")
    total_items: int = Field(..., description="Total items processed")
    optimization_summary: Dict[str, Any] = Field(..., description="Batch optimization summary")
    individual_results: List[Dict[str, Any]] = Field(..., description="Individual optimization results")
    prioritized_recommendations: List[str] = Field(..., description="Prioritized batch recommendations")
    resource_allocation: Dict[str, Any] = Field(..., description="Recommended resource allocation")
    implementation_roadmap: List[Dict[str, Any]] = Field(..., description="Implementation roadmap")


class WorkflowRequest(BaseModel):
    """Request model for creating optimization workflows."""
    workflow_name: str = Field(..., description="Name for the optimization workflow")
    workflow_type: str = Field(..., description="Type of workflow: continuous, scheduled, trigger-based")
    content_sources: List[str] = Field(..., description="Content sources to monitor/optimize")
    optimization_criteria: Dict[str, Any] = Field(..., description="Optimization criteria and thresholds")
    schedule: Optional[Dict[str, Any]] = Field(None, description="Schedule configuration for scheduled workflows")
    triggers: Optional[List[str]] = Field(None, description="Trigger conditions for trigger-based workflows")
    approval_settings: Dict[str, Any] = Field(default_factory=dict, description="Approval workflow settings")


class WorkflowResponse(BaseModel):
    """Response model for workflow operations."""
    workflow_id: str = Field(..., description="Workflow identifier")
    workflow_name: str = Field(..., description="Workflow name")
    status: str = Field(..., description="Workflow status")
    configuration: Dict[str, Any] = Field(..., description="Workflow configuration")
    last_execution: Optional[datetime] = Field(None, description="Last execution timestamp")
    next_execution: Optional[datetime] = Field(None, description="Next scheduled execution")
    execution_history: List[Dict[str, Any]] = Field(default_factory=list, description="Recent execution history")
    performance_metrics: Dict[str, Any] = Field(default_factory=dict, description="Workflow performance metrics")


class ScheduleRequest(BaseModel):
    """Request model for scheduling optimization tasks."""
    task_type: str = Field(..., description="Type of optimization task")
    task_parameters: Dict[str, Any] = Field(..., description="Task-specific parameters")
    schedule_type: str = Field(..., description="Schedule type: one-time, recurring, conditional")
    schedule_config: Dict[str, Any] = Field(..., description="Schedule configuration")
    priority: str = Field(default="medium", description="Task priority")
    dependencies: List[str] = Field(default_factory=list, description="Task dependencies")


class ScheduleResponse(BaseModel):
    """Response model for scheduled tasks."""
    task_id: str = Field(..., description="Scheduled task identifier")
    task_type: str = Field(..., description="Task type")
    schedule_status: str = Field(..., description="Schedule status")
    next_execution: datetime = Field(..., description="Next execution time")
    execution_count: int = Field(..., description="Number of executions")
    last_result: Optional[Dict[str, Any]] = Field(None, description="Last execution result")
    estimated_resource_usage: Dict[str, Any] = Field(..., description="Estimated resource usage")


class AudienceAnalysisRequest(BaseModel):
    """Request model for audience analysis."""
    text: str = Field(..., description="Content text to analyze for audience insights")
    platform: str = Field(default="general", description="Platform type: general, linkedin, twitter")
    context: Dict[str, Any] = Field(default_factory=dict, description="Additional context")


class AudienceAnalysisResponse(BaseModel):
    """Response model for audience analysis."""
    audience_segment: Dict[str, Any] = Field(..., description="Analyzed audience segment")
    audience_persona: Dict[str, Any] = Field(..., description="Generated audience persona")
    demographic_analysis: Dict[str, Any] = Field(..., description="Demographic insights")
    behavior_analysis: Dict[str, Any] = Field(..., description="Behavioral patterns")
    psychographic_analysis: Dict[str, Any] = Field(..., description="Psychological characteristics")
    audience_insights: Dict[str, Any] = Field(..., description="Strategic audience insights")
    content_recommendations: List[str] = Field(..., description="Content strategy recommendations")
    overall_confidence: float = Field(..., description="Analysis confidence level")


class ResonanceAnalysisRequest(BaseModel):
    """Request model for content-audience resonance analysis."""
    content: str = Field(..., description="Content to analyze for resonance")
    audience_segment_data: Dict[str, Any] = Field(..., description="Target audience segment data")
    platform: str = Field(default="general", description="Platform for analysis")


class ResonanceAnalysisResponse(BaseModel):
    """Response model for resonance analysis."""
    resonance_score: float = Field(..., description="Content-audience resonance score (0.0-1.0)")
    demographic_alignment: float = Field(..., description="Demographic alignment score")
    behavioral_alignment: float = Field(..., description="Behavioral alignment score")
    psychographic_alignment: float = Field(..., description="Psychographic alignment score")
    platform_optimization: float = Field(..., description="Platform optimization score")
    improvement_suggestions: List[str] = Field(..., description="Content improvement recommendations")
    resonance_factors: List[str] = Field(..., description="Key resonance drivers")
    confidence: float = Field(..., description="Analysis confidence")


class AudienceSegmentsResponse(BaseModel):
    """Response model for audience segments retrieval."""
    segments: List[Dict[str, Any]] = Field(..., description="Available audience segments")
    total_segments: int = Field(..., description="Total number of segments")
    segment_distribution: Dict[str, int] = Field(..., description="Segment distribution by type")
    cross_segment_insights: Dict[str, Any] = Field(..., description="Cross-segment analysis")


class PersonaGenerationRequest(BaseModel):
    """Request model for persona generation."""
    content_samples: List[str] = Field(..., description="Content samples for persona generation")
    platform: str = Field(default="general", description="Platform context")
    persona_count: int = Field(default=3, description="Number of personas to generate")


class PersonaGenerationResponse(BaseModel):
    """Response model for persona generation."""
    personas: List[Dict[str, Any]] = Field(..., description="Generated audience personas")
    persona_insights: Dict[str, Any] = Field(..., description="Persona analysis insights")
    content_strategy_recommendations: List[str] = Field(..., description="Strategy recommendations")
    target_audience_summary: Dict[str, Any] = Field(..., description="Overall audience summary")


class CompetitiveAnalysisRequest(BaseModel):
    """Request model for competitive analysis."""
    competitor_data: Dict[str, List[Dict[str, Any]]] = Field(..., description="Competitor content data")
    our_strategy: Optional[Dict[str, Any]] = Field(None, description="Our current content strategy")
    analysis_scope: Optional[Dict[str, Any]] = Field(None, description="Analysis scope parameters")


class CompetitiveAnalysisResponse(BaseModel):
    """Response model for competitive analysis."""
    analysis_id: str = Field(..., description="Analysis identifier")
    market_landscape: Dict[str, Any] = Field(..., description="Market landscape overview")
    competitor_profiles: List[Dict[str, Any]] = Field(..., description="Competitor analysis profiles")
    market_gaps: List[Dict[str, Any]] = Field(..., description="Identified market gaps")
    competitive_insights: List[Dict[str, Any]] = Field(..., description="Strategic insights")
    strategic_recommendations: List[str] = Field(..., description="Strategic recommendations")
    differentiation_opportunities: List[str] = Field(..., description="Differentiation opportunities")
    competitive_benchmarks: Dict[str, float] = Field(..., description="Performance benchmarks")
    confidence_level: float = Field(..., description="Analysis confidence level")


@router.post("/audience/analyze", response_model=AudienceAnalysisResponse)
async def analyze_audience(
    request: AudienceAnalysisRequest
) -> AudienceAnalysisResponse:
    """Comprehensive audience segmentation analysis (Epic 8.1 & 8.4)."""
    try:
        logger.info(f"Epic 8.4: Analyzing audience for {request.platform} content")
        
        # Initialize audience segmentation engine
        audience_engine = AudienceSegmentationEngine()
        
        # Perform comprehensive audience analysis
        analysis_result = await audience_engine.analyze_audience(
            request.text, 
            {**request.context, "platform": request.platform}
        )
        
        # Extract key components from analysis
        audience_segment = analysis_result.get("audience_segment", {})
        audience_persona = analysis_result.get("audience_persona", {})
        demographic_analysis = analysis_result.get("demographic_analysis", {})
        behavior_analysis = analysis_result.get("behavior_analysis", {})
        psychographic_analysis = analysis_result.get("psychographic_analysis", {})
        audience_insights = analysis_result.get("audience_insights", {})
        content_recommendations = analysis_result.get("content_recommendations", [])
        overall_confidence = analysis_result.get("overall_confidence", 0.0)
        
        logger.info(f"Epic 8.4: Audience analysis complete with confidence: {overall_confidence:.2f}")
        
        return AudienceAnalysisResponse(
            audience_segment=audience_segment,
            audience_persona=audience_persona,
            demographic_analysis=demographic_analysis,
            behavior_analysis=behavior_analysis,
            psychographic_analysis=psychographic_analysis,
            audience_insights=audience_insights,
            content_recommendations=content_recommendations,
            overall_confidence=overall_confidence
        )
        
    except Exception as e:
        logger.error(f"Epic 8.4: Error in audience analysis: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Audience analysis failed: {str(e)}")


@router.post("/audience/resonance", response_model=ResonanceAnalysisResponse)
async def analyze_content_resonance(
    request: ResonanceAnalysisRequest
) -> ResonanceAnalysisResponse:
    """Content-audience resonance analysis (Epic 8.2 & 8.4)."""
    try:
        logger.info(f"Epic 8.4: Analyzing content resonance for {request.platform}")
        
        # Initialize audience segmentation engine
        audience_engine = AudienceSegmentationEngine()
        
        # Convert audience segment data to AudienceSegment object
        audience_segment = AudienceSegment(**request.audience_segment_data)
        
        # Get viral prediction if available
        viral_prediction = None
        try:
            from graph_rag.core.viral_prediction_engine import ViralPredictionEngine, Platform
            viral_engine = ViralPredictionEngine()
            
            # Map platform string to enum
            platform_map = {"linkedin": Platform.LINKEDIN, "twitter": Platform.TWITTER, "general": Platform.GENERAL}
            platform_enum = platform_map.get(request.platform.lower(), Platform.GENERAL)
            
            viral_prediction = await viral_engine.predict_viral_potential(
                request.content, platform_enum
            )
        except Exception as e:
            logger.warning(f"Could not get viral prediction: {e}")
        
        # Predict content-audience resonance
        resonance_score = await audience_engine.predict_audience_content_resonance(
            audience_segment, request.content, viral_prediction
        )
        
        # Generate detailed alignment scores
        demographic_alignment = 0.8  # Mock - would be calculated from actual analysis
        behavioral_alignment = 0.7
        psychographic_alignment = 0.6
        platform_optimization = viral_prediction.platform_optimization_score if viral_prediction else 0.7
        
        # Generate improvement suggestions
        improvement_suggestions = [
            "Adjust content tone to better match audience preferences",
            "Include more audience-specific examples and use cases",
            "Optimize content length for target audience attention span",
            "Add stronger call-to-action elements for engagement"
        ]
        
        # Identify key resonance factors
        resonance_factors = [
            "Content topic alignment with audience interests",
            "Communication style match with audience preferences",
            "Platform-appropriate formatting and structure",
            "Timing alignment with audience activity patterns"
        ]
        
        confidence = min(
            audience_segment.confidence_score,
            viral_prediction.confidence if viral_prediction else 0.8
        )
        
        logger.info(f"Epic 8.4: Resonance analysis complete - Score: {resonance_score:.2f}, Confidence: {confidence:.2f}")
        
        return ResonanceAnalysisResponse(
            resonance_score=resonance_score,
            demographic_alignment=demographic_alignment,
            behavioral_alignment=behavioral_alignment,
            psychographic_alignment=psychographic_alignment,
            platform_optimization=platform_optimization,
            improvement_suggestions=improvement_suggestions,
            resonance_factors=resonance_factors,
            confidence=confidence
        )
        
    except Exception as e:
        logger.error(f"Epic 8.4: Error in resonance analysis: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Resonance analysis failed: {str(e)}")


@router.get("/audience/segments", response_model=AudienceSegmentsResponse)
async def get_audience_segments(
    platform: Optional[str] = Query(None, description="Filter by platform"),
    min_confidence: float = Query(0.5, description="Minimum confidence threshold"),
    limit: int = Query(50, description="Maximum number of segments to return")
) -> AudienceSegmentsResponse:
    """Retrieve audience segments from analysis history (Epic 8.4)."""
    try:
        logger.info(f"Epic 8.4: Retrieving audience segments with filters: platform={platform}, min_confidence={min_confidence}")
        
        # Mock implementation - in production, this would query stored segments from database
        mock_segments = [
            {
                "id": "seg_001",
                "name": "Tech Professional Creators",
                "description": "Senior technology professionals who create thought leadership content",
                "confidence_score": 0.85,
                "platform_focus": ["linkedin"],
                "audience_size_estimate": 15000,
                "engagement_potential": 0.82
            },
            {
                "id": "seg_002", 
                "name": "Marketing Professional Commenters",
                "description": "Mid-level marketing professionals who actively engage with content",
                "confidence_score": 0.78,
                "platform_focus": ["linkedin", "twitter"],
                "audience_size_estimate": 25000,
                "engagement_potential": 0.74
            },
            {
                "id": "seg_003",
                "name": "Business Leader Lurkers",
                "description": "Executive-level professionals who consume but rarely create content",
                "confidence_score": 0.72,
                "platform_focus": ["linkedin"],
                "audience_size_estimate": 8000,
                "engagement_potential": 0.45
            }
        ]
        
        # Apply filters
        filtered_segments = []
        for segment in mock_segments:
            if segment["confidence_score"] >= min_confidence:
                if not platform or platform in segment["platform_focus"]:
                    filtered_segments.append(segment)
        
        # Limit results
        filtered_segments = filtered_segments[:limit]
        
        # Calculate distribution
        segment_distribution = {}
        for segment in filtered_segments:
            seg_type = segment["name"].split()[-1]  # Last word as type
            segment_distribution[seg_type] = segment_distribution.get(seg_type, 0) + 1
        
        # Generate cross-segment insights
        cross_segment_insights = {
            "total_audience_reach": sum(seg["audience_size_estimate"] for seg in filtered_segments),
            "average_engagement_potential": sum(seg["engagement_potential"] for seg in filtered_segments) / len(filtered_segments) if filtered_segments else 0.0,
            "platform_coverage": list(set(platform for seg in filtered_segments for platform in seg["platform_focus"])),
            "confidence_range": {
                "min": min(seg["confidence_score"] for seg in filtered_segments) if filtered_segments else 0.0,
                "max": max(seg["confidence_score"] for seg in filtered_segments) if filtered_segments else 0.0
            }
        }
        
        logger.info(f"Epic 8.4: Retrieved {len(filtered_segments)} audience segments")
        
        return AudienceSegmentsResponse(
            segments=filtered_segments,
            total_segments=len(filtered_segments),
            segment_distribution=segment_distribution,
            cross_segment_insights=cross_segment_insights
        )
        
    except Exception as e:
        logger.error(f"Epic 8.4: Error retrieving audience segments: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Segment retrieval failed: {str(e)}")


@router.post("/audience/personas", response_model=PersonaGenerationResponse)
async def generate_audience_personas(
    request: PersonaGenerationRequest
) -> PersonaGenerationResponse:
    """Generate detailed audience personas from content analysis (Epic 8.1 & 8.4)."""
    try:
        logger.info(f"Epic 8.4: Generating {request.persona_count} audience personas from {len(request.content_samples)} content samples")
        
        # Initialize audience segmentation engine
        audience_engine = AudienceSegmentationEngine()
        
        # Analyze multiple content samples to generate diverse personas
        personas = []
        segment_data = []
        
        for i, content in enumerate(request.content_samples[:request.persona_count]):
            try:
                # Analyze audience for this content sample
                analysis_result = await audience_engine.analyze_audience(
                    content, {"platform": request.platform, "sample_id": i}
                )
                
                # Extract segment and persona data
                if analysis_result.get("audience_segment") and analysis_result.get("audience_persona"):
                    personas.append(analysis_result["audience_persona"])
                    segment_data.append(analysis_result["audience_segment"])
                
            except Exception as e:
                logger.warning(f"Error analyzing content sample {i}: {e}")
                continue
        
        # Generate persona insights
        persona_insights = {
            "total_personas_generated": len(personas),
            "persona_diversity_score": 0.8 if len(personas) > 1 else 0.5,
            "common_characteristics": [],
            "unique_differentiators": [],
            "engagement_patterns": {}
        }
        
        if personas:
            # Analyze common characteristics across personas
            common_traits = []
            for persona in personas:
                if persona.get("psychographic_profile", {}).get("personality_traits"):
                    traits = list(persona["psychographic_profile"]["personality_traits"].keys())
                    common_traits.extend(traits)
            
            # Count trait frequency
            trait_counts = {}
            for trait in common_traits:
                trait_counts[trait] = trait_counts.get(trait, 0) + 1
            
            # Identify common characteristics (appear in multiple personas)
            common_characteristics = [trait for trait, count in trait_counts.items() if count > 1]
            persona_insights["common_characteristics"] = common_characteristics[:5]
            
            # Engagement patterns analysis
            persona_insights["engagement_patterns"] = {
                "high_engagement_personas": len([p for p in personas if p.get("engagement_potential", 0) > 0.7]),
                "content_creators": len([p for p in personas if p.get("behavior_profile", {}).get("interaction_style") == "creator"]),
                "professional_focus": len([p for p in personas if p.get("demographic_profile", {}).get("industry")])
            }
        
        # Generate content strategy recommendations
        content_strategy_recommendations = [
            "Create content tailored to each persona's communication style and preferences",
            "Develop platform-specific strategies based on persona platform usage patterns",
            "Align content timing with persona activity patterns for maximum engagement",
            "Use persona insights to inform content tone and messaging approach",
            "Create persona-specific calls-to-action to improve conversion rates"
        ]
        
        # Target audience summary
        target_audience_summary = {
            "primary_demographics": "Professional audience with diverse industry backgrounds",
            "key_platforms": [request.platform],
            "content_preferences": ["educational", "professional", "thought_leadership"],
            "engagement_drivers": ["industry insights", "practical advice", "authentic perspectives"],
            "optimal_content_mix": {
                "educational_content": 40,
                "industry_insights": 30,
                "personal_experiences": 20,
                "trending_topics": 10
            }
        }
        
        logger.info(f"Epic 8.4: Generated {len(personas)} personas with {persona_insights['total_personas_generated']} successful analyses")
        
        return PersonaGenerationResponse(
            personas=personas,
            persona_insights=persona_insights,
            content_strategy_recommendations=content_strategy_recommendations,
            target_audience_summary=target_audience_summary
        )
        
    except Exception as e:
        logger.error(f"Epic 8.4: Error generating personas: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Persona generation failed: {str(e)}")


@router.post("/audience/competitive", response_model=CompetitiveAnalysisResponse)
async def analyze_competitive_positioning(
    request: CompetitiveAnalysisRequest
) -> CompetitiveAnalysisResponse:
    """Comprehensive competitive analysis for market positioning (Epic 8.3 & 8.4)."""
    try:
        logger.info(f"Epic 8.4: Starting competitive analysis for {len(request.competitor_data)} competitors")
        
        # Initialize competitive analyzer
        competitive_analyzer = CompetitiveAnalyzer()
        
        # Perform comprehensive competitive analysis
        analysis_result = await competitive_analyzer.analyze_competitive_landscape(
            request.competitor_data,
            request.our_strategy,
            request.analysis_scope
        )
        
        # Convert result to response format
        # Competitor profiles
        competitor_profiles = []
        for profile in analysis_result.competitor_profiles:
            competitor_profiles.append({
                "id": profile.id,
                "name": profile.name,
                "competitor_type": profile.competitor_type.value if profile.competitor_type else None,
                "market_position": profile.market_position.value if profile.market_position else None,
                "content_strategy": profile.content_strategy.value if profile.content_strategy else None,
                "average_engagement_rate": profile.average_engagement_rate,
                "average_viral_score": profile.average_viral_score,
                "audience_overlap_score": profile.audience_overlap_score,
                "strengths": profile.strengths,
                "weaknesses": profile.weaknesses,
                "confidence_score": profile.confidence_score
            })
        
        # Market gaps
        market_gaps = []
        for gap in analysis_result.market_gaps:
            market_gaps.append({
                "id": gap.id,
                "gap_type": gap.gap_type,
                "description": gap.description,
                "opportunity_size": gap.opportunity_size,
                "difficulty_score": gap.difficulty_score,
                "success_probability": gap.success_probability,
                "target_audience": gap.target_audience,
                "content_themes": gap.content_themes,
                "estimated_timeline": gap.estimated_timeline,
                "resource_requirements": gap.resource_requirements
            })
        
        # Competitive insights
        competitive_insights = []
        for insight in analysis_result.competitive_insights:
            competitive_insights.append({
                "id": insight.id,
                "insight_type": insight.insight_type,
                "title": insight.title,
                "description": insight.description,
                "confidence": insight.confidence,
                "strategic_priority": insight.strategic_priority,
                "actionable_recommendations": insight.actionable_recommendations,
                "competitors_involved": insight.competitors_involved,
                "potential_impact": insight.potential_impact
            })
        
        logger.info(f"Epic 8.4: Competitive analysis complete - "
                   f"{len(competitor_profiles)} competitors analyzed, "
                   f"{len(market_gaps)} gaps identified, "
                   f"confidence: {analysis_result.confidence_level:.2f}")
        
        return CompetitiveAnalysisResponse(
            analysis_id=analysis_result.analysis_id,
            market_landscape=analysis_result.market_landscape,
            competitor_profiles=competitor_profiles,
            market_gaps=market_gaps,
            competitive_insights=competitive_insights,
            strategic_recommendations=analysis_result.strategic_recommendations,
            differentiation_opportunities=analysis_result.differentiation_opportunities,
            competitive_benchmarks=analysis_result.competitive_benchmarks,
            confidence_level=analysis_result.confidence_level
        )
        
    except Exception as e:
        logger.error(f"Epic 8.4: Error in competitive analysis: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Competitive analysis failed: {str(e)}")


# === EPIC 9.3: CONTENT STRATEGY API ENDPOINTS ===

@router.post("/strategies/optimize", response_model=StrategyOptimizationResponse)
async def optimize_content_strategy(
    request: StrategyOptimizationRequest,
    strategy_optimizer = Depends(get_content_strategy_optimizer)
) -> StrategyOptimizationResponse:
    """Full content strategy optimization with AI-powered recommendations (Epic 9.3)."""
    try:
        start_time = asyncio.get_event_loop().time()
        
        logger.info(f"Epic 9.3: Starting comprehensive content strategy optimization")
        
        # Parse brand profile for optimizer
        from graph_rag.core.brand_safety_analyzer import BrandProfile
        brand_profile_enum = BrandProfile.MODERATE
        try:
            brand_profile_enum = BrandProfile(request.brand_profile.lower())
        except ValueError:
            pass
        
        # Create strategy optimizer with brand profile
        from graph_rag.core.content_strategy_optimizer import ContentStrategyOptimizer
        optimizer = ContentStrategyOptimizer(brand_profile_enum)
        
        # Generate comprehensive strategy
        strategy = await optimizer.generate_comprehensive_strategy(
            business_context=request.business_context,
            content_samples=request.content_samples,
            competitive_analysis=request.competitive_analysis,
            historical_performance=request.historical_performance
        )
        
        # Convert strategy to response format
        strategy_dict = {
            "id": strategy.id,
            "title": strategy.title,
            "description": strategy.description,
            "primary_objective": strategy.primary_objective.value,
            "secondary_objectives": [obj.value for obj in strategy.secondary_objectives],
            "competitive_position": strategy.competitive_position.value,
            "target_platforms": [platform.value for platform in strategy.target_platforms],
            "content_themes": strategy.content_themes,
            "messaging_framework": strategy.messaging_framework,
            "identified_gaps_count": len(strategy.identified_gaps),
            "resource_plan": {
                "total_hours_per_week": strategy.resource_plan.total_hours_per_week,
                "total_monthly_budget": strategy.resource_plan.total_monthly_budget,
                "implementation_weeks": strategy.resource_plan.implementation_weeks
            },
            "implementation_phases": strategy.implementation_phases,
            "success_metrics": strategy.success_metrics
        }
        
        # Generate optimization summary
        optimization_summary = {
            "optimization_time_ms": (asyncio.get_event_loop().time() - start_time) * 1000,
            "content_samples_analyzed": len(request.content_samples),
            "gaps_identified": len(strategy.identified_gaps),
            "high_priority_gaps": len([g for g in strategy.identified_gaps if g.strategic_priority in ["critical", "high"]]),
            "optimization_goals_addressed": len(request.optimization_goals),
            "business_context_factors": len(request.business_context.keys())
        }
        
        # Confidence metrics
        confidence_metrics = {
            "overall_confidence": strategy.recommendation_confidence,
            "data_quality": strategy.data_quality_score,
            "strategic_coherence": strategy.strategic_coherence_score,
            "belief_alignment": strategy.belief_alignment_score,
            "brand_safety": strategy.brand_safety_score,
            "audience_resonance": strategy.audience_resonance_score,
            "viral_potential": strategy.viral_potential_score
        }
        
        # Implementation timeline
        implementation_timeline = {
            "total_duration_weeks": 12,
            "milestones_count": len(strategy.content_calendar.milestones),
            "performance_reviews": len(strategy.content_calendar.performance_review_dates),
            "optimization_checkpoints": len(strategy.content_calendar.optimization_checkpoints),
            "start_date": strategy.content_calendar.start_date.isoformat(),
            "end_date": strategy.content_calendar.end_date.isoformat()
        }
        
        # Resource requirements
        resource_requirements = {
            "personnel": {
                "content_creators": strategy.resource_plan.content_creators,
                "designers": strategy.resource_plan.designers,
                "community_managers": strategy.resource_plan.community_managers,
                "analysts": strategy.resource_plan.analysts
            },
            "budget_breakdown": {
                "content": strategy.resource_plan.content_budget,
                "design": strategy.resource_plan.design_budget,
                "promotion": strategy.resource_plan.promotion_budget,
                "tools": strategy.resource_plan.tools_budget
            },
            "time_allocation": {
                "content_creation": strategy.resource_plan.content_creation_hours,
                "design": strategy.resource_plan.design_hours,
                "community_management": strategy.resource_plan.community_management_hours,
                "analysis": strategy.resource_plan.analysis_hours
            }
        }
        
        # Performance predictions
        performance_predictions = {
            "reach": {
                "min": strategy.performance_prediction.predicted_reach[0],
                "expected": strategy.performance_prediction.predicted_reach[1],
                "max": strategy.performance_prediction.predicted_reach[2]
            },
            "engagement_rate": {
                "min": strategy.performance_prediction.predicted_engagement_rate[0],
                "expected": strategy.performance_prediction.predicted_engagement_rate[1],
                "max": strategy.performance_prediction.predicted_engagement_rate[2]
            },
            "roi": {
                "min": strategy.performance_prediction.roi_percentage[0],
                "expected": strategy.performance_prediction.roi_percentage[1],
                "max": strategy.performance_prediction.roi_percentage[2]
            },
            "leads": {
                "min": strategy.performance_prediction.estimated_leads[0],
                "expected": strategy.performance_prediction.estimated_leads[1],
                "max": strategy.performance_prediction.estimated_leads[2]
            },
            "prediction_confidence": strategy.performance_prediction.prediction_confidence
        }
        
        # Next steps
        next_steps = [
            "Review and approve the strategic recommendation",
            "Allocate resources according to the resource plan",
            "Begin implementation with Phase 1: Strategy Setup",
            "Set up performance monitoring and KPI tracking",
            "Schedule first performance review for week 4"
        ]
        
        if len(strategy.identified_gaps) > 0:
            next_steps.insert(2, f"Prioritize top {min(3, len(strategy.identified_gaps))} content gaps for immediate execution")
        
        logger.info(f"Epic 9.3: Strategy optimization completed in {optimization_summary['optimization_time_ms']:.2f}ms with {confidence_metrics['overall_confidence']:.2f} confidence")
        
        return StrategyOptimizationResponse(
            strategy_id=strategy.id,
            strategy=strategy_dict,
            optimization_summary=optimization_summary,
            confidence_metrics=confidence_metrics,
            implementation_timeline=implementation_timeline,
            resource_requirements=resource_requirements,
            performance_predictions=performance_predictions,
            next_steps=next_steps
        )
        
    except Exception as e:
        logger.error(f"Epic 9.3: Error optimizing content strategy: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Content strategy optimization failed: {str(e)}")


@router.post("/strategies/analyze", response_model=StrategyAnalysisResponse)
async def analyze_content_strategy(
    request: StrategyAnalysisRequest,
    strategy_optimizer = Depends(get_content_strategy_optimizer),
    audience_engine = Depends(get_audience_segmentation_engine)
) -> StrategyAnalysisResponse:
    """Content strategy analysis without full optimization (Epic 9.3)."""
    try:
        start_time = asyncio.get_event_loop().time()
        
        logger.info(f"Epic 9.3: Analyzing content strategy for {len(request.existing_content)} content items")
        
        # Analyze target audience
        audience_analysis = await audience_engine.analyze_audience(
            request.target_audience, {"platform": request.platform}
        )
        
        # Create audience segment from analysis
        from graph_rag.core.audience_intelligence import AudienceSegment
        audience_segment = AudienceSegment(**audience_analysis["audience_segment"])
        
        # Perform content gap analysis
        from graph_rag.core.content_strategy_optimizer import ContentGapAnalyzer
        gap_analyzer = ContentGapAnalyzer()
        
        content_gaps = await gap_analyzer.identify_content_gaps(
            target_audiences=[audience_segment],
            existing_content=request.existing_content
        )
        
        # Convert content gaps to response format
        gaps_data = []
        for gap in content_gaps[:10]:  # Top 10 gaps
            gap_dict = {
                "id": gap.id,
                "title": gap.title,
                "description": gap.description,
                "opportunity_score": gap.opportunity_score,
                "strategic_priority": gap.strategic_priority,
                "estimated_reach": gap.estimated_reach,
                "viral_potential": gap.viral_potential,
                "execution_difficulty": gap.execution_difficulty,
                "suggested_angles": gap.suggested_angles[:3],  # Top 3 angles
                "recommended_formats": [fmt.value for fmt in gap.recommended_content_formats]
            }
            gaps_data.append(gap_dict)
        
        # Audience insights
        audience_insights = {
            "segment_id": audience_segment.id,
            "segment_name": audience_segment.name,
            "size_estimate": audience_segment.size_estimate,
            "confidence_score": audience_segment.confidence_score,
            "preferred_platforms": [p.value for p in audience_segment.preferred_platforms],
            "engagement_potential": audience_analysis.get("overall_confidence", 0.7),
            "key_interests": list(audience_segment.psychographic_profile.interests.keys())[:5]
        }
        
        # Competitive position analysis (simplified)
        competitive_position = {
            "current_position": "follower",  # Default
            "market_saturation": 0.6,  # Mock
            "differentiation_opportunities": [
                "Focus on unique value proposition in content",
                "Leverage audience-specific insights for better targeting",
                "Develop thought leadership in underserved topics"
            ],
            "competitive_advantages": [
                gap.title for gap in content_gaps[:3] if gap.opportunity_score > 0.7
            ]
        }
        
        # Strategic recommendations based on analysis
        strategic_recommendations = [
            f"Focus on {len([g for g in content_gaps if g.strategic_priority in ['critical', 'high']])} high-priority content gaps",
            f"Develop content themes around {', '.join(audience_segment.psychographic_profile.interests.keys())}",
            f"Optimize for {request.platform} platform based on audience preferences",
            "Implement regular content gap analysis to identify new opportunities",
            "Create content calendar based on identified gaps and audience behavior"
        ]
        
        # Opportunity prioritization
        opportunity_prioritization = []
        for i, gap in enumerate(sorted(content_gaps, key=lambda g: g.opportunity_score, reverse=True)[:5]):
            opportunity = {
                "rank": i + 1,
                "gap_id": gap.id,
                "title": gap.title,
                "opportunity_score": gap.opportunity_score,
                "strategic_priority": gap.strategic_priority,
                "estimated_impact": gap.business_impact,
                "implementation_effort": gap.execution_difficulty,
                "recommendation": gap.suggested_angles[0] if gap.suggested_angles else "Develop content addressing this gap"
            }
            opportunity_prioritization.append(opportunity)
        
        # Calculate analysis confidence
        confidence_factors = [
            audience_analysis.get("overall_confidence", 0.7),
            min(1.0, len(content_gaps) / 5.0),  # Gap analysis completeness
            min(1.0, len(request.existing_content) / 10.0),  # Content sample size
            0.8 if request.analysis_depth == "comprehensive" else 0.6  # Analysis depth
        ]
        analysis_confidence = sum(confidence_factors) / len(confidence_factors)
        
        analysis_time = (asyncio.get_event_loop().time() - start_time) * 1000
        
        logger.info(f"Epic 9.3: Strategy analysis completed in {analysis_time:.2f}ms - {len(content_gaps)} gaps identified")
        
        return StrategyAnalysisResponse(
            analysis_id=f"analysis_{int(start_time)}",
            content_gaps=gaps_data,
            audience_insights=audience_insights,
            competitive_position=competitive_position,
            strategic_recommendations=strategic_recommendations,
            opportunity_prioritization=opportunity_prioritization,
            analysis_confidence=analysis_confidence
        )
        
    except Exception as e:
        logger.error(f"Epic 9.3: Error analyzing content strategy: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Content strategy analysis failed: {str(e)}")


@router.get("/strategies/{strategy_id}")
async def get_strategy_details(strategy_id: str) -> Dict[str, Any]:
    """Get strategy details by ID (Epic 9.3)."""
    try:
        logger.info(f"Epic 9.3: Retrieving strategy details for {strategy_id}")
        
        # Mock implementation - in production would query database
        strategy_details = {
            "strategy_id": strategy_id,
            "title": "AI-Powered Content Strategy",
            "description": "Comprehensive content strategy optimized for engagement and growth",
            "status": "active",
            "created_at": datetime.utcnow().isoformat(),
            "last_updated": datetime.utcnow().isoformat(),
            "performance_summary": {
                "current_reach": 15000,
                "engagement_rate": 0.045,
                "content_published": 24,
                "goals_achieved": 3
            },
            "next_milestones": [
                {
                    "title": "Week 8 Performance Review",
                    "target_date": (datetime.utcnow() + timedelta(weeks=2)).isoformat(),
                    "status": "upcoming"
                }
            ],
            "optimization_opportunities": [
                "Increase video content production",
                "Expand into trending topics",
                "Improve call-to-action effectiveness"
            ]
        }
        
        return strategy_details
        
    except Exception as e:
        logger.error(f"Epic 9.3: Error retrieving strategy details: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Strategy retrieval failed: {str(e)}")


@router.put("/strategies/{strategy_id}")
async def update_strategy(
    strategy_id: str,
    updates: Dict[str, Any],
    strategy_optimizer = Depends(get_content_strategy_optimizer)
) -> Dict[str, Any]:
    """Update strategy configuration (Epic 9.3)."""
    try:
        logger.info(f"Epic 9.3: Updating strategy {strategy_id} with {len(updates)} changes")
        
        # Mock implementation - in production would update database
        updated_strategy = {
            "strategy_id": strategy_id,
            "update_summary": {
                "fields_updated": list(updates.keys()),
                "update_count": len(updates),
                "last_updated": datetime.utcnow().isoformat(),
                "version": "1.1"
            },
            "validation_results": {
                "valid_updates": len(updates),
                "invalid_updates": 0,
                "warnings": []
            },
            "impact_assessment": {
                "performance_impact": "minimal",
                "resource_impact": "none",
                "timeline_impact": "none"
            },
            "next_actions": [
                "Changes will take effect immediately",
                "Monitor performance for next 2 weeks",
                "Review impact at next milestone"
            ]
        }
        
        logger.info(f"Epic 9.3: Strategy {strategy_id} updated successfully")
        return updated_strategy
        
    except Exception as e:
        logger.error(f"Epic 9.3: Error updating strategy: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Strategy update failed: {str(e)}")


@router.delete("/strategies/{strategy_id}")
async def delete_strategy(strategy_id: str) -> Dict[str, Any]:
    """Delete strategy (Epic 9.3)."""
    try:
        logger.info(f"Epic 9.3: Deleting strategy {strategy_id}")
        
        # Mock implementation - in production would delete from database
        deletion_result = {
            "strategy_id": strategy_id,
            "deletion_status": "success",
            "deleted_at": datetime.utcnow().isoformat(),
            "cleanup_summary": {
                "content_calendar_archived": True,
                "performance_data_retained": True,
                "resource_plans_archived": True,
                "workflows_stopped": True
            },
            "backup_location": f"archive/strategies/{strategy_id}",
            "recovery_period_days": 30
        }
        
        logger.info(f"Epic 9.3: Strategy {strategy_id} deleted successfully")
        return deletion_result
        
    except Exception as e:
        logger.error(f"Epic 9.3: Error deleting strategy: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Strategy deletion failed: {str(e)}")


@router.get("/strategies")
async def list_strategies(
    status: Optional[str] = Query(None, description="Filter by status"),
    limit: int = Query(20, description="Maximum number of strategies to return"),
    offset: int = Query(0, description="Number of strategies to skip")
) -> Dict[str, Any]:
    """List all content strategies (Epic 9.3)."""
    try:
        logger.info(f"Epic 9.3: Listing strategies with status={status}, limit={limit}")
        
        # Mock implementation - in production would query database
        mock_strategies = [
            {
                "strategy_id": f"strategy_{i}",
                "title": f"Content Strategy {i+1}",
                "status": "active" if i % 2 == 0 else "draft",
                "created_at": (datetime.utcnow() - timedelta(days=i*7)).isoformat(),
                "performance_score": 0.7 + (i * 0.05),
                "content_count": 15 + i * 3,
                "engagement_rate": 0.035 + (i * 0.005)
            }
            for i in range(10)
        ]
        
        # Apply status filter
        if status:
            mock_strategies = [s for s in mock_strategies if s["status"] == status]
        
        # Apply pagination
        paginated_strategies = mock_strategies[offset:offset + limit]
        
        response = {
            "strategies": paginated_strategies,
            "total_count": len(mock_strategies),
            "limit": limit,
            "offset": offset,
            "has_more": offset + limit < len(mock_strategies),
            "summary": {
                "active_strategies": len([s for s in mock_strategies if s["status"] == "active"]),
                "draft_strategies": len([s for s in mock_strategies if s["status"] == "draft"]),
                "average_performance": sum(s["performance_score"] for s in mock_strategies) / len(mock_strategies) if mock_strategies else 0
            }
        }
        
        logger.info(f"Epic 9.3: Retrieved {len(paginated_strategies)} strategies")
        return response
        
    except Exception as e:
        logger.error(f"Epic 9.3: Error listing strategies: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Strategy listing failed: {str(e)}")


# === CONTENT OPTIMIZATION ENDPOINTS ===

@router.post("/content/optimize", response_model=ContentOptimizationResponse)
async def optimize_content(
    request: ContentOptimizationRequest,
    optimization_engine = Depends(get_content_optimization_engine),
    viral_engine = Depends(get_viral_prediction_engine),
    brand_safety = Depends(get_brand_safety_analyzer)
) -> ContentOptimizationResponse:
    """Optimize individual content pieces (Epic 9.3)."""
    try:
        start_time = asyncio.get_event_loop().time()
        
        logger.info(f"Epic 9.3: Optimizing content for {request.platform} platform")
        
        # Parse platform enum
        from graph_rag.core.viral_prediction_engine import Platform
        platform_map = {"linkedin": Platform.LINKEDIN, "twitter": Platform.TWITTER, "general": Platform.GENERAL}
        platform_enum = platform_map.get(request.platform.lower(), Platform.GENERAL)
        
        # Generate optimization ID
        optimization_id = f"opt_{hash(request.content[:100])}_{int(start_time)}"
        
        # Get baseline viral prediction
        baseline_prediction = await viral_engine.predict_viral_potential(request.content, platform_enum)
        
        # Get baseline brand safety assessment
        baseline_safety = await brand_safety.assess_brand_safety(request.content, platform_enum, optimization_id)
        
        # Mock content optimization (in production, would use actual optimization engine)
        optimized_content = f"{request.content.strip()}\n\n✨ Optimized for better engagement and clarity."
        
        # Quality metrics assessment
        quality_metrics = {
            "readability_score": 0.75,
            "engagement_potential": baseline_prediction.engagement_score + 0.1,
            "brand_alignment": 1.0 - baseline_safety.risk_score.overall,
            "viral_potential": baseline_prediction.overall_viral_score + 0.05,
            "safety_score": 1.0 - baseline_safety.risk_score.overall,
            "clarity_score": 0.8,
            "actionability_score": 0.7
        }
        
        # Improvement suggestions
        improvement_suggestions = [
            {
                "category": "engagement",
                "priority": "high",
                "suggestion": "Add stronger call-to-action elements",
                "expected_impact": 0.15,
                "implementation_effort": "low"
            },
            {
                "category": "structure",
                "priority": "medium", 
                "suggestion": "Improve content structure with better headings",
                "expected_impact": 0.1,
                "implementation_effort": "medium"
            },
            {
                "category": "platform_specific",
                "priority": "medium",
                "suggestion": f"Optimize formatting for {request.platform} platform",
                "expected_impact": 0.12,
                "implementation_effort": "low"
            }
        ]
        
        # Predicted improvements
        predicted_improvements = {
            "engagement_increase": 0.15,
            "reach_increase": 0.12,
            "click_rate_increase": 0.08,
            "overall_performance_lift": 0.18,
            "confidence": 0.75
        }
        
        optimization_time = (asyncio.get_event_loop().time() - start_time) * 1000
        optimization_confidence = min(1.0, baseline_prediction.confidence + 0.1)
        
        logger.info(f"Epic 9.3: Content optimization completed in {optimization_time:.2f}ms with {optimization_confidence:.2f} confidence")
        
        return ContentOptimizationResponse(
            optimization_id=optimization_id,
            original_content=request.content,
            optimized_content=optimized_content,
            improvement_suggestions=improvement_suggestions,
            quality_metrics=quality_metrics,
            predicted_improvements=predicted_improvements,
            optimization_confidence=optimization_confidence,
            implementation_priority="high" if sum(quality_metrics.values()) / len(quality_metrics) < 0.7 else "medium"
        )
        
    except Exception as e:
        logger.error(f"Epic 9.3: Error optimizing content: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Content optimization failed: {str(e)}")


@router.post("/content/analyze", response_model=ContentAnalysisResponse)
async def analyze_content_quality(
    request: ContentAnalysisRequest,
    viral_engine = Depends(get_viral_prediction_engine),
    brand_safety = Depends(get_brand_safety_analyzer)
) -> ContentAnalysisResponse:
    """Analyze content quality and potential (Epic 9.3)."""
    try:
        start_time = asyncio.get_event_loop().time()
        
        logger.info(f"Epic 9.3: Analyzing content quality for {len(request.content)} characters")
        
        analysis_id = f"analysis_{hash(request.content[:100])}_{int(start_time)}"
        
        # Content summary
        content_summary = {
            "character_count": len(request.content),
            "word_count": len(request.content.split()),
            "sentence_count": len([s for s in request.content.split('.') if s.strip()]),
            "paragraph_count": len([p for p in request.content.split('\n\n') if p.strip()]),
            "estimated_reading_time_minutes": len(request.content.split()) / 200,  # Average reading speed
            "content_type": "text_post"  # Simplified detection
        }
        
        # Get viral prediction for quality assessment
        from graph_rag.core.viral_prediction_engine import Platform
        viral_prediction = await viral_engine.predict_viral_potential(request.content, Platform.GENERAL)
        
        # Get brand safety assessment
        safety_assessment = await brand_safety.assess_brand_safety(request.content, Platform.GENERAL, analysis_id)
        
        # Multi-dimensional quality scores
        quality_assessment = {
            "readability": 0.75,  # Mock score
            "engagement_potential": viral_prediction.engagement_score,
            "brand_alignment": 1.0 - safety_assessment.risk_score.overall,
            "audience_relevance": 0.7,  # Mock score
            "viral_potential": viral_prediction.overall_viral_score,
            "safety_score": 1.0 - safety_assessment.risk_score.overall,
            "originality": 0.8,  # Mock score
            "clarity": 0.75,  # Mock score
            "emotional_impact": viral_prediction.emotional_impact if hasattr(viral_prediction, 'emotional_impact') else 0.6,
            "actionability": 0.65  # Mock score
        }
        
        # Identify strengths
        strengths = []
        if quality_assessment["viral_potential"] > 0.7:
            strengths.append("High viral potential with strong engagement drivers")
        if quality_assessment["brand_alignment"] > 0.8:
            strengths.append("Excellent brand safety and alignment")
        if quality_assessment["clarity"] > 0.7:
            strengths.append("Clear and well-structured content")
        if content_summary["word_count"] > 100 and content_summary["word_count"] < 300:
            strengths.append("Optimal length for social media engagement")
        
        # Identify weaknesses
        weaknesses = []
        if quality_assessment["engagement_potential"] < 0.5:
            weaknesses.append("Low engagement potential - needs stronger hooks")
        if quality_assessment["actionability"] < 0.6:
            weaknesses.append("Lacks clear call-to-action elements")
        if quality_assessment["emotional_impact"] < 0.5:
            weaknesses.append("Limited emotional resonance with audience")
        if content_summary["sentence_count"] < 3:
            weaknesses.append("Too brief for comprehensive value delivery")
        
        # Benchmark comparison (if provided)
        benchmark_comparison = None
        if request.benchmark_content:
            benchmark_scores = []
            for benchmark in request.benchmark_content[:3]:  # Compare with top 3
                benchmark_prediction = await viral_engine.predict_viral_potential(benchmark, Platform.GENERAL)
                benchmark_scores.append(benchmark_prediction.overall_viral_score)
            
            avg_benchmark_score = sum(benchmark_scores) / len(benchmark_scores) if benchmark_scores else 0.5
            benchmark_comparison = {
                "vs_benchmark_performance": quality_assessment["viral_potential"] / avg_benchmark_score if avg_benchmark_score > 0 else 1.0,
                "benchmark_count": len(request.benchmark_content),
                "relative_ranking": "above_average" if quality_assessment["viral_potential"] > avg_benchmark_score else "below_average"
            }
        
        # Improvement recommendations
        recommendations = []
        if quality_assessment["engagement_potential"] < 0.6:
            recommendations.append("Add compelling hooks and questions to increase engagement")
        if quality_assessment["actionability"] < 0.7:
            recommendations.append("Include clear and specific call-to-action elements")
        if quality_assessment["emotional_impact"] < 0.6:
            recommendations.append("Incorporate storytelling elements to enhance emotional connection")
        if content_summary["word_count"] < 50:
            recommendations.append("Expand content to provide more comprehensive value")
        
        # Calculate overall analysis confidence
        analysis_confidence = min(1.0, (
            viral_prediction.confidence * 0.4 +
            safety_assessment.confidence * 0.3 +
            (len(request.content) / 500.0) * 0.3  # Content length factor
        ))
        
        analysis_time = (asyncio.get_event_loop().time() - start_time) * 1000
        
        logger.info(f"Epic 9.3: Content analysis completed in {analysis_time:.2f}ms - Overall quality: {sum(quality_assessment.values()) / len(quality_assessment):.2f}")
        
        return ContentAnalysisResponse(
            analysis_id=analysis_id,
            content_summary=content_summary,
            quality_assessment=quality_assessment,
            strengths=strengths,
            weaknesses=weaknesses,
            benchmark_comparison=benchmark_comparison,
            recommendations=recommendations,
            analysis_confidence=analysis_confidence
        )
        
    except Exception as e:
        logger.error(f"Epic 9.3: Error analyzing content: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Content analysis failed: {str(e)}")


@router.post("/content/variations", response_model=ContentVariationsResponse)
async def generate_content_variations(
    request: ContentVariationsRequest,
    viral_engine = Depends(get_viral_prediction_engine)
) -> ContentVariationsResponse:
    """Generate A/B testing content variations (Epic 9.3)."""
    try:
        start_time = asyncio.get_event_loop().time()
        
        logger.info(f"Epic 9.3: Generating {request.variation_count} content variations")
        
        # Parse platform enum
        from graph_rag.core.viral_prediction_engine import Platform
        platform_map = {"linkedin": Platform.LINKEDIN, "twitter": Platform.TWITTER, "general": Platform.GENERAL}
        platform_enum = platform_map.get(request.platform.lower(), Platform.GENERAL)
        
        # Get baseline prediction for original content
        baseline_prediction = await viral_engine.predict_viral_potential(request.original_content, platform_enum)
        
        # Generate variations (mock implementation)
        variations = []
        variation_goals_map = {
            "higher_engagement": "📈 Engagement-Optimized Version",
            "different_tone": "🎭 Tone-Adjusted Version", 
            "shorter_format": "⚡ Concise Version",
            "more_professional": "👔 Professional Version",
            "more_casual": "😊 Casual Version"
        }
        
        for i in range(request.variation_count):
            # Mock variation generation
            goal = request.variation_goals[i % len(request.variation_goals)] if request.variation_goals else "higher_engagement"
            goal_prefix = variation_goals_map.get(goal, "✨ Optimized Version")
            
            variation_content = f"{goal_prefix}:\n\n{request.original_content}"
            
            # Add variation-specific modifications
            if "engagement" in goal:
                variation_content += "\n\nWhat are your thoughts? 💭"
            elif "tone" in goal:
                variation_content += "\n\n#ThoughtLeadership #Innovation"
            elif "shorter" in goal:
                variation_content = request.original_content[:100] + "..." if len(request.original_content) > 100 else request.original_content
            
            # Predict performance for variation
            variation_prediction = await viral_engine.predict_viral_potential(variation_content, platform_enum)
            
            variation_data = {
                "variation_id": f"var_{i+1}",
                "content": variation_content,
                "goal": goal,
                "predicted_performance": {
                    "viral_score": variation_prediction.overall_viral_score,
                    "engagement_score": variation_prediction.engagement_score,
                    "reach_potential": variation_prediction.reach_potential
                },
                "differences_from_original": [
                    f"Modified for {goal.replace('_', ' ')}",
                    f"{'Shorter' if len(variation_content) < len(request.original_content) else 'Enhanced'} format",
                    "Platform-optimized elements added"
                ],
                "confidence": variation_prediction.confidence
            }
            variations.append(variation_data)
        
        # Variation analysis
        variation_analysis = {
            "total_variations": len(variations),
            "best_predicted_performer": max(variations, key=lambda v: v["predicted_performance"]["viral_score"])["variation_id"],
            "variation_score_range": {
                "min": min(v["predicted_performance"]["viral_score"] for v in variations),
                "max": max(v["predicted_performance"]["viral_score"] for v in variations),
                "average": sum(v["predicted_performance"]["viral_score"] for v in variations) / len(variations)
            },
            "original_vs_variations": {
                "original_score": baseline_prediction.overall_viral_score,
                "best_variation_improvement": max(v["predicted_performance"]["viral_score"] for v in variations) - baseline_prediction.overall_viral_score,
                "variations_outperforming_original": len([v for v in variations if v["predicted_performance"]["viral_score"] > baseline_prediction.overall_viral_score])
            }
        }
        
        # Testing recommendations
        testing_recommendations = [
            "Run A/B test with 50/50 traffic split between original and best variation",
            "Test for minimum 1 week to gather statistically significant data",
            "Monitor engagement rate, click-through rate, and conversion metrics",
            "Consider audience segmentation for more targeted testing",
            f"Start with top {min(2, len(variations))} performing variations to reduce complexity"
        ]
        
        # Predicted performance summary
        predicted_performance = {
            "original_baseline": {
                "viral_score": baseline_prediction.overall_viral_score,
                "engagement_score": baseline_prediction.engagement_score,
                "reach_potential": baseline_prediction.reach_potential
            },
            "variation_performance": [
                {
                    "variation_id": v["variation_id"],
                    "expected_lift": v["predicted_performance"]["viral_score"] - baseline_prediction.overall_viral_score,
                    "confidence": v["confidence"]
                }
                for v in variations
            ],
            "recommended_test_duration_days": 7,
            "minimum_sample_size": 1000
        }
        
        generation_time = (asyncio.get_event_loop().time() - start_time) * 1000
        
        logger.info(f"Epic 9.3: Generated {len(variations)} variations in {generation_time:.2f}ms")
        
        return ContentVariationsResponse(
            original_content=request.original_content,
            variations=variations,
            variation_analysis=variation_analysis,
            testing_recommendations=testing_recommendations,
            predicted_performance=predicted_performance
        )
        
    except Exception as e:
        logger.error(f"Epic 9.3: Error generating content variations: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Content variation generation failed: {str(e)}")


@router.post("/content/predict-performance", response_model=PerformancePredictionResponse)
async def predict_content_performance(
    request: PerformancePredictionRequest,
    viral_engine = Depends(get_viral_prediction_engine),
    audience_engine = Depends(get_audience_segmentation_engine)
) -> PerformancePredictionResponse:
    """Predict content performance with confidence intervals (Epic 9.3)."""
    try:
        start_time = asyncio.get_event_loop().time()
        
        logger.info(f"Epic 9.3: Predicting performance for {request.platform} content")
        
        # Parse platform enum
        from graph_rag.core.viral_prediction_engine import Platform
        platform_map = {"linkedin": Platform.LINKEDIN, "twitter": Platform.TWITTER, "general": Platform.GENERAL}
        platform_enum = platform_map.get(request.platform.lower(), Platform.GENERAL)
        
        content_id = f"perf_{hash(request.content[:100])}_{int(start_time)}"
        
        # Get viral prediction
        viral_prediction = await viral_engine.predict_viral_potential(
            request.content, platform_enum, content_id, request.publishing_context
        )
        
        # Analyze audience if provided
        audience_resonance = 0.7  # Default
        if request.audience_data:
            # Mock audience analysis - in production would use actual audience data
            audience_resonance = request.audience_data.get("resonance_score", 0.7)
        
        # Historical context adjustment
        historical_multiplier = 1.0
        if request.historical_context:
            # Adjust predictions based on historical performance
            historical_avg = request.historical_context.get("average_performance", 0.5)
            historical_multiplier = 1.0 + (historical_avg - 0.5) * 0.5  # -25% to +25% adjustment
        
        # Detailed performance forecast
        base_reach = int(viral_prediction.reach_potential * 10000 * historical_multiplier)
        base_engagement = viral_prediction.engagement_score * historical_multiplier * audience_resonance
        
        performance_forecast = {
            "reach_prediction": {
                "min": int(base_reach * 0.7),
                "expected": base_reach,
                "max": int(base_reach * 1.5)
            },
            "engagement_metrics": {
                "engagement_rate": {
                    "min": base_engagement * 0.6,
                    "expected": base_engagement,
                    "max": base_engagement * 1.8
                },
                "likes": {
                    "min": int(base_reach * base_engagement * 0.8),
                    "expected": int(base_reach * base_engagement),
                    "max": int(base_reach * base_engagement * 1.5)
                },
                "shares": {
                    "min": int(base_reach * base_engagement * 0.1),
                    "expected": int(base_reach * base_engagement * 0.15),
                    "max": int(base_reach * base_engagement * 0.25)
                },
                "comments": {
                    "min": int(base_reach * base_engagement * 0.05),
                    "expected": int(base_reach * base_engagement * 0.08),
                    "max": int(base_reach * base_engagement * 0.15)
                }
            },
            "timing_insights": {
                "optimal_posting_time": viral_prediction.optimal_posting_time.isoformat() if viral_prediction.optimal_posting_time else None,
                "peak_engagement_window_hours": 4,
                "viral_probability": viral_prediction.viral_velocity
            },
            "platform_specific": {
                "platform_optimization_score": viral_prediction.platform_optimization_score,
                "algorithm_compatibility": 0.75,  # Mock score
                "trending_potential": viral_prediction.viral_velocity
            }
        }
        
        # Confidence intervals for key metrics
        confidence_intervals = {
            "reach": (performance_forecast["reach_prediction"]["min"], 
                     performance_forecast["reach_prediction"]["expected"], 
                     performance_forecast["reach_prediction"]["max"]),
            "engagement_rate": (performance_forecast["engagement_metrics"]["engagement_rate"]["min"],
                               performance_forecast["engagement_metrics"]["engagement_rate"]["expected"],
                               performance_forecast["engagement_metrics"]["engagement_rate"]["max"]),
            "viral_score": (viral_prediction.overall_viral_score * 0.8,
                           viral_prediction.overall_viral_score,
                           viral_prediction.overall_viral_score * 1.2),
            "conversion_rate": (0.001, 0.005, 0.02)  # Mock conversion predictions
        }
        
        # Key performance drivers
        key_performance_drivers = viral_prediction.key_features[:5] if viral_prediction.key_features else [
            "Content topic relevance",
            "Posting time optimization",
            "Audience engagement potential",
            "Platform algorithm compatibility",
            "Content format effectiveness"
        ]
        
        # Risk factors
        risk_factors = [
            "Algorithm changes could impact reach",
            "Audience fatigue with similar content",
            "Competitive content may overshadow",
            "Platform-specific feature changes",
            "Seasonal engagement variations"
        ]
        
        # Optimization suggestions
        optimization_suggestions = viral_prediction.improvement_suggestions[:5] if viral_prediction.improvement_suggestions else [
            "Add stronger call-to-action elements",
            "Include trending hashtags or keywords",
            "Optimize content length for platform",
            "Enhance visual elements if possible",
            "Time publication for peak audience activity"
        ]
        
        # Calculate prediction confidence
        confidence_factors = [
            viral_prediction.confidence,
            audience_resonance,
            1.0 if request.historical_context else 0.7,
            0.9 if request.publishing_context else 0.8
        ]
        prediction_confidence = sum(confidence_factors) / len(confidence_factors)
        
        prediction_time = (asyncio.get_event_loop().time() - start_time) * 1000
        
        logger.info(f"Epic 9.3: Performance prediction completed in {prediction_time:.2f}ms - Expected reach: {base_reach}, Confidence: {prediction_confidence:.2f}")
        
        return PerformancePredictionResponse(
            content_id=content_id,
            performance_forecast=performance_forecast,
            confidence_intervals=confidence_intervals,
            key_performance_drivers=key_performance_drivers,
            risk_factors=risk_factors,
            optimization_suggestions=optimization_suggestions,
            prediction_confidence=prediction_confidence
        )
        
    except Exception as e:
        logger.error(f"Epic 9.3: Error predicting content performance: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Performance prediction failed: {str(e)}")


@router.get("/content/optimization-history/{content_id}")
async def get_content_optimization_history(content_id: str) -> Dict[str, Any]:
    """Get optimization history for specific content (Epic 9.3)."""
    try:
        logger.info(f"Epic 9.3: Retrieving optimization history for content {content_id}")
        
        # Mock implementation - in production would query database
        optimization_history = {
            "content_id": content_id,
            "total_optimizations": 3,
            "optimization_timeline": [
                {
                    "optimization_id": "opt_001",
                    "timestamp": (datetime.utcnow() - timedelta(days=7)).isoformat(),
                    "optimization_type": "engagement",
                    "changes_made": ["Added call-to-action", "Improved headline"],
                    "performance_impact": {
                        "engagement_increase": 0.15,
                        "reach_increase": 0.08
                    },
                    "status": "applied"
                },
                {
                    "optimization_id": "opt_002", 
                    "timestamp": (datetime.utcnow() - timedelta(days=3)).isoformat(),
                    "optimization_type": "platform_specific",
                    "changes_made": ["LinkedIn formatting", "Added hashtags"],
                    "performance_impact": {
                        "platform_score_increase": 0.12,
                        "reach_increase": 0.05
                    },
                    "status": "applied"
                },
                {
                    "optimization_id": "opt_003",
                    "timestamp": datetime.utcnow().isoformat(),
                    "optimization_type": "viral_potential",
                    "changes_made": ["Enhanced emotional appeal", "Added trending elements"],
                    "performance_impact": {
                        "viral_score_increase": 0.18,
                        "projected_reach_increase": 0.22
                    },
                    "status": "pending"
                }
            ],
            "cumulative_impact": {
                "total_engagement_improvement": 0.27,
                "total_reach_improvement": 0.35,
                "optimization_roi": 2.4
            },
            "optimization_patterns": {
                "most_effective_type": "engagement",
                "average_improvement": 0.13,
                "success_rate": 0.85
            },
            "next_recommendations": [
                "Consider A/B testing for further optimization",
                "Monitor performance for 1 week before next optimization",
                "Focus on conversion optimization in next iteration"
            ]
        }
        
        return optimization_history
        
    except Exception as e:
        logger.error(f"Epic 9.3: Error retrieving optimization history: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Optimization history retrieval failed: {str(e)}")


@router.post("/content/batch-optimize", response_model=BatchOptimizationResponse)
async def batch_optimize_content(
    request: BatchOptimizationRequest,
    optimization_engine = Depends(get_content_optimization_engine)
) -> BatchOptimizationResponse:
    """Batch optimize multiple content pieces (Epic 9.3)."""
    try:
        start_time = asyncio.get_event_loop().time()
        
        logger.info(f"Epic 9.3: Starting batch optimization of {len(request.content_items)} items")
        
        batch_id = f"batch_{int(start_time)}"
        individual_results = []
        total_improvements = 0
        
        # Process each content item
        for i, item in enumerate(request.content_items):
            try:
                content = item.get("content", "")
                item_id = item.get("id", f"item_{i}")
                
                # Mock individual optimization
                optimization_result = {
                    "item_id": item_id,
                    "original_content": content,
                    "optimized_content": f"{content}\n\n✨ Batch optimized for improved performance.",
                    "optimization_applied": ["engagement_enhancement", "clarity_improvement"],
                    "quality_improvement": 0.15,
                    "estimated_performance_lift": 0.12,
                    "optimization_confidence": 0.78,
                    "processing_time_ms": 150
                }
                
                individual_results.append(optimization_result)
                total_improvements += optimization_result["quality_improvement"]
                
            except Exception as e:
                logger.warning(f"Error optimizing item {i}: {e}")
                individual_results.append({
                    "item_id": item.get("id", f"item_{i}"),
                    "error": str(e),
                    "status": "failed"
                })
        
        # Batch optimization summary
        successful_optimizations = len([r for r in individual_results if "error" not in r])
        average_improvement = total_improvements / successful_optimizations if successful_optimizations > 0 else 0
        
        optimization_summary = {
            "total_processed": len(request.content_items),
            "successful_optimizations": successful_optimizations,
            "failed_optimizations": len(request.content_items) - successful_optimizations,
            "average_quality_improvement": average_improvement,
            "total_processing_time_ms": (asyncio.get_event_loop().time() - start_time) * 1000,
            "batch_success_rate": successful_optimizations / len(request.content_items) if request.content_items else 0
        }
        
        # Prioritized recommendations
        prioritized_recommendations = [
            f"Implement optimizations for {successful_optimizations} successfully processed items",
            "Review and address failed optimizations manually",
            "Monitor performance impact over next 2 weeks",
            "Consider A/B testing top-performing optimizations",
            "Schedule next batch optimization in 4 weeks"
        ]
        
        if average_improvement > 0.2:
            prioritized_recommendations.insert(1, "High improvement detected - prioritize immediate implementation")
        
        # Resource allocation recommendations
        resource_allocation = {
            "implementation_priority": "high" if average_improvement > 0.15 else "medium",
            "estimated_implementation_hours": successful_optimizations * 0.5,
            "recommended_team_size": min(3, max(1, successful_optimizations // 10)),
            "timeline_weeks": max(1, successful_optimizations // 20),
            "budget_estimate": successful_optimizations * 50  # $50 per optimization
        }
        
        # Implementation roadmap
        implementation_roadmap = [
            {
                "phase": "immediate",
                "timeline": "Week 1",
                "actions": ["Apply high-impact optimizations", "Set up performance monitoring"],
                "items_count": min(successful_optimizations, 10)
            },
            {
                "phase": "rollout",
                "timeline": "Week 2-3", 
                "actions": ["Apply remaining optimizations", "Monitor performance metrics"],
                "items_count": max(0, successful_optimizations - 10)
            },
            {
                "phase": "evaluation",
                "timeline": "Week 4",
                "actions": ["Analyze performance impact", "Plan next optimization cycle"],
                "items_count": 0
            }
        ]
        
        logger.info(f"Epic 9.3: Batch optimization completed - {successful_optimizations}/{len(request.content_items)} items optimized successfully")
        
        return BatchOptimizationResponse(
            batch_id=batch_id,
            total_items=len(request.content_items),
            optimization_summary=optimization_summary,
            individual_results=individual_results,
            prioritized_recommendations=prioritized_recommendations,
            resource_allocation=resource_allocation,
            implementation_roadmap=implementation_roadmap
        )
        
    except Exception as e:
        logger.error(f"Epic 9.3: Error in batch optimization: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Batch optimization failed: {str(e)}")


# === AUTOMATION ENDPOINTS ===

@router.post("/automation/workflows", response_model=WorkflowResponse)
async def create_optimization_workflow(
    request: WorkflowRequest
) -> WorkflowResponse:
    """Create optimization workflow for automation (Epic 9.3)."""
    try:
        start_time = asyncio.get_event_loop().time()
        
        logger.info(f"Epic 9.3: Creating {request.workflow_type} workflow: {request.workflow_name}")
        
        workflow_id = f"workflow_{int(start_time)}"
        
        # Validate workflow configuration
        if request.workflow_type == "scheduled" and not request.schedule:
            raise HTTPException(status_code=400, detail="Schedule configuration required for scheduled workflows")
        
        if request.workflow_type == "trigger-based" and not request.triggers:
            raise HTTPException(status_code=400, detail="Trigger conditions required for trigger-based workflows")
        
        # Calculate next execution time
        next_execution = None
        if request.workflow_type == "scheduled" and request.schedule:
            # Mock schedule calculation
            schedule_interval = request.schedule.get("interval_hours", 24)
            next_execution = datetime.utcnow() + timedelta(hours=schedule_interval)
        elif request.workflow_type == "continuous":
            next_execution = datetime.utcnow() + timedelta(minutes=5)  # Continuous workflows run every 5 minutes
        
        # Workflow configuration
        configuration = {
            "workflow_type": request.workflow_type,
            "content_sources": request.content_sources,
            "optimization_criteria": request.optimization_criteria,
            "schedule": request.schedule,
            "triggers": request.triggers,
            "approval_settings": request.approval_settings,
            "created_at": datetime.utcnow().isoformat(),
            "status": "active"
        }
        
        # Initialize execution history
        execution_history = [
            {
                "execution_id": f"exec_001",
                "timestamp": datetime.utcnow().isoformat(),
                "status": "scheduled",
                "items_processed": 0,
                "duration_ms": 0
            }
        ]
        
        # Performance metrics
        performance_metrics = {
            "total_executions": 0,
            "successful_executions": 0,
            "average_execution_time_ms": 0,
            "total_items_processed": 0,
            "average_optimization_improvement": 0,
            "last_execution_status": "pending"
        }
        
        logger.info(f"Epic 9.3: Workflow {workflow_id} created successfully")
        
        return WorkflowResponse(
            workflow_id=workflow_id,
            workflow_name=request.workflow_name,
            status="active",
            configuration=configuration,
            last_execution=None,
            next_execution=next_execution,
            execution_history=execution_history,
            performance_metrics=performance_metrics
        )
        
    except Exception as e:
        logger.error(f"Epic 9.3: Error creating workflow: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Workflow creation failed: {str(e)}")


@router.get("/automation/workflows/{workflow_id}", response_model=WorkflowResponse)
async def get_workflow_status(workflow_id: str) -> WorkflowResponse:
    """Get workflow status and details (Epic 9.3)."""
    try:
        logger.info(f"Epic 9.3: Retrieving workflow status for {workflow_id}")
        
        # Mock implementation - in production would query database
        workflow_response = WorkflowResponse(
            workflow_id=workflow_id,
            workflow_name="Content Optimization Workflow",
            status="running",
            configuration={
                "workflow_type": "scheduled",
                "content_sources": ["linkedin", "blog"],
                "optimization_criteria": {"min_quality_score": 0.7},
                "schedule": {"interval_hours": 24},
                "created_at": (datetime.utcnow() - timedelta(days=5)).isoformat()
            },
            last_execution=datetime.utcnow() - timedelta(hours=2),
            next_execution=datetime.utcnow() + timedelta(hours=22),
            execution_history=[
                {
                    "execution_id": "exec_003",
                    "timestamp": (datetime.utcnow() - timedelta(hours=2)).isoformat(),
                    "status": "completed",
                    "items_processed": 12,
                    "duration_ms": 45000,
                    "optimizations_applied": 8
                },
                {
                    "execution_id": "exec_002",
                    "timestamp": (datetime.utcnow() - timedelta(days=1, hours=2)).isoformat(),
                    "status": "completed",
                    "items_processed": 15,
                    "duration_ms": 52000,
                    "optimizations_applied": 11
                }
            ],
            performance_metrics={
                "total_executions": 3,
                "successful_executions": 3,
                "average_execution_time_ms": 48500,
                "total_items_processed": 42,
                "average_optimization_improvement": 0.18,
                "last_execution_status": "completed",
                "success_rate": 1.0
            }
        )
        
        return workflow_response
        
    except Exception as e:
        logger.error(f"Epic 9.3: Error retrieving workflow status: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Workflow status retrieval failed: {str(e)}")


@router.put("/automation/workflows/{workflow_id}", response_model=WorkflowResponse)
async def update_workflow(
    workflow_id: str,
    updates: Dict[str, Any]
) -> WorkflowResponse:
    """Update workflow configuration (Epic 9.3)."""
    try:
        logger.info(f"Epic 9.3: Updating workflow {workflow_id} with {len(updates)} changes")
        
        # Mock implementation - in production would update database
        updated_workflow = WorkflowResponse(
            workflow_id=workflow_id,
            workflow_name=updates.get("workflow_name", "Updated Workflow"),
            status=updates.get("status", "active"),
            configuration={
                "workflow_type": updates.get("workflow_type", "scheduled"),
                "content_sources": updates.get("content_sources", ["linkedin"]),
                "optimization_criteria": updates.get("optimization_criteria", {}),
                "schedule": updates.get("schedule", {"interval_hours": 24}),
                "updated_at": datetime.utcnow().isoformat(),
                "update_count": len(updates)
            },
            last_execution=datetime.utcnow() - timedelta(hours=1),
            next_execution=datetime.utcnow() + timedelta(hours=23),
            execution_history=[],
            performance_metrics={
                "total_executions": 0,
                "successful_executions": 0,
                "average_execution_time_ms": 0,
                "configuration_updates": len(updates)
            }
        )
        
        logger.info(f"Epic 9.3: Workflow {workflow_id} updated successfully")
        return updated_workflow
        
    except Exception as e:
        logger.error(f"Epic 9.3: Error updating workflow: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Workflow update failed: {str(e)}")


@router.delete("/automation/workflows/{workflow_id}")
async def delete_workflow(workflow_id: str) -> Dict[str, Any]:
    """Stop and delete workflow (Epic 9.3)."""
    try:
        logger.info(f"Epic 9.3: Deleting workflow {workflow_id}")
        
        # Mock implementation - in production would delete from database
        deletion_result = {
            "workflow_id": workflow_id,
            "deletion_status": "success",
            "stopped_at": datetime.utcnow().isoformat(),
            "final_stats": {
                "total_executions": 5,
                "total_items_processed": 67,
                "total_optimizations_applied": 42,
                "average_improvement": 0.16
            },
            "cleanup_actions": [
                "Workflow stopped",
                "Scheduled tasks cancelled",
                "Execution history archived",
                "Performance metrics saved"
            ],
            "archive_location": f"archive/workflows/{workflow_id}"
        }
        
        logger.info(f"Epic 9.3: Workflow {workflow_id} deleted successfully")
        return deletion_result
        
    except Exception as e:
        logger.error(f"Epic 9.3: Error deleting workflow: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Workflow deletion failed: {str(e)}")


@router.get("/automation/workflows")
async def list_workflows(
    status: Optional[str] = Query(None, description="Filter by workflow status"),
    workflow_type: Optional[str] = Query(None, description="Filter by workflow type"),
    limit: int = Query(20, description="Maximum number of workflows to return")
) -> Dict[str, Any]:
    """List all optimization workflows (Epic 9.3)."""
    try:
        logger.info(f"Epic 9.3: Listing workflows with status={status}, type={workflow_type}")
        
        # Mock implementation - in production would query database
        mock_workflows = [
            {
                "workflow_id": f"workflow_{i}",
                "workflow_name": f"Optimization Workflow {i+1}",
                "workflow_type": "scheduled" if i % 2 == 0 else "continuous",
                "status": "active" if i % 3 != 0 else "paused",
                "created_at": (datetime.utcnow() - timedelta(days=i*2)).isoformat(),
                "last_execution": (datetime.utcnow() - timedelta(hours=i*6)).isoformat(),
                "next_execution": (datetime.utcnow() + timedelta(hours=24-i*2)).isoformat(),
                "total_executions": 10 + i * 3,
                "items_processed": 150 + i * 25
            }
            for i in range(8)
        ]
        
        # Apply filters
        filtered_workflows = mock_workflows
        if status:
            filtered_workflows = [w for w in filtered_workflows if w["status"] == status]
        if workflow_type:
            filtered_workflows = [w for w in filtered_workflows if w["workflow_type"] == workflow_type]
        
        # Apply limit
        limited_workflows = filtered_workflows[:limit]
        
        summary = {
            "total_workflows": len(filtered_workflows),
            "active_workflows": len([w for w in filtered_workflows if w["status"] == "active"]),
            "paused_workflows": len([w for w in filtered_workflows if w["status"] == "paused"]),
            "scheduled_workflows": len([w for w in filtered_workflows if w["workflow_type"] == "scheduled"]),
            "continuous_workflows": len([w for w in filtered_workflows if w["workflow_type"] == "continuous"]),
            "total_executions": sum(w["total_executions"] for w in filtered_workflows),
            "total_items_processed": sum(w["items_processed"] for w in filtered_workflows)
        }
        
        response = {
            "workflows": limited_workflows,
            "summary": summary,
            "filters_applied": {
                "status": status,
                "workflow_type": workflow_type,
                "limit": limit
            }
        }
        
        logger.info(f"Epic 9.3: Retrieved {len(limited_workflows)} workflows")
        return response
        
    except Exception as e:
        logger.error(f"Epic 9.3: Error listing workflows: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Workflow listing failed: {str(e)}")


@router.post("/automation/schedules", response_model=ScheduleResponse)
async def schedule_optimization_task(
    request: ScheduleRequest
) -> ScheduleResponse:
    """Schedule optimization tasks (Epic 9.3)."""
    try:
        start_time = asyncio.get_event_loop().time()
        
        logger.info(f"Epic 9.3: Scheduling {request.task_type} task with {request.schedule_type} schedule")
        
        task_id = f"task_{int(start_time)}"
        
        # Calculate next execution time
        if request.schedule_type == "one-time":
            next_execution = datetime.fromisoformat(request.schedule_config.get("execution_time", datetime.utcnow().isoformat()))
        elif request.schedule_type == "recurring":
            interval_hours = request.schedule_config.get("interval_hours", 24)
            next_execution = datetime.utcnow() + timedelta(hours=interval_hours)
        else:  # conditional
            next_execution = datetime.utcnow() + timedelta(hours=1)  # Check conditions hourly
        
        # Estimate resource usage
        task_complexity = {
            "content_optimization": {"cpu": "medium", "memory": "low", "duration_min": 5},
            "strategy_analysis": {"cpu": "high", "memory": "medium", "duration_min": 15},
            "batch_optimization": {"cpu": "high", "memory": "high", "duration_min": 30},
            "performance_prediction": {"cpu": "medium", "memory": "low", "duration_min": 3}
        }
        
        complexity = task_complexity.get(request.task_type, {"cpu": "medium", "memory": "medium", "duration_min": 10})
        
        estimated_resource_usage = {
            "cpu_usage": complexity["cpu"],
            "memory_usage": complexity["memory"],
            "estimated_duration_minutes": complexity["duration_min"],
            "dependencies": request.dependencies,
            "priority_impact": request.priority
        }
        
        logger.info(f"Epic 9.3: Task {task_id} scheduled for {next_execution.isoformat()}")
        
        return ScheduleResponse(
            task_id=task_id,
            task_type=request.task_type,
            schedule_status="scheduled",
            next_execution=next_execution,
            execution_count=0,
            last_result=None,
            estimated_resource_usage=estimated_resource_usage
        )
        
    except Exception as e:
        logger.error(f"Epic 9.3: Error scheduling task: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Task scheduling failed: {str(e)}")