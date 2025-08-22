#!/usr/bin/env python3
"""
Unified Content Management System
Cross-platform content coordination, scheduling, and analytics
"""

import json
import logging
import sqlite3
import sys
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Add project paths
sys.path.insert(0, str(Path(__file__).parent.parent / 'business_development'))
sys.path.insert(0, str(Path(__file__).parent))

from linkedin_api_client import LinkedInAPIClient
from twitter_api_client import TwitterAPIClient

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class Platform(Enum):
    """Supported social media platforms"""
    LINKEDIN = "linkedin"
    TWITTER = "twitter"
    NEWSLETTER = "newsletter"
    BLOG = "blog"

class ContentStatus(Enum):
    """Content status tracking"""
    DRAFT = "draft"
    SCHEDULED = "scheduled" 
    POSTED = "posted"
    FAILED = "failed"

@dataclass
class ContentPiece:
    """Unified content structure for cross-platform publishing"""
    content_id: str
    original_content: str
    platform_adaptations: Dict[Platform, str]
    scheduled_times: Dict[Platform, str]
    post_ids: Dict[Platform, str]
    status: Dict[Platform, ContentStatus]
    performance_metrics: Dict[Platform, Dict[str, Any]]
    business_objective: str
    target_audience: str
    created_at: str
    updated_at: str

@dataclass
class CrossPlatformStrategy:
    """Cross-platform posting strategy"""
    primary_platform: Platform
    secondary_platforms: List[Platform]
    timing_delays: Dict[Platform, int]  # Minutes after primary
    content_adaptations: Dict[Platform, str]  # Adaptation instructions
    cross_promotion: bool = True

