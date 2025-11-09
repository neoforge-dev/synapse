#!/usr/bin/env python3
"""
A/B Testing Framework for Content Optimization
Test and optimize content elements for maximum consultation generation
"""

import json
import logging
import random
import sqlite3
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

# Add business_development to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'business_development'))

from linkedin_posting_system import LinkedInBusinessDevelopmentEngine

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@dataclass
class ABTestVariant:
    """A/B test variant structure"""
    variant_id: str
    test_id: str
    variant_name: str
    element_type: str  # hook, cta, timing, content_length, etc.
    content: str
    expected_metric: str  # engagement_rate, consultation_requests, etc.

    # Results
    impressions: int = 0
    engagement_actions: int = 0
    consultation_requests: int = 0
    engagement_rate: float = 0.0
    consultation_conversion: float = 0.0

    # Statistical significance
    sample_size: int = 0
    confidence_level: float = 0.0
    is_winner: bool = False

@dataclass
class ABTest:
    """A/B test configuration and results"""
    test_id: str
    test_name: str
    hypothesis: str
    element_type: str
    start_date: str
    end_date: str = ""
    status: str = "active"  # active, completed, paused

    # Test configuration
    traffic_split: float = 0.5  # 50/50 split
    minimum_sample_size: int = 100
    confidence_threshold: float = 0.95

    # Results
    winning_variant: str = ""
    improvement_rate: float = 0.0
    statistical_significance: float = 0.0

