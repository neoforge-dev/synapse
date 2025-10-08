# Epic 7 PostgreSQL Integration Tests

## Overview

Comprehensive integration test suite for Epic 7's $1.158M sales pipeline, validating end-to-end operations after Phase 3 PostgreSQL migration.

## Test Coverage

### 1. Contact Management Tests
- ✅ Create contact and verify persistence
- ✅ Retrieve contact by ID and email
- ✅ Update contact fields
- ✅ Delete contact
- ✅ Bulk contact import (10+ contacts)

### 2. Pipeline Integrity Tests (CRITICAL - $1.158M Protection)
- ✅ Create realistic $1.158M pipeline scenario
- ✅ Verify tier distribution (platinum/gold/silver/bronze)
- ✅ Preserve lead scores (0-100 range)
- ✅ Validate pipeline summary structure
- ✅ Calculate total pipeline value

### 3. Proposal Generation Tests
- ✅ Create proposal for qualified contact
- ✅ ROI calculation accuracy
- ✅ Proposal status workflow (draft→sent→accepted)
- ✅ Retrieve all proposals for contact

### 4. Revenue Forecasting Tests
- ✅ Annual forecast calculation
- ✅ Tier-based conversion rates:
  - Platinum: 65%
  - Gold: 45%
  - Silver: 30%
  - Bronze: 15%
- ✅ ARR target achievement ($2M target)
- ✅ Confidence interval validation (±25%)

### 5. Data Consistency Tests
- ✅ Transaction rollback on errors
- ✅ Duplicate email prevention
- ✅ Concurrent update handling

### 6. Performance Tests
- ✅ Contact query performance (<100ms)
- ✅ Pipeline aggregation performance (<500ms)
- ✅ Forecast calculation performance (<500ms)

## Database Configuration

The test suite automatically detects and uses the available database:

### Primary: PostgreSQL (Production-like)
```bash
# Set environment variables
export SYNAPSE_POSTGRES_HOST=localhost
export SYNAPSE_POSTGRES_PORT=5432
export SYNAPSE_POSTGRES_TEST_DB=synapse_business_crm_test
export SYNAPSE_POSTGRES_USER=postgres
export SYNAPSE_POSTGRES_PASSWORD=postgres

# Run tests
pytest tests/business/test_epic7_postgresql_integration.py -v
```

### Fallback: SQLite In-Memory (CI/CD)
- Automatically used when PostgreSQL is unavailable
- Uses cross-database compatibility layer
- Validates business logic without external dependencies
- Fast execution (<5s total)

```bash
# No configuration needed - auto-detects
pytest tests/business/test_epic7_postgresql_integration.py -v
```

## Running Tests

### All Epic 7 Integration Tests
```bash
pytest tests/business/test_epic7_postgresql_integration.py -v
```

### Specific Test Class
```bash
pytest tests/business/test_epic7_postgresql_integration.py::TestContactManagement -v
pytest tests/business/test_epic7_postgresql_integration.py::TestPipelineIntegrity -v
pytest tests/business/test_epic7_postgresql_integration.py::TestProposalGeneration -v
pytest tests/business/test_epic7_postgresql_integration.py::TestRevenueForecast -v
```

### Single Test
```bash
pytest tests/business/test_epic7_postgresql_integration.py::TestContactManagement::test_create_contact -v
```

### With Coverage
```bash
pytest tests/business/test_epic7_postgresql_integration.py --cov=graph_rag.services.crm_service --cov-report=html
```

## Expected Test Results

### Success Criteria
- ✅ 23 tests pass (100% pass rate)
- ✅ All queries complete <100ms
- ✅ All aggregations complete <500ms
- ✅ Pipeline value calculations accurate to 2 decimal places
- ✅ Zero data loss or corruption

### Test Execution Time
- PostgreSQL: ~5-10 seconds (full suite)
- SQLite: ~2-5 seconds (full suite)

## CI/CD Integration

### GitHub Actions
```yaml
- name: Run Epic 7 PostgreSQL Integration Tests
  run: |
    # Tests auto-fallback to SQLite in CI
    pytest tests/business/test_epic7_postgresql_integration.py -v --tb=short
  env:
    SYNAPSE_POSTGRES_HOST: localhost
    SYNAPSE_POSTGRES_PORT: 5432
```

### Local Development
```bash
# Quick validation (SQLite fallback)
make test-epic7-integration

# Full PostgreSQL testing (requires PostgreSQL running)
docker-compose up -d postgres
pytest tests/business/test_epic7_postgresql_integration.py -v
```

## Troubleshooting

### PostgreSQL Connection Issues
```bash
# Check PostgreSQL is running
pg_isready -h localhost -p 5432

# Create test database
createdb synapse_business_crm_test

# Verify connection
psql -h localhost -U postgres -d synapse_business_crm_test
```

### SQLite Fallback
If PostgreSQL is unavailable, tests automatically use SQLite:
```
=== Using SQLite (in-memory) for Epic 7 Integration Tests ===
    PostgreSQL not available. Tests will validate business logic
    using SQLite with cross-database compatibility layer.
```

### Test Failures
1. **"no such table" errors**: Database schema not created - check fixture execution
2. **Connection refused**: PostgreSQL not running - start service or use SQLite fallback
3. **Permission denied**: Check PostgreSQL user permissions

## Architecture Notes

### Cross-Database Compatibility
The test suite uses SQLAlchemy's type decorators for compatibility:
- `GUID`: PostgreSQL UUID ↔ SQLite CHAR(36)
- `JSONType`: PostgreSQL JSONB ↔ SQLite JSON

### Test Isolation
- Each test uses a clean database state
- PostgreSQL: Transaction rollback for isolation
- SQLite: In-memory database (recreated per session)

### Fixtures
- `test_db_engine`: Session-scoped engine (shared across tests)
- `crm_service`: Function-scoped CRM service (clean per test)
- `sample_contact_data`: Test data generator

## Related Documentation

- [DATABASE_MIGRATION_STATUS.md](../../DATABASE_MIGRATION_STATUS.md) - Migration progress
- [Epic 7 Sales Automation](../../business_development/epic7_sales_automation.py) - Source code
- [CRM Service](../../graph_rag/services/crm_service.py) - Service layer
- [CRM Models](../../graph_rag/infrastructure/persistence/models/crm.py) - Database models

## Maintenance

### Adding New Tests
1. Follow existing test patterns (AAA: Arrange, Act, Assert)
2. Use descriptive test names: `test_<feature>_<scenario>`
3. Add docstrings explaining business context
4. Update this README with new test coverage

### Updating for Schema Changes
1. Update CRM models in `models/crm.py`
2. Run migration: `alembic upgrade head`
3. Update test fixtures if needed
4. Verify all tests pass

---

**Status**: ✅ Comprehensive test suite ready for PostgreSQL validation
**Last Updated**: 2025-10-08
**Test Count**: 23 integration tests
**Coverage**: Contact, Pipeline, Proposals, Forecasting, Data Consistency, Performance
