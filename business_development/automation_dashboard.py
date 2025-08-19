#!/usr/bin/env python3
"""
Automation Dashboard and Control Center
Monitor and control all business development automation systems
"""

import sqlite3
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import logging
from pathlib import Path
import sys

# Add business_development to path
sys.path.insert(0, str(Path(__file__).parent))

from linkedin_posting_system import LinkedInBusinessDevelopmentEngine
from consultation_inquiry_detector import ConsultationInquiryDetector
from linkedin_api_client import LinkedInAPIClient
from content_scheduler import ContentAutomationPipeline

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
        
    def get_comprehensive_status(self) -> Dict:
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
                'total_value': sum(inq['estimated_value'] for inq in pending_inquiries),
                'high_priority': len([inq for inq in pending_inquiries if inq['priority_score'] >= 4])
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
    
    def _generate_action_items(self, status: Dict) -> List[str]:
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
    
    def monitor_critical_alerts(self) -> List[str]:
        """Monitor for critical alerts that need immediate attention"""
        alerts = []
        
        # Check for high-priority inquiries over 24 hours old
        pending_inquiries = self.inquiry_detector.get_pending_inquiries(priority_threshold=4)
        
        for inquiry in pending_inquiries:
            created_at = datetime.fromisoformat(inquiry['created_at'])
            hours_old = (datetime.now() - created_at).total_hours
            
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
            print("7. Exit")
            
            choice = input("\nSelect option (1-7): ").strip()
            
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
                print("👋 Dashboard closed!")
                break
                
            else:
                print("Invalid choice. Please select 1-7.")
    
    def _display_comprehensive_status(self, status: Dict):
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
        print(f"\n📈 PERFORMANCE:")
        print(f"  • Posts: {metrics['post_performance']['total_posts']}")
        print(f"  • Avg Engagement: {metrics['post_performance']['avg_engagement_rate']*100:.2f}%")
        print(f"  • Consultations: {metrics['post_performance']['total_consultation_requests']}")
        print(f"  • Pipeline: ${metrics['business_pipeline']['total_pipeline_value']:,}")
        
        # Pending business development
        print(f"\n💼 PENDING BUSINESS DEV:")
        print(f"  • Inquiries: {status['pending_inquiries']['count']}")
        print(f"  • High Priority: {status['pending_inquiries']['high_priority']}")
        print(f"  • Value: ${status['pending_inquiries']['total_value']:,}")
    
    def _display_pending_inquiries(self, inquiries: List[Dict]):
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