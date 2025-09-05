"""
Epic 10 System Consolidation Validation Test Suite

This package provides comprehensive validation testing for Epic 10 system
consolidation completion and enterprise readiness verification.
"""

from .test_epic10_system_validation import Epic10ValidationFramework
from .test_database_consolidation import DatabaseConsolidationValidator
from .test_epic7_pipeline_protection import Epic7PipelineValidator
from .test_enterprise_readiness import EnterpriseReadinessValidator
from .test_comprehensive_regression import ComprehensiveRegressionValidator

__all__ = [
    "Epic10ValidationFramework",
    "DatabaseConsolidationValidator", 
    "Epic7PipelineValidator",
    "EnterpriseReadinessValidator",
    "ComprehensiveRegressionValidator"
]