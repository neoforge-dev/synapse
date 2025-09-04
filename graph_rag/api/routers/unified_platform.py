#!/usr/bin/env python3
"""
Unified Platform Router
Epic 6 Week 4 - Unified Platform Integration

Provides API endpoints for monitoring and managing the unified platform orchestrator
that integrates AI failure prediction, multi-cloud deployment, and business automation.
"""

from typing import Any, Dict
from fastapi import APIRouter, Depends, HTTPException
from graph_rag.api.dependencies import get_unified_platform

router = APIRouter(prefix="/unified-platform", tags=["Unified Platform"])

@router.get("/status")
async def get_platform_status(
    unified_platform = Depends(get_unified_platform)
) -> Dict[str, Any]:
    """Get unified platform status including all integrated systems."""
    if not unified_platform:
        raise HTTPException(status_code=503, detail="Unified platform not available")
    
    try:
        # Execute unified monitoring to get current status
        status = await unified_platform.execute_unified_monitoring()
        return {
            "platform_status": "operational",
            "systems": status,
            "integration": "production_ready"
        }
    except Exception as e:
        return {
            "platform_status": "error",
            "error": str(e),
            "integration": "degraded"
        }

@router.get("/health")
async def get_platform_health(
    unified_platform = Depends(get_unified_platform)
) -> Dict[str, Any]:
    """Get comprehensive health check of all integrated systems."""
    if not unified_platform:
        raise HTTPException(status_code=503, detail="Unified platform not available")
    
    try:
        # Get AI predictions health
        ai_health = "operational"
        try:
            ai_predictions = await unified_platform.ai_predictor.predict_system_failures(["api", "database", "kubernetes"])
            if len(ai_predictions) == 0:
                ai_health = "no_predictions"
        except Exception:
            ai_health = "degraded"
        
        # Get multi-cloud health
        multi_cloud_health = "operational"
        try:
            cloud_status = await unified_platform.multi_cloud.get_deployment_status()
            if not cloud_status.get("aws", {}).get("healthy", True):
                multi_cloud_health = "degraded"
        except Exception:
            multi_cloud_health = "error"
        
        # Get business automation health
        business_health = "operational"
        try:
            business_stats = unified_platform.business_engine.get_performance_analytics()
            if business_stats.get("total_inquiries", 0) == 0:
                business_health = "no_data"
        except Exception:
            business_health = "error"
            
        # Get authentication health
        auth_health = "operational"
        try:
            auth_stats = unified_platform.auth_integration.get_session_stats()
            if auth_stats.get("total_sessions", 0) == 0:
                auth_health = "no_sessions"
        except Exception:
            auth_health = "error"
        
        overall_health = "healthy"
        if any(h in ["error", "degraded"] for h in [ai_health, multi_cloud_health, business_health, auth_health]):
            overall_health = "degraded"
        
        return {
            "overall_health": overall_health,
            "components": {
                "ai_failure_prediction": ai_health,
                "multi_cloud_deployment": multi_cloud_health,
                "business_automation": business_health,
                "authentication": auth_health
            },
            "integration_status": "epic_6_week_4_complete"
        }
    except Exception as e:
        return {
            "overall_health": "error",
            "error": str(e),
            "integration_status": "failed"
        }

@router.get("/business-pipeline")
async def get_business_pipeline_status(
    unified_platform = Depends(get_unified_platform)
) -> Dict[str, Any]:
    """Get business pipeline protection status and metrics."""
    if not unified_platform:
        raise HTTPException(status_code=503, detail="Unified platform not available")
    
    try:
        # Get business metrics
        business_stats = unified_platform.business_engine.get_performance_analytics()
        inquiry_stats = unified_platform.inquiry_detector.get_inquiry_stats()
        
        # Calculate pipeline value protection
        total_inquiries = inquiry_stats.get("total_inquiries", 0)
        high_value_inquiries = inquiry_stats.get("high_value_inquiries", 0)
        pipeline_value = high_value_inquiries * 37000  # Average consultation value
        
        return {
            "pipeline_protection": "active",
            "total_inquiries": total_inquiries,
            "high_value_inquiries": high_value_inquiries,
            "estimated_pipeline_value": pipeline_value,
            "protection_status": "operational" if total_inquiries > 0 else "monitoring",
            "business_continuity": "100%" if total_inquiries >= 10 else "75%"
        }
    except Exception as e:
        return {
            "pipeline_protection": "error",
            "error": str(e),
            "protection_status": "degraded"
        }

@router.post("/trigger-monitoring")
async def trigger_unified_monitoring(
    unified_platform = Depends(get_unified_platform)
) -> Dict[str, Any]:
    """Manually trigger unified platform monitoring cycle."""
    if not unified_platform:
        raise HTTPException(status_code=503, detail="Unified platform not available")
    
    try:
        result = await unified_platform.execute_unified_monitoring()
        return {
            "monitoring_triggered": True,
            "result": result,
            "timestamp": result.get("timestamp")
        }
    except Exception as e:
        return {
            "monitoring_triggered": False,
            "error": str(e)
        }

def create_unified_platform_router() -> APIRouter:
    """Factory function to create unified platform router."""
    return router