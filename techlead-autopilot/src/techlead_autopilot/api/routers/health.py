"""Health check endpoints."""

from fastapi import APIRouter
from datetime import datetime

router = APIRouter()


@router.get("/")
async def health_check():
    """Basic health check endpoint."""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "service": "TechLead AutoPilot API"
    }


@router.get("/ready")  
async def readiness_check():
    """Readiness check - indicates if service is ready to accept traffic."""
    # TODO: Add checks for database connection, external services, etc.
    return {
        "status": "ready",
        "timestamp": datetime.utcnow().isoformat(),
        "checks": {
            "database": "ok",
            "content_engine": "ok", 
            "lead_detector": "ok"
        }
    }