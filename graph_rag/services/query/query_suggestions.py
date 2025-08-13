"""Query suggestion engine for auto-complete and query enhancement."""

import logging
import re
from typing import List
from collections import defaultdict

logger = logging.getLogger(__name__)


class QuerySuggestionEngine:
    """Provides intelligent query suggestions and auto-completion."""
    
    def __init__(self, vector_store=None):
        self.vector_store = vector_store
        self._suggestion_cache = {}
        self._query_patterns = defaultdict(int)
        self._initialize_suggestion_data()
        logger.info("QuerySuggestionEngine initialized")
    
    async def get_suggestions(self, partial_query: str, limit: int = 5) -> List[str]:
        """Get query suggestions based on partial input."""
        if len(partial_query.strip()) < 2:
            return self._get_popular_queries(limit)
        
        suggestions = set()
        
        # Add completion suggestions
        completions = self._get_query_completions(partial_query, limit // 2)
        suggestions.update(completions)
        
        # Add similar queries from content
        if self.vector_store:
            similar_suggestions = await self._get_content_based_suggestions(partial_query, limit // 2)
            suggestions.update(similar_suggestions)
        
        # Add pattern-based suggestions
        pattern_suggestions = self._get_pattern_suggestions(partial_query, limit // 2)
        suggestions.update(pattern_suggestions)
        
        # Filter and rank suggestions
        filtered_suggestions = self._filter_and_rank_suggestions(
            list(suggestions), partial_query
        )
        
        return filtered_suggestions[:limit]
    
    async def get_related_queries(self, query: str, limit: int = 5) -> List[str]:
        """Get queries related to the input query."""
        related = set()
        
        # Extract key terms from query
        terms = self._extract_key_terms(query)
        
        # Find queries with overlapping terms
        for term in terms:
            if term in self._suggestion_cache:
                related.update(self._suggestion_cache[term][:2])
        
        # Get content-based related queries
        if self.vector_store:
            content_related = await self._get_content_based_suggestions(query, limit // 2)
            related.update(content_related)
        
        # Remove the original query if it appears
        related.discard(query.lower())
        
        return list(related)[:limit]
    
    def learn_from_query(self, query: str, result_count: int = 0):
        """Learn from user queries to improve suggestions."""
        # Normalize query
        normalized_query = query.lower().strip()
        
        # Update query patterns
        self._query_patterns[normalized_query] += 1
        
        # Update term-based cache
        terms = self._extract_key_terms(query)
        for term in terms:
            if term not in self._suggestion_cache:
                self._suggestion_cache[term] = []
            if normalized_query not in self._suggestion_cache[term]:
                self._suggestion_cache[term].append(normalized_query)
        
        logger.debug(f"Learned from query: {query} (results: {result_count})")
    
    def get_trending_queries(self, limit: int = 10) -> List[str]:
        """Get currently trending queries."""
        # Return most frequent recent queries
        return [query for query, count in self._query_patterns.most_common(limit)]
    
    def _get_query_completions(self, partial_query: str, limit: int) -> List[str]:
        """Get query completions based on partial input."""
        completions = []
        partial_lower = partial_query.lower()
        
        # Find queries that start with partial input
        for query, frequency in self._query_patterns.items():
            if query.startswith(partial_lower) and query != partial_lower:
                completions.append((query, frequency))
        
        # Sort by frequency and return top completions
        completions.sort(key=lambda x: x[1], reverse=True)
        return [completion[0] for completion in completions[:limit]]
    
    async def _get_content_based_suggestions(self, query: str, limit: int) -> List[str]:
        """Get suggestions based on similar content."""
        suggestions = []
        
        try:
            # Search for similar content
            similar_chunks = await self.vector_store.search_similar_chunks(
                query, limit=limit * 2, threshold=0.7
            )
            
            # Extract meaningful phrases from similar content
            for chunk in similar_chunks:
                content = chunk.get("text", "")
                phrases = self._extract_query_phrases(content)
                suggestions.extend(phrases[:2])  # Take top 2 phrases per chunk
                
        except Exception as e:
            logger.warning(f"Could not get content-based suggestions: {e}")
        
        return suggestions[:limit]
    
    def _get_pattern_suggestions(self, partial_query: str, limit: int) -> List[str]:
        """Get suggestions based on common query patterns."""
        suggestions = []
        terms = self._extract_key_terms(partial_query)
        
        # Common query patterns
        patterns = [
            "how to {term}",
            "{term} tutorial",
            "{term} best practices",
            "{term} documentation",
            "{term} examples",
            "what is {term}",
            "{term} vs",
            "{term} setup",
            "{term} configuration"
        ]
        
        for term in terms:
            for pattern in patterns:
                suggestion = pattern.format(term=term)
                if suggestion.lower() != partial_query.lower():
                    suggestions.append(suggestion)
        
        return suggestions[:limit]
    
    def _get_popular_queries(self, limit: int) -> List[str]:
        """Get popular queries when no partial input is provided."""
        # Return most common queries
        popular = [
            "python api development",
            "database design",
            "authentication setup",
            "web security",
            "microservices architecture",
            "docker deployment",
            "rest api best practices",
            "javascript frameworks",
            "machine learning basics",
            "testing strategies"
        ]
        
        # Mix with learned popular queries
        learned_popular = [q for q, c in self._query_patterns.most_common(5)]
        
        combined = list(set(popular + learned_popular))
        return combined[:limit]
    
    def _extract_key_terms(self, query: str) -> List[str]:
        """Extract key terms from a query."""
        # Remove common words and extract meaningful terms
        stop_words = {
            "the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for",
            "of", "with", "by", "is", "are", "was", "were", "be", "been", "have",
            "has", "had", "do", "does", "did", "will", "would", "could", "should",
            "how", "what", "where", "when", "why", "who"
        }
        
        words = re.findall(r'\b[a-zA-Z][a-zA-Z0-9_-]*\b', query.lower())
        return [word for word in words if len(word) > 2 and word not in stop_words]
    
    def _extract_query_phrases(self, content: str) -> List[str]:
        """Extract potential query phrases from content."""
        phrases = []
        
        # Look for phrases in titles and headings
        title_patterns = [
            r"# (.+)",  # Markdown headers
            r"## (.+)",
            r"### (.+)"
        ]
        
        for pattern in title_patterns:
            matches = re.findall(pattern, content)
            for match in matches:
                phrase = match.strip()
                if 3 <= len(phrase.split()) <= 6:  # Good phrase length
                    phrases.append(phrase.lower())
        
        # Look for "how to" patterns
        how_to_pattern = r"how to ([^.!?\\n]+)"
        how_to_matches = re.findall(how_to_pattern, content, re.IGNORECASE)
        for match in how_to_matches:
            phrase = f"how to {match.strip()}"
            if len(phrase.split()) <= 6:
                phrases.append(phrase.lower())
        
        return phrases
    
    def _filter_and_rank_suggestions(self, suggestions: List[str], partial_query: str) -> List[str]:
        """Filter and rank suggestions by relevance."""
        if not suggestions:
            return []
        
        partial_terms = set(self._extract_key_terms(partial_query))
        scored_suggestions = []
        
        for suggestion in suggestions:
            suggestion_terms = set(self._extract_key_terms(suggestion))
            
            # Calculate relevance score
            overlap_score = len(partial_terms.intersection(suggestion_terms))
            frequency_score = self._query_patterns.get(suggestion.lower(), 0)
            length_penalty = abs(len(suggestion.split()) - len(partial_query.split())) * 0.1
            
            total_score = overlap_score + (frequency_score * 0.1) - length_penalty
            scored_suggestions.append((suggestion, total_score))
        
        # Sort by score and return
        scored_suggestions.sort(key=lambda x: x[1], reverse=True)
        
        # Remove duplicates while preserving order
        seen = set()
        unique_suggestions = []
        for suggestion, score in scored_suggestions:
            if suggestion.lower() not in seen:
                seen.add(suggestion.lower())
                unique_suggestions.append(suggestion)
        
        return unique_suggestions
    
    def _initialize_suggestion_data(self):
        """Initialize suggestion data with common patterns."""
        # Common technical queries
        common_queries = [
            "api documentation",
            "database schema",
            "authentication flow",
            "error handling",
            "performance optimization",
            "security best practices",
            "deployment guide",
            "testing strategy",
            "code review",
            "version control"
        ]
        
        # Initialize query patterns
        for query in common_queries:
            self._query_patterns[query] = 5  # Give them some initial weight
            
            terms = self._extract_key_terms(query)
            for term in terms:
                if term not in self._suggestion_cache:
                    self._suggestion_cache[term] = []
                self._suggestion_cache[term].append(query)