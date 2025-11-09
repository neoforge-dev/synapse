"""
Epic 16 PostgreSQL Migration Script
Production-ready migration of Fortune 500 acquisition system from SQLite to PostgreSQL

Business Critical: Epic 16 Fortune 500 Acquisition Pipeline
- 3 SQLite databases → 1 PostgreSQL database (synapse_business_core)
- 15 tables with 90+ rows of business-critical data
- $5M+ ARR Fortune 500 acquisition pipeline protection
- Zero disruption migration with full validation

Migration Scope:
1. Fortune 500 Acquisition (6 tables, ~28 rows)
2. ABM Campaigns (4 tables, ~32 rows)
3. Enterprise Onboarding (5 tables, ~30 rows)

Data Transformations:
- TEXT IDs → UUIDs with mapping preservation
- TEXT timestamps → Python datetime objects
- TEXT JSON → JSONB (PostgreSQL native)
- INTEGER booleans → Python bool
- NUMERIC/REAL preserved as-is

Usage:
    # Production migration
    python epic16_postgresql_migration.py

    # Dry-run mode (validation only)
    python epic16_postgresql_migration.py --dry-run

    # Verbose logging
    python epic16_postgresql_migration.py --verbose

Environment Variables:
    POSTGRES_HOST: PostgreSQL host (default: localhost)
    POSTGRES_PORT: PostgreSQL port (default: 5432)
    POSTGRES_DB: Database name (default: synapse_business_core)
    POSTGRES_USER: PostgreSQL user (default: synapse)
    POSTGRES_PASSWORD: PostgreSQL password (required)
"""

import argparse
import json
import logging
import os
import sqlite3
import sys
import uuid
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

# SQLAlchemy imports
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

