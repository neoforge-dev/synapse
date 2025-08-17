"""API router for concept mapping and idea relationship analysis."""

import asyncio
import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from graph_rag.api.dependencies import get_concept_extractor, get_temporal_tracker, get_cross_platform_correlator, get_belief_preference_extractor, get_viral_prediction_engine, get_brand_safety_analyzer
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