#!/usr/bin/env python3
"""
Week 3 Analytics Dashboard
Real-time tracking and analysis for Week 3 content performance
"""

import sqlite3
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import matplotlib.pyplot as plt


@dataclass
class ContentPerformanceMetrics:
    """Track real-time performance metrics for content"""
    post_id: str
    platform: str = "LinkedIn"

    # Engagement metrics
    impressions: int = 0
    views: int = 0
    likes: int = 0
    comments: int = 0
    shares: int = 0
    saves: int = 0
    clicks: int = 0

    # Advanced metrics
    engagement_rate: float = 0.0
    click_through_rate: float = 0.0
    save_rate: float = 0.0
    comment_quality_score: float = 0.0

    # Business development metrics
    profile_views: int = 0
    connection_requests: int = 0
    dm_inquiries: int = 0
    consultation_leads: int = 0

    # Timing and context
    posted_at: str = ""
    optimal_timing_score: float = 0.0
    audience_match_score: float = 0.0

    def calculate_engagement_rate(self):
        """Calculate engagement rate from current metrics"""
        if self.impressions > 0:
            total_engagement = self.likes + self.comments + self.shares + self.saves
            self.engagement_rate = total_engagement / self.impressions
        return self.engagement_rate

    def calculate_business_conversion_rate(self):
        """Calculate business lead conversion from engagement"""
        if self.views > 0:
            business_actions = self.profile_views + self.connection_requests + self.dm_inquiries
            return business_actions / self.views
        return 0.0

