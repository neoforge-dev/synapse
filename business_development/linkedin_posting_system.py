#!/usr/bin/env python3
"""
LinkedIn Posting and Business Development System
Real-time posting, engagement tracking, and consultation inquiry detection
"""

import logging
import sqlite3
from dataclasses import dataclass
from datetime import datetime
from typing import Any

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@dataclass
class LinkedInPost:
    """Structure for LinkedIn post data"""
    post_id: str
    content: str
    posted_at: str
    week_theme: str
    day: str
    target_audience: str
    business_objective: str
    expected_engagement_rate: float
    expected_consultation_inquiries: int

    # Real performance metrics
    impressions: int = 0
    views: int = 0
    likes: int = 0
    comments: int = 0
    shares: int = 0
    saves: int = 0
    clicks: int = 0

    # Business development metrics
    profile_views: int = 0
    connection_requests: int = 0
    dm_inquiries: int = 0
    consultation_requests: int = 0

    # Calculated metrics
    actual_engagement_rate: float = 0.0
    business_conversion_rate: float = 0.0
    roi_score: float = 0.0

@dataclass
class ConsultationInquiry:
    """Structure for consultation inquiry tracking"""
    inquiry_id: str
    source_post_id: str
    contact_name: str
    company: str
    company_size: str
    inquiry_type: str  # team_building, architecture, fractional_cto, nobuild_audit
    inquiry_channel: str  # comment, dm, profile_visit, connection_request
    inquiry_text: str
    estimated_value: int
    priority_score: int  # 1-5 based on company size and inquiry type
    status: str  # new, contacted, discovery_scheduled, proposal_sent, closed_won, closed_lost
    created_at: str
    last_contact: str = ""
    notes: str = ""

