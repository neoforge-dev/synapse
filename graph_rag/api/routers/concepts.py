"""API router for concept mapping and idea relationship analysis."""

import asyncio
import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from graph_rag.api.dependencies import get_concept_extractor, get_temporal_tracker, get_cross_platform_correlator, get_belief_preference_extractor
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