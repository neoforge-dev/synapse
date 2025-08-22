#!/usr/bin/env python3
"""
LinkedIn Data Ingestion Pipeline for Synapse
Processes LinkedIn posts and comments to extract beliefs, preferences, stories, and insights.
"""

import csv
import re
from collections import defaultdict
from datetime import datetime
from pathlib import Path


class LinkedInDataProcessor:
    def __init__(self, posts_csv_path, comments_csv_path, output_dir):
        self.posts_csv_path = Path(posts_csv_path)
        self.comments_csv_path = Path(comments_csv_path)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Categories for organizing content
        self.categories = {
            'technical_beliefs': [],
            'personal_stories': [],
            'development_practices': [],
            'career_insights': [],
            'architecture_opinions': [],
            'tool_preferences': [],
            'management_philosophy': [],
            'learning_approaches': [],
            'controversial_takes': [],
            'engagement_winners': []
        }

        # Keywords for categorization
        self.category_keywords = {
            'technical_beliefs': ['architecture', 'design pattern', 'best practice', 'principle', 'philosophy', 'approach'],
            'personal_stories': ['years ago', 'my experience', 'I found', 'I learned', 'my journey', 'when I', 'I discovered'],
            'development_practices': ['testing', 'deployment', 'CI/CD', 'code review', 'development process', 'workflow'],
            'career_insights': ['career', 'advice', 'transition', 'growth', 'skill', 'learning', 'experience'],
            'architecture_opinions': ['microservices', 'monolith', 'distributed', 'scalability', 'performance', 'system'],
            'tool_preferences': ['Python', 'Django', 'FastAPI', 'Kubernetes', 'Docker', 'AWS', 'database'],
            'management_philosophy': ['team', 'management', 'leadership', 'hiring', 'culture', 'meeting'],
            'learning_approaches': ['book', 'tutorial', 'course', 'learning', 'study', 'education'],
            'controversial_takes': ['unpopular opinion', 'controversial', 'disagree', 'wrong', 'myth', 'everyone says'],
            'engagement_winners': []  # Will be populated based on metrics
        }

    def clean_text(self, text):
        """Clean and normalize text content."""
        if not text:
            return ""

        # Remove excessive whitespace and normalize
        text = re.sub(r'\n+', '\n', text)
        text = re.sub(r'\s+', ' ', text)
        text = text.strip()

        # Fix common LinkedIn formatting issues
        text = text.replace('""', '"')
        text = re.sub(r'(\d+)️⃣', r'\1.', text)  # Fix numbered lists

        return text

    def extract_engagement_metrics(self, row):
        """Extract and normalize engagement metrics."""
        try:
            return {
                'impressions': int(row.get('numImpressions', 0) or 0),
                'views': int(row.get('numViews', 0) or 0),
                'reactions': int(row.get('numReactions', 0) or 0),
                'comments': int(row.get('numComments', 0) or 0),
                'shares': int(row.get('numShares', 0) or 0),
                'engagement_rate': float(row.get('numEngagementRate', 0) or 0)
            }
        except (ValueError, TypeError):
            return {
                'impressions': 0, 'views': 0, 'reactions': 0,
                'comments': 0, 'shares': 0, 'engagement_rate': 0.0
            }

    def categorize_content(self, text, metrics):
        """Categorize content based on keywords and engagement."""
        text_lower = text.lower()
        categories = []

        # Check keyword-based categories
        for category, keywords in self.category_keywords.items():
            if category == 'engagement_winners':
                continue

            if any(keyword in text_lower for keyword in keywords):
                categories.append(category)

        # Add engagement winners (top 10% by engagement rate)
        if metrics['engagement_rate'] > 0.01:  # Above 1% engagement rate
            categories.append('engagement_winners')

        # Add controversial takes if engagement is high but mixed sentiment
        if (metrics['comments'] > 20 and metrics['engagement_rate'] > 0.005 and
            any(word in text_lower for word in ['but', 'however', 'disagree', 'wrong', 'myth'])):
            categories.append('controversial_takes')

        return categories if categories else ['general_insights']

    def extract_beliefs_and_preferences(self, text):
        """Extract explicit beliefs, opinions, and preferences."""
        beliefs = []
        preferences = []

        # Belief indicators
        belief_patterns = [
            r"I believe (?:that )?(.+?)(?:\.|$)",
            r"In my opinion,? (.+?)(?:\.|$)",
            r"My philosophy is (.+?)(?:\.|$)",
            r"I think (?:that )?(.+?)(?:\.|$)",
            r"The key is (.+?)(?:\.|$)",
            r"What matters most is (.+?)(?:\.|$)"
        ]

        for pattern in belief_patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                belief = match.group(1).strip()
                if len(belief) > 10 and len(belief) < 200:
                    beliefs.append(belief)

        # Preference indicators
        preference_patterns = [
            r"I prefer (.+?) (?:over|to|than) (.+?)(?:\.|$)",
            r"(.+?) is better than (.+?)(?:\.|$)",
            r"Rather than (.+?), I (.+?)(?:\.|$)",
            r"Instead of (.+?), (?:I|we) should (.+?)(?:\.|$)"
        ]

        for pattern in preference_patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                if len(match.groups()) >= 2:
                    preferences.append({
                        'preferred': match.group(1).strip() if len(match.groups()) > 1 else match.group(1).strip(),
                        'over': match.group(2).strip() if len(match.groups()) > 1 else ""
                    })

        return beliefs, preferences

    def process_posts(self):
        """Process LinkedIn posts CSV and extract valuable content."""
        processed_posts = []

        print(f"Processing LinkedIn posts from {self.posts_csv_path}")

        with open(self.posts_csv_path, encoding='utf-8') as file:
            reader = csv.DictReader(file)

            for row in reader:
                text = self.clean_text(row.get('text', ''))

                if not text or len(text) < 100:  # Skip very short posts
                    continue

                metrics = self.extract_engagement_metrics(row)
                categories = self.categorize_content(text, metrics)
                beliefs, preferences = self.extract_beliefs_and_preferences(text)

                post_data = {
                    'id': row.get('urn', '').replace('urn:li:activity:', ''),
                    'text': text,
                    'created_at': row.get('createdAt (TZ=Europe/Bucharest)', ''),
                    'hashtags': row.get('hashtags', '').split(',') if row.get('hashtags') else [],
                    'metrics': metrics,
                    'categories': categories,
                    'beliefs': beliefs,
                    'preferences': preferences,
                    'type': row.get('type', ''),
                    'link': row.get('link', '')
                }

                processed_posts.append(post_data)

                # Add to categorical collections
                for category in categories:
                    if category in self.categories:
                        self.categories[category].append(post_data)

        print(f"Processed {len(processed_posts)} LinkedIn posts")
        return processed_posts

    def process_comments(self):
        """Process LinkedIn comments CSV and extract insights."""
        processed_comments = []

        print(f"Processing LinkedIn comments from {self.comments_csv_path}")

        with open(self.comments_csv_path, encoding='utf-8') as file:
            reader = csv.DictReader(file)

            for row in reader:
                message = self.clean_text(row.get('Message', ''))

                if not message or len(message) < 20:  # Skip very short comments
                    continue

                beliefs, preferences = self.extract_beliefs_and_preferences(message)

                comment_data = {
                    'date': row.get('Date', ''),
                    'message': message,
                    'link': row.get('Link', ''),
                    'beliefs': beliefs,
                    'preferences': preferences
                }

                processed_comments.append(comment_data)

        print(f"Processed {len(processed_comments)} LinkedIn comments")
        return processed_comments

    def create_categorical_documents(self, posts, comments):
        """Create organized markdown documents by category."""

        # Create comprehensive belief and preference documents
        self.create_beliefs_document(posts, comments)
        self.create_preferences_document(posts, comments)

        # Create category-specific documents
        for category, posts_list in self.categories.items():
            if not posts_list:
                continue

            filename = f"linkedin_{category}.md"
            filepath = self.output_dir / filename

            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(f"# LinkedIn {category.replace('_', ' ').title()}\n\n")
                f.write(f"*Extracted from {len(posts_list)} LinkedIn posts*\n\n")
                f.write(f"**Category**: {category}\n")
                f.write(f"**Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
                f.write("---\n\n")

                # Sort by engagement rate for most impactful content first
                posts_list.sort(key=lambda x: x['metrics']['engagement_rate'], reverse=True)

                for i, post in enumerate(posts_list[:50], 1):  # Top 50 posts per category
                    f.write(f"## Post {i}: {post['created_at'][:10] if post['created_at'] else 'Unknown Date'}\n\n")
                    f.write(f"**Engagement**: {post['metrics']['reactions']} reactions, ")
                    f.write(f"{post['metrics']['comments']} comments, ")
                    f.write(f"{post['metrics']['shares']} shares ")
                    f.write(f"({post['metrics']['engagement_rate']:.3%} rate)\n\n")

                    if post['hashtags']:
                        f.write(f"**Tags**: {', '.join(post['hashtags'])}\n\n")

                    f.write("**Content**:\n")
                    f.write(f"{post['text']}\n\n")

                    if post['beliefs']:
                        f.write("**Extracted Beliefs**:\n")
                        for belief in post['beliefs']:
                            f.write(f"- {belief}\n")
                        f.write("\n")

                    if post['preferences']:
                        f.write("**Extracted Preferences**:\n")
                        for pref in post['preferences']:
                            if isinstance(pref, dict):
                                f.write(f"- Prefers: {pref['preferred']} over {pref['over']}\n")
                            else:
                                f.write(f"- {pref}\n")
                        f.write("\n")

                    f.write("---\n\n")

            print(f"Created {filepath}")

    def create_beliefs_document(self, posts, comments):
        """Create a comprehensive beliefs and philosophy document."""
        filepath = self.output_dir / "linkedin_core_beliefs_and_philosophy.md"

        # Collect all beliefs
        all_beliefs = []
        for post in posts:
            for belief in post['beliefs']:
                all_beliefs.append({
                    'belief': belief,
                    'context': post['text'][:200] + "...",
                    'date': post['created_at'],
                    'engagement': post['metrics']['engagement_rate']
                })

        for comment in comments:
            for belief in comment['beliefs']:
                all_beliefs.append({
                    'belief': belief,
                    'context': comment['message'],
                    'date': comment['date'],
                    'engagement': 0  # Comments don't have engagement metrics
                })

        # Sort by engagement and remove duplicates
        seen = set()
        unique_beliefs = []
        for item in sorted(all_beliefs, key=lambda x: x['engagement'], reverse=True):
            belief_key = item['belief'].lower().strip()
            if belief_key not in seen and len(belief_key) > 10:
                seen.add(belief_key)
                unique_beliefs.append(item)

        with open(filepath, 'w', encoding='utf-8') as f:
            f.write("# Core Beliefs and Technical Philosophy\n\n")
            f.write("*Extracted from LinkedIn posts and comments*\n\n")
            f.write(f"**Total unique beliefs identified**: {len(unique_beliefs)}\n")
            f.write(f"**Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            f.write("---\n\n")

            f.write("## High-Impact Beliefs (by engagement)\n\n")

            for i, item in enumerate(unique_beliefs[:100], 1):  # Top 100 beliefs
                f.write(f"### {i}. {item['belief']}\n\n")
                f.write(f"**Date**: {item['date'][:10] if item['date'] else 'Unknown'}\n")
                f.write(f"**Engagement**: {item['engagement']:.3%}\n\n")
                f.write(f"**Context**: {item['context']}\n\n")
                f.write("---\n\n")

        print(f"Created {filepath} with {len(unique_beliefs)} unique beliefs")

    def create_preferences_document(self, posts, comments):
        """Create a comprehensive preferences and opinions document."""
        filepath = self.output_dir / "linkedin_technical_preferences.md"

        # Collect all preferences
        all_preferences = []
        for post in posts:
            for pref in post['preferences']:
                all_preferences.append({
                    'preference': pref,
                    'context': post['text'][:200] + "...",
                    'date': post['created_at'],
                    'engagement': post['metrics']['engagement_rate']
                })

        for comment in comments:
            for pref in comment['preferences']:
                all_preferences.append({
                    'preference': pref,
                    'context': comment['message'],
                    'date': comment['date'],
                    'engagement': 0
                })

        with open(filepath, 'w', encoding='utf-8') as f:
            f.write("# Technical Preferences and Opinions\n\n")
            f.write("*Extracted from LinkedIn posts and comments*\n\n")
            f.write(f"**Total preferences identified**: {len(all_preferences)}\n")
            f.write(f"**Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            f.write("---\n\n")

            for i, item in enumerate(sorted(all_preferences, key=lambda x: x['engagement'], reverse=True)[:50], 1):
                f.write(f"## Preference {i}\n\n")

                if isinstance(item['preference'], dict):
                    f.write(f"**Preferred**: {item['preference']['preferred']}\n")
                    f.write(f"**Over**: {item['preference']['over']}\n\n")
                else:
                    f.write(f"**Preference**: {item['preference']}\n\n")

                f.write(f"**Date**: {item['date'][:10] if item['date'] else 'Unknown'}\n")
                f.write(f"**Engagement**: {item['engagement']:.3%}\n\n")
                f.write(f"**Context**: {item['context']}\n\n")
                f.write("---\n\n")

        print(f"Created {filepath} with {len(all_preferences)} preferences")

    def create_master_summary(self, posts, comments):
        """Create a master summary document with key insights."""
        filepath = self.output_dir / "linkedin_master_summary.md"

        # Calculate summary statistics
        total_posts = len(posts)
        total_comments = len(comments)
        total_engagement = sum(p['metrics']['engagement_rate'] for p in posts)
        avg_engagement = total_engagement / total_posts if total_posts > 0 else 0

        # Top performing posts
        top_posts = sorted(posts, key=lambda x: x['metrics']['engagement_rate'], reverse=True)[:10]

        # Most common categories
        category_counts = defaultdict(int)
        for post in posts:
            for category in post['categories']:
                category_counts[category] += 1

        with open(filepath, 'w', encoding='utf-8') as f:
            f.write("# LinkedIn Content Analysis - Master Summary\n\n")
            f.write(f"**Analysis Date**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            f.write("---\n\n")

            f.write("## Content Statistics\n\n")
            f.write(f"- **Total Posts Analyzed**: {total_posts:,}\n")
            f.write(f"- **Total Comments Analyzed**: {total_comments:,}\n")
            f.write(f"- **Average Engagement Rate**: {avg_engagement:.3%}\n")
            f.write(f"- **Total Content Categories**: {len(self.categories)}\n\n")

            f.write("## Content Categories Distribution\n\n")
            for category, count in sorted(category_counts.items(), key=lambda x: x[1], reverse=True):
                f.write(f"- **{category.replace('_', ' ').title()}**: {count} posts\n")
            f.write("\n")

            f.write("## Top 10 Highest Engagement Posts\n\n")
            for i, post in enumerate(top_posts, 1):
                f.write(f"### {i}. {post['created_at'][:10] if post['created_at'] else 'Unknown Date'}\n")
                f.write(f"**Engagement**: {post['metrics']['engagement_rate']:.3%} | ")
                f.write(f"Reactions: {post['metrics']['reactions']} | ")
                f.write(f"Comments: {post['metrics']['comments']}\n\n")
                f.write(f"**Preview**: {post['text'][:200]}...\n\n")
                f.write("---\n\n")

        print(f"Created master summary: {filepath}")

    def run(self):
        """Execute the full LinkedIn data processing pipeline."""
        print("🚀 Starting LinkedIn Data Processing Pipeline")
        print("=" * 60)

        # Process data
        posts = self.process_posts()
        comments = self.process_comments()

        # Create documents
        self.create_categorical_documents(posts, comments)
        self.create_master_summary(posts, comments)

        print("\n" + "=" * 60)
        print("✅ LinkedIn Data Processing Complete!")
        print(f"📁 Output directory: {self.output_dir}")
        print(f"📊 Processed: {len(posts)} posts, {len(comments)} comments")
        print("🔍 Generated categorical documents for Synapse ingestion")


def main():
    """Main execution function."""
    posts_csv = "/Users/bogdan/data/LinkedInPost stats.csv"
    comments_csv = "/Users/bogdan/data/Complete_LinkedInDataExport_10-18-2024/Comments.csv"
    output_dir = "/Users/bogdan/til/graph-rag-mcp/linkedin_processed_data"

    processor = LinkedInDataProcessor(posts_csv, comments_csv, output_dir)
    processor.run()


if __name__ == "__main__":
    main()
