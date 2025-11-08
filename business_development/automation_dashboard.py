#!/usr/bin/env python3
"""
Automation Dashboard and Control Center
Monitor and control all business development automation systems
"""

import logging
import sqlite3
import sys
from datetime import datetime

try:
    from .consultation_inquiry_detector import ConsultationInquiryDetector
    from .content_scheduler import ContentAutomationPipeline
    from .content_templates import ContentType, LinkedInContentGenerator
    from .linkedin_api_client import LinkedInAPIClient
    from .linkedin_posting_system import LinkedInBusinessDevelopmentEngine
except ImportError:
    # For standalone execution
    import os
    sys.path.append(os.path.dirname(__file__))
    from consultation_inquiry_detector import ConsultationInquiryDetector
    from content_scheduler import ContentAutomationPipeline
    from content_templates import ContentType, LinkedInContentGenerator
    from linkedin_api_client import LinkedInAPIClient
    from linkedin_posting_system import LinkedInBusinessDevelopmentEngine

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class AutomationDashboard:
    """Central dashboard for monitoring all automation systems"""

    def __init__(self):
        self.business_engine = LinkedInBusinessDevelopmentEngine()
        self.inquiry_detector = ConsultationInquiryDetector()
        self.api_client = LinkedInAPIClient()
        self.automation_pipeline = ContentAutomationPipeline()
        self.content_generator = LinkedInContentGenerator()

    def get_comprehensive_status(self) -> dict:
        """Get comprehensive status of all systems"""
        # Business development metrics
        bd_report = self.business_engine.generate_business_development_report()

        # Pending inquiries
        pending_inquiries = self.inquiry_detector.get_pending_inquiries()

        # Automation status
        automation_status = self.automation_pipeline.get_automation_status()

        # Content pipeline status
        conn = sqlite3.connect(self.business_engine.db_path)
        cursor = conn.cursor()

        # Get posts by status
        cursor.execute('''
            SELECT 
                day,
                CASE 
                    WHEN impressions = 0 THEN 'scheduled'
                    WHEN impressions > 0 AND consultation_requests = 0 THEN 'posted_no_inquiries'
                    WHEN consultation_requests > 0 THEN 'posted_with_inquiries'
                END as status,
                expected_consultation_inquiries,
                consultation_requests,
                actual_engagement_rate,
                business_objective
            FROM linkedin_posts
            ORDER BY posted_at
        ''')

        posts_status = []
        for row in cursor.fetchall():
            posts_status.append({
                'day': row[0],
                'status': row[1],
                'expected_inquiries': row[2],
                'actual_inquiries': row[3],
                'engagement_rate': row[4],
                'objective': row[5]
            })

        # Recent performance trends
        cursor.execute('''
            SELECT 
                DATE(posted_at) as post_date,
                AVG(actual_engagement_rate) as avg_engagement,
                SUM(consultation_requests) as daily_inquiries
            FROM linkedin_posts 
            WHERE impressions > 0 
            AND posted_at >= date('now', '-7 days')
            GROUP BY DATE(posted_at)
            ORDER BY post_date DESC
        ''')

        recent_trends = []
        for row in cursor.fetchall():
            recent_trends.append({
                'date': row[0],
                'engagement_rate': row[1] or 0,
                'inquiries': row[2] or 0
            })

        conn.close()

        return {
            'timestamp': datetime.now().isoformat(),
            'systems_status': {
                'linkedin_api': self.api_client.api_available,
                'automation_pipeline': automation_status['automation_active'],
                'inquiry_detection': True,
                'business_tracking': True
            },
            'business_metrics': bd_report,
            'pending_inquiries': {
                'count': len(pending_inquiries),
                'total_value': sum(inq.get('estimated_value', 0) or 0 for inq in pending_inquiries),
                'high_priority': len([inq for inq in pending_inquiries if (inq.get('priority_score', 0) or 0) >= 4])
            },
            'content_pipeline': {
                'total_posts': len(posts_status),
                'scheduled': len([p for p in posts_status if p['status'] == 'scheduled']),
                'posted_no_inquiries': len([p for p in posts_status if p['status'] == 'posted_no_inquiries']),
                'posted_with_inquiries': len([p for p in posts_status if p['status'] == 'posted_with_inquiries'])
            },
            'automation_status': automation_status,
            'recent_trends': recent_trends,
            'posts_detail': posts_status
        }

    def generate_daily_report(self) -> str:
        """Generate daily performance report"""
        status = self.get_comprehensive_status()

        report = []
        report.append("🚀 DAILY BUSINESS DEVELOPMENT REPORT")
        report.append("=" * 60)
        report.append(f"📅 Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append("")

        # System Health
        report.append("🔧 SYSTEM STATUS:")
        systems = status['systems_status']
        for system, active in systems.items():
            status_icon = "✅" if active else "❌"
            report.append(f"  {status_icon} {system.replace('_', ' ').title()}: {'Active' if active else 'Inactive'}")
        report.append("")

        # Key Metrics
        metrics = status['business_metrics']
        report.append("📊 KEY METRICS:")
        report.append(f"  • Total Posts Published: {metrics['post_performance']['total_posts']}")
        report.append(f"  • Average Engagement Rate: {metrics['post_performance']['avg_engagement_rate']*100:.2f}%")
        report.append(f"  • Total Consultation Requests: {metrics['post_performance']['total_consultation_requests']}")
        report.append(f"  • Pipeline Value: ${metrics['business_pipeline']['total_pipeline_value']:,}")
        report.append(f"  • Revenue Generated: ${metrics['business_pipeline']['won_value']:,}")
        report.append("")

        # Content Pipeline Status
        pipeline = status['content_pipeline']
        report.append("📝 CONTENT PIPELINE:")
        report.append(f"  • Scheduled Posts: {pipeline['scheduled']}")
        report.append(f"  • Posted (No Inquiries): {pipeline['posted_no_inquiries']}")
        report.append(f"  • Posted (With Inquiries): {pipeline['posted_with_inquiries']}")
        report.append("")

        # Pending Business Development
        pending = status['pending_inquiries']
        report.append("💼 PENDING BUSINESS DEVELOPMENT:")
        report.append(f"  • Total Inquiries: {pending['count']}")
        report.append(f"  • High Priority: {pending['high_priority']}")
        report.append(f"  • Pipeline Value: ${pending['total_value']:,}")
        report.append("")

        # Recent Trends
        if status['recent_trends']:
            report.append("📈 RECENT TRENDS (Last 7 Days):")
            for trend in status['recent_trends'][:5]:  # Last 5 days
                report.append(f"  • {trend['date']}: {trend['engagement_rate']*100:.1f}% engagement, {trend['inquiries']} inquiries")
            report.append("")

        # Action Items
        report.append("⚡ ACTION ITEMS:")
        action_items = self._generate_action_items(status)
        for item in action_items:
            report.append(f"  • {item}")

        report.append("")
        report.append("🎯 Focus: Working software delivering business value through systematic content strategy execution")

        return "\n".join(report)

    def _generate_action_items(self, status: dict) -> list[str]:
        """Generate actionable recommendations based on current status"""
        action_items = []

        # Check for high-priority pending inquiries
        if status['pending_inquiries']['high_priority'] > 0:
            action_items.append(f"URGENT: Follow up on {status['pending_inquiries']['high_priority']} high-priority consultation inquiries")

        # Check for scheduled posts
        if status['content_pipeline']['scheduled'] > 0:
            action_items.append(f"Publish {status['content_pipeline']['scheduled']} scheduled posts")

        # Check engagement rates
        avg_engagement = status['business_metrics']['post_performance']['avg_engagement_rate']
        if avg_engagement < 0.06:  # Below 6%
            action_items.append("Engagement below target (6%) - optimize posting times and content hooks")

        # Check for posts without inquiries
        no_inquiries = status['content_pipeline']['posted_no_inquiries']
        if no_inquiries > 2:
            action_items.append(f"{no_inquiries} posts published without consultation inquiries - analyze and optimize CTAs")

        # LinkedIn API status
        if not status['systems_status']['linkedin_api']:
            action_items.append("LinkedIn API not configured - set up automated posting for better timing")

        # Recent trends analysis
        if status['recent_trends']:
            last_3_days = status['recent_trends'][:3]
            avg_recent_engagement = sum(t['engagement_rate'] for t in last_3_days) / len(last_3_days)
            if avg_recent_engagement < 0.05:
                action_items.append("Engagement declining - review content strategy and posting times")

        # Business development pipeline
        pipeline_value = status['business_metrics']['business_pipeline']['total_pipeline_value']
        if pipeline_value < 50000:  # Below $50K target
            action_items.append(f"Pipeline value ${pipeline_value:,} below $50K target - increase consultation-focused content")

        return action_items

    def save_daily_report(self, filename: str = None):
        """Save daily report to file"""
        if filename is None:
            filename = f"daily_report_{datetime.now().strftime('%Y%m%d')}.txt"

        report = self.generate_daily_report()

        with open(filename, 'w') as f:
            f.write(report)

        logger.info(f"Daily report saved: {filename}")
        return filename

    def monitor_critical_alerts(self) -> list[str]:
        """Monitor for critical alerts that need immediate attention"""
        alerts = []

        # Check for high-priority inquiries over 24 hours old
        pending_inquiries = self.inquiry_detector.get_pending_inquiries(priority_threshold=4)

        for inquiry in pending_inquiries:
            created_at = datetime.fromisoformat(inquiry['created_at'])
            hours_old = (datetime.now() - created_at).total_seconds() / 3600

            if hours_old > 24:
                alerts.append(f"CRITICAL: High-priority inquiry from {inquiry['contact_name']} pending {hours_old:.1f} hours")

        # Check for posting failures
        conn = sqlite3.connect(self.business_engine.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            SELECT post_id, day FROM linkedin_posts 
            WHERE posted_at < datetime('now', '-1 day')
            AND impressions = 0
        ''')

        failed_posts = cursor.fetchall()
        if failed_posts:
            alerts.append(f"CRITICAL: {len(failed_posts)} posts failed to publish")

        # Check engagement rates
        cursor.execute('''
            SELECT AVG(actual_engagement_rate) FROM linkedin_posts 
            WHERE posted_at >= datetime('now', '-3 days')
            AND impressions > 0
        ''')

        result = cursor.fetchone()
        if result and result[0] and result[0] < 0.03:  # Below 3%
            alerts.append(f"WARNING: Engagement rate critically low ({result[0]*100:.1f}%)")

        conn.close()

        return alerts

    def interactive_dashboard(self):
        """Interactive dashboard interface"""
        while True:
            print("\n🚀 AUTOMATION DASHBOARD & CONTROL CENTER")
            print("=" * 50)

            # Show critical alerts first
            alerts = self.monitor_critical_alerts()
            if alerts:
                print("🚨 CRITICAL ALERTS:")
                for alert in alerts:
                    print(f"  {alert}")
                print()

            print("📊 Dashboard Options:")
            print("1. View comprehensive status")
            print("2. Generate daily report")
            print("3. Monitor pending inquiries")
            print("4. Check content pipeline")
            print("5. System health check")
            print("6. Save daily report")
            print("7. Generate AI content")
            print("8. Content generation pipeline")
            print("9. Exit")

            choice = input("\nSelect option (1-9): ").strip()

            if choice == '1':
                status = self.get_comprehensive_status()
                self._display_comprehensive_status(status)

            elif choice == '2':
                report = self.generate_daily_report()
                print("\n" + report)

            elif choice == '3':
                pending = self.inquiry_detector.get_pending_inquiries()
                self._display_pending_inquiries(pending)

            elif choice == '4':
                self._display_content_pipeline_status()

            elif choice == '5':
                self._display_system_health()

            elif choice == '6':
                filename = self.save_daily_report()
                print(f"✅ Daily report saved: {filename}")

            elif choice == '7':
                self._ai_content_generation_menu()

            elif choice == '8':
                self._content_pipeline_menu()

            elif choice == '9':
                print("👋 Dashboard closed!")
                break

            else:
                print("Invalid choice. Please select 1-9.")

    def _display_comprehensive_status(self, status: dict):
        """Display comprehensive status information"""
        print("\n📊 COMPREHENSIVE STATUS REPORT")
        print("=" * 50)

        # Systems status
        print("🔧 SYSTEMS:")
        for system, active in status['systems_status'].items():
            icon = "✅" if active else "❌"
            print(f"  {icon} {system.replace('_', ' ').title()}")

        # Key metrics
        metrics = status['business_metrics']
        print("\n📈 PERFORMANCE:")
        print(f"  • Posts: {metrics['post_performance']['total_posts']}")

        # Handle None values for engagement rate
        avg_engagement = metrics['post_performance']['avg_engagement_rate']
        if avg_engagement is not None:
            print(f"  • Avg Engagement: {avg_engagement*100:.2f}%")
        else:
            print("  • Avg Engagement: N/A")

        print(f"  • Consultations: {metrics['post_performance']['total_consultation_requests']}")
        print(f"  • Pipeline: ${metrics['business_pipeline']['total_pipeline_value']:,}")

        # Pending business development
        print("\n💼 PENDING BUSINESS DEV:")
        print(f"  • Inquiries: {status['pending_inquiries']['count']}")
        print(f"  • High Priority: {status['pending_inquiries']['high_priority']}")
        print(f"  • Value: ${status['pending_inquiries']['total_value']:,}")

    def _display_pending_inquiries(self, inquiries: list[dict]):
        """Display pending consultation inquiries"""
        print(f"\n💼 PENDING CONSULTATION INQUIRIES ({len(inquiries)})")
        print("=" * 60)

        if not inquiries:
            print("No pending inquiries")
            return

        for inquiry in inquiries:
            priority_icon = "🔥" if inquiry['priority_score'] >= 4 else "📋"
            print(f"{priority_icon} {inquiry['contact_name']} - {inquiry['company']}")
            print(f"   Type: {inquiry['inquiry_type']} | Value: ${inquiry['estimated_value']:,}")
            print(f"   Channel: {inquiry['inquiry_channel']} | Priority: {inquiry['priority_score']}")
            print(f"   Created: {inquiry['created_at']}")
            print()

    def _display_content_pipeline_status(self):
        """Display content pipeline status"""
        status = self.get_comprehensive_status()
        posts = status['posts_detail']

        print(f"\n📝 CONTENT PIPELINE STATUS ({len(posts)} total posts)")
        print("=" * 60)

        for post in posts:
            status_icon = {
                'scheduled': "⏰",
                'posted_no_inquiries': "📤",
                'posted_with_inquiries': "💼"
            }.get(post['status'], "❓")

            print(f"{status_icon} {post['day']}: {post['objective']}")

            if post['status'] != 'scheduled':
                print(f"   Engagement: {post['engagement_rate']*100:.1f}% | Inquiries: {post['actual_inquiries']}/{post['expected_inquiries']}")

            print()

    def _display_system_health(self):
        """Display system health information"""
        print("\n🔧 SYSTEM HEALTH CHECK")
        print("=" * 40)

        # Check all system components
        systems = {
            'LinkedIn API': self.api_client.api_available,
            'Business Database': self._check_database_health(),
            'Content Pipeline': True,  # Always available
            'Inquiry Detection': True,  # Always available
            'Automation Scheduler': self.automation_pipeline.get_automation_status()['automation_active']
        }

        for system, healthy in systems.items():
            icon = "✅" if healthy else "❌"
            status = "Healthy" if healthy else "Needs Attention"
            print(f"  {icon} {system}: {status}")

        print("\n💡 System Recommendations:")
        if not systems['LinkedIn API']:
            print("  • Set up LinkedIn API for automated posting")
        if not systems['Automation Scheduler']:
            print("  • Start automation scheduler for optimal timing")

    def _check_database_health(self) -> bool:
        """Check database health"""
        try:
            conn = sqlite3.connect(self.business_engine.db_path)
            cursor = conn.cursor()
            cursor.execute('SELECT COUNT(*) FROM linkedin_posts')
            conn.close()
            return True
        except Exception:
            return False

    def _ai_content_generation_menu(self):
        """AI Content Generation Menu"""
        while True:
            print("\n🤖 AI CONTENT GENERATION")
            print("=" * 40)
            print("Generate LinkedIn content using Synapse AI enrichment")
            print()

            print("Content Types:")
            print("1. Controversial Take (High engagement)")
            print("2. Personal Story (Authentic)")
            print("3. Technical Insight (Authority)")
            print("4. Career Advice (Valuable)")
            print("5. Product Management (Business)")
            print("6. Startup Lessons (Community)")
            print("7. Generate multiple posts")
            print("8. Back to main menu")

            choice = input("\nSelect content type (1-8): ").strip()

            if choice in ['1', '2', '3', '4', '5', '6']:
                self._generate_single_content(choice)
            elif choice == '7':
                self._generate_content_batch()
            elif choice == '8':
                break
            else:
                print("Invalid choice. Please select 1-8.")

    def _generate_single_content(self, choice: str):
        """Generate single piece of content"""
        content_types = {
            '1': ContentType.CONTROVERSIAL_TAKE,
            '2': ContentType.PERSONAL_STORY,
            '3': ContentType.TECHNICAL_INSIGHT,
            '4': ContentType.CAREER_ADVICE,
            '5': ContentType.PRODUCT_MANAGEMENT,
            '6': ContentType.STARTUP_LESSONS
        }

        content_type = content_types[choice]

        print(f"\n🎯 Generating {content_type.value.replace('_', ' ').title()} Content")
        print("=" * 50)

        # Get topic from user
        topic = input("Enter topic/subject: ").strip()
        if not topic:
            print("❌ Topic is required")
            return

        # Get specific angle (optional)
        angle = input("Specific angle or take (optional): ").strip()
        if not angle:
            angle = None

        try:
            print("\n🔄 Generating content with Synapse AI enrichment...")

            generated = self.content_generator.generate_content(
                content_type=content_type,
                topic=topic,
                specific_angle=angle
            )

            print("\n✅ GENERATED CONTENT")
            print("=" * 50)
            print(generated.full_post)
            print("=" * 50)

            print("\n📊 Content Analysis:")
            print(f"• Content Type: {generated.content_type.value}")
            print(f"• Predicted Engagement: {generated.engagement_prediction:.1%}")
            print(f"• Synapse Confidence: {generated.enrichment_data.confidence_score:.1%}")
            print(f"• Content Length: {generated.generation_metadata['content_length']} chars")
            print(f"• Estimated Read Time: {generated.generation_metadata['estimated_read_time']:.1f} minutes")

            if generated.enrichment_data.relevant_beliefs:
                print(f"• Leveraged {len(generated.enrichment_data.relevant_beliefs)} core beliefs")
            if generated.enrichment_data.personal_stories:
                print(f"• Included {len(generated.enrichment_data.personal_stories)} personal stories")

            # Option to save to content pipeline
            save = input("\nSave to content pipeline? (y/n): ").strip().lower()
            if save == 'y':
                self._save_generated_content(generated, topic)

        except Exception as e:
            print(f"❌ Error generating content: {e}")
            logger.error(f"Content generation error: {e}")

    def _generate_content_batch(self):
        """Generate multiple pieces of content"""
        print("\n📝 BATCH CONTENT GENERATION")
        print("=" * 40)

        try:
            num_posts = int(input("Number of posts to generate (1-7): ").strip())
            if not 1 <= num_posts <= 7:
                print("❌ Number must be between 1 and 7")
                return
        except ValueError:
            print("❌ Invalid number")
            return

        base_topic = input("Base topic/theme: ").strip()
        if not base_topic:
            print("❌ Base topic is required")
            return

        print(f"\n🔄 Generating {num_posts} posts about '{base_topic}'...")

        # Define content mix for week
        content_mix = [
            (ContentType.CONTROVERSIAL_TAKE, f"{base_topic} misconceptions"),
            (ContentType.PERSONAL_STORY, f"My experience with {base_topic}"),
            (ContentType.TECHNICAL_INSIGHT, f"{base_topic} best practices"),
            (ContentType.CAREER_ADVICE, f"Growing in {base_topic}"),
            (ContentType.PRODUCT_MANAGEMENT, f"{base_topic} in product development"),
            (ContentType.STARTUP_LESSONS, f"{base_topic} for startups"),
            (ContentType.PERSONAL_STORY, f"Lessons learned from {base_topic}")
        ]

        generated_posts = []

        for i in range(num_posts):
            content_type, topic = content_mix[i]

            try:
                generated = self.content_generator.generate_content(
                    content_type=content_type,
                    topic=topic
                )
                generated_posts.append(generated)
                print(f"✅ Generated {content_type.value} post")

            except Exception as e:
                print(f"❌ Error generating post {i+1}: {e}")

        # Display all generated content
        print(f"\n📋 GENERATED {len(generated_posts)} POSTS")
        print("=" * 60)

        for i, post in enumerate(generated_posts, 1):
            print(f"\n📝 POST {i}: {post.content_type.value.replace('_', ' ').title()}")
            print("-" * 40)
            print(post.full_post)
            print(f"\nPredicted Engagement: {post.engagement_prediction:.1%}")
            print("-" * 40)

        # Option to save all to pipeline
        save_all = input(f"\nSave all {len(generated_posts)} posts to content pipeline? (y/n): ").strip().lower()
        if save_all == 'y':
            for i, post in enumerate(generated_posts, 1):
                self._save_generated_content(post, f"{base_topic} - Post {i}")
            print(f"✅ Saved {len(generated_posts)} posts to content pipeline")

    def _save_generated_content(self, generated_content, topic_description: str):
        """Save generated content to the business development pipeline"""
        try:
            # Create a post entry in the database
            conn = sqlite3.connect(self.business_engine.db_path)
            cursor = conn.cursor()

            # Generate post ID
            post_id = f"ai-generated-{datetime.now().strftime('%Y%m%d-%H%M%S')}"

            # Determine business objective based on content type
            objectives = {
                ContentType.CONTROVERSIAL_TAKE: "Drive engagement and thought leadership",
                ContentType.PERSONAL_STORY: "Build authentic connection and relatability",
                ContentType.TECHNICAL_INSIGHT: "Demonstrate expertise and authority",
                ContentType.CAREER_ADVICE: "Provide value and establish advisory positioning",
                ContentType.PRODUCT_MANAGEMENT: "Generate consultation inquiries",
                ContentType.STARTUP_LESSONS: "Engage startup community and attract clients"
            }

            objective = objectives.get(generated_content.content_type, "Build engagement and authority")

            # Insert into linkedin_posts table
            cursor.execute('''
                INSERT INTO linkedin_posts (
                    post_id, day, content, business_objective, 
                    expected_consultation_inquiries, posted_at,
                    impressions, consultation_requests, actual_engagement_rate
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                post_id,
                "AI Generated",
                generated_content.full_post,
                objective,
                1 if generated_content.content_type in [ContentType.PRODUCT_MANAGEMENT, ContentType.STARTUP_LESSONS] else 0,
                datetime.now().isoformat(),
                0,  # Not posted yet
                0,  # No consultation requests yet
                0   # No engagement yet
            ))

            conn.commit()
            conn.close()

            print(f"✅ Content saved with ID: {post_id}")

        except Exception as e:
            print(f"❌ Error saving content: {e}")
            logger.error(f"Error saving generated content: {e}")

    def _content_pipeline_menu(self):
        """Content Pipeline Management Menu"""
        while True:
            print("\n📋 CONTENT PIPELINE MANAGEMENT")
            print("=" * 45)

            # Get pipeline stats
            conn = sqlite3.connect(self.business_engine.db_path)
            cursor = conn.cursor()

            cursor.execute("SELECT COUNT(*) FROM linkedin_posts WHERE impressions = 0")
            pending_count = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM linkedin_posts WHERE post_id LIKE 'ai-generated-%'")
            ai_generated_count = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM linkedin_posts WHERE impressions > 0")
            published_count = cursor.fetchone()[0]

            conn.close()

            print("📊 Pipeline Status:")
            print(f"• Pending Posts: {pending_count}")
            print(f"• AI Generated: {ai_generated_count}")
            print(f"• Published Posts: {published_count}")
            print()

            print("Pipeline Options:")
            print("1. View pending posts")
            print("2. View AI generated posts")
            print("3. Schedule posts for publication")
            print("4. Generate weekly content plan")
            print("5. Content performance analysis")
            print("6. Back to main menu")

            choice = input("\nSelect option (1-6): ").strip()

            if choice == '1':
                self._view_pending_posts()
            elif choice == '2':
                self._view_ai_generated_posts()
            elif choice == '3':
                self._schedule_posts_for_publication()
            elif choice == '4':
                self._generate_weekly_content_plan()
            elif choice == '5':
                self._analyze_content_performance()
            elif choice == '6':
                break
            else:
                print("Invalid choice. Please select 1-6.")

    def _view_pending_posts(self):
        """View all pending posts"""
        conn = sqlite3.connect(self.business_engine.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            SELECT post_id, day, business_objective, 
                   substr(content, 1, 100) as preview
            FROM linkedin_posts 
            WHERE impressions = 0
            ORDER BY posted_at DESC
        ''')

        posts = cursor.fetchall()
        conn.close()

        print(f"\n📝 PENDING POSTS ({len(posts)})")
        print("=" * 60)

        if not posts:
            print("No pending posts")
            return

        for post_id, day, objective, preview in posts:
            print(f"\n🆔 {post_id}")
            print(f"📅 {day}")
            print(f"🎯 {objective}")
            print(f"📄 {preview}...")
            print("-" * 40)

    def _view_ai_generated_posts(self):
        """View AI generated posts"""
        conn = sqlite3.connect(self.business_engine.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            SELECT post_id, business_objective, posted_at,
                   substr(content, 1, 150) as preview
            FROM linkedin_posts 
            WHERE post_id LIKE 'ai-generated-%'
            ORDER BY posted_at DESC
        ''')

        posts = cursor.fetchall()
        conn.close()

        print(f"\n🤖 AI GENERATED POSTS ({len(posts)})")
        print("=" * 60)

        for post_id, objective, created_at, preview in posts:
            print(f"\n🆔 {post_id}")
            print(f"⏰ Generated: {created_at}")
            print(f"🎯 {objective}")
            print(f"📄 {preview}...")
            print("-" * 40)

    def _schedule_posts_for_publication(self):
        """Schedule pending posts for publication"""
        print("\n⏰ SCHEDULE POSTS FOR PUBLICATION")
        print("=" * 45)

        # Get pending posts
        conn = sqlite3.connect(self.business_engine.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            SELECT post_id, substr(content, 1, 60) as preview
            FROM linkedin_posts 
            WHERE impressions = 0
            ORDER BY posted_at DESC
            LIMIT 7
        ''')

        posts = cursor.fetchall()

        if not posts:
            print("No pending posts to schedule")
            return

        print(f"📋 Available posts ({len(posts)}):")
        for i, (post_id, preview) in enumerate(posts, 1):
            print(f"{i}. {post_id}: {preview}...")

        print("\n📅 Optimal posting schedule:")
        print("• Tuesday 6:30 AM (Peak engagement)")
        print("• Thursday 6:30 AM (Peak engagement)")
        print("• Monday 7:00 AM")
        print("• Wednesday 8:00 AM")
        print("• Friday 8:30 AM")

        schedule_now = input("\nSchedule these posts with automation system? (y/n): ").strip().lower()
        if schedule_now == 'y':
            try:
                scheduled_count = self.automation_pipeline.schedule_week_content(4)  # Week 4
                print(f"✅ Scheduled {scheduled_count} posts for optimal timing")
            except Exception as e:
                print(f"❌ Error scheduling posts: {e}")

        conn.close()

    def _generate_weekly_content_plan(self):
        """Generate a complete weekly content plan"""
        print("\n📅 WEEKLY CONTENT PLAN GENERATOR")
        print("=" * 45)

        theme = input("Weekly theme/focus: ").strip()
        if not theme:
            print("❌ Theme is required")
            return

        print(f"\n🔄 Generating weekly content plan for '{theme}'...")

        # Define optimal content for each day
        weekly_plan = [
            ('Monday', ContentType.CAREER_ADVICE, f"Starting the week: {theme} career tips"),
            ('Tuesday', ContentType.TECHNICAL_INSIGHT, f"Technical deep dive: {theme}"),
            ('Wednesday', ContentType.PERSONAL_STORY, f"My journey with {theme}"),
            ('Thursday', ContentType.CONTROVERSIAL_TAKE, f"Unpopular opinion about {theme}"),
            ('Friday', ContentType.STARTUP_LESSONS, f"{theme} lessons for entrepreneurs"),
            ('Saturday', ContentType.PRODUCT_MANAGEMENT, f"{theme} in product development"),
            ('Sunday', ContentType.PERSONAL_STORY, f"Weekend reflection on {theme}")
        ]

        generated_plan = []

        for day, content_type, topic in weekly_plan:
            try:
                generated = self.content_generator.generate_content(
                    content_type=content_type,
                    topic=topic
                )
                # Optimize for the specific day
                optimized = self.content_generator.optimize_for_timing(generated, day)
                generated_plan.append((day, optimized))
                print(f"✅ Generated {day} content")

            except Exception as e:
                print(f"❌ Error generating {day} content: {e}")

        # Display the complete plan
        print(f"\n📋 COMPLETE WEEKLY PLAN: {theme.upper()}")
        print("=" * 60)

        for day, content in generated_plan:
            print(f"\n📅 {day.upper()}")
            print(f"📝 Type: {content.content_type.value.replace('_', ' ').title()}")
            print(f"📊 Predicted Engagement: {content.engagement_prediction:.1%}")
            print(f"📄 Preview: {content.full_post[:100]}...")
            print("-" * 40)

        # Save entire plan
        save_plan = input(f"\nSave complete weekly plan ({len(generated_plan)} posts) to pipeline? (y/n): ").strip().lower()
        if save_plan == 'y':
            for day, content in generated_plan:
                self._save_generated_content(content, f"{theme} - {day}")
            print("✅ Saved complete weekly plan to content pipeline")

    def _analyze_content_performance(self):
        """Analyze content performance and patterns"""
        print("\n📈 CONTENT PERFORMANCE ANALYSIS")
        print("=" * 45)

        conn = sqlite3.connect(self.business_engine.db_path)
        cursor = conn.cursor()

        # Get performance metrics
        cursor.execute('''
            SELECT 
                AVG(actual_engagement_rate) as avg_engagement,
                COUNT(*) as total_posts,
                SUM(consultation_requests) as total_inquiries,
                COUNT(CASE WHEN post_id LIKE 'ai-generated-%' THEN 1 END) as ai_posts
            FROM linkedin_posts 
            WHERE impressions > 0
        ''')

        metrics = cursor.fetchone()
        avg_engagement, total_posts, total_inquiries, ai_posts = metrics

        print("📊 Overall Performance:")
        print(f"• Total Published Posts: {total_posts or 0}")
        print(f"• AI Generated Posts: {ai_posts or 0}")
        print(f"• Average Engagement Rate: {(avg_engagement or 0)*100:.2f}%")
        print(f"• Total Consultation Inquiries: {total_inquiries or 0}")

        # Get top performing posts
        cursor.execute('''
            SELECT post_id, actual_engagement_rate, consultation_requests
            FROM linkedin_posts 
            WHERE impressions > 0 
            ORDER BY actual_engagement_rate DESC 
            LIMIT 5
        ''')

        top_posts = cursor.fetchall()

        if top_posts:
            print("\n🏆 Top Performing Posts:")
            for post_id, engagement, inquiries in top_posts:
                print(f"• {post_id}: {engagement*100:.1f}% engagement, {inquiries} inquiries")

        conn.close()

def main():
    """Launch automation dashboard"""
    dashboard = AutomationDashboard()

    print("🚀 BUSINESS DEVELOPMENT AUTOMATION DASHBOARD")
    print("=" * 60)
    print("Central command center for LinkedIn content strategy and business development")
    print()

    # Show initial status
    status = dashboard.get_comprehensive_status()
    dashboard._display_comprehensive_status(status)

    # Check for critical alerts
    alerts = dashboard.monitor_critical_alerts()
    if alerts:
        print(f"\n🚨 {len(alerts)} CRITICAL ALERTS REQUIRE ATTENTION!")
        for alert in alerts:
            print(f"  • {alert}")

    # Launch interactive dashboard
    dashboard.interactive_dashboard()

if __name__ == "__main__":
    main()
