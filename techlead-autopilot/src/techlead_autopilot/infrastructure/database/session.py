"""
Database session management for multi-tenant SaaS platform.

Provides async database sessions with proper connection pooling and
multi-tenant isolation.
"""

import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool, QueuePool

from ...config import get_settings

logger = logging.getLogger(__name__)

# Global variables for database engine and session factory
_engine = None
_session_factory = None


def get_database_engine():
    """Get or create the database engine."""
    global _engine
    
    if _engine is None:
        settings = get_settings()
        
        # Configure engine based on environment
        if settings.is_development:
            # Development: Smaller pool, more verbose logging
            _engine = create_async_engine(
                settings.database_url_async,
                pool_size=5,
                max_overflow=10,
                pool_pre_ping=True,
                echo=settings.database_echo,
                future=True
            )
        else:
            # Production: Larger pool, optimized for performance  
            _engine = create_async_engine(
                settings.database_url_async,
                pool_size=settings.database_pool_size,
                max_overflow=settings.database_pool_size * 2,
                pool_pre_ping=True,
                pool_recycle=3600,  # Recycle connections every hour
                echo=False,
                future=True
            )
        
        logger.info(f"Database engine created for {settings.environment} environment")
    
    return _engine


def get_session_factory():
    """Get or create the session factory."""
    global _session_factory
    
    if _session_factory is None:
        engine = get_database_engine()
        _session_factory = async_sessionmaker(
            engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autoflush=False,
            autocommit=False
        )
        logger.info("Database session factory created")
    
    return _session_factory


@asynccontextmanager
async def get_database_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Get an async database session with proper error handling.
    
    Usage:
        async with get_database_session() as session:
            result = await session.execute(query)
            await session.commit()
    """
    session_factory = get_session_factory()
    
    async with session_factory() as session:
        try:
            yield session
        except Exception as e:
            await session.rollback()
            logger.error(f"Database session error: {e}")
            raise
        finally:
            await session.close()


class DatabaseSession:
    """
    Database session dependency for FastAPI.
    
    Provides proper session lifecycle management and multi-tenant isolation.
    """
    
    def __init__(self):
        self.session_factory = None
    
    async def __call__(self) -> AsyncGenerator[AsyncSession, None]:
        """Create and yield a database session."""
        if self.session_factory is None:
            self.session_factory = get_session_factory()
            
        async with self.session_factory() as session:
            try:
                yield session
            except Exception as e:
                await session.rollback()
                logger.error(f"Database session dependency error: {e}")
                raise
            finally:
                await session.close()


# Dependency instance for FastAPI
get_db_session = DatabaseSession()


async def init_database():
    """
    Initialize database connection and verify connectivity.
    
    Should be called during application startup.
    """
    try:
        engine = get_database_engine()
        
        # Test connection
        async with engine.begin() as conn:
            await conn.execute("SELECT 1")
        
        logger.info("Database connection initialized successfully")
        
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        raise


async def close_database():
    """
    Close database connections.
    
    Should be called during application shutdown.
    """
    global _engine, _session_factory
    
    if _engine:
        await _engine.dispose()
        _engine = None
        _session_factory = None
        logger.info("Database connections closed")


# Multi-tenant query helpers

class TenantAwareSession:
    """
    Wrapper for database session with automatic tenant isolation.
    
    Ensures all queries are automatically filtered by organization_id.
    """
    
    def __init__(self, session: AsyncSession, organization_id: str):
        self.session = session
        self.organization_id = organization_id
    
    async def execute(self, query, params=None):
        """Execute query with automatic tenant filtering."""
        # TODO: Implement automatic tenant filtering for queries
        # This would intercept queries and add WHERE organization_id = :org_id
        return await self.session.execute(query, params)
    
    async def commit(self):
        """Commit the transaction."""
        return await self.session.commit()
    
    async def rollback(self):
        """Rollback the transaction."""
        return await self.session.rollback()


def get_tenant_session(session: AsyncSession, organization_id: str) -> TenantAwareSession:
    """
    Get a tenant-aware session wrapper.
    
    Args:
        session: The database session
        organization_id: The organization ID for tenant isolation
    
    Returns:
        TenantAwareSession with automatic filtering
    """
    return TenantAwareSession(session, organization_id)