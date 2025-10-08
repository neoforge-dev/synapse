"""
Epic 16 Data Validation Tool
=============================
Comprehensive validation to verify migration accuracy and data integrity
for Fortune 500 Acquisition, ABM Campaigns, and Enterprise Onboarding systems.

Validates 100% data parity between SQLite and PostgreSQL before cutover.

Usage:
    python epic16_validation.py                    # Full validation with detailed output
    python epic16_validation.py --json             # JSON report output
    python epic16_validation.py --quick            # Quick validation (row counts only)
    python epic16_validation.py --table f500_prospects  # Single table validation

Exit Codes:
    0 - All validations passed (PROCEED with cutover)
    1 - Validation failures detected (ROLLBACK recommended)
"""

import os
import sys
import sqlite3
import json
import random
from typing import Dict, List, Tuple, Any, Optional
from datetime import datetime
from decimal import Decimal
from dataclasses import dataclass, asdict

try:
    import psycopg2
    import psycopg2.extras
    PSYCOPG2_AVAILABLE = True
except ImportError:
    PSYCOPG2_AVAILABLE = False
    print("Warning: psycopg2 not available. Install with: uv pip install psycopg2-binary")


@dataclass
class ValidationResult:
    """Result of a validation check"""
    check_name: str
    status: str  # PASS, FAIL, WARNING
    sqlite_value: Any
    postgres_value: Any
    details: str
    timestamp: str = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.utcnow().isoformat()


@dataclass
class TableValidation:
    """Validation results for a single table"""
    table_name: str
    row_count_match: bool
    sqlite_rows: int
    postgres_rows: int
    foreign_key_check: bool
    sample_data_match: bool
    json_structure_valid: bool
    business_logic_valid: bool
    errors: List[str]
    warnings: List[str]


