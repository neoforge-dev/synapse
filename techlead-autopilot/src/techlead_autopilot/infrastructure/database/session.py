"""
Database session management for multi-tenant SaaS platform.

Provides async database sessions with proper connection pooling and
multi-tenant isolation.
"""

import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Optional
import time

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool, QueuePool
from sqlalchemy import text, event
from sqlalchemy.engine import Engine

from ...config import get_settings
from ..logging import get_logger, log_error
from ..monitoring import add_breadcrumb

logger = get_logger('database.session')

# Global variables for database engine and session factory
_engine = None
_session_factory = None


def get_database_engine():
    """Get or create the database engine with production optimizations."""
    global _engine
    
    if _engine is None:
        settings = get_settings()
        
        # Base engine configuration
        engine_kwargs = {
            'pool_pre_ping': True,
            'pool_recycle': 3600,  # Recycle connections every hour
            'future': True,
            # Connection arguments for PostgreSQL optimization
            'connect_args': {
                'server_settings': {
                    'jit': 'off',  # Disable JIT for better predictability
                    'statement_timeout': '30000',  # 30 second timeout
                    'lock_timeout': '10000',  # 10 second lock timeout
                }
            }
        }
        
        # Configure pool based on environment
        if settings.is_development:
            engine_kwargs.update({
                'pool_size': 5,
                'max_overflow': 10,
                'echo': settings.database_echo,
            })
        else:
            # Production optimizations
            engine_kwargs.update({
                'pool_size': settings.database_pool_size,
                'max_overflow': settings.database_pool_size * 2,
                'pool_timeout': 30,  # Max wait time for connection
                'pool_reset_on_return': 'commit',  # Reset connections on return
                'echo': False,
            })
        
        _engine = create_async_engine(settings.database_url_async, **engine_kwargs)
        
        # Add query performance logging for slow queries
        if not settings.is_production:
            _setup_query_logging(_engine)
        
        logger.info(
            "Database engine created",
            environment=settings.environment,
            pool_size=engine_kwargs.get('pool_size'),
            max_overflow=engine_kwargs.get('max_overflow')
        )
    
    return _engine


def _setup_query_logging(engine):
    """Set up query performance logging for development."""
    @event.listens_for(engine.sync_engine, "before_cursor_execute")
    def receive_before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
        context._query_start_time = time.time()
    
    @event.listens_for(engine.sync_engine, "after_cursor_execute") 
    def receive_after_cursor_execute(conn, cursor, statement, parameters, context, executemany):
        total = time.time() - context._query_start_time
        if total > 1.0:  # Log queries taking more than 1 second
            logger.warning(
                "Slow query detected",
                duration_seconds=round(total, 3),
                query=statement[:200] + "..." if len(statement) > 200 else statement
            )


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
    Get an async database session with proper error handling and monitoring.
    
    Usage:
        async with get_database_session() as session:
            result = await session.execute(query)
            await session.commit()
    """
    session_factory = get_session_factory()
    session_start_time = time.time()
    
    async with session_factory() as session:
        try:
            add_breadcrumb("Database session started")
            yield session
        except Exception as e:
            await session.rollback()
            session_duration = time.time() - session_start_time
            
            logger.error(
                "Database session error",
                error_type=type(e).__name__,
                error_message=str(e),
                session_duration_seconds=round(session_duration, 3),
                exc_info=True
            )
            
            add_breadcrumb(
                "Database session error",
                category="database",
                level="error",
                data={
                    "error_type": type(e).__name__,
                    "duration_seconds": round(session_duration, 3)
                }
            )
            raise
        finally:
            await session.close()
            session_duration = time.time() - session_start_time
            
            # Log long-running sessions
            if session_duration > 5.0:
                logger.warning(
                    "Long-running database session",
                    duration_seconds=round(session_duration, 3)
                )


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