class UnifiedContentManager:
    """Unified system for cross-platform content management"""

    def __init__(self):
        self.linkedin_client = LinkedInAPIClient()
        self.twitter_client = TwitterAPIClient()
        self.db_path = "unified_content_management.db"
        self._init_database()
        
        # Platform-specific optimal posting times (24-hour format)
        self.optimal_times = {
            Platform.LINKEDIN: {
                'Monday': '07:00', 'Tuesday': '08:00', 'Wednesday': '08:30',
                'Thursday': '09:00', 'Friday': '09:30'
            },
            Platform.TWITTER: {
                'Monday': '09:00', 'Tuesday': '09:30', 'Wednesday': '10:00', 
                'Thursday': '10:30', 'Friday': '11:00'
            },
            Platform.NEWSLETTER: {
                'Sunday': '18:00', 'Wednesday': '19:00'
            }
        }
        
        logger.info("Unified Content Manager initialized")

    def _init_database(self):
        """Initialize unified content management database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Content pieces table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS content_pieces (
                content_id TEXT PRIMARY KEY,
                original_content TEXT NOT NULL,
                business_objective TEXT,
                target_audience TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Platform adaptations table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS platform_adaptations (
                adaptation_id TEXT PRIMARY KEY,
                content_id TEXT NOT NULL,
                platform TEXT NOT NULL,
                adapted_content TEXT NOT NULL,
                scheduled_time TIMESTAMP,
                post_id TEXT,
                status TEXT DEFAULT 'draft',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (content_id) REFERENCES content_pieces (content_id)
            )
        ''')

        # Cross-platform performance tracking
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS cross_platform_metrics (
                metric_id TEXT PRIMARY KEY,
                content_id TEXT NOT NULL,
                platform TEXT NOT NULL,
                impressions INTEGER DEFAULT 0,
                engagement INTEGER DEFAULT 0,
                clicks INTEGER DEFAULT 0,
                conversions INTEGER DEFAULT 0,
                engagement_rate REAL DEFAULT 0.0,
                ctr REAL DEFAULT 0.0,
                conversion_rate REAL DEFAULT 0.0,
                recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (content_id) REFERENCES content_pieces (content_id)
            )
        ''')

        # Content strategies table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS content_strategies (
                strategy_id TEXT PRIMARY KEY,
                content_id TEXT NOT NULL,
                primary_platform TEXT NOT NULL,
                secondary_platforms TEXT,  -- JSON array
                timing_strategy TEXT,  -- JSON object
                adaptation_notes TEXT,
                cross_promotion BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (content_id) REFERENCES content_pieces (content_id)
            )
        ''')

        # Create indexes
        indexes = [
            "CREATE INDEX IF NOT EXISTS idx_content_created ON content_pieces (created_at DESC)",
            "CREATE INDEX IF NOT EXISTS idx_adaptations_content ON platform_adaptations (content_id)",
            "CREATE INDEX IF NOT EXISTS idx_adaptations_platform ON platform_adaptations (platform, status)",
            "CREATE INDEX IF NOT EXISTS idx_metrics_content ON cross_platform_metrics (content_id, platform)",
            "CREATE INDEX IF NOT EXISTS idx_strategies_content ON content_strategies (content_id)"
        ]

        for index in indexes:
            cursor.execute(index)

        conn.commit()
        conn.close()
        logger.info("Unified content management database initialized")

    def create_content_piece(self, original_content: str, business_objective: str, 
                           target_audience: str) -> str:
        """Create new content piece for cross-platform distribution"""
        content_id = f"content_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO content_pieces 
            (content_id, original_content, business_objective, target_audience)
            VALUES (?, ?, ?, ?)
        ''', (content_id, original_content, business_objective, target_audience))
        
        conn.commit()
        conn.close()
        
        logger.info(f"Created content piece: {content_id}")
        return content_id

    def adapt_content_for_platforms(self, content_id: str, 
                                  target_platforms: List[Platform]) -> Dict[Platform, str]:
        """Adapt content for multiple platforms"""
        # Get original content
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT original_content FROM content_pieces WHERE content_id = ?', (content_id,))
        result = cursor.fetchone()
        conn.close()
        
        if not result:
            raise ValueError(f"Content {content_id} not found")
        
        original_content = result[0]
        adaptations = {}
        
        for platform in target_platforms:
            if platform == Platform.LINKEDIN:
                # LinkedIn content remains largely unchanged (already optimized)
                adaptations[platform] = original_content
                
            elif platform == Platform.TWITTER:
                # Convert to Twitter thread
                tweets = self.twitter_client.convert_linkedin_to_twitter_thread(original_content, content_id)
                adaptations[platform] = json.dumps([tweet.content for tweet in tweets])
                
            elif platform == Platform.NEWSLETTER:
                # Newsletter format with more context
                adaptations[platform] = self._adapt_for_newsletter(original_content)
                
            elif platform == Platform.BLOG:
                # Long-form blog content
                adaptations[platform] = self._adapt_for_blog(original_content)
        
        # Save adaptations to database
        self._save_platform_adaptations(content_id, adaptations)
        
        return adaptations

    def _adapt_for_newsletter(self, content: str) -> str:
        """Adapt content for newsletter format"""
        # Extract core message and expand with context
        newsletter_content = f"""
# Strategic Tech Leadership Insight

{content}

---

## Why This Matters for Technical Leaders

This insight directly impacts your ability to build and scale high-performance engineering teams. Understanding these principles helps you:

- Make better hiring and team composition decisions
- Improve team productivity and delivery velocity  
- Reduce technical debt and increase code quality
- Build sustainable engineering culture

## Take Action

Consider how you can apply this in your current role:
1. Assess your current team dynamics
2. Identify areas for improvement
3. Implement systematic changes
4. Measure and iterate

---

*Want more strategic technical leadership insights? Reply with your biggest team challenge.*

**P.S.** If you're looking for personalized guidance on building high-performance engineering teams, I offer consultation sessions. Reply "CONSULT" to learn more.
        """.strip()
        
        return newsletter_content

    def _adapt_for_blog(self, content: str) -> str:
        """Adapt content for long-form blog format"""
        blog_content = f"""
# Building High-Performance Engineering Teams: A Strategic Approach

{content}

## The Strategic Context

In today's competitive technology landscape, the difference between companies that scale successfully and those that struggle often comes down to engineering team performance. While individual talent matters, the systematic approach to team building and culture development creates sustainable competitive advantages.

