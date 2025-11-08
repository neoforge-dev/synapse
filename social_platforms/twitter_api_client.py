#!/usr/bin/env python3
"""
Twitter/X API Client for Cross-Platform Content Distribution
Production-ready Twitter integration with thread support and analytics
"""

import json
import logging
import os
import sqlite3
from dataclasses import dataclass
from datetime import datetime
from typing import Any

import requests

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@dataclass
class TwitterAPICredentials:
    """Twitter API credentials structure"""
    api_key: str
    api_secret: str
    access_token: str
    access_token_secret: str
    bearer_token: str

@dataclass
class TweetData:
    """Tweet data structure for posting"""
    content: str
    thread_position: int = 1
    total_threads: int = 1
    media_urls: list[str] | None = None
    reply_to_tweet_id: str | None = None

@dataclass
class TwitterMetrics:
    """Twitter engagement metrics"""
    tweet_id: str
    impressions: int
    retweets: int
    likes: int
    replies: int
    clicks: int
    engagement_rate: float
    posted_at: str

class TwitterAPIClient:
    """Twitter API client with thread support and analytics tracking"""

    def __init__(self, credentials_file: str = "twitter_credentials.json"):
        self.credentials_file = credentials_file
        self.credentials = None
        self.api_base_url = "https://api.twitter.com/2"
        self.api_available = self._load_credentials()
        self.db_path = "twitter_analytics.db"
        self._init_database()

    def _load_credentials(self) -> bool:
        """Load Twitter API credentials"""
        try:
            if os.path.exists(self.credentials_file):
                with open(self.credentials_file) as f:
                    cred_data = json.load(f)
                    self.credentials = TwitterAPICredentials(**cred_data)
                logger.info("Twitter API credentials loaded successfully")
                return True
            else:
                logger.info("No Twitter credentials found - manual posting mode")
                return False
        except Exception as e:
            logger.error(f"Error loading Twitter credentials: {e}")
            return False

    def _init_database(self):
        """Initialize Twitter analytics database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS twitter_posts (
                tweet_id TEXT PRIMARY KEY,
                post_id TEXT NOT NULL,
                content TEXT NOT NULL,
                thread_position INTEGER DEFAULT 1,
                total_threads INTEGER DEFAULT 1,
                impressions INTEGER DEFAULT 0,
                retweets INTEGER DEFAULT 0,
                likes INTEGER DEFAULT 0,
                replies INTEGER DEFAULT 0,
                clicks INTEGER DEFAULT 0,
                engagement_rate REAL DEFAULT 0.0,
                posted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS twitter_threads (
                thread_id TEXT PRIMARY KEY,
                post_id TEXT NOT NULL,
                total_tweets INTEGER NOT NULL,
                first_tweet_id TEXT,
                thread_performance REAL DEFAULT 0.0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Create indexes for performance
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_twitter_posts_post_id ON twitter_posts (post_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_twitter_posts_engagement ON twitter_posts (engagement_rate DESC)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_twitter_threads_performance ON twitter_threads (thread_performance DESC)')

        conn.commit()
        conn.close()
        logger.info("Twitter analytics database initialized")

    def _get_auth_headers(self) -> dict[str, str]:
        """Get authentication headers for Twitter API"""
        if not self.credentials or not self.credentials.bearer_token:
            raise Exception("No valid bearer token available")

        return {
            'Authorization': f'Bearer {self.credentials.bearer_token}',
            'Content-Type': 'application/json'
        }

    def convert_linkedin_to_twitter_thread(self, linkedin_content: str, post_id: str) -> list[TweetData]:
        """Convert LinkedIn post to Twitter thread format"""
        # Extract actual content from LinkedIn markdown
        content = self._extract_linkedin_content(linkedin_content)

        # Split into tweets (280 char limit with buffer for links/hashtags)
        max_tweet_length = 250
        tweets = []

        lines = content.split('\n')
        current_tweet = ""
        thread_count = 1

        for line in lines:
            line = line.strip()
            if not line:
                continue

            # Start new tweet if adding line would exceed limit
            if len(current_tweet + '\n' + line) > max_tweet_length and current_tweet:
                tweets.append(TweetData(
                    content=current_tweet.strip(),
                    thread_position=thread_count,
                    total_threads=0  # Will be updated later
                ))
                current_tweet = line
                thread_count += 1
            else:
                current_tweet += ('\n' if current_tweet else '') + line

        # Add final tweet
        if current_tweet:
            tweets.append(TweetData(
                content=current_tweet.strip(),
                thread_position=thread_count,
                total_threads=0
            ))

        # Update total thread count
        total_threads = len(tweets)
        for tweet in tweets:
            tweet.total_threads = total_threads

        # Add thread indicators for multi-tweet threads
        if total_threads > 1:
            for i, tweet in enumerate(tweets):
                if i == 0:
                    tweet.content += f"\n\n🧵 Thread ({i+1}/{total_threads})"
                else:
                    tweet.content += f"\n\n🧵 {i+1}/{total_threads}"

        return tweets

    def _extract_linkedin_content(self, raw_content: str) -> str:
        """Extract clean content from LinkedIn post format"""
        if "## Final Optimized Post" in raw_content:
            lines = raw_content.split('\n')
            post_start = None

            for i, line in enumerate(lines):
                if "## Final Optimized Post" in line:
                    post_start = i + 1
                    break

            if post_start:
                post_content = []
                for line in lines[post_start:]:
                    if line.strip() and not line.startswith('**Content Strategy') and not line.startswith('---'):
                        post_content.append(line)
                    elif line.startswith('---') or line.startswith('## Content Strategy'):
                        break

                return '\n'.join(post_content).strip()

        return raw_content

    def post_twitter_thread(self, tweets: list[TweetData], post_id: str) -> list[str]:
        """Post Twitter thread and track analytics"""
        if not self.api_available:
            logger.warning("Twitter API not available - using manual posting workflow")
            return self._handle_manual_twitter_posting(tweets, post_id)

        posted_tweet_ids = []
        thread_id = f"thread_{post_id}_{datetime.now().strftime('%Y%m%d%H%M%S')}"

        try:
            headers = self._get_auth_headers()

            for i, tweet in enumerate(tweets):
                # Prepare tweet data
                tweet_data = {
                    "text": tweet.content
                }

                # Add reply reference for thread continuation
                if i > 0 and posted_tweet_ids:
                    tweet_data["reply"] = {
                        "in_reply_to_tweet_id": posted_tweet_ids[-1]
                    }

                # Post tweet
                response = requests.post(
                    f"{self.api_base_url}/tweets",
                    headers=headers,
                    json=tweet_data
                )
                response.raise_for_status()

                result = response.json()
                tweet_id = result['data']['id']
                posted_tweet_ids.append(tweet_id)

                # Store in database
                self._save_twitter_post(tweet_id, post_id, tweet.content, i+1, len(tweets))

                logger.info(f"Posted tweet {i+1}/{len(tweets)}: {tweet_id}")

            # Create thread record
            self._save_twitter_thread(thread_id, post_id, len(tweets), posted_tweet_ids[0])

            logger.info(f"Successfully posted Twitter thread: {len(posted_tweet_ids)} tweets")
            return posted_tweet_ids

        except Exception as e:
            logger.error(f"Error posting Twitter thread: {e}")
            return self._handle_manual_twitter_posting(tweets, post_id)

    def _handle_manual_twitter_posting(self, tweets: list[TweetData], post_id: str) -> list[str]:
        """Handle manual Twitter posting workflow"""
        print("\n" + "="*80)
        print("🐦 MANUAL TWITTER POSTING REQUIRED")
        print("="*80)
        print(f"Twitter API not available. Please post this {len(tweets)}-tweet thread manually:")
        print("-"*80)

        manual_tweet_ids = []
        for i, tweet in enumerate(tweets):
            print(f"\n📱 TWEET {i+1}/{len(tweets)}:")
            print("-" * 40)
            print(tweet.content)
            print("-" * 40)

            if i == 0:
                print("1. Copy the content above")
                print("2. Post as new tweet on Twitter/X")
                print("3. Get the tweet URL and extract the ID")
            else:
                print("1. Copy the content above")
                print("2. Reply to the previous tweet in the thread")
                print("3. Get the reply tweet URL and extract the ID")

        print("\n" + "="*80)
        confirmation = input("Confirm that thread was posted manually (y/N): ").lower().strip()

        if confirmation == 'y':
            # Generate manual tweet IDs for tracking
            base_id = datetime.now().strftime('%Y%m%d%H%M%S')
            for i in range(len(tweets)):
                manual_id = f"manual_{post_id}_{base_id}_{i+1}"
                manual_tweet_ids.append(manual_id)
                self._save_twitter_post(manual_id, post_id, tweets[i].content, i+1, len(tweets))

            thread_id = f"manual_thread_{post_id}_{base_id}"
            self._save_twitter_thread(thread_id, post_id, len(tweets), manual_tweet_ids[0])

            logger.info(f"Manual Twitter thread confirmed: {len(manual_tweet_ids)} tweets")
            return manual_tweet_ids
        else:
            logger.info("Manual Twitter posting cancelled")
            return []

    def _save_twitter_post(self, tweet_id: str, post_id: str, content: str,
                          position: int, total: int):
        """Save Twitter post to database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            INSERT OR REPLACE INTO twitter_posts 
            (tweet_id, post_id, content, thread_position, total_threads)
            VALUES (?, ?, ?, ?, ?)
        ''', (tweet_id, post_id, content, position, total))

        conn.commit()
        conn.close()

    def _save_twitter_thread(self, thread_id: str, post_id: str, total_tweets: int,
                           first_tweet_id: str):
        """Save Twitter thread to database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            INSERT OR REPLACE INTO twitter_threads 
            (thread_id, post_id, total_tweets, first_tweet_id)
            VALUES (?, ?, ?, ?)
        ''', (thread_id, post_id, total_tweets, first_tweet_id))

        conn.commit()
        conn.close()

    def get_twitter_analytics(self, tweet_id: str) -> TwitterMetrics | None:
        """Get analytics for a specific tweet"""
        if not self.api_available:
            return self._get_manual_twitter_analytics(tweet_id)

        try:
            headers = self._get_auth_headers()

            # Get tweet metrics (requires Twitter API v2 with appropriate permissions)
            url = f"{self.api_base_url}/tweets/{tweet_id}"
            params = {
                "tweet.fields": "public_metrics,created_at",
                "expansions": "author_id"
            }

            response = requests.get(url, headers=headers, params=params)
            response.raise_for_status()

            data = response.json()
            tweet_data = data['data']
            metrics = tweet_data['public_metrics']

            # Calculate engagement rate
            impressions = metrics.get('impression_count', 0)
            total_engagement = (
                metrics.get('retweet_count', 0) +
                metrics.get('like_count', 0) +
                metrics.get('reply_count', 0) +
                metrics.get('quote_count', 0)
            )
            engagement_rate = total_engagement / impressions if impressions > 0 else 0

            twitter_metrics = TwitterMetrics(
                tweet_id=tweet_id,
                impressions=impressions,
                retweets=metrics.get('retweet_count', 0),
                likes=metrics.get('like_count', 0),
                replies=metrics.get('reply_count', 0),
                clicks=0,  # Not available in public metrics
                engagement_rate=engagement_rate,
                posted_at=tweet_data['created_at']
            )

            # Update database
            self._update_twitter_metrics(twitter_metrics)

            return twitter_metrics

        except Exception as e:
            logger.error(f"Error getting Twitter analytics for {tweet_id}: {e}")
            return self._get_manual_twitter_analytics(tweet_id)

    def _get_manual_twitter_analytics(self, tweet_id: str) -> TwitterMetrics:
        """Get manual Twitter analytics input"""
        print(f"\n📊 MANUAL TWITTER ANALYTICS for {tweet_id}")
        print("-" * 50)
        print("Please collect these metrics from Twitter Analytics:")

        metrics_data = {}
        metrics = [
            ("impressions", "Impressions"),
            ("retweets", "Retweets"),
            ("likes", "Likes"),
            ("replies", "Replies"),
            ("clicks", "Link clicks")
        ]

        for metric, description in metrics:
            while True:
                try:
                    value = input(f"{description}: ").strip()
                    metrics_data[metric] = int(value) if value else 0
                    break
                except ValueError:
                    print("Please enter a valid number or press Enter for 0")

        engagement_rate = (
            (metrics_data['retweets'] + metrics_data['likes'] + metrics_data['replies']) /
            metrics_data['impressions']
        ) if metrics_data['impressions'] > 0 else 0

        twitter_metrics = TwitterMetrics(
            tweet_id=tweet_id,
            impressions=metrics_data['impressions'],
            retweets=metrics_data['retweets'],
            likes=metrics_data['likes'],
            replies=metrics_data['replies'],
            clicks=metrics_data['clicks'],
            engagement_rate=engagement_rate,
            posted_at=datetime.now().isoformat()
        )

        self._update_twitter_metrics(twitter_metrics)
        return twitter_metrics

    def _update_twitter_metrics(self, metrics: TwitterMetrics):
        """Update Twitter metrics in database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            UPDATE twitter_posts 
            SET impressions = ?, retweets = ?, likes = ?, replies = ?, 
                clicks = ?, engagement_rate = ?, last_updated = CURRENT_TIMESTAMP
            WHERE tweet_id = ?
        ''', (metrics.impressions, metrics.retweets, metrics.likes, metrics.replies,
              metrics.clicks, metrics.engagement_rate, metrics.tweet_id))

        conn.commit()
        conn.close()

    def get_thread_performance(self, post_id: str) -> dict[str, Any]:
        """Get comprehensive thread performance analytics"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Get thread overview
        cursor.execute('''
            SELECT thread_id, total_tweets, first_tweet_id 
            FROM twitter_threads 
            WHERE post_id = ?
        ''', (post_id,))

        thread_data = cursor.fetchone()
        if not thread_data:
            return {"error": "Thread not found"}

        thread_id, total_tweets, first_tweet_id = thread_data

        # Get individual tweet performance
        cursor.execute('''
            SELECT tweet_id, thread_position, impressions, retweets, likes, 
                   replies, engagement_rate 
            FROM twitter_posts 
            WHERE post_id = ? 
            ORDER BY thread_position
        ''', (post_id,))

        tweets = cursor.fetchall()
        conn.close()

        # Calculate thread metrics
        total_impressions = sum(tweet[2] for tweet in tweets)
        total_engagement = sum(tweet[3] + tweet[4] + tweet[5] for tweet in tweets)
        avg_engagement_rate = sum(tweet[6] for tweet in tweets) / len(tweets) if tweets else 0

        return {
            "thread_id": thread_id,
            "post_id": post_id,
            "total_tweets": total_tweets,
            "first_tweet_id": first_tweet_id,
            "total_impressions": total_impressions,
            "total_engagement": total_engagement,
            "average_engagement_rate": avg_engagement_rate,
            "individual_tweets": [
                {
                    "tweet_id": tweet[0],
                    "position": tweet[1],
                    "impressions": tweet[2],
                    "total_engagement": tweet[3] + tweet[4] + tweet[5],
                    "engagement_rate": tweet[6]
                }
                for tweet in tweets
            ]
        }

