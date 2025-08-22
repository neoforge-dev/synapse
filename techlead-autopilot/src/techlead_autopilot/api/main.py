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
from ..infrastructure.database import init_database, close_database
from .middleware import (
    SecurityMiddleware,
    AuthenticationMiddleware,
    ErrorHandlingMiddleware,
    RateLimitingMiddleware,
    RequestLoggingMiddleware,
    PII_SanitizationMiddleware
)
from .routers import auth, content, leads, organizations, health, scheduler


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan manager."""
    settings = get_settings()
    
    # Startup logic
    print(f"Starting TechLead AutoPilot API v{settings.version}")
    print(f"Environment: {settings.environment}")
    
    try:
        # Initialize database connection
        await init_database()
        print("Database connection initialized")
    except Exception as e:
        print(f"Warning: Database initialization failed: {e}")
    
    yield
    
    # Shutdown logic
    try:
        await close_database()
        print("Database connections closed")
    except Exception as e:
        print(f"Warning: Database cleanup failed: {e}")
    
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
    
    # Add security middleware (order matters - first added = outermost layer)
    # 1. Error handling (outermost - catches all errors)
    app.add_middleware(ErrorHandlingMiddleware)
    app.add_middleware(PII_SanitizationMiddleware)
    
    # 2. Request logging (for monitoring)
    app.add_middleware(RequestLoggingMiddleware)
    
    # 3. Rate limiting (prevent abuse)
    app.add_middleware(RateLimitingMiddleware)
    
    # 4. Security headers and validation
    app.add_middleware(SecurityMiddleware)
    
    # 5. Authentication context
    app.add_middleware(AuthenticationMiddleware)
    
    # 6. CORS (allow cross-origin requests)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=_get_allowed_origins(settings),
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH"],
        allow_headers=["*"],
    )
    
    # 7. Compression (innermost - applied to response)
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
    
    app.include_router(
        scheduler.router,
        prefix=f"{settings.api_prefix}/scheduler",
        tags=["Automated Posting"]
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


def _get_allowed_origins(settings) -> list[str]:
    """Get allowed CORS origins based on environment."""
    if settings.is_development:
        return [
            "http://localhost:3000",    # React dev server
            "http://localhost:8000",    # API server
            "http://127.0.0.1:3000",   # Alternative localhost
            "http://127.0.0.1:8000",   # Alternative localhost
        ]
    elif settings.environment == "staging":
        return [
            "https://staging.techleadautopilot.com",
            "https://staging-app.techleadautopilot.com",
        ]
    else:  # production
        return [
            "https://techleadautopilot.com",
            "https://app.techleadautopilot.com",
            "https://www.techleadautopilot.com",
        ]