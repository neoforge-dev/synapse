"""
Epic 15 Phase 3: Unified Business Intelligence API Router
Enterprise-ready business intelligence endpoints with cross-platform analytics
"""

import logging
from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta
import asyncio
import json

from fastapi import APIRouter, HTTPException, Query, Depends, BackgroundTasks
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

class BusinessIntelligenceMetrics(BaseModel):
    """Business intelligence metrics response model"""
    total_pipeline_value: int = Field(..., description="Total pipeline value in USD")
    qualified_leads: int = Field(..., description="Number of qualified leads")
    conversion_rate: float = Field(..., description="Lead conversion rate as decimal")
    arr_progress: float = Field(..., description="ARR target achievement as percentage")
    automation_efficiency: float = Field(..., description="Automation efficiency score")
    business_health_score: float = Field(..., description="Overall business health score")
    last_updated: str = Field(..., description="Last update timestamp")

class DatabasePerformanceResponse(BaseModel):
    """Database performance metrics response"""
    database_name: str
    optimization_score: float
    query_time_ms: float
    size_mb: float
    record_count: int
    last_optimized: str

class UnifiedAnalyticsResponse(BaseModel):
    """Unified analytics response model"""
    epic7_crm: Dict[str, Any]
    cross_platform_correlation: Dict[str, Any]
    unified_revenue_forecast: Dict[str, Any]
    business_insights: List[str]
    optimization_recommendations: List[str]

class EnterpriseReadinessResponse(BaseModel):
    """Enterprise readiness assessment response"""
    overall_score: float = Field(..., description="Overall enterprise readiness score (0-100)")
    status: str = Field(..., description="Readiness status: ready, needs_optimization, not_ready")
    database_readiness: float = Field(..., description="Database readiness score")
    intelligence_readiness: float = Field(..., description="Intelligence system readiness score")
    automation_readiness: float = Field(..., description="Automation system readiness score")
    governance_readiness: float = Field(..., description="Data governance readiness score")
    recommendations: List[str] = Field(..., description="Enterprise improvement recommendations")

class RealTimeDashboardResponse(BaseModel):
    """Real-time dashboard data response"""
    executive_summary: Dict[str, Any]
    operational_metrics: Dict[str, Any] 
    revenue_analytics: Dict[str, Any]
    system_health: Dict[str, Any]
    automation_performance: Dict[str, Any]
    alerts_notifications: List[Dict[str, Any]]
    last_updated: str
    refresh_rate: str
    data_freshness: str

