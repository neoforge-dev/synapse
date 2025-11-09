#!/usr/bin/env python3
"""
Content Automation Pipeline and Scheduling System
Automate content posting at optimal times with performance tracking
"""

import logging
import sqlite3
import time
from datetime import datetime
from datetime import time as datetime_time

import schedule

from .consultation_inquiry_detector import ConsultationInquiryDetector
from .linkedin_api_client import LinkedInAPIClient, LinkedInAutomationScheduler
from .linkedin_posting_system import LinkedInBusinessDevelopmentEngine

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class ContentAutomationPipeline:
    """Complete content automation pipeline with optimal scheduling"""

    def __init__(self):
        self.business_engine = LinkedInBusinessDevelopmentEngine()
        self.api_client = LinkedInAPIClient()
        self.scheduler = LinkedInAutomationScheduler(self.api_client)
        self.inquiry_detector = ConsultationInquiryDetector()

        # Optimal posting times based on research
        self.optimal_times = {
            'Monday': datetime_time(7, 0),      # 7:00 AM
            'Tuesday': datetime_time(6, 30),    # 6:30 AM (OPTIMAL)
            'Wednesday': datetime_time(8, 0),   # 8:00 AM
            'Thursday': datetime_time(6, 30),   # 6:30 AM (OPTIMAL)
            'Friday': datetime_time(8, 30),     # 8:30 AM
            'Saturday': datetime_time(10, 0),   # 10:00 AM
            'Sunday': datetime_time(18, 0)      # 6:00 PM
        }

    def schedule_week_content(self, week_number: int):
        """Schedule all content for a specific week"""
        conn = sqlite3.connect(self.business_engine.db_path)
        cursor = conn.cursor()

        # Get all posts for the week that haven't been posted yet
        cursor.execute('''
            SELECT post_id, day, posted_at, business_objective
            FROM linkedin_posts
            WHERE post_id LIKE ?
            AND impressions = 0
            ORDER BY posted_at
        ''', (f'%-week-{week_number:02d}-%',))

        results = cursor.fetchall()

        scheduled_count = 0
        for post_id, day, _scheduled_time, _objective in results:

            # Schedule using Python schedule library
            if day == 'Monday':
                schedule.every().monday.at("07:00").do(self._post_content, post_id)
            elif day == 'Tuesday':
                schedule.every().tuesday.at("06:30").do(self._post_content, post_id)
            elif day == 'Wednesday':
                schedule.every().wednesday.at("08:00").do(self._post_content, post_id)
            elif day == 'Thursday':
                schedule.every().thursday.at("06:30").do(self._post_content, post_id)
            elif day == 'Friday':
                schedule.every().friday.at("08:30").do(self._post_content, post_id)
            elif day == 'Saturday':
                schedule.every().saturday.at("10:00").do(self._post_content, post_id)
            elif day == 'Sunday':
                schedule.every().sunday.at("18:00").do(self._post_content, post_id)

            scheduled_count += 1
            logger.info(f"Scheduled {day} post: {post_id}")

        conn.close()
        logger.info(f"Scheduled {scheduled_count} posts for week {week_number}")
        return scheduled_count

    def _post_content(self, post_id: str):
        """Execute scheduled content posting"""
        logger.info(f"Executing scheduled post: {post_id}")

        try:
            # Get post content
            conn = sqlite3.connect(self.business_engine.db_path)
            cursor = conn.cursor()

            cursor.execute('SELECT content, day, business_objective FROM linkedin_posts WHERE post_id = ?', (post_id,))
            result = cursor.fetchone()

            if not result:
                logger.error(f"Post not found: {post_id}")
                return

            content, day, objective = result
            formatted_content = self._extract_post_content(content)

            # Post to LinkedIn
            linkedin_post_id = self.api_client.post_to_linkedin(formatted_content, post_id)

            if linkedin_post_id:
                # Mark as posted
                cursor.execute('''
                    UPDATE linkedin_posts
                    SET impressions = 1, posted_at = ?
                    WHERE post_id = ?
                ''', (datetime.now().isoformat(), post_id))
                conn.commit()

                logger.info(f"Successfully posted {day} content: {post_id}")

                # Schedule performance check for later
                self._schedule_performance_check(post_id, linkedin_post_id)

            else:
                logger.error(f"Failed to post content: {post_id}")

            conn.close()

        except Exception as e:
            logger.error(f"Error posting scheduled content {post_id}: {e}")

    def _extract_post_content(self, raw_content: str) -> str:
        """Extract actual post content from markdown"""
        if "## Final Optimized Post" in raw_content or "## LinkedIn Post" in raw_content:
            lines = raw_content.split('\n')
            post_start = None

            for i, line in enumerate(lines):
                if "## Final Optimized Post" in line or "## LinkedIn Post" in line:
                    post_start = i + 1
                    break

            if post_start:
                post_content = []
                for line in lines[post_start:]:
                    if line.strip() and not line.startswith('#') and not line.startswith('**Content Strategy'):
                        post_content.append(line)
                    elif line.startswith('---') or line.startswith('## Content Strategy'):
                        break

                return '\n'.join(post_content).strip()

        return raw_content

    def _schedule_performance_check(self, post_id: str, linkedin_post_id: str):
        """Schedule performance check for posted content"""
        # Schedule checks at 2 hours, 24 hours, and 48 hours
        schedule.every(2).hours.do(
            self._check_post_performance,
            post_id,
            linkedin_post_id,
            "2-hour"
        ).tag(f'check_{post_id}')

        schedule.every(24).hours.do(
            self._check_post_performance,
            post_id,
            linkedin_post_id,
            "24-hour"
        ).tag(f'check_{post_id}')

    def _check_post_performance(self, post_id: str, linkedin_post_id: str, check_type: str):
        """Check post performance and update metrics"""
        logger.info(f"Running {check_type} performance check for {post_id}")

        try:
            # Get analytics from LinkedIn
            analytics = self.api_client.get_post_analytics(linkedin_post_id)

            if analytics:
                # Update performance metrics
                metrics = {
                    'impressions': analytics.get('impressions', 0),
                    'clicks': analytics.get('clicks', 0),
                    'likes': analytics.get('likes', 0),
                    'comments': analytics.get('comments', 0),
                    'shares': analytics.get('shares', 0)
                }

                self.business_engine.update_post_performance(post_id, metrics)
                logger.info(f"Updated metrics for {post_id}: {metrics}")

                # If this is the 24-hour check, analyze for consultation inquiries
                if check_type == "24-hour" and analytics.get('comments', 0) > 0:
                    self._analyze_comments_for_inquiries(post_id, linkedin_post_id)

        except Exception as e:
            logger.error(f"Error checking performance for {post_id}: {e}")

        # Clean up one-time schedules
        if check_type == "48-hour":
            schedule.clear(f'check_{post_id}')

    def _analyze_comments_for_inquiries(self, post_id: str, linkedin_post_id: str):
        """Analyze post comments for consultation inquiries"""
        logger.info(f"Analyzing comments for consultation inquiries: {post_id}")

        # In a full implementation, this would fetch actual comments from LinkedIn API
        # For now, we'll set up the framework for manual comment processing

        print(f"\n💬 COMMENT ANALYSIS NEEDED: {post_id}")
        print("=" * 60)
        print("Please check LinkedIn for comments on this post and process any")
        print("consultation inquiries using the consultation_inquiry_detector.py")
        print("=" * 60)

    def start_automation_daemon(self):
        """Start the content automation daemon"""
        logger.info("Starting content automation daemon...")

        # Schedule Week 3 content immediately
        self.schedule_week_content(3)

        print("📅 CONTENT AUTOMATION SCHEDULER ACTIVE")
        print("=" * 50)
        print("Scheduled Posts:")

        jobs = schedule.get_jobs()
        for job in jobs:
            print(f"• {job}")

        print("\n🔄 Running scheduler daemon...")
        print("Press Ctrl+C to stop")

        try:
            while True:
                schedule.run_pending()
                time.sleep(60)  # Check every minute

        except KeyboardInterrupt:
            logger.info("Content automation daemon stopped")
            print("\n👋 Content automation daemon stopped")

    def schedule_immediate_posting(self, post_id: str):
        """Schedule a post for immediate publishing"""
        logger.info(f"Scheduling immediate posting: {post_id}")

        # Schedule for 1 minute from now
        schedule.every(1).minutes.do(self._post_content, post_id).tag(f'immediate_{post_id}')

        print(f"📝 {post_id} scheduled for immediate posting...")

        # Wait for the post to be published
        posted = False
        wait_count = 0

        while not posted and wait_count < 5:  # Wait up to 5 minutes
            schedule.run_pending()
            time.sleep(60)
            wait_count += 1

            # Check if post was published
            conn = sqlite3.connect(self.business_engine.db_path)
            cursor = conn.cursor()
            cursor.execute('SELECT impressions FROM linkedin_posts WHERE post_id = ?', (post_id,))
            result = cursor.fetchone()
            conn.close()

            if result and result[0] > 0:
                posted = True
                print(f"✅ {post_id} posted successfully!")

        # Clean up the job
        schedule.clear(f'immediate_{post_id}')

        return posted

    def get_automation_status(self) -> dict:
        """Get current automation status"""
        scheduled_jobs = len(schedule.get_jobs())

        # Get pending posts
        conn = sqlite3.connect(self.business_engine.db_path)
        cursor = conn.cursor()

        cursor.execute('SELECT COUNT(*) FROM linkedin_posts WHERE impressions = 0')
        pending_posts = cursor.fetchone()[0]

        cursor.execute('SELECT COUNT(*) FROM linkedin_posts WHERE impressions > 0')
        published_posts = cursor.fetchone()[0]

        conn.close()

        return {
            'scheduled_jobs': scheduled_jobs,
            'pending_posts': pending_posts,
            'published_posts': published_posts,
            'api_available': self.api_client.api_available,
            'automation_active': scheduled_jobs > 0
        }

