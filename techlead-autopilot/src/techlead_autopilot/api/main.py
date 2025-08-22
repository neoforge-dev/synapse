"""
FastAPI application factory for TechLead AutoPilot.

Multi-tenant SaaS API with authentication, content generation, and lead detection.
"""

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware

from ..config import get_settings
from .routers import auth, content, leads, organizations, health


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan manager."""
    settings = get_settings()
    
    # Startup logic
    print(f"Starting TechLead AutoPilot API v{settings.version}")
    print(f"Environment: {settings.environment}")
    
    yield
    
    # Shutdown logic
    print("Shutting down TechLead AutoPilot API")


def create_app() -> FastAPI:
    """Create and configure FastAPI application."""
    settings = get_settings()
    
    # Create FastAPI app
    app = FastAPI(
        title="TechLead AutoPilot API",
        description="Technical Leadership Automation Platform - Transform expertise into systematic business growth",
        version=settings.version,
        lifespan=lifespan,
        docs_url="/docs" if not settings.is_production else None,
        redoc_url="/redoc" if not settings.is_production else None,
    )
    
    # Add middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"] if settings.is_development else ["https://app.techleadautopilot.com"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    app.add_middleware(GZipMiddleware, minimum_size=1000)
    
    # Include routers
    app.include_router(
        health.router,
        prefix="/health",
        tags=["Health"]
    )
    
    app.include_router(
        auth.router,
        prefix=f"{settings.api_prefix}/auth",
        tags=["Authentication"]
    )
    
    app.include_router(
        organizations.router,
        prefix=f"{settings.api_prefix}/organizations",
        tags=["Organizations"]
    )
    
    app.include_router(
        content.router,
        prefix=f"{settings.api_prefix}/content",
        tags=["Content Generation"]
    )
    
    app.include_router(
        leads.router,
        prefix=f"{settings.api_prefix}/leads",
        tags=["Lead Detection"]
    )
    
    @app.get("/")
    async def root():
        """Root endpoint."""
        return {
            "message": "TechLead AutoPilot API",
            "version": settings.version,
            "docs": "/docs" if not settings.is_production else None
        }
    
    return app