#!/usr/bin/env python3
"""
LinkedIn Content Ingestion Script
Extracts authentic ideas, beliefs, preferences, and personal stories from LinkedIn data
"""

import json
import re
import sys
from pathlib import Path
from typing import Any

import pandas as pd

# Add the project root to the path
sys.path.append(str(Path(__file__).parent.parent))

def extract_ideas_and_beliefs(text: str) -> dict[str, list[str]]:
    """Extract ideas, beliefs, and preferences from post text"""
    ideas = []
    beliefs = []
    preferences = []

    # Patterns for beliefs/opinions
    belief_patterns = [
        r"I believe that",
        r"In my opinion",
        r"I think",
        r"My experience shows",
        r"I've learned that",
        r"The truth is",
        r"What I've discovered",
        r"After \d+ years"
    ]

    # Patterns for preferences
    preference_patterns = [
        r"I prefer",
        r"I choose",
        r"My approach",
        r"I recommend",
        r"I suggest",
        r"Instead of.*I",
        r"Rather than.*I"
    ]

    # Extract beliefs
    for pattern in belief_patterns:
        matches = re.finditer(pattern + r"[^.!?]*[.!?]", text, re.IGNORECASE)
        for match in matches:
            beliefs.append(match.group().strip())

    # Extract preferences
    for pattern in preference_patterns:
        matches = re.finditer(pattern + r"[^.!?]*[.!?]", text, re.IGNORECASE)
        for match in matches:
            preferences.append(match.group().strip())

    # Extract general ideas (sentences with technical terms)
    tech_terms = [
        "Python", "FastAPI", "architecture", "scaling", "microservices",
        "monolith", "technical debt", "CTO", "leadership", "startup",
        "engineering", "DevOps", "cloud", "performance", "database"
    ]

    sentences = re.split(r'[.!?]+', text)
    for sentence in sentences:
        if any(term in sentence for term in tech_terms) and len(sentence.strip()) > 20:
            ideas.append(sentence.strip())

    return {
        "ideas": ideas,
        "beliefs": beliefs,
        "preferences": preferences
    }

def extract_personal_stories(text: str) -> list[dict[str, Any]]:
    """Extract personal stories and experiences"""
    stories = []

    # Story patterns
    story_patterns = [
        r"Three years ago",
        r"Last week",
        r"Recently",
        r"In my experience",
        r"I once worked",
        r"At my previous",
        r"When I was at",
        r"During my time",
        r"I remember",
        r"Picture this"
    ]

    for pattern in story_patterns:
        matches = re.finditer(pattern + r"[^.!?]*[.!?]", text, re.IGNORECASE)
        for match in matches:
            story_text = match.group().strip()
            if len(story_text) > 50:  # Only substantial stories
                stories.append({
                    "story_snippet": story_text,
                    "story_type": "experience",
                    "pattern_matched": pattern
                })

    return stories

def extract_technical_insights(text: str) -> list[str]:
    """Extract technical insights and patterns"""
    insights = []

    # Technical insight patterns
    insight_patterns = [
        r"The key is",
        r"What matters most",
        r"The difference between",
        r"The problem with",
        r"The solution is",
        r"What works best",
        r"I've found that",
        r"The secret to"
    ]

    for pattern in insight_patterns:
        matches = re.finditer(pattern + r"[^.!?]*[.!?]", text, re.IGNORECASE)
        for match in matches:
            insight = match.group().strip()
            if len(insight) > 30:
                insights.append(insight)

    return insights