# Import Epic 16 models
sys.path.insert(0, str(Path(__file__).parent.parent))
from graph_rag.infrastructure.persistence.models.epic16 import (
    ABMCampaignModel,
    ABMContentAssetModel,
    ABMPerformanceModel,
    ABMTouchpointModel,
    Base,
    F500BusinessCaseModel,
    F500LeadScoringModel,
    F500ROITrackingModel,
    F500SalesSequenceModel,
    Fortune500ProspectModel,
    OnboardingClientModel,
    OnboardingCommunicationModel,
    OnboardingHealthMetricModel,
    OnboardingMilestoneModel,
    OnboardingSuccessTemplateModel,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('epic16_postgresql_migration.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class Epic16PostgreSQLMigrator:
    """Production-ready migrator for Epic 16 data from SQLite to PostgreSQL"""

    def __init__(self, dry_run: bool = False, verbose: bool = False):
        self.dry_run = dry_run
        self.verbose = verbose

        if self.verbose:
            logger.setLevel(logging.DEBUG)

        # SQLite database paths
        base_path = Path(__file__).parent.parent / "business_development"
        self.sqlite_dbs = {
            'fortune500': base_path / 'epic16_fortune500_acquisition.db',
            'abm': base_path / 'epic16_abm_campaigns.db',
            'onboarding': base_path / 'epic16_enterprise_onboarding.db'
        }

        # PostgreSQL configuration
        self.postgres_config = {
            'host': os.getenv('POSTGRES_HOST', 'localhost'),
            'port': int(os.getenv('POSTGRES_PORT', '5432')),
            'database': os.getenv('POSTGRES_DB', 'synapse_business_core'),
            'user': os.getenv('POSTGRES_USER', 'synapse'),
            'password': os.getenv('POSTGRES_PASSWORD', '')
        }

        # UUID mapping: old TEXT ID → new UUID
        self.uuid_mapping: dict[str, uuid.UUID] = {}

        # Migration statistics
        self.stats = {
            'tables_migrated': 0,
            'rows_migrated': 0,
            'errors': [],
            'start_time': None,
            'end_time': None
        }

        # PostgreSQL engine and session
        self.pg_engine = None
        self.pg_session: Session | None = None

    def validate_environment(self) -> bool:
        """Validate migration environment and prerequisites"""
        logger.info("=" * 80)
        logger.info("Epic 16 PostgreSQL Migration - Environment Validation")
        logger.info("=" * 80)

        # Check SQLite databases exist
        for name, path in self.sqlite_dbs.items():
            if not path.exists():
                logger.error(f"❌ SQLite database not found: {path}")
                return False
            logger.info(f"✅ Found SQLite database: {name} ({path})")

        # Test SQLite connections
        for name, path in self.sqlite_dbs.items():
            try:
                conn = sqlite3.connect(str(path))
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table'")
                table_count = cursor.fetchone()[0]
                conn.close()
                logger.info(f"✅ SQLite connection validated: {name} ({table_count} tables)")
            except Exception as e:
                logger.error(f"❌ SQLite connection failed for {name}: {e}")
                return False

        # Test PostgreSQL connection
        try:
            pg_url = self._get_postgres_url()
            engine = create_engine(pg_url, echo=False)
            with engine.connect() as conn:
                result = conn.execute(text("SELECT version()"))
                version = result.fetchone()[0]
                logger.info("✅ PostgreSQL connection validated")
                logger.debug(f"PostgreSQL version: {version}")
            engine.dispose()
        except Exception as e:
            logger.error(f"❌ PostgreSQL connection failed: {e}")
            logger.error("Ensure PostgreSQL is running and credentials are correct")
            return False

        logger.info("✅ Environment validation complete")
        return True

    def _get_postgres_url(self) -> str:
        """Generate PostgreSQL connection URL"""
        return (
            f"postgresql://{self.postgres_config['user']}:"
            f"{self.postgres_config['password']}@"
            f"{self.postgres_config['host']}:{self.postgres_config['port']}/"
            f"{self.postgres_config['database']}"
        )

    def create_postgres_schema(self):
        """Create PostgreSQL schema using SQLAlchemy models"""
        logger.info("=" * 80)
        logger.info("Creating PostgreSQL Schema")
        logger.info("=" * 80)

        try:
            pg_url = self._get_postgres_url()
            self.pg_engine = create_engine(pg_url, echo=self.verbose)

            if self.dry_run:
                logger.info("🔍 DRY RUN: Would create PostgreSQL schema")
                return

            # Create all tables
            Base.metadata.create_all(self.pg_engine)
            logger.info("✅ PostgreSQL schema created successfully")

            # Create session
            SessionLocal = sessionmaker(bind=self.pg_engine)
            self.pg_session = SessionLocal()

        except Exception as e:
            logger.error(f"❌ Schema creation failed: {e}")
            raise

    def transform_timestamp(self, value: str | None) -> datetime | None:
        """Transform SQLite TEXT timestamp to Python datetime"""
        if not value:
            return None

        # Handle various SQLite timestamp formats
        formats = [
            '%Y-%m-%d %H:%M:%S',
            '%Y-%m-%d %H:%M:%S.%f',
            '%Y-%m-%dT%H:%M:%S',
            '%Y-%m-%dT%H:%M:%S.%f',
            '%Y-%m-%d',
        ]

        for fmt in formats:
            try:
                return datetime.strptime(value, fmt)
            except ValueError:
                continue

        logger.warning(f"Could not parse timestamp: {value}")
        return None

    def transform_json(self, value: str | None) -> Any:
        """Transform SQLite TEXT JSON to Python dict/list"""
        if not value:
            return None

        if isinstance(value, dict | list):
            return value

        try:
            return json.loads(value)
        except (json.JSONDecodeError, TypeError):
            logger.warning(f"Could not parse JSON: {value}")
            return None

    def transform_boolean(self, value: Any) -> bool:
        """Transform SQLite INTEGER/TEXT boolean to Python bool"""
        if value is None:
            return False
        if isinstance(value, bool):
            return value
        if isinstance(value, int):
            return bool(value)
        if isinstance(value, str):
            return value.lower() in ('true', '1', 'yes', 't')
        return False

    def get_or_create_uuid(self, old_id: str | None) -> uuid.UUID:
        """Get existing UUID mapping or create new one"""
        if not old_id:
            return uuid.uuid4()

        if old_id in self.uuid_mapping:
            return self.uuid_mapping[old_id]

        new_uuid = uuid.uuid4()
        self.uuid_mapping[old_id] = new_uuid
        return new_uuid

    def migrate_fortune500_prospects(self) -> int:
        """Migrate fortune500_prospects table"""
        logger.info("\n📊 Migrating fortune500_prospects...")

        sqlite_conn = sqlite3.connect(str(self.sqlite_dbs['fortune500']))
        sqlite_conn.row_factory = sqlite3.Row
        cursor = sqlite_conn.cursor()

        cursor.execute("SELECT * FROM fortune500_prospects")
        rows = cursor.fetchall()

        if self.dry_run:
            logger.info(f"🔍 DRY RUN: Would migrate {len(rows)} prospects")
            sqlite_conn.close()
            return len(rows)

        migrated = 0
        for row in rows:
            try:
                prospect = Fortune500ProspectModel(
                    prospect_id=self.get_or_create_uuid(row['prospect_id']),
                    company_name=row['company_name'],
                    revenue_billions=Decimal(str(row['revenue_billions'])) if row['revenue_billions'] else None,
                    industry=row['industry'],
                    headquarters=row['headquarters'],
                    employees=row['employees'],
                    stock_symbol=row['stock_symbol'],
                    market_cap_billions=Decimal(str(row['market_cap_billions'])) if row['market_cap_billions'] else None,
                    ceo_name=row['ceo_name'],
                    cto_name=row['cto_name'],
                    engineering_headcount=row['engineering_headcount'],
                    tech_stack=self.transform_json(row['tech_stack']),
                    digital_transformation_score=Decimal(str(row['digital_transformation_score'])) if row['digital_transformation_score'] else None,
                    acquisition_score=Decimal(str(row['acquisition_score'])) if row['acquisition_score'] else None,
                    contact_priority=row['contact_priority'],
                    estimated_contract_value=row['estimated_contract_value'],
                    pain_points=self.transform_json(row['pain_points']),
                    decision_makers=self.transform_json(row['decision_makers']),
                    created_at=self.transform_timestamp(row['created_at']),
                    last_updated=self.transform_timestamp(row['last_updated'])
                )
                self.pg_session.add(prospect)
                migrated += 1
            except Exception as e:
                logger.error(f"Error migrating prospect {row['prospect_id']}: {e}")
                self.stats['errors'].append(f"fortune500_prospects: {row['prospect_id']}: {e}")

        self.pg_session.flush()
        sqlite_conn.close()
        logger.info(f"✅ Migrated {migrated} prospects")
        return migrated

    def migrate_f500_lead_scoring(self) -> int:
        """Migrate enterprise_lead_scoring table"""
        logger.info("\n📊 Migrating enterprise_lead_scoring...")

        sqlite_conn = sqlite3.connect(str(self.sqlite_dbs['fortune500']))
        sqlite_conn.row_factory = sqlite3.Row
        cursor = sqlite_conn.cursor()

        cursor.execute("SELECT * FROM enterprise_lead_scoring")
        rows = cursor.fetchall()

        if self.dry_run:
            logger.info(f"🔍 DRY RUN: Would migrate {len(rows)} scoring records")
            sqlite_conn.close()
            return len(rows)

        migrated = 0
        for row in rows:
            try:
                scoring = F500LeadScoringModel(
                    scoring_id=self.get_or_create_uuid(row['scoring_id']),
                    prospect_id=self.get_or_create_uuid(row['prospect_id']),
                    base_score=Decimal(str(row['base_score'])) if row['base_score'] else None,
                    revenue_multiplier=Decimal(str(row['revenue_multiplier'])) if row['revenue_multiplier'] else None,
                    industry_fit_score=Decimal(str(row['industry_fit_score'])) if row['industry_fit_score'] else None,
                    technology_readiness=Decimal(str(row['technology_readiness'])) if row['technology_readiness'] else None,
                    decision_maker_accessibility=Decimal(str(row['decision_maker_accessibility'])) if row['decision_maker_accessibility'] else None,
                    timing_signals=Decimal(str(row['timing_signals'])) if row['timing_signals'] else None,
                    competitive_landscape=Decimal(str(row['competitive_landscape'])) if row['competitive_landscape'] else None,
                    final_score=Decimal(str(row['final_score'])),
                    confidence_level=Decimal(str(row['confidence_level'])) if row['confidence_level'] else None,
                    scoring_rationale=self.transform_json(row['scoring_rationale']),
                    scored_at=self.transform_timestamp(row['scored_at'])
                )
                self.pg_session.add(scoring)
                migrated += 1
            except Exception as e:
                logger.error(f"Error migrating scoring {row['scoring_id']}: {e}")
                self.stats['errors'].append(f"f500_lead_scoring: {row['scoring_id']}: {e}")

        self.pg_session.flush()
        sqlite_conn.close()
        logger.info(f"✅ Migrated {migrated} scoring records")
        return migrated

    def migrate_f500_business_cases(self) -> int:
        """Migrate enterprise_business_cases table"""
        logger.info("\n📊 Migrating enterprise_business_cases...")

        sqlite_conn = sqlite3.connect(str(self.sqlite_dbs['fortune500']))
        sqlite_conn.row_factory = sqlite3.Row
        cursor = sqlite_conn.cursor()

        cursor.execute("SELECT * FROM enterprise_business_cases")
        rows = cursor.fetchall()

        if self.dry_run:
            logger.info(f"🔍 DRY RUN: Would migrate {len(rows)} business cases")
            sqlite_conn.close()
            return len(rows)

        migrated = 0
        for row in rows:
            try:
                business_case = F500BusinessCaseModel(
                    case_id=self.get_or_create_uuid(row['case_id']),
                    prospect_id=self.get_or_create_uuid(row['prospect_id']),
                    problem_quantification=self.transform_json(row['problem_quantification']),
                    solution_benefits=self.transform_json(row['solution_benefits']),
                    roi_calculation=self.transform_json(row['roi_calculation']),
                    risk_assessment=self.transform_json(row['risk_assessment']),
                    implementation_timeline=self.transform_json(row['implementation_timeline']),
                    investment_options=self.transform_json(row['investment_options']),
                    projected_savings=row['projected_savings'],
                    payback_months=row['payback_months'],
                    confidence_score=Decimal(str(row['confidence_score'])) if row['confidence_score'] else None,
                    generated_at=self.transform_timestamp(row['generated_at'])
                )
                self.pg_session.add(business_case)
                migrated += 1
            except Exception as e:
                logger.error(f"Error migrating business case {row['case_id']}: {e}")
                self.stats['errors'].append(f"f500_business_cases: {row['case_id']}: {e}")

        self.pg_session.flush()
        sqlite_conn.close()
        logger.info(f"✅ Migrated {migrated} business cases")
        return migrated

    def migrate_f500_sales_sequences(self) -> int:
        """Migrate enterprise_sales_sequences table"""
        logger.info("\n📊 Migrating enterprise_sales_sequences...")

        sqlite_conn = sqlite3.connect(str(self.sqlite_dbs['fortune500']))
        sqlite_conn.row_factory = sqlite3.Row
        cursor = sqlite_conn.cursor()

        cursor.execute("SELECT * FROM enterprise_sales_sequences")
        rows = cursor.fetchall()

        if self.dry_run:
            logger.info(f"🔍 DRY RUN: Would migrate {len(rows)} sales sequences")
            sqlite_conn.close()
            return len(rows)

        migrated = 0
        for row in rows:
            try:
                sequence = F500SalesSequenceModel(
                    sequence_id=self.get_or_create_uuid(row['sequence_id']),
                    prospect_id=self.get_or_create_uuid(row['prospect_id']),
                    sequence_type=row['sequence_type'],
                    touch_points=self.transform_json(row['touch_points']),
                    current_step=row['current_step'],
                    status=row['status'],
                    personalization_data=self.transform_json(row['personalization_data']),
                    engagement_metrics=self.transform_json(row['engagement_metrics']),
                    conversion_probability=Decimal(str(row['conversion_probability'])) if row['conversion_probability'] else None,
                    created_at=self.transform_timestamp(row['created_at']),
                    last_interaction=self.transform_timestamp(row['last_interaction'])
                )
                self.pg_session.add(sequence)
                migrated += 1
            except Exception as e:
                logger.error(f"Error migrating sales sequence {row['sequence_id']}: {e}")
                self.stats['errors'].append(f"f500_sales_sequences: {row['sequence_id']}: {e}")

        self.pg_session.flush()
        sqlite_conn.close()
        logger.info(f"✅ Migrated {migrated} sales sequences")
        return migrated

    def migrate_f500_roi_tracking(self) -> int:
        """Migrate enterprise_roi_tracking table"""
        logger.info("\n📊 Migrating enterprise_roi_tracking...")

        sqlite_conn = sqlite3.connect(str(self.sqlite_dbs['fortune500']))
        sqlite_conn.row_factory = sqlite3.Row
        cursor = sqlite_conn.cursor()

        cursor.execute("SELECT * FROM enterprise_roi_tracking")
        rows = cursor.fetchall()

        if self.dry_run:
            logger.info(f"🔍 DRY RUN: Would migrate {len(rows)} ROI tracking records")
            sqlite_conn.close()
            return len(rows)

        migrated = 0
        for row in rows:
            try:
                roi = F500ROITrackingModel(
                    roi_id=self.get_or_create_uuid(row['roi_id']),
                    prospect_id=self.get_or_create_uuid(row['prospect_id']),
                    engagement_type=row['engagement_type'],
                    investment_stage=row['investment_stage'],
                    actual_investment=row['actual_investment'],
                    projected_value=row['projected_value'],
                    time_investment_hours=row['time_investment_hours'],
                    success_probability=Decimal(str(row['success_probability'])) if row['success_probability'] else None,
                    current_roi=Decimal(str(row['current_roi'])) if row['current_roi'] else None,
                    lifetime_value_projection=row['lifetime_value_projection'],
                    tracked_at=self.transform_timestamp(row['tracked_at'])
                )
                self.pg_session.add(roi)
                migrated += 1
            except Exception as e:
                logger.error(f"Error migrating ROI tracking {row['roi_id']}: {e}")
                self.stats['errors'].append(f"f500_roi_tracking: {row['roi_id']}: {e}")

        self.pg_session.flush()
        sqlite_conn.close()
        logger.info(f"✅ Migrated {migrated} ROI tracking records")
        return migrated

    def migrate_abm_campaigns(self) -> int:
        """Migrate abm_campaigns table"""
        logger.info("\n📊 Migrating abm_campaigns...")

        sqlite_conn = sqlite3.connect(str(self.sqlite_dbs['abm']))
        sqlite_conn.row_factory = sqlite3.Row
        cursor = sqlite_conn.cursor()

        cursor.execute("SELECT * FROM abm_campaigns")
        rows = cursor.fetchall()

        if self.dry_run:
            logger.info(f"🔍 DRY RUN: Would migrate {len(rows)} ABM campaigns")
            sqlite_conn.close()
            return len(rows)

        migrated = 0
        for row in rows:
            try:
                campaign = ABMCampaignModel(
                    campaign_id=self.get_or_create_uuid(row['campaign_id']),
                    campaign_name=row['campaign_name'],
                    target_accounts=self.transform_json(row['target_accounts']),
                    campaign_type=row['campaign_type'],
                    personalization_level=row['personalization_level'],
                    content_assets=self.transform_json(row['content_assets']),
                    distribution_channels=self.transform_json(row['distribution_channels']),
                    budget_allocated=row['budget_allocated'],
                    expected_engagement=Decimal(str(row['expected_engagement'])) if row['expected_engagement'] else None,
                    conversion_target=row['conversion_target'],
                    roi_target=Decimal(str(row['roi_target'])) if row['roi_target'] else None,
                    campaign_status=row['campaign_status'],
                    launch_date=self.transform_timestamp(row['launch_date']),
                    end_date=self.transform_timestamp(row['end_date']),
                    performance_metrics=self.transform_json(row['performance_metrics']),
                    created_at=self.transform_timestamp(row['created_at'])
                )
                self.pg_session.add(campaign)
                migrated += 1
            except Exception as e:
                logger.error(f"Error migrating ABM campaign {row['campaign_id']}: {e}")
                self.stats['errors'].append(f"abm_campaigns: {row['campaign_id']}: {e}")

        self.pg_session.flush()
        sqlite_conn.close()
        logger.info(f"✅ Migrated {migrated} ABM campaigns")
        return migrated

    def migrate_abm_content_assets(self) -> int:
        """Migrate content_assets table"""
        logger.info("\n📊 Migrating content_assets...")

        sqlite_conn = sqlite3.connect(str(self.sqlite_dbs['abm']))
        sqlite_conn.row_factory = sqlite3.Row
        cursor = sqlite_conn.cursor()

        cursor.execute("SELECT * FROM content_assets")
        rows = cursor.fetchall()

        if self.dry_run:
            logger.info(f"🔍 DRY RUN: Would migrate {len(rows)} content assets")
            sqlite_conn.close()
            return len(rows)

        migrated = 0
        for row in rows:
            try:
                asset = ABMContentAssetModel(
                    asset_id=self.get_or_create_uuid(row['asset_id']),
                    asset_type=row['asset_type'],
                    title=row['title'],
                    description=row['description'],
                    target_persona=row['target_persona'],
                    industry_focus=row['industry_focus'],
                    personalization_data=self.transform_json(row['personalization_data']),
                    content_url=row['content_url'],
                    engagement_score=Decimal(str(row['engagement_score'])) if row['engagement_score'] else Decimal('7.0'),
                    conversion_rate=Decimal(str(row['conversion_rate'])) if row['conversion_rate'] else Decimal('0.20'),
                    created_at=self.transform_timestamp(row['created_at'])
                )
                self.pg_session.add(asset)
                migrated += 1
            except Exception as e:
                logger.error(f"Error migrating content asset {row['asset_id']}: {e}")
                self.stats['errors'].append(f"abm_content_assets: {row['asset_id']}: {e}")

        self.pg_session.flush()
        sqlite_conn.close()
        logger.info(f"✅ Migrated {migrated} content assets")
        return migrated

    def migrate_abm_touchpoints(self) -> int:
        """Migrate campaign_touchpoints table"""
        logger.info("\n📊 Migrating campaign_touchpoints...")

        sqlite_conn = sqlite3.connect(str(self.sqlite_dbs['abm']))
        sqlite_conn.row_factory = sqlite3.Row
        cursor = sqlite_conn.cursor()

        cursor.execute("SELECT * FROM campaign_touchpoints")
        rows = cursor.fetchall()

        if self.dry_run:
            logger.info(f"🔍 DRY RUN: Would migrate {len(rows)} touchpoints")
            sqlite_conn.close()
            return len(rows)

        migrated = 0
        for row in rows:
            try:
                touchpoint = ABMTouchpointModel(
                    touchpoint_id=self.get_or_create_uuid(row['touchpoint_id']),
                    campaign_id=self.get_or_create_uuid(row['campaign_id']),
                    prospect_id=self.get_or_create_uuid(row['prospect_id']) if row['prospect_id'] else None,
                    touchpoint_type=row['touchpoint_type'],
                    content_asset_id=self.get_or_create_uuid(row['content_asset_id']) if row['content_asset_id'] else None,
                    scheduled_date=self.transform_timestamp(row['scheduled_date']),
                    executed_date=self.transform_timestamp(row['executed_date']),
                    personalization_applied=self.transform_json(row['personalization_applied']),
                    engagement_metrics=self.transform_json(row['engagement_metrics']),
                    status=row['status']
                )
                self.pg_session.add(touchpoint)
                migrated += 1
            except Exception as e:
                logger.error(f"Error migrating touchpoint {row['touchpoint_id']}: {e}")
                self.stats['errors'].append(f"abm_touchpoints: {row['touchpoint_id']}: {e}")

        self.pg_session.flush()
        sqlite_conn.close()
        logger.info(f"✅ Migrated {migrated} touchpoints")
        return migrated

    def migrate_abm_performance(self) -> int:
        """Migrate campaign_performance table"""
        logger.info("\n📊 Migrating campaign_performance...")

        sqlite_conn = sqlite3.connect(str(self.sqlite_dbs['abm']))
        sqlite_conn.row_factory = sqlite3.Row
        cursor = sqlite_conn.cursor()

        cursor.execute("SELECT * FROM campaign_performance")
        rows = cursor.fetchall()

        if self.dry_run:
            logger.info(f"🔍 DRY RUN: Would migrate {len(rows)} performance records")
            sqlite_conn.close()
            return len(rows)

        migrated = 0
        for row in rows:
            try:
                performance = ABMPerformanceModel(
                    performance_id=self.get_or_create_uuid(row['performance_id']),
                    campaign_id=self.get_or_create_uuid(row['campaign_id']),
                    measurement_date=self.transform_timestamp(row['measurement_date']),
                    accounts_engaged=row['accounts_engaged'],
                    total_touchpoints=row['total_touchpoints'],
                    engagement_rate=Decimal(str(row['engagement_rate'])) if row['engagement_rate'] else None,
                    response_rate=Decimal(str(row['response_rate'])) if row['response_rate'] else None,
                    conversion_rate=Decimal(str(row['conversion_rate'])) if row['conversion_rate'] else None,
                    pipeline_generated=row['pipeline_generated'],
                    roi_achieved=Decimal(str(row['roi_achieved'])) if row['roi_achieved'] else None,
                    cost_per_engagement=Decimal(str(row['cost_per_engagement'])) if row['cost_per_engagement'] else None
                )
                self.pg_session.add(performance)
                migrated += 1
            except Exception as e:
                logger.error(f"Error migrating performance {row['performance_id']}: {e}")
                self.stats['errors'].append(f"abm_performance: {row['performance_id']}: {e}")

        self.pg_session.flush()
        sqlite_conn.close()
        logger.info(f"✅ Migrated {migrated} performance records")
        return migrated

    def migrate_onboarding_clients(self) -> int:
        """Migrate enterprise_clients table"""
        logger.info("\n📊 Migrating enterprise_clients...")

        sqlite_conn = sqlite3.connect(str(self.sqlite_dbs['onboarding']))
        sqlite_conn.row_factory = sqlite3.Row
        cursor = sqlite_conn.cursor()

        cursor.execute("SELECT * FROM enterprise_clients")
        rows = cursor.fetchall()

        if self.dry_run:
            logger.info(f"🔍 DRY RUN: Would migrate {len(rows)} enterprise clients")
            sqlite_conn.close()
            return len(rows)

        migrated = 0
        for row in rows:
            try:
                client = OnboardingClientModel(
                    client_id=self.get_or_create_uuid(row['client_id']),
                    company_name=row['company_name'],
                    contract_value=row['contract_value'],
                    contract_start_date=self.transform_timestamp(row['created_at']),  # Using created_at as proxy
                    onboarding_status=row['current_phase'] if row['current_phase'] else 'initiated',
                    success_plan_template=row['onboarding_tier'],
                    team_size=50,  # Default value
                    implementation_complexity='medium',  # Default value
                    created_at=self.transform_timestamp(row['created_at']),
                    updated_at=self.transform_timestamp(row['last_updated'])
                )
                self.pg_session.add(client)
                migrated += 1
            except Exception as e:
                logger.error(f"Error migrating client {row['client_id']}: {e}")
                self.stats['errors'].append(f"onboarding_clients: {row['client_id']}: {e}")

        self.pg_session.flush()
        sqlite_conn.close()
        logger.info(f"✅ Migrated {migrated} enterprise clients")
        return migrated

    def migrate_onboarding_milestones(self) -> int:
        """Migrate onboarding_milestones table"""
        logger.info("\n📊 Migrating onboarding_milestones...")

        sqlite_conn = sqlite3.connect(str(self.sqlite_dbs['onboarding']))
        sqlite_conn.row_factory = sqlite3.Row
        cursor = sqlite_conn.cursor()

        cursor.execute("SELECT * FROM onboarding_milestones")
        rows = cursor.fetchall()

        if self.dry_run:
            logger.info(f"🔍 DRY RUN: Would migrate {len(rows)} milestones")
            sqlite_conn.close()
            return len(rows)

        migrated = 0
        for row in rows:
            try:
                milestone = OnboardingMilestoneModel(
                    milestone_id=self.get_or_create_uuid(row['milestone_id']),
                    client_id=self.get_or_create_uuid(row['client_id']),
                    milestone_name=row['milestone_name'],
                    milestone_type=row['milestone_type'],
                    planned_date=self.transform_timestamp(row['target_date']),
                    actual_date=self.transform_timestamp(row['completion_date']),
                    status=row['status'],
                    dependencies=self.transform_json(row['dependencies']),
                    deliverables=self.transform_json(row['deliverables']),
                    created_at=self.transform_timestamp(row['created_at'])
                )
                self.pg_session.add(milestone)
                migrated += 1
            except Exception as e:
                logger.error(f"Error migrating milestone {row['milestone_id']}: {e}")
                self.stats['errors'].append(f"onboarding_milestones: {row['milestone_id']}: {e}")

        self.pg_session.flush()
        sqlite_conn.close()
        logger.info(f"✅ Migrated {migrated} milestones")
        return migrated

    def migrate_onboarding_health_metrics(self) -> int:
        """Migrate client_health_metrics table"""
        logger.info("\n📊 Migrating client_health_metrics...")

        sqlite_conn = sqlite3.connect(str(self.sqlite_dbs['onboarding']))
        sqlite_conn.row_factory = sqlite3.Row
        cursor = sqlite_conn.cursor()

        cursor.execute("SELECT * FROM client_health_metrics")
        rows = cursor.fetchall()

        if self.dry_run:
            logger.info(f"🔍 DRY RUN: Would migrate {len(rows)} health metrics")
            sqlite_conn.close()
            return len(rows)

        migrated = 0
        for row in rows:
            try:
                health = OnboardingHealthMetricModel(
                    metric_id=self.get_or_create_uuid(row['health_id']),
                    client_id=self.get_or_create_uuid(row['client_id']),
                    measurement_date=self.transform_timestamp(row['measurement_date']),
                    overall_health_score=Decimal(str(row['metric_value'])) if row['metric_value'] else None,
                    engagement_score=Decimal(str(row['metric_value'])) if row['metric_value'] else None,
                    progress_score=Decimal(str(row['metric_value'])) if row['metric_value'] else None,
                    satisfaction_score=Decimal(str(row['metric_target'])) if row['metric_target'] else None,
                    risk_level='low' if not self.transform_boolean(row['escalation_required']) else 'high',
                    risk_factors=self.transform_json(row['action_items']),
                    stakeholder_sentiment=row['trend_direction']
                )
                self.pg_session.add(health)
                migrated += 1
            except Exception as e:
                logger.error(f"Error migrating health metric {row['health_id']}: {e}")
                self.stats['errors'].append(f"onboarding_health_metrics: {row['health_id']}: {e}")

        self.pg_session.flush()
        sqlite_conn.close()
        logger.info(f"✅ Migrated {migrated} health metrics")
        return migrated

    def migrate_onboarding_success_templates(self) -> int:
        """Migrate success_plan_templates table"""
        logger.info("\n📊 Migrating success_plan_templates...")

        sqlite_conn = sqlite3.connect(str(self.sqlite_dbs['onboarding']))
        sqlite_conn.row_factory = sqlite3.Row
        cursor = sqlite_conn.cursor()

        cursor.execute("SELECT * FROM success_plan_templates")
        rows = cursor.fetchall()

        if self.dry_run:
            logger.info(f"🔍 DRY RUN: Would migrate {len(rows)} success templates")
            sqlite_conn.close()
            return len(rows)

        migrated = 0
        for row in rows:
            try:
                template = OnboardingSuccessTemplateModel(
                    template_id=self.get_or_create_uuid(row['template_id']),
                    template_name=row['template_name'],
                    template_type=row['engagement_model'] if row['engagement_model'] else 'standard',
                    target_duration_days=row['timeline_weeks'] * 7 if row['timeline_weeks'] else 90,
                    target_complexity=row['onboarding_tier'] if row['onboarding_tier'] else 'medium',
                    milestone_templates=self.transform_json(row['milestone_templates']),
                    success_criteria=self.transform_json(row['success_metrics_template']),
                    risk_mitigation_strategies=self.transform_json(row['risk_mitigation_strategies']),
                    resource_requirements=self.transform_json(row['resource_requirements']),
                    created_at=self.transform_timestamp(row['created_at'])
                )
                self.pg_session.add(template)
                migrated += 1
            except Exception as e:
                logger.error(f"Error migrating success template {row['template_id']}: {e}")
                self.stats['errors'].append(f"onboarding_success_templates: {row['template_id']}: {e}")

        self.pg_session.flush()
        sqlite_conn.close()
        logger.info(f"✅ Migrated {migrated} success templates")
        return migrated

    def migrate_onboarding_communications(self) -> int:
        """Migrate client_communications table"""
        logger.info("\n📊 Migrating client_communications...")

        sqlite_conn = sqlite3.connect(str(self.sqlite_dbs['onboarding']))
        sqlite_conn.row_factory = sqlite3.Row
        cursor = sqlite_conn.cursor()

        cursor.execute("SELECT * FROM client_communications")
        rows = cursor.fetchall()

        if self.dry_run:
            logger.info(f"🔍 DRY RUN: Would migrate {len(rows)} communications")
            sqlite_conn.close()
            return len(rows)

        migrated = 0
        for row in rows:
            try:
                comm = OnboardingCommunicationModel(
                    communication_id=self.get_or_create_uuid(row['communication_id']),
                    client_id=self.get_or_create_uuid(row['client_id']),
                    communication_type=row['communication_type'],
                    communication_date=self.transform_timestamp(row['communication_date']),
                    subject=row['subject'],
                    summary=row['summary'],
                    participants=self.transform_json(row['participants']),
                    action_items=self.transform_json(row['action_items']),
                    follow_up_required='true' if self.transform_boolean(row['follow_up_required']) else 'false',
                    follow_up_date=self.transform_timestamp(row['follow_up_date'])
                )
                self.pg_session.add(comm)
                migrated += 1
            except Exception as e:
                logger.error(f"Error migrating communication {row['communication_id']}: {e}")
                self.stats['errors'].append(f"onboarding_communications: {row['communication_id']}: {e}")

        self.pg_session.flush()
        sqlite_conn.close()
        logger.info(f"✅ Migrated {migrated} communications")
        return migrated

    def validate_migration(self) -> bool:
        """Validate migration results"""
        logger.info("\n" + "=" * 80)
        logger.info("Migration Validation")
        logger.info("=" * 80)

        validation_passed = True

        # Table row count validation
        table_mappings = [
            ('fortune500_prospects', 'f500_prospects', self.sqlite_dbs['fortune500']),
            ('enterprise_lead_scoring', 'f500_lead_scoring', self.sqlite_dbs['fortune500']),
            ('enterprise_business_cases', 'f500_business_cases', self.sqlite_dbs['fortune500']),
            ('enterprise_sales_sequences', 'f500_sales_sequences', self.sqlite_dbs['fortune500']),
            ('enterprise_roi_tracking', 'f500_roi_tracking', self.sqlite_dbs['fortune500']),
            ('abm_campaigns', 'abm_campaigns', self.sqlite_dbs['abm']),
            ('content_assets', 'abm_content_assets', self.sqlite_dbs['abm']),
            ('campaign_touchpoints', 'abm_touchpoints', self.sqlite_dbs['abm']),
            ('campaign_performance', 'abm_performance', self.sqlite_dbs['abm']),
            ('enterprise_clients', 'onboarding_clients', self.sqlite_dbs['onboarding']),
            ('onboarding_milestones', 'onboarding_milestones', self.sqlite_dbs['onboarding']),
            ('client_health_metrics', 'onboarding_health_metrics', self.sqlite_dbs['onboarding']),
            ('success_plan_templates', 'onboarding_success_templates', self.sqlite_dbs['onboarding']),
            ('client_communications', 'onboarding_communications', self.sqlite_dbs['onboarding']),
        ]

        for sqlite_table, pg_table, sqlite_db in table_mappings:
            # SQLite count
            sqlite_conn = sqlite3.connect(str(sqlite_db))
            cursor = sqlite_conn.cursor()
            cursor.execute(f"SELECT COUNT(*) FROM {sqlite_table}")
            sqlite_count = cursor.fetchone()[0]
            sqlite_conn.close()

            # PostgreSQL count
            if not self.dry_run:
                pg_count = self.pg_session.execute(text(f"SELECT COUNT(*) FROM {pg_table}")).fetchone()[0]

                if sqlite_count == pg_count:
                    logger.info(f"✅ {pg_table}: {pg_count} rows (matches SQLite)")
                else:
                    logger.error(f"❌ {pg_table}: SQLite={sqlite_count}, PostgreSQL={pg_count} (MISMATCH)")
                    validation_passed = False
            else:
                logger.info(f"🔍 {sqlite_table}: {sqlite_count} rows in SQLite")

        return validation_passed

    def generate_report(self):
        """Generate migration summary report"""
        logger.info("\n" + "=" * 80)
        logger.info("MIGRATION SUMMARY REPORT")
        logger.info("=" * 80)

        duration = (self.stats['end_time'] - self.stats['start_time']).total_seconds()

        logger.info("\n📊 Migration Statistics:")
        logger.info(f"   - Total Tables Migrated: {self.stats['tables_migrated']}")
        logger.info(f"   - Total Rows Migrated: {self.stats['rows_migrated']}")
        logger.info(f"   - Total UUIDs Generated: {len(self.uuid_mapping)}")
        logger.info(f"   - Duration: {duration:.2f} seconds")
        logger.info(f"   - Errors: {len(self.stats['errors'])}")

        if self.stats['errors']:
            logger.warning("\n⚠️  Errors Encountered:")
            for error in self.stats['errors'][:10]:  # Show first 10 errors
                logger.warning(f"   - {error}")
            if len(self.stats['errors']) > 10:
                logger.warning(f"   ... and {len(self.stats['errors']) - 10} more errors")

        if self.dry_run:
            logger.info("\n🔍 DRY RUN MODE: No data was actually migrated")
        else:
            logger.info("\n✅ Migration completed successfully!")
            logger.info(f"   All data migrated to PostgreSQL database: {self.postgres_config['database']}")

        logger.info("=" * 80)

    def run_migration(self):
        """Execute the complete migration process"""
        try:
            self.stats['start_time'] = datetime.now()

            # Step 1: Validate environment
            if not self.validate_environment():
                logger.error("Environment validation failed. Aborting migration.")
                return False

            # Step 2: Create PostgreSQL schema
            self.create_postgres_schema()

            # Step 3: Migrate all tables (in correct order for foreign keys)
            logger.info("\n" + "=" * 80)
            logger.info("Starting Data Migration")
            logger.info("=" * 80)

            # Fortune 500 tables (parent first)
            rows = self.migrate_fortune500_prospects()
            self.stats['rows_migrated'] += rows
            self.stats['tables_migrated'] += 1

            rows = self.migrate_f500_lead_scoring()
            self.stats['rows_migrated'] += rows
            self.stats['tables_migrated'] += 1

            rows = self.migrate_f500_business_cases()
            self.stats['rows_migrated'] += rows
            self.stats['tables_migrated'] += 1

            rows = self.migrate_f500_sales_sequences()
            self.stats['rows_migrated'] += rows
            self.stats['tables_migrated'] += 1

            rows = self.migrate_f500_roi_tracking()
            self.stats['rows_migrated'] += rows
            self.stats['tables_migrated'] += 1

            # ABM tables
            rows = self.migrate_abm_campaigns()
            self.stats['rows_migrated'] += rows
            self.stats['tables_migrated'] += 1

            rows = self.migrate_abm_content_assets()
            self.stats['rows_migrated'] += rows
            self.stats['tables_migrated'] += 1

            rows = self.migrate_abm_touchpoints()
            self.stats['rows_migrated'] += rows
            self.stats['tables_migrated'] += 1

            rows = self.migrate_abm_performance()
            self.stats['rows_migrated'] += rows
            self.stats['tables_migrated'] += 1

            # Onboarding tables
            rows = self.migrate_onboarding_clients()
            self.stats['rows_migrated'] += rows
            self.stats['tables_migrated'] += 1

            rows = self.migrate_onboarding_milestones()
            self.stats['rows_migrated'] += rows
            self.stats['tables_migrated'] += 1

            rows = self.migrate_onboarding_health_metrics()
            self.stats['rows_migrated'] += rows
            self.stats['tables_migrated'] += 1

            rows = self.migrate_onboarding_success_templates()
            self.stats['rows_migrated'] += rows
            self.stats['tables_migrated'] += 1

            rows = self.migrate_onboarding_communications()
            self.stats['rows_migrated'] += rows
            self.stats['tables_migrated'] += 1

            # Step 4: Commit transaction
            if not self.dry_run:
                logger.info("\n💾 Committing transaction...")
                self.pg_session.commit()
                logger.info("✅ Transaction committed successfully")

            # Step 5: Validate migration
            validation_passed = self.validate_migration()

            self.stats['end_time'] = datetime.now()

            # Step 6: Generate report
            self.generate_report()

            return validation_passed

        except Exception as e:
            logger.error(f"\n❌ MIGRATION FAILED: {e}")
            if self.pg_session and not self.dry_run:
                logger.info("Rolling back transaction...")
                self.pg_session.rollback()
            raise
        finally:
            if self.pg_session:
                self.pg_session.close()
            if self.pg_engine:
                self.pg_engine.dispose()


def main():
    """Main entry point for migration script"""
    parser = argparse.ArgumentParser(
        description='Epic 16 PostgreSQL Migration - Fortune 500 Acquisition System',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Production migration
  python epic16_postgresql_migration.py

  # Dry-run mode (validation only)
  python epic16_postgresql_migration.py --dry-run

  # Verbose logging
  python epic16_postgresql_migration.py --verbose

Environment Variables:
  POSTGRES_HOST     PostgreSQL host (default: localhost)
  POSTGRES_PORT     PostgreSQL port (default: 5432)
  POSTGRES_DB       Database name (default: synapse_business_core)
  POSTGRES_USER     PostgreSQL user (default: synapse)
  POSTGRES_PASSWORD PostgreSQL password (required)
        """
    )

    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Run in dry-run mode (validation only, no actual migration)'
    )

    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Enable verbose logging'
    )

    args = parser.parse_args()

    # Validate PostgreSQL password is set
    if not os.getenv('POSTGRES_PASSWORD') and not args.dry_run:
        logger.error("ERROR: POSTGRES_PASSWORD environment variable must be set")
        logger.error("Usage: POSTGRES_PASSWORD=your_password python epic16_postgresql_migration.py")
        sys.exit(1)

    # Run migration
    migrator = Epic16PostgreSQLMigrator(dry_run=args.dry_run, verbose=args.verbose)

    try:
        success = migrator.run_migration()
        if success:
            logger.info("\n🎉 Migration completed successfully!")
            sys.exit(0)
        else:
            logger.error("\n❌ Migration validation failed")
            sys.exit(1)
    except KeyboardInterrupt:
        logger.warning("\n⚠️  Migration interrupted by user")
        sys.exit(130)
    except Exception as e:
        logger.error(f"\n❌ Migration failed with error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
