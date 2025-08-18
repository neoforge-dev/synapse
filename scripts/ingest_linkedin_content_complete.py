#!/usr/bin/env python3
"""
Complete LinkedIn Content Ingestion Script
Processes ALL LinkedIn data including posts, engagement metrics, and extracts comprehensive content
"""

import pandas as pd
import json
import re
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any
import sys
import os

# Add the project root to the path
sys.path.append(str(Path(__file__).parent.parent))

def extract_ideas_and_beliefs(text: str) -> Dict[str, List[str]]:
    """Enhanced extraction of ideas, beliefs, and preferences from post text"""
    ideas = []
    beliefs = []
    preferences = []
    
    # Enhanced patterns for beliefs/opinions
    belief_patterns = [
        r"I believe that[^.!?]*[.!?]",
        r"In my opinion[^.!?]*[.!?]", 
        r"I think[^.!?]*[.!?]",
        r"My experience shows[^.!?]*[.!?]",
        r"I've learned that[^.!?]*[.!?]",
        r"The truth is[^.!?]*[.!?]",
        r"What I've discovered[^.!?]*[.!?]",
        r"After \d+ years[^.!?]*[.!?]",
        r"I've found that[^.!?]*[.!?]",
        r"I've come to realize[^.!?]*[.!?]",
        r"I've observed that[^.!?]*[.!?]"
    ]
    
    # Enhanced patterns for preferences
    preference_patterns = [
        r"I prefer[^.!?]*[.!?]",
        r"I choose[^.!?]*[.!?]",
        r"My approach[^.!?]*[.!?]",
        r"I recommend[^.!?]*[.!?]",
        r"I suggest[^.!?]*[.!?]",
        r"Instead of[^.!?]*[.!?]",
        r"Rather than[^.!?]*[.!?]",
        r"I always[^.!?]*[.!?]",
        r"I tend to[^.!?]*[.!?]"
    ]
    
    # Extract beliefs
    for pattern in belief_patterns:
        matches = re.finditer(pattern, text, re.IGNORECASE | re.DOTALL)
        for match in matches:
            belief = match.group().strip()
            if len(belief) > 20:  # Filter out very short matches
                beliefs.append(belief)
    
    # Extract preferences  
    for pattern in preference_patterns:
        matches = re.finditer(pattern, text, re.IGNORECASE | re.DOTALL)
        for match in matches:
            pref = match.group().strip()
            if len(pref) > 20:  # Filter out very short matches
                preferences.append(pref)
    
    # Enhanced technical ideas extraction
    tech_terms = [
        "Python", "FastAPI", "Django", "architecture", "scaling", "microservices", 
        "monolith", "technical debt", "CTO", "leadership", "startup", "scaleup",
        "engineering", "DevOps", "cloud", "performance", "database", "API",
        "React", "JavaScript", "TypeScript", "Docker", "Kubernetes", "AWS",
        "Azure", "GCP", "CI/CD", "testing", "agile", "product management",
        "software development", "code review", "refactoring", "optimization"
    ]
    
    sentences = re.split(r'[.!?]+', text)
    for sentence in sentences:
        sentence = sentence.strip()
        if any(term.lower() in sentence.lower() for term in tech_terms) and len(sentence) > 30:
            ideas.append(sentence)
    
    return {
        "ideas": ideas[:10],  # Limit to avoid duplication
        "beliefs": beliefs[:5],
        "preferences": preferences[:5]
    }

def extract_personal_stories(text: str) -> List[Dict[str, Any]]:
    """Enhanced extraction of personal stories and experiences"""
    stories = []
    
    # Enhanced story patterns
    story_patterns = [
        r"Three years ago[^.!?]*[.!?]",
        r"Last week[^.!?]*[.!?]",
        r"Recently[^.!?]*[.!?]",
        r"In my experience[^.!?]*[.!?]",
        r"I once worked[^.!?]*[.!?]",
        r"At my previous[^.!?]*[.!?]",
        r"When I was at[^.!?]*[.!?]",
        r"During my time[^.!?]*[.!?]",
        r"I remember[^.!?]*[.!?]",
        r"Picture this[^.!?]*[.!?]",
        r"A few months ago[^.!?]*[.!?]",
        r"Earlier this year[^.!?]*[.!?]",
        r"Back when I[^.!?]*[.!?]",
        r"I found myself[^.!?]*[.!?]",
        r"There was a time[^.!?]*[.!?]"
    ]
    
    for pattern in story_patterns:
        matches = re.finditer(pattern, text, re.IGNORECASE | re.DOTALL)
        for match in matches:
            story_text = match.group().strip()
            if len(story_text) > 50:  # Only substantial stories
                stories.append({
                    "story_snippet": story_text,
                    "story_type": "experience",
                    "pattern_matched": pattern.replace(r"[^.!?]*[.!?]", "")
                })
    
    return stories[:3]  # Limit to avoid duplication

