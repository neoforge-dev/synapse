"""
Epic 7 PostgreSQL Dual-Write Layer
Transparent replication from SQLite to PostgreSQL

This module provides a context manager that monitors SQLite changes
and replicates them to PostgreSQL in real-time for the dual-write period.
"""

import json
import logging
import os
import sqlite3
from contextlib import contextmanager

import psycopg2

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class PostgreSQLReplicator:
    """Replicates SQLite writes to PostgreSQL"""

    def __init__(self):
        self.pg_config = {
            'host': os.getenv('POSTGRES_HOST', 'localhost'),
            'port': int(os.getenv('POSTGRES_PORT', '5432')),
            'database': os.getenv('POSTGRES_DB', 'synapse_business_core'),
            'user': os.getenv('POSTGRES_USER', 'synapse'),
            'password': os.getenv('POSTGRES_PASSWORD', 'synapse_password')
        }
        self.pg_conn: psycopg2.extensions.connection | None = None

    def connect(self):
        """Connect to PostgreSQL"""
        try:
            self.pg_conn = psycopg2.connect(**self.pg_config)
            logger.info("✅ PostgreSQL dual-write connection established")
        except Exception as e:
            logger.error(f"❌ PostgreSQL connection failed: {e}")
            raise

    def disconnect(self):
        """Disconnect from PostgreSQL"""
        if self.pg_conn:
            self.pg_conn.close()
            logger.info("PostgreSQL dual-write connection closed")

    def replicate_crm_contact(self, contact_data: dict):
        """Replicate CRM contact to PostgreSQL"""
        if not self.pg_conn:
            logger.warning("PostgreSQL not connected, skipping replication")
            return

        try:
            cursor = self.pg_conn.cursor()
            cursor.execute("""
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
            self.pg_conn.commit()
            logger.debug(f"✅ Replicated CRM contact {contact_data.get('contact_id')} to PostgreSQL")
        except Exception as e:
            logger.error(f"❌ Failed to replicate CRM contact: {e}")
            self.pg_conn.rollback()
            raise

    def replicate_generated_proposal(self, proposal_data: dict):
        """Replicate generated proposal to PostgreSQL"""
        if not self.pg_conn:
            return

        try:
            cursor = self.pg_conn.cursor()

            # Parse ROI calculation
            roi_data = {}
            if proposal_data.get('roi_calculation'):
                try:
                    roi_data = json.loads(proposal_data['roi_calculation']) if isinstance(proposal_data['roi_calculation'], str) else {}
                except:
                    roi_data = {"raw": str(proposal_data['roi_calculation'])}

            cursor.execute("""
                INSERT INTO generated_proposals (
                    proposal_id, contact_id, template_used, proposal_value,
                    estimated_close_probability, roi_calculation, status,
                    generated_at, sent_at, notes
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (proposal_id) DO UPDATE SET
                    status = EXCLUDED.status,
                    sent_at = EXCLUDED.sent_at
            """, (
                proposal_data.get('proposal_id'),
                proposal_data.get('contact_id'),
                proposal_data.get('template_used', 'standard'),
                proposal_data.get('proposal_value', 0),
                proposal_data.get('estimated_close_probability', 0.0),
                json.dumps(roi_data),
                proposal_data.get('status', 'draft'),
                proposal_data.get('generated_at'),
                proposal_data.get('sent_at'),
                proposal_data.get('proposal_content', '')
            ))
            self.pg_conn.commit()
            logger.debug(f"✅ Replicated proposal {proposal_data.get('proposal_id')} to PostgreSQL")
        except Exception as e:
            logger.error(f"❌ Failed to replicate proposal: {e}")
            self.pg_conn.rollback()

    def sync_all_recent_changes(self, sqlite_db_path: str):
        """Sync all recent changes from SQLite to PostgreSQL"""
        logger.info("Syncing recent changes from SQLite to PostgreSQL...")

        sqlite_conn = sqlite3.connect(sqlite_db_path)
        sqlite_cursor = sqlite_conn.cursor()

        # Sync CRM contacts modified in last hour
        sqlite_cursor.execute("""
            SELECT * FROM crm_contacts
            WHERE updated_at >= datetime('now', '-1 hour')
        """)
        contacts = sqlite_cursor.fetchall()

        if contacts:
            logger.info(f"Syncing {len(contacts)} recently updated contacts...")
            for contact in contacts:
                contact_dict = {
                    'contact_id': contact[0],
                    'name': contact[1],
                    'company': contact[2],
                    'company_size': contact[3],
                    'title': contact[4],
                    'email': contact[5],
                    'linkedin_profile': contact[6],
                    'phone': contact[7],
                    'lead_score': contact[8],
                    'qualification_status': contact[9],
                    'estimated_value': contact[10],
                    'priority_tier': contact[11],
                    'next_action': contact[12],
                    'next_action_date': contact[13],
                    'created_at': contact[14],
                    'updated_at': contact[15],
                    'notes': contact[16]
                }
                self.replicate_crm_contact(contact_dict)

        sqlite_conn.close()
        logger.info(f"✅ Sync completed: {len(contacts)} contacts updated")


# Global replicator instance
_replicator: PostgreSQLReplicator | None = None


def enable_dual_write():
    """Enable PostgreSQL dual-write mode"""
    global _replicator
    if _replicator is None:
        _replicator = PostgreSQLReplicator()
        _replicator.connect()
        logger.info("✅ Epic 7 PostgreSQL dual-write ENABLED")
    return _replicator


def disable_dual_write():
    """Disable PostgreSQL dual-write mode"""
    global _replicator
    if _replicator:
        _replicator.disconnect()
        _replicator = None
        logger.info("Epic 7 PostgreSQL dual-write DISABLED")


@contextmanager
def dual_write_context(sqlite_db_path: str):
    """Context manager for dual-write operations"""
    replicator = enable_dual_write()
    try:
        # Sync any recent changes before starting
        replicator.sync_all_recent_changes(sqlite_db_path)
        yield replicator
    finally:
        disable_dual_write()


if __name__ == "__main__":
    # Test dual-write functionality

    sqlite_path = "business_development/epic7_sales_automation.db"

    logger.info("Testing Epic 7 PostgreSQL dual-write layer...")

    with dual_write_context(sqlite_path) as replicator:
        logger.info("✅ Dual-write context active")
        logger.info("✅ Recent changes synced")

    logger.info("✅ Dual-write test completed successfully")
