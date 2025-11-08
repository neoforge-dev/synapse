"""Multi-tenant architecture components for Synapse Graph-RAG.

This module provides the core components for supporting multi-tenant deployments
with data isolation, white-label customization, and enterprise onboarding automation.
"""

from .data_isolation import IsolationLevel, TenantDataManager
from .resource_isolation import TenantResourceManager
from .tenant_lifecycle import TenantLifecycleManager
from .tenant_manager import TenantContext, TenantManager

__all__ = [
    'TenantManager',
    'TenantContext',
    'TenantDataManager',
    'IsolationLevel',
    'TenantResourceManager',
    'TenantLifecycleManager',
]