def extract_technical_insights(text: str) -> List[str]:
    """Enhanced extraction of technical insights and patterns"""
    insights = []
    
    # Enhanced technical insight patterns
    insight_patterns = [
        r"The key is[^.!?]*[.!?]",
        r"What matters most[^.!?]*[.!?]",
        r"The difference between[^.!?]*[.!?]",
        r"The problem with[^.!?]*[.!?]",
        r"The solution is[^.!?]*[.!?]",
        r"What works best[^.!?]*[.!?]",
        r"I've found that[^.!?]*[.!?]",
        r"The secret to[^.!?]*[.!?]",
        r"The biggest mistake[^.!?]*[.!?]",
        r"Here's what changed[^.!?]*[.!?]",
        r"This led to[^.!?]*[.!?]"
    ]
    
    for pattern in insight_patterns:
        matches = re.finditer(pattern, text, re.IGNORECASE | re.DOTALL)
        for match in matches:
            insight = match.group().strip()
            if len(insight) > 30:
                insights.append(insight)
    
    return insights[:5]  # Limit to avoid duplication

def extract_engagement_patterns(row: pd.Series) -> Dict[str, Any]:
    """Extract engagement insights from LinkedIn post metrics"""
    return {
        "impressions": int(row.get('numImpressions', 0)),
        "reactions": int(row.get('numReactions', 0)),
        "comments": int(row.get('numComments', 0)),
        "shares": int(row.get('numShares', 0)),
        "engagement_rate": float(row.get('numEngagementRate', 0)),
        "created_at": row.get('createdAt (TZ=Europe/Bucharest)', ''),
        "hashtags": row.get('hashtags', ''),
        "urn": row.get('urn', '')
    }

def analyze_high_performing_content(content_list: List[Dict]) -> Dict[str, Any]:
    """Analyze patterns in high-performing LinkedIn content"""
    
    # Sort by engagement rate
    sorted_content = sorted(content_list, 
                          key=lambda x: x.get('engagement', {}).get('engagement_rate', 0), 
                          reverse=True)
    
    top_performers = sorted_content[:20]  # Top 20 posts
    
    # Extract patterns from top performers
    top_ideas = []
    top_beliefs = []
    top_stories = []
    top_hashtags = []
    
    for post in top_performers:
        extracted = post.get('extracted_content', {})
        top_ideas.extend(extracted.get('ideas', []))
        top_beliefs.extend(extracted.get('beliefs', []))
        top_stories.extend(extracted.get('personal_stories', []))
        
        hashtags = post.get('engagement', {}).get('hashtags', '')
        if hashtags:
            top_hashtags.append(hashtags)
    
    return {
        "high_performing_posts_count": len(top_performers),
        "avg_engagement_rate": sum(p.get('engagement', {}).get('engagement_rate', 0) for p in top_performers) / len(top_performers),
        "top_performing_ideas": top_ideas[:20],
        "top_performing_beliefs": top_beliefs[:10],
        "top_performing_stories": top_stories[:10],
        "common_hashtags": top_hashtags[:10]
    }

def process_complete_linkedin_data():
    """Process ALL LinkedIn data from stats file"""
    
    data_dir = Path("./data")
    output_dir = data_dir / "linkedin_processed"
    output_dir.mkdir(exist_ok=True)
    
    # Process the comprehensive LinkedIn stats file
    stats_file = data_dir / "linkedin_posts_stats.csv"
    
    if not stats_file.exists():
        print(f"ERROR: {stats_file} not found!")
        return []
    
    print(f"Processing complete LinkedIn dataset from {stats_file}")
    
    # Read with proper error handling
    try:
        df = pd.read_csv(stats_file)
        print(f"Loaded {len(df)} LinkedIn entries")
    except Exception as e:
        print(f"Error reading CSV: {e}")
        return []
    
    all_content = []
    processed_count = 0
    
    for idx, row in df.iterrows():
        # Skip entries without meaningful text content
        if pd.isna(row.get('text')) or len(str(row.get('text', ''))) < 50:
            continue
            
        post_text = str(row['text'])
        
        # Extract all content types
        ideas_beliefs = extract_ideas_and_beliefs(post_text)
        stories = extract_personal_stories(post_text)
        insights = extract_technical_insights(post_text)
        engagement = extract_engagement_patterns(row)
        
        content_item = {
            "source": "linkedin_complete_dataset",
            "post_id": row.get('urn', f'post_{idx}'),
            "text": post_text,
            "engagement": engagement,
            "extracted_content": {
                "ideas": ideas_beliefs["ideas"],
                "beliefs": ideas_beliefs["beliefs"],
                "preferences": ideas_beliefs["preferences"],
                "personal_stories": stories,
                "technical_insights": insights
            }
        }
        
        all_content.append(content_item)
        processed_count += 1
        
        if processed_count % 50 == 0:
            print(f"Processed {processed_count} posts...")
    
    print(f"Processed {processed_count} LinkedIn posts with meaningful content")
    
    # Analyze high-performing content patterns
    performance_analysis = analyze_high_performing_content(all_content)
    
    # Save complete processed content
    output_file = output_dir / "linkedin_complete_extracted_content.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(all_content, f, indent=2, ensure_ascii=False)
    
    # Save performance analysis
    analysis_file = output_dir / "linkedin_performance_analysis.json"
    with open(analysis_file, 'w', encoding='utf-8') as f:
        json.dump(performance_analysis, f, indent=2, ensure_ascii=False)
    
    print(f"Complete dataset saved to {output_file}")
    print(f"Performance analysis saved to {analysis_file}")
    
    # Create enhanced Synapse documents
    create_enhanced_synapse_documents(all_content, performance_analysis, output_dir)
    
    return all_content