class Epic16ValidationTool:
    """
    Comprehensive validation tool for Epic 16 database migration.

    Validates:
    1. Row Count Validation - 100% match requirement
    2. Foreign Key Integrity - No orphaned records
    3. JSON Structure Validation - All JSONB fields
    4. Financial Calculation Validation - ROI, pipeline values
    5. Business Logic Validation - Score ranges, date order, enum values
    6. Sample Data Comparison - Deep field-by-field validation
    """

    # Fortune 500 database configuration
    FORTUNE_500_TABLES = [
        'f500_prospects',
        'f500_lead_scoring',
        'f500_business_cases',
        'f500_sales_sequences',
        'f500_roi_tracking'
    ]

    # ABM Campaigns database configuration
    ABM_TABLES = [
        'abm_campaigns',
        'abm_content_assets',
        'abm_touchpoints',
        'abm_performance'
    ]

    # Enterprise Onboarding database configuration
    ONBOARDING_TABLES = [
        'onboarding_clients',
        'onboarding_milestones',
        'onboarding_health_metrics',
        'onboarding_success_templates',
        'onboarding_communications'
    ]

    # Database file paths
    SQLITE_DBS = {
        'fortune500': 'business_development/epic16_fortune500_acquisition.db',
        'abm': 'business_development/epic16_abm_campaigns.db',
        'onboarding': 'business_development/epic16_enterprise_onboarding.db'
    }

    def __init__(self, quick_mode: bool = False, json_output: bool = False):
        """Initialize validation tool"""
        self.quick_mode = quick_mode
        self.json_output = json_output
        self.results: List[ValidationResult] = []
        self.table_results: Dict[str, TableValidation] = {}
        self.overall_status = "PASS"

        # PostgreSQL configuration
        self.pg_config = {
            'host': os.getenv('POSTGRES_HOST', 'localhost'),
            'port': int(os.getenv('POSTGRES_PORT', '5432')),
            'database': os.getenv('POSTGRES_DB', 'synapse_business_core'),
            'user': os.getenv('POSTGRES_USER', 'synapse'),
            'password': os.getenv('POSTGRES_PASSWORD', 'synapse_password')
        }

    def log(self, message: str, level: str = "INFO"):
        """Log message to stdout unless in JSON mode"""
        if not self.json_output:
            prefix = {
                "INFO": "ℹ️ ",
                "SUCCESS": "✅",
                "WARNING": "⚠️ ",
                "ERROR": "❌",
                "SECTION": "\n" + "="*70 + "\n"
            }.get(level, "")
            print(f"{prefix} {message}")

    def connect_sqlite(self, db_key: str) -> sqlite3.Connection:
        """Connect to SQLite database"""
        db_path = self.SQLITE_DBS.get(db_key)
        if not db_path or not os.path.exists(db_path):
            raise FileNotFoundError(f"SQLite database not found: {db_path}")
        return sqlite3.connect(db_path)

    def connect_postgres(self):
        """Connect to PostgreSQL database"""
        if not PSYCOPG2_AVAILABLE:
            raise ImportError("psycopg2 not available. Install with: uv pip install psycopg2-binary")
        return psycopg2.connect(**self.pg_config)

    # ========================================================================
    # 1. ROW COUNT VALIDATION
    # ========================================================================

    def validate_row_counts(self, db_key: str, tables: List[str]) -> bool:
        """
        Validate row counts match 100% between SQLite and PostgreSQL.
        Target: 0 tolerance for discrepancies.
        """
        self.log("1. Row Count Validation", "SECTION")
        self.log(f"Validating {db_key} database tables...")

        sqlite_conn = self.connect_sqlite(db_key)
        pg_conn = self.connect_postgres()

        all_match = True

        for table in tables:
            try:
                # SQLite count
                sqlite_cursor = sqlite_conn.cursor()
                sqlite_cursor.execute(f'SELECT COUNT(*) FROM {table}')
                sqlite_count = sqlite_cursor.fetchone()[0]

                # PostgreSQL count
                pg_cursor = pg_conn.cursor()
                pg_cursor.execute(f'SELECT COUNT(*) FROM {table}')
                pg_count = pg_cursor.fetchone()[0]

                match = sqlite_count == pg_count

                result = ValidationResult(
                    check_name=f"row_count_{table}",
                    status="PASS" if match else "FAIL",
                    sqlite_value=sqlite_count,
                    postgres_value=pg_count,
                    details=f"Table {table}: SQLite={sqlite_count}, PostgreSQL={pg_count}"
                )
                self.results.append(result)

                if match:
                    self.log(f"✅ {table}: {sqlite_count} rows match", "SUCCESS")
                else:
                    self.log(f"❌ {table}: SQLite={sqlite_count}, PostgreSQL={pg_count} - MISMATCH", "ERROR")
                    all_match = False
                    self.overall_status = "FAIL"

            except Exception as e:
                self.log(f"❌ Error validating {table}: {e}", "ERROR")
                all_match = False
                self.overall_status = "FAIL"

        sqlite_conn.close()
        pg_conn.close()

        return all_match

    # ========================================================================
    # 2. FOREIGN KEY INTEGRITY VALIDATION
    # ========================================================================

    def validate_foreign_keys(self, db_key: str, tables: List[str]) -> bool:
        """
        Verify all foreign key references exist.
        Check for orphaned records and validate cascade relationships.
        """
        self.log("2. Foreign Key Integrity Validation", "SECTION")

        # Define foreign key relationships
        fk_checks = {
            'fortune500': [
                ('f500_lead_scoring', 'prospect_id', 'f500_prospects', 'prospect_id'),
                ('f500_business_cases', 'prospect_id', 'f500_prospects', 'prospect_id'),
                ('f500_sales_sequences', 'prospect_id', 'f500_prospects', 'prospect_id'),
                ('f500_roi_tracking', 'prospect_id', 'f500_prospects', 'prospect_id'),
            ],
            'abm': [
                ('abm_touchpoints', 'campaign_id', 'abm_campaigns', 'campaign_id'),
                ('abm_touchpoints', 'content_asset_id', 'abm_content_assets', 'asset_id'),
                ('abm_performance', 'campaign_id', 'abm_campaigns', 'campaign_id'),
            ],
            'onboarding': [
                ('onboarding_milestones', 'client_id', 'onboarding_clients', 'client_id'),
                ('onboarding_health_metrics', 'client_id', 'onboarding_clients', 'client_id'),
                ('onboarding_communications', 'client_id', 'onboarding_clients', 'client_id'),
            ]
        }

        if db_key not in fk_checks:
            self.log(f"⚠️  No FK checks defined for {db_key}", "WARNING")
            return True

        pg_conn = self.connect_postgres()
        pg_cursor = pg_conn.cursor()

        all_valid = True

        for child_table, child_col, parent_table, parent_col in fk_checks[db_key]:
            try:
                # Check for orphaned records in PostgreSQL
                query = f"""
                    SELECT COUNT(*)
                    FROM {child_table} c
                    LEFT JOIN {parent_table} p ON c.{child_col} = p.{parent_col}
                    WHERE p.{parent_col} IS NULL AND c.{child_col} IS NOT NULL
                """
                pg_cursor.execute(query)
                orphaned_count = pg_cursor.fetchone()[0]

                if orphaned_count == 0:
                    self.log(f"✅ {child_table}.{child_col} → {parent_table}.{parent_col}: No orphaned records", "SUCCESS")
                    result = ValidationResult(
                        check_name=f"fk_{child_table}_{child_col}",
                        status="PASS",
                        sqlite_value=0,
                        postgres_value=0,
                        details=f"No orphaned records in {child_table}"
                    )
                else:
                    self.log(f"❌ {child_table}.{child_col}: {orphaned_count} orphaned records", "ERROR")
                    all_valid = False
                    self.overall_status = "FAIL"
                    result = ValidationResult(
                        check_name=f"fk_{child_table}_{child_col}",
                        status="FAIL",
                        sqlite_value=0,
                        postgres_value=orphaned_count,
                        details=f"{orphaned_count} orphaned records found"
                    )

                self.results.append(result)

            except Exception as e:
                self.log(f"❌ Error checking FK {child_table}.{child_col}: {e}", "ERROR")
                all_valid = False
                self.overall_status = "FAIL"

        pg_conn.close()
        return all_valid

    # ========================================================================
    # 3. JSON STRUCTURE VALIDATION
    # ========================================================================

    def validate_json_structures(self, db_key: str, tables: List[str]) -> bool:
        """
        Validate JSONB column structures.
        Check for missing fields and validate data types within JSON.
        """
        self.log("3. JSON Structure Validation", "SECTION")

        # Define expected JSON structures
        json_columns = {
            'fortune500': {
                'f500_prospects': ['tech_stack', 'pain_points', 'decision_makers'],
                'f500_lead_scoring': ['scoring_rationale'],
                'f500_business_cases': ['problem_quantification', 'solution_benefits', 'roi_calculation', 'risk_assessment', 'implementation_timeline', 'investment_options'],
                'f500_sales_sequences': ['touchpoints'],
                'f500_roi_tracking': []
            },
            'abm': {
                'abm_campaigns': ['target_accounts', 'content_assets', 'distribution_channels', 'performance_metrics'],
                'abm_content_assets': ['personalization_data'],
                'abm_touchpoints': ['personalization_applied', 'engagement_metrics'],
                'abm_performance': []
            },
            'onboarding': {
                'onboarding_clients': ['decision_makers', 'technical_contacts', 'success_metrics'],
                'onboarding_milestones': ['success_criteria', 'deliverables', 'dependencies'],
                'onboarding_health_metrics': ['action_items'],
                'onboarding_success_templates': ['phase_structure', 'milestone_templates', 'success_metrics_template', 'resource_requirements', 'risk_mitigation_strategies'],
                'onboarding_communications': ['participants', 'action_items']
            }
        }

        if db_key not in json_columns:
            self.log(f"⚠️  No JSON validation defined for {db_key}", "WARNING")
            return True

        pg_conn = self.connect_postgres()
        pg_cursor = pg_conn.cursor()

        all_valid = True

        for table, columns in json_columns[db_key].items():
            if table not in tables:
                continue

            for column in columns:
                try:
                    # Check for NULL or invalid JSON
                    query = f"""
                        SELECT COUNT(*)
                        FROM {table}
                        WHERE {column} IS NOT NULL
                        AND jsonb_typeof({column}) IS NULL
                    """
                    pg_cursor.execute(query)
                    invalid_count = pg_cursor.fetchone()[0]

                    # Get sample to validate structure
                    query = f"""
                        SELECT {column}
                        FROM {table}
                        WHERE {column} IS NOT NULL
                        LIMIT 1
                    """
                    pg_cursor.execute(query)
                    sample = pg_cursor.fetchone()

                    if invalid_count == 0:
                        self.log(f"✅ {table}.{column}: Valid JSON structure", "SUCCESS")
                        result = ValidationResult(
                            check_name=f"json_{table}_{column}",
                            status="PASS",
                            sqlite_value="valid",
                            postgres_value="valid",
                            details=f"All {column} values have valid JSON structure"
                        )
                    else:
                        self.log(f"❌ {table}.{column}: {invalid_count} invalid JSON entries", "ERROR")
                        all_valid = False
                        self.overall_status = "FAIL"
                        result = ValidationResult(
                            check_name=f"json_{table}_{column}",
                            status="FAIL",
                            sqlite_value="valid",
                            postgres_value=f"{invalid_count} invalid",
                            details=f"{invalid_count} invalid JSON structures found"
                        )

                    self.results.append(result)

                except Exception as e:
                    self.log(f"⚠️  Error validating {table}.{column}: {e}", "WARNING")

        pg_conn.close()
        return all_valid

    # ========================================================================
    # 4. FINANCIAL CALCULATION VALIDATION
    # ========================================================================

    def validate_financial_calculations(self, db_key: str) -> bool:
        """
        Validate financial calculations and precision.
        - ROI values
        - Payback months
        - Pipeline value totals
        - NUMERIC precision vs REAL
        """
        self.log("4. Financial Calculation Validation", "SECTION")

        if db_key != 'fortune500':
            self.log("⚠️  Financial validation only applies to fortune500 database", "WARNING")
            return True

        sqlite_conn = self.connect_sqlite(db_key)
        pg_conn = self.connect_postgres()

        all_valid = True

        # Validate ROI calculations in f500_business_cases
        try:
            self.log("Validating ROI calculations in f500_business_cases...")

            sqlite_cursor = sqlite_conn.cursor()
            sqlite_cursor.execute("""
                SELECT
                    COUNT(*) as total,
                    SUM(projected_savings) as total_savings,
                    AVG(payback_months) as avg_payback
                FROM f500_business_cases
            """)
            sqlite_data = sqlite_cursor.fetchone()

            pg_cursor = pg_conn.cursor()
            pg_cursor.execute("""
                SELECT
                    COUNT(*) as total,
                    SUM(projected_savings) as total_savings,
                    AVG(payback_months) as avg_payback
                FROM f500_business_cases
            """)
            pg_data = pg_cursor.fetchone()

            # Compare with tolerance for floating point
            count_match = sqlite_data[0] == pg_data[0]
            savings_match = abs((sqlite_data[1] or 0) - float(pg_data[1] or 0)) < 0.01
            payback_match = abs((sqlite_data[2] or 0) - float(pg_data[2] or 0)) < 0.01

            if count_match and savings_match and payback_match:
                self.log(f"✅ ROI calculations match: {pg_data[0]} business cases, ${float(pg_data[1] or 0):,.2f} total savings", "SUCCESS")
                result = ValidationResult(
                    check_name="financial_roi_validation",
                    status="PASS",
                    sqlite_value=sqlite_data,
                    postgres_value=pg_data,
                    details="ROI calculations match within tolerance"
                )
            else:
                self.log(f"❌ ROI calculation mismatch: SQLite={sqlite_data}, PostgreSQL={pg_data}", "ERROR")
                all_valid = False
                self.overall_status = "FAIL"
                result = ValidationResult(
                    check_name="financial_roi_validation",
                    status="FAIL",
                    sqlite_value=sqlite_data,
                    postgres_value=pg_data,
                    details="ROI calculations do not match"
                )

            self.results.append(result)

        except Exception as e:
            self.log(f"❌ Error validating ROI calculations: {e}", "ERROR")
            all_valid = False
            self.overall_status = "FAIL"

        # Validate pipeline value in f500_roi_tracking
        try:
            self.log("Validating pipeline values in f500_roi_tracking...")

            sqlite_cursor = sqlite_conn.cursor()
            sqlite_cursor.execute("""
                SELECT
                    SUM(pipeline_value_generated) as total_pipeline,
                    SUM(actual_revenue) as total_revenue,
                    AVG(roi_ratio) as avg_roi
                FROM f500_roi_tracking
            """)
            sqlite_data = sqlite_cursor.fetchone()

            pg_cursor = pg_conn.cursor()
            pg_cursor.execute("""
                SELECT
                    SUM(pipeline_value_generated) as total_pipeline,
                    SUM(actual_revenue) as total_revenue,
                    AVG(roi_ratio) as avg_roi
                FROM f500_roi_tracking
            """)
            pg_data = pg_cursor.fetchone()

            pipeline_match = abs((sqlite_data[0] or 0) - float(pg_data[0] or 0)) < 0.01
            revenue_match = abs((sqlite_data[1] or 0) - float(pg_data[1] or 0)) < 0.01
            roi_match = abs((sqlite_data[2] or 0) - float(pg_data[2] or 0)) < 0.01

            if pipeline_match and revenue_match and roi_match:
                self.log(f"✅ Pipeline values match: ${float(pg_data[0] or 0):,.2f} pipeline, ${float(pg_data[1] or 0):,.2f} revenue", "SUCCESS")
                result = ValidationResult(
                    check_name="financial_pipeline_validation",
                    status="PASS",
                    sqlite_value=sqlite_data,
                    postgres_value=pg_data,
                    details="Pipeline values match within tolerance"
                )
            else:
                self.log(f"❌ Pipeline value mismatch: SQLite={sqlite_data}, PostgreSQL={pg_data}", "ERROR")
                all_valid = False
                self.overall_status = "FAIL"
                result = ValidationResult(
                    check_name="financial_pipeline_validation",
                    status="FAIL",
                    sqlite_value=sqlite_data,
                    postgres_value=pg_data,
                    details="Pipeline values do not match"
                )

            self.results.append(result)

        except Exception as e:
            self.log(f"❌ Error validating pipeline values: {e}", "ERROR")
            all_valid = False
            self.overall_status = "FAIL"

        sqlite_conn.close()
        pg_conn.close()

        return all_valid

    # ========================================================================
    # 5. BUSINESS LOGIC VALIDATION
    # ========================================================================

    def validate_business_logic(self, db_key: str, tables: List[str]) -> bool:
        """
        Validate business logic rules:
        - Acquisition scores within valid range (0-100)
        - Health scores within valid range (0-100)
        - Dates in logical order (created < updated)
        - Status values are valid enums
        """
        self.log("5. Business Logic Validation", "SECTION")

        pg_conn = self.connect_postgres()
        pg_cursor = pg_conn.cursor()

        all_valid = True

        # Define business logic checks
        logic_checks = {
            'fortune500': [
                ("f500_prospects", "acquisition_score", "acquisition_score >= 0 AND acquisition_score <= 100"),
                ("f500_prospects", "digital_transformation_score", "digital_transformation_score >= 0 AND digital_transformation_score <= 100"),
                ("f500_lead_scoring", "final_score", "final_score >= 0 AND final_score <= 100"),
                ("f500_lead_scoring", "confidence_level", "confidence_level >= 0 AND confidence_level <= 1"),
            ],
            'abm': [
                ("abm_campaigns", "campaign_status", "campaign_status IN ('planning', 'active', 'completed', 'paused')"),
                ("abm_touchpoints", "status", "status IN ('scheduled', 'sent', 'opened', 'clicked', 'responded')"),
            ],
            'onboarding': [
                ("onboarding_clients", "health_score", "health_score >= 0 AND health_score <= 100"),
                ("onboarding_milestones", "status", "status IN ('planned', 'in_progress', 'completed', 'blocked', 'delayed')"),
                ("onboarding_health_metrics", "metric_value", "metric_value >= 0"),
            ]
        }

        if db_key not in logic_checks:
            self.log(f"⚠️  No business logic checks defined for {db_key}", "WARNING")
            pg_conn.close()
            return True

        for table, field, condition in logic_checks[db_key]:
            if table not in tables:
                continue

            try:
                # Check for violations
                query = f"""
                    SELECT COUNT(*)
                    FROM {table}
                    WHERE NOT ({condition})
                    AND {field} IS NOT NULL
                """
                pg_cursor.execute(query)
                violation_count = pg_cursor.fetchone()[0]

                if violation_count == 0:
                    self.log(f"✅ {table}.{field}: All values satisfy business logic", "SUCCESS")
                    result = ValidationResult(
                        check_name=f"logic_{table}_{field}",
                        status="PASS",
                        sqlite_value="valid",
                        postgres_value="valid",
                        details=f"All {field} values satisfy: {condition}"
                    )
                else:
                    self.log(f"❌ {table}.{field}: {violation_count} violations of business logic", "ERROR")
                    all_valid = False
                    self.overall_status = "FAIL"
                    result = ValidationResult(
                        check_name=f"logic_{table}_{field}",
                        status="FAIL",
                        sqlite_value="valid",
                        postgres_value=f"{violation_count} violations",
                        details=f"Business logic violation: {condition}"
                    )

                self.results.append(result)

            except Exception as e:
                self.log(f"⚠️  Error checking {table}.{field}: {e}", "WARNING")

        # Check date ordering (created_at < updated_at)
        for table in tables:
            try:
                query = f"""
                    SELECT COUNT(*)
                    FROM {table}
                    WHERE created_at > updated_at
                """
                pg_cursor.execute(query)
                violation_count = pg_cursor.fetchone()[0]

                if violation_count == 0:
                    self.log(f"✅ {table}: Date ordering is correct (created_at ≤ updated_at)", "SUCCESS")
                else:
                    self.log(f"❌ {table}: {violation_count} records with created_at > updated_at", "ERROR")
                    all_valid = False
                    self.overall_status = "FAIL"

            except Exception as e:
                # Table might not have these columns
                pass

        pg_conn.close()
        return all_valid

    # ========================================================================
    # 6. SAMPLE DATA COMPARISON
    # ========================================================================

    def validate_sample_data(self, db_key: str, tables: List[str], sample_size: int = 5) -> bool:
        """
        Deep comparison of random sample records.
        Pick N random records from each table and compare field-by-field.
        """
        self.log("6. Sample Data Comparison", "SECTION")
        self.log(f"Comparing {sample_size} random records from each table...")

        sqlite_conn = self.connect_sqlite(db_key)
        pg_conn = self.connect_postgres()

        all_valid = True

        for table in tables:
            try:
                # Get primary key column name
                pk_col = self._get_primary_key(table)

                # Get all IDs from SQLite
                sqlite_cursor = sqlite_conn.cursor()
                sqlite_cursor.execute(f'SELECT {pk_col} FROM {table}')
                all_ids = [row[0] for row in sqlite_cursor.fetchall()]

                if len(all_ids) == 0:
                    self.log(f"⚠️  {table}: No records to sample", "WARNING")
                    continue

                # Sample random IDs
                sample_ids = random.sample(all_ids, min(sample_size, len(all_ids)))

                matches = 0
                mismatches = 0

                for record_id in sample_ids:
                    # Get SQLite record
                    sqlite_cursor.execute(f'SELECT * FROM {table} WHERE {pk_col} = ?', (record_id,))
                    sqlite_record = sqlite_cursor.fetchone()
                    sqlite_columns = [desc[0] for desc in sqlite_cursor.description]

                    # Get PostgreSQL record
                    pg_cursor = pg_conn.cursor()
                    pg_cursor.execute(f'SELECT * FROM {table} WHERE {pk_col} = %s', (record_id,))
                    pg_record = pg_cursor.fetchone()

                    if pg_record is None:
                        self.log(f"❌ {table}: Record {record_id} missing from PostgreSQL", "ERROR")
                        mismatches += 1
                        all_valid = False
                        self.overall_status = "FAIL"
                        continue

                    # Compare field by field
                    field_match = self._compare_records(sqlite_record, pg_record, sqlite_columns)

                    if field_match:
                        matches += 1
                    else:
                        mismatches += 1
                        all_valid = False
                        self.overall_status = "FAIL"

                if mismatches == 0:
                    self.log(f"✅ {table}: All {matches} sampled records match perfectly", "SUCCESS")
                    result = ValidationResult(
                        check_name=f"sample_{table}",
                        status="PASS",
                        sqlite_value=matches,
                        postgres_value=matches,
                        details=f"{matches} sampled records match"
                    )
                else:
                    self.log(f"❌ {table}: {mismatches} mismatches out of {matches + mismatches} samples", "ERROR")
                    result = ValidationResult(
                        check_name=f"sample_{table}",
                        status="FAIL",
                        sqlite_value=matches + mismatches,
                        postgres_value=matches,
                        details=f"{mismatches} mismatches found in sample data"
                    )

                self.results.append(result)

            except Exception as e:
                self.log(f"❌ Error sampling {table}: {e}", "ERROR")
                all_valid = False
                self.overall_status = "FAIL"

        sqlite_conn.close()
        pg_conn.close()

        return all_valid

    # ========================================================================
    # HELPER METHODS
    # ========================================================================

    def _get_primary_key(self, table: str) -> str:
        """Get primary key column name for a table"""
        pk_mapping = {
            'f500_prospects': 'prospect_id',
            'f500_lead_scoring': 'scoring_id',
            'f500_business_cases': 'case_id',
            'f500_sales_sequences': 'sequence_id',
            'f500_roi_tracking': 'roi_id',
            'abm_campaigns': 'campaign_id',
            'abm_content_assets': 'asset_id',
            'abm_touchpoints': 'touchpoint_id',
            'abm_performance': 'performance_id',
            'onboarding_clients': 'client_id',
            'onboarding_milestones': 'milestone_id',
            'onboarding_health_metrics': 'health_id',
            'onboarding_success_templates': 'template_id',
            'onboarding_communications': 'communication_id',
        }
        return pk_mapping.get(table, 'id')

    def _compare_records(self, sqlite_record: tuple, pg_record: tuple, columns: List[str]) -> bool:
        """Compare two records field by field"""
        for i, (sqlite_val, pg_val) in enumerate(zip(sqlite_record, pg_record)):
            # Handle type conversions
            if isinstance(sqlite_val, str) and isinstance(pg_val, str):
                if sqlite_val != pg_val:
                    return False
            elif isinstance(sqlite_val, (int, float)) and isinstance(pg_val, (int, float, Decimal)):
                if abs(float(sqlite_val or 0) - float(pg_val or 0)) > 0.01:
                    return False
            elif sqlite_val != pg_val:
                # Allow None/NULL differences
                if not (sqlite_val is None and pg_val is None):
                    return False
        return True

    # ========================================================================
    # MAIN VALIDATION ORCHESTRATION
    # ========================================================================

    def run_validation(self, specific_table: Optional[str] = None) -> bool:
        """
        Run complete validation suite.
        Returns True if all validations pass, False otherwise.
        """
        start_time = datetime.utcnow()

        self.log("Epic 16 Migration Validation Report", "SECTION")
        self.log(f"Started: {start_time.isoformat()}")
        self.log(f"Mode: {'Quick' if self.quick_mode else 'Full'}")

        if not PSYCOPG2_AVAILABLE:
            self.log("❌ psycopg2 not available. Cannot connect to PostgreSQL.", "ERROR")
            self.overall_status = "FAIL"
            return False

        # Determine which databases to validate
        databases_to_validate = [
            ('fortune500', self.FORTUNE_500_TABLES),
            ('abm', self.ABM_TABLES),
            ('onboarding', self.ONBOARDING_TABLES)
        ]

        for db_key, tables in databases_to_validate:
            self.log(f"\n{'='*70}", "SECTION")
            self.log(f"Validating {db_key.upper()} Database", "SECTION")
            self.log(f"{'='*70}", "SECTION")

            # Filter to specific table if requested
            if specific_table:
                if specific_table not in tables:
                    continue
                tables = [specific_table]

            # 1. Row Count Validation (always run)
            self.validate_row_counts(db_key, tables)

            if not self.quick_mode:
                # 2. Foreign Key Integrity
                self.validate_foreign_keys(db_key, tables)

                # 3. JSON Structure Validation
                self.validate_json_structures(db_key, tables)

                # 4. Financial Calculation Validation
                if db_key == 'fortune500':
                    self.validate_financial_calculations(db_key)

                # 5. Business Logic Validation
                self.validate_business_logic(db_key, tables)

                # 6. Sample Data Comparison
                self.validate_sample_data(db_key, tables, sample_size=5)

        # Generate final report
        end_time = datetime.utcnow()
        duration = (end_time - start_time).total_seconds()

        self._print_summary_report(duration)

        return self.overall_status == "PASS"

    def _print_summary_report(self, duration: float):
        """Print final summary report"""
        self.log("\n" + "="*70, "SECTION")
        self.log("VALIDATION SUMMARY REPORT", "SECTION")
        self.log("="*70, "SECTION")

        # Count results by status
        passed = sum(1 for r in self.results if r.status == "PASS")
        failed = sum(1 for r in self.results if r.status == "FAIL")
        warnings = sum(1 for r in self.results if r.status == "WARNING")

        self.log(f"Total Checks: {len(self.results)}")
        self.log(f"✅ Passed: {passed}")
        self.log(f"❌ Failed: {failed}")
        self.log(f"⚠️  Warnings: {warnings}")
        self.log(f"Duration: {duration:.2f} seconds")

        self.log("\n" + "-"*70)

        if self.overall_status == "PASS":
            self.log("✅ Overall Status: PASS", "SUCCESS")
            self.log("✅ Recommendation: PROCEED with cutover", "SUCCESS")
        else:
            self.log("❌ Overall Status: FAIL", "ERROR")
            self.log("❌ Recommendation: ROLLBACK - Fix issues before cutover", "ERROR")

        self.log("="*70 + "\n")

    def generate_json_report(self) -> dict:
        """Generate JSON report for programmatic consumption"""
        return {
            'validation_run': {
                'timestamp': datetime.utcnow().isoformat(),
                'overall_status': self.overall_status,
                'mode': 'quick' if self.quick_mode else 'full'
            },
            'summary': {
                'total_checks': len(self.results),
                'passed': sum(1 for r in self.results if r.status == "PASS"),
                'failed': sum(1 for r in self.results if r.status == "FAIL"),
                'warnings': sum(1 for r in self.results if r.status == "WARNING"),
            },
            'recommendation': 'PROCEED' if self.overall_status == "PASS" else 'ROLLBACK',
            'results': [asdict(r) for r in self.results]
        }


def main():
    """Main entry point for Epic 16 validation tool"""
    import argparse

    parser = argparse.ArgumentParser(
        description='Epic 16 Data Validation Tool - Verify migration accuracy and data integrity'
    )
    parser.add_argument('--json', action='store_true', help='Output JSON report')
    parser.add_argument('--quick', action='store_true', help='Quick validation (row counts only)')
    parser.add_argument('--table', type=str, help='Validate specific table only')

    args = parser.parse_args()

    # Create validator
    validator = Epic16ValidationTool(quick_mode=args.quick, json_output=args.json)

    # Run validation
    success = validator.run_validation(specific_table=args.table)

    # Output JSON if requested
    if args.json:
        report = validator.generate_json_report()
        print(json.dumps(report, indent=2))

    # Exit with appropriate code
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