def setup_twitter_credentials():
    """Interactive setup for Twitter API credentials"""
    print("🐦 Twitter API Setup")
    print("=" * 40)
    print("To use automated Twitter posting, you need:")
    print("1. Twitter Developer Account")
    print("2. Twitter API v2 credentials")
    print("3. Bearer token for read/write access")
    print()

    api_key = input("Enter your Twitter API Key (or press Enter to skip): ").strip()

    if api_key:
        api_secret = input("Enter your Twitter API Secret: ").strip()
        access_token = input("Enter your Access Token: ").strip()
        access_token_secret = input("Enter your Access Token Secret: ").strip()
        bearer_token = input("Enter your Bearer Token: ").strip()

        if all([api_secret, access_token, access_token_secret, bearer_token]):
            credentials = {
                'api_key': api_key,
                'api_secret': api_secret,
                'access_token': access_token,
                'access_token_secret': access_token_secret,
                'bearer_token': bearer_token
            }

            with open('twitter_credentials.json', 'w') as f:
                json.dump(credentials, f, indent=2)

            print("✅ Twitter credentials saved!")
            print("Next steps:")
            print("1. Test the connection with get_user_profile()")
            print("2. Use automated thread posting features")
            return True

    print("⚠️  Skipping Twitter API setup - manual posting will be used")
    return False

