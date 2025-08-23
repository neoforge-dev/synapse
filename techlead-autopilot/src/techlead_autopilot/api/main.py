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
from ..infrastructure.logging import setup_logging, get_logger, log_security_event
from ..infrastructure.monitoring import get_monitoring_service
from .middleware import (
    SecurityMiddleware,
    AuthenticationMiddleware,
    ErrorHandlingMiddleware,
    RateLimitingMiddleware,
    PII_SanitizationMiddleware
)
from .middleware.logging import ConditionalLoggingMiddleware, RequestContextMiddleware
from .routers import auth, content, leads, organizations, health, scheduler, jobs, integrations
from ..infrastructure.documentation.openapi_enhancer import OpenAPIEnhancer


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan manager."""
    settings = get_settings()
    
    # Initialize logging and monitoring first
    setup_logging()
    logger = get_logger('api.startup')
    
    # Initialize monitoring service (Sentry if configured)
    monitoring_service = get_monitoring_service()
    if monitoring_service.is_enabled():
        logger.info("Error tracking and monitoring initialized")
    
    # Startup logic
    logger.info(
        "Starting TechLead AutoPilot API",
        version=settings.version,
        environment=settings.environment
    )
    
    try:
        # Initialize database connection
        await init_database()
        logger.info("Database connection initialized")
        
        # Log security event for application startup
        log_security_event(
            event_type="application_startup",
            description=f"API started in {settings.environment} environment",
            additional_data={"version": settings.version}
        )
        
    except Exception as e:
        logger.error(
            "Database initialization failed",
            error=str(e),
            exc_info=True
        )
    
    yield
    
    # Shutdown logic
    logger.info("Shutting down TechLead AutoPilot API")
    
    try:
        await close_database()
        logger.info("Database connections closed")
    except Exception as e:
        logger.error(
            "Database cleanup failed",
            error=str(e),
            exc_info=True
        )
    
    # Log security event for application shutdown
    log_security_event(
        event_type="application_shutdown",
        description=f"API stopped gracefully in {settings.environment} environment"
    )


def create_app() -> FastAPI:
    """Create and configure FastAPI application."""
    settings = get_settings()
    
    # Create FastAPI app with enhanced documentation
    app = FastAPI(
        title="TechLead AutoPilot API",
        description="Technical Leadership Automation Platform - Transform expertise into systematic business growth",
        version=settings.version,
        lifespan=lifespan,
        # Documentation URLs will be handled by OpenAPI enhancer
        docs_url=None,
        redoc_url=None,
        openapi_url="/openapi.json" if not settings.is_production else "/openapi.json",
    )
    
    # Add security middleware (order matters - first added = outermost layer)
    # 1. Error handling (outermost - catches all errors)
    app.add_middleware(ErrorHandlingMiddleware)
    app.add_middleware(PII_SanitizationMiddleware)
    
    # 2. Request context and logging (for monitoring)
    app.add_middleware(RequestContextMiddleware)
    app.add_middleware(ConditionalLoggingMiddleware, log_requests=True, log_responses=True)
    
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
    
    # Setup enhanced OpenAPI documentation
    docs_url = "/docs" if not settings.is_production else None
    redoc_url = "/redoc" if not settings.is_production else None
    
    openapi_enhancer = OpenAPIEnhancer(
        app=app,
        title="TechLead AutoPilot API",
        version=settings.version,
        docs_url=docs_url,
        redoc_url=redoc_url,
        enable_auth_flows=True,
        enable_examples=True,
        enable_multi_env=True
    )
    
    # Setup enhanced OpenAPI schema and custom documentation routes
    openapi_enhancer.enhance_openapi_schema()
    
    if docs_url or redoc_url:
        openapi_enhancer.setup_custom_docs_routes()
    
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
    
    app.include_router(
        integrations.router,
        prefix=f"{settings.api_prefix}/integrations",
        tags=["LinkedIn Integration"]
    )
    
    app.include_router(
        jobs.router,
        prefix=f"{settings.api_prefix}/jobs",
        tags=["Job Management"]
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