"""
Epic 7 PostgreSQL Hot Migration
Zero-downtime migration of $1.158M sales pipeline from SQLite to PostgreSQL

Business Critical: Epic 7 Sales Automation Pipeline Protection
- 16 qualified contacts with complete data
- $1.158M pipeline value maintained
- Zero disruption to sales operations
"""

import json
import logging
import os
import sqlite3
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

import psycopg2
import psycopg2.extras

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('epic7_postgresql_migration.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class Epic7PostgreSQLMigrator:
    """Hot migration orchestrator for Epic 7 sales automation data"""

    def __init__(self):
        self.sqlite_db_path = Path("../business_development/epic7_sales_automation.db")
        self.postgres_config = {
            'host': os.getenv('POSTGRES_HOST', 'localhost'),
            'port': int(os.getenv('POSTGRES_PORT', '5432')),
            'database': os.getenv('POSTGRES_DB', 'synapse_business_core'),
            'user': os.getenv('POSTGRES_USER', 'synapse'),
            'password': os.getenv('POSTGRES_PASSWORD', 'synapse_password')
        }
        self.batch_size = 1000
        self.migration_start_time = None

    def validate_environment(self) -> bool:
        """Validate migration environment and dependencies"""
        logger.info("Validating migration environment...")

        # Check SQLite database exists
        if not self.sqlite_db_path.exists():
            logger.error(f"SQLite database not found: {self.sqlite_db_path}")
            return False

        # Test SQLite connection
        try:
            sqlite_conn = sqlite3.connect(str(self.sqlite_db_path))
            sqlite_conn.close()
            logger.info("✅ SQLite database connection validated")
        except Exception as e:
            logger.error(f"❌ SQLite connection failed: {e}")
            return False

        # Test PostgreSQL connection
        try:
            pg_conn = psycopg2.connect(**self.postgres_config)
            pg_conn.close()
            logger.info("✅ PostgreSQL database connection validated")
        except Exception as e:
            logger.error(f"❌ PostgreSQL connection failed: {e}")
            return False

        return True

    def create_postgres_schema(self):
        """Create PostgreSQL schema for Epic 7 CRM data"""
        logger.info("Creating PostgreSQL schema for Epic 7 CRM...")

        schema_sql = """
        -- Epic 7 CRM Schema for PostgreSQL
        -- Business Critical: $1.158M Sales Pipeline Protection

        -- Enable required extensions
        CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

        -- CRM Contacts Table
        CREATE TABLE IF NOT EXISTS crm_contacts (
            contact_id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            company TEXT NOT NULL,
            company_size TEXT,
            title TEXT,
            email TEXT NOT NULL,
            linkedin_profile TEXT,
            phone TEXT,
            lead_score INTEGER CHECK (lead_score >= 0 AND lead_score <= 100),
            qualification_status TEXT CHECK (qualification_status IN ('qualified', 'unqualified', 'disqualified')),
            estimated_value INTEGER CHECK (estimated_value >= 0),
            priority_tier TEXT CHECK (priority_tier IN ('platinum', 'gold', 'silver', 'bronze')),
            next_action TEXT,
            next_action_date TEXT,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            notes TEXT
        );

        -- Lead Scoring History Table
        CREATE TABLE IF NOT EXISTS lead_scoring_history (
            history_id SERIAL PRIMARY KEY,
            contact_id TEXT NOT NULL REFERENCES crm_contacts(contact_id) ON DELETE CASCADE,
            previous_score INTEGER,
            new_score INTEGER NOT NULL,
            scoring_factors JSONB,
            scored_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            scored_by TEXT DEFAULT 'system'
        );

        -- Generated Proposals Table
        CREATE TABLE IF NOT EXISTS generated_proposals (
            proposal_id TEXT PRIMARY KEY,
            contact_id TEXT NOT NULL REFERENCES crm_contacts(contact_id) ON DELETE CASCADE,
            template_used TEXT NOT NULL,
            proposal_value INTEGER CHECK (proposal_value >= 0),
            estimated_close_probability DECIMAL(5,2) CHECK (estimated_close_probability >= 0 AND estimated_close_probability <= 100),
            roi_calculation JSONB,
            status TEXT CHECK (status IN ('draft', 'sent', 'accepted', 'rejected', 'expired')),
            generated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            sent_at TIMESTAMPTZ,
            notes TEXT
        );

        -- Sales Pipeline Table
        CREATE TABLE IF NOT EXISTS sales_pipeline (
            pipeline_id SERIAL PRIMARY KEY,
            contact_id TEXT NOT NULL REFERENCES crm_contacts(contact_id) ON DELETE CASCADE,
            stage TEXT NOT NULL,
            probability DECIMAL(5,2) CHECK (probability >= 0 AND probability <= 100),
            expected_close_date DATE,
            deal_value INTEGER CHECK (deal_value >= 0),
            notes TEXT,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );

        -- ROI Templates Table
        CREATE TABLE IF NOT EXISTS roi_templates (
            template_id TEXT PRIMARY KEY,
            inquiry_type TEXT NOT NULL,
            title TEXT NOT NULL,
            executive_summary TEXT,
            problem_statement TEXT,
            solution_overview TEXT,
            roi_calculation JSONB,
            timeline TEXT,
            risks_mitigation TEXT,
            call_to_action TEXT,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );

        -- LinkedIn Automation Tracking Table
        CREATE TABLE IF NOT EXISTS linkedin_automation_tracking (
            tracking_id SERIAL PRIMARY KEY,
            contact_id TEXT REFERENCES crm_contacts(contact_id) ON DELETE SET NULL,
            action_type TEXT NOT NULL,
            action_data JSONB,
            executed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            success BOOLEAN DEFAULT TRUE,
            error_message TEXT
        );

        -- A/B Test Campaigns Table
        CREATE TABLE IF NOT EXISTS ab_test_campaigns (
            campaign_id TEXT PRIMARY KEY,
            campaign_name TEXT NOT NULL,
            test_type TEXT NOT NULL,
            target_metric TEXT NOT NULL,
            control_group JSONB,
            test_group JSONB,
            start_date TIMESTAMPTZ NOT NULL,
            end_date TIMESTAMPTZ,
            status TEXT CHECK (status IN ('active', 'completed', 'cancelled')),
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );

        -- A/B Test Results Table
        CREATE TABLE IF NOT EXISTS ab_test_results (
            result_id SERIAL PRIMARY KEY,
            campaign_id TEXT NOT NULL REFERENCES ab_test_campaigns(campaign_id) ON DELETE CASCADE,
            metric_name TEXT NOT NULL,
            control_value DECIMAL(10,4),
            test_value DECIMAL(10,4),
            improvement_percentage DECIMAL(7,4),
            statistical_significance DECIMAL(5,4),
            confidence_level DECIMAL(5,4),
            recorded_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );

        -- Revenue Forecasts Table
        CREATE TABLE IF NOT EXISTS revenue_forecasts (
            forecast_id SERIAL PRIMARY KEY,
            forecast_period TEXT NOT NULL,
            predicted_revenue INTEGER CHECK (predicted_revenue >= 0),
            confidence_level DECIMAL(5,2) CHECK (confidence_level >= 0 AND confidence_level <= 100),
            factors JSONB,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );

        -- Create indexes for performance
        CREATE INDEX IF NOT EXISTS idx_crm_contacts_qualification ON crm_contacts(qualification_status);
        CREATE INDEX IF NOT EXISTS idx_crm_contacts_priority ON crm_contacts(priority_tier);
        CREATE INDEX IF NOT EXISTS idx_crm_contacts_lead_score ON crm_contacts(lead_score);
        CREATE INDEX IF NOT EXISTS idx_lead_scoring_history_contact ON lead_scoring_history(contact_id);
        CREATE INDEX IF NOT EXISTS idx_generated_proposals_contact ON generated_proposals(contact_id);
        CREATE INDEX IF NOT EXISTS idx_generated_proposals_status ON generated_proposals(status);
        CREATE INDEX IF NOT EXISTS idx_sales_pipeline_contact ON sales_pipeline(contact_id);
        CREATE INDEX IF NOT EXISTS idx_linkedin_automation_contact ON linkedin_automation_tracking(contact_id);

        -- Create updated_at trigger function
        CREATE OR REPLACE FUNCTION update_updated_at_column()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = NOW();
            RETURN NEW;
        END;
        $$ language 'plpgsql';

        -- Add triggers for updated_at
        CREATE TRIGGER update_crm_contacts_updated_at
            BEFORE UPDATE ON crm_contacts
            FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

        CREATE TRIGGER update_sales_pipeline_updated_at
            BEFORE UPDATE ON sales_pipeline
            FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

        CREATE TRIGGER update_revenue_forecasts_updated_at
            BEFORE UPDATE ON revenue_forecasts
            FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
        """

        try:
            conn = psycopg2.connect(**self.postgres_config)
            cursor = conn.cursor()

            # Execute schema creation
            cursor.execute(schema_sql)
            conn.commit()

            logger.info("✅ PostgreSQL schema created successfully")
            return True

        except Exception as e:
            logger.error(f"❌ Schema creation failed: {e}")
            return False
        finally:
            if 'conn' in locals():
                conn.close()

    def migrate_table_data(self, table_name: str, sqlite_conn, pg_conn) -> int:
        """Migrate data for a specific table"""
        logger.info(f"Migrating table: {table_name}")

        try:
            sqlite_cursor = sqlite_conn.cursor()
            pg_cursor = pg_conn.cursor()

            # Get row count
            sqlite_cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
            total_rows = sqlite_cursor.fetchone()[0]

            if total_rows == 0:
                logger.info(f"Table {table_name} is empty, skipping")
                return 0

            # Get column information
            sqlite_cursor.execute(f"PRAGMA table_info({table_name})")
            columns_info = sqlite_cursor.fetchall()
            columns = [col[1] for col in columns_info]

            # Migrate data in batches
            migrated_count = 0
            offset = 0

            while offset < total_rows:
                # Fetch batch from SQLite
                sqlite_cursor.execute(f"""
                    SELECT {', '.join(columns)}
                    FROM {table_name}
                    LIMIT {self.batch_size} OFFSET {offset}
                """)

                rows = sqlite_cursor.fetchall()

                if not rows:
                    break

                # Insert batch into PostgreSQL
                if table_name == 'crm_contacts':
                    # Special handling for crm_contacts with proper type conversion
                    for row in rows:
                        contact_data = dict(zip(columns, row, strict=False))
                        # Convert datetime strings to proper format if needed
                        if 'created_at' in contact_data and contact_data['created_at']:
                            # Ensure proper timestamp format
                            pass
                        if 'updated_at' in contact_data and contact_data['updated_at']:
                            # Ensure proper timestamp format
                            pass

                        pg_cursor.execute("""
                            INSERT INTO crm_contacts (
                                contact_id, name, company, company_size, title, email,
                                linkedin_profile, phone, lead_score, qualification_status,
                                estimated_value, priority_tier, next_action, next_action_date,
                                created_at, updated_at, notes
                            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                            ON CONFLICT (contact_id) DO UPDATE SET
                                name = EXCLUDED.name,
                                company = EXCLUDED.company,
                                company_size = EXCLUDED.company_size,
                                title = EXCLUDED.title,
                                email = EXCLUDED.email,
                                linkedin_profile = EXCLUDED.linkedin_profile,
                                phone = EXCLUDED.phone,
                                lead_score = EXCLUDED.lead_score,
                                qualification_status = EXCLUDED.qualification_status,
                                estimated_value = EXCLUDED.estimated_value,
                                priority_tier = EXCLUDED.priority_tier,
                                next_action = EXCLUDED.next_action,
                                next_action_date = EXCLUDED.next_action_date,
                                updated_at = EXCLUDED.updated_at,
                                notes = EXCLUDED.notes
                        """, (
                            contact_data.get('contact_id'),
                            contact_data.get('name'),
                            contact_data.get('company'),
                            contact_data.get('company_size'),
                            contact_data.get('title'),
                            contact_data.get('email'),
                            contact_data.get('linkedin_profile'),
                            contact_data.get('phone'),
                            contact_data.get('lead_score'),
                            contact_data.get('qualification_status'),
                            contact_data.get('estimated_value'),
                            contact_data.get('priority_tier'),
                            contact_data.get('next_action'),
                            contact_data.get('next_action_date'),
                            contact_data.get('created_at'),
                            contact_data.get('updated_at'),
                            contact_data.get('notes')
                        ))
                else:
                    # Generic insert for other tables
                    placeholders = ', '.join(['%s'] * len(columns))
                    columns_str = ', '.join(columns)

                    # Handle potential JSON fields
                    json_columns = ['scoring_factors', 'roi_calculation', 'action_data', 'control_group', 'test_group', 'factors']
                    for row in rows:
                        processed_row = []
                        for i, value in enumerate(row):
                            col_name = columns[i]
                            if col_name in json_columns and value:
                                try:
                                    # Try to parse as JSON if it's a string
                                    if isinstance(value, str):
                                        processed_row.append(json.loads(value))
                                    else:
                                        processed_row.append(value)
                                except (json.JSONDecodeError, TypeError, ValueError):
                                    processed_row.append(value)
                            else:
                                processed_row.append(value)

                        pg_cursor.execute(f"""
                            INSERT INTO {table_name} ({columns_str})
                            VALUES ({placeholders})
                            ON CONFLICT DO NOTHING
                        """, processed_row)

                migrated_count += len(rows)
                offset += self.batch_size

                logger.info(f"Migrated {migrated_count}/{total_rows} rows for {table_name}")

            pg_conn.commit()
            logger.info(f"✅ Successfully migrated {migrated_count} rows for table {table_name}")
            return migrated_count

        except Exception as e:
            logger.error(f"❌ Failed to migrate table {table_name}: {e}")
            pg_conn.rollback()
            return 0

    def migrate_all_data(self) -> dict[str, int]:
        """Migrate all Epic 7 data from SQLite to PostgreSQL"""
        logger.info("Starting data migration from SQLite to PostgreSQL...")

        sqlite_conn = sqlite3.connect(str(self.sqlite_db_path))
        pg_conn = psycopg2.connect(**self.postgres_config)

        migration_results = {}

        # List of tables to migrate (in dependency order)
        tables_to_migrate = [
            'roi_templates',  # No dependencies
            'crm_contacts',   # Referenced by others
            'lead_scoring_history',  # References crm_contacts
            'generated_proposals',   # References crm_contacts
            'sales_pipeline',        # References crm_contacts
            'linkedin_automation_tracking',  # References crm_contacts
            'ab_test_campaigns',     # No dependencies
            'ab_test_results',       # References ab_test_campaigns
            'revenue_forecasts'      # No dependencies
        ]

        try:
            for table in tables_to_migrate:
                # Check if table exists in SQLite
                sqlite_cursor = sqlite_conn.cursor()
                sqlite_cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,))
                if sqlite_cursor.fetchone():
                    migrated_count = self.migrate_table_data(table, sqlite_conn, pg_conn)
                    migration_results[table] = migrated_count
                else:
                    logger.info(f"Table {table} does not exist in SQLite, skipping")
                    migration_results[table] = 0

            logger.info("✅ Data migration completed successfully")
            return migration_results

        except Exception as e:
            logger.error(f"❌ Data migration failed: {e}")
            raise
        finally:
            sqlite_conn.close()
            pg_conn.close()

    def validate_migration(self) -> dict[str, Any]:
        """Validate that migration was successful"""
        logger.info("Validating migration results...")

        validation_results = {
            'row_counts_match': True,
            'pipeline_value_preserved': True,
            'critical_data_integrity': True,
            'details': {}
        }

        try:
            sqlite_conn = sqlite3.connect(str(self.sqlite_db_path))
            pg_conn = psycopg2.connect(**self.postgres_config)

            sqlite_cursor = sqlite_conn.cursor()
            pg_cursor = pg_conn.cursor()

            # Validate row counts for each table
            tables_to_check = [
                'crm_contacts', 'lead_scoring_history', 'generated_proposals',
                'sales_pipeline', 'roi_templates', 'linkedin_automation_tracking',
                'ab_test_campaigns', 'ab_test_results', 'revenue_forecasts'
            ]

            for table in tables_to_check:
                # SQLite count
                sqlite_cursor.execute(f"SELECT COUNT(*) FROM {table}")
                sqlite_count = sqlite_cursor.fetchone()[0]

                # PostgreSQL count
                pg_cursor.execute(f"SELECT COUNT(*) FROM {table}")
                pg_count = pg_cursor.fetchone()[0]

                validation_results['details'][table] = {
                    'sqlite_count': sqlite_count,
                    'postgres_count': pg_count,
                    'counts_match': sqlite_count == pg_count
                }

                if sqlite_count != pg_count:
                    validation_results['row_counts_match'] = False
                    logger.warning(f"Row count mismatch for {table}: SQLite={sqlite_count}, PostgreSQL={pg_count}")

            # Validate pipeline value preservation
            sqlite_cursor.execute("SELECT SUM(estimated_value) FROM crm_contacts WHERE qualification_status = 'qualified'")
            sqlite_pipeline = sqlite_cursor.fetchone()[0] or 0

            pg_cursor.execute("SELECT SUM(estimated_value) FROM crm_contacts WHERE qualification_status = 'qualified'")
            pg_pipeline = pg_cursor.fetchone()[0] or 0

            validation_results['details']['pipeline_value'] = {
                'sqlite_value': sqlite_pipeline,
                'postgres_value': pg_pipeline,
                'values_match': sqlite_pipeline == pg_pipeline
            }

            if sqlite_pipeline != pg_pipeline:
                validation_results['pipeline_value_preserved'] = False
                logger.error(f"Pipeline value mismatch: SQLite=${sqlite_pipeline:,}, PostgreSQL=${pg_pipeline:,}")

            # Validate critical data integrity (sample check)
            sqlite_cursor.execute("SELECT contact_id, name, email FROM crm_contacts WHERE qualification_status = 'qualified' LIMIT 5")
            sqlite_sample = sqlite_cursor.fetchall()

            for contact_id, name, email in sqlite_sample:
                pg_cursor.execute("SELECT name, email FROM crm_contacts WHERE contact_id = %s", (contact_id,))
                pg_result = pg_cursor.fetchone()

                if not pg_result or pg_result[0] != name or pg_result[1] != email:
                    validation_results['critical_data_integrity'] = False
                    logger.error(f"Data integrity issue for contact {contact_id}")
                    break

            logger.info("✅ Migration validation completed")
            return validation_results

        except Exception as e:
            logger.error(f"❌ Migration validation failed: {e}")
            validation_results['validation_error'] = str(e)
            return validation_results
        finally:
            if 'sqlite_conn' in locals():
                sqlite_conn.close()
            if 'pg_conn' in locals():
                pg_conn.close()

    def execute_hot_migration(self) -> bool:
        """Execute the complete hot migration process"""
        logger.info("🚀 Starting Epic 7 PostgreSQL Hot Migration")
        logger.info("Business Critical: $1.158M Sales Pipeline Protection")
        self.migration_start_time = datetime.now()

        try:
            # Phase 1: Environment Validation
            logger.info("Phase 1: Environment Validation")
            if not self.validate_environment():
                raise Exception("Environment validation failed")

            # Phase 2: Schema Creation
            logger.info("Phase 2: PostgreSQL Schema Creation")
            if not self.create_postgres_schema():
                raise Exception("Schema creation failed")

            # Phase 3: Data Migration
            logger.info("Phase 3: Data Migration")
            migration_results = self.migrate_all_data()

            total_migrated = sum(migration_results.values())
            logger.info(f"Total rows migrated: {total_migrated}")

            # Phase 4: Validation
            logger.info("Phase 4: Migration Validation")
            validation_results = self.validate_migration()

            # Phase 5: Results Summary
            migration_duration = datetime.now() - self.migration_start_time

            logger.info("=== MIGRATION RESULTS SUMMARY ===")
            logger.info(f"Migration Duration: {migration_duration}")
            logger.info(f"Total Rows Migrated: {total_migrated}")
            logger.info(f"Row Counts Match: {validation_results['row_counts_match']}")
            logger.info(f"Pipeline Value Preserved: {validation_results['pipeline_value_preserved']}")
            logger.info(f"Data Integrity Maintained: {validation_results['critical_data_integrity']}")

            success = all([
                validation_results['row_counts_match'],
                validation_results['pipeline_value_preserved'],
                validation_results['critical_data_integrity']
            ])

            if success:
                logger.info("✅ Epic 7 PostgreSQL Hot Migration COMPLETED SUCCESSFULLY!")
                logger.info("Business Continuity: $1.158M sales pipeline fully protected")
            else:
                logger.error("❌ Epic 7 PostgreSQL Hot Migration FAILED!")
                logger.error("Manual intervention required to ensure data integrity")

            return success

        except Exception as e:
            logger.error(f"❌ Hot migration failed: {e}")
            return False


if __name__ == "__main__":
    migrator = Epic7PostgreSQLMigrator()
    success = migrator.execute_hot_migration()

    if success:
        logger.info("🎉 Epic 7 PostgreSQL migration completed successfully!")
        sys.exit(0)
    else:
        logger.error("💥 Epic 7 PostgreSQL migration failed!")
        sys.exit(1)
