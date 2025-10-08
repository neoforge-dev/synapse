# Epic 16 Data Validation Tool - Usage Guide

## Overview

The Epic 16 validation tool provides **comprehensive data validation** to verify 100% migration accuracy and data integrity before PostgreSQL cutover. This tool ensures zero data loss and complete parity between SQLite and PostgreSQL databases.

## Installation

```bash
# Install required dependencies
uv pip install psycopg2-binary

# Ensure PostgreSQL is running and accessible
export POSTGRES_HOST=localhost
export POSTGRES_PORT=5432
export POSTGRES_DB=synapse_business_core
export POSTGRES_USER=synapse
export POSTGRES_PASSWORD=synapse_password
```

## Quick Start

```bash
# Full validation with detailed output
python database_migration/epic16_validation.py

# Quick validation (row counts only)
python database_migration/epic16_validation.py --quick

# JSON report output
python database_migration/epic16_validation.py --json > validation_report.json

# Validate specific table
python database_migration/epic16_validation.py --table f500_prospects
```

## Validation Checks

The tool performs **6 comprehensive validation checks**:

### 1. Row Count Validation
- **Requirement:** 100% match (0 tolerance)
- **Validates:** All 14 tables across 3 databases
- **Checks:** SQLite row count = PostgreSQL row count

**Example Output:**
```
✅ f500_prospects: 42 rows match
✅ f500_lead_scoring: 128 rows match
✅ f500_business_cases: 35 rows match
```

### 2. Foreign Key Integrity
- **Validates:** All foreign key references exist
- **Checks:** No orphaned records, cascade relationships intact
- **Tables Validated:**
  - Fortune 500: `f500_lead_scoring`, `f500_business_cases`, `f500_sales_sequences`, `f500_roi_tracking`
  - ABM: `abm_touchpoints`, `abm_performance`
  - Onboarding: `onboarding_milestones`, `onboarding_health_metrics`, `onboarding_communications`

**Example Output:**
```
✅ f500_lead_scoring.prospect_id → f500_prospects.prospect_id: No orphaned records
✅ f500_business_cases.prospect_id → f500_prospects.prospect_id: No orphaned records
```

### 3. JSON Structure Validation
- **Validates:** All JSONB columns have valid structure
- **Checks:** No NULL/invalid JSON, proper data types within JSON
- **Columns Validated:** 20+ JSONB columns across all tables

**Example Output:**
```
✅ f500_prospects.tech_stack: Valid JSON structure
✅ f500_prospects.decision_makers: Valid JSON structure
✅ f500_business_cases.roi_calculation: Valid JSON structure
```

### 4. Financial Calculation Validation
- **Validates:** ROI values, payback months, pipeline totals
- **Checks:** NUMERIC precision maintained (no REAL → NUMERIC loss)
- **Tolerance:** ±$0.01 for floating point precision

**Example Output:**
```
✅ ROI calculations match: 35 business cases, $4,250,000.00 total savings
✅ Pipeline values match: $12,500,000.00 pipeline, $3,200,000.00 revenue
```

### 5. Business Logic Validation
- **Validates:** Acquisition scores (0-100), health scores (0-100)
- **Checks:** Date ordering (created < updated), valid enum values
- **Rules Enforced:** 15+ business logic constraints

**Example Output:**
```
✅ f500_prospects.acquisition_score: All values satisfy business logic (0-100)
✅ f500_lead_scoring.confidence_level: All values satisfy business logic (0-1)
✅ abm_campaigns.campaign_status: All values in valid enum
✅ onboarding_clients: Date ordering is correct (created_at ≤ updated_at)
```

### 6. Sample Data Comparison
- **Validates:** Deep field-by-field comparison
- **Checks:** 5 random records per table (configurable)
- **Comparison:** All fields match exactly (type-aware comparison)

**Example Output:**
```
✅ f500_prospects: All 5 sampled records match perfectly
✅ f500_business_cases: All 5 sampled records match perfectly
✅ abm_campaigns: All 5 sampled records match perfectly
```

## Command-Line Options

### Full Validation (Default)
```bash
python database_migration/epic16_validation.py
```
- Runs all 6 validation checks
- Detailed console output with ✅/❌ status
- Validates all 14 tables across 3 databases
- Exit code: 0 (PASS) or 1 (FAIL)

### Quick Mode (Row Counts Only)
```bash
python database_migration/epic16_validation.py --quick
```
- Runs only row count validation
- Fast execution (< 10 seconds)
- Useful for CI/CD pipelines
- Exit code: 0 (PASS) or 1 (FAIL)

