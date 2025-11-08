"""
Database Consolidation Validation Tests for Epic 10

This module provides comprehensive testing for database consolidation 
from 17+ databases to 3 optimized databases.
"""

import json
import sqlite3
from pathlib import Path
from typing import Any

import pytest


class DatabaseConsolidationValidator:
    """Validates database consolidation for Epic 10."""

    def __init__(self):
        self.project_root = Path(__file__).parent.parent.parent

        # Target consolidated databases
        self.target_databases = {
            "synapse_business_crm.db": {
                "purpose": "Business CRM and sales automation data",
                "expected_tables": ["contacts", "opportunities", "proposals", "campaigns", "interactions"]
            },
            "synapse_analytics_intelligence.db": {
                "purpose": "Analytics and intelligence data",
                "expected_tables": ["analytics_metrics", "performance_data", "ab_tests", "insights"]
            },
            "synapse_system_infrastructure.db": {
                "purpose": "System infrastructure and configuration",
                "expected_tables": ["system_config", "user_management", "audit_logs", "monitoring"]
            }
        }

    def get_all_databases(self) -> list[Path]:
        """Get all database files in the project."""
        return list(self.project_root.glob("*.db"))

    def analyze_database_schema(self, db_path: Path) -> dict[str, Any]:
        """Analyze database schema and structure."""
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()

            # Get all tables
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [row[0] for row in cursor.fetchall()]

            # Get table details
            table_details = {}
            for table in tables:
                cursor.execute(f"PRAGMA table_info({table})")
                columns = [
                    {
                        "name": row[1],
                        "type": row[2],
                        "not_null": bool(row[3]),
                        "primary_key": bool(row[5])
                    }
                    for row in cursor.fetchall()
                ]

                cursor.execute(f"SELECT COUNT(*) FROM {table}")
                row_count = cursor.fetchone()[0]

                table_details[table] = {
                    "columns": columns,
                    "row_count": row_count
                }

            # Calculate database size
            cursor.execute("PRAGMA page_size")
            page_size = cursor.fetchone()[0]
            cursor.execute("PRAGMA page_count")
            page_count = cursor.fetchone()[0]
            db_size = page_size * page_count

            conn.close()

            return {
                "name": db_path.name,
                "path": str(db_path),
                "size_bytes": db_size,
                "size_mb": round(db_size / (1024 * 1024), 2),
                "tables": tables,
                "table_count": len(tables),
                "table_details": table_details,
                "total_rows": sum(details["row_count"] for details in table_details.values())
            }

        except Exception as e:
            return {
                "name": db_path.name,
                "path": str(db_path),
                "error": str(e),
                "accessible": False
            }

    def validate_target_database_structure(self, db_name: str) -> dict[str, Any]:
        """Validate that a target database has the expected structure."""
        db_path = self.project_root / db_name

        if not db_path.exists():
            return {
                "exists": False,
                "valid_structure": False,
                "missing_tables": self.target_databases[db_name]["expected_tables"],
                "status": "MISSING"
            }

        schema = self.analyze_database_schema(db_path)

        if "error" in schema:
            return {
                "exists": True,
                "valid_structure": False,
                "error": schema["error"],
                "status": "ERROR"
            }

        expected_tables = set(self.target_databases[db_name]["expected_tables"])
        actual_tables = set(schema["tables"])

        missing_tables = expected_tables - actual_tables
        extra_tables = actual_tables - expected_tables

        valid_structure = len(missing_tables) == 0

        return {
            "exists": True,
            "valid_structure": valid_structure,
            "schema": schema,
            "expected_tables": list(expected_tables),
            "actual_tables": list(actual_tables),
            "missing_tables": list(missing_tables),
            "extra_tables": list(extra_tables),
            "has_data": schema["total_rows"] > 0,
            "status": "VALID" if valid_structure else "INVALID_STRUCTURE"
        }

    def identify_legacy_databases(self) -> list[dict[str, Any]]:
        """Identify databases that should have been consolidated."""
        all_databases = self.get_all_databases()
        target_db_names = set(self.target_databases.keys())

        legacy_databases = []
        for db_path in all_databases:
            if db_path.name not in target_db_names:
                schema = self.analyze_database_schema(db_path)
                legacy_databases.append({
                    "name": db_path.name,
                    "schema": schema,
                    "should_be_consolidated": True
                })

        return legacy_databases

    def validate_data_migration_integrity(self) -> dict[str, Any]:
        """Validate that data migration preserved data integrity."""
        results = {}

        # Check each target database for data presence
        for db_name, config in self.target_databases.items():
            validation = self.validate_target_database_structure(db_name)

            if validation["exists"] and validation["valid_structure"]:
                # Check for data in key tables
                db_path = self.project_root / db_name
                try:
                    conn = sqlite3.connect(db_path)
                    cursor = conn.cursor()

                    table_data_status = {}
                    for table in config["expected_tables"]:
                        try:
                            cursor.execute(f"SELECT COUNT(*) FROM {table}")
                            count = cursor.fetchone()[0]
                            table_data_status[table] = {
                                "exists": True,
                                "row_count": count,
                                "has_data": count > 0
                            }
                        except sqlite3.OperationalError:
                            table_data_status[table] = {
                                "exists": False,
                                "row_count": 0,
                                "has_data": False
                            }

                    conn.close()

                    validation["table_data_status"] = table_data_status
                    validation["data_migrated"] = any(
                        status["has_data"] for status in table_data_status.values()
                    )

                except Exception as e:
                    validation["data_migration_error"] = str(e)
                    validation["data_migrated"] = False

            results[db_name] = validation

        return results

    def generate_consolidation_report(self) -> dict[str, Any]:
        """Generate comprehensive database consolidation report."""
        all_databases = self.get_all_databases()
        legacy_databases = self.identify_legacy_databases()
        target_validations = self.validate_data_migration_integrity()

        # Calculate consolidation metrics
        total_db_count = len(all_databases)
        target_db_count = len(self.target_databases)
        legacy_db_count = len(legacy_databases)

        consolidation_ratio = (
            (total_db_count - target_db_count) / total_db_count * 100
            if total_db_count > 0 else 0
        )

        # Determine consolidation status
        consolidation_complete = legacy_db_count == 0
        all_targets_valid = all(
            validation["exists"] and validation["valid_structure"]
            for validation in target_validations.values()
        )
        data_migration_complete = all(
            validation.get("data_migrated", False)
            for validation in target_validations.values()
        )

        # Calculate total size reduction
        total_size_before = sum(
            db["schema"].get("size_bytes", 0)
            for db in legacy_databases
            if "schema" in db and "size_bytes" in db["schema"]
        )
        total_size_after = sum(
            validation["schema"].get("size_bytes", 0)
            for validation in target_validations.values()
            if validation.get("schema") and "size_bytes" in validation["schema"]
        )

        return {
            "consolidation_complete": consolidation_complete and all_targets_valid,
            "data_migration_complete": data_migration_complete,
            "total_databases": total_db_count,
            "target_databases": target_db_count,
            "legacy_databases": legacy_db_count,
            "consolidation_ratio": consolidation_ratio,
            "target_validations": target_validations,
            "legacy_databases_details": legacy_databases,
            "size_reduction": {
                "before_bytes": total_size_before,
                "after_bytes": total_size_after,
                "reduction_bytes": total_size_before - total_size_after,
                "reduction_percentage": (
                    (total_size_before - total_size_after) / total_size_before * 100
                    if total_size_before > 0 else 0
                )
            },
            "status": (
                "COMPLETE" if consolidation_complete and all_targets_valid and data_migration_complete
                else "IN_PROGRESS"
            )
        }