class Week3AnalyticsDashboard:
    """Advanced analytics dashboard for Week 3 content strategy"""

    def __init__(self, db_path: str = "week3_analytics.db"):
        self.db_path = db_path
        self.init_analytics_database()

    def init_analytics_database(self):
        """Initialize advanced analytics database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Performance metrics table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS content_metrics (
                post_id TEXT PRIMARY KEY,
                platform TEXT DEFAULT 'LinkedIn',
                posted_at TEXT,

                -- Basic engagement
                impressions INTEGER DEFAULT 0,
                views INTEGER DEFAULT 0,
                likes INTEGER DEFAULT 0,
                comments INTEGER DEFAULT 0,
                shares INTEGER DEFAULT 0,
                saves INTEGER DEFAULT 0,
                clicks INTEGER DEFAULT 0,

                -- Calculated metrics
                engagement_rate REAL DEFAULT 0.0,
                click_through_rate REAL DEFAULT 0.0,
                save_rate REAL DEFAULT 0.0,
                comment_quality_score REAL DEFAULT 0.0,

                -- Business metrics
                profile_views INTEGER DEFAULT 0,
                connection_requests INTEGER DEFAULT 0,
                dm_inquiries INTEGER DEFAULT 0,
                consultation_leads INTEGER DEFAULT 0,

                -- Performance scores
                optimal_timing_score REAL DEFAULT 0.0,
                audience_match_score REAL DEFAULT 0.0,

                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Comment analysis table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS comment_analysis (
                comment_id TEXT PRIMARY KEY,
                post_id TEXT,
                comment_text TEXT,
                sentiment_score REAL,
                engagement_quality REAL,
                business_interest_score REAL,
                commenter_profile_type TEXT,
                potential_lead BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (post_id) REFERENCES content_metrics (post_id)
            )
        ''')

        # Timing analysis table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS timing_analysis (
                analysis_id TEXT PRIMARY KEY,
                post_id TEXT,
                day_of_week TEXT,
                hour_posted INTEGER,
                optimal_timing BOOLEAN,
                audience_activity_score REAL,
                performance_vs_predicted REAL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (post_id) REFERENCES content_metrics (post_id)
            )
        ''')

        conn.commit()
        conn.close()

    def update_post_metrics(self, post_id: str, metrics: dict):
        """Update real-time metrics for a post"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Calculate derived metrics
        if 'impressions' in metrics and 'views' in metrics:
            impressions = metrics.get('impressions', 0)
            views = metrics.get('views', 0)
            likes = metrics.get('likes', 0)
            comments = metrics.get('comments', 0)
            shares = metrics.get('shares', 0)
            saves = metrics.get('saves', 0)
            clicks = metrics.get('clicks', 0)

            # Calculate engagement rate
            if impressions > 0:
                total_engagement = likes + comments + shares + saves
                metrics['engagement_rate'] = total_engagement / impressions

            # Calculate click-through rate
            if views > 0:
                metrics['click_through_rate'] = clicks / views
                metrics['save_rate'] = saves / views

        # Insert or update metrics
        fields = list(metrics.keys())
        placeholders = ', '.join(['?' for _ in fields])
        values = list(metrics.values())

        cursor.execute(f'''
            INSERT OR REPLACE INTO content_metrics
            (post_id, {', '.join(fields)}, updated_at)
            VALUES (?, {placeholders}, CURRENT_TIMESTAMP)
        ''', [post_id] + values)

        conn.commit()
        conn.close()

    def analyze_optimal_timing(self, post_id: str, posted_datetime: str):
        """Analyze posting timing effectiveness"""
        posted_dt = datetime.fromisoformat(posted_datetime)
        day_of_week = posted_dt.strftime('%A')
        hour_posted = posted_dt.hour

        # Define optimal timing windows based on research
        optimal_windows = {
            'Tuesday': [6, 7, 8, 9],  # 6:30 AM optimal
            'Thursday': [6, 7, 8, 9], # 6:30 AM optimal
            'Monday': [7, 8, 9],      # 7:00 AM good
            'Wednesday': [7, 8, 9],   # 8:00 AM good
            'Friday': [8, 9, 10],     # 8:30 AM good
            'Saturday': [9, 10, 11],  # 10:00 AM good
            'Sunday': [17, 18, 19]    # 6:00 PM good
        }

        is_optimal = hour_posted in optimal_windows.get(day_of_week, [])

        # Calculate audience activity score (0-100)
        if day_of_week in ['Tuesday', 'Thursday'] and hour_posted in [6, 7]:
            audience_activity_score = 95  # Peak engagement time
        elif day_of_week in ['Monday', 'Wednesday', 'Friday'] and hour_posted in [7, 8, 9]:
            audience_activity_score = 85  # High engagement time
        elif day_of_week == 'Saturday' and hour_posted in [9, 10, 11]:
            audience_activity_score = 70  # Good weekend engagement
        elif day_of_week == 'Sunday' and hour_posted in [17, 18, 19]:
            audience_activity_score = 75  # Good evening engagement
        else:
            audience_activity_score = 40  # Suboptimal timing

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            INSERT OR REPLACE INTO timing_analysis
            (analysis_id, post_id, day_of_week, hour_posted, optimal_timing,
             audience_activity_score, created_at)
            VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        ''', (f"{post_id}_timing", post_id, day_of_week, hour_posted,
              is_optimal, audience_activity_score))

        conn.commit()
        conn.close()

        return {
            'optimal_timing': is_optimal,
            'audience_activity_score': audience_activity_score,
            'timing_recommendation': self._get_timing_recommendation(day_of_week, hour_posted)
        }

    def _get_timing_recommendation(self, day: str, hour: int) -> str:
        """Get timing improvement recommendations"""
        optimal_times = {
            'Monday': '7:00 AM',
            'Tuesday': '6:30 AM (OPTIMAL)',
            'Wednesday': '8:00 AM',
            'Thursday': '6:30 AM (OPTIMAL)',
            'Friday': '8:30 AM',
            'Saturday': '10:00 AM',
            'Sunday': '6:00 PM'
        }

        if day in ['Tuesday', 'Thursday'] and hour == 6:
            return "Perfect timing! Tuesday/Thursday 6:30 AM is optimal."

        return f"Consider posting at {optimal_times.get(day, '8:00 AM')} for better engagement."

    def track_business_inquiry(self, post_id: str, inquiry_type: str, details: dict):
        """Track business development inquiries from content"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Update consultation leads count
        cursor.execute('''
            UPDATE content_metrics
            SET consultation_leads = consultation_leads + 1
            WHERE post_id = ?
        ''', (post_id,))

        # Log detailed inquiry (integrate with existing consultation tracker)
        from week3_content_tracker import Week3BusinessTracker
        business_tracker = Week3BusinessTracker()
        business_tracker.log_consultation_inquiry(post_id, details)

        conn.commit()
        conn.close()

    def generate_performance_report(self) -> dict:
        """Generate comprehensive performance analysis"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Get all metrics
        cursor.execute('''
            SELECT * FROM content_metrics
            ORDER BY posted_at
        ''')
        metrics = cursor.fetchall()

        # Get timing analysis
        cursor.execute('''
            SELECT ta.*, cm.engagement_rate
            FROM timing_analysis ta
            JOIN content_metrics cm ON ta.post_id = cm.post_id
        ''')
        timing_data = cursor.fetchall()

        conn.close()

        # Calculate summary statistics
        total_posts = len(metrics)
        total_impressions = sum(m[3] for m in metrics if m[3])
        total_engagement = sum(m[5] + m[6] + m[7] + m[8] for m in metrics)
        avg_engagement_rate = sum(m[10] for m in metrics if m[10]) / total_posts if total_posts > 0 else 0
        total_business_leads = sum(m[16] for m in metrics if m[16])

        # Analyze optimal timing performance
        optimal_posts = [t for t in timing_data if t[4]]  # optimal_timing = True
        optimal_avg_engagement = sum(t[6] for t in optimal_posts) / len(optimal_posts) if optimal_posts else 0

        report = {
            'summary': {
                'total_posts': total_posts,
                'total_impressions': total_impressions,
                'total_engagement_actions': total_engagement,
                'average_engagement_rate': avg_engagement_rate,
                'total_business_leads': total_business_leads,
                'business_conversion_rate': total_business_leads / total_impressions if total_impressions > 0 else 0
            },
            'timing_analysis': {
                'optimal_timing_posts': len(optimal_posts),
                'optimal_timing_avg_engagement': optimal_avg_engagement,
                'timing_improvement_opportunity': optimal_avg_engagement - avg_engagement_rate
            },
            'performance_by_post': [],
            'recommendations': []
        }

        # Add per-post performance
        for metric in metrics:
            report['performance_by_post'].append({
                'post_id': metric[0],
                'engagement_rate': metric[10],
                'business_leads': metric[16],
                'timing_score': metric[18]  # optimal_timing_score
            })

        # Generate recommendations
        if avg_engagement_rate < 0.07:
            report['recommendations'].append("Engagement below target (7%). Focus on Tuesday/Thursday 6:30 AM posting.")

        if total_business_leads < 2:
            report['recommendations'].append("Business leads below target (2-3). Strengthen CTAs and business value propositions.")

        if len(optimal_posts) < total_posts * 0.5:
            report['recommendations'].append("Less than 50% of posts at optimal timing. Use Tuesday/Thursday 6:30 AM more frequently.")

        return report

    def create_analytics_visualization(self, output_dir: str = "analytics_reports"):
        """Create visual analytics dashboard"""
        Path(output_dir).mkdir(exist_ok=True)

        conn = sqlite3.connect(self.db_path)

        # Get data for visualization
        metrics_df = []
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM content_metrics')

        for row in cursor.fetchall():
            metrics_df.append({
                'post_id': row[0],
                'engagement_rate': row[10],
                'business_leads': row[16],
                'timing_score': row[18]
            })

        conn.close()

        if not metrics_df:
            return None

        # Create engagement rate chart
        plt.figure(figsize=(12, 8))

        plt.subplot(2, 2, 1)
        posts = [m['post_id'].split('-')[2] for m in metrics_df]  # Extract day
        engagement_rates = [m['engagement_rate'] * 100 for m in metrics_df]
        plt.bar(posts, engagement_rates)
        plt.axhline(y=7, color='r', linestyle='--', label='Target (7%)')
        plt.title('Engagement Rate by Day')
        plt.ylabel('Engagement Rate (%)')
        plt.legend()

        plt.subplot(2, 2, 2)
        business_leads = [m['business_leads'] for m in metrics_df]
        plt.bar(posts, business_leads)
        plt.axhline(y=1, color='r', linestyle='--', label='Target (1 per post)')
        plt.title('Business Leads by Day')
        plt.ylabel('Business Leads')
        plt.legend()

        plt.subplot(2, 2, 3)
        timing_scores = [m['timing_score'] for m in metrics_df]
        plt.bar(posts, timing_scores)
        plt.title('Timing Optimization Score')
        plt.ylabel('Timing Score')

        plt.subplot(2, 2, 4)
        # Correlation between timing and engagement
        plt.scatter(timing_scores, engagement_rates)
        plt.xlabel('Timing Score')
        plt.ylabel('Engagement Rate (%)')
        plt.title('Timing vs Engagement Correlation')

        plt.tight_layout()
        plt.savefig(f"{output_dir}/week3_analytics_dashboard.png", dpi=300, bbox_inches='tight')
        plt.close()

        return f"{output_dir}/week3_analytics_dashboard.png"

def main():
    """Example usage and testing"""
    dashboard = Week3AnalyticsDashboard()

    # Example: Update metrics for Monday post
    monday_metrics = {
        'posted_at': '2025-01-20T07:00:00',
        'impressions': 1500,
        'views': 120,
        'likes': 85,
        'comments': 12,
        'shares': 8,
        'saves': 15,
        'profile_views': 25,
        'connection_requests': 3,
        'dm_inquiries': 2
    }

    dashboard.update_post_metrics('2025-01-20-monday', monday_metrics)

    # Analyze timing
    timing_analysis = dashboard.analyze_optimal_timing('2025-01-20-monday', '2025-01-20T07:00:00')
    print(f"Timing analysis: {timing_analysis}")

    # Generate report
    report = dashboard.generate_performance_report()
    print("Performance summary:")
    print(f"Average engagement rate: {report['summary']['average_engagement_rate']*100:.1f}%")
    print(f"Business leads: {report['summary']['total_business_leads']}")

    # Create visualization
    chart_path = dashboard.create_analytics_visualization()
    if chart_path:
        print(f"Analytics dashboard saved: {chart_path}")

if __name__ == "__main__":
    main()
