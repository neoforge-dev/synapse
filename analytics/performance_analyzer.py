#!/usr/bin/env python3
"""
Performance Analytics Enhancement System
Advanced analytics to identify content patterns that drive consultation inquiries
"""

import sqlite3
import json
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from dataclasses import dataclass
from typing import Dict, List, Optional, Any, Tuple
import logging
from pathlib import Path
import sys
import re
from collections import defaultdict, Counter

# Add business_development to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'business_development'))

from linkedin_posting_system import LinkedInBusinessDevelopmentEngine
from consultation_inquiry_detector import ConsultationInquiryDetector

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@dataclass
class ContentPattern:
    """Identified content pattern that drives performance"""
    pattern_id: str
    pattern_type: str  # hook_style, content_length, timing, topic, etc.
    pattern_value: str
    avg_engagement_rate: float
    avg_consultation_conversion: float
    sample_size: int
    confidence_score: float
    recommendation: str

@dataclass
class PerformancePrediction:
    """Predicted performance for content based on patterns"""
    predicted_engagement_rate: float
    predicted_consultation_requests: int
    confidence_interval: Tuple[float, float]
    key_success_factors: List[str]
    optimization_recommendations: List[str]

class PerformanceAnalyzer:
    """Advanced performance analytics for content optimization"""
    
    def __init__(self):
        self.business_engine = LinkedInBusinessDevelopmentEngine()
        self.inquiry_detector = ConsultationInquiryDetector()
        self.db_path = "performance_analytics.db"
        self.init_database()
        
    def init_database(self):
        """Initialize performance analytics database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Content patterns table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS content_patterns (
                pattern_id TEXT PRIMARY KEY,
                pattern_type TEXT,
                pattern_value TEXT,
                avg_engagement_rate REAL,
                avg_consultation_conversion REAL,
                sample_size INTEGER,
                confidence_score REAL,
                recommendation TEXT,
                identified_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Performance predictions table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS performance_predictions (
                prediction_id TEXT PRIMARY KEY,
                post_id TEXT,
                predicted_engagement_rate REAL,
                predicted_consultation_requests INTEGER,
                confidence_lower REAL,
                confidence_upper REAL,
                key_factors TEXT,  -- JSON array
                recommendations TEXT,  -- JSON array
                actual_engagement_rate REAL DEFAULT NULL,
                actual_consultation_requests INTEGER DEFAULT NULL,
                prediction_accuracy REAL DEFAULT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Content analysis table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS content_analysis (
                analysis_id TEXT PRIMARY KEY,
                post_id TEXT,
                word_count INTEGER,
                hook_type TEXT,
                cta_type TEXT,
                topic_category TEXT,
                technical_depth INTEGER,  -- 1-5 scale
                business_focus INTEGER,   -- 1-5 scale
                controversy_score INTEGER, -- 1-5 scale
                emoji_count INTEGER,
                hashtag_count INTEGER,
                question_count INTEGER,
                personal_story BOOLEAN,
                data_points INTEGER,
                code_snippets BOOLEAN,
                analyzed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        conn.commit()
        conn.close()
        logger.info("Performance analytics database initialized")
    
    def analyze_all_content(self):
        """Analyze all existing content to identify performance patterns"""
        conn = sqlite3.connect(self.business_engine.db_path)
        cursor = conn.cursor()
        
        # Get all posts with performance data
        cursor.execute('''
            SELECT post_id, content, day, actual_engagement_rate, 
                   consultation_requests, impressions, business_objective
            FROM linkedin_posts 
            WHERE impressions > 0
        ''')
        
        posts = cursor.fetchall()
        conn.close()
        
        analyzed_count = 0
        patterns = defaultdict(list)
        
        for post_id, content, day, engagement_rate, consultations, impressions, objective in posts:
            # Analyze content characteristics
            analysis = self._analyze_content_characteristics(post_id, content)
            self._save_content_analysis(analysis)
            
            # Extract performance data
            consultation_conversion = consultations / impressions if impressions > 0 else 0
            
            # Group by patterns
            patterns['day'].append((day, engagement_rate, consultation_conversion))
            patterns['hook_type'].append((analysis['hook_type'], engagement_rate, consultation_conversion))
            patterns['cta_type'].append((analysis['cta_type'], engagement_rate, consultation_conversion))
            patterns['topic_category'].append((analysis['topic_category'], engagement_rate, consultation_conversion))
            patterns['technical_depth'].append((analysis['technical_depth'], engagement_rate, consultation_conversion))
            
            analyzed_count += 1
        
        logger.info(f"Analyzed {analyzed_count} posts for performance patterns")
        
        # Identify significant patterns
        identified_patterns = self._identify_performance_patterns(patterns)
        
        # Save patterns to database
        for pattern in identified_patterns:
            self._save_content_pattern(pattern)
        
        return identified_patterns
    
    def _analyze_content_characteristics(self, post_id: str, content: str) -> Dict:
        """Analyze characteristics of content that affect performance"""
        
        # Extract actual post content (remove metadata)
        post_content = self._extract_post_content(content)
        
        analysis = {
            'analysis_id': f"analysis_{post_id}_{datetime.now().strftime('%Y%m%d%H%M%S')}",
            'post_id': post_id,
            'word_count': len(post_content.split()),
            'hook_type': self._identify_hook_type(post_content),
            'cta_type': self._identify_cta_type(post_content),
            'topic_category': self._identify_topic_category(post_content),
            'technical_depth': self._score_technical_depth(post_content),
            'business_focus': self._score_business_focus(post_content),
            'controversy_score': self._score_controversy_level(post_content),
            'emoji_count': len(re.findall(r'[^\w\s,.]', post_content)),
            'hashtag_count': len(re.findall(r'#\w+', post_content)),
            'question_count': post_content.count('?'),
            'personal_story': self._has_personal_story(post_content),
            'data_points': len(re.findall(r'\d+%|\$\d+|\d+[Kk]|\d+x', post_content)),
            'code_snippets': '```' in post_content or 'python' in post_content.lower()
        }
        
        return analysis
    
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
    
    def _identify_hook_type(self, content: str) -> str:
        """Identify the type of hook used in content"""
        first_line = content.split('\n')[0].lower()
        
        if 'controversial' in first_line or '🔥' in first_line:
            return 'controversial'
        elif 'story' in first_line or 'never' in first_line:
            return 'personal_story'
        elif any(stat in first_line for stat in ['%', 'stat', 'data', 'study']):
            return 'statistics'
        elif '?' in first_line:
            return 'question'
        elif any(word in first_line for word in ['shocking', 'surprising', 'brutal']):
            return 'shock_value'
        elif 'unpopular opinion' in first_line:
            return 'unpopular_opinion'
        else:
            return 'standard'
    
    def _identify_cta_type(self, content: str) -> str:
        """Identify the type of call-to-action used"""
        content_lower = content.lower()
        
        if 'dm me' in content_lower or 'message me' in content_lower:
            return 'direct_dm'
        elif 'let\'s discuss' in content_lower or 'happy to chat' in content_lower:
            return 'consultation_offer'
        elif 'share' in content_lower and 'comment' in content_lower:
            return 'engagement_focused'
        elif 'follow' in content_lower:
            return 'follow_request'
        elif any(phrase in content_lower for phrase in ['book a call', 'schedule', 'calendly']):
            return 'booking_focused'
        else:
            return 'soft_ask'
    
    def _identify_topic_category(self, content: str) -> str:
        """Identify the main topic category"""
        content_lower = content.lower()
        
        if any(term in content_lower for term in ['team', 'hiring', 'culture', 'leadership']):
            return 'team_building'
        elif any(term in content_lower for term in ['architecture', 'system', 'technical debt', 'scaling']):
            return 'technical_architecture'
        elif any(term in content_lower for term in ['nobuild', 'build vs buy', 'saas']):
            return 'nobuild_philosophy'
        elif any(term in content_lower for term in ['performance', 'optimization', 'speed']):
            return 'performance'
        elif any(term in content_lower for term in ['career', 'growth', 'mentorship']):
            return 'career_development'
        elif any(term in content_lower for term in ['startup', 'founder', 'scaling']):
            return 'startup_advice'
        else:
            return 'general_technical'
    
    def _score_technical_depth(self, content: str) -> int:
        """Score technical depth on 1-5 scale"""
        content_lower = content.lower()
        technical_indicators = [
            'architecture', 'database', 'api', 'microservices', 'algorithm',
            'python', 'javascript', 'sql', 'redis', 'docker', 'kubernetes',
            'fastapi', 'django', 'react', 'performance', 'optimization'
        ]
        
        tech_score = sum(1 for term in technical_indicators if term in content_lower)
        
        if '```' in content or 'code' in content_lower:
            tech_score += 2
        
        return min(tech_score, 5)
    
    def _score_business_focus(self, content: str) -> int:
        """Score business focus on 1-5 scale"""
        content_lower = content.lower()
        business_indicators = [
            'revenue', 'cost', 'roi', 'business', 'startup', 'founder',
            'consultation', 'client', 'project', 'contract', 'value',
            'growth', 'scaling', 'market', 'competitive'
        ]
        
        business_score = sum(1 for term in business_indicators if term in content_lower)
        
        if any(symbol in content for symbol in ['$', '%']):
            business_score += 1
        
        return min(business_score, 5)
    
    def _score_controversy_level(self, content: str) -> int:
        """Score controversy level on 1-5 scale"""
        content_lower = content.lower()
        controversy_indicators = [
            'controversial', 'unpopular', 'wrong', 'myth', 'mistake',
            'brutal truth', 'harsh reality', 'shocking', 'surprising'
        ]
        
        controversy_score = sum(1 for term in controversy_indicators if term in content_lower)
        
        if '🔥' in content or 'hot take' in content_lower:
            controversy_score += 1
        
        return min(controversy_score, 5)
    
    def _has_personal_story(self, content: str) -> bool:
        """Check if content includes personal story"""
        content_lower = content.lower()
        story_indicators = [
            'i worked', 'i helped', 'i saw', 'i learned', 'my experience',
            'last year', 'recently', 'story:', 'when i'
        ]
        
        return any(indicator in content_lower for indicator in story_indicators)
    
    def _identify_performance_patterns(self, patterns: Dict) -> List[ContentPattern]:
        """Identify significant performance patterns"""
        identified_patterns = []
        
        for pattern_type, data in patterns.items():
            if len(data) < 3:  # Need at least 3 samples
                continue
                
            # Group by pattern value and calculate averages
            pattern_groups = defaultdict(list)
            for pattern_value, engagement, consultation in data:
                pattern_groups[pattern_value].append((engagement, consultation))
            
            for pattern_value, performances in pattern_groups.items():
                if len(performances) < 2:
                    continue
                
                engagements = [p[0] for p in performances if p[0] is not None]
                consultations = [p[1] for p in performances if p[1] is not None]
                
                if not engagements:
                    continue
                
                avg_engagement = np.mean(engagements)
                avg_consultation = np.mean(consultations) if consultations else 0
                sample_size = len(performances)
                
                # Calculate confidence score (simple implementation)
                confidence = min(sample_size / 10, 1.0) * (avg_engagement + avg_consultation)
                
                # Generate recommendation
                recommendation = self._generate_pattern_recommendation(
                    pattern_type, pattern_value, avg_engagement, avg_consultation
                )
                
                pattern = ContentPattern(
                    pattern_id=f"{pattern_type}_{pattern_value}_{datetime.now().strftime('%Y%m%d')}",
                    pattern_type=pattern_type,
                    pattern_value=str(pattern_value),
                    avg_engagement_rate=avg_engagement,
                    avg_consultation_conversion=avg_consultation,
                    sample_size=sample_size,
                    confidence_score=confidence,
                    recommendation=recommendation
                )
                
                identified_patterns.append(pattern)
        
        # Sort by confidence score
        identified_patterns.sort(key=lambda x: x.confidence_score, reverse=True)
        
        return identified_patterns
    
    def _generate_pattern_recommendation(self, pattern_type: str, pattern_value: str, 
                                       engagement: float, consultation: float) -> str:
        """Generate actionable recommendations based on patterns"""
        if pattern_type == 'hook_type':
            if pattern_value == 'controversial' and engagement > 0.08:
                return "Use controversial hooks for high engagement. Test with strong opinion statements."
            elif pattern_value == 'personal_story' and consultation > 0.02:
                return "Personal stories drive consultation requests. Include specific examples from your experience."
        
        elif pattern_type == 'day':
            if pattern_value in ['Tuesday', 'Thursday'] and engagement > 0.07:
                return f"{pattern_value} shows strong performance. Prioritize high-value content on this day."
        
        elif pattern_type == 'cta_type':
            if pattern_value == 'direct_dm' and consultation > 0.015:
                return "Direct DM requests generate consultations. Use clear consultation invitations."
        
        return f"Pattern shows {engagement*100:.1f}% engagement, {consultation*100:.2f}% consultation conversion"
    
    def predict_content_performance(self, content: str, post_day: str) -> PerformancePrediction:
        """Predict performance for new content based on identified patterns"""
        
        # Analyze content characteristics
        analysis = self._analyze_content_characteristics("prediction", content)
        
        # Get relevant patterns from database
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT pattern_type, pattern_value, avg_engagement_rate, 
                   avg_consultation_conversion, confidence_score, recommendation
            FROM content_patterns 
            ORDER BY confidence_score DESC
        ''')
        
        patterns = cursor.fetchall()
        conn.close()
        
        # Calculate predictions based on matching patterns
        engagement_predictions = []
        consultation_predictions = []
        key_factors = []
        recommendations = []
        
        for pattern_type, pattern_value, avg_eng, avg_cons, confidence, rec in patterns:
            weight = confidence / 100  # Normalize confidence as weight
            
            if pattern_type == 'day' and pattern_value == post_day:
                engagement_predictions.append(avg_eng * weight)
                consultation_predictions.append(avg_cons * weight)
                key_factors.append(f"{post_day} timing")
                
            elif pattern_type == 'hook_type' and pattern_value == analysis.get('hook_type'):
                engagement_predictions.append(avg_eng * weight)
                consultation_predictions.append(avg_cons * weight)
                key_factors.append(f"{pattern_value} hook")
                
            elif pattern_type == 'cta_type' and pattern_value == analysis.get('cta_type'):
                engagement_predictions.append(avg_eng * weight)
                consultation_predictions.append(avg_cons * weight)
                key_factors.append(f"{pattern_value} CTA")
                
            elif pattern_type == 'topic_category' and pattern_value == analysis.get('topic_category'):
                engagement_predictions.append(avg_eng * weight)
                consultation_predictions.append(avg_cons * weight)
                key_factors.append(f"{pattern_value} topic")
            
            if confidence > 0.7:  # High confidence patterns
                recommendations.append(rec)
        
        # Calculate final predictions
        if engagement_predictions:
            predicted_engagement = np.mean(engagement_predictions)
            engagement_confidence = (
                predicted_engagement * 0.8,  # Lower bound
                predicted_engagement * 1.2   # Upper bound
            )
        else:
            predicted_engagement = 0.06  # Default baseline
            engagement_confidence = (0.04, 0.08)
        
        if consultation_predictions:
            consultation_rate = np.mean(consultation_predictions)
            # Assume 1000 impressions for prediction
            predicted_consultations = max(1, int(consultation_rate * 1000))
        else:
            predicted_consultations = 1  # Default baseline
        
        return PerformancePrediction(
            predicted_engagement_rate=predicted_engagement,
            predicted_consultation_requests=predicted_consultations,
            confidence_interval=engagement_confidence,
            key_success_factors=key_factors[:5],  # Top 5 factors
            optimization_recommendations=recommendations[:3]  # Top 3 recommendations
        )
    
    def _save_content_analysis(self, analysis: Dict):
        """Save content analysis to database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO content_analysis 
            (analysis_id, post_id, word_count, hook_type, cta_type, topic_category,
             technical_depth, business_focus, controversy_score, emoji_count,
             hashtag_count, question_count, personal_story, data_points, code_snippets)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            analysis['analysis_id'], analysis['post_id'], analysis['word_count'],
            analysis['hook_type'], analysis['cta_type'], analysis['topic_category'],
            analysis['technical_depth'], analysis['business_focus'], analysis['controversy_score'],
            analysis['emoji_count'], analysis['hashtag_count'], analysis['question_count'],
            analysis['personal_story'], analysis['data_points'], analysis['code_snippets']
        ))
        
        conn.commit()
        conn.close()
    
    def _save_content_pattern(self, pattern: ContentPattern):
        """Save identified content pattern to database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO content_patterns 
            (pattern_id, pattern_type, pattern_value, avg_engagement_rate,
             avg_consultation_conversion, sample_size, confidence_score, recommendation)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            pattern.pattern_id, pattern.pattern_type, pattern.pattern_value,
            pattern.avg_engagement_rate, pattern.avg_consultation_conversion,
            pattern.sample_size, pattern.confidence_score, pattern.recommendation
        ))
        
        conn.commit()
        conn.close()
    
    def generate_optimization_report(self) -> str:
        """Generate comprehensive performance optimization report"""
        # Analyze all content first
        patterns = self.analyze_all_content()
        
        report = []
        report.append("📊 PERFORMANCE OPTIMIZATION REPORT")
        report.append("=" * 60)
        report.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append("")
        
        # Top performing patterns
        report.append("🏆 TOP PERFORMING PATTERNS:")
        for i, pattern in enumerate(patterns[:5], 1):
            report.append(f"{i}. {pattern.pattern_type.title()}: {pattern.pattern_value}")
            report.append(f"   • Engagement: {pattern.avg_engagement_rate*100:.1f}%")
            report.append(f"   • Consultation Rate: {pattern.avg_consultation_conversion*100:.2f}%")
            report.append(f"   • Sample Size: {pattern.sample_size}")
            report.append(f"   • Recommendation: {pattern.recommendation}")
            report.append("")
        
        # Optimization recommendations
        report.append("💡 KEY OPTIMIZATION RECOMMENDATIONS:")
        high_confidence_patterns = [p for p in patterns if p.confidence_score > 0.5]
        
        for pattern in high_confidence_patterns[:10]:
            report.append(f"• {pattern.recommendation}")
        
        report.append("")
        
        # Performance prediction example
        sample_content = "🔥 CONTROVERSIAL: Most CTOs are just senior engineers with a fancy title. Here's what separates real technical leaders..."
        prediction = self.predict_content_performance(sample_content, "Tuesday")
        
        report.append("🔮 PERFORMANCE PREDICTION EXAMPLE:")
        report.append(f"Content: {sample_content[:100]}...")
        report.append(f"Predicted Engagement: {prediction.predicted_engagement_rate*100:.1f}%")
        report.append(f"Predicted Consultations: {prediction.predicted_consultation_requests}")
        report.append(f"Key Success Factors: {', '.join(prediction.key_success_factors)}")
        report.append("")
        
        report.append("🎯 Focus: Data-driven content optimization for maximum business development impact")
        
        return "\n".join(report)

def main():
    """Demonstrate performance analyzer"""
    analyzer = PerformanceAnalyzer()
    
    print("📊 Performance Analytics Enhancement System")
    print("=" * 60)
    
    # Generate optimization report
    print("Analyzing content patterns and generating optimization report...")
    report = analyzer.generate_optimization_report()
    print(report)
    
    print(f"\n✅ Performance Analytics System Ready!")
    print(f"Database: {analyzer.db_path}")

if __name__ == "__main__":
    main()