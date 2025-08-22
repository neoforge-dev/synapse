#!/usr/bin/env python3
"""
LinkedIn Performance Tracking Script
Monitor real-time performance of Week 3 content and update analytics
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from business_development.week3_analytics_dashboard import Week3AnalyticsDashboard


def track_monday_post():
    """Track Monday's 10x team building post performance"""
    dashboard = Week3AnalyticsDashboard()

    print("📊 Week 3 Monday Post Performance Tracking")
    print("=" * 50)
    print("Post: Building a 10x Engineering Team")
    print("Posted: Monday 7:00 AM (target time)")
    print("Target Engagement: 8-10%")
    print("Target Business Leads: 1-2 team building consultations")
    print()

    # Get current metrics (manual input for now, could integrate with LinkedIn API)
    print("Enter current metrics (press Enter to skip):")

    metrics = {}

    # Basic engagement metrics
    impressions = input("Impressions: ").strip()
    if impressions:
        metrics['impressions'] = int(impressions)

    views = input("Profile views from post: ").strip()
    if views:
        metrics['views'] = int(views)

    likes = input("Likes: ").strip()
    if likes:
        metrics['likes'] = int(likes)

    comments = input("Comments: ").strip()
    if comments:
        metrics['comments'] = int(comments)

    shares = input("Shares: ").strip()
    if shares:
        metrics['shares'] = int(shares)

    saves = input("Saves: ").strip()
    if saves:
        metrics['saves'] = int(saves)

    clicks = input("Link clicks: ").strip()
    if clicks:
        metrics['clicks'] = int(clicks)

    # Business development metrics
    profile_views = input("Profile views: ").strip()
    if profile_views:
        metrics['profile_views'] = int(profile_views)

    connection_requests = input("Connection requests: ").strip()
    if connection_requests:
        metrics['connection_requests'] = int(connection_requests)

    dm_inquiries = input("DM inquiries: ").strip()
    if dm_inquiries:
        metrics['dm_inquiries'] = int(dm_inquiries)

    consultation_leads = input("Consultation inquiries: ").strip()
    if consultation_leads:
        metrics['consultation_leads'] = int(consultation_leads)

    if metrics:
        # Add posting time
        metrics['posted_at'] = '2025-01-20T07:00:00'

        # Update dashboard
        dashboard.update_post_metrics('2025-01-20-monday', metrics)

        # Analyze timing
        timing_analysis = dashboard.analyze_optimal_timing('2025-01-20-monday', '2025-01-20T07:00:00')

        print("\n📈 Performance Analysis:")
        print("-" * 30)

        if 'impressions' in metrics and metrics['impressions'] > 0:
            total_engagement = metrics.get('likes', 0) + metrics.get('comments', 0) + metrics.get('shares', 0) + metrics.get('saves', 0)
            engagement_rate = total_engagement / metrics['impressions']
            print(f"Engagement Rate: {engagement_rate*100:.1f}%")

            if engagement_rate >= 0.08:
                print("✅ Above target engagement (8%+)")
            elif engagement_rate >= 0.06:
                print("⚠️  Below target but acceptable (6-8%)")
            else:
                print("❌ Below target engagement (<6%)")

        business_actions = metrics.get('profile_views', 0) + metrics.get('connection_requests', 0) + metrics.get('dm_inquiries', 0)
        consultation_leads = metrics.get('consultation_leads', 0)

        print(f"Business Actions: {business_actions}")
        print(f"Consultation Leads: {consultation_leads}")

        if consultation_leads >= 1:
            print("✅ Meeting business lead target")
        else:
            print("⚠️  Track consultation inquiries over next 48 hours")

        print("\nTiming Analysis:")
        print(f"Optimal Timing: {'✅ Yes' if timing_analysis['optimal_timing'] else '❌ No'}")
        print(f"Audience Activity Score: {timing_analysis['audience_activity_score']}/100")
        print(f"Recommendation: {timing_analysis['timing_recommendation']}")

        # Generate full report
        report = dashboard.generate_performance_report()
        print("\n📊 Week 3 Summary So Far:")
        print(f"Average Engagement Rate: {report['summary']['average_engagement_rate']*100:.1f}%")
        print(f"Total Business Leads: {report['summary']['total_business_leads']}")

        # Create visualization
        try:
            chart_path = dashboard.create_analytics_visualization()
            if chart_path:
                print(f"\n📈 Analytics chart saved: {chart_path}")
        except Exception as e:
            print(f"⚠️  Could not create chart (matplotlib not available): {e}")

        print("\n🎯 Next Steps:")
        print("1. Monitor comments for business development opportunities")
        print("2. Respond to engagement within 2 hours for maximum visibility")
        print("3. Follow up on any consultation inquiries within 24 hours")
        print("4. Post Tuesday content at 6:30 AM for optimal engagement")

    else:
        print("No metrics entered. Run again when you have performance data.")