def create_enhanced_synapse_documents(content: List[Dict], analysis: Dict, output_dir: Path):
    """Create enhanced structured documents for Synapse ingestion"""
    
    # Aggregate all content
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
    
    # Remove duplicates while preserving order
    def deduplicate_list(lst):
        seen = set()
        result = []
        for item in lst:
            if isinstance(item, dict):
                item_str = item.get('story_snippet', str(item))
            else:
                item_str = str(item)
            if item_str not in seen:
                seen.add(item_str)
                result.append(item)
        return result
    
    all_ideas = deduplicate_list(all_ideas)
    all_beliefs = deduplicate_list(all_beliefs)
    all_preferences = deduplicate_list(all_preferences)
    all_stories = deduplicate_list(all_stories)
    all_insights = deduplicate_list(all_insights)
    
    # Create comprehensive ideas and beliefs document
    ideas_doc = f"""# Bogdan's Complete Professional Ideas and Beliefs
## Extracted from Full LinkedIn Dataset ({len(content)} posts)

### Core Professional Ideas ({len(all_ideas)} total)
{chr(10).join(f"- {idea}" for idea in all_ideas[:100])}

### Personal Beliefs and Opinions ({len(all_beliefs)} total)
{chr(10).join(f"- {belief}" for belief in all_beliefs)}

### Professional Preferences and Approaches ({len(all_preferences)} total)
{chr(10).join(f"- {pref}" for pref in all_preferences)}

### Technical Insights and Patterns ({len(all_insights)} total)
{chr(10).join(f"- {insight}" for insight in all_insights)}

### High-Performance Content Analysis
**Average engagement rate of top performers:** {analysis.get('avg_engagement_rate', 0):.4f}

**Top performing ideas:**
{chr(10).join(f"- {idea}" for idea in analysis.get('top_performing_ideas', [])[:10])}

**Most effective beliefs:**
{chr(10).join(f"- {belief}" for belief in analysis.get('top_performing_beliefs', []))}

This document contains authentic professional perspectives extracted from Bogdan's complete LinkedIn dataset for use in content creation and voice consistency.
"""
    
    # Create enhanced personal stories document
    stories_doc = f"""# Bogdan's Complete Professional Stories Collection
## Extracted from Full LinkedIn Dataset

### Professional Experience Stories ({len(all_stories)} total)
{chr(10).join(f"- {story['story_snippet']}" for story in all_stories[:50])}

### High-Performing Stories
These stories generated the highest engagement:
{chr(10).join(f"- {story['story_snippet']}" for story in analysis.get('top_performing_stories', []))}

### Story Patterns and Contexts
"""
    
    for story in all_stories[:30]:
        stories_doc += f"""
**Story**: {story['story_snippet']}
**Type**: {story['story_type']}
**Pattern**: {story['pattern_matched']}
---
"""
    
    # Save enhanced documents
    with open(output_dir / "complete_authentic_ideas_beliefs.md", 'w', encoding='utf-8') as f:
        f.write(ideas_doc)
    
    with open(output_dir / "complete_authentic_personal_stories.md", 'w', encoding='utf-8') as f:
        f.write(stories_doc)
    
    print(f"Enhanced Synapse documents created:")
    print(f"- Complete ideas and beliefs: {output_dir / 'complete_authentic_ideas_beliefs.md'}")
    print(f"- Complete personal stories: {output_dir / 'complete_authentic_personal_stories.md'}")
    print(f"- Total ideas extracted: {len(all_ideas)}")
    print(f"- Total beliefs extracted: {len(all_beliefs)}")
    print(f"- Total preferences extracted: {len(all_preferences)}")
    print(f"- Total personal stories: {len(all_stories)}")
    print(f"- Total technical insights: {len(all_insights)}")

if __name__ == "__main__":
    print("Complete LinkedIn Content Ingestion Starting...")
    content = process_complete_linkedin_data()
    print("Complete LinkedIn Content Ingestion Finished!")
    
    if content:
        print(f"\nFinal Summary:")
        print(f"- Processed {len(content)} LinkedIn posts")
        print(f"- Ready for Synapse ingestion")
        print(f"- Enhanced with performance analysis")
        print(f"- Contains comprehensive authentic voice data")