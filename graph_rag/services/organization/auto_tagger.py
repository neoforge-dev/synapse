"""Automatic document tagging based on content analysis."""

import logging
import re
from collections import Counter
from typing import Dict, List, Tuple, Set

logger = logging.getLogger(__name__)


class AutoTagger:
    """Automatically extract tags and categories from document content."""
    
    def __init__(self):
        self._initialize_keywords()
        logger.info("AutoTagger initialized")
    
    def _initialize_keywords(self):
        """Initialize keyword patterns for different categories."""
        self.tech_keywords = {
            "api", "fastapi", "rest", "http", "endpoint", "authentication", "auth",
            "database", "postgresql", "mysql", "sql", "migration", "deployment",
            "docker", "kubernetes", "microservices", "pydantic", "validation",
            "python", "javascript", "typescript", "react", "vue", "flask", "django",
            "framework", "library", "development", "programming", "coding",
            "git", "github", "version", "control", "testing", "unittest", "pytest"
        }
        
        self.business_keywords = {
            "meeting", "planning", "strategy", "roadmap", "quarterly", "goals",
            "action", "items", "deadline", "milestone", "project", "team",
            "stakeholder", "requirement", "budget", "resource", "timeline"
        }
        
        self.research_keywords = {
            "research", "analysis", "study", "methodology", "experiment", "data",
            "algorithm", "machine", "learning", "artificial", "intelligence",
            "nlp", "processing", "model", "training", "evaluation", "paper",
            "academic", "publication", "theory", "hypothesis", "conclusion"
        }
        
        self.category_keywords = {
            "technical": self.tech_keywords,
            "business": self.business_keywords,
            "research": self.research_keywords
        }
    
    def extract_tags(self, content: str, normalize: bool = False) -> List[str]:
        """Extract tags from content using keyword matching and frequency analysis."""
        if not content:
            return []
        
        # Convert to lowercase and extract words
        words = self._extract_words(content)
        word_counts = Counter(words)
        
        # Find tags based on keyword matching
        found_tags = set()
        
        # Check against known keyword sets
        for word in words:
            word_lower = word.lower()
            # Direct keyword match
            if word_lower in self.tech_keywords:
                found_tags.add(word_lower)
            elif word_lower in self.business_keywords:
                found_tags.add(word_lower)
            elif word_lower in self.research_keywords:
                found_tags.add(word_lower)
            else:
                # Check for partial keyword matches (for variations like "api-design" -> "api")
                for keyword in self.tech_keywords:
                    if keyword in word_lower or word_lower in keyword:
                        found_tags.add(keyword)
                        break
                else:
                    for keyword in self.business_keywords:
                        if keyword in word_lower or word_lower in keyword:
                            found_tags.add(keyword)
                            break
                    else:
                        for keyword in self.research_keywords:
                            if keyword in word_lower or word_lower in keyword:
                                found_tags.add(keyword)
                                break
        
        # Add high-frequency meaningful words as potential tags
        meaningful_words = self._find_meaningful_words(word_counts)
        found_tags.update(meaningful_words)
        
        tags = list(found_tags)
        
        if normalize:
            tags = self._normalize_tags(tags)
        
        # Sort by relevance/frequency
        return sorted(tags, key=lambda tag: word_counts.get(tag, 0), reverse=True)[:10]
    
    def extract_tags_with_confidence(self, content: str) -> List[Tuple[str, float]]:
        """Extract tags with confidence scores."""
        if not content:
            return []
        
        words = self._extract_words(content)
        word_counts = Counter(words)
        total_words = sum(word_counts.values())
        
        tags_with_scores = []
        
        for word in words:
            word_lower = word.lower()
            
            # Calculate confidence based on frequency and keyword match
            frequency_score = word_counts[word] / total_words
            
            if word_lower in self.tech_keywords:
                keyword_bonus = 0.8
            elif word_lower in self.business_keywords:
                keyword_bonus = 0.8
            elif word_lower in self.research_keywords:
                keyword_bonus = 0.8
            else:
                keyword_bonus = 0.3
            
            # Combine frequency and keyword matching for confidence
            confidence = min(frequency_score * 20 + keyword_bonus, 1.0)
            
            if confidence > 0.3:  # Minimum threshold
                tags_with_scores.append((word_lower, confidence))
        
        # Remove duplicates and sort by confidence
        unique_tags = {}
        for tag, conf in tags_with_scores:
            if tag not in unique_tags or conf > unique_tags[tag]:
                unique_tags[tag] = conf
        
        result = [(tag, conf) for tag, conf in unique_tags.items()]
        return sorted(result, key=lambda x: x[1], reverse=True)[:10]
    
    def classify_category(self, content: str) -> str:
        """Classify document into a broad category."""
        if not content:
            return "general"
        
        words = set(word.lower() for word in self._extract_words(content))
        
        category_scores = {}
        for category, keywords in self.category_keywords.items():
            score = len(words.intersection(keywords))
            category_scores[category] = score
        
        # Return category with highest score
        if max(category_scores.values()) == 0:
            return "general"
        
        return max(category_scores.keys(), key=lambda k: category_scores[k])
    
    def extract_hierarchical_tags(self, content: str) -> Dict[str, List[str]]:
        """Extract tags organized in hierarchical categories."""
        words = set(word.lower() for word in self._extract_words(content))
        
        hierarchical = {}
        
        # Technology tags
        tech_tags = words.intersection(self.tech_keywords)
        if tech_tags:
            hierarchical["technology"] = list(tech_tags)
        
        # Business tags
        business_tags = words.intersection(self.business_keywords)
        if business_tags:
            hierarchical["business"] = list(business_tags)
        
        # Research tags
        research_tags = words.intersection(self.research_keywords)
        if research_tags:
            hierarchical["research"] = list(research_tags)
        
        return hierarchical
    
    def _extract_words(self, content: str) -> List[str]:
        """Extract meaningful words from content."""
        # Remove punctuation and split into words
        words = re.findall(r'\b[a-zA-Z][a-zA-Z0-9_-]*\b', content.lower())
        
        # Filter out common stop words and very short words
        stop_words = {
            "the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for",
            "of", "with", "by", "is", "are", "was", "were", "be", "been", "have",
            "has", "had", "do", "does", "did", "will", "would", "could", "should",
            "this", "that", "these", "those", "we", "us", "our", "you", "your",
            "it", "its", "they", "them", "their", "as", "if", "then", "than"
        }
        
        return [word for word in words if len(word) > 2 and word not in stop_words]
    
    def _find_meaningful_words(self, word_counts: Counter) -> Set[str]:
        """Find meaningful words that could be tags."""
        meaningful = set()
        
        # Words that appear multiple times might be meaningful
        for word, count in word_counts.items():
            if count >= 2 and len(word) >= 4:
                meaningful.add(word)
        
        return meaningful
    
    def _normalize_tags(self, tags: List[str]) -> List[str]:
        """Normalize tags for consistency."""
        normalized = []
        
        for tag in tags:
            # Convert to lowercase
            normalized_tag = tag.lower()
            
            # Replace hyphens and underscores with consistent format
            normalized_tag = normalized_tag.replace("-", "_")
            
            normalized.append(normalized_tag)
        
        return list(set(normalized))  # Remove duplicates