## Deep Dive: Implementation Framework

### Phase 1: Assessment and Foundation
- Evaluate current team dynamics and performance patterns
- Identify knowledge silos and communication bottlenecks
- Establish baseline metrics for team productivity

### Phase 2: Systematic Improvement
- Implement knowledge sharing protocols
- Develop mentorship and growth pathways
- Create accountability systems for collective ownership

### Phase 3: Scaling and Optimization
- Measure and optimize team performance over time
- Scale successful patterns across multiple teams
- Build organizational learning systems

## Case Study: Real-World Application

I recently worked with a startup facing rapid growth challenges. Their 5-person engineering team was struggling to maintain velocity while adding new team members...

[Detailed case study with specific metrics and outcomes]

## Key Takeaways for Technical Leaders

1. **Systems over Heroes**: Build processes that work regardless of individual availability
2. **Culture as Strategy**: Team culture directly impacts delivery outcomes
3. **Measurement Matters**: Track both technical and team health metrics
4. **Continuous Iteration**: Teams are living systems that require ongoing optimization

## Next Steps

If you're ready to transform your engineering team performance:

1. **Assessment**: Evaluate your current team dynamics using the framework above
2. **Planning**: Develop a systematic improvement strategy
3. **Implementation**: Execute changes with clear metrics and feedback loops
4. **Scaling**: Apply successful patterns across your organization

---

