#!/usr/bin/env python3
"""
LinkedIn Real-Time Posting Interface
Manual posting interface with real-time performance tracking
"""

import logging
import sqlite3
from datetime import datetime

from consultation_inquiry_detector import ConsultationInquiryDetector
from linkedin_posting_system import LinkedInBusinessDevelopmentEngine

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class LinkedInPosterInterface:
    """Interactive LinkedIn posting interface with business development tracking"""

    def __init__(self):
        self.business_engine = LinkedInBusinessDevelopmentEngine()
        self.inquiry_detector = ConsultationInquiryDetector()

    def get_ready_posts(self) -> list[dict]:
        """Get posts ready for publishing"""
        conn = sqlite3.connect(self.business_engine.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            SELECT post_id, day, business_objective, expected_engagement_rate,
                   expected_consultation_inquiries, posted_at
            FROM linkedin_posts
            WHERE impressions = 0
            ORDER BY posted_at
        ''')

        results = cursor.fetchall()
        columns = [description[0] for description in cursor.description]

        posts = []
        for result in results:
            post = dict(zip(columns, result, strict=False))
            posts.append(post)

        conn.close()
        return posts

    def get_post_content(self, post_id: str) -> str | None:
        """Get formatted content for posting"""
        conn = sqlite3.connect(self.business_engine.db_path)
        cursor = conn.cursor()

        cursor.execute('SELECT content FROM linkedin_posts WHERE post_id = ?', (post_id,))
        result = cursor.fetchone()

        if result:
            content = result[0]
            # Extract the actual post content (remove metadata)
            if "## Final Optimized Post" in content or "## LinkedIn Post" in content:
                lines = content.split('\n')
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

            return content

        conn.close()
        return None

    def display_post_preview(self, post_id: str):
        """Display formatted post preview for review"""
        conn = sqlite3.connect(self.business_engine.db_path)
        cursor = conn.cursor()

        cursor.execute('SELECT * FROM linkedin_posts WHERE post_id = ?', (post_id,))
        result = cursor.fetchone()

        if not result:
            print("Post not found!")
            return

        columns = [description[0] for description in cursor.description]
        post = dict(zip(columns, result, strict=False))

        content = self.get_post_content(post_id)

        print("="*80)
        print(f"📝 POST PREVIEW: {post['day']} - {post['week_theme']}")
        print("="*80)
        print(f"🎯 Business Objective: {post['business_objective']}")
        print(f"📊 Expected Engagement: {post['expected_engagement_rate']*100:.1f}%")
        print(f"💼 Expected Consultations: {post['expected_consultation_inquiries']}")
        print(f"⏰ Scheduled Time: {post['posted_at']}")
        print(f"👥 Target Audience: {post['target_audience']}")
        print("-"*80)
        print("CONTENT:")
        print("-"*80)
        print(content)
        print("-"*80)
        print()

        conn.close()

    def mark_post_as_published(self, post_id: str, initial_metrics: dict[str, int] = None):
        """Mark post as published and add initial metrics"""
        if initial_metrics is None:
            initial_metrics = {
                'impressions': 1,  # Mark as published
                'views': 0,
                'likes': 0,
                'comments': 0,
                'shares': 0,
                'saves': 0
            }

        self.business_engine.update_post_performance(post_id, initial_metrics)
        logger.info(f"Marked post as published: {post_id}")

        # Log publication
        conn = sqlite3.connect(self.business_engine.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            UPDATE linkedin_posts
            SET posted_at = ?
            WHERE post_id = ?
        ''', (datetime.now().isoformat(), post_id))

        conn.commit()
        conn.close()

    def update_post_metrics_interactive(self, post_id: str):
        """Interactive metrics update for published post"""
        print(f"\n📊 UPDATE METRICS for {post_id}")
        print("-"*50)

        metrics = {}
        metric_prompts = [
            ("impressions", "Impressions (reach)"),
            ("views", "Profile views from this post"),
            ("likes", "Likes"),
            ("comments", "Comments"),
            ("shares", "Shares"),
            ("saves", "Saves"),
            ("clicks", "Link clicks"),
            ("profile_views", "Profile views"),
            ("connection_requests", "Connection requests"),
            ("dm_inquiries", "DM inquiries")
        ]

        for metric, description in metric_prompts:
            while True:
                try:
                    value = input(f"{description}: ").strip()
                    if value:
                        metrics[metric] = int(value)
                    break
                except ValueError:
                    print("Please enter a valid number or press Enter to skip.")

        if metrics:
            self.business_engine.update_post_performance(post_id, metrics)
            print(f"✅ Updated metrics for {post_id}")

            # Calculate and display performance
            if 'impressions' in metrics and metrics['impressions'] > 0:
                total_engagement = (
                    metrics.get('likes', 0) +
                    metrics.get('comments', 0) +
                    metrics.get('shares', 0) +
                    metrics.get('saves', 0)
                )
                engagement_rate = total_engagement / metrics['impressions']
                print(f"📈 Engagement Rate: {engagement_rate*100:.2f}%")

    def process_comments_for_inquiries(self, post_id: str):
        """Process comments for consultation inquiries"""
        print(f"\n💬 PROCESS COMMENTS for {post_id}")
        print("-"*50)
        print("Enter comments that might contain consultation inquiries.")
        print("Format: Commenter Name | Comment Text")
        print("Type 'done' when finished.")
        print()

        while True:
            comment_input = input("Comment (Name | Text): ").strip()

            if comment_input.lower() == 'done':
                break

            if '|' in comment_input:
                try:
                    name, text = comment_input.split('|', 1)
                    name = name.strip()
                    text = text.strip()

                    inquiry_id = self.inquiry_detector.process_linkedin_comment(
                        post_id, text, name
                    )

                    if inquiry_id:
                        print(f"✅ Detected consultation inquiry: {inquiry_id}")

                        # Generate suggested response
                        response = self.inquiry_detector.generate_follow_up_response(inquiry_id)
                        print(f"💡 Suggested response: {response.get('comment_reply', 'No response generated')}")
                        print()
                    else:
                        print("❌ No consultation inquiry detected in this comment")
                        print()

                except Exception as e:
                    print(f"Error processing comment: {e}")
            else:
                print("Please use format: Name | Comment Text")

    def show_business_development_dashboard(self):
        """Show current business development status"""
        report = self.business_engine.generate_business_development_report()
        pending_inquiries = self.inquiry_detector.get_pending_inquiries()

        print("\n" + "="*80)
        print("💼 BUSINESS DEVELOPMENT DASHBOARD")
        print("="*80)

        # Post performance summary
        print("📊 CONTENT PERFORMANCE:")
        print(f"  • Total posts published: {report['post_performance']['total_posts']}")
        print(f"  • Average engagement rate: {report['post_performance']['avg_engagement_rate']*100:.2f}%")
        print(f"  • Total impressions: {report['post_performance']['total_impressions']:,}")
        print(f"  • Total consultation requests: {report['post_performance']['total_consultation_requests']}")

        # Business pipeline
        print("\n💰 BUSINESS PIPELINE:")
        print(f"  • Total inquiries: {report['business_pipeline']['total_inquiries']}")
        print(f"  • Discovery calls scheduled: {report['business_pipeline']['discovery_calls']}")
        print(f"  • Proposals sent: {report['business_pipeline']['proposals_sent']}")
        print(f"  • Contracts won: {report['business_pipeline']['contracts_won']}")
        print(f"  • Total pipeline value: ${report['business_pipeline']['total_pipeline_value']:,}")
        print(f"  • Revenue generated: ${report['business_pipeline']['won_value']:,}")

        # Pending inquiries
        print(f"\n📋 PENDING INQUIRIES ({len(pending_inquiries)}):")
        if pending_inquiries:
            for inquiry in pending_inquiries[:5]:  # Show top 5
                print(f"  • {inquiry['inquiry_type']} - {inquiry['contact_name']} - ${inquiry['estimated_value']:,} (Priority: {inquiry['priority_score']})")
        else:
            print("  • No pending inquiries")

        # Top performing posts
        if report['top_performing_posts']:
            print("\n🏆 TOP PERFORMING POSTS:")
            for post in report['top_performing_posts'][:3]:
                print(f"  • {post['day']} - {post['engagement_rate']*100:.1f}% engagement, {post['consultation_requests']} inquiries")

        print("="*80)

    def interactive_menu(self):
        """Main interactive menu"""
        while True:
            print("\n🚀 LINKEDIN BUSINESS DEVELOPMENT INTERFACE")
            print("="*50)
            print("1. View ready posts")
            print("2. Preview post content")
            print("3. Mark post as published")
            print("4. Update post metrics")
            print("5. Process comments for inquiries")
            print("6. Business development dashboard")
            print("7. Exit")
            print()

            choice = input("Select option (1-7): ").strip()

            if choice == '1':
                ready_posts = self.get_ready_posts()
                if ready_posts:
                    print(f"\n📋 READY POSTS ({len(ready_posts)}):")
                    for i, post in enumerate(ready_posts, 1):
                        print(f"{i}. {post['day']} - {post['business_objective']}")
                        print(f"   Expected: {post['expected_engagement_rate']*100:.1f}% engagement, {post['expected_consultation_inquiries']} consultations")
                        print()
                else:
                    print("\n❌ No posts ready for publishing")

            elif choice == '2':
                post_id = input("Enter post ID: ").strip()
                if post_id:
                    self.display_post_preview(post_id)

            elif choice == '3':
                post_id = input("Enter post ID to mark as published: ").strip()
                if post_id:
                    self.mark_post_as_published(post_id)
                    print(f"✅ Marked {post_id} as published")

            elif choice == '4':
                post_id = input("Enter post ID to update metrics: ").strip()
                if post_id:
                    self.update_post_metrics_interactive(post_id)

            elif choice == '5':
                post_id = input("Enter post ID to process comments: ").strip()
                if post_id:
                    self.process_comments_for_inquiries(post_id)

            elif choice == '6':
                self.show_business_development_dashboard()

            elif choice == '7':
                print("Goodbye! 🚀")
                break

            else:
                print("Invalid choice. Please select 1-7.")

def main():
    """Launch LinkedIn posting interface"""
    poster = LinkedInPosterInterface()

    print("🚀 LinkedIn Business Development Interface")
    print("Ready to start posting Week 3 content and tracking consultation inquiries!")
    print()

    # Show available posts
    ready_posts = poster.get_ready_posts()
    if ready_posts:
        print(f"📋 {len(ready_posts)} posts ready for publishing:")
        for post in ready_posts:
            print(f"  • {post['day']}: {post['business_objective']}")

    print("\n💡 SUGGESTED IMMEDIATE ACTION:")
    print("1. Preview and publish Monday's '10x Engineering Team' post")
    print("2. Track engagement metrics after 24 hours")
    print("3. Process any comments for consultation inquiries")
    print("4. Follow up on high-priority inquiries within 24 hours")
    print()

    # Launch interactive menu
    poster.interactive_menu()

if __name__ == "__main__":
    main()
