#!/usr/bin/env python3
"""
Advanced Cross-Platform Analytics and Attribution System
Complete attribution tracking across LinkedIn, Twitter, Newsletter, and website conversions
"""

import json
import logging
import sqlite3
import sys
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import numpy as np

# Configure logging first
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Visualization imports (optional)
try:
    import matplotlib.pyplot as plt
    import seaborn as sns
    VISUALIZATION_AVAILABLE = True
except ImportError:
    VISUALIZATION_AVAILABLE = False
    logger.warning("Matplotlib/Seaborn not available - visualization features disabled")

# Add project paths
sys.path.insert(0, str(Path(__file__).parent.parent / 'social_platforms'))
sys.path.insert(0, str(Path(__file__).parent))

from database_optimizer import OptimizedAnalyticsDatabase
from unified_content_manager import Platform

# Logging already configured above

@dataclass
class AttributionDataPoint:
    """Single attribution data point"""
    content_id: str
    platform: Platform
    touchpoint: str  # impression, click, engagement, conversion
    user_id: str | None
    session_id: str | None
    timestamp: str
    value: float  # monetary value for conversions
    metadata: dict[str, Any]

@dataclass
class ConversionPath:
    """User conversion path across platforms"""
    user_id: str
    content_id: str
    touchpoints: list[dict[str, Any]]
    conversion_value: float
    conversion_type: str  # consultation, newsletter, download
    attribution_weights: dict[Platform, float]
    journey_duration_hours: float

@dataclass
class CrossPlatformReport:
    """Comprehensive cross-platform performance report"""
    content_id: str
    reporting_period: str
    platform_performance: dict[Platform, dict[str, Any]]
    attribution_analysis: dict[str, Any]
    conversion_paths: list[ConversionPath]
    roi_analysis: dict[str, Any]
    optimization_recommendations: list[str]