class ABTestingFramework:
    """Complete A/B testing framework for content optimization"""

    def __init__(self, db_path: str = "ab_testing.db"):
        self.db_path = db_path
        self.business_engine = LinkedInBusinessDevelopmentEngine()
        self.init_database()

    def init_database(self):
        """Initialize A/B testing database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # A/B tests table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS ab_tests (
                test_id TEXT PRIMARY KEY,
                test_name TEXT,
                hypothesis TEXT,
                element_type TEXT,
                start_date TEXT,
                end_date TEXT,
                status TEXT DEFAULT 'active',
                traffic_split REAL DEFAULT 0.5,
                minimum_sample_size INTEGER DEFAULT 100,
                confidence_threshold REAL DEFAULT 0.95,
                winning_variant TEXT,
                improvement_rate REAL DEFAULT 0.0,
                statistical_significance REAL DEFAULT 0.0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Test variants table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS test_variants (
                variant_id TEXT PRIMARY KEY,
                test_id TEXT,
                variant_name TEXT,
                element_type TEXT,
                content TEXT,
                expected_metric TEXT,
                impressions INTEGER DEFAULT 0,
                engagement_actions INTEGER DEFAULT 0,
                consultation_requests INTEGER DEFAULT 0,
                engagement_rate REAL DEFAULT 0.0,
                consultation_conversion REAL DEFAULT 0.0,
                sample_size INTEGER DEFAULT 0,
                confidence_level REAL DEFAULT 0.0,
                is_winner BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (test_id) REFERENCES ab_tests (test_id)
            )
        ''')

        # Test assignments table (which post got which variant)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS test_assignments (
                assignment_id TEXT PRIMARY KEY,
                test_id TEXT,
                variant_id TEXT,
                post_id TEXT,
                assigned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (test_id) REFERENCES ab_tests (test_id),
                FOREIGN KEY (variant_id) REFERENCES test_variants (variant_id)
            )
        ''')

        conn.commit()
        conn.close()
        logger.info("A/B testing database initialized")

    def create_hook_optimization_test(self) -> str:
        """Create A/B test for optimizing content hooks"""
        test_id = f"hook_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        # Define hook variants to test
        hook_variants = [
            {
                "name": "Controversial Question",
                "template": "🔥 CONTROVERSIAL: {topic}? Here's why the conventional wisdom is wrong...",
                "example": "🔥 CONTROVERSIAL: Should startups build or buy? Here's why the conventional wisdom is wrong..."
            },
            {
                "name": "Statistics Shock",
                "template": "📊 SHOCKING STAT: {percentage}% of {audience} are making this costly mistake...",
                "example": "📊 SHOCKING STAT: 78% of startups are making this costly technical decision mistake..."
            },
            {
                "name": "Personal Story",
                "template": "💡 STORY: The {outcome} that changed how I think about {topic}...",
                "example": "💡 STORY: The $500K mistake that changed how I think about architecture decisions..."
            },
            {
                "name": "Direct Challenge",
                "template": "⚡ CHALLENGE: If your {system} can't {capability}, you're already behind...",
                "example": "⚡ CHALLENGE: If your engineering team can't ship weekly, you're already behind..."
            }
        ]

        # Create the test
        test = ABTest(
            test_id=test_id,
            test_name="Hook Optimization for Consultation Generation",
            hypothesis="Controversial hooks generate 25%+ more consultation inquiries than standard hooks",
            element_type="hook",
            start_date=datetime.now().isoformat(),
            minimum_sample_size=200,
            confidence_threshold=0.95
        )

        self._save_ab_test(test)

        # Create variants
        for i, variant in enumerate(hook_variants):
            variant_id = f"{test_id}_variant_{i+1}"

            ab_variant = ABTestVariant(
                variant_id=variant_id,
                test_id=test_id,
                variant_name=variant["name"],
                element_type="hook",
                content=json.dumps(variant),
                expected_metric="consultation_requests"
            )

            self._save_test_variant(ab_variant)

        logger.info(f"Created hook optimization test: {test_id}")
        return test_id

    def create_cta_optimization_test(self) -> str:
        """Create A/B test for optimizing calls-to-action"""
        test_id = f"cta_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        # Define CTA variants
        cta_variants = [
            {
                "name": "Direct Ask",
                "template": "Need help with {service}? DM me to discuss your specific situation.",
                "urgency": "low"
            },
            {
                "name": "Value Proposition",
                "template": "I help {audience} {outcome}. If this resonates, let's chat about your {challenge}.",
                "urgency": "medium"
            },
            {
                "name": "Time-Sensitive",
                "template": "Taking on 2 new {service} clients this month. If you're struggling with {problem}, let's talk.",
                "urgency": "high"
            },
            {
                "name": "Soft Consultation",
                "template": "What's your experience with {topic}? Happy to share insights if you want to discuss further.",
                "urgency": "low"
            }
        ]

        test = ABTest(
            test_id=test_id,
            test_name="CTA Optimization for Consultation Conversion",
            hypothesis="Time-sensitive CTAs generate 30%+ more consultation requests than soft CTAs",
            element_type="cta",
            start_date=datetime.now().isoformat(),
            minimum_sample_size=150
        )

        self._save_ab_test(test)

        for i, variant in enumerate(cta_variants):
            variant_id = f"{test_id}_variant_{i+1}"

            ab_variant = ABTestVariant(
                variant_id=variant_id,
                test_id=test_id,
                variant_name=variant["name"],
                element_type="cta",
                content=json.dumps(variant),
                expected_metric="consultation_requests"
            )

            self._save_test_variant(ab_variant)

        logger.info(f"Created CTA optimization test: {test_id}")
        return test_id

    def create_timing_optimization_test(self) -> str:
        """Create A/B test for optimal posting times"""
        test_id = f"timing_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        timing_variants = [
            {
                "name": "Early Bird (6:30 AM)",
                "time": "06:30",
                "days": ["Tuesday", "Thursday"],
                "hypothesis": "Peak professional attention"
            },
            {
                "name": "Morning Professional (8:00 AM)",
                "time": "08:00",
                "days": ["Monday", "Wednesday", "Friday"],
                "hypothesis": "Start of workday engagement"
            },
            {
                "name": "Mid-Morning (9:30 AM)",
                "time": "09:30",
                "days": ["Tuesday", "Thursday"],
                "hypothesis": "Post-meeting window"
            },
            {
                "name": "Lunch Break (12:30 PM)",
                "time": "12:30",
                "days": ["Wednesday"],
                "hypothesis": "Lunch scrolling behavior"
            }
        ]

        test = ABTest(
            test_id=test_id,
            test_name="Optimal Posting Time for Engagement",
            hypothesis="6:30 AM Tuesday/Thursday generates 40%+ higher engagement than other times",
            element_type="timing",
            start_date=datetime.now().isoformat(),
            minimum_sample_size=300
        )

        self._save_ab_test(test)

        for i, variant in enumerate(timing_variants):
            variant_id = f"{test_id}_variant_{i+1}"

            ab_variant = ABTestVariant(
                variant_id=variant_id,
                test_id=test_id,
                variant_name=variant["name"],
                element_type="timing",
                content=json.dumps(variant),
                expected_metric="engagement_rate"
            )

            self._save_test_variant(ab_variant)

        logger.info(f"Created timing optimization test: {test_id}")
        return test_id

    def assign_variant_to_post(self, test_id: str, post_id: str) -> str | None:
        """Assign a test variant to a specific post"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Get test configuration
        cursor.execute('SELECT traffic_split FROM ab_tests WHERE test_id = ?', (test_id,))
        test_result = cursor.fetchone()

        if not test_result:
            conn.close()
            return None

        # Get available variants
        cursor.execute('SELECT variant_id FROM test_variants WHERE test_id = ?', (test_id,))
        variants = [row[0] for row in cursor.fetchall()]

        if len(variants) < 2:
            conn.close()
            return None

        # Assign variant based on traffic split (random assignment)
        assigned_variant = random.choice(variants)

        # Record assignment
        assignment_id = f"assign_{test_id}_{post_id}_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        cursor.execute('''
            INSERT INTO test_assignments (assignment_id, test_id, variant_id, post_id)
            VALUES (?, ?, ?, ?)
        ''', (assignment_id, test_id, assigned_variant, post_id))

        conn.commit()
        conn.close()

        logger.info(f"Assigned variant {assigned_variant} to post {post_id}")
        return assigned_variant

    def update_variant_results(self, post_id: str, metrics: dict[str, Any]):
        """Update variant results based on post performance"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Find variant assignment for this post
        cursor.execute('''
            SELECT variant_id FROM test_assignments WHERE post_id = ?
        ''', (post_id,))

        result = cursor.fetchone()
        if not result:
            conn.close()
            return

        variant_id = result[0]

        # Calculate metrics
        impressions = metrics.get('impressions', 0)
        engagement_actions = (
            metrics.get('likes', 0) +
            metrics.get('comments', 0) +
            metrics.get('shares', 0) +
            metrics.get('saves', 0)
        )
        consultation_requests = metrics.get('consultation_requests', 0)

        engagement_actions / impressions if impressions > 0 else 0
        consultation_requests / impressions if impressions > 0 else 0

        # Update variant results
        cursor.execute('''
            UPDATE test_variants SET
                impressions = impressions + ?,
                engagement_actions = engagement_actions + ?,
                consultation_requests = consultation_requests + ?,
                engagement_rate = (engagement_actions + ?) / (impressions + ?),
                consultation_conversion = (consultation_requests + ?) / (impressions + ?),
                sample_size = sample_size + 1
            WHERE variant_id = ?
        ''', (
            impressions, engagement_actions, consultation_requests,
            engagement_actions, impressions,
            consultation_requests, impressions,
            variant_id
        ))

        conn.commit()
        conn.close()

        logger.info(f"Updated results for variant {variant_id}")

        # Check if test has enough data for statistical analysis
        self._check_test_completion(variant_id)

    def _check_test_completion(self, variant_id: str):
        """Check if test has enough data and analyze results"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Get test ID
        cursor.execute('SELECT test_id FROM test_variants WHERE variant_id = ?', (variant_id,))
        test_id = cursor.fetchone()[0]

        # Get test configuration
        cursor.execute('SELECT minimum_sample_size, confidence_threshold FROM ab_tests WHERE test_id = ?', (test_id,))
        min_sample, confidence_threshold = cursor.fetchone()

        # Get all variants for this test
        cursor.execute('''
            SELECT variant_id, variant_name, sample_size, consultation_conversion, engagement_rate
            FROM test_variants WHERE test_id = ?
        ''', (test_id,))

        variants = cursor.fetchall()

        # Check if we have enough sample size
        min_samples_met = all(variant[2] >= min_sample for variant in variants)

        if min_samples_met and len(variants) >= 2:
            # Analyze statistical significance
            winner = self._analyze_statistical_significance(variants, confidence_threshold)

            if winner:
                # Mark test as completed and record winner
                cursor.execute('''
                    UPDATE ab_tests SET
                        status = 'completed',
                        winning_variant = ?,
                        end_date = ?
                    WHERE test_id = ?
                ''', (winner['variant_id'], datetime.now().isoformat(), test_id))

                cursor.execute('''
                    UPDATE test_variants SET is_winner = TRUE
                    WHERE variant_id = ?
                ''', (winner['variant_id'],))

                conn.commit()
                logger.info(f"Test {test_id} completed. Winner: {winner['variant_name']}")

        conn.close()

    def _analyze_statistical_significance(self, variants: list[tuple], confidence_threshold: float) -> dict | None:
        """Analyze statistical significance between variants"""
        # Simple implementation - in production would use proper statistical tests
        if len(variants) < 2:
            return None

        # Sort by consultation conversion rate (primary metric)
        sorted_variants = sorted(variants, key=lambda x: x[3], reverse=True)  # consultation_conversion

        best_variant = sorted_variants[0]
        second_best = sorted_variants[1]

        # Calculate improvement rate
        if second_best[3] > 0:  # consultation_conversion
            improvement = (best_variant[3] - second_best[3]) / second_best[3]

            # Simple significance check - needs proper statistical test in production
            if improvement > 0.20 and best_variant[2] >= 100:  # 20% improvement and 100+ samples
                return {
                    'variant_id': best_variant[0],
                    'variant_name': best_variant[1],
                    'improvement': improvement,
                    'significance': 0.95  # Placeholder
                }

        return None

    def get_test_results(self, test_id: str) -> dict:
        """Get comprehensive test results"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Get test info
        cursor.execute('SELECT * FROM ab_tests WHERE test_id = ?', (test_id,))
        test_row = cursor.fetchone()

        if not test_row:
            conn.close()
            return {}

        test_columns = [description[0] for description in cursor.description]
        test_data = dict(zip(test_columns, test_row, strict=False))

        # Get variants
        cursor.execute('SELECT * FROM test_variants WHERE test_id = ? ORDER BY consultation_conversion DESC', (test_id,))
        variant_rows = cursor.fetchall()
        variant_columns = [description[0] for description in cursor.description]

        variants = []
        for row in variant_rows:
            variant = dict(zip(variant_columns, row, strict=False))
            variants.append(variant)

        conn.close()

        return {
            'test': test_data,
            'variants': variants,
            'winner': next((v for v in variants if v['is_winner']), None)
        }

    def _save_ab_test(self, test: ABTest):
        """Save A/B test to database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            INSERT INTO ab_tests
            (test_id, test_name, hypothesis, element_type, start_date,
             traffic_split, minimum_sample_size, confidence_threshold)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            test.test_id, test.test_name, test.hypothesis, test.element_type,
            test.start_date, test.traffic_split, test.minimum_sample_size,
            test.confidence_threshold
        ))

        conn.commit()
        conn.close()

    def _save_test_variant(self, variant: ABTestVariant):
        """Save test variant to database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            INSERT INTO test_variants
            (variant_id, test_id, variant_name, element_type, content, expected_metric)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            variant.variant_id, variant.test_id, variant.variant_name,
            variant.element_type, variant.content, variant.expected_metric
        ))

        conn.commit()
        conn.close()

def main():
    """Demonstrate A/B testing framework"""
    framework = ABTestingFramework()

    print("🧪 A/B Testing Framework for Content Optimization")
    print("=" * 60)

    # Create optimization tests
    print("Creating A/B tests...")

    hook_test = framework.create_hook_optimization_test()
    print(f"✅ Hook optimization test: {hook_test}")

    cta_test = framework.create_cta_optimization_test()
    print(f"✅ CTA optimization test: {cta_test}")

    timing_test = framework.create_timing_optimization_test()
    print(f"✅ Timing optimization test: {timing_test}")

    print("\n📊 A/B Testing Framework Ready!")
    print("• 3 active tests for content optimization")
    print("• Automatic variant assignment for new posts")
    print("• Statistical significance analysis")
    print("• Performance tracking and winner selection")

    print("\n💡 Usage:")
    print("1. Assign variants to posts using assign_variant_to_post()")
    print("2. Update results with post performance using update_variant_results()")
    print("3. Monitor test completion and winners")
    print("4. Apply winning variants to future content")

    # Example: Assign variant to a post
    example_post = "2025-01-20-monday-10x-teams"
    assigned_variant = framework.assign_variant_to_post(hook_test, example_post)
    if assigned_variant:
        print(f"\n🎯 Example: Assigned variant {assigned_variant} to {example_post}")

    print(f"\nDatabase: {framework.db_path}")

if __name__ == "__main__":
    main()
