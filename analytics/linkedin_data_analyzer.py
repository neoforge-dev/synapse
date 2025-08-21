#!/usr/bin/env python3
"""
LinkedIn Data Analyzer for Business Development Automation

Analyzes comprehensive LinkedIn export data to extract:
- High-performing content patterns  
- Engagement optimization insights
- Controversial take effectiveness
- Business development opportunities
"""

import csv
import json
import logging
import pandas as pd
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Tuple
from dataclasses import dataclass, field
import re
from collections import defaultdict, Counter

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class LinkedInPost:
    """Represents a LinkedIn post with engagement metrics."""
    urn: str
    text: str
    post_type: str
    impressions: int
    views: int
    reactions: int
    comments: int
    shares: int
    engagement_rate: float
    hashtags: List[str]
    created_at: datetime
    link: str
    
    @property
    def total_engagement(self) -> int:
        return self.reactions + self.comments + self.shares

    @property
    def engagement_quality_score(self) -> float:
        """Calculate engagement quality prioritizing comments and shares over reactions."""
        if self.views == 0:
            return 0.0
        # Weight: comments=3, shares=2, reactions=1 (comments drive business value)
        weighted_engagement = (self.comments * 3) + (self.shares * 2) + self.reactions
        return weighted_engagement / self.views


@dataclass
class LinkedInComment:
    """Represents a LinkedIn comment."""
    date: datetime
    link: str
    message: str
    
    @property
    def is_controversial_discussion(self) -> bool:
        """Check if comment indicates controversial discussion."""
        controversial_indicators = [
            "don't think", "disagree", "however", "but", "actually",
            "wrong", "mistake", "not really", "interesting but"
        ]
        return any(indicator in self.message.lower() for indicator in controversial_indicators)

    @property
    def is_business_inquiry(self) -> bool:
        """Check if comment indicates potential business inquiry."""
        business_indicators = [
            "can you help", "looking for", "need advice", "consultant",
            "would love to discuss", "interested in", "hire", "work together"
        ]
        return any(indicator in self.message.lower() for indicator in business_indicators)


@dataclass
class ContentAnalysis:
    """Analysis results for content performance."""
    post: LinkedInPost
    controversial_elements: List[str] = field(default_factory=list)
    business_hooks: List[str] = field(default_factory=list)
    cta_effectiveness: str = "none"
    topic_category: str = "general"
    authenticity_score: float = 0.0
    consultation_potential: int = 0