### JSON Report Output
```bash
python database_migration/epic16_validation.py --json > report.json
```
- Machine-readable JSON output
- Programmatic consumption
- Includes all validation results
- Exit code: 0 (PASS) or 1 (FAIL)

**JSON Report Structure:**
```json
{
  "validation_run": {
    "timestamp": "2025-10-08T12:34:56.789Z",
    "overall_status": "PASS",
    "mode": "full"
  },
  "summary": {
    "total_checks": 84,
    "passed": 84,
    "failed": 0,
    "warnings": 0
  },
  "recommendation": "PROCEED",
  "results": [
    {
      "check_name": "row_count_f500_prospects",
      "status": "PASS",
      "sqlite_value": 42,
      "postgres_value": 42,
      "details": "Table f500_prospects: SQLite=42, PostgreSQL=42",
      "timestamp": "2025-10-08T12:34:57.123Z"
    }
  ]
}
```

### Single Table Validation
```bash
python database_migration/epic16_validation.py --table f500_prospects
```
- Validates only the specified table
- Runs all 6 checks on that table
- Useful for focused debugging
- Exit code: 0 (PASS) or 1 (FAIL)

## Exit Codes

The tool uses standard Unix exit codes:

- **Exit Code 0:** All validations passed → **PROCEED with cutover**
- **Exit Code 1:** Validation failures detected → **ROLLBACK recommended**

## Example Usage Scenarios

### Pre-Migration Validation
```bash
# Before migrating data, validate schema is ready
python database_migration/epic16_validation.py --quick

# If row counts are 0, this is expected (no data migrated yet)
```

### Post-Migration Validation
```bash
# After data migration, run full validation
python database_migration/epic16_validation.py

# Expected output: All checks PASS
# Exit code: 0
```

### CI/CD Pipeline Integration
```bash
#!/bin/bash
# CI/CD validation script

# Run quick validation
python database_migration/epic16_validation.py --quick --json > validation.json

# Check exit code
if [ $? -eq 0 ]; then
  echo "✅ Validation passed - safe to deploy"
  exit 0
else
  echo "❌ Validation failed - rollback required"
  cat validation.json
  exit 1
fi
```

### Debugging Specific Table
```bash
# Investigate issue with specific table
python database_migration/epic16_validation.py --table f500_business_cases

# Review detailed field-by-field comparison
# Identify exact field mismatches
```

## Sample Output

### Successful Validation
```
======================================================================
Epic 16 Migration Validation Report
======================================================================
Started: 2025-10-08T12:34:56.789Z
Mode: Full

======================================================================
Validating FORTUNE500 Database
======================================================================

1. Row Count Validation
======================================================================
ℹ️  Validating fortune500 database tables...
✅ f500_prospects: 42 rows match
✅ f500_lead_scoring: 128 rows match
✅ f500_business_cases: 35 rows match
✅ f500_sales_sequences: 67 rows match
✅ f500_roi_tracking: 89 rows match

2. Foreign Key Integrity Validation
======================================================================
✅ f500_lead_scoring.prospect_id → f500_prospects.prospect_id: No orphaned records
✅ f500_business_cases.prospect_id → f500_prospects.prospect_id: No orphaned records
✅ f500_sales_sequences.prospect_id → f500_prospects.prospect_id: No orphaned records
✅ f500_roi_tracking.prospect_id → f500_prospects.prospect_id: No orphaned records

3. JSON Structure Validation
======================================================================
✅ f500_prospects.tech_stack: Valid JSON structure
✅ f500_prospects.decision_makers: Valid JSON structure
✅ f500_prospects.pain_points: Valid JSON structure
✅ f500_lead_scoring.scoring_rationale: Valid JSON structure
✅ f500_business_cases.roi_calculation: Valid JSON structure

4. Financial Calculation Validation
======================================================================
ℹ️  Validating ROI calculations in f500_business_cases...
✅ ROI calculations match: 35 business cases, $4,250,000.00 total savings
ℹ️  Validating pipeline values in f500_roi_tracking...
✅ Pipeline values match: $12,500,000.00 pipeline, $3,200,000.00 revenue

5. Business Logic Validation
======================================================================
✅ f500_prospects.acquisition_score: All values satisfy business logic
✅ f500_prospects.digital_transformation_score: All values satisfy business logic
✅ f500_lead_scoring.final_score: All values satisfy business logic
✅ f500_lead_scoring.confidence_level: All values satisfy business logic

6. Sample Data Comparison
======================================================================
ℹ️  Comparing 5 random records from each table...
✅ f500_prospects: All 5 sampled records match perfectly
✅ f500_lead_scoring: All 5 sampled records match perfectly
✅ f500_business_cases: All 5 sampled records match perfectly

======================================================================
VALIDATION SUMMARY REPORT
======================================================================
Total Checks: 84
✅ Passed: 84
❌ Failed: 0
⚠️  Warnings: 0
Duration: 12.45 seconds

----------------------------------------------------------------------
✅ Overall Status: PASS
✅ Recommendation: PROCEED with cutover
======================================================================
```

