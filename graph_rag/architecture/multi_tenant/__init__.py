"""Multi-tenant architecture components for Synapse Graph-RAG.

This module provides the core components for supporting multi-tenant deployments
with data isolation, white-label customization, and enterprise onboarding automation.
"""

from .tenant_manager import TenantManager, TenantContext
from .data_isolation import TenantDataManager, IsolationLevel
from .resource_isolation import TenantResourceManager
from .tenant_lifecycle import TenantLifecycleManager

__all__ = [
    'TenantManager',
    'TenantContext', 
    'TenantDataManager',
    'IsolationLevel',
    'TenantResourceManager',
    'TenantLifecycleManager',
]