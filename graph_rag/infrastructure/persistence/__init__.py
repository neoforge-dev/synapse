"""
Epic 20 Phase 1: PostgreSQL Infrastructure & Validation Framework

This module provides the infrastructure for migrating 17 SQLite databases
to 3 PostgreSQL databases with zero business disruption.

Architecture:
- models/: SQLAlchemy ORM models for all 3 databases
- repositories/: Data access layer for business operations
- validation/: Data validation and consistency checking framework
"""

from graph_rag.infrastructure.persistence.models.base import Base

__all__ = ["Base"]