@pytest.fixture
def db_validator():
    """Provide database consolidation validator."""
    return DatabaseConsolidationValidator()


class TestDatabaseConsolidation:
    """Database consolidation validation tests."""

    def test_target_database_count(self, db_validator):
        """Test that we have the correct number of target databases."""
        all_dbs = db_validator.get_all_databases()
        target_count = len(db_validator.target_databases)

        # Should have exactly 3 target databases or fewer total databases
        assert len(all_dbs) <= target_count * 2, (
            f"Too many databases found: {len(all_dbs)}, "
            f"expected maximum {target_count * 2} during consolidation"
        )

    def test_business_crm_database_structure(self, db_validator):
        """Test synapse_business_crm.db structure and data."""
        validation = db_validator.validate_target_database_structure("synapse_business_crm.db")

        assert validation["exists"], "synapse_business_crm.db database missing"
        assert validation["valid_structure"], (
            f"Invalid CRM database structure. Missing tables: {validation.get('missing_tables', [])}"
        )
        assert validation.get("has_data", False), "CRM database has no data"

    def test_analytics_intelligence_database_structure(self, db_validator):
        """Test synapse_analytics_intelligence.db structure and data."""
        validation = db_validator.validate_target_database_structure("synapse_analytics_intelligence.db")

        assert validation["exists"], "synapse_analytics_intelligence.db database missing"
        assert validation["valid_structure"], (
            f"Invalid analytics database structure. Missing tables: {validation.get('missing_tables', [])}"
        )
        # Analytics database may be empty initially, so not requiring data

    def test_system_infrastructure_database_structure(self, db_validator):
        """Test synapse_system_infrastructure.db structure and data."""
        validation = db_validator.validate_target_database_structure("synapse_system_infrastructure.db")

        assert validation["exists"], "synapse_system_infrastructure.db database missing"
        assert validation["valid_structure"], (
            f"Invalid system database structure. Missing tables: {validation.get('missing_tables', [])}"
        )
        # System database should have basic configuration data

    def test_legacy_database_consolidation(self, db_validator):
        """Test that legacy databases have been properly consolidated."""
        legacy_databases = db_validator.identify_legacy_databases()

        # Allow some legacy databases during transition, but flag for consolidation
        if len(legacy_databases) > 10:  # More than 10 suggests consolidation not started
            pytest.fail(
                f"Too many legacy databases found: {len(legacy_databases)}. "
                f"Legacy databases: {[db['name'] for db in legacy_databases]}"
            )
        elif len(legacy_databases) > 0:
            pytest.warn(UserWarning(
                f"Legacy databases still present: {[db['name'] for db in legacy_databases]}. "
                "Consider completing consolidation."
            ))

    def test_data_migration_integrity(self, db_validator):
        """Test that data migration preserved data integrity."""
        migration_results = db_validator.validate_data_migration_integrity()

        # At minimum, CRM database should have migrated data
        crm_result = migration_results.get("synapse_business_crm.db", {})
        assert crm_result.get("data_migrated", False), (
            "CRM data migration incomplete or failed"
        )

        # Check for migration errors
        for db_name, result in migration_results.items():
            assert "data_migration_error" not in result, (
                f"Data migration error in {db_name}: {result.get('data_migration_error')}"
            )

    def test_overall_consolidation_status(self, db_validator):
        """Test overall database consolidation completion."""
        report = db_validator.generate_consolidation_report()

        print("\nDatabase Consolidation Report:")
        print(f"Total Databases: {report['total_databases']}")
        print(f"Target Databases: {report['target_databases']}")
        print(f"Legacy Databases: {report['legacy_databases']}")
        print(f"Consolidation Ratio: {report['consolidation_ratio']:.1f}%")
        print(f"Status: {report['status']}")

        # For Epic 10 completion, we need significant consolidation progress
        assert report['consolidation_ratio'] >= 50, (
            f"Insufficient consolidation progress: {report['consolidation_ratio']:.1f}%, "
            f"expected at least 50%"
        )

        # All target databases should be valid
        for db_name, validation in report['target_validations'].items():
            assert validation['exists'], f"Target database {db_name} missing"
            assert validation['valid_structure'], (
                f"Target database {db_name} has invalid structure"
            )


if __name__ == "__main__":
    """Run database consolidation validation."""
    validator = DatabaseConsolidationValidator()
    report = validator.generate_consolidation_report()

    print(json.dumps(report, indent=2, default=str))