def create_unified_business_intelligence_router() -> APIRouter:
    """Create unified business intelligence API router"""
    router = APIRouter(prefix="/api/v1/business-intelligence", tags=["Business Intelligence"])
    
    # Import here to avoid circular imports and ensure availability
    try:
        import sys
        import os
        sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', '..', 'business_development'))
        from unified_business_intelligence import UnifiedBusinessIntelligence
        
        # Global UBI instance for API endpoints
        _ubi_instance = None
        
        def get_ubi_instance():
            nonlocal _ubi_instance
            if _ubi_instance is None:
                _ubi_instance = UnifiedBusinessIntelligence()
            return _ubi_instance
            
    except ImportError as e:
        logger.error(f"Failed to import UnifiedBusinessIntelligence: {e}")
        
        def get_ubi_instance():
            raise HTTPException(
                status_code=503,
                detail="Business intelligence system not available"
            )
    
    @router.get("/metrics", response_model=BusinessIntelligenceMetrics)
    async def get_business_intelligence_metrics():
        """Get current business intelligence metrics"""
        try:
            ubi = get_ubi_instance()
            
            # Get unified analytics data
            analytics = ubi.create_unified_analytics_engine()
            epic7_data = analytics.get('epic7_crm', {})
            crm_metrics = epic7_data.get('crm_metrics', {})
            forecast_data = analytics.get('unified_revenue_forecast', {})
            correlation_data = analytics.get('cross_platform_correlation', {}).get('correlation_analysis', {})
            
            return BusinessIntelligenceMetrics(
                total_pipeline_value=crm_metrics.get('total_pipeline_value', 0),
                qualified_leads=crm_metrics.get('qualified_leads', 0),
                conversion_rate=epic7_data.get('automation_metrics', {}).get('conversion_rate', 0.0) / 100.0,
                arr_progress=forecast_data.get('arr_target_achievement', {}).get('achievement_percentage', 0.0),
                automation_efficiency=correlation_data.get('automation_efficiency', 0.0),
                business_health_score=epic7_data.get('business_health_score', 0.0),
                last_updated=datetime.now().isoformat()
            )
            
        except Exception as e:
            logger.error(f"Failed to get business intelligence metrics: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to retrieve metrics: {str(e)}")
    
    @router.get("/database-performance", response_model=List[DatabasePerformanceResponse])
    async def get_database_performance():
        """Get database performance metrics across all systems"""
        try:
            ubi = get_ubi_instance()
            performance_metrics = ubi.optimize_database_performance()
            
            return [
                DatabasePerformanceResponse(
                    database_name=db_name,
                    optimization_score=metrics.optimization_score,
                    query_time_ms=metrics.query_time,
                    size_mb=metrics.size_mb,
                    record_count=metrics.record_count,
                    last_optimized=metrics.last_updated
                )
                for db_name, metrics in performance_metrics.items()
            ]
            
        except Exception as e:
            logger.error(f"Failed to get database performance: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to retrieve database performance: {str(e)}")
    
    @router.post("/optimize-databases")
    async def optimize_databases(background_tasks: BackgroundTasks):
        """Trigger database optimization in background"""
        try:
            ubi = get_ubi_instance()
            
            def run_optimization():
                performance_metrics = ubi.optimize_database_performance()
                logger.info(f"Background database optimization completed for {len(performance_metrics)} databases")
                
            background_tasks.add_task(run_optimization)
            
            return {
                "message": "Database optimization started in background",
                "status": "initiated",
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to start database optimization: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to start optimization: {str(e)}")
    
    @router.get("/analytics", response_model=UnifiedAnalyticsResponse)
    async def get_unified_analytics():
        """Get comprehensive unified analytics across all platforms"""
        try:
            ubi = get_ubi_instance()
            analytics = ubi.create_unified_analytics_engine()
            
            # Extract insights and recommendations
            correlation_data = analytics.get('cross_platform_correlation', {})
            insights = correlation_data.get('business_insights', [])
            recommendations = correlation_data.get('optimization_recommendations', [])
            
            return UnifiedAnalyticsResponse(
                epic7_crm=analytics.get('epic7_crm', {}),
                cross_platform_correlation=analytics.get('cross_platform_correlation', {}),
                unified_revenue_forecast=analytics.get('unified_revenue_forecast', {}),
                business_insights=insights,
                optimization_recommendations=recommendations
            )
            
        except Exception as e:
            logger.error(f"Failed to get unified analytics: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to retrieve analytics: {str(e)}")
    
    @router.get("/dashboard", response_model=RealTimeDashboardResponse)
    async def get_real_time_dashboard():
        """Get real-time business intelligence dashboard data"""
        try:
            ubi = get_ubi_instance()
            dashboard_data = ubi.create_real_time_dashboard()
            
            return RealTimeDashboardResponse(
                executive_summary=dashboard_data.get('executive_summary', {}),
                operational_metrics=dashboard_data.get('operational_metrics', {}),
                revenue_analytics=dashboard_data.get('revenue_analytics', {}),
                system_health=dashboard_data.get('system_health', {}),
                automation_performance=dashboard_data.get('automation_performance', {}),
                alerts_notifications=dashboard_data.get('alerts_notifications', []),
                last_updated=dashboard_data.get('last_updated', datetime.now().isoformat()),
                refresh_rate=dashboard_data.get('refresh_rate', '60 seconds'),
                data_freshness=dashboard_data.get('data_freshness', 'real-time')
            )
            
        except Exception as e:
            logger.error(f"Failed to get dashboard data: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to retrieve dashboard: {str(e)}")
    
    @router.get("/enterprise-readiness", response_model=EnterpriseReadinessResponse)
    async def get_enterprise_readiness():
        """Get enterprise readiness assessment"""
        try:
            ubi = get_ubi_instance()
            assessment = ubi.get_enterprise_readiness_assessment()
            
            overall = assessment.get('overall_enterprise_readiness', {})
            
            return EnterpriseReadinessResponse(
                overall_score=overall.get('score', 0.0),
                status=overall.get('status', 'unknown'),
                database_readiness=assessment.get('database_readiness', {}).get('score', 0.0),
                intelligence_readiness=assessment.get('intelligence_readiness', {}).get('score', 0.0),
                automation_readiness=assessment.get('automation_readiness', {}).get('score', 0.0),
                governance_readiness=assessment.get('governance_readiness', {}).get('score', 0.0),
                recommendations=assessment.get('recommendations', [])
            )
            
        except Exception as e:
            logger.error(f"Failed to get enterprise readiness: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to retrieve readiness assessment: {str(e)}")
    
    @router.get("/epic7-status")
    async def get_epic7_business_continuity():
        """Get Epic 7 business continuity status"""
        try:
            ubi = get_ubi_instance()
            analytics = ubi.create_unified_analytics_engine()
            epic7_data = analytics.get('epic7_crm', {})
            crm_metrics = epic7_data.get('crm_metrics', {})
            
            pipeline_value = crm_metrics.get('total_pipeline_value', 0)
            protection_status = "protected" if pipeline_value >= 1158000 else "at_risk"
            
            return {
                "pipeline_value": pipeline_value,
                "protection_target": 1158000,
                "protection_status": protection_status,
                "contacts_preserved": crm_metrics.get('total_contacts', 0),
                "qualified_leads": crm_metrics.get('qualified_leads', 0),
                "proposals_active": epic7_data.get('proposal_metrics', {}).get('total_proposals', 0),
                "automation_sequences": epic7_data.get('automation_metrics', {}).get('active_sequences', 0),
                "business_health_score": epic7_data.get('business_health_score', 0.0),
                "last_validated": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to get Epic 7 status: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to retrieve Epic 7 status: {str(e)}")
    
    @router.get("/revenue-forecast")
    async def get_revenue_forecast(
        period: str = Query("annual", description="Forecast period: monthly, quarterly, annual")
    ):
        """Get unified revenue forecast"""
        try:
            ubi = get_ubi_instance()
            analytics = ubi.create_unified_analytics_engine()
            forecast_data = analytics.get('unified_revenue_forecast', {})
            
            if period == "monthly":
                projection = forecast_data.get('monthly_projection', 0)
            elif period == "quarterly":
                projection = forecast_data.get('quarterly_projection', 0)
            else:
                projection = forecast_data.get('annual_projection', 0)
            
            return {
                "period": period,
                "projection": projection,
                "current_pipeline_value": forecast_data.get('current_pipeline_value', 0),
                "arr_target_achievement": forecast_data.get('arr_target_achievement', {}),
                "confidence_score": forecast_data.get('confidence_score', 0.0),
                "efficiency_multiplier": forecast_data.get('efficiency_multiplier', 1.0),
                "health_multiplier": forecast_data.get('health_multiplier', 1.0),
                "forecast_generated": forecast_data.get('forecast_generated', datetime.now().isoformat())
            }
            
        except Exception as e:
            logger.error(f"Failed to get revenue forecast: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to retrieve revenue forecast: {str(e)}")
    
    @router.get("/cross-platform-correlation")
    async def get_cross_platform_correlation():
        """Get cross-platform correlation analysis"""
        try:
            ubi = get_ubi_instance()
            analytics = ubi.create_unified_analytics_engine()
            correlation_data = analytics.get('cross_platform_correlation', {})
            
            return {
                "correlation_analysis": correlation_data.get('correlation_analysis', {}),
                "business_insights": correlation_data.get('business_insights', []),
                "optimization_recommendations": correlation_data.get('optimization_recommendations', []),
                "last_analyzed": correlation_data.get('last_analyzed', datetime.now().isoformat())
            }
            
        except Exception as e:
            logger.error(f"Failed to get correlation analysis: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to retrieve correlation analysis: {str(e)}")
    
    @router.get("/alerts")
    async def get_business_intelligence_alerts(
        level: Optional[str] = Query(None, description="Filter by alert level: info, warning, critical")
    ):
        """Get business intelligence alerts and notifications"""
        try:
            ubi = get_ubi_instance()
            dashboard_data = ubi.create_real_time_dashboard()
            alerts = dashboard_data.get('alerts_notifications', [])
            
            # Filter by level if specified
            if level:
                alerts = [alert for alert in alerts if alert.get('level') == level]
            
            return {
                "alerts": alerts,
                "total_count": len(alerts),
                "filter_applied": level,
                "last_updated": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to get alerts: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to retrieve alerts: {str(e)}")
    
    @router.get("/export")
    async def export_enterprise_data():
        """Export comprehensive enterprise business intelligence data"""
        try:
            ubi = get_ubi_instance()
            export_data = ubi.export_enterprise_data()
            
            return JSONResponse(
                content=export_data,
                headers={
                    "Content-Type": "application/json",
                    "Content-Disposition": f"attachment; filename=epic15_unified_intelligence_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                }
            )
            
        except Exception as e:
            logger.error(f"Failed to export enterprise data: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to export data: {str(e)}")
    
    @router.get("/health")
    async def get_business_intelligence_health():
        """Get business intelligence system health status"""
        try:
            ubi = get_ubi_instance()
            
            # Quick health check
            analytics = ubi.create_unified_analytics_engine()
            performance = ubi.optimize_database_performance()
            
            system_health = {
                "status": "operational",
                "databases_monitored": len(performance),
                "analytics_platforms": len(analytics),
                "real_time_monitoring": True,
                "epic7_protection_active": analytics.get('epic7_crm', {}).get('crm_metrics', {}).get('total_pipeline_value', 0) >= 1158000,
                "last_health_check": datetime.now().isoformat()
            }
            
            # Check for any system issues
            avg_optimization = sum(m.optimization_score for m in performance.values()) / max(len(performance), 1)
            if avg_optimization < 0.6:
                system_health["status"] = "degraded"
                system_health["issues"] = ["Database optimization below threshold"]
            
            return system_health
            
        except Exception as e:
            logger.error(f"Business intelligence health check failed: {e}")
            return {
                "status": "unhealthy",
                "error": str(e),
                "last_health_check": datetime.now().isoformat()
            }
    
    @router.post("/refresh-cache")
    async def refresh_intelligence_cache():
        """Manually refresh business intelligence cache"""
        try:
            ubi = get_ubi_instance()
            ubi.update_real_time_metrics()
            
            return {
                "message": "Business intelligence cache refreshed successfully",
                "status": "completed",
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to refresh cache: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to refresh cache: {str(e)}")
    
    return router

# Factory function for easy integration with main API
def create_unified_business_intelligence_api_router() -> APIRouter:
    """Factory function to create unified business intelligence router"""
    return create_unified_business_intelligence_router()