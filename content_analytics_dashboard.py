#!/usr/bin/env python3
"""
Content Analytics Dashboard
Tracks performance metrics for the 52-week content strategy based on Synapse analysis insights.
Monitors engagement, business development, and ROI metrics.
"""

import csv
import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timedelta


@dataclass
class ContentPost:
    """Represents a single content post with all tracking metrics."""
    post_id: str
    date: str
    day_of_week: str
    content_type: str  # Strategic, Technical, Scaling, etc.
    signature_series: str | None  # Fractional CTO Insights, #NOBUILD, etc.
    headline: str
    platform: str
    posting_time: str

    # Engagement metrics
    views: int = 0
    likes: int = 0
    comments: int = 0
    shares: int = 0
    saves: int = 0
    engagement_rate: float = 0.0

    # Business development metrics
    profile_views: int = 0
    connection_requests: int = 0
    consultation_inquiries: int = 0
    discovery_calls: int = 0

    # Content performance
    click_through_rate: float = 0.0
    comment_quality_score: float = 0.0  # 1-5 scale
    business_relevance_score: float = 0.0  # 1-5 scale

@dataclass
class WeeklyPerformance:
    """Weekly aggregated performance metrics."""
    week_number: int
    start_date: str
    quarter: str
    theme: str

    # Engagement totals
    total_posts: int
    total_views: int
    total_engagement: int
    avg_engagement_rate: float

    # Business development totals
    total_profile_views: int
    total_connections: int
    total_inquiries: int
    total_discovery_calls: int

    # Performance analysis
    best_performing_post: str
    best_engagement_rate: float
    optimal_posting_time: str