class LinkedInDataAnalyzer:
    """Analyzes LinkedIn data for business development insights."""
    
    def __init__(self, data_dir: str):
        self.data_dir = Path(data_dir)
        self.posts: List[LinkedInPost] = []
        self.comments: List[LinkedInComment] = []
        self.reactions: List[Dict[str, Any]] = []
        
        # Load data
        self._load_post_stats()
        self._load_comments()
        self._load_reactions()
        
    def _load_post_stats(self):
        """Load post statistics from CSV."""
        post_stats_file = self.data_dir.parent / "LinkedInPost stats.csv"
        
        if not post_stats_file.exists():
            logger.warning(f"Post stats file not found: {post_stats_file}")
            return
            
        try:
            with open(post_stats_file, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if not row['urn']:  # Skip empty rows
                        continue
                        
                    # Parse hashtags
                    hashtags = []
                    if row['hashtags']:
                        hashtags = [tag.strip().replace('#', '').replace(',', '') 
                                  for tag in row['hashtags'].split() if tag.strip()]
                    
                    # Parse created_at
                    created_at = datetime.strptime(
                        row['createdAt (TZ=Europe/Bucharest)'], 
                        '%Y-%m-%d %H:%M:%S'
                    )
                    
                    post = LinkedInPost(
                        urn=row['urn'],
                        text=row['text'],
                        post_type=row['type'],
                        impressions=int(row['numImpressions'] or 0),
                        views=int(row['numViews'] or 0),
                        reactions=int(row['numReactions'] or 0),
                        comments=int(row['numComments'] or 0),
                        shares=int(row['numShares'] or 0),
                        engagement_rate=float(row['numEngagementRate'] or 0),
                        hashtags=hashtags,
                        created_at=created_at,
                        link=row['link']
                    )
                    
                    self.posts.append(post)
                    
            logger.info(f"Loaded {len(self.posts)} LinkedIn posts")
            
        except Exception as e:
            logger.error(f"Error loading post stats: {e}")
    
    def _load_comments(self):
        """Load comments from CSV."""
        comments_file = self.data_dir / "Comments.csv"
        
        if not comments_file.exists():
            logger.warning(f"Comments file not found: {comments_file}")
            return
            
        try:
            with open(comments_file, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if not row['Date']:  # Skip empty rows
                        continue
                        
                    date = datetime.strptime(row['Date'], '%Y-%m-%d %H:%M:%S')
                    
                    comment = LinkedInComment(
                        date=date,
                        link=row['Link'],
                        message=row['Message']
                    )
                    
                    self.comments.append(comment)
                    
            logger.info(f"Loaded {len(self.comments)} LinkedIn comments")
            
        except Exception as e:
            logger.error(f"Error loading comments: {e}")

    def _load_reactions(self):
        """Load reactions from CSV."""
        reactions_file = self.data_dir / "Reactions.csv"
        
        if not reactions_file.exists():
            logger.warning(f"Reactions file not found: {reactions_file}")
            return
            
        try:
            with open(reactions_file, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if not row['Date']:  # Skip empty rows
                        continue
                        
                    date = datetime.strptime(row['Date'], '%Y-%m-%d %H:%M:%S')
                    
                    reaction = {
                        'date': date,
                        'type': row['Type'],
                        'link': row['Link']
                    }
                    
                    self.reactions.append(reaction)
                    
            logger.info(f"Loaded {len(self.reactions)} LinkedIn reactions")
            
        except Exception as e:
            logger.error(f"Error loading reactions: {e}")

    def analyze_top_performing_content(self, top_n: int = 10) -> List[ContentAnalysis]:
        """Analyze top performing content by engagement quality."""
        # Sort posts by engagement quality score
        sorted_posts = sorted(self.posts, 
                            key=lambda p: p.engagement_quality_score, 
                            reverse=True)
        
        analyses = []
        for post in sorted_posts[:top_n]:
            analysis = ContentAnalysis(post=post)
            
            # Analyze controversial elements
            analysis.controversial_elements = self._identify_controversial_elements(post.text)
            
            # Analyze business hooks
            analysis.business_hooks = self._identify_business_hooks(post.text)
            
            # Analyze CTA effectiveness
            analysis.cta_effectiveness = self._analyze_cta_effectiveness(post)
            
            # Categorize topic
            analysis.topic_category = self._categorize_topic(post)
            
            # Calculate authenticity score
            analysis.authenticity_score = self._calculate_authenticity_score(post)
            
            # Estimate consultation potential
            analysis.consultation_potential = self._estimate_consultation_potential(post)
            
            analyses.append(analysis)
            
        return analyses

    def _identify_controversial_elements(self, text: str) -> List[str]:
        """Identify controversial elements in post text."""
        controversial_patterns = [
            r"don't believe.*",
            r"unpopular opinion",
            r"controversial.*take",
            r"most.*wrong about",
            r"myth.*",
            r"problem with.*",
            r"tired of.*",
            r"overrated.*",
            r"underrated.*",
            r"everyone.*but",
            r"truth.*",
            r"reality.*"
        ]
        
        elements = []
        text_lower = text.lower()
        
        for pattern in controversial_patterns:
            matches = re.findall(pattern, text_lower)
            elements.extend(matches)
            
        return elements

    def _identify_business_hooks(self, text: str) -> List[str]:
        """Identify business-oriented hooks in post text."""
        business_patterns = [
            r"scaling.*",
            r"building.*team",
            r"startup.*",
            r"technical.*debt",
            r"architecture.*",
            r"cto.*",
            r"tech.*leadership",
            r"engineering.*",
            r"system.*design",
            r"microservices.*",
            r"monolith.*"
        ]
        
        hooks = []
        text_lower = text.lower()
        
        for pattern in business_patterns:
            matches = re.findall(pattern, text_lower)
            hooks.extend(matches)
            
        return hooks

    def _analyze_cta_effectiveness(self, post: LinkedInPost) -> str:
        """Analyze call-to-action effectiveness."""
        cta_patterns = {
            'strong': [r'what.*think', r'share.*experience', r'love.*hear', r'comment.*below'],
            'medium': [r'like.*share', r'follow.*more', r'subscribe'],
            'weak': [r'thanks.*reading', r'hope.*helps']
        }
        
        text_lower = post.text.lower()
        
        for strength, patterns in cta_patterns.items():
            if any(re.search(pattern, text_lower) for pattern in patterns):
                return strength
                
        return 'none'

    def _categorize_topic(self, post: LinkedInPost) -> str:
        """Categorize post topic."""
        topic_keywords = {
            'technical_leadership': ['cto', 'tech lead', 'engineering manager', 'technical debt'],
            'architecture': ['microservices', 'monolith', 'architecture', 'system design'],
            'career_development': ['career', 'growth', 'learning', 'development'],
            'python_development': ['python', 'django', 'fastapi', 'backend'],
            'startup_scaling': ['startup', 'scaling', 'growth', 'team building'],
            'controversial_tech': ['myth', 'unpopular', 'wrong', 'truth about']
        }
        
        text_lower = post.text.lower()
        
        for topic, keywords in topic_keywords.items():
            if any(keyword in text_lower for keyword in keywords):
                return topic
                
        return 'general'

    def _calculate_authenticity_score(self, post: LinkedInPost) -> float:
        """Calculate authenticity score based on personal experience indicators."""
        authenticity_indicators = [
            'my experience', 'i learned', 'i discovered', 'i found',
            'in my case', 'personally', 'years ago', 'when i',
            'my journey', 'i believe', 'i think', 'my approach'
        ]
        
        text_lower = post.text.lower()
        matches = sum(1 for indicator in authenticity_indicators if indicator in text_lower)
        
        # Normalize score (max observed is typically 5-6 indicators)
        return min(matches / 6.0, 1.0)

    def _estimate_consultation_potential(self, post: LinkedInPost) -> int:
        """Estimate consultation inquiry potential based on engagement and topic."""
        base_potential = 0
        
        # High-value topics
        if any(topic in post.text.lower() for topic in 
               ['cto', 'scaling', 'architecture', 'technical debt', 'startup']):
            base_potential += 3
            
        # Engagement multiplier
        if post.comments > 20:
            base_potential += 2
        elif post.comments > 10:
            base_potential += 1
            
        # Controversial elements boost
        controversial_count = len(self._identify_controversial_elements(post.text))
        base_potential += min(controversial_count, 2)
        
        return base_potential

    def generate_insights_report(self) -> Dict[str, Any]:
        """Generate comprehensive insights report."""
        if not self.posts:
            return {"error": "No posts data available"}
            
        # Analyze top performers
        top_content = self.analyze_top_performing_content(10)
        
        # Overall statistics
        total_impressions = sum(p.impressions for p in self.posts)
        total_reactions = sum(p.reactions for p in self.posts)
        total_comments = sum(p.comments for p in self.posts)
        avg_engagement_rate = sum(p.engagement_rate for p in self.posts) / len(self.posts)
        
        # Topic performance
        topic_performance = defaultdict(list)
        for post in self.posts:
            category = self._categorize_topic(post)
            topic_performance[category].append(post.engagement_quality_score)
        
        topic_avg_performance = {
            topic: sum(scores) / len(scores) 
            for topic, scores in topic_performance.items()
        }
        
        # Controversial content analysis
        controversial_posts = [p for p in self.posts 
                             if self._identify_controversial_elements(p.text)]
        
        controversial_avg_engagement = (
            sum(p.engagement_quality_score for p in controversial_posts) / len(controversial_posts)
            if controversial_posts else 0
        )
        
        non_controversial_posts = [p for p in self.posts 
                                 if not self._identify_controversial_elements(p.text)]
        
        regular_avg_engagement = (
            sum(p.engagement_quality_score for p in non_controversial_posts) / len(non_controversial_posts)
            if non_controversial_posts else 0
        )
        
        # Business inquiry analysis
        business_comments = [c for c in self.comments if c.is_business_inquiry]
        controversial_comments = [c for c in self.comments if c.is_controversial_discussion]
        
        report = {
            "overview": {
                "total_posts": len(self.posts),
                "total_impressions": total_impressions,
                "total_reactions": total_reactions,
                "total_comments": total_comments,
                "average_engagement_rate": avg_engagement_rate,
                "analysis_date": datetime.now().isoformat()
            },
            "top_performing_content": [
                {
                    "text_preview": analysis.post.text[:200] + "...",
                    "engagement_quality_score": analysis.post.engagement_quality_score,
                    "total_engagement": analysis.post.total_engagement,
                    "controversial_elements": analysis.controversial_elements,
                    "business_hooks": analysis.business_hooks,
                    "cta_effectiveness": analysis.cta_effectiveness,
                    "topic_category": analysis.topic_category,
                    "authenticity_score": analysis.authenticity_score,
                    "consultation_potential": analysis.consultation_potential,
                    "link": analysis.post.link
                }
                for analysis in top_content
            ],
            "topic_performance": topic_avg_performance,
            "controversial_content_analysis": {
                "controversial_posts_count": len(controversial_posts),
                "controversial_avg_engagement": controversial_avg_engagement,
                "regular_avg_engagement": regular_avg_engagement,
                "controversial_boost_factor": (
                    controversial_avg_engagement / regular_avg_engagement
                    if regular_avg_engagement > 0 else 0
                )
            },
            "business_development_insights": {
                "total_business_inquiry_comments": len(business_comments),
                "total_controversial_discussion_comments": len(controversial_comments),
                "high_consultation_potential_posts": len([
                    a for a in top_content if a.consultation_potential >= 3
                ]),
                "estimated_monthly_consultation_inquiries": len(business_comments) * 2  # Extrapolation
            },
            "recommendations": self._generate_recommendations(top_content, controversial_avg_engagement, regular_avg_engagement)
        }
        
        return report

    def _generate_recommendations(self, top_content: List[ContentAnalysis], 
                                controversial_engagement: float, regular_engagement: float) -> List[str]:
        """Generate actionable recommendations."""
        recommendations = []
        
        # Controversial content recommendation
        if controversial_engagement > regular_engagement * 1.2:
            boost_factor = controversial_engagement / regular_engagement if regular_engagement > 0 else 0
            recommendations.append(
                f"Controversial content drives {boost_factor:.1f}x higher engagement. "
                "Integrate more contrarian technical opinions in Week 3 content."
            )
        
        # Topic recommendations
        high_performing_topics = [a.topic_category for a in top_content[:3]]
        if high_performing_topics:
            top_topic = Counter(high_performing_topics).most_common(1)[0][0]
            recommendations.append(
                f"Focus on '{top_topic}' content - consistently high engagement. "
                "Prioritize this topic in upcoming LinkedIn posts."
            )
        
        # Authenticity recommendations
        high_auth_posts = [a for a in top_content if a.authenticity_score > 0.5]
        if len(high_auth_posts) > len(top_content) * 0.6:
            recommendations.append(
                "Personal experience posts perform well. Continue sharing authentic "
                "journey stories and lessons learned."
            )
        
        # CTA recommendations
        strong_cta_posts = [a for a in top_content if a.cta_effectiveness == 'strong']
        if strong_cta_posts:
            recommendations.append(
                "Strong CTAs asking for opinions/experiences drive engagement. "
                "Use 'What's your experience?' style questions in all posts."
            )
        
        # Business development recommendations
        high_consult_posts = [a for a in top_content if a.consultation_potential >= 3]
        if high_consult_posts:
            recommendations.append(
                f"{len(high_consult_posts)} posts show high consultation potential. "
                "Amplify CTO/scaling/architecture content to drive business inquiries."
            )
            
        return recommendations

    def export_insights_for_automation(self, output_path: str):
        """Export insights in format suitable for business development automation."""
        report = self.generate_insights_report()
        
        # Create automation-ready format
        automation_data = {
            "linkedin_insights": {
                "controversial_boost_factor": report["controversial_content_analysis"].get("controversial_boost_factor", 1.0),
                "top_performing_topics": list(report["topic_performance"].keys()),
                "high_engagement_patterns": [
                    {
                        "pattern": "controversial_technical_opinions",
                        "effectiveness": report["controversial_content_analysis"].get("controversial_boost_factor", 1.0)
                    },
                    {
                        "pattern": "authentic_personal_experience", 
                        "effectiveness": sum(a["authenticity_score"] for a in report["top_performing_content"]) / len(report["top_performing_content"])
                    }
                ],
                "business_hooks": [],
                "consultation_triggers": []
            },
            "content_templates": [],
            "automation_parameters": {
                "optimal_posting_frequency": 3,  # Per week
                "controversial_content_ratio": 0.3,  # 30% controversial
                "authenticity_threshold": 0.5,
                "consultation_potential_threshold": 3
            }
        }
        
        # Extract business hooks and consultation triggers
        for analysis in report["top_performing_content"]:
            automation_data["linkedin_insights"]["business_hooks"].extend(analysis["business_hooks"])
            if analysis["consultation_potential"] >= 3:
                automation_data["linkedin_insights"]["consultation_triggers"].append({
                    "text_preview": analysis["text_preview"],
                    "elements": analysis["controversial_elements"] + analysis["business_hooks"]
                })
        
        # Create content templates from top performers
        for analysis in report["top_performing_content"][:5]:
            template = {
                "topic_category": analysis["topic_category"],
                "controversial_elements": analysis["controversial_elements"],
                "business_hooks": analysis["business_hooks"],
                "cta_style": analysis["cta_effectiveness"],
                "authenticity_score": analysis["authenticity_score"],
                "expected_consultation_potential": analysis["consultation_potential"]
            }
            automation_data["content_templates"].append(template)
        
        # Save to file
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(automation_data, f, indent=2, ensure_ascii=False, default=str)
            
        logger.info(f"Automation insights exported to {output_path}")
        return automation_data


def main():
    """Main execution function."""
    # Initialize analyzer
    data_dir = "/Users/bogdan/data/Complete_LinkedInDataExport_10-18-2024"
    analyzer = LinkedInDataAnalyzer(data_dir)
    
    # Generate insights report
    report = analyzer.generate_insights_report()
    
    # Save detailed report
    report_path = "/Users/bogdan/til/graph-rag-mcp/analytics/linkedin_insights_report.json"
    with open(report_path, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False, default=str)
    
    logger.info(f"Detailed insights report saved to {report_path}")
    
    # Export automation-ready data
    automation_path = "/Users/bogdan/til/graph-rag-mcp/analytics/linkedin_automation_data.json"
    automation_data = analyzer.export_insights_for_automation(automation_path)
    
    # Print summary
    print("\n🔍 LinkedIn Data Analysis Summary")
    print("=" * 50)
    print(f"📊 Analyzed {report['overview']['total_posts']} posts")
    print(f"💡 Total impressions: {report['overview']['total_impressions']:,}")
    print(f"❤️  Total reactions: {report['overview']['total_reactions']:,}")
    print(f"💬 Total comments: {report['overview']['total_comments']:,}")
    print(f"📈 Average engagement rate: {report['overview']['average_engagement_rate']:.1%}")
    
    if report['controversial_content_analysis']['controversial_boost_factor'] > 1:
        print(f"\n⚡ Controversial content boost: {report['controversial_content_analysis']['controversial_boost_factor']:.1f}x")
    
    print(f"\n🎯 High consultation potential posts: {report['business_development_insights']['high_consultation_potential_posts']}")
    print(f"💼 Estimated monthly inquiries: {report['business_development_insights']['estimated_monthly_consultation_inquiries']}")
    
    print("\n📋 Key Recommendations:")
    for i, rec in enumerate(report['recommendations'], 1):
        print(f"{i}. {rec}")
    
    return analyzer, report, automation_data


if __name__ == "__main__":
    main()