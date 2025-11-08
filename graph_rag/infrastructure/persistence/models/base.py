"""
Base SQLAlchemy model and database configuration for the consolidated PostgreSQL databases.
"""

from sqlalchemy.ext.declarative import declarative_base

# Create the base class for all models
Base = declarative_base()

# Database URLs for the three consolidated databases
DATABASE_URLS = {
    "business_crm": "postgresql+asyncpg://user:password@localhost/synapse_business_crm",
    "analytics_intelligence": "postgresql+asyncpg://user:password@localhost/synapse_analytics_intelligence",
    "system_infrastructure": "postgresql+asyncpg://user:password@localhost/synapse_system_infrastructure"
}

# Metadata for Alembic migrations
from sqlalchemy import MetaData

metadata = MetaData()