def main():
    """Launch content automation pipeline"""
    pipeline = ContentAutomationPipeline()

    print("🚀 Content Automation Pipeline")
    print("=" * 40)

    # Show automation status
    status = pipeline.get_automation_status()
    print("📊 Status:")
    print(f"• LinkedIn API Available: {status['api_available']}")
    print(f"• Pending Posts: {status['pending_posts']}")
    print(f"• Published Posts: {status['published_posts']}")
    print(f"• Scheduled Jobs: {status['scheduled_jobs']}")

    print("\n💡 Available Commands:")
    print("1. Schedule Week 3 content")
    print("2. Start automation daemon")
    print("3. Schedule immediate posting")
    print("4. Check automation status")
    print("5. Exit")

    while True:
        choice = input("\nSelect option (1-5): ").strip()

        if choice == '1':
            count = pipeline.schedule_week_content(3)
            print(f"✅ Scheduled {count} posts for Week 3")

        elif choice == '2':
            pipeline.start_automation_daemon()
            break

        elif choice == '3':
            post_id = input("Enter post ID for immediate posting: ").strip()
            if post_id:
                success = pipeline.schedule_immediate_posting(post_id)
                if success:
                    print(f"✅ {post_id} posted successfully")
                else:
                    print(f"❌ Failed to post {post_id}")

        elif choice == '4':
            status = pipeline.get_automation_status()
            print("\n📊 Automation Status:")
            for key, value in status.items():
                print(f"• {key}: {value}")

        elif choice == '5':
            print("👋 Goodbye!")
            break

        else:
            print("Invalid choice. Please select 1-5.")

if __name__ == "__main__":
    main()
