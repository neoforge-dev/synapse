#!/usr/bin/env python3
"""
Week 3 Content Performance Tracker
Tracks business development metrics for Week 3 Team Building & Culture content
"""

import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime


@dataclass
class Week3ContentPost:
    """Week 3 specific content tracking"""
    post_id: str
    date: str
    day: str
    title: str
    series: str
    posting_time: str
    business_dev_focus: str
    target_consultation_type: str

    # Performance metrics
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
    inquiry_details: list[dict] = None

    def __post_init__(self):
        if self.inquiry_details is None:
            self.inquiry_details = []

class Week3BusinessTracker:
    """Track business development results from Week 3 content"""

    def __init__(self, db_path: str = "week3_business_development.db"):
        self.db_path = db_path
        self.init_database()
        self.setup_week3_content()

    def init_database(self):
        """Initialize tracking database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS week3_posts (
                post_id TEXT PRIMARY KEY,
                date TEXT NOT NULL,
                day TEXT NOT NULL,
                title TEXT NOT NULL,
                series TEXT NOT NULL,
                posting_time TEXT NOT NULL,
                business_dev_focus TEXT NOT NULL,
                target_consultation_type TEXT NOT NULL,
                views INTEGER DEFAULT 0,
                likes INTEGER DEFAULT 0,
                comments INTEGER DEFAULT 0,
                shares INTEGER DEFAULT 0,
                saves INTEGER DEFAULT 0,
                engagement_rate REAL DEFAULT 0.0,
                profile_views INTEGER DEFAULT 0,
                connection_requests INTEGER DEFAULT 0,
                consultation_inquiries INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS consultation_inquiries (
                inquiry_id TEXT PRIMARY KEY,
                source_post_id TEXT,
                inquiry_date TEXT NOT NULL,
                inquiry_type TEXT NOT NULL,
                company_name TEXT,
                contact_name TEXT,
                company_size TEXT,
                inquiry_details TEXT,
                estimated_value REAL,
                status TEXT DEFAULT 'new',
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (source_post_id) REFERENCES week3_posts (post_id)
            )
        ''')

        conn.commit()
        conn.close()

    def setup_week3_content(self):
        """Initialize Week 3 content posts for tracking"""
        week3_posts = [
            Week3ContentPost(
                post_id="2025-01-20-monday",
                date="2025-01-20",
                day="Monday",
                title="Building a 10x Engineering Team: It's Not About 10x Developers",
                series="Strategic Tech Leadership",
                posting_time="7:00 AM",
                business_dev_focus="Team building consultation",
                target_consultation_type="Engineering team performance assessment"
            ),
            Week3ContentPost(
                post_id="2025-01-21-tuesday",
                date="2025-01-21",
                day="Tuesday",
                title="Code Review Culture: The Make-or-Break Factor for Engineering Teams",
                series="Technical Deep Dive + Culture",
                posting_time="6:30 AM",
                business_dev_focus="Engineering culture optimization",
                target_consultation_type="Code review process and team culture assessment"
            ),
            Week3ContentPost(
                post_id="2025-01-22-wednesday",
                date="2025-01-22",
                day="Wednesday",
                title="Hiring Your First 10 Developers: Lessons from 5 Scaling Journeys",
                series="Startup Scaling Insights",
                posting_time="8:00 AM",
                business_dev_focus="Startup hiring strategy",
                target_consultation_type="Early-stage technical hiring consultation"
            ),
            Week3ContentPost(
                post_id="2025-01-23-thursday",
                date="2025-01-23",
                day="Thursday",
                title="Python Project Structure: From Solo Script to Team Codebase",
                series="FastAPI Production + Team Practices",
                posting_time="6:30 AM",
                business_dev_focus="Team collaboration optimization",
                target_consultation_type="Code organization and team productivity assessment"
            ),
            Week3ContentPost(
                post_id="2025-01-24-friday",
                date="2025-01-24",
                day="Friday",
                title="The Mentor Who Taught Me to Say No: A Career-Changing Lesson",
                series="Career Development + Leadership",
                posting_time="8:30 AM",
                business_dev_focus="Leadership development",
                target_consultation_type="Technical leadership coaching and mentorship"
            ),
            Week3ContentPost(
                post_id="2025-01-25-saturday",
                date="2025-01-25",
                day="Saturday",
                title="Weekend Project: Building a Developer Community Slack Bot in 2 Hours",
                series="Community Engagement",
                posting_time="10:00 AM",
                business_dev_focus="Team productivity automation",
                target_consultation_type="Team process optimization and automation"
            ),
            Week3ContentPost(
                post_id="2025-01-26-sunday",
                date="2025-01-26",
                day="Sunday",
                title="The Bug That Taught Me About Empathy (Sunday Reflection)",
                series="Personal Stories/Reflection",
                posting_time="6:00 PM",
                business_dev_focus="Empathetic technical leadership",
                target_consultation_type="Technical leadership development and culture building"
            )
        ]

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        for post in week3_posts:
            cursor.execute('''
                INSERT OR REPLACE INTO week3_posts 
                (post_id, date, day, title, series, posting_time, business_dev_focus, target_consultation_type)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                post.post_id, post.date, post.day, post.title, post.series,
                post.posting_time, post.business_dev_focus, post.target_consultation_type
            ))

        conn.commit()
        conn.close()

    def update_post_metrics(self, post_id: str, metrics: dict):
        """Update engagement metrics for a post"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        fields = []
        values = []
        for key, value in metrics.items():
            fields.append(f"{key} = ?")
            values.append(value)

        values.append(post_id)

        query = f"UPDATE week3_posts SET {', '.join(fields)} WHERE post_id = ?"
        cursor.execute(query, values)

        conn.commit()
        conn.close()

    def log_consultation_inquiry(self, source_post_id: str, inquiry_details: dict):
        """Log a consultation inquiry from content engagement"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        inquiry_id = f"{source_post_id}-inquiry-{datetime.now().strftime('%Y%m%d%H%M%S')}"

        cursor.execute('''
            INSERT INTO consultation_inquiries
            (inquiry_id, source_post_id, inquiry_date, inquiry_type, company_name,
             contact_name, company_size, inquiry_details, estimated_value, status, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            inquiry_id,
            source_post_id,
            inquiry_details.get('inquiry_date', datetime.now().strftime('%Y-%m-%d')),
            inquiry_details.get('inquiry_type', 'Unknown'),
            inquiry_details.get('company_name', ''),
            inquiry_details.get('contact_name', ''),
            inquiry_details.get('company_size', ''),
            json.dumps(inquiry_details),
            inquiry_details.get('estimated_value', 0),
            inquiry_details.get('status', 'new'),
            inquiry_details.get('notes', '')
        ))

        # Update consultation_inquiries count for the post
        cursor.execute('''
            UPDATE week3_posts 
            SET consultation_inquiries = consultation_inquiries + 1 
            WHERE post_id = ?
        ''', (source_post_id,))

        conn.commit()
        conn.close()

        return inquiry_id

    def generate_week3_report(self) -> dict:
        """Generate comprehensive Week 3 business development report"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Get all posts with metrics
        cursor.execute('SELECT * FROM week3_posts ORDER BY date')
        posts = cursor.fetchall()

        # Get all consultation inquiries
        cursor.execute('''
            SELECT ci.*, wp.title, wp.day 
            FROM consultation_inquiries ci
            JOIN week3_posts wp ON ci.source_post_id = wp.post_id
            ORDER BY ci.inquiry_date
        ''')
        inquiries = cursor.fetchall()

        # Calculate totals
        total_views = sum(post[8] for post in posts)
        total_engagement = sum(post[9] + post[10] + post[11] + post[12] for post in posts)
        avg_engagement_rate = sum(post[13] for post in posts) / len(posts) if posts else 0
        total_inquiries = sum(post[16] for post in posts)

        # Calculate estimated pipeline value
        total_pipeline_value = sum(float(inquiry[8]) for inquiry in inquiries if inquiry[8])

        report = {
            'week3_summary': {
                'total_posts': len(posts),
                'total_views': total_views,
                'total_engagement': total_engagement,
                'avg_engagement_rate': avg_engagement_rate,
                'total_consultation_inquiries': total_inquiries,
                'total_pipeline_value': total_pipeline_value
            },
            'posts_performance': [],
            'consultation_inquiries': [],
            'business_development_analysis': {}
        }

        # Post performance details
        for post in posts:
            report['posts_performance'].append({
                'post_id': post[0],
                'day': post[2],
                'title': post[3],
                'engagement_rate': post[13],
                'consultation_inquiries': post[16],
                'business_dev_focus': post[6]
            })

        # Consultation inquiry details
        for inquiry in inquiries:
            report['consultation_inquiries'].append({
                'inquiry_id': inquiry[0],
                'source_post': inquiry[12],  # title
                'post_day': inquiry[13],     # day
                'inquiry_type': inquiry[3],
                'company_size': inquiry[6],
                'estimated_value': inquiry[8],
                'status': inquiry[9]
            })

        # Business development analysis
        if inquiries:
            # Best performing day for inquiries
            day_inquiries = {}
            for inquiry in inquiries:
                day = inquiry[13]
                day_inquiries[day] = day_inquiries.get(day, 0) + 1

            best_day = max(day_inquiries.items(), key=lambda x: x[1])

            report['business_development_analysis'] = {
                'best_day_for_inquiries': best_day[0],
                'inquiries_on_best_day': best_day[1],
                'most_valuable_inquiry_type': max(set(inquiry[3] for inquiry in inquiries),
                                                 key=[inquiry[3] for inquiry in inquiries].count),
                'average_inquiry_value': total_pipeline_value / len(inquiries) if inquiries else 0
            }

        conn.close()
        return report

    def generate_html_report(self, output_file: str = "week3_business_development_report.html"):
        """Generate HTML report for Week 3 business development results"""
        report = self.generate_week3_report()

        html_content = f'''
        <!DOCTYPE html>
        <html>
        <head>
            <title>Week 3 Business Development Report</title>
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
                table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
                th, td {{ padding: 12px; text-align: left; border-bottom: 1px solid #ddd; }}
                th {{ background-color: #f8f9fa; }}
                .success {{ color: #28a745; font-weight: bold; }}
                .warning {{ color: #ffc107; font-weight: bold; }}
            </style>
        </head>
        <body>
            <div class="container">
                <h1>📊 Week 3: Team Building & Culture - Business Development Report</h1>
                <p><strong>Content Strategy:</strong> Transform technical expertise into consultation inquiries through team building authority</p>
                
                <h2>🎯 Key Performance Metrics</h2>
                <div class="metric-card">
                    <div class="metric-value">{report['week3_summary']['total_posts']}</div>
                    <div class="metric-label">Content Pieces</div>
                </div>
                <div class="metric-card">
                    <div class="metric-value">{report['week3_summary']['total_views']:,}</div>
                    <div class="metric-label">Total Views</div>
                </div>
                <div class="metric-card">
                    <div class="metric-value">{report['week3_summary']['avg_engagement_rate']*100:.1f}%</div>
                    <div class="metric-label">Avg Engagement Rate</div>
                </div>
                <div class="metric-card">
                    <div class="metric-value">{report['week3_summary']['total_consultation_inquiries']}</div>
                    <div class="metric-label">Consultation Inquiries</div>
                </div>
                <div class="metric-card">
                    <div class="metric-value">${report['week3_summary']['total_pipeline_value']:,.0f}</div>
                    <div class="metric-label">Pipeline Value</div>
                </div>
                
                <h2>📈 Content Performance Analysis</h2>
                <table>
                    <tr>
                        <th>Day</th>
                        <th>Content Focus</th>
                        <th>Engagement Rate</th>
                        <th>Inquiries Generated</th>
                        <th>Business Development Focus</th>
                    </tr>
        '''

        for post in report['posts_performance']:
            engagement_class = "success" if post['engagement_rate'] > 0.08 else "warning" if post['engagement_rate'] > 0.06 else ""
            inquiry_class = "success" if post['consultation_inquiries'] > 0 else ""

            html_content += f'''
                    <tr>
                        <td>{post['day']}</td>
                        <td>{post['title'][:50]}...</td>
                        <td class="{engagement_class}">{post['engagement_rate']*100:.1f}%</td>
                        <td class="{inquiry_class}">{post['consultation_inquiries']}</td>
                        <td>{post['business_dev_focus']}</td>
                    </tr>
            '''

        if report['consultation_inquiries']:
            html_content += '''
                </table>
                
                <h2>💼 Consultation Inquiries Generated</h2>
                <table>
                    <tr>
                        <th>Source Content</th>
                        <th>Inquiry Type</th>
                        <th>Company Size</th>
                        <th>Estimated Value</th>
                        <th>Status</th>
                    </tr>
            '''

            for inquiry in report['consultation_inquiries']:
                html_content += f'''
                        <tr>
                            <td>{inquiry['source_post'][:40]}...</td>
                            <td>{inquiry['inquiry_type']}</td>
                            <td>{inquiry['company_size']}</td>
                            <td>${inquiry['estimated_value']:,.0f}</td>
                            <td>{inquiry['status']}</td>
                        </tr>
                '''

        html_content += '''
                </table>
                
                <h2>🎯 Success Metrics vs Targets</h2>
                <ul>
                    <li><strong>Target Engagement Rate:</strong> 7-9% → <span class="''' + ("success" if report['week3_summary']['avg_engagement_rate'] >= 0.07 else "warning") + f'''">Achieved: {report['week3_summary']['avg_engagement_rate']*100:.1f}%</span></li>
                    <li><strong>Target Consultation Inquiries:</strong> 2-3 → <span class="''' + ("success" if report['week3_summary']['total_consultation_inquiries'] >= 2 else "warning") + f'''">Achieved: {report['week3_summary']['total_consultation_inquiries']}</span></li>
                    <li><strong>Business Development Focus:</strong> Team building and engineering culture authority</li>
                </ul>
                
                <h2>📋 Next Steps</h2>
                <ul>
                    <li>Start LinkedIn posting for Week 3 content</li>
                    <li>Monitor engagement and consultation inquiries</li>
                    <li>Follow up on consultation inquiries within 24 hours</li>
                    <li>Use performance data to optimize Week 4 content</li>
                </ul>
            </div>
        </body>
        </html>
        '''

        with open(output_file, 'w') as f:
            f.write(html_content)

        return output_file

def main():
    """Example usage and testing"""
    tracker = Week3BusinessTracker()

    # Example: Log a consultation inquiry from Monday's post
    inquiry_details = {
        'inquiry_date': '2025-01-20',
        'inquiry_type': 'Team building consultation',
        'company_name': 'Example Startup',
        'contact_name': 'John Doe',
        'company_size': '15-25 employees',
        'estimated_value': 15000,
        'notes': 'Interested in engineering team performance assessment after reading Monday post about 10x teams'
    }

    inquiry_id = tracker.log_consultation_inquiry('2025-01-20-monday', inquiry_details)
    print(f"Logged consultation inquiry: {inquiry_id}")

    # Generate report
    report_file = tracker.generate_html_report()
    print(f"Business development report generated: {report_file}")

    # Print summary
    report = tracker.generate_week3_report()
    print("\nWeek 3 Summary:")
    print(f"Total consultation inquiries: {report['week3_summary']['total_consultation_inquiries']}")
    print(f"Total pipeline value: ${report['week3_summary']['total_pipeline_value']:,.0f}")

if __name__ == "__main__":
    main()