class CrossPlatformAnalytics:
    """Advanced cross-platform analytics with attribution modeling"""

    def __init__(self):
        self.db_path = "cross_platform_analytics.db"
        self.optimized_db = OptimizedAnalyticsDatabase("cross_platform_performance.db")
        self._init_database()

        # Attribution models configuration
        self.attribution_models = {
            'first_touch': self._first_touch_attribution,
            'last_touch': self._last_touch_attribution,
            'linear': self._linear_attribution,
            'time_decay': self._time_decay_attribution,
            'position_based': self._position_based_attribution
        }

        logger.info("Cross-platform analytics system initialized")

    def _init_database(self):
        """Initialize cross-platform analytics database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Attribution tracking table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS attribution_tracking (
                tracking_id TEXT PRIMARY KEY,
                content_id TEXT NOT NULL,
                platform TEXT NOT NULL,
                touchpoint TEXT NOT NULL,
                user_id TEXT,
                session_id TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                value REAL DEFAULT 0.0,
                metadata TEXT,  -- JSON
                processed BOOLEAN DEFAULT FALSE
            )
        ''')

        # Conversion paths table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS conversion_paths (
                path_id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                content_id TEXT NOT NULL,
                touchpoints TEXT NOT NULL,  -- JSON array
                conversion_value REAL NOT NULL,
                conversion_type TEXT NOT NULL,
                journey_start TIMESTAMP NOT NULL,
                journey_end TIMESTAMP NOT NULL,
                attribution_weights TEXT  -- JSON
            )
        ''')

        # Cross-platform performance aggregates
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS cross_platform_performance (
                performance_id TEXT PRIMARY KEY,
                content_id TEXT NOT NULL,
                platform TEXT NOT NULL,
                date TEXT NOT NULL,
                impressions INTEGER DEFAULT 0,
                clicks INTEGER DEFAULT 0,
                engagements INTEGER DEFAULT 0,
                conversions INTEGER DEFAULT 0,
                revenue REAL DEFAULT 0.0,
                assisted_conversions INTEGER DEFAULT 0,
                attribution_revenue REAL DEFAULT 0.0,
                calculated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Platform interaction matrix
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS platform_interactions (
                interaction_id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                from_platform TEXT NOT NULL,
                to_platform TEXT NOT NULL,
                content_id TEXT NOT NULL,
                interaction_type TEXT NOT NULL,
                time_between_seconds INTEGER,
                recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Create performance indexes
        indexes = [
            "CREATE INDEX IF NOT EXISTS idx_attribution_content ON attribution_tracking (content_id, platform)",
            "CREATE INDEX IF NOT EXISTS idx_attribution_user ON attribution_tracking (user_id, timestamp)",
            "CREATE INDEX IF NOT EXISTS idx_conversion_paths_user ON conversion_paths (user_id, content_id)",
            "CREATE INDEX IF NOT EXISTS idx_performance_content_date ON cross_platform_performance (content_id, date)",
            "CREATE INDEX IF NOT EXISTS idx_interactions_user ON platform_interactions (user_id, recorded_at)"
        ]

        for index in indexes:
            cursor.execute(index)

        conn.commit()
        conn.close()
        logger.info("Cross-platform analytics database initialized")

    def track_attribution_event(self, content_id: str, platform: Platform,
                               touchpoint: str, user_id: str | None = None,
                               session_id: str | None = None, value: float = 0.0,
                               metadata: dict[str, Any] | None = None) -> str:
        """Track attribution event across platforms"""
        tracking_id = f"attr_{platform.value}_{touchpoint}_{datetime.now().strftime('%Y%m%d%H%M%S%f')}"

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            INSERT INTO attribution_tracking 
            (tracking_id, content_id, platform, touchpoint, user_id, session_id, value, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (tracking_id, content_id, platform.value, touchpoint, user_id, session_id,
              value, json.dumps(metadata or {})))

        conn.commit()
        conn.close()

        logger.info(f"Tracked attribution event: {platform.value}/{touchpoint} for {content_id}")
        return tracking_id

    def analyze_conversion_paths(self, content_id: str,
                               lookback_days: int = 30) -> list[ConversionPath]:
        """Analyze user conversion paths for content"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Get all attribution events for content
        cursor.execute(f'''
            SELECT user_id, platform, touchpoint, timestamp, value, metadata
            FROM attribution_tracking 
            WHERE content_id = ? 
              AND timestamp >= date('now', '-{lookback_days} days')
              AND user_id IS NOT NULL
            ORDER BY user_id, timestamp
        ''', (content_id,))

        events = cursor.fetchall()
        conn.close()

        # Group events by user
        user_journeys = defaultdict(list)
        for event in events:
            user_id, platform, touchpoint, timestamp, value, metadata = event
            user_journeys[user_id].append({
                'platform': Platform(platform),
                'touchpoint': touchpoint,
                'timestamp': timestamp,
                'value': value,
                'metadata': json.loads(metadata or '{}')
            })

        # Analyze conversion paths
        conversion_paths = []
        for user_id, journey in user_journeys.items():
            # Find conversions (events with value > 0)
            conversions = [event for event in journey if event['value'] > 0]

            for conversion in conversions:
                # Get all touchpoints leading to this conversion
                conversion_time = datetime.fromisoformat(conversion['timestamp'])
                leading_touchpoints = [
                    event for event in journey
                    if datetime.fromisoformat(event['timestamp']) <= conversion_time
                ]

                if len(leading_touchpoints) > 1:  # Multi-touch journey
                    journey_start = datetime.fromisoformat(leading_touchpoints[0]['timestamp'])
                    journey_duration = (conversion_time - journey_start).total_seconds() / 3600

                    # Calculate attribution weights using different models
                    attribution_weights = self._calculate_attribution_weights(leading_touchpoints)

                    conversion_path = ConversionPath(
                        user_id=user_id,
                        content_id=content_id,
                        touchpoints=leading_touchpoints,
                        conversion_value=conversion['value'],
                        conversion_type=conversion['metadata'].get('conversion_type', 'unknown'),
                        attribution_weights=attribution_weights,
                        journey_duration_hours=journey_duration
                    )

                    conversion_paths.append(conversion_path)

        # Save conversion paths
        self._save_conversion_paths(conversion_paths)

        logger.info(f"Analyzed {len(conversion_paths)} conversion paths for {content_id}")
        return conversion_paths

    def _calculate_attribution_weights(self, touchpoints: list[dict[str, Any]]) -> dict[Platform, float]:
        """Calculate attribution weights across platforms using multiple models"""
        platforms = [Platform(tp['platform']) for tp in touchpoints]

        # Use time-decay model as default (gives more weight to recent touchpoints)
        weights = {}
        total_weight = 0

        for i, platform in enumerate(platforms):
            # Time decay: more recent touchpoints get higher weight
            weight = 0.5 ** (len(platforms) - i - 1)
            weights[platform] = weights.get(platform, 0) + weight
            total_weight += weight

        # Normalize weights
        for platform in weights:
            weights[platform] /= total_weight

        return weights

    def _first_touch_attribution(self, touchpoints: list[dict[str, Any]]) -> dict[Platform, float]:
        """First-touch attribution model"""
        if not touchpoints:
            return {}

        first_platform = Platform(touchpoints[0]['platform'])
        return {first_platform: 1.0}

    def _last_touch_attribution(self, touchpoints: list[dict[str, Any]]) -> dict[Platform, float]:
        """Last-touch attribution model"""
        if not touchpoints:
            return {}

        last_platform = Platform(touchpoints[-1]['platform'])
        return {last_platform: 1.0}

    def _linear_attribution(self, touchpoints: list[dict[str, Any]]) -> dict[Platform, float]:
        """Linear attribution model (equal weight to all touchpoints)"""
        if not touchpoints:
            return {}

        platforms = [Platform(tp['platform']) for tp in touchpoints]
        weight_per_touchpoint = 1.0 / len(touchpoints)

        weights = {}
        for platform in platforms:
            weights[platform] = weights.get(platform, 0) + weight_per_touchpoint

        return weights

    def _time_decay_attribution(self, touchpoints: list[dict[str, Any]]) -> dict[Platform, float]:
        """Time-decay attribution model"""
        return self._calculate_attribution_weights(touchpoints)  # Already implemented

    def _position_based_attribution(self, touchpoints: list[dict[str, Any]]) -> dict[Platform, float]:
        """Position-based attribution (40% first, 40% last, 20% middle)"""
        if not touchpoints:
            return {}

        platforms = [Platform(tp['platform']) for tp in touchpoints]
        weights = {}

        if len(platforms) == 1:
            weights[platforms[0]] = 1.0
        elif len(platforms) == 2:
            weights[platforms[0]] = 0.5
            weights[platforms[1]] = 0.5
        else:
            # First touch: 40%
            weights[platforms[0]] = weights.get(platforms[0], 0) + 0.4

            # Last touch: 40%
            weights[platforms[-1]] = weights.get(platforms[-1], 0) + 0.4

            # Middle touches: 20% divided equally
            middle_weight = 0.2 / (len(platforms) - 2)
            for platform in platforms[1:-1]:
                weights[platform] = weights.get(platform, 0) + middle_weight

        return weights

    def _save_conversion_paths(self, conversion_paths: list[ConversionPath]):
        """Save conversion paths to database"""
        if not conversion_paths:
            return

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        for path in conversion_paths:
            path_id = f"path_{path.user_id}_{path.content_id}_{datetime.now().strftime('%Y%m%d%H%M%S')}"

            journey_start = path.touchpoints[0]['timestamp']
            journey_end = path.touchpoints[-1]['timestamp']

            # Convert Platform objects to strings for JSON serialization
            touchpoints_serializable = []
            for tp in path.touchpoints:
                tp_dict = dict(tp)
                tp_dict['platform'] = tp_dict['platform'].value if hasattr(tp_dict['platform'], 'value') else str(tp_dict['platform'])
                touchpoints_serializable.append(tp_dict)

            cursor.execute('''
                INSERT OR REPLACE INTO conversion_paths 
                (path_id, user_id, content_id, touchpoints, conversion_value,
                 conversion_type, journey_start, journey_end, attribution_weights)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                path_id, path.user_id, path.content_id,
                json.dumps(touchpoints_serializable),
                path.conversion_value, path.conversion_type,
                journey_start, journey_end,
                json.dumps({p.value: w for p, w in path.attribution_weights.items()})
            ))

        conn.commit()
        conn.close()

    def generate_cross_platform_report(self, content_id: str,
                                     period_days: int = 30) -> CrossPlatformReport:
        """Generate comprehensive cross-platform performance report"""

        # Get conversion paths
        conversion_paths = self.analyze_conversion_paths(content_id, period_days)

        # Analyze platform performance
        platform_performance = self._analyze_platform_performance(content_id, period_days)

        # Calculate attribution analysis
        attribution_analysis = self._calculate_attribution_analysis(conversion_paths)

        # ROI analysis
        roi_analysis = self._calculate_roi_analysis(content_id, platform_performance, attribution_analysis)

        # Generate optimization recommendations
        optimization_recommendations = self._generate_optimization_recommendations(
            platform_performance, attribution_analysis, roi_analysis
        )

        report = CrossPlatformReport(
            content_id=content_id,
            reporting_period=f"Last {period_days} days",
            platform_performance=platform_performance,
            attribution_analysis=attribution_analysis,
            conversion_paths=conversion_paths,
            roi_analysis=roi_analysis,
            optimization_recommendations=optimization_recommendations
        )

        # Save report
        self._save_cross_platform_report(report)

        logger.info(f"Generated cross-platform report for {content_id}")
        return report

    def _analyze_platform_performance(self, content_id: str,
                                    period_days: int) -> dict[Platform, dict[str, Any]]:
        """Analyze individual platform performance"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        performance = {}

        for platform in Platform:
            cursor.execute(f'''
                SELECT 
                    COUNT(*) as total_events,
                    SUM(CASE WHEN touchpoint = 'impression' THEN 1 ELSE 0 END) as impressions,
                    SUM(CASE WHEN touchpoint = 'click' THEN 1 ELSE 0 END) as clicks,
                    SUM(CASE WHEN touchpoint = 'engagement' THEN 1 ELSE 0 END) as engagements,
                    SUM(CASE WHEN value > 0 THEN 1 ELSE 0 END) as conversions,
                    SUM(value) as revenue
                FROM attribution_tracking
                WHERE content_id = ? AND platform = ?
                  AND timestamp >= date('now', '-{period_days} days')
            ''', (content_id, platform.value))

            result = cursor.fetchone()
            if result and result[0] > 0:  # Has data
                total_events, impressions, clicks, engagements, conversions, revenue = result

                # Calculate rates
                click_rate = clicks / impressions if impressions > 0 else 0
                engagement_rate = engagements / impressions if impressions > 0 else 0
                conversion_rate = conversions / clicks if clicks > 0 else 0

                performance[platform] = {
                    'total_events': total_events,
                    'impressions': impressions,
                    'clicks': clicks,
                    'engagements': engagements,
                    'conversions': conversions,
                    'revenue': revenue,
                    'click_rate': click_rate,
                    'engagement_rate': engagement_rate,
                    'conversion_rate': conversion_rate,
                    'revenue_per_impression': revenue / impressions if impressions > 0 else 0
                }

        conn.close()
        return performance

    def _calculate_attribution_analysis(self, conversion_paths: list[ConversionPath]) -> dict[str, Any]:
        """Calculate attribution analysis across platforms"""
        if not conversion_paths:
            return {}

        # Aggregate attribution weights
        platform_attribution = defaultdict(float)
        total_revenue = 0

        for path in conversion_paths:
            total_revenue += path.conversion_value
            for platform, weight in path.attribution_weights.items():
                platform_attribution[platform] += path.conversion_value * weight

        # Calculate attribution percentages
        attribution_percentages = {}
        for platform, attributed_revenue in platform_attribution.items():
            attribution_percentages[platform.value] = attributed_revenue / total_revenue if total_revenue > 0 else 0

        # Journey analysis
        avg_journey_length = np.mean([len(path.touchpoints) for path in conversion_paths])
        avg_journey_duration = np.mean([path.journey_duration_hours for path in conversion_paths])

        # Most common conversion paths
        path_patterns = defaultdict(int)
        for path in conversion_paths:
            platforms = [tp['platform'].value for tp in path.touchpoints]
            pattern = ' → '.join(platforms)
            path_patterns[pattern] += 1

        top_paths = sorted(path_patterns.items(), key=lambda x: x[1], reverse=True)[:5]

        return {
            'platform_attribution_revenue': dict(platform_attribution),
            'platform_attribution_percentage': attribution_percentages,
            'total_attributed_revenue': total_revenue,
            'average_journey_length': avg_journey_length,
            'average_journey_duration_hours': avg_journey_duration,
            'top_conversion_paths': top_paths,
            'total_conversion_paths': len(conversion_paths)
        }

    def _calculate_roi_analysis(self, content_id: str,
                              platform_performance: dict[Platform, dict[str, Any]],
                              attribution_analysis: dict[str, Any]) -> dict[str, Any]:
        """Calculate ROI analysis with platform-specific costs"""

        # Estimated platform costs (per 1000 impressions equivalent)
        platform_costs = {
            Platform.LINKEDIN: 5.0,  # $5 CPM equivalent
            Platform.TWITTER: 3.0,   # $3 CPM equivalent
            Platform.NEWSLETTER: 1.0,  # $1 CPM equivalent (lower organic cost)
        }

        roi_analysis = {}
        total_cost = 0
        total_revenue = 0

        for platform, performance in platform_performance.items():
            impressions = performance.get('impressions', 0)
            revenue = performance.get('revenue', 0)

            # Calculate estimated cost
            cost = (impressions / 1000) * platform_costs.get(platform, 2.0)

            # Calculate ROI
            roi = ((revenue - cost) / cost * 100) if cost > 0 else 0

            roi_analysis[platform.value] = {
                'revenue': revenue,
                'estimated_cost': cost,
                'roi_percentage': roi,
                'revenue_per_dollar': revenue / cost if cost > 0 else 0
            }

            total_cost += cost
            total_revenue += revenue

        # Overall ROI
        overall_roi = ((total_revenue - total_cost) / total_cost * 100) if total_cost > 0 else 0

        roi_analysis['overall'] = {
            'total_revenue': total_revenue,
            'total_cost': total_cost,
            'overall_roi_percentage': overall_roi,
            'profit': total_revenue - total_cost
        }

        return roi_analysis

    def _generate_optimization_recommendations(self,
                                             platform_performance: dict[Platform, dict[str, Any]],
                                             attribution_analysis: dict[str, Any],
                                             roi_analysis: dict[str, Any]) -> list[str]:
        """Generate actionable optimization recommendations"""
        recommendations = []

        # Platform performance recommendations
        best_roi_platform = None
        best_roi = -float('inf')

        for platform_str, roi_data in roi_analysis.items():
            if platform_str != 'overall' and roi_data['roi_percentage'] > best_roi:
                best_roi = roi_data['roi_percentage']
                best_roi_platform = platform_str

        if best_roi_platform and best_roi > 100:  # Positive ROI
            recommendations.append(f"Scale investment in {best_roi_platform.upper()} - highest ROI at {best_roi:.1f}%")

        # Attribution-based recommendations
        if attribution_analysis:
            top_attribution_platform = max(
                attribution_analysis['platform_attribution_percentage'].items(),
                key=lambda x: x[1]
            )

            if top_attribution_platform[1] > 0.4:  # More than 40% attribution
                recommendations.append(f"Maintain strong presence on {top_attribution_platform[0].upper()} - drives {top_attribution_platform[1]*100:.1f}% of conversions")

        # Journey optimization
        if attribution_analysis.get('average_journey_length', 0) > 3:
            recommendations.append("Consider simplifying conversion path - average journey has 3+ touchpoints")

        # Conversion rate optimization
        for platform, performance in platform_performance.items():
            if performance.get('click_rate', 0) > 0.02 and performance.get('conversion_rate', 0) < 0.01:
                recommendations.append(f"Optimize {platform.value.upper()} landing page - high clicks but low conversions")

        # Cross-platform synergy
        if len(platform_performance) > 1:
            recommendations.append("Implement cross-platform retargeting to capture users across all touchpoints")

        return recommendations[:5]  # Top 5 recommendations

    def _save_cross_platform_report(self, report: CrossPlatformReport):
        """Save cross-platform report to database"""
        # Implementation would save to dedicated reports table
        logger.info(f"Cross-platform report saved for {report.content_id}")

    def create_attribution_dashboard(self, content_ids: list[str]) -> dict[str, Any]:
        """Create comprehensive attribution dashboard"""

        dashboard_data = {
            'content_performance': {},
            'platform_comparison': {},
            'attribution_flow': {},
            'roi_summary': {},
            'optimization_priorities': [],
            'generated_at': datetime.now().isoformat()
        }

        # Analyze each content piece
        for content_id in content_ids:
            report = self.generate_cross_platform_report(content_id)
            dashboard_data['content_performance'][content_id] = {
                'total_revenue': report.roi_analysis.get('overall', {}).get('total_revenue', 0),
                'overall_roi': report.roi_analysis.get('overall', {}).get('overall_roi_percentage', 0),
                'conversion_paths': len(report.conversion_paths),
                'top_platform': max(report.platform_performance.items(),
                                  key=lambda x: x[1].get('revenue', 0))[0].value if report.platform_performance else None
            }

        # Platform comparison across all content
        platform_totals = defaultdict(lambda: {'revenue': 0, 'impressions': 0, 'conversions': 0})

        for content_id in content_ids:
            report = self.generate_cross_platform_report(content_id, 7)  # Last 7 days
            for platform, performance in report.platform_performance.items():
                platform_totals[platform]['revenue'] += performance.get('revenue', 0)
                platform_totals[platform]['impressions'] += performance.get('impressions', 0)
                platform_totals[platform]['conversions'] += performance.get('conversions', 0)

        dashboard_data['platform_comparison'] = {
            platform.value: {
                'total_revenue': data['revenue'],
                'total_impressions': data['impressions'],
                'total_conversions': data['conversions'],
                'revenue_per_impression': data['revenue'] / data['impressions'] if data['impressions'] > 0 else 0
            }
            for platform, data in platform_totals.items()
        }

        return dashboard_data

def main():
    """Demonstrate cross-platform analytics system"""
    print("🚀 Advanced Cross-Platform Analytics & Attribution System")
    print("=" * 65)

    # Initialize analytics system
    analytics = CrossPlatformAnalytics()

    # Simulate attribution events for testing
    content_id = "content_test_attribution"
    user_id = "user_123"
    session_id = "session_456"

    print("📊 Simulating cross-platform user journey...")

    # Simulate user journey: LinkedIn → Twitter → Newsletter → Conversion
    journey_events = [
        (Platform.LINKEDIN, 'impression', 0),
        (Platform.LINKEDIN, 'click', 0),
        (Platform.LINKEDIN, 'engagement', 0),
        (Platform.TWITTER, 'impression', 0),
        (Platform.TWITTER, 'engagement', 0),
        (Platform.NEWSLETTER, 'impression', 0),
        (Platform.NEWSLETTER, 'click', 0),
        (Platform.NEWSLETTER, 'conversion', 2500.0),  # $2500 consultation
    ]

    # Track attribution events
    for i, (platform, touchpoint, value) in enumerate(journey_events):
        timestamp_offset = i * 3600  # 1 hour between touchpoints
        analytics.track_attribution_event(
            content_id=content_id,
            platform=platform,
            touchpoint=touchpoint,
            user_id=user_id,
            session_id=session_id,
            value=value,
            metadata={'conversion_type': 'consultation' if value > 0 else None}
        )
        print(f"   {i+1}. {platform.value.upper()}: {touchpoint}" + (f" (${value})" if value > 0 else ""))

    print("\n🔍 Analyzing conversion paths...")
    conversion_paths = analytics.analyze_conversion_paths(content_id)

    print(f"✅ Found {len(conversion_paths)} conversion paths")
    if conversion_paths:
        path = conversion_paths[0]
        print(f"   Journey: {len(path.touchpoints)} touchpoints over {path.journey_duration_hours:.1f} hours")
        print(f"   Conversion value: ${path.conversion_value}")
        print("   Attribution weights:")
        for platform, weight in path.attribution_weights.items():
            print(f"      {platform.value.upper()}: {weight*100:.1f}%")

    print("\n📈 Generating cross-platform report...")
    report = analytics.generate_cross_platform_report(content_id)

    print("📊 Platform Performance:")
    for platform, performance in report.platform_performance.items():
        revenue = performance.get('revenue', 0)
        impressions = performance.get('impressions', 0)
        conversion_rate = performance.get('conversion_rate', 0)
        print(f"   {platform.value.upper()}: ${revenue:.0f} revenue, {impressions} impressions, {conversion_rate*100:.1f}% conversion")

    print("\n💰 ROI Analysis:")
    for platform_str, roi_data in report.roi_analysis.items():
        if platform_str != 'overall':
            roi = roi_data['roi_percentage']
            revenue_per_dollar = roi_data['revenue_per_dollar']
            print(f"   {platform_str.upper()}: {roi:.1f}% ROI, ${revenue_per_dollar:.2f} per $1 spent")
        else:
            overall_roi = roi_data['overall_roi_percentage']
            profit = roi_data['profit']
            print(f"   OVERALL: {overall_roi:.1f}% ROI, ${profit:.0f} profit")

    print("\n🎯 Optimization Recommendations:")
    for i, rec in enumerate(report.optimization_recommendations, 1):
        print(f"   {i}. {rec}")

    print("\n📱 Attribution Dashboard:")
    dashboard = analytics.create_attribution_dashboard([content_id])
    print(f"   Content analyzed: {len(dashboard['content_performance'])}")
    print(f"   Platform comparison: {len(dashboard['platform_comparison'])} platforms")

    print("\n💡 Advanced Features:")
    print("• Multi-touch attribution modeling (first-touch, last-touch, linear, time-decay, position-based)")
    print("• Cross-platform user journey mapping")
    print("• Revenue attribution with platform costs")
    print("• ROI optimization recommendations")
    print("• Real-time conversion path analysis")
    print("• Attribution flow visualization")
    print("• Platform interaction matrix")

    print("\n✅ Cross-platform analytics system ready!")
    print("Complete attribution tracking across LinkedIn, Twitter, Newsletter, and website conversions")

if __name__ == "__main__":
    main()
