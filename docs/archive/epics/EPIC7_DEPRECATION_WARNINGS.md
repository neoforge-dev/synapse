# Epic 7 SQLite Deprecation Warnings

## Overview

Added comprehensive deprecation warnings to Epic 7 Sales Automation to prevent accidental SQLite usage in production and guide developers toward the recommended PostgreSQL configuration.

## Changes Implemented

### 1. **Class-Level Documentation**
- Updated `SalesAutomationEngine` docstring to clearly indicate PostgreSQL is preferred
- Added prominent warnings about SQLite deprecation
- Documented `SYNAPSE_FORCE_POSTGRES` environment variable

### 2. **Constructor Deprecation Warning**
```python
def __init__(self, ..., use_postgres: bool = True):
    if not use_postgres:
        warnings.warn(
            "SQLite mode is deprecated and will be removed in a future version. "
            "Please use PostgreSQL by setting use_postgres=True (default). "
            "This mode is only maintained for backward compatibility with legacy code.",
            DeprecationWarning,
            stacklevel=2
        )
```

**Behavior:**
- Emits Python `DeprecationWarning` when `use_postgres=False`
- Logs warning message with ⚠️ emoji for visibility
- No warnings when using default `use_postgres=True`

### 3. **Environment Variable Enforcement**
```python
force_postgres = os.getenv("SYNAPSE_FORCE_POSTGRES", "").lower() in ("true", "1", "yes")

if not use_postgres and force_postgres:
    raise RuntimeError(
        "SQLite mode is disabled in this environment. "
        "SYNAPSE_FORCE_POSTGRES=true requires use_postgres=True. "
        "Please update your configuration to use PostgreSQL."
    )
```

**Behavior:**
- When `SYNAPSE_FORCE_POSTGRES=true`, SQLite mode raises `RuntimeError`
- Prevents accidental SQLite usage in production environments
- Clear error message guides developers to correct configuration

### 4. **SQLite Operation Logging**
Added `_log_sqlite_operation()` helper method that logs every SQLite database operation:

```python
def _log_sqlite_operation(self, operation: str, db_path: str):
    logger.warning(
        f"⚠️  DEPRECATED SQLite operation: {operation} "
        f"(database: {db_path}). "
        "Please migrate to PostgreSQL for production use."
    )
```

**Applied to:**
- `_init_database()` - Database initialization
- `_save_contacts()` - Contact persistence
- `generate_automated_proposal()` - Proposal generation
- `create_ab_test_campaign()` - A/B testing campaigns
- `assign_ab_test_variant()` - Variant assignment
- `analyze_ab_test_results()` - Results analysis
- `get_sales_pipeline_summary()` - Pipeline statistics
- `create_referral_automation_system()` - Referral automation
- `get_unified_dashboard_data()` - Dashboard data
- `populate_synthetic_consultation_data()` - Test data generation
- `import_consultation_inquiries()` - Inquiry imports

### 5. **Method Docstring Updates**
All SQLite-using methods now include deprecation notices:

```python
"""
Method description here.

DEPRECATED: This method uses SQLite and should only be used for legacy compatibility.
For production, use PostgreSQL via the CRM service layer.
"""
```

## Test Results

Run the test script to verify deprecation warnings:

```bash
uv run python test_deprecation_warnings.py
```

**Test Coverage:**
1. ✅ PostgreSQL mode (default) - No warnings
2. ✅ SQLite mode - DeprecationWarning emitted
3. ✅ Environment enforcement - RuntimeError when forced
4. ✅ SQLite operations - All logged with warnings

## Example Warning Output

### SQLite Mode Initialization
```
DeprecationWarning: SQLite mode is deprecated and will be removed in a future version.
Please use PostgreSQL by setting use_postgres=True (default).
This mode is only maintained for backward compatibility with legacy code.

WARNING - ⚠️  DEPRECATION WARNING: SQLite mode is deprecated.
Please migrate to PostgreSQL (use_postgres=True).

WARNING - ⚠️  Running in DEPRECATED SQLite-only mode (legacy)
```

### SQLite Operation Logging
```
WARNING - ⚠️  DEPRECATED SQLite operation: Database initialization
(database: business_development/epic7_sales_automation.db).
Please migrate to PostgreSQL for production use.
```

### Environment Enforcement
```
RuntimeError: SQLite mode is disabled in this environment.
SYNAPSE_FORCE_POSTGRES=true requires use_postgres=True.
Please update your configuration to use PostgreSQL.
```

## Recommended Production Configuration

### Environment Variables
```bash
export SYNAPSE_FORCE_POSTGRES=true
export SYNAPSE_POSTGRES_HOST=localhost
export SYNAPSE_POSTGRES_PORT=5432
export SYNAPSE_POSTGRES_DB=synapse_business_crm
export SYNAPSE_POSTGRES_USER=postgres
export SYNAPSE_POSTGRES_PASSWORD=secure_password
export SYNAPSE_POSTGRES_POOL_SIZE=10
```

### Code Usage
```python
# Recommended: Use default PostgreSQL mode
engine = SalesAutomationEngine()

# For testing with custom CRM service
from graph_rag.services.crm_service import CRMService, DatabaseConfig

db_config = DatabaseConfig(
    host="localhost",
    port=5432,
    database="synapse_business_crm",
    user="postgres",
    password="postgres"
)
crm_service = CRMService(db_config=db_config, use_async=False)
engine = SalesAutomationEngine(crm_service=crm_service, use_postgres=True)
```

## Migration Guide

### For Existing SQLite Users

1. **Update initialization:**
   ```python
   # OLD (deprecated)
   engine = SalesAutomationEngine(use_postgres=False)

   # NEW (recommended)
   engine = SalesAutomationEngine(use_postgres=True)
   ```

2. **Set environment variables** (see above)

3. **Monitor logs** for deprecation warnings during transition period

4. **Set enforcement** when ready:
   ```bash
   export SYNAPSE_FORCE_POSTGRES=true
   ```

### For New Projects

- Always use `use_postgres=True` (default)
- Set `SYNAPSE_FORCE_POSTGRES=true` in production
- Never explicitly set `use_postgres=False`

## Files Modified

1. **business_development/epic7_sales_automation.py**
   - Added `warnings` import
   - Updated class docstring
   - Enhanced `__init__` with deprecation warnings and enforcement
   - Added `_log_sqlite_operation()` helper method
   - Updated 11 method docstrings with deprecation notices
   - Added logging to 11 SQLite operations

2. **test_deprecation_warnings.py** (new)
   - Comprehensive test script demonstrating all warning types
   - Validates environment enforcement
   - Documents expected behavior

3. **EPIC7_DEPRECATION_WARNINGS.md** (this file)
   - Complete documentation of deprecation system
   - Migration guide for existing users
   - Production configuration examples

## Success Criteria

All requirements met:

- ✅ Deprecation warning shown when `use_postgres=False`
- ✅ No warnings when `use_postgres=True` (default)
- ✅ Environment variable enforcement works (`SYNAPSE_FORCE_POSTGRES=true`)
- ✅ SQLite operations logged with clear warnings
- ✅ Clear messaging guides users to PostgreSQL
- ✅ Updated docstrings indicate SQLite is legacy
- ✅ Backward compatibility maintained for transition period

## Future Work

- **Epic 20 Phase 3**: Complete code migration to remove SQLite entirely
- **Remove deprecation warnings**: Once all users migrated to PostgreSQL
- **Delete SQLite code paths**: After deprecation period (estimated Q2 2025)