def process_linkedin_posts():
    """Process LinkedIn posts and extract content for Synapse ingestion"""

    data_dir = Path("./data")
    output_dir = data_dir / "linkedin_processed"
    output_dir.mkdir(exist_ok=True)

    # Process LinkedIn post stats
    posts_stats_file = data_dir / "linkedin_posts_stats.csv"
    posts_content_files = [
        data_dir / "linkedin_posts_content.csv",
        data_dir / "linkedin_posts_content_2.csv"
    ]

    all_content = []

    # Process detailed posts with stats
    if posts_stats_file.exists():
        print(f"Processing LinkedIn post stats from {posts_stats_file}")
        df_stats = pd.read_csv(posts_stats_file)

        for _idx, row in df_stats.iterrows():
            if pd.notna(row['text']) and len(str(row['text'])) > 100:
                post_text = str(row['text'])

                # Extract content
                ideas_beliefs = extract_ideas_and_beliefs(post_text)
                stories = extract_personal_stories(post_text)
                insights = extract_technical_insights(post_text)

                content_item = {
                    "source": "linkedin_post_with_stats",
                    "created_at": row.get('createdAt (TZ=Europe/Bucharest)', ''),
                    "text": post_text,
                    "engagement": {
                        "impressions": row.get('numImpressions', 0),
                        "reactions": row.get('numReactions', 0),
                        "comments": row.get('numComments', 0),
                        "shares": row.get('numShares', 0),
                        "engagement_rate": row.get('numEngagementRate', 0)
                    },
                    "hashtags": row.get('hashtags', ''),
                    "extracted_content": {
                        "ideas": ideas_beliefs["ideas"],
                        "beliefs": ideas_beliefs["beliefs"],
                        "preferences": ideas_beliefs["preferences"],
                        "personal_stories": stories,
                        "technical_insights": insights
                    }
                }
                all_content.append(content_item)

    # Process additional posts content
    for content_file in posts_content_files:
        if content_file.exists():
            print(f"Processing LinkedIn content from {content_file}")
            df_content = pd.read_csv(content_file)

            for _idx, row in df_content.iterrows():
                if pd.notna(row['Text']) and len(str(row['Text'])) > 100:
                    post_text = str(row['Text'])

                    # Extract content
                    ideas_beliefs = extract_ideas_and_beliefs(post_text)
                    stories = extract_personal_stories(post_text)
                    insights = extract_technical_insights(post_text)

                    content_item = {
                        "source": f"linkedin_post_content_{content_file.name}",
                        "handle": row.get('Handle', ''),
                        "text": post_text,
                        "extracted_content": {
                            "ideas": ideas_beliefs["ideas"],
                            "beliefs": ideas_beliefs["beliefs"],
                            "preferences": ideas_beliefs["preferences"],
                            "personal_stories": stories,
                            "technical_insights": insights
                        }
                    }
                    all_content.append(content_item)

    # Save processed content
    output_file = output_dir / "linkedin_extracted_content.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(all_content, f, indent=2, ensure_ascii=False)

    print(f"Processed {len(all_content)} LinkedIn posts")
    print(f"Extracted content saved to {output_file}")

    # Create summaries for Synapse ingestion
    create_synapse_documents(all_content, output_dir)

    return all_content

def create_synapse_documents(content: list[dict], output_dir: Path):
    """Create structured documents for Synapse ingestion"""

    # Aggregate ideas and beliefs
    all_ideas = []
    all_beliefs = []
    all_preferences = []
    all_stories = []
    all_insights = []

    for item in content:
        extracted = item["extracted_content"]
        all_ideas.extend(extracted["ideas"])
        all_beliefs.extend(extracted["beliefs"])
        all_preferences.extend(extracted["preferences"])
        all_stories.extend(extracted["personal_stories"])
        all_insights.extend(extracted["technical_insights"])

    # Create ideas and beliefs document
    ideas_doc = f"""# Bogdan's Professional Ideas and Beliefs
## Extracted from LinkedIn Content

### Core Professional Ideas
{chr(10).join(f"- {idea}" for idea in all_ideas[:50])}

### Personal Beliefs and Opinions
{chr(10).join(f"- {belief}" for belief in all_beliefs[:30])}

### Professional Preferences and Approaches
{chr(10).join(f"- {pref}" for pref in all_preferences[:30])}

### Technical Insights and Patterns
{chr(10).join(f"- {insight}" for insight in all_insights[:40])}

This document contains authentic professional perspectives extracted from LinkedIn content for use in content creation and voice consistency.
"""

    # Create personal stories document
    stories_doc = f"""# Bogdan's Personal Professional Stories
## Extracted from LinkedIn Content

### Professional Experience Stories
{chr(10).join(f"- {story['story_snippet']}" for story in all_stories[:30])}

### Story Patterns and Contexts
"""

    for story in all_stories[:20]:
        stories_doc += f"""
**Story**: {story['story_snippet']}
**Type**: {story['story_type']}
**Pattern**: {story['pattern_matched']}
---
"""

    # Save documents
    with open(output_dir / "authentic_ideas_beliefs.md", 'w', encoding='utf-8') as f:
        f.write(ideas_doc)

    with open(output_dir / "authentic_personal_stories.md", 'w', encoding='utf-8') as f:
        f.write(stories_doc)

    print("Created Synapse documents:")
    print(f"- Ideas and beliefs: {output_dir / 'authentic_ideas_beliefs.md'}")
    print(f"- Personal stories: {output_dir / 'authentic_personal_stories.md'}")

if __name__ == "__main__":
    print("LinkedIn Content Ingestion Starting...")
    content = process_linkedin_posts()
    print("LinkedIn Content Ingestion Complete!")

    # Print summary statistics
    total_ideas = sum(len(item["extracted_content"]["ideas"]) for item in content)
    total_beliefs = sum(len(item["extracted_content"]["beliefs"]) for item in content)
    total_stories = sum(len(item["extracted_content"]["personal_stories"]) for item in content)
    total_insights = sum(len(item["extracted_content"]["technical_insights"]) for item in content)

    print("\nExtraction Summary:")
    print(f"- Total ideas extracted: {total_ideas}")
    print(f"- Total beliefs extracted: {total_beliefs}")
    print(f"- Total personal stories: {total_stories}")
    print(f"- Total technical insights: {total_insights}")