class ContentAnalytics:
    """Main analytics tracking and dashboard system."""

    def __init__(self, db_path: str = "content_analytics.db"):
        self.db_path = db_path
        self.init_database()

    def init_database(self):
        """Initialize SQLite database for content tracking."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Create posts table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS posts (
                post_id TEXT PRIMARY KEY,
                date TEXT NOT NULL,
                day_of_week TEXT NOT NULL,
                content_type TEXT NOT NULL,
                signature_series TEXT,
                headline TEXT NOT NULL,
                platform TEXT NOT NULL,
                posting_time TEXT NOT NULL,
                views INTEGER DEFAULT 0,
                likes INTEGER DEFAULT 0,
                comments INTEGER DEFAULT 0,
                shares INTEGER DEFAULT 0,
                saves INTEGER DEFAULT 0,
                engagement_rate REAL DEFAULT 0.0,
                profile_views INTEGER DEFAULT 0,
                connection_requests INTEGER DEFAULT 0,
                consultation_inquiries INTEGER DEFAULT 0,
                discovery_calls INTEGER DEFAULT 0,
                click_through_rate REAL DEFAULT 0.0,
                comment_quality_score REAL DEFAULT 0.0,
                business_relevance_score REAL DEFAULT 0.0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Create weekly_performance table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS weekly_performance (
                week_number INTEGER PRIMARY KEY,
                start_date TEXT NOT NULL,
                quarter TEXT NOT NULL,
                theme TEXT NOT NULL,
                total_posts INTEGER DEFAULT 0,
                total_views INTEGER DEFAULT 0,
                total_engagement INTEGER DEFAULT 0,
                avg_engagement_rate REAL DEFAULT 0.0,
                total_profile_views INTEGER DEFAULT 0,
                total_connections INTEGER DEFAULT 0,
                total_inquiries INTEGER DEFAULT 0,
                total_discovery_calls INTEGER DEFAULT 0,
                best_performing_post TEXT,
                best_engagement_rate REAL DEFAULT 0.0,
                optimal_posting_time TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Create business_pipeline table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS business_pipeline (
                inquiry_id TEXT PRIMARY KEY,
                source_post_id TEXT,
                inquiry_date TEXT NOT NULL,
                inquiry_type TEXT NOT NULL,
                company_size TEXT,
                industry TEXT,
                project_value REAL,
                status TEXT DEFAULT 'new',
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (source_post_id) REFERENCES posts (post_id)
            )
        ''')

        conn.commit()
        conn.close()

    def add_post(self, post: ContentPost):
        """Add a new content post to tracking."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            INSERT OR REPLACE INTO posts 
            (post_id, date, day_of_week, content_type, signature_series, headline, 
             platform, posting_time, views, likes, comments, shares, saves, 
             engagement_rate, profile_views, connection_requests, consultation_inquiries,
             discovery_calls, click_through_rate, comment_quality_score, business_relevance_score)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            post.post_id, post.date, post.day_of_week, post.content_type,
            post.signature_series, post.headline, post.platform, post.posting_time,
            post.views, post.likes, post.comments, post.shares, post.saves,
            post.engagement_rate, post.profile_views, post.connection_requests,
            post.consultation_inquiries, post.discovery_calls, post.click_through_rate,
            post.comment_quality_score, post.business_relevance_score
        ))

        conn.commit()
        conn.close()

    def update_post_metrics(self, post_id: str, metrics: dict):
        """Update engagement and business metrics for a post."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Build dynamic update query
        fields = []
        values = []
        for key, value in metrics.items():
            fields.append(f"{key} = ?")
            values.append(value)

        values.append(post_id)

        query = f"UPDATE posts SET {', '.join(fields)} WHERE post_id = ?"
        cursor.execute(query, values)

        conn.commit()
        conn.close()

    def calculate_weekly_performance(self, week_number: int) -> WeeklyPerformance | None:
        """Calculate and store weekly performance metrics."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Get week date range
        start_date = datetime(2025, 1, 6) + timedelta(weeks=week_number-1)  # Week 1 starts Jan 6, 2025
        end_date = start_date + timedelta(days=6)

        # Get posts for the week
        cursor.execute('''
            SELECT * FROM posts 
            WHERE date BETWEEN ? AND ?
        ''', (start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d')))

        posts = cursor.fetchall()

        if not posts:
            return None

        # Calculate aggregated metrics
        total_posts = len(posts)
        total_views = sum(post[8] for post in posts)  # views column
        total_engagement = sum(post[9] + post[10] + post[11] + post[12] for post in posts)  # likes + comments + shares + saves
        avg_engagement_rate = sum(post[13] for post in posts) / total_posts if total_posts > 0 else 0

        total_profile_views = sum(post[14] for post in posts)
        total_connections = sum(post[15] for post in posts)
        total_inquiries = sum(post[16] for post in posts)
        total_discovery_calls = sum(post[17] for post in posts)

        # Find best performing post
        best_post = max(posts, key=lambda x: x[13])  # engagement_rate column
        best_performing_post = best_post[5]  # headline column
        best_engagement_rate = best_post[13]

        # Determine optimal posting time (most common time for high engagement)
        high_engagement_posts = [post for post in posts if post[13] > avg_engagement_rate]
        if high_engagement_posts:
            posting_times = [post[7] for post in high_engagement_posts]
            optimal_posting_time = max(set(posting_times), key=posting_times.count)
        else:
            optimal_posting_time = "6:30 AM"  # Default from Synapse analysis

        # Determine quarter and theme
        quarter = f"Q{((week_number - 1) // 13) + 1}"
        themes = {
            "Q1": "Foundation & Strategy",
            "Q2": "Growth & Scaling",
            "Q3": "Optimization & Efficiency",
            "Q4": "Reflection & Future Planning"
        }
        theme = themes.get(quarter, "Unknown")

        performance = WeeklyPerformance(
            week_number=week_number,
            start_date=start_date.strftime('%Y-%m-%d'),
            quarter=quarter,
            theme=theme,
            total_posts=total_posts,
            total_views=total_views,
            total_engagement=total_engagement,
            avg_engagement_rate=avg_engagement_rate,
            total_profile_views=total_profile_views,
            total_connections=total_connections,
            total_inquiries=total_inquiries,
            total_discovery_calls=total_discovery_calls,
            best_performing_post=best_performing_post,
            best_engagement_rate=best_engagement_rate,
            optimal_posting_time=optimal_posting_time
        )

        # Store in database
        cursor.execute('''
            INSERT OR REPLACE INTO weekly_performance
            (week_number, start_date, quarter, theme, total_posts, total_views,
             total_engagement, avg_engagement_rate, total_profile_views, total_connections,
             total_inquiries, total_discovery_calls, best_performing_post, 
             best_engagement_rate, optimal_posting_time)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            performance.week_number, performance.start_date, performance.quarter,
            performance.theme, performance.total_posts, performance.total_views,
            performance.total_engagement, performance.avg_engagement_rate,
            performance.total_profile_views, performance.total_connections,
            performance.total_inquiries, performance.total_discovery_calls,
            performance.best_performing_post, performance.best_engagement_rate,
            performance.optimal_posting_time
        ))

        conn.commit()
        conn.close()

        return performance

    def generate_dashboard_report(self, output_file: str = "content_dashboard_report.html"):
        """Generate HTML dashboard report with visualizations."""
        conn = sqlite3.connect(self.db_path)

        # Get summary statistics
        cursor = conn.cursor()
        cursor.execute('''
            SELECT 
                COUNT(*) as total_posts,
                SUM(views) as total_views,
                SUM(likes + comments + shares + saves) as total_engagement,
                AVG(engagement_rate) as avg_engagement_rate,
                SUM(consultation_inquiries) as total_inquiries,
                SUM(discovery_calls) as total_calls
            FROM posts
        ''')

        summary = cursor.fetchone()

        # Get top performing posts
        cursor.execute('''
            SELECT headline, engagement_rate, content_type, date
            FROM posts
            ORDER BY engagement_rate DESC
            LIMIT 10
        ''')

        top_posts = cursor.fetchall()

        # Get weekly trends
        cursor.execute('''
            SELECT week_number, avg_engagement_rate, total_inquiries, theme
            FROM weekly_performance
            ORDER BY week_number
        ''')

        weekly_trends = cursor.fetchall()

        # Generate HTML report
        html_content = f'''
        <!DOCTYPE html>
        <html>
        <head>
            <title>Content Strategy Dashboard</title>
            <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                .container {{ max-width: 1200px; margin: 0 auto; }}
                .metric-card {{ 
                    display: inline-block; 
                    background: #f8f9fa; 
                    padding: 20px; 
                    margin: 10px; 
                    border-radius: 8px; 
                    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                }}
                .metric-value {{ font-size: 2em; font-weight: bold; color: #007bff; }}
                .metric-label {{ color: #6c757d; margin-top: 5px; }}
                .chart-container {{ width: 100%; height: 400px; margin: 20px 0; }}
                table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
                th, td {{ padding: 12px; text-align: left; border-bottom: 1px solid #ddd; }}
                th {{ background-color: #f8f9fa; }}
            </style>
        </head>
        <body>
            <div class="container">
                <h1>📊 Content Strategy Dashboard</h1>
                <p><strong>Based on Synapse Analysis:</strong> 40% higher engagement from technical debates, 6:30 AM optimal timing</p>
                
                <h2>📈 Key Performance Metrics</h2>
                <div class="metric-card">
                    <div class="metric-value">{summary[0] or 0}</div>
                    <div class="metric-label">Total Posts</div>
                </div>
                <div class="metric-card">
                    <div class="metric-value">{summary[1] or 0:,}</div>
                    <div class="metric-label">Total Views</div>
                </div>
                <div class="metric-card">
                    <div class="metric-value">{summary[2] or 0:,}</div>
                    <div class="metric-label">Total Engagement</div>
                </div>
                <div class="metric-card">
                    <div class="metric-value">{(summary[3] or 0) * 100:.1f}%</div>
                    <div class="metric-label">Avg Engagement Rate</div>
                </div>
                <div class="metric-card">
                    <div class="metric-value">{summary[4] or 0}</div>
                    <div class="metric-label">Consultation Inquiries</div>
                </div>
                <div class="metric-card">
                    <div class="metric-value">{summary[5] or 0}</div>
                    <div class="metric-label">Discovery Calls</div>
                </div>
                
                <h2>🏆 Top Performing Posts</h2>
                <table>
                    <tr>
                        <th>Headline</th>
                        <th>Engagement Rate</th>
                        <th>Content Type</th>
                        <th>Date</th>
                    </tr>
        '''

        for post in top_posts:
            html_content += f'''
                    <tr>
                        <td>{post[0]}</td>
                        <td>{post[1] * 100:.1f}%</td>
                        <td>{post[2]}</td>
                        <td>{post[3]}</td>
                    </tr>
            '''

        html_content += '''
                </table>
                
                <h2>📅 Weekly Performance Trends</h2>
                <div class="chart-container">
                    <canvas id="weeklyChart"></canvas>
                </div>
                
                <script>
                    const ctx = document.getElementById('weeklyChart').getContext('2d');
                    const chart = new Chart(ctx, {
                        type: 'line',
                        data: {
        '''

        # Add chart data
        week_labels = [f"Week {w[0]}" for w in weekly_trends]
        engagement_data = [w[1] * 100 for w in weekly_trends]
        inquiry_data = [w[2] for w in weekly_trends]

        html_content += f'''
                            labels: {json.dumps(week_labels)},
                            datasets: [{{
                                label: 'Engagement Rate (%)',
                                data: {json.dumps(engagement_data)},
                                borderColor: 'rgb(75, 192, 192)',
                                backgroundColor: 'rgba(75, 192, 192, 0.2)',
                                tension: 0.1
                            }}, {{
                                label: 'Consultation Inquiries',
                                data: {json.dumps(inquiry_data)},
                                borderColor: 'rgb(255, 99, 132)',
                                backgroundColor: 'rgba(255, 99, 132, 0.2)',
                                tension: 0.1,
                                yAxisID: 'y1'
                            }}]
                        }},
                        options: {{
                            responsive: true,
                            scales: {{
                                y: {{
                                    type: 'linear',
                                    display: true,
                                    position: 'left',
                                }},
                                y1: {{
                                    type: 'linear',
                                    display: true,
                                    position: 'right',
                                    grid: {{
                                        drawOnChartArea: false,
                                    }},
                                }}
                            }}
                        }}
                    }});
                </script>
                
                <h2>💡 Optimization Insights</h2>
                <ul>
                    <li><strong>Best Day for Technical Content:</strong> Tuesday 6:30 AM (40% higher engagement)</li>
                    <li><strong>Best Day for Business Development:</strong> Wednesday morning</li>
                    <li><strong>Signature Series Performance:</strong> Track "Fractional CTO Insights" vs "#NOBUILD Chronicles"</li>
                    <li><strong>Target Engagement Rate:</strong> 6-10% (industry average: 2-3%)</li>
                    <li><strong>Business Development Target:</strong> 5-10 monthly consultation inquiries</li>
                </ul>
            </div>
        </body>
        </html>
        '''

        with open(output_file, 'w') as f:
            f.write(html_content)

        conn.close()

        return output_file

    def export_data_csv(self, output_file: str = "content_data_export.csv"):
        """Export all data to CSV for external analysis."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('SELECT * FROM posts ORDER BY date')
        posts = cursor.fetchall()

        # Get column names
        cursor.execute('PRAGMA table_info(posts)')
        columns = [column[1] for column in cursor.fetchall()]

        with open(output_file, 'w', newline='') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(columns)
            writer.writerows(posts)

        conn.close()
        return output_file

def main():
    """Example usage and testing."""
    analytics = ContentAnalytics()

    # Example: Add a sample post
    sample_post = ContentPost(
        post_id="2025-01-06-monday",
        date="2025-01-06",
        day_of_week="Monday",
        content_type="Strategic Tech Leadership",
        signature_series="Fractional CTO Insights",
        headline="New Year Technical Leadership Foundations",
        platform="LinkedIn",
        posting_time="6:30 AM",
        views=1250,
        likes=47,
        comments=12,
        shares=8,
        saves=15,
        engagement_rate=0.066,  # 6.6%
        profile_views=45,
        connection_requests=3,
        consultation_inquiries=1,
        discovery_calls=0
    )

    analytics.add_post(sample_post)

    # Calculate weekly performance for week 1
    weekly_perf = analytics.calculate_weekly_performance(1)
    if weekly_perf:
        print(f"Week 1 Performance: {weekly_perf.avg_engagement_rate * 100:.1f}% avg engagement")

    # Generate dashboard
    dashboard_file = analytics.generate_dashboard_report()
    print(f"Dashboard generated: {dashboard_file}")

    # Export data
    csv_file = analytics.export_data_csv()
    print(f"Data exported: {csv_file}")

if __name__ == "__main__":
    main()
