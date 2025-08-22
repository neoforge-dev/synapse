#!/usr/bin/env python3
"""
Database initialization script for TechLead AutoPilot.

Creates the database, runs migrations, and sets up initial data.
"""

import asyncio
import logging
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError

from techlead_autopilot.config import get_settings
from techlead_autopilot.infrastructure.database.session import init_database

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def create_database_if_not_exists():
    """Create the database if it doesn't exist."""
    settings = get_settings()
    
    # Parse database URL to get components
    db_url = settings.database_url
    if "postgresql://" in db_url:
        parts = db_url.replace("postgresql://", "").split("/")
        db_name = parts[-1].split("?")[0]  # Remove any query parameters
        base_url = db_url.replace(f"/{db_name}", "/postgres")
        
        try:
            # Connect to postgres database to create our database
            engine = create_engine(base_url)
            with engine.connect() as conn:
                # Set autocommit mode for CREATE DATABASE
                conn.execute(text("COMMIT"))
                
                # Check if database exists
                result = conn.execute(
                    text("SELECT 1 FROM pg_database WHERE datname = :db_name"),
                    {"db_name": db_name}
                )
                
                if not result.fetchone():
                    # Create database
                    conn.execute(text(f'CREATE DATABASE "{db_name}"'))
                    logger.info(f"Created database: {db_name}")
                else:
                    logger.info(f"Database already exists: {db_name}")
            
        except OperationalError as e:
            logger.error(f"Failed to create database: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error creating database: {e}")
            return False
    
    return True


def run_migrations():
    """Run Alembic migrations."""
    try:
        # Get Alembic config
        alembic_cfg = Config("alembic.ini")
        
        # Run migrations
        logger.info("Running database migrations...")
        command.upgrade(alembic_cfg, "head")
        logger.info("Database migrations completed successfully")
        
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        return False
    
    return True


async def create_initial_data():
    """Create initial data for the application."""
    try:
        # Initialize database connection
        await init_database()
        
        logger.info("Database initialization completed")
        
        # TODO: Add initial data creation here if needed
        # For example, create default organization, admin user, etc.
        
    except Exception as e:
        logger.error(f"Failed to create initial data: {e}")
        return False
    
    return True


async def main():
    """Main initialization function."""
    logger.info("Starting TechLead AutoPilot database initialization...")
    
    # Step 1: Create database if it doesn't exist
    if not create_database_if_not_exists():
        logger.error("Database creation failed")
        return False
    
    # Step 2: Run migrations
    if not run_migrations():
        logger.error("Migration failed")
        return False
    
    # Step 3: Create initial data
    if not await create_initial_data():
        logger.error("Initial data creation failed")
        return False
    
    logger.info("Database initialization completed successfully!")
    return True


if __name__ == "__main__":
    success = asyncio.run(main())
    if not success:
        sys.exit(1)