def main():
    """Demonstrate Twitter API client"""
    print("🚀 Twitter/X API Client & Thread System")
    print("=" * 50)

    # Check if credentials exist
    if not os.path.exists('twitter_credentials.json'):
        print("⚠️  No Twitter credentials found - will demonstrate with manual mode")

    # Initialize API client
    twitter_client = TwitterAPIClient()

    if twitter_client.api_available:
        print("✅ Twitter API ready for automated posting")
    else:
        print("⚠️  Twitter API not available - manual posting mode active")

    # Test thread conversion
    sample_linkedin_content = """
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

    print("\n🧵 Converting LinkedIn post to Twitter thread...")
    tweets = twitter_client.convert_linkedin_to_twitter_thread(sample_linkedin_content, "test_post")

    print(f"📱 Generated {len(tweets)} tweets:")
    for i, tweet in enumerate(tweets, 1):
        print(f"\nTweet {i}/{len(tweets)} ({len(tweet.content)} chars):")
        print("-" * 40)
        print(tweet.content[:100] + "..." if len(tweet.content) > 100 else tweet.content)

    print("\n💡 Available Features:")
    print("• LinkedIn to Twitter thread conversion")
    print("• Automated thread posting with proper reply chains")
    print("• Manual posting workflow (fallback)")
    print("• Comprehensive thread analytics and performance tracking")
    print("• Cross-platform content optimization")

    print("\n✅ Twitter integration system ready!")
    print(f"API Available: {twitter_client.api_available}")
    print("Ready for cross-platform content distribution")

if __name__ == "__main__":
    main()
