"""
Pipeline data validation for Epic 7 sales automation migration.
Validates the $1.158M sales pipeline data integrity during consolidation.
"""

import sqlite3
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import field


@dataclass
class ValidationResult:
    """Result of pipeline validation"""
    contact_count: int
    total_value: Decimal
    is_valid: bool
    errors: List[str] = field(default_factory=list)


class PipelineValidator:
    """Validates Epic 7 sales pipeline data integrity"""

    def __init__(self, epic7_db_path: str):
        self.epic7_db_path = Path(epic7_db_path)
        if not self.epic7_db_path.exists():
            raise FileNotFoundError(f"Epic 7 database not found: {epic7_db_path}")

    def validate_pipeline_integrity(self) -> ValidationResult:
        """
        Validate the complete Epic 7 sales pipeline integrity.
        Returns validation result with contact count, total value, and any errors.
        """
        try:
            with sqlite3.connect(str(self.epic7_db_path)) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()

                # Get contact count and total estimated value
                cursor.execute("""
                    SELECT COUNT(*) as contact_count,
                           COALESCE(SUM(estimated_value), 0) as total_value
                    FROM crm_contacts
                    WHERE qualification_status IN ('qualified', 'customer')
                """)

                row = cursor.fetchone()
                contact_count = row['contact_count']
                total_value = Decimal(str(row['total_value'] or 0))

                # Validate business rules
                errors = []
                is_valid = True

                # Check minimum pipeline value ($1.158M target)
                if total_value < Decimal('1158000.00'):
                    errors.append(f"Pipeline value ${total_value} below target $1,158,000")
                    is_valid = False

                # Check for data consistency
                cursor.execute("""
                    SELECT COUNT(*) as orphaned_pipeline
                    FROM sales_pipeline sp
                    LEFT JOIN crm_contacts cc ON sp.contact_id = cc.contact_id
                    WHERE cc.contact_id IS NULL
                """)

                orphaned_count = cursor.fetchone()['orphaned_pipeline']
                if orphaned_count > 0:
                    errors.append(f"Found {orphaned_count} orphaned pipeline entries")
                    is_valid = False

                # Check for contacts without required fields
                cursor.execute("""
                    SELECT COUNT(*) as incomplete_contacts
                    FROM crm_contacts
                    WHERE email IS NULL OR email = ''
                       OR name IS NULL OR name = ''
                """)

                incomplete_count = cursor.fetchone()['incomplete_contacts']
                if incomplete_count > 0:
                    errors.append(f"Found {incomplete_count} contacts with missing required fields")
                    is_valid = False

                return ValidationResult(
                    contact_count=contact_count,
                    total_value=total_value,
                    is_valid=is_valid,
                    errors=errors
                )

        except sqlite3.Error as e:
            return ValidationResult(
                contact_count=0,
                total_value=Decimal('0'),
                is_valid=False,
                errors=[f"Database error: {str(e)}"]
            )

    def get_pipeline_summary(self) -> Dict:
        """Get detailed pipeline summary for reporting"""
        try:
            with sqlite3.connect(str(self.epic7_db_path)) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()

                # Get breakdown by priority tier
                cursor.execute("""
                    SELECT priority_tier,
                           COUNT(*) as contact_count,
                           SUM(estimated_value) as total_value
                    FROM crm_contacts
                    WHERE qualification_status IN ('qualified', 'customer')
                    GROUP BY priority_tier
                    ORDER BY total_value DESC
                """)

                tier_breakdown = {}
                for row in cursor.fetchall():
                    tier_breakdown[row['priority_tier']] = {
                        'contacts': row['contact_count'],
                        'value': Decimal(str(row['total_value'] or 0))
                    }

                # Get pipeline stage distribution
                cursor.execute("""
                    SELECT sp.stage, COUNT(*) as count, SUM(sp.deal_value * sp.probability) as weighted_value
                    FROM sales_pipeline sp
                    JOIN crm_contacts cc ON sp.contact_id = cc.contact_id
                    WHERE cc.qualification_status IN ('qualified', 'customer')
                    GROUP BY sp.stage
                """)

                stage_breakdown = {}
                for row in cursor.fetchall():
                    stage_breakdown[row['stage']] = {
                        'count': row['count'],
                        'weighted_value': Decimal(str(row['weighted_value'] or 0))
                    }

                return {
                    'tier_breakdown': tier_breakdown,
                    'stage_breakdown': stage_breakdown,
                    'total_contacts': sum(t['contacts'] for t in tier_breakdown.values()),
                    'total_value': sum(t['value'] for t in tier_breakdown.values())
                }

        except sqlite3.Error as e:
            return {'error': str(e)}

    def export_pipeline_data(self, output_path: str) -> bool:
        """Export pipeline data for backup/archival"""
        try:
            with sqlite3.connect(str(self.epic7_db_path)) as conn:
                # Export to CSV for backup
                with open(output_path, 'w') as f:
                    # Export contacts
                    cursor = conn.cursor()
                    cursor.execute("""
                        SELECT contact_id, name, company, title, email, lead_score,
                               estimated_value, priority_tier, qualification_status,
                               created_at, updated_at
                        FROM crm_contacts
                        WHERE qualification_status IN ('qualified', 'customer')
                        ORDER BY estimated_value DESC
                    """)

                    f.write("CONTACTS\n")
                    f.write("contact_id,name,company,title,email,lead_score,estimated_value,priority_tier,qualification_status,created_at,updated_at\n")

                    for row in cursor.fetchall():
                        f.write(','.join(str(field) for field in row) + '\n')

                    f.write("\nPIPELINE\n")
                    f.write("pipeline_id,contact_id,stage,probability,expected_close_date,deal_value,notes,created_at,updated_at\n")

                    cursor.execute("""
                        SELECT sp.pipeline_id, sp.contact_id, sp.stage, sp.probability,
                               sp.expected_close_date, sp.deal_value, sp.notes,
                               sp.created_at, sp.updated_at
                        FROM sales_pipeline sp
                        JOIN crm_contacts cc ON sp.contact_id = cc.contact_id
                        WHERE cc.qualification_status IN ('qualified', 'customer')
                        ORDER BY sp.deal_value DESC
                    """)

                    for row in cursor.fetchall():
                        f.write(','.join(str(field or '') for field in row) + '\n')

            return True

        except Exception as e:
            print(f"Export failed: {e}")
            return False