class LinkedInBusinessDevelopmentEngine:
    """Complete LinkedIn posting and business development system"""

    def __init__(self, db_path: str = "linkedin_business_development.db"):
        self.db_path = db_path
        self.init_database()

    def init_database(self):
        """Initialize business development tracking database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # LinkedIn posts table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS linkedin_posts (
                post_id TEXT PRIMARY KEY,
                content TEXT,
                posted_at TEXT,
                week_theme TEXT,
                day TEXT,
                target_audience TEXT,
                business_objective TEXT,
                expected_engagement_rate REAL,
                expected_consultation_inquiries INTEGER,
                
                -- Real performance metrics
                impressions INTEGER DEFAULT 0,
                views INTEGER DEFAULT 0,
                likes INTEGER DEFAULT 0,
                comments INTEGER DEFAULT 0,
                shares INTEGER DEFAULT 0,
                saves INTEGER DEFAULT 0,
                clicks INTEGER DEFAULT 0,
                
                -- Business development metrics
                profile_views INTEGER DEFAULT 0,
                connection_requests INTEGER DEFAULT 0,
                dm_inquiries INTEGER DEFAULT 0,
                consultation_requests INTEGER DEFAULT 0,
                
                -- Calculated metrics
                actual_engagement_rate REAL DEFAULT 0.0,
                business_conversion_rate REAL DEFAULT 0.0,
                roi_score REAL DEFAULT 0.0,
                
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Consultation inquiries table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS consultation_inquiries (
                inquiry_id TEXT PRIMARY KEY,
                source_post_id TEXT,
                contact_name TEXT,
                company TEXT,
                company_size TEXT,
                inquiry_type TEXT,
                inquiry_channel TEXT,
                inquiry_text TEXT,
                estimated_value INTEGER,
                priority_score INTEGER,
                status TEXT,
                created_at TEXT,
                last_contact TEXT,
                notes TEXT,
                FOREIGN KEY (source_post_id) REFERENCES linkedin_posts (post_id)
            )
        ''')

        # Business development pipeline table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS business_pipeline (
                pipeline_id TEXT PRIMARY KEY,
                month TEXT,
                total_posts INTEGER,
                total_impressions INTEGER,
                total_engagement INTEGER,
                total_inquiries INTEGER,
                discovery_calls INTEGER,
                proposals_sent INTEGER,
                contracts_won INTEGER,
                revenue_generated INTEGER,
                pipeline_value INTEGER,
                conversion_rate REAL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        conn.commit()
        conn.close()
        logger.info("Business development database initialized")

    def schedule_week3_posts(self):
        """Schedule all Week 3 team building posts for LinkedIn"""
        week3_posts = [
            {
                "post_id": "2025-01-20-monday-10x-teams",
                "content_file": "/Users/bogdan/til/graph-rag-mcp/content/2025/Q1_Foundation_Strategy/Week_03_Team_Building_Culture/final/Monday_10x_Engineering_Team_FINAL.md",
                "posted_at": "2025-01-20T07:00:00",
                "week_theme": "Team Building and Culture",
                "day": "Monday",
                "target_audience": "Startup founders, CTOs, engineering managers",
                "business_objective": "Generate 2-3 team building consultation inquiries",
                "expected_engagement_rate": 0.08,
                "expected_consultation_inquiries": 2
            },
            {
                "post_id": "2025-01-21-tuesday-code-reviews",
                "content_file": "/Users/bogdan/til/graph-rag-mcp/content/2025/Q1_Foundation_Strategy/Week_03_Team_Building_Culture/final/Tuesday_Code_Review_Culture_FINAL.md",
                "posted_at": "2025-01-21T06:30:00",  # Optimal timing
                "week_theme": "Team Building and Culture",
                "day": "Tuesday",
                "target_audience": "Technical leads, senior developers",
                "business_objective": "Position team culture expertise",
                "expected_engagement_rate": 0.09,  # 6:30 AM boost
                "expected_consultation_inquiries": 1
            },
            {
                "post_id": "2025-01-22-wednesday-hiring",
                "content_file": "/Users/bogdan/til/graph-rag-mcp/content/2025/Q1_Foundation_Strategy/Week_03_Team_Building_Culture/final/Wednesday_Hiring_Strategy_FINAL.md",
                "posted_at": "2025-01-22T08:00:00",
                "week_theme": "Team Building and Culture",
                "day": "Wednesday",
                "target_audience": "Startup founders, hiring managers",
                "business_objective": "Generate hiring strategy consultation inquiries",
                "expected_engagement_rate": 0.07,
                "expected_consultation_inquiries": 2
            },
            {
                "post_id": "2025-01-23-thursday-python-teams",
                "content_file": "/Users/bogdan/til/graph-rag-mcp/content/2025/Q1_Foundation_Strategy/Week_03_Team_Building_Culture/final/Thursday_Python_Team_Structure_FINAL.md",
                "posted_at": "2025-01-23T06:30:00",  # Optimal timing
                "week_theme": "Team Building and Culture",
                "day": "Thursday",
                "target_audience": "Python developers, team leads",
                "business_objective": "Technical team organization consultation",
                "expected_engagement_rate": 0.09,  # 6:30 AM boost
                "expected_consultation_inquiries": 1
            },
            {
                "post_id": "2025-01-24-friday-leadership",
                "content_file": "/Users/bogdan/til/graph-rag-mcp/content/2025/Q1_Foundation_Strategy/Week_03_Team_Building_Culture/final/Friday_Leadership_Mentorship_FINAL.md",
                "posted_at": "2025-01-24T08:30:00",
                "week_theme": "Team Building and Culture",
                "day": "Friday",
                "target_audience": "Senior developers, aspiring leaders",
                "business_objective": "Leadership coaching consultation inquiries",
                "expected_engagement_rate": 0.07,
                "expected_consultation_inquiries": 1
            },
            {
                "post_id": "2025-01-25-saturday-automation",
                "content_file": "/Users/bogdan/til/graph-rag-mcp/content/2025/Q1_Foundation_Strategy/Week_03_Team_Building_Culture/final/Saturday_Team_Automation_FINAL.md",
                "posted_at": "2025-01-25T10:00:00",
                "week_theme": "Team Building and Culture",
                "day": "Saturday",
                "target_audience": "Technical teams, productivity enthusiasts",
                "business_objective": "Team productivity consultation",
                "expected_engagement_rate": 0.06,
                "expected_consultation_inquiries": 1
            },
            {
                "post_id": "2025-01-26-sunday-empathy",
                "content_file": "/Users/bogdan/til/graph-rag-mcp/content/2025/Q1_Foundation_Strategy/Week_03_Team_Building_Culture/final/Sunday_Technical_Empathy_FINAL.md",
                "posted_at": "2025-01-26T18:00:00",
                "week_theme": "Team Building and Culture",
                "day": "Sunday",
                "target_audience": "Technical leaders, empathetic engineers",
                "business_objective": "Leadership development authority",
                "expected_engagement_rate": 0.07,
                "expected_consultation_inquiries": 1
            }
        ]

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        for post_data in week3_posts:
            # Read content from file
            try:
                with open(post_data["content_file"]) as f:
                    content = f.read()

                post_data["content"] = content

                # Insert into database
                cursor.execute('''
                    INSERT OR REPLACE INTO linkedin_posts 
                    (post_id, content, posted_at, week_theme, day, target_audience, 
                     business_objective, expected_engagement_rate, expected_consultation_inquiries)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    post_data["post_id"], content, post_data["posted_at"],
                    post_data["week_theme"], post_data["day"], post_data["target_audience"],
                    post_data["business_objective"], post_data["expected_engagement_rate"],
                    post_data["expected_consultation_inquiries"]
                ))

                logger.info(f"Scheduled {post_data['day']} post: {post_data['post_id']}")

            except FileNotFoundError:
                logger.warning(f"Content file not found: {post_data['content_file']}")
                continue

        conn.commit()
        conn.close()
        logger.info("Week 3 posts scheduled successfully")

    def update_post_performance(self, post_id: str, metrics: dict[str, Any]):
        """Update real performance metrics for a post"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Calculate engagement rate
        if 'impressions' in metrics and metrics['impressions'] > 0:
            total_engagement = (
                metrics.get('likes', 0) +
                metrics.get('comments', 0) +
                metrics.get('shares', 0) +
                metrics.get('saves', 0)
            )
            metrics['actual_engagement_rate'] = total_engagement / metrics['impressions']

        # Calculate business conversion rate
        if 'views' in metrics and metrics['views'] > 0:
            business_actions = (
                metrics.get('profile_views', 0) +
                metrics.get('connection_requests', 0) +
                metrics.get('dm_inquiries', 0)
            )
            metrics['business_conversion_rate'] = business_actions / metrics['views']

        # Build UPDATE query dynamically
        set_clauses = []
        values = []
        for key, value in metrics.items():
            if key != 'post_id':
                set_clauses.append(f"{key} = ?")
                values.append(value)

        if set_clauses:
            set_clauses.append("updated_at = CURRENT_TIMESTAMP")
            query = f"UPDATE linkedin_posts SET {', '.join(set_clauses)} WHERE post_id = ?"
            values.append(post_id)
            cursor.execute(query, values)
            conn.commit()
            logger.info(f"Updated metrics for post {post_id}")

        conn.close()

    def log_consultation_inquiry(self, inquiry: ConsultationInquiry):
        """Log a new consultation inquiry"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            INSERT OR REPLACE INTO consultation_inquiries 
            (inquiry_id, source_post_id, contact_name, company, company_size,
             inquiry_type, inquiry_channel, inquiry_text, estimated_value,
             priority_score, status, created_at, last_contact, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            inquiry.inquiry_id, inquiry.source_post_id, inquiry.contact_name,
            inquiry.company, inquiry.company_size, inquiry.inquiry_type,
            inquiry.inquiry_channel, inquiry.inquiry_text, inquiry.estimated_value,
            inquiry.priority_score, inquiry.status, inquiry.created_at,
            inquiry.last_contact, inquiry.notes
        ))

        # Update post consultation count
        cursor.execute('''
            UPDATE linkedin_posts 
            SET consultation_requests = consultation_requests + 1
            WHERE post_id = ?
        ''', (inquiry.source_post_id,))

        conn.commit()
        conn.close()
        logger.info(f"Logged consultation inquiry: {inquiry.inquiry_id}")

    def get_post_for_publishing(self, day: str = None) -> dict | None:
        """Get next post ready for publishing"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        query = '''
            SELECT * FROM linkedin_posts 
            WHERE impressions = 0  -- Not yet posted
        '''
        params = []

        if day:
            query += ' AND day = ?'
            params.append(day)

        query += ' ORDER BY posted_at LIMIT 1'

        cursor.execute(query, params)
        result = cursor.fetchone()

        if result:
            columns = [description[0] for description in cursor.description]
            post_dict = dict(zip(columns, result, strict=False))
            conn.close()
            return post_dict

        conn.close()
        return None

    def generate_business_development_report(self) -> dict:
        """Generate comprehensive business development report"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Get post performance summary
        cursor.execute('''
            SELECT 
                COUNT(*) as total_posts,
                AVG(actual_engagement_rate) as avg_engagement_rate,
                SUM(impressions) as total_impressions,
                SUM(likes + comments + shares + saves) as total_engagement,
                SUM(consultation_requests) as total_consultation_requests,
                SUM(profile_views) as total_profile_views,
                SUM(connection_requests) as total_connection_requests
            FROM linkedin_posts 
            WHERE impressions > 0
        ''')
        post_summary = cursor.fetchone()

        # Get consultation inquiries summary
        cursor.execute('''
            SELECT 
                COUNT(*) as total_inquiries,
                COUNT(CASE WHEN status = 'discovery_scheduled' THEN 1 END) as discovery_calls,
                COUNT(CASE WHEN status = 'proposal_sent' THEN 1 END) as proposals_sent,
                COUNT(CASE WHEN status = 'closed_won' THEN 1 END) as contracts_won,
                SUM(estimated_value) as total_pipeline_value,
                SUM(CASE WHEN status = 'closed_won' THEN estimated_value ELSE 0 END) as won_value
            FROM consultation_inquiries
        ''')
        inquiry_summary = cursor.fetchone()

        # Get top performing posts
        cursor.execute('''
            SELECT post_id, day, actual_engagement_rate, consultation_requests
            FROM linkedin_posts 
            WHERE impressions > 0
            ORDER BY consultation_requests DESC, actual_engagement_rate DESC
            LIMIT 5
        ''')
        top_posts = cursor.fetchall()

        conn.close()

        report = {
            'post_performance': {
                'total_posts': post_summary[0] if post_summary and post_summary[0] is not None else 0,
                'avg_engagement_rate': post_summary[1] if post_summary and post_summary[1] is not None else 0,
                'total_impressions': post_summary[2] if post_summary and post_summary[2] is not None else 0,
                'total_engagement': post_summary[3] if post_summary and post_summary[3] is not None else 0,
                'total_consultation_requests': post_summary[4] if post_summary and post_summary[4] is not None else 0,
                'total_profile_views': post_summary[5] if post_summary and post_summary[5] is not None else 0,
                'total_connection_requests': post_summary[6] if post_summary and post_summary[6] is not None else 0
            },
            'business_pipeline': {
                'total_inquiries': inquiry_summary[0] if inquiry_summary and inquiry_summary[0] is not None else 0,
                'discovery_calls': inquiry_summary[1] if inquiry_summary and inquiry_summary[1] is not None else 0,
                'proposals_sent': inquiry_summary[2] if inquiry_summary and inquiry_summary[2] is not None else 0,
                'contracts_won': inquiry_summary[3] if inquiry_summary and inquiry_summary[3] is not None else 0,
                'total_pipeline_value': inquiry_summary[4] if inquiry_summary and inquiry_summary[4] is not None else 0,
                'won_value': inquiry_summary[5] if inquiry_summary and inquiry_summary[5] is not None else 0
            },
            'top_performing_posts': [
                {
                    'post_id': post[0],
                    'day': post[1],
                    'engagement_rate': post[2],
                    'consultation_requests': post[3]
                } for post in top_posts
            ]
        }

        return report

def main():
    """Initialize and demonstrate the business development system"""
    engine = LinkedInBusinessDevelopmentEngine()

    # Schedule Week 3 posts
    print("🚀 Scheduling Week 3 Team Building posts...")
    engine.schedule_week3_posts()

    # Get Monday post for immediate publishing
    monday_post = engine.get_post_for_publishing("Monday")
    if monday_post:
        print(f"\n📝 Ready to post: {monday_post['day']} - {monday_post['business_objective']}")
        print(f"Expected engagement: {monday_post['expected_engagement_rate']*100:.1f}%")
        print(f"Expected consultations: {monday_post['expected_consultation_inquiries']}")

    # Log a sample consultation inquiry
    sample_inquiry = ConsultationInquiry(
        inquiry_id=f"inquiry-{datetime.now().strftime('%Y%m%d%H%M%S')}",
        source_post_id="2025-01-20-monday-10x-teams",
        contact_name="John Smith",
        company="TechStartup Inc",
        company_size="Series A (20-50 employees)",
        inquiry_type="team_building",
        inquiry_channel="linkedin_comment",
        inquiry_text="Great post! We're struggling with team velocity. Would love to discuss your approach.",
        estimated_value=25000,
        priority_score=4,
        status="new",
        created_at=datetime.now().isoformat()
    )

    engine.log_consultation_inquiry(sample_inquiry)
    print(f"\n💼 Logged sample consultation inquiry: {sample_inquiry.inquiry_id}")

    # Generate business development report
    report = engine.generate_business_development_report()
    print("\n📊 Business Development Summary:")
    print(f"Total consultation inquiries: {report['business_pipeline']['total_inquiries']}")
    print(f"Pipeline value: ${report['business_pipeline']['total_pipeline_value']:,}")

    print("\n✅ LinkedIn Business Development System ready!")
    print(f"Database: {engine.db_path}")
    print("Ready for Week 3 content posting and real-time business development tracking.")

if __name__ == "__main__":
    main()
