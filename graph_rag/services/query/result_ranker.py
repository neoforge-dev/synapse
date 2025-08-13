"""Advanced result ranking and scoring for search results."""

import logging
import math
from typing import List, Dict, Any, Optional, Set
from datetime import datetime, timedelta
from collections import Counter

logger = logging.getLogger(__name__)


class AdvancedResultRanker:
    """Advanced ranking system for search results with custom scoring."""
    
    def __init__(self):
        self.scoring_weights = {
            "relevance": 0.4,      # Base relevance score
            "freshness": 0.2,      # How recent the content is
            "quality": 0.2,        # Content quality indicators
            "user_preference": 0.1, # User preference signals
            "diversity": 0.1       # Result diversity
        }
        logger.info("AdvancedResultRanker initialized")
    
    def rank_results(self, results: List[Dict[str, Any]], 
                    query_context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Rank search results using advanced scoring."""
        if not results:
            return []
        
        # Calculate scores for each result
        scored_results = []
        for result in results:
            score = self._calculate_composite_score(result, query_context)
            result_with_score = result.copy()
            result_with_score["final_score"] = score
            scored_results.append(result_with_score)
        
        # Apply diversity filtering
        diverse_results = self._apply_diversity_filter(scored_results, query_context)
        
        # Sort by final score
        diverse_results.sort(key=lambda x: x["final_score"], reverse=True)
        
        logger.debug(f"Ranked {len(results)} results, returning {len(diverse_results)}")
        return diverse_results
    
    def _calculate_composite_score(self, result: Dict[str, Any], 
                                 query_context: Dict[str, Any]) -> float:
        """Calculate composite score for a single result."""
        scores = {}
        
        # Relevance score (base similarity score)
        scores["relevance"] = result.get("score", 0.0)
        
        # Freshness score
        scores["freshness"] = self._calculate_freshness_score(result, query_context)
        
        # Quality score
        scores["quality"] = self._calculate_quality_score(result, query_context)
        
        # User preference score
        scores["user_preference"] = self._calculate_preference_score(result, query_context)
        
        # Calculate weighted composite score
        composite_score = sum(
            scores[component] * self.scoring_weights[component]
            for component in scores
        )
        
        return min(composite_score, 1.0)  # Cap at 1.0
    
    def _calculate_freshness_score(self, result: Dict[str, Any], 
                                  query_context: Dict[str, Any]) -> float:
        """Calculate freshness score based on content age."""
        created_at = result.get("created_at")
        if not created_at:
            return 0.5  # Neutral score for unknown dates
        
        try:
            # Parse date (assume ISO format)
            if isinstance(created_at, str):
                content_date = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
            else:
                content_date = created_at
            
            now = datetime.now(content_date.tzinfo)
            age_days = (now - content_date).days
            
            # Boost recent content if requested
            boost_recent = query_context.get("boost_recent", False)
            if boost_recent:
                # Exponential decay: fresh content gets higher scores
                freshness_score = math.exp(-age_days / 30.0)  # 30-day half-life
            else:
                # Linear decay with minimum threshold
                freshness_score = max(0.1, 1.0 - (age_days / 365.0))  # 1-year decay
            
            return min(freshness_score, 1.0)
            
        except (ValueError, TypeError) as e:
            logger.warning(f"Could not parse date: {created_at}, error: {e}")
            return 0.5
    
    def _calculate_quality_score(self, result: Dict[str, Any], 
                                query_context: Dict[str, Any]) -> float:
        """Calculate content quality score."""
        quality_score = 0.5  # Base score
        
        # Content length indicators
        content = result.get("content", "")
        title = result.get("title", "")
        
        # Reasonable content length (not too short, not too long)
        content_length = len(content)
        if 200 <= content_length <= 5000:
            quality_score += 0.1
        elif content_length > 5000:
            quality_score += 0.05
        
        # Has descriptive title
        if title and len(title.split()) >= 3:
            quality_score += 0.1
        
        # Has tags/metadata
        tags = result.get("tags", [])
        if isinstance(tags, list) and len(tags) > 0:
            quality_score += 0.1
        
        # Category classification
        category = result.get("category")
        if category and category != "general":
            quality_score += 0.1
        
        # Code or technical content indicators
        if any(indicator in content.lower() for indicator in 
               ["```", "def ", "class ", "function", "import", "SELECT"]):
            quality_score += 0.1
        
        # Structured content indicators
        if any(indicator in content for indicator in 
               ["# ", "## ", "- ", "1. ", "* "]):
            quality_score += 0.05
        
        return min(quality_score, 1.0)
    
    def _calculate_preference_score(self, result: Dict[str, Any], 
                                   query_context: Dict[str, Any]) -> float:
        """Calculate score based on user preferences."""
        preference_score = 0.2  # Lower base score
        
        # Preferred categories - higher boost
        preferred_categories = query_context.get("preferred_categories", [])
        result_category = result.get("category")
        if result_category in preferred_categories:
            preference_score += 0.4  # Increased from 0.3
        
        # Search term matching in title (higher preference)
        search_terms = query_context.get("search_terms", [])
        title = result.get("title", "").lower()
        content = result.get("content", "").lower()
        
        # Check both title and content for search terms with different weights
        title_matches = sum(1 for term in search_terms if term.lower() in title)
        content_matches = sum(1 for term in search_terms if term.lower() in content)
        
        if title_matches > 0:
            preference_score += min(0.4, title_matches * 0.2)  # Higher weight for title matches
        if content_matches > 0:
            preference_score += min(0.3, content_matches * 0.15)  # Content matches
        
        # Tag matching with search terms
        result_tags = result.get("tags", [])
        if isinstance(result_tags, list):
            tag_search_matches = sum(1 for term in search_terms 
                                   for tag in result_tags 
                                   if term.lower() == tag.lower())
            preference_score += min(0.3, tag_search_matches * 0.15)
        
        # Preferred tags
        preferred_tags = query_context.get("preferred_tags", [])
        if isinstance(result_tags, list):
            tag_matches = len(set(preferred_tags).intersection(set(result_tags)))
            preference_score += min(0.2, tag_matches * 0.1)
        
        # Language/technology preferences
        preferred_languages = query_context.get("preferred_languages", [])
        
        for lang in preferred_languages:
            if lang.lower() in content:
                preference_score += 0.1
                break
        
        return min(preference_score, 1.0)
    
    def _apply_diversity_filter(self, results: List[Dict[str, Any]], 
                               query_context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Apply diversity filtering to avoid too similar results."""
        if len(results) <= 5:
            return results  # Don't filter small result sets
        
        diverse_results = []
        seen_categories = Counter()
        seen_sources = Counter()
        max_per_category = query_context.get("max_per_category", 3)
        
        for result in sorted(results, key=lambda x: x["final_score"], reverse=True):
            category = result.get("category", "general")
            source = result.get("source", "unknown")
            
            # Check diversity constraints
            if (seen_categories[category] < max_per_category and 
                seen_sources[source] < 2):  # Max 2 per source
                
                diverse_results.append(result)
                seen_categories[category] += 1
                seen_sources[source] += 1
            
            # Stop when we have enough diverse results
            if len(diverse_results) >= min(20, len(results)):
                break
        
        # If we don't have enough diverse results, add more from remaining
        if len(diverse_results) < 10 and len(diverse_results) < len(results):
            remaining = [r for r in results if r not in diverse_results]
            diverse_results.extend(remaining[:10 - len(diverse_results)])
        
        return diverse_results
    
    def update_scoring_weights(self, weights: Dict[str, float]):
        """Update scoring weights for different components."""
        # Validate weights sum to approximately 1.0
        total_weight = sum(weights.values())
        if abs(total_weight - 1.0) > 0.1:
            logger.warning(f"Scoring weights sum to {total_weight}, should be ~1.0")
        
        self.scoring_weights.update(weights)
        logger.info(f"Updated scoring weights: {self.scoring_weights}")
    
    def explain_ranking(self, result: Dict[str, Any], 
                       query_context: Dict[str, Any]) -> Dict[str, Any]:
        """Explain why a result got its ranking score."""
        explanation = {
            "final_score": result.get("final_score", 0.0),
            "components": {}
        }
        
        # Calculate individual component scores
        explanation["components"]["relevance"] = result.get("score", 0.0)
        explanation["components"]["freshness"] = self._calculate_freshness_score(result, query_context)
        explanation["components"]["quality"] = self._calculate_quality_score(result, query_context)
        explanation["components"]["user_preference"] = self._calculate_preference_score(result, query_context)
        
        # Add weighted contributions
        explanation["weighted_contributions"] = {
            component: score * self.scoring_weights[component]
            for component, score in explanation["components"].items()
        }
        
        return explanation