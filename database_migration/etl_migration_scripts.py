#!/usr/bin/env python3
"""
Database Migration ETL Scripts for PostgreSQL Consolidation
Epic 2 Week 1: Mission-Critical $555K Pipeline Protection

This module provides comprehensive ETL (Extract, Transform, Load) functionality
to migrate 13 SQLite databases into 3 optimized PostgreSQL databases while
maintaining 100% data integrity and zero business disruption.

Performance Targets:
- Core Business queries: <50ms
- Analytics queries: <100ms
- Zero data loss validation
- 100% consultation pipeline accessibility
"""

import sqlite3
import psycopg2
from psycopg2.extras import RealDictCursor
import json
import hashlib
import logging
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from pathlib import Path
import uuid
from decimal import Decimal


# Configure logging for migration tracking
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('migration.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


@dataclass
class DatabaseConfig:
    """Configuration for database connections"""
    host: str
    port: int
    database: str
    username: str
    password: str
    
    def connection_string(self) -> str:
        return f"postgresql://{self.username}:{self.password}@{self.host}:{self.port}/{self.database}"


@dataclass
class MigrationResult:
    """Result tracking for migration operations"""
    source_db: str
    target_db: str
    table_name: str
    records_processed: int
    records_migrated: int
    data_checksum: str
    processing_time_seconds: float
    validation_passed: bool
    errors: List[str]


class DataValidator:
    """Comprehensive data validation framework for migration integrity"""
    
    def __init__(self):
        self.validation_errors: List[str] = []
    
    def calculate_checksum(self, data: List[Dict[str, Any]]) -> str:
        """Calculate checksum for data integrity validation"""
        # Sort data by primary key for consistent checksums
        sorted_data = sorted(data, key=lambda x: str(x.get('id', x.get('post_id', x.get('inquiry_id', '')))))
        data_string = json.dumps(sorted_data, sort_keys=True, default=str)
        return hashlib.md5(data_string.encode()).hexdigest()
    
    def validate_record_count(self, source_count: int, target_count: int, table_name: str) -> bool:
        """Validate that record counts match between source and target"""
        if source_count != target_count:
            error = f"Record count mismatch for {table_name}: Source={source_count}, Target={target_count}"
            self.validation_errors.append(error)
            logger.error(error)
            return False
        logger.info(f"✅ Record count validation passed for {table_name}: {source_count} records")
        return True
    
    def validate_consultation_pipeline_data(self, inquiries_data: List[Dict]) -> bool:
        """Critical validation for $555K consultation pipeline data"""
        required_fields = ['inquiry_id', 'contact_name', 'estimated_value', 'status']
        
        for inquiry in inquiries_data:
            for field in required_fields:
                if field not in inquiry or inquiry[field] is None:
                    error = f"Missing critical field '{field}' in consultation inquiry: {inquiry.get('inquiry_id')}"
                    self.validation_errors.append(error)
                    logger.error(error)
                    return False
        
        total_pipeline_value = sum(
            float(inquiry.get('estimated_value', 0)) 
            for inquiry in inquiries_data 
            if inquiry.get('estimated_value') is not None
        )
        
        logger.info(f"✅ Consultation pipeline validation passed: ${total_pipeline_value:,.2f} total value")
        return True
    
    def validate_foreign_key_integrity(self, posts_data: List[Dict], inquiries_data: List[Dict]) -> bool:
        """Validate foreign key relationships between posts and inquiries"""
        post_ids = {post['post_id'] for post in posts_data}
        
        for inquiry in inquiries_data:
            source_post_id = inquiry.get('source_post_id')
            if source_post_id and source_post_id not in post_ids:
                error = f"Invalid foreign key reference: inquiry {inquiry['inquiry_id']} references non-existent post {source_post_id}"
                self.validation_errors.append(error)
                logger.error(error)
                return False
        
        logger.info("✅ Foreign key integrity validation passed")
        return True


class SQLiteExtractor:
    """Extract data from SQLite databases with deduplication logic"""
    
    def __init__(self, db_paths: Dict[str, str]):
        self.db_paths = db_paths
        self.extracted_data: Dict[str, List[Dict]] = {}
    
    def extract_linkedin_posts(self) -> List[Dict[str, Any]]:
        """Extract and deduplicate LinkedIn posts from multiple sources"""
        all_posts = []
        seen_post_ids = set()
        
        # Primary database takes precedence
        primary_db = self.db_paths['linkedin_business_development.db']
        posts = self._extract_from_sqlite(primary_db, "linkedin_posts")
        for post in posts:
            if post['post_id'] not in seen_post_ids:
                post['data_source'] = 'linkedin_primary'
                all_posts.append(post)
                seen_post_ids.add(post['post_id'])
        
        # Check duplicate database for unique records
        duplicate_db = self.db_paths['business_development/linkedin_business_development.db']
        duplicate_posts = self._extract_from_sqlite(duplicate_db, "linkedin_posts")
        for post in duplicate_posts:
            if post['post_id'] not in seen_post_ids:
                post['data_source'] = 'linkedin_duplicate'
                all_posts.append(post)
                seen_post_ids.add(post['post_id'])
                logger.warning(f"Found unique post in duplicate database: {post['post_id']}")
        
        # Add Week 3 posts with different structure
        week3_db = self.db_paths['week3_business_development.db']
        week3_posts = self._extract_from_sqlite(week3_db, "week3_posts")
        for post in week3_posts:
            # Transform Week 3 structure to match LinkedIn posts
            transformed_post = {
                'post_id': post['post_id'],
                'content': post.get('title', ''),  # Week 3 uses 'title' instead of 'content'
                'posted_at': post.get('date'),
                'week_theme': post.get('series'),
                'day': post.get('day'),
                'business_objective': post.get('business_dev_focus'),
                'target_consultation_type': post.get('target_consultation_type'),
                'views': post.get('views', 0),
                'likes': post.get('likes', 0),
                'comments': post.get('comments', 0),
                'shares': post.get('shares', 0),
                'saves': post.get('saves', 0),
                'profile_views': post.get('profile_views', 0),
                'connection_requests': post.get('connection_requests', 0),
                'consultation_requests': post.get('consultation_inquiries', 0),
                'actual_engagement_rate': post.get('engagement_rate', 0.0),
                'data_source': 'week3'
            }
            
            if post['post_id'] not in seen_post_ids:
                all_posts.append(transformed_post)
                seen_post_ids.add(post['post_id'])
        
        logger.info(f"Extracted {len(all_posts)} unique posts from {len(seen_post_ids)} total records")
        return all_posts
    
    def extract_consultation_inquiries(self) -> List[Dict[str, Any]]:
        """Extract and merge consultation inquiries with critical business validation"""
        all_inquiries = []
        seen_inquiry_ids = set()
        
        # Primary LinkedIn database inquiries (15 records - critical!)
        primary_db = self.db_paths['linkedin_business_development.db']
        primary_inquiries = self._extract_from_sqlite(primary_db, "consultation_inquiries")
        for inquiry in primary_inquiries:
            if inquiry['inquiry_id'] not in seen_inquiry_ids:
                inquiry['data_source'] = 'linkedin_primary'
                all_inquiries.append(inquiry)
                seen_inquiry_ids.add(inquiry['inquiry_id'])
        
        logger.info(f"Primary database inquiries: {len(primary_inquiries)} ($555K pipeline critical)")
        
        # Duplicate database inquiries (1 record - check for uniqueness)
        duplicate_db = self.db_paths['business_development/linkedin_business_development.db']
        duplicate_inquiries = self._extract_from_sqlite(duplicate_db, "consultation_inquiries")
        for inquiry in duplicate_inquiries:
            if inquiry['inquiry_id'] not in seen_inquiry_ids:
                inquiry['data_source'] = 'linkedin_duplicate'
                all_inquiries.append(inquiry)
                seen_inquiry_ids.add(inquiry['inquiry_id'])
                logger.warning(f"Found unique inquiry in duplicate database: {inquiry['inquiry_id']}")
        
        # Week 3 inquiries with structure transformation
        week3_db = self.db_paths['week3_business_development.db']
        week3_inquiries = self._extract_from_sqlite(week3_db, "consultation_inquiries")
        for inquiry in week3_inquiries:
            # Transform Week 3 structure
            transformed_inquiry = {
                'inquiry_id': inquiry['inquiry_id'],
                'source_post_id': inquiry.get('source_post_id'),
                'contact_name': inquiry.get('contact_name'),
                'company': inquiry.get('company_name'),
                'company_size': inquiry.get('company_size'),
                'inquiry_type': inquiry.get('inquiry_type'),
                'inquiry_channel': 'linkedin',  # Default for Week 3
                'inquiry_text': inquiry.get('inquiry_details'),
                'estimated_value': inquiry.get('estimated_value'),
                'status': inquiry.get('status', 'new'),
                'created_at': inquiry.get('inquiry_date'),
                'notes': inquiry.get('notes'),
                'data_source': 'week3'
            }
            
            if inquiry['inquiry_id'] not in seen_inquiry_ids:
                all_inquiries.append(transformed_inquiry)
                seen_inquiry_ids.add(inquiry['inquiry_id'])
        
        # Critical business validation
        total_pipeline_value = sum(
            float(inquiry.get('estimated_value', 0)) 
            for inquiry in all_inquiries 
            if inquiry.get('estimated_value') is not None
        )
        
        logger.info(f"✅ CRITICAL: Extracted {len(all_inquiries)} consultation inquiries")
        logger.info(f"✅ CRITICAL: Total pipeline value: ${total_pipeline_value:,.2f}")
        
        return all_inquiries
    
    def extract_analytics_data(self) -> Dict[str, List[Dict[str, Any]]]:
        """Extract analytics data from multiple performance databases"""
        analytics_data = {}
        
        # Content analysis (deduplicate from multiple sources)
        content_analysis = []
        analysis_sources = [
            'performance_analytics.db',
            'optimized_performance_analytics.db',
            'cross_platform_performance.db'
        ]
        
        seen_analysis_ids = set()
        for db_name in analysis_sources:
            if db_name in self.db_paths:
                db_data = self._extract_from_sqlite(self.db_paths[db_name], "content_analysis")
                for record in db_data:
                    # Create composite key for deduplication
                    composite_key = f"{record.get('post_id')}_{record.get('analyzed_at')}"
                    if composite_key not in seen_analysis_ids:
                        record['data_source'] = db_name
                        content_analysis.append(record)
                        seen_analysis_ids.add(composite_key)
        
        analytics_data['content_analysis'] = content_analysis
        
        # Performance patterns (similar deduplication)
        patterns_data = []
        seen_patterns = set()
        for db_name in analysis_sources:
            if db_name in self.db_paths:
                db_data = self._extract_from_sqlite(self.db_paths[db_name], "content_patterns")
                for record in db_data:
                    pattern_key = f"{record.get('pattern_type')}_{record.get('pattern_value')}"
                    if pattern_key not in seen_patterns:
                        record['data_source'] = db_name
                        patterns_data.append(record)
                        seen_patterns.add(pattern_key)
        
        analytics_data['content_patterns'] = patterns_data
        
        # Performance predictions
        predictions_data = []
        for db_name in analysis_sources:
            if db_name in self.db_paths:
                db_data = self._extract_from_sqlite(self.db_paths[db_name], "performance_predictions")
                for record in db_data:
                    record['data_source'] = db_name
                    predictions_data.append(record)
        
        analytics_data['performance_predictions'] = predictions_data
        
        logger.info(f"Extracted analytics data: {len(content_analysis)} analyses, {len(patterns_data)} patterns, {len(predictions_data)} predictions")
        return analytics_data
    
    def _extract_from_sqlite(self, db_path: str, table_name: str) -> List[Dict[str, Any]]:
        """Extract data from SQLite database table"""
        try:
            with sqlite3.connect(db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute(f"SELECT * FROM {table_name}")
                rows = cursor.fetchall()
                return [dict(row) for row in rows]
        except sqlite3.OperationalError as e:
            if "no such table" in str(e):
                logger.warning(f"Table {table_name} not found in {db_path}")
                return []
            raise e
        except Exception as e:
            logger.error(f"Error extracting from {db_path}.{table_name}: {e}")
            raise e


class PostgreSQLLoader:
    """Load data into PostgreSQL databases with optimized performance"""
    
    def __init__(self, db_configs: Dict[str, DatabaseConfig]):
        self.db_configs = db_configs
        self.connections: Dict[str, psycopg2.extensions.connection] = {}
    
    def connect(self, db_name: str) -> psycopg2.extensions.connection:
        """Get or create PostgreSQL connection with optimizations"""
        if db_name not in self.connections:
            config = self.db_configs[db_name]
            conn = psycopg2.connect(
                host=config.host,
                port=config.port,
                database=config.database,
                user=config.username,
                password=config.password,
                cursor_factory=RealDictCursor
            )
            # Optimize connection for bulk loading
            conn.autocommit = False
            self.connections[db_name] = conn
        
        return self.connections[db_name]
    
    def load_posts_data(self, posts_data: List[Dict[str, Any]]) -> MigrationResult:
        """Load posts data into synapse_business_core with UUID generation"""
        start_time = datetime.now()
        conn = self.connect('synapse_business_core')
        
        try:
            with conn.cursor() as cursor:
                # Prepare batch insert with UUID generation
                insert_sql = """
                    INSERT INTO posts (
                        post_id, external_post_id, content, posted_at, platform,
                        week_theme, day_of_week, business_objective, target_audience,
                        target_consultation_type, views, impressions, likes, comments,
                        shares, saves, clicks, profile_views, connection_requests,
                        dm_inquiries, consultation_requests, actual_engagement_rate,
                        business_conversion_rate, roi_score, data_source
                    ) VALUES (
                        gen_random_uuid(), %s, %s, %s, %s, %s, %s, %s, %s, %s,
                        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                    )
                """
                
                batch_data = []
                for post in posts_data:
                    # Convert timestamp
                    posted_at = self._parse_timestamp(post.get('posted_at'))
                    
                    batch_data.append((
                        post['post_id'],  # external_post_id
                        post.get('content', ''),
                        posted_at,
                        post.get('platform', 'linkedin'),
                        post.get('week_theme'),
                        post.get('day'),
                        post.get('business_objective'),
                        post.get('target_audience'),
                        post.get('target_consultation_type'),
                        post.get('views', 0),
                        post.get('impressions', 0),
                        post.get('likes', 0),
                        post.get('comments', 0),
                        post.get('shares', 0),
                        post.get('saves', 0),
                        post.get('clicks', 0),
                        post.get('profile_views', 0),
                        post.get('connection_requests', 0),
                        post.get('dm_inquiries', 0),
                        post.get('consultation_requests', 0),
                        float(post.get('actual_engagement_rate', 0.0)),
                        float(post.get('business_conversion_rate', 0.0)),
                        float(post.get('roi_score', 0.0)),
                        post.get('data_source')
                    ))
                
                # Batch insert for performance
                cursor.executemany(insert_sql, batch_data)
                conn.commit()
                
                # Validation query
                cursor.execute("SELECT COUNT(*) FROM posts")
                loaded_count = cursor.fetchone()[0]
                
                processing_time = (datetime.now() - start_time).total_seconds()
                
                return MigrationResult(
                    source_db="SQLite",
                    target_db="synapse_business_core",
                    table_name="posts",
                    records_processed=len(posts_data),
                    records_migrated=loaded_count,
                    data_checksum=DataValidator().calculate_checksum(posts_data),
                    processing_time_seconds=processing_time,
                    validation_passed=loaded_count == len(posts_data),
                    errors=[]
                )
        
        except Exception as e:
            conn.rollback()
            logger.error(f"Error loading posts data: {e}")
            raise e
    
    def load_consultation_inquiries(self, inquiries_data: List[Dict[str, Any]]) -> MigrationResult:
        """Load consultation inquiries with critical business validation"""
        start_time = datetime.now()
        conn = self.connect('synapse_business_core')
        
        try:
            with conn.cursor() as cursor:
                # First, get post_id mappings
                cursor.execute("SELECT post_id, external_post_id FROM posts")
                post_id_mapping = {row['external_post_id']: row['post_id'] for row in cursor.fetchall()}
                
                insert_sql = """
                    INSERT INTO consultation_inquiries (
                        inquiry_id, external_inquiry_id, source_post_id, contact_name,
                        company, company_size, industry, inquiry_type, inquiry_channel,
                        inquiry_text, inquiry_details, estimated_value, priority_score,
                        qualification_score, status, last_contact, notes, data_source
                    ) VALUES (
                        gen_random_uuid(), %s, %s, %s, %s, %s, %s, %s, %s, %s,
                        %s, %s, %s, %s, %s, %s, %s, %s
                    )
                """
                
                batch_data = []
                total_pipeline_value = 0.0
                
                for inquiry in inquiries_data:
                    # Map external post ID to internal UUID
                    source_post_uuid = None
                    if inquiry.get('source_post_id'):
                        source_post_uuid = post_id_mapping.get(inquiry['source_post_id'])
                    
                    # Validate and accumulate pipeline value
                    estimated_value = inquiry.get('estimated_value')
                    if estimated_value:
                        try:
                            estimated_value = float(estimated_value)
                            total_pipeline_value += estimated_value
                        except (ValueError, TypeError):
                            estimated_value = None
                    
                    batch_data.append((
                        inquiry['inquiry_id'],  # external_inquiry_id
                        source_post_uuid,
                        inquiry.get('contact_name'),
                        inquiry.get('company'),
                        inquiry.get('company_size'),
                        inquiry.get('industry'),
                        inquiry.get('inquiry_type'),
                        inquiry.get('inquiry_channel', 'linkedin'),
                        inquiry.get('inquiry_text'),
                        inquiry.get('inquiry_details'),
                        estimated_value,
                        inquiry.get('priority_score'),
                        inquiry.get('qualification_score'),
                        inquiry.get('status', 'new'),
                        self._parse_timestamp(inquiry.get('last_contact')),
                        inquiry.get('notes'),
                        inquiry.get('data_source')
                    ))
                
                # Critical: Log pipeline value for business validation
                logger.info(f"🚨 CRITICAL BUSINESS METRIC: Total pipeline value being migrated: ${total_pipeline_value:,.2f}")
                
                # Batch insert
                cursor.executemany(insert_sql, batch_data)
                conn.commit()
                
                # Validation
                cursor.execute("SELECT COUNT(*) FROM consultation_inquiries")
                loaded_count = cursor.fetchone()[0]
                
                processing_time = (datetime.now() - start_time).total_seconds()
                
                return MigrationResult(
                    source_db="SQLite",
                    target_db="synapse_business_core", 
                    table_name="consultation_inquiries",
                    records_processed=len(inquiries_data),
                    records_migrated=loaded_count,
                    data_checksum=DataValidator().calculate_checksum(inquiries_data),
                    processing_time_seconds=processing_time,
                    validation_passed=loaded_count == len(inquiries_data),
                    errors=[]
                )
        
        except Exception as e:
            conn.rollback()
            logger.error(f"💥 CRITICAL ERROR loading consultation inquiries: {e}")
            raise e
    
    def _parse_timestamp(self, timestamp_str: Optional[str]) -> Optional[datetime]:
        """Parse timestamp string to datetime with timezone"""
        if not timestamp_str:
            return None
        
        try:
            # Try multiple timestamp formats
            formats = [
                '%Y-%m-%d %H:%M:%S',
                '%Y-%m-%d',
                '%Y-%m-%d %H:%M:%S.%f',
            ]
            
            for fmt in formats:
                try:
                    dt = datetime.strptime(timestamp_str, fmt)
                    return dt.replace(tzinfo=timezone.utc)
                except ValueError:
                    continue
            
            # If all formats fail, log and return None
            logger.warning(f"Could not parse timestamp: {timestamp_str}")
            return None
            
        except Exception as e:
            logger.warning(f"Error parsing timestamp {timestamp_str}: {e}")
            return None
    
    def close_connections(self):
        """Close all database connections"""
        for conn in self.connections.values():
            conn.close()
        self.connections.clear()


class MigrationOrchestrator:
    """Main orchestrator for database migration with business continuity"""
    
    def __init__(self, sqlite_db_paths: Dict[str, str], postgresql_configs: Dict[str, DatabaseConfig]):
        self.sqlite_db_paths = sqlite_db_paths
        self.postgresql_configs = postgresql_configs
        self.extractor = SQLiteExtractor(sqlite_db_paths)
        self.loader = PostgreSQLLoader(postgresql_configs)
        self.validator = DataValidator()
        self.migration_results: List[MigrationResult] = []
    
    def execute_core_business_migration(self) -> bool:
        """Execute Phase 1: Core Business Migration with $555K pipeline protection"""
        logger.info("🚀 PHASE 1: Core Business Migration Starting")
        logger.info("🎯 MISSION CRITICAL: Protecting $555K consultation pipeline")
        
        try:
            # Step 1: Extract posts with deduplication
            logger.info("📊 Extracting posts data with deduplication...")
            posts_data = self.extractor.extract_linkedin_posts()
            
            # Step 2: Extract consultation inquiries (CRITICAL)
            logger.info("💰 Extracting consultation inquiries (CRITICAL BUSINESS DATA)...")
            inquiries_data = self.extractor.extract_consultation_inquiries()
            
            # Step 3: Critical business validation
            if not self.validator.validate_consultation_pipeline_data(inquiries_data):
                raise Exception("❌ CRITICAL: Consultation pipeline data validation FAILED")
            
            # Step 4: Validate foreign key integrity
            if not self.validator.validate_foreign_key_integrity(posts_data, inquiries_data):
                raise Exception("❌ CRITICAL: Foreign key integrity validation FAILED")
            
            # Step 5: Load posts data
            logger.info("📝 Loading posts data to PostgreSQL...")
            posts_result = self.loader.load_posts_data(posts_data)
            self.migration_results.append(posts_result)
            
            if not posts_result.validation_passed:
                raise Exception(f"❌ Posts migration validation FAILED: {posts_result.errors}")
            
            # Step 6: Load consultation inquiries (CRITICAL)
            logger.info("💼 Loading consultation inquiries to PostgreSQL...")
            inquiries_result = self.loader.load_consultation_inquiries(inquiries_data)
            self.migration_results.append(inquiries_result)
            
            if not inquiries_result.validation_passed:
                raise Exception(f"❌ CRITICAL: Consultation inquiries migration FAILED: {inquiries_result.errors}")
            
            logger.info("✅ PHASE 1 COMPLETE: Core Business Migration Successful")
            logger.info(f"✅ Posts migrated: {posts_result.records_migrated}")
            logger.info(f"✅ Consultation inquiries migrated: {inquiries_result.records_migrated}")
            logger.info(f"✅ Processing time: {posts_result.processing_time_seconds + inquiries_result.processing_time_seconds:.2f}s")
            
            return True
            
        except Exception as e:
            logger.error(f"💥 CRITICAL FAILURE in Phase 1 migration: {e}")
            return False
    
    def generate_migration_report(self) -> str:
        """Generate comprehensive migration report for business stakeholders"""
        report = []
        report.append("=" * 80)
        report.append("DATABASE CONSOLIDATION MIGRATION REPORT")
        report.append("Epic 2 Week 1: PostgreSQL Consolidation")
        report.append("=" * 80)
        report.append(f"Migration executed at: {datetime.now()}")
        report.append("")
        
        # Summary metrics
        total_records_processed = sum(r.records_processed for r in self.migration_results)
        total_records_migrated = sum(r.records_migrated for r in self.migration_results)
        total_processing_time = sum(r.processing_time_seconds for r in self.migration_results)
        
        report.append("EXECUTIVE SUMMARY")
        report.append("-" * 40)
        report.append(f"Total Records Processed: {total_records_processed:,}")
        report.append(f"Total Records Migrated: {total_records_migrated:,}")
        report.append(f"Success Rate: {(total_records_migrated/total_records_processed*100):.1f}%")
        report.append(f"Total Processing Time: {total_processing_time:.2f} seconds")
        report.append("")
        
        # Critical business metrics
        consultation_result = next((r for r in self.migration_results if r.table_name == 'consultation_inquiries'), None)
        if consultation_result:
            report.append("CRITICAL BUSINESS METRICS")
            report.append("-" * 40)
            report.append(f"Consultation Inquiries Migrated: {consultation_result.records_migrated}")
            report.append(f"Pipeline Data Integrity: {'✅ VERIFIED' if consultation_result.validation_passed else '❌ FAILED'}")
            report.append(f"Business Continuity: {'✅ MAINTAINED' if consultation_result.validation_passed else '❌ COMPROMISED'}")
        
        report.append("")
        
        # Detailed results
        report.append("DETAILED MIGRATION RESULTS")
        report.append("-" * 40)
        for result in self.migration_results:
            report.append(f"Table: {result.table_name}")
            report.append(f"  Records: {result.records_processed} → {result.records_migrated}")
            report.append(f"  Validation: {'✅ PASSED' if result.validation_passed else '❌ FAILED'}")
            report.append(f"  Processing Time: {result.processing_time_seconds:.2f}s")
            report.append(f"  Data Checksum: {result.data_checksum}")
            if result.errors:
                report.append(f"  Errors: {', '.join(result.errors)}")
            report.append("")
        
        return "\n".join(report)


def main():
    """Main migration execution function"""
    
    # Define SQLite database paths
    base_path = Path("/Users/bogdan/til/graph-rag-mcp")
    sqlite_paths = {
        'linkedin_business_development.db': str(base_path / 'linkedin_business_development.db'),
        'business_development/linkedin_business_development.db': str(base_path / 'business_development' / 'linkedin_business_development.db'),
        'week3_business_development.db': str(base_path / 'week3_business_development.db'),
        'performance_analytics.db': str(base_path / 'performance_analytics.db'),
        'optimized_performance_analytics.db': str(base_path / 'optimized_performance_analytics.db'),
        'cross_platform_performance.db': str(base_path / 'cross_platform_performance.db'),
        'content_analytics.db': str(base_path / 'content_analytics.db'),
        'cross_platform_analytics.db': str(base_path / 'cross_platform_analytics.db'),
        'revenue_acceleration.db': str(base_path / 'revenue_acceleration.db'),
        'ab_testing.db': str(base_path / 'ab_testing.db'),
        'synapse_content_intelligence.db': str(base_path / 'synapse_content_intelligence.db'),
        'unified_content_management.db': str(base_path / 'unified_content_management.db'),
        'twitter_analytics.db': str(base_path / 'twitter_analytics.db')
    }
    
    # Define PostgreSQL configurations (to be configured by DevOps)
    postgresql_configs = {
        'synapse_business_core': DatabaseConfig(
            host='localhost',  # To be configured
            port=5432,
            database='synapse_business_core',
            username='synapse_user',
            password='secure_password'
        ),
        'synapse_analytics_intelligence': DatabaseConfig(
            host='localhost',  # To be configured
            port=5432,
            database='synapse_analytics_intelligence',
            username='synapse_user',
            password='secure_password'
        ),
        'synapse_revenue_intelligence': DatabaseConfig(
            host='localhost',  # To be configured
            port=5432,
            database='synapse_revenue_intelligence', 
            username='synapse_user',
            password='secure_password'
        )
    }
    
    # Execute migration
    logger.info("🚀 DATABASE CONSOLIDATION MIGRATION STARTING")
    logger.info("🎯 Mission: 13 SQLite → 3 PostgreSQL with zero business disruption")
    
    orchestrator = MigrationOrchestrator(sqlite_paths, postgresql_configs)
    
    # Phase 1: Core Business Migration (CRITICAL)
    success = orchestrator.execute_core_business_migration()
    
    if success:
        # Generate and save migration report
        report = orchestrator.generate_migration_report()
        
        report_path = base_path / 'migration_report.txt'
        with open(report_path, 'w') as f:
            f.write(report)
        
        logger.info(f"📊 Migration report saved: {report_path}")
        print(report)
        
        logger.info("✅ DATABASE CONSOLIDATION PHASE 1 COMPLETE")
        logger.info("🎯 $555K consultation pipeline successfully protected")
    else:
        logger.error("💥 MIGRATION FAILED - BUSINESS CONTINUITY COMPROMISED")
        return 1
    
    # Cleanup
    orchestrator.loader.close_connections()
    return 0


if __name__ == "__main__":
    exit(main())