### Failed Validation (Example)
```
======================================================================
Epic 16 Migration Validation Report
======================================================================

1. Row Count Validation
======================================================================
✅ f500_prospects: 42 rows match
❌ f500_lead_scoring: SQLite=128, PostgreSQL=127 - MISMATCH
✅ f500_business_cases: 35 rows match

2. Foreign Key Integrity Validation
======================================================================
❌ f500_lead_scoring.prospect_id: 3 orphaned records

======================================================================
VALIDATION SUMMARY REPORT
======================================================================
Total Checks: 84
✅ Passed: 82
❌ Failed: 2
⚠️  Warnings: 0
Duration: 11.23 seconds

----------------------------------------------------------------------
❌ Overall Status: FAIL
❌ Recommendation: ROLLBACK - Fix issues before cutover
======================================================================
```

## Validation Coverage

### Tables Validated (14 Total)

**Fortune 500 Acquisition (5 tables):**
- `f500_prospects`
- `f500_lead_scoring`
- `f500_business_cases`
- `f500_sales_sequences`
- `f500_roi_tracking`

**ABM Campaigns (4 tables):**
- `abm_campaigns`
- `abm_content_assets`
- `abm_touchpoints`
- `abm_performance`

**Enterprise Onboarding (5 tables):**
- `onboarding_clients`
- `onboarding_milestones`
- `onboarding_health_metrics`
- `onboarding_success_templates`
- `onboarding_communications`

### Business Value Protected

- **Fortune 500 Pipeline:** $5M+ ARR potential
- **ABM Campaign ROI:** Critical marketing investment tracking
- **Enterprise Onboarding:** White-glove client success metrics

## Troubleshooting

### Issue: psycopg2 not available
```
Solution: Install psycopg2-binary
uv pip install psycopg2-binary
```

### Issue: Connection refused to PostgreSQL
```
Solution: Ensure PostgreSQL is running
docker-compose up -d postgres
# OR
pg_ctl start
```

### Issue: Database not found
```
Solution: Set environment variables
export POSTGRES_DB=synapse_business_core
export POSTGRES_HOST=localhost
export POSTGRES_PORT=5432
```

### Issue: Row count mismatch
```
Solution: Re-run migration
python database_migration/epic16_migration.py

Then re-validate:
python database_migration/epic16_validation.py
```

### Issue: Orphaned records detected
```
Solution: Check foreign key migration
1. Identify orphaned records in PostgreSQL
2. Verify parent records exist in SQLite
3. Re-run migration with proper FK handling
```

## Integration with Migration Workflow

### Recommended Migration Workflow

```bash
# Step 1: Pre-migration validation (expect 0 rows)
python database_migration/epic16_validation.py --quick

# Step 2: Run migration
python database_migration/epic16_migration.py

# Step 3: Post-migration validation (full)
python database_migration/epic16_validation.py

# Step 4: Check exit code
if [ $? -eq 0 ]; then
  echo "✅ Safe to cutover to PostgreSQL"
else
  echo "❌ Issues detected - rollback required"
fi

# Step 5: Enable dual-write (if validation passes)
python database_migration/epic16_dual_write.py --enable

# Step 6: 7-day monitoring with hourly validation
for i in {1..168}; do
  sleep 3600
  python database_migration/epic16_validation.py --quick
done

# Step 7: Final cutover
python database_migration/epic16_cutover.py
```

## Performance

- **Quick mode:** < 10 seconds (row counts only)
- **Full validation:** 10-30 seconds (depends on data volume)
- **Sample size:** Configurable (default: 5 records per table)

## Best Practices

1. **Run quick validation frequently** during dual-write period (hourly)
2. **Run full validation** before cutover decision
3. **Save JSON reports** for audit trail and compliance
4. **Validate incrementally** during large migrations (--table flag)
5. **Monitor exit codes** in automated pipelines
6. **Review warnings** even if overall status is PASS

## Support

For issues or questions:
- Review DATABASE_MIGRATION_STATUS.md for migration context
- Check EPIC16_MIGRATION_PLAN.md for detailed migration strategy
- Consult validation logs for specific error details

## License

Part of Synapse Graph-RAG platform - internal tool for database migration validation.