def track_custom_post():
    """Track performance for any Week 3 post"""
    dashboard = Week3AnalyticsDashboard()

    print("📊 Week 3 Custom Post Tracking")
    print("=" * 40)

    # Select post
    posts = {
        '1': '2025-01-20-monday (10x Engineering Team)',
        '2': '2025-01-21-tuesday (Code Review Culture)',
        '3': '2025-01-22-wednesday (Hiring Strategy)',
        '4': '2025-01-23-thursday (Python Project Structure)',
        '5': '2025-01-24-friday (Leadership Mentorship)',
        '6': '2025-01-25-saturday (Team Automation)',
        '7': '2025-01-26-sunday (Technical Empathy)'
    }

    print("Select post to track:")
    for key, post in posts.items():
        print(f"{key}. {post}")

    selection = input("\nEnter post number (1-7): ").strip()

    if selection not in posts:
        print("Invalid selection")
        return

    post_id = posts[selection].split(' ')[0]
    post_title = posts[selection].split(' (')[1].rstrip(')')

    print(f"\nTracking: {post_title}")
    print(f"Post ID: {post_id}")

    # Get metrics (same as monday_post function)
    # ... (same input collection logic)

    print("Enter current metrics:")

    metrics = {}
    fields = [
        ('impressions', 'Impressions'),
        ('views', 'Profile views from post'),
        ('likes', 'Likes'),
        ('comments', 'Comments'),
        ('shares', 'Shares'),
        ('saves', 'Saves'),
        ('clicks', 'Link clicks'),
        ('profile_views', 'Profile views'),
        ('connection_requests', 'Connection requests'),
        ('dm_inquiries', 'DM inquiries'),
        ('consultation_leads', 'Consultation inquiries')
    ]

    for field, label in fields:
        value = input(f"{label}: ").strip()
        if value:
            metrics[field] = int(value)

    if metrics:
        # Determine posting time based on post
        posting_times = {
            '2025-01-20-monday': '2025-01-20T07:00:00',
            '2025-01-21-tuesday': '2025-01-21T06:30:00',
            '2025-01-22-wednesday': '2025-01-22T08:00:00',
            '2025-01-23-thursday': '2025-01-23T06:30:00',
            '2025-01-24-friday': '2025-01-24T08:30:00',
            '2025-01-25-saturday': '2025-01-25T10:00:00',
            '2025-01-26-sunday': '2025-01-26T18:00:00'
        }

        metrics['posted_at'] = posting_times.get(post_id, '2025-01-20T08:00:00')

        # Update dashboard
        dashboard.update_post_metrics(post_id, metrics)

        # Generate analysis
        print(f"\n📈 Performance Analysis for {post_title}")
        report = dashboard.generate_performance_report()

        # Find this post's performance
        post_performance = None
        for p in report['performance_by_post']:
            if p['post_id'] == post_id:
                post_performance = p
                break

        if post_performance:
            print(f"Engagement Rate: {post_performance['engagement_rate']*100:.1f}%")
            print(f"Business Leads: {post_performance['business_leads']}")
            print(f"Timing Score: {post_performance['timing_score']:.1f}")

        print("\n📊 Week 3 Overall Performance:")
        print(f"Average Engagement: {report['summary']['average_engagement_rate']*100:.1f}%")
        print(f"Total Business Leads: {report['summary']['total_business_leads']}")

        if report['recommendations']:
            print("\n💡 Recommendations:")
            for rec in report['recommendations']:
                print(f"• {rec}")

def main():
    """Main tracking interface"""
    if len(sys.argv) > 1 and sys.argv[1] == 'monday':
        track_monday_post()
    else:
        print("LinkedIn Performance Tracking")
        print("=" * 30)
        print("1. Track Monday post (quick)")
        print("2. Track any Week 3 post")
        print("3. Generate full Week 3 report")

        choice = input("\nSelect option (1-3): ").strip()

        if choice == '1':
            track_monday_post()
        elif choice == '2':
            track_custom_post()
        elif choice == '3':
            dashboard = Week3AnalyticsDashboard()
            report = dashboard.generate_performance_report()

            print("\n📊 Full Week 3 Performance Report")
            print("=" * 40)
            print(f"Total Posts: {report['summary']['total_posts']}")
            print(f"Total Impressions: {report['summary']['total_impressions']:,}")
            print(f"Average Engagement Rate: {report['summary']['average_engagement_rate']*100:.1f}%")
            print(f"Total Business Leads: {report['summary']['total_business_leads']}")
            print(f"Business Conversion Rate: {report['summary']['business_conversion_rate']*100:.3f}%")

            if report['recommendations']:
                print("\n💡 Recommendations:")
                for rec in report['recommendations']:
                    print(f"• {rec}")
        else:
            print("Invalid choice")

if __name__ == "__main__":
    main()