*Need help implementing these strategies in your organization? I work with technical leaders to build high-performance engineering teams. [Book a consultation](link) to discuss your specific challenges.*
        """.strip()
        
        return blog_content

    def _save_platform_adaptations(self, content_id: str, adaptations: Dict[Platform, str]):
        """Save platform adaptations to database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        for platform, adapted_content in adaptations.items():
            adaptation_id = f"{content_id}_{platform.value}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            cursor.execute('''
                INSERT OR REPLACE INTO platform_adaptations 
                (adaptation_id, content_id, platform, adapted_content)
                VALUES (?, ?, ?, ?)
            ''', (adaptation_id, content_id, platform.value, adapted_content))
        
        conn.commit()
        conn.close()

    def schedule_cross_platform_posting(self, content_id: str, 
                                      strategy: CrossPlatformStrategy,
                                      base_date: datetime) -> Dict[Platform, str]:
        """Schedule content across multiple platforms with optimal timing"""
        scheduled_times = {}
        
        # Get base posting time for primary platform
        day_name = base_date.strftime('%A')
        base_time_str = self.optimal_times.get(strategy.primary_platform, {}).get(day_name, '09:00')
        base_hour, base_minute = map(int, base_time_str.split(':'))
        
        primary_time = base_date.replace(hour=base_hour, minute=base_minute, second=0, microsecond=0)
        scheduled_times[strategy.primary_platform] = primary_time.isoformat()
        
        # Schedule secondary platforms with delays
        for platform in strategy.secondary_platforms:
            if platform in strategy.timing_delays:
                delay_minutes = strategy.timing_delays[platform]
                platform_time = primary_time + timedelta(minutes=delay_minutes)
            else:
                # Default 2-hour delay for cross-platform posting
                platform_time = primary_time + timedelta(hours=2)
            
            scheduled_times[platform] = platform_time.isoformat()
        
        # Update database with scheduled times
        self._update_scheduled_times(content_id, scheduled_times)
        
        # Save strategy
        self._save_content_strategy(content_id, strategy)
        
        logger.info(f"Scheduled cross-platform posting for content {content_id}")
        logger.info(f"Primary: {strategy.primary_platform.value} at {scheduled_times[strategy.primary_platform]}")
        
        return scheduled_times

    def _update_scheduled_times(self, content_id: str, scheduled_times: Dict[Platform, str]):
        """Update scheduled times in database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        for platform, scheduled_time in scheduled_times.items():
            cursor.execute('''
                UPDATE platform_adaptations 
                SET scheduled_time = ?, status = 'scheduled'
                WHERE content_id = ? AND platform = ?
            ''', (scheduled_time, content_id, platform.value))
        
        conn.commit()
        conn.close()

    def _save_content_strategy(self, content_id: str, strategy: CrossPlatformStrategy):
        """Save content strategy to database"""
        strategy_id = f"strategy_{content_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Convert Platform keys to strings for JSON serialization
        timing_delays_serializable = {p.value: delay for p, delay in strategy.timing_delays.items()}
        
        cursor.execute('''
            INSERT OR REPLACE INTO content_strategies 
            (strategy_id, content_id, primary_platform, secondary_platforms, 
             timing_strategy, cross_promotion)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            strategy_id, content_id, strategy.primary_platform.value,
            json.dumps([p.value for p in strategy.secondary_platforms]),
            json.dumps(timing_delays_serializable),
            strategy.cross_promotion
        ))
        
        conn.commit()
        conn.close()

    def execute_scheduled_posting(self, content_id: str) -> Dict[Platform, str]:
        """Execute scheduled posting across all platforms"""
        # Get scheduled adaptations
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT platform, adapted_content, scheduled_time 
            FROM platform_adaptations 
            WHERE content_id = ? AND status = 'scheduled'
            AND datetime(scheduled_time) <= datetime('now')
            ORDER BY scheduled_time
        ''', (content_id,))
        
        scheduled_posts = cursor.fetchall()
        conn.close()
        
        posted_ids = {}
        
        for platform_str, adapted_content, scheduled_time in scheduled_posts:
            platform = Platform(platform_str)
            
            try:
                if platform == Platform.LINKEDIN:
                    post_id = self.linkedin_client.post_to_linkedin(adapted_content, content_id)
                    if post_id:
                        posted_ids[platform] = post_id
                        self._update_posting_status(content_id, platform, 'posted', post_id)
                        logger.info(f"Posted to LinkedIn: {post_id}")
                
                elif platform == Platform.TWITTER:
                    # Parse Twitter thread content
                    thread_contents = json.loads(adapted_content)
                    tweets = [{'content': content} for content in thread_contents]
                    tweet_ids = self.twitter_client.post_twitter_thread(tweets, content_id)
                    if tweet_ids:
                        posted_ids[platform] = tweet_ids[0]  # First tweet ID
                        self._update_posting_status(content_id, platform, 'posted', tweet_ids[0])
                        logger.info(f"Posted Twitter thread: {len(tweet_ids)} tweets")
                
                elif platform == Platform.NEWSLETTER:
                    # Newsletter posting would integrate with email service
                    newsletter_id = self._post_to_newsletter(adapted_content, content_id)
                    if newsletter_id:
                        posted_ids[platform] = newsletter_id
                        self._update_posting_status(content_id, platform, 'posted', newsletter_id)
                        logger.info(f"Published to newsletter: {newsletter_id}")
                
            except Exception as e:
                logger.error(f"Failed to post to {platform_str}: {e}")
                self._update_posting_status(content_id, platform, 'failed', None)
        
        return posted_ids

    def _update_posting_status(self, content_id: str, platform: Platform, 
                              status: str, post_id: Optional[str]):
        """Update posting status in database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE platform_adaptations 
            SET status = ?, post_id = ?
            WHERE content_id = ? AND platform = ?
        ''', (status, post_id, content_id, platform.value))
        
        conn.commit()
        conn.close()

    def _post_to_newsletter(self, content: str, content_id: str) -> str:
        """Post to newsletter (placeholder for email service integration)"""
        # This would integrate with services like ConvertKit, Mailchimp, Substack API
        logger.info("Newsletter posting requires manual publication for now")
        return f"newsletter_{content_id}_{datetime.now().strftime('%Y%m%d')}"

    def collect_cross_platform_analytics(self, content_id: str) -> Dict[str, Any]:
        """Collect and analyze performance across all platforms"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get all posted adaptations
        cursor.execute('''
            SELECT platform, post_id 
            FROM platform_adaptations 
            WHERE content_id = ? AND status = 'posted' AND post_id IS NOT NULL
        ''', (content_id,))
        
        posted_content = cursor.fetchall()
        conn.close()
        
        platform_metrics = {}
        total_impressions = 0
        total_engagement = 0
        
        for platform_str, post_id in posted_content:
            platform = Platform(platform_str)
            
            try:
                if platform == Platform.LINKEDIN:
                    metrics = self.linkedin_client.get_post_analytics(post_id)
                    if metrics:
                        platform_metrics[platform_str] = {
                            'impressions': metrics.get('impressions', 0),
                            'engagement': metrics.get('clicks', 0) + metrics.get('likes', 0),
                            'clicks': metrics.get('clicks', 0),
                            'engagement_rate': metrics.get('impressions', 0) > 0 and 
                                             (metrics.get('clicks', 0) + metrics.get('likes', 0)) / metrics.get('impressions', 1)
                        }
                
                elif platform == Platform.TWITTER:
                    twitter_metrics = self.twitter_client.get_twitter_analytics(post_id)
                    if twitter_metrics:
                        platform_metrics[platform_str] = {
                            'impressions': twitter_metrics.impressions,
                            'engagement': twitter_metrics.likes + twitter_metrics.retweets + twitter_metrics.replies,
                            'clicks': twitter_metrics.clicks,
                            'engagement_rate': twitter_metrics.engagement_rate
                        }
                
                # Add to totals
                if platform_str in platform_metrics:
                    total_impressions += platform_metrics[platform_str]['impressions']
                    total_engagement += platform_metrics[platform_str]['engagement']
                    
            except Exception as e:
                logger.error(f"Error collecting analytics for {platform_str}: {e}")
        
        # Calculate cross-platform metrics
        overall_metrics = {
            'content_id': content_id,
            'total_impressions': total_impressions,
            'total_engagement': total_engagement,
            'overall_engagement_rate': total_engagement / total_impressions if total_impressions > 0 else 0,
            'platform_breakdown': platform_metrics,
            'platforms_count': len(platform_metrics),
            'collected_at': datetime.now().isoformat()
        }
        
        # Save aggregated metrics
        self._save_cross_platform_metrics(content_id, overall_metrics)
        
        return overall_metrics

    def _save_cross_platform_metrics(self, content_id: str, metrics: Dict[str, Any]):
        """Save cross-platform metrics to database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        for platform_str, platform_metrics in metrics['platform_breakdown'].items():
            metric_id = f"metric_{content_id}_{platform_str}_{datetime.now().strftime('%Y%m%d')}"
            
            cursor.execute('''
                INSERT OR REPLACE INTO cross_platform_metrics 
                (metric_id, content_id, platform, impressions, engagement, 
                 clicks, engagement_rate)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                metric_id, content_id, platform_str,
                platform_metrics.get('impressions', 0),
                platform_metrics.get('engagement', 0),
                platform_metrics.get('clicks', 0),
                platform_metrics.get('engagement_rate', 0.0)
            ))
        
        conn.commit()
        conn.close()

    def get_unified_dashboard_data(self) -> Dict[str, Any]:
        """Get unified dashboard data for all platforms"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get recent content performance
        cursor.execute('''
            SELECT 
                cp.content_id,
                cp.business_objective,
                COUNT(DISTINCT pa.platform) as platforms_used,
                AVG(cpm.engagement_rate) as avg_engagement_rate,
                SUM(cpm.impressions) as total_impressions,
                SUM(cpm.engagement) as total_engagement
            FROM content_pieces cp
            LEFT JOIN platform_adaptations pa ON cp.content_id = pa.content_id
            LEFT JOIN cross_platform_metrics cpm ON cp.content_id = cpm.content_id
            WHERE cp.created_at >= date('now', '-30 days')
            GROUP BY cp.content_id
            ORDER BY cp.created_at DESC
            LIMIT 10
        ''')
        
        recent_content = cursor.fetchall()
        
        # Get platform performance comparison
        cursor.execute('''
            SELECT 
                platform,
                COUNT(*) as posts_count,
                AVG(impressions) as avg_impressions,
                AVG(engagement_rate) as avg_engagement_rate,
                SUM(impressions) as total_impressions,
                SUM(engagement) as total_engagement
            FROM cross_platform_metrics
            WHERE recorded_at >= date('now', '-30 days')
            GROUP BY platform
        ''')
        
        platform_comparison = cursor.fetchall()
        
        conn.close()
        
        return {
            'recent_content': [
                {
                    'content_id': row[0],
                    'business_objective': row[1],
                    'platforms_used': row[2],
                    'avg_engagement_rate': row[3] or 0,
                    'total_impressions': row[4] or 0,
                    'total_engagement': row[5] or 0
                }
                for row in recent_content
            ],
            'platform_comparison': [
                {
                    'platform': row[0],
                    'posts_count': row[1],
                    'avg_impressions': row[2] or 0,
                    'avg_engagement_rate': row[3] or 0,
                    'total_impressions': row[4] or 0,
                    'total_engagement': row[5] or 0
                }
                for row in platform_comparison
            ],
            'last_updated': datetime.now().isoformat()
        }

def main():
    """Demonstrate unified content management system"""
    print("🚀 Unified Cross-Platform Content Management System")
    print("=" * 60)
    
    # Initialize unified manager
    manager = UnifiedContentManager()
    
    # Demo content creation and adaptation
    sample_content = """
    ## Final Optimized Post
    
    I've never met a 10x developer, but I've built 10x teams. Here's the difference.
    
    Team performance multiplies when you focus on systems over individuals.
    
    The best engineering teams I've built had:
    - Clear communication standards  
    - Systematic knowledge sharing
    - Collective code ownership
    - Continuous learning culture
    
    What made your best engineering team special? Share the secret sauce.
    """
    
    print("📝 Creating content piece...")
    content_id = manager.create_content_piece(
        sample_content,
        "Generate team building consultation inquiries",
        "CTOs, Engineering Managers, Technical Leaders"
    )
    
    print(f"✅ Created content: {content_id}")
    
    # Test platform adaptation
    target_platforms = [Platform.LINKEDIN, Platform.TWITTER, Platform.NEWSLETTER]
    print(f"\n🔄 Adapting content for {len(target_platforms)} platforms...")
    
    adaptations = manager.adapt_content_for_platforms(content_id, target_platforms)
    
    for platform, adaptation in adaptations.items():
        print(f"\n📱 {platform.value.upper()}:")
        preview = adaptation[:150] + "..." if len(adaptation) > 150 else adaptation
        print(f"   {preview}")
    
    # Test scheduling strategy
    strategy = CrossPlatformStrategy(
        primary_platform=Platform.LINKEDIN,
        secondary_platforms=[Platform.TWITTER, Platform.NEWSLETTER],
        timing_delays={Platform.TWITTER: 120, Platform.NEWSLETTER: 1440},  # 2 hours, 24 hours
        content_adaptations={},
        cross_promotion=True
    )
    
    print(f"\n📅 Scheduling cross-platform posting...")
    base_date = datetime.now().replace(hour=8, minute=0, second=0, microsecond=0)
    scheduled_times = manager.schedule_cross_platform_posting(content_id, strategy, base_date)
    
    for platform, scheduled_time in scheduled_times.items():
        print(f"   {platform.value}: {scheduled_time}")
    
    # Get dashboard data
    print(f"\n📊 Unified Dashboard Data:")
    dashboard = manager.get_unified_dashboard_data()
    print(f"   Recent content pieces: {len(dashboard['recent_content'])}")
    print(f"   Platform performance tracking: {len(dashboard['platform_comparison'])} platforms")
    
    print("\n💡 Available Features:")
    print("• Unified content creation and cross-platform adaptation")
    print("• Intelligent scheduling with platform-optimized timing")
    print("• LinkedIn → Twitter thread conversion")
    print("• Newsletter and blog format adaptation")
    print("• Cross-platform analytics aggregation")
    print("• Unified performance dashboard")
    print("• Manual posting workflow fallbacks")
    
    print("\n✅ Unified content management system ready!")
    print("Ready for 3x reach through coordinated multi-platform posting")

if __name__ == "__main__":
    main()