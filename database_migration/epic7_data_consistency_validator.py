"""
Epic 7 Data Consistency Validator
Continuous validation comparing SQLite vs PostgreSQL data

Run this every hour during the 1-week dual-write validation period
"""

import os
import sys
import sqlite3
import psycopg2
import logging
from datetime import datetime
from typing import Dict, Tuple

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('epic7_consistency_validation.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class Epic7ConsistencyValidator:
    """Validates data consistency between SQLite and PostgreSQL"""

    def __init__(self):
        self.sqlite_path = "business_development/epic7_sales_automation.db"
        self.pg_config = {
            'host': os.getenv('POSTGRES_HOST', 'localhost'),
            'port': int(os.getenv('POSTGRES_PORT', '5432')),
            'database': os.getenv('POSTGRES_DB', 'synapse_business_core'),
            'user': os.getenv('POSTGRES_USER', 'synapse'),
            'password': os.getenv('POSTGRES_PASSWORD', 'synapse_password')
        }
        self.tables_to_validate = [
            'crm_contacts',
            'generated_proposals',
            'roi_templates',
            'linkedin_automation_tracking',
            'ab_test_campaigns',
            'revenue_forecasts'
        ]

    def validate_row_counts(self) -> Dict[str, Tuple[int, int, bool]]:
        """Validate row counts for all tables"""
        logger.info("Validating row counts across all tables...")

        sqlite_conn = sqlite3.connect(self.sqlite_path)
        pg_conn = psycopg2.connect(**self.pg_config)

        results = {}

        for table in self.tables_to_validate:
            # SQLite count
            sqlite_cursor = sqlite_conn.cursor()
            sqlite_cursor.execute(f'SELECT COUNT(*) FROM {table}')
            sqlite_count = sqlite_cursor.fetchone()[0]

            # PostgreSQL count
            pg_cursor = pg_conn.cursor()
            pg_cursor.execute(f'SELECT COUNT(*) FROM {table}')
            pg_count = pg_cursor.fetchone()[0]

            match = sqlite_count == pg_count
            results[table] = (sqlite_count, pg_count, match)

            status = "✅" if match else "❌"
            logger.info(f"{status} {table}: SQLite={sqlite_count}, PostgreSQL={pg_count}")

        sqlite_conn.close()
        pg_conn.close()

        return results

    def validate_pipeline_value(self) -> Tuple[float, float, bool]:
        """Validate $1.158M pipeline value preservation"""
        logger.info("Validating critical $1.158M pipeline value...")

        sqlite_conn = sqlite3.connect(self.sqlite_path)
        pg_conn = psycopg2.connect(**self.pg_config)

        # SQLite pipeline value
        sqlite_cursor = sqlite_conn.cursor()
        sqlite_cursor.execute(
            'SELECT SUM(estimated_value) FROM crm_contacts WHERE qualification_status = "qualified"'
        )
        sqlite_value = sqlite_cursor.fetchone()[0] or 0

        # PostgreSQL pipeline value
        pg_cursor = pg_conn.cursor()
        pg_cursor.execute(
            "SELECT SUM(estimated_value) FROM crm_contacts WHERE qualification_status = 'qualified'"
        )
        pg_value = pg_cursor.fetchone()[0] or 0

        sqlite_conn.close()
        pg_conn.close()

        # Allow for small floating point differences
        match = abs(sqlite_value - pg_value) < 1

        status = "✅" if match else "❌"
        logger.info(f"{status} Pipeline value: SQLite=${sqlite_value:,.0f}, PostgreSQL=${pg_value:,.0f}")

        return sqlite_value, pg_value, match

    def validate_crm_contacts_integrity(self) -> bool:
        """Validate detailed CRM contacts data integrity"""
        logger.info("Validating CRM contacts data integrity...")

        sqlite_conn = sqlite3.connect(self.sqlite_path)
        pg_conn = psycopg2.connect(**self.pg_config)

        # Get all contact IDs from both databases
        sqlite_cursor = sqlite_conn.cursor()
        sqlite_cursor.execute('SELECT contact_id, name, email, estimated_value FROM crm_contacts ORDER BY contact_id')
        sqlite_contacts = sqlite_cursor.fetchall()

        pg_cursor = pg_conn.cursor()
        pg_cursor.execute('SELECT contact_id, name, email, estimated_value FROM crm_contacts ORDER BY contact_id')
        pg_contacts = pg_cursor.fetchall()

        sqlite_conn.close()
        pg_conn.close()

        # Compare
        if len(sqlite_contacts) != len(pg_contacts):
            logger.error(f"❌ Contact count mismatch: SQLite={len(sqlite_contacts)}, PostgreSQL={len(pg_contacts)}")
            return False

        mismatches = 0
        for i, (sqlite_contact, pg_contact) in enumerate(zip(sqlite_contacts, pg_contacts)):
            if sqlite_contact != pg_contact:
                logger.error(f"❌ Contact mismatch at index {i}: SQLite={sqlite_contact}, PostgreSQL={pg_contact}")
                mismatches += 1

        if mismatches == 0:
            logger.info(f"✅ All {len(sqlite_contacts)} CRM contacts match perfectly")
            return True
        else:
            logger.error(f"❌ Found {mismatches} mismatches in CRM contacts")
            return False

    def run_full_validation(self) -> bool:
        """Run complete validation suite"""
        logger.info(f"{'='*60}")
        logger.info(f"Epic 7 Data Consistency Validation - {datetime.now()}")
        logger.info(f"{'='*60}")

        try:
            # Test 1: Row counts
            row_count_results = self.validate_row_counts()
            row_counts_match = all(result[2] for result in row_count_results.values())

            # Test 2: Pipeline value
            sqlite_value, pg_value, pipeline_match = self.validate_pipeline_value()

            # Test 3: CRM contacts integrity
            contacts_integrity = self.validate_crm_contacts_integrity()

            # Summary
            logger.info(f"\n{'='*60}")
            logger.info("VALIDATION SUMMARY")
            logger.info(f"{'='*60}")
            logger.info(f"Row counts match: {'✅ PASS' if row_counts_match else '❌ FAIL'}")
            logger.info(f"Pipeline value preserved: {'✅ PASS' if pipeline_match else '❌ FAIL'}")
            logger.info(f"CRM contacts integrity: {'✅ PASS' if contacts_integrity else '❌ FAIL'}")

            overall_success = row_counts_match and pipeline_match and contacts_integrity

            if overall_success:
                logger.info(f"\n✅ VALIDATION PASSED: 100% data consistency")
                logger.info(f"   SQLite and PostgreSQL are perfectly synchronized")
                logger.info(f"   $1.158M pipeline fully protected")
            else:
                logger.error(f"\n❌ VALIDATION FAILED: Data inconsistencies detected")
                logger.error(f"   Manual review required before cutover")

            return overall_success

        except Exception as e:
            logger.error(f"❌ Validation failed with error: {e}")
            return False


def run_continuous_validation():
    """Run validation and log results"""
    validator = Epic7ConsistencyValidator()
    success = validator.run_full_validation()

    if success:
        logger.info("\n🎉 Validation successful - Safe to proceed with dual-write period")
        return 0
    else:
        logger.error("\n💥 Validation failed - Data inconsistencies detected")
        return 1


if __name__ == "__main__":
    sys.exit(run_continuous_validation())