def main():
    """Command-line validation of Epic 7 pipeline"""
    import sys

    if len(sys.argv) != 2:
        print("Usage: python pipeline_validator.py <epic7_db_path>")
        sys.exit(1)

    db_path = sys.argv[1]
    validator = PipelineValidator(db_path)

    print("🔍 Validating Epic 7 Sales Pipeline Integrity")
    print("=" * 50)

    result = validator.validate_pipeline_integrity()

    print(f"📊 Contacts: {result.contact_count}")
    print(f"💰 Total Value: ${result.total_value:,.2f}")
    print(f"✅ Valid: {result.is_valid}")

    if result.errors:
        print("\n❌ Errors:")
        for error in result.errors:
            print(f"  - {error}")

    print("\n📈 Pipeline Summary:")
    summary = validator.get_pipeline_summary()
    if 'error' not in summary:
        print("Priority Tiers:")
        for tier, data in summary['tier_breakdown'].items():
            print(f"  {tier}: {data['contacts']} contacts, ${data['value']:,.2f}")

        print("\nPipeline Stages:")
        for stage, data in summary['stage_breakdown'].items():
            print(f"  {stage}: {data['count']} deals, ${data['weighted_value']:,.2f}")

    # Export backup
    backup_path = f"{db_path}.pipeline_backup.csv"
    if validator.export_pipeline_data(backup_path):
        print(f"\n💾 Backup exported to: {backup_path}")
    else:
        print("\n❌ Backup export failed")


if __name__ == "__main__":
    main()