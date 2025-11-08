"""
Epic 7 PostgreSQL Migration - Schema Aligned Version
Migrates all Epic 7 data with SQLite-to-PostgreSQL schema mapping

Business Critical: $1.158M Sales Pipeline + Supporting Data
"""

import json
import logging
import os
import sqlite3
import sys

import psycopg2
import psycopg2.extras

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('epic7_migration_aligned.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class Epic7AlignedMigrator:
    """Schema-aligned migration for Epic 7 data"""

    def __init__(self):
        self.sqlite_db_path = "../business_development/epic7_sales_automation.db"
        self.postgres_config = {
            'host': os.getenv('POSTGRES_HOST', 'localhost'),
            'port': int(os.getenv('POSTGRES_PORT', '5432')),
            'database': os.getenv('POSTGRES_DB', 'synapse_business_core'),
            'user': os.getenv('POSTGRES_USER', 'synapse'),
            'password': os.getenv('POSTGRES_PASSWORD', 'synapse_password')
        }

    def migrate_roi_templates(self, sqlite_conn, pg_conn) -> int:
        """Migrate ROI templates with schema mapping"""
        logger.info("Migrating roi_templates...")

        sqlite_cursor = sqlite_conn.cursor()
        pg_cursor = pg_conn.cursor()

        sqlite_cursor.execute("SELECT * FROM roi_templates")
        rows = sqlite_cursor.fetchall()

        if not rows:
            logger.info("No ROI templates to migrate")
            return 0

        migrated = 0
        for row in rows:
            try:
                pg_cursor.execute("""
                    INSERT INTO roi_templates (
                        template_id, inquiry_type, title, executive_summary,
                        problem_statement, solution_overview, roi_calculation,
                        timeline, risks_mitigation, call_to_action,
                        created_at, updated_at
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (template_id) DO UPDATE SET
                        inquiry_type = EXCLUDED.inquiry_type,
                        title = EXCLUDED.title
                """, (
                    row[0],  # template_id
                    row[1],  # inquiry_type
                    row[2],  # template_name -> title
                    f"Cost: {row[3]}, Benefits: {row[4]}",  # executive_summary
                    "",  # problem_statement
                    "",  # solution_overview
                    json.dumps({"formula": row[5], "benchmarks": row[6]}) if row[5] else '{}',  # roi_calculation
                    "",  # timeline
                    "",  # risks_mitigation
                    "",  # call_to_action
                    row[7],  # created_at
                    row[8]   # updated_at
                ))
                migrated += 1
            except Exception as e:
                logger.error(f"Failed to migrate ROI template {row[0]}: {e}")

        pg_conn.commit()
        logger.info(f"✅ Migrated {migrated} ROI templates")
        return migrated

    def migrate_generated_proposals(self, sqlite_conn, pg_conn) -> int:
        """Migrate generated proposals"""
        logger.info("Migrating generated_proposals...")

        sqlite_cursor = sqlite_conn.cursor()
        pg_cursor = pg_conn.cursor()

        sqlite_cursor.execute("SELECT * FROM generated_proposals")
        rows = sqlite_cursor.fetchall()

        if not rows:
            logger.info("No proposals to migrate")
            return 0

        migrated = 0
        for row in rows:
            try:
                # Parse ROI calculation
                roi_data = {}
                if row[5]:  # roi_calculation
                    try:
                        roi_data = json.loads(row[5]) if isinstance(row[5], str) else {}
                    except:
                        roi_data = {"raw": str(row[5])}

                pg_cursor.execute("""
                    INSERT INTO generated_proposals (
                        proposal_id, contact_id, template_used, proposal_value,
                        estimated_close_probability, roi_calculation, status,
                        generated_at, sent_at, notes
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (proposal_id) DO UPDATE SET
                        status = EXCLUDED.status,
                        sent_at = EXCLUDED.sent_at
                """, (
                    row[0],  # proposal_id
                    row[1],  # contact_id
                    row[3] if row[3] else 'standard',  # template_used
                    row[7] if row[7] else 0,  # proposal_value
                    row[6] if row[6] else 0.0,  # estimated_close_probability
                    json.dumps(roi_data),  # roi_calculation
                    row[8] if row[8] else 'draft',  # status
                    row[9],  # generated_at
                    row[10],  # sent_at
                    row[4] if row[4] else ''  # proposal_content -> notes
                ))
                migrated += 1
            except Exception as e:
                logger.error(f"Failed to migrate proposal {row[0]}: {e}")

        pg_conn.commit()
        logger.info(f"✅ Migrated {migrated} generated proposals")
        return migrated

    def migrate_linkedin_tracking(self, sqlite_conn, pg_conn) -> int:
        """Migrate LinkedIn automation tracking"""
        logger.info("Migrating linkedin_automation_tracking...")

        sqlite_cursor = sqlite_conn.cursor()
        pg_cursor = pg_conn.cursor()

        sqlite_cursor.execute("SELECT * FROM linkedin_automation_tracking")
        rows = sqlite_cursor.fetchall()

        if not rows:
            logger.info("No LinkedIn tracking data to migrate")
            return 0

        migrated = 0
        for row in rows:
            try:
                # Parse sequence data
                action_data = {}
                if row[5]:  # sequence_data
                    try:
                        action_data = json.loads(row[5]) if isinstance(row[5], str) else {"raw": str(row[5])}
                    except:
                        action_data = {"raw": str(row[5])}

                action_data.update({
                    "sequence_type": row[2],  # sequence_type
                    "messages_sent": row[6],  # messages_sent
                    "responses_received": row[7],  # responses_received
                    "conversion_achieved": row[8]  # conversion_achieved
                })

                pg_cursor.execute("""
                    INSERT INTO linkedin_automation_tracking (
                        contact_id, action_type, action_data, executed_at,
                        success, error_message
                    ) VALUES (%s, %s, %s, %s, %s, %s)
                """, (
                    row[1],  # contact_id
                    row[2] if row[2] else 'sequence',  # sequence_type -> action_type
                    json.dumps(action_data),  # action_data
                    row[9] if row[9] else row[3],  # created_at/scheduled_at -> executed_at
                    row[5] == 'completed' if row[5] else True,  # success based on status
                    None  # error_message
                ))
                migrated += 1
            except Exception as e:
                logger.error(f"Failed to migrate LinkedIn tracking {row[0]}: {e}")

        pg_conn.commit()
        logger.info(f"✅ Migrated {migrated} LinkedIn tracking records")
        return migrated

    def migrate_ab_campaigns(self, sqlite_conn, pg_conn) -> int:
        """Migrate A/B test campaigns"""
        logger.info("Migrating ab_test_campaigns...")

        sqlite_cursor = sqlite_conn.cursor()
        pg_cursor = pg_conn.cursor()

        sqlite_cursor.execute("SELECT * FROM ab_test_campaigns")
        rows = sqlite_cursor.fetchall()

        if not rows:
            logger.info("No A/B campaigns to migrate")
            return 0

        migrated = 0
        for row in rows:
            try:
                control_group = {"description": row[2]} if row[2] else {}
                test_group = {"description": row[3]} if row[3] else {}

                pg_cursor.execute("""
                    INSERT INTO ab_test_campaigns (
                        campaign_id, campaign_name, test_type, target_metric,
                        control_group, test_group, start_date, end_date,
                        status, created_at
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (campaign_id) DO UPDATE SET
                        status = EXCLUDED.status,
                        end_date = EXCLUDED.end_date
                """, (
                    row[0],  # campaign_id
                    row[1],  # test_name -> campaign_name
                    'linkedin_post',  # test_type (default)
                    row[5] if row[5] else 'engagement',  # success_metric -> target_metric
                    json.dumps(control_group),  # control_group
                    json.dumps(test_group),  # test_group
                    row[6],  # start_date
                    row[7],  # end_date
                    row[8] if row[8] else 'active',  # status
                    row[11]  # created_at
                ))
                migrated += 1
            except Exception as e:
                logger.error(f"Failed to migrate A/B campaign {row[0]}: {e}")

        pg_conn.commit()
        logger.info(f"✅ Migrated {migrated} A/B test campaigns")
        return migrated

    def migrate_revenue_forecasts(self, sqlite_conn, pg_conn) -> int:
        """Migrate revenue forecasts"""
        logger.info("Migrating revenue_forecasts...")

        sqlite_cursor = sqlite_conn.cursor()
        pg_cursor = pg_conn.cursor()

        sqlite_cursor.execute("SELECT * FROM revenue_forecasts")
        rows = sqlite_cursor.fetchall()

        if not rows:
            logger.info("No revenue forecasts to migrate")
            return 0

        migrated = 0
        for row in rows:
            try:
                factors = {
                    "pipeline_snapshot": row[2] if row[2] else "",
                    "conversion_assumptions": row[3] if row[3] else "",
                    "confidence_interval": row[5] if row[5] else ""
                }

                pg_cursor.execute("""
                    INSERT INTO revenue_forecasts (
                        forecast_period, predicted_revenue, confidence_level,
                        factors, created_at, updated_at
                    ) VALUES (%s, %s, %s, %s, %s, %s)
                """, (
                    row[1],  # forecast_period
                    row[4] if row[4] else 0,  # projected_revenue -> predicted_revenue
                    85.0,  # default confidence_level
                    json.dumps(factors),  # factors
                    row[6],  # created_at
                    row[6]   # created_at -> updated_at
                ))
                migrated += 1
            except Exception as e:
                logger.error(f"Failed to migrate revenue forecast: {e}")

        pg_conn.commit()
        logger.info(f"✅ Migrated {migrated} revenue forecasts")
        return migrated

    def execute_migration(self) -> bool:
        """Execute the complete migration"""
        logger.info("🚀 Starting Epic 7 Schema-Aligned Migration")

        try:
            # Connect to databases
            sqlite_conn = sqlite3.connect(self.sqlite_db_path)
            pg_conn = psycopg2.connect(**self.postgres_config)

            total_migrated = 0

            # Migrate each table
            total_migrated += self.migrate_roi_templates(sqlite_conn, pg_conn)
            total_migrated += self.migrate_generated_proposals(sqlite_conn, pg_conn)
            total_migrated += self.migrate_linkedin_tracking(sqlite_conn, pg_conn)
            total_migrated += self.migrate_ab_campaigns(sqlite_conn, pg_conn)
            total_migrated += self.migrate_revenue_forecasts(sqlite_conn, pg_conn)

            sqlite_conn.close()
            pg_conn.close()

            logger.info(f"✅ Migration completed! Total rows migrated: {total_migrated}")
            logger.info("✅ CRM contacts ($1.158M pipeline) already migrated in previous step")
            return True

        except Exception as e:
            logger.error(f"❌ Migration failed: {e}")
            return False


if __name__ == "__main__":
    migrator = Epic7AlignedMigrator()
    success = migrator.execute_migration()

    if success:
        logger.info("🎉 Epic 7 schema-aligned migration completed!")
        sys.exit(0)
    else:
        logger.error("💥 Epic 7 migration failed!")
        sys.exit(1)
