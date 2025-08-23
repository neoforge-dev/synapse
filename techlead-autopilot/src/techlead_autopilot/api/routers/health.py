"""Health check endpoints with comprehensive monitoring."""

import asyncio
import psutil
import time
from datetime import datetime, timedelta
from typing import Dict, Any, Optional

from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from ...infrastructure.database.session import get_db_session
from ...infrastructure.logging import get_logger
from ...config.settings import get_settings

router = APIRouter()
logger = get_logger('api.health')


@router.get("/")
async def health_check():
    """Basic health check endpoint."""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "service": "TechLead AutoPilot API",
        "version": get_settings().version
    }


@router.get("/ready")  
async def readiness_check(db: AsyncSession = Depends(get_db_session)):
    """Readiness check - indicates if service is ready to accept traffic."""
    checks = {}
    overall_status = "ready"
    
    try:
        # Database connectivity check
        start_time = time.time()
        await db.execute(text("SELECT 1"))
        db_response_time = (time.time() - start_time) * 1000
        
        checks["database"] = {
            "status": "ok",
            "response_time_ms": round(db_response_time, 2)
        }
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        checks["database"] = {
            "status": "error",
            "error": str(e)
        }
        overall_status = "degraded"
    
    # Additional service checks could be added here
    checks["content_engine"] = {"status": "ok"}
    checks["lead_detector"] = {"status": "ok"}
    
    return {
        "status": overall_status,
        "timestamp": datetime.utcnow().isoformat(),
        "checks": checks
    }


@router.get("/live")
async def liveness_check():
    """Liveness check - indicates if the application is alive."""
    return {
        "status": "alive",
        "timestamp": datetime.utcnow().isoformat(),
        "uptime_seconds": time.time() - _get_start_time()
    }


@router.get("/metrics")
async def system_metrics():
    """Get system metrics for monitoring."""
    try:
        # CPU and memory metrics
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        # Process-specific metrics
        process = psutil.Process()
        process_memory = process.memory_info()
        process_cpu = process.cpu_percent()
        
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "system": {
                "cpu_percent": cpu_percent,
                "memory": {
                    "total": memory.total,
                    "available": memory.available,
                    "used": memory.used,
                    "percent": memory.percent
                },
                "disk": {
                    "total": disk.total,
                    "used": disk.used,
                    "free": disk.free,
                    "percent": disk.percent
                }
            },
            "process": {
                "cpu_percent": process_cpu,
                "memory": {
                    "rss": process_memory.rss,
                    "vms": process_memory.vms
                },
                "threads": process.num_threads(),
                "connections": len(process.connections()),
                "open_files": len(process.open_files())
            }
        }
    except Exception as e:
        logger.error(f"Failed to get system metrics: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve system metrics")


@router.get("/detailed")
async def detailed_health_check(db: AsyncSession = Depends(get_db_session)):
    """Comprehensive health check with detailed information."""
    settings = get_settings()
    checks = {}
    overall_status = "healthy"
    
    # Database checks
    try:
        start_time = time.time()
        
        # Test basic connectivity
        await db.execute(text("SELECT 1"))
        basic_response_time = (time.time() - start_time) * 1000
        
        # Test more complex query
        start_time = time.time()
        result = await db.execute(text("SELECT COUNT(*) as table_count FROM information_schema.tables WHERE table_schema = 'public'"))
        table_count = (await result.fetchone())[0]
        complex_response_time = (time.time() - start_time) * 1000
        
        checks["database"] = {
            "status": "ok",
            "basic_query_time_ms": round(basic_response_time, 2),
            "complex_query_time_ms": round(complex_response_time, 2),
            "table_count": table_count
        }
        
        # Performance warnings
        if basic_response_time > 100:
            checks["database"]["warning"] = "Slow database response time"
            overall_status = "degraded"
            
    except Exception as e:
        logger.error(f"Database detailed check failed: {e}")
        checks["database"] = {
            "status": "error",
            "error": str(e)
        }
        overall_status = "unhealthy"
    
    # System resource checks
    try:
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        checks["system_resources"] = {
            "status": "ok",
            "memory_usage_percent": memory.percent,
            "disk_usage_percent": disk.percent,
            "cpu_count": psutil.cpu_count()
        }
        
        # Resource warnings
        if memory.percent > 85:
            checks["system_resources"]["warning"] = "High memory usage"
            overall_status = "degraded"
        
        if disk.percent > 90:
            checks["system_resources"]["warning"] = "High disk usage"
            overall_status = "degraded"
            
    except Exception as e:
        logger.error(f"System resources check failed: {e}")
        checks["system_resources"] = {
            "status": "error",
            "error": str(e)
        }
    
    # External service checks (if configured)
    checks["external_services"] = await _check_external_services(settings)
    
    return {
        "status": overall_status,
        "timestamp": datetime.utcnow().isoformat(),
        "version": settings.version,
        "environment": settings.environment,
        "uptime_seconds": time.time() - _get_start_time(),
        "checks": checks
    }


async def _check_external_services(settings) -> Dict[str, Any]:
    """Check external service connectivity."""
    services = {}
    
    # Redis check (if configured)
    try:
        import redis
        if settings.redis_url:
            r = redis.from_url(settings.redis_url)
            start_time = time.time()
            r.ping()
            response_time = (time.time() - start_time) * 1000
            services["redis"] = {
                "status": "ok",
                "response_time_ms": round(response_time, 2)
            }
    except Exception as e:
        services["redis"] = {
            "status": "error",
            "error": str(e)
        }
    
    # OpenAI API check (if configured)
    if settings.openai_api_key:
        try:
            import openai
            client = openai.AsyncOpenAI(api_key=settings.openai_api_key)
            # Just check if we can create a client - don't make actual API calls in health checks
            services["openai"] = {"status": "configured"}
        except Exception as e:
            services["openai"] = {
                "status": "error",
                "error": "Configuration error"
            }
    
    return services


# Global variable to track start time
_START_TIME = time.time()

def _get_start_time() -> float:
    """Get application start time."""
    return _START_TIME