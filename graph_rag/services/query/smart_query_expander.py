"""Smart query expansion using graph relationships and content analysis."""

import logging
import re
from collections import Counter

logger = logging.getLogger(__name__)


class SmartQueryExpander:
    """Automatically expand queries using graph relationships and semantic understanding."""

    def __init__(self, graph_repository=None):
        self.graph_repository = graph_repository
        self._synonym_cache = {}
        self._initialize_expansion_rules()
        logger.info("SmartQueryExpander initialized")

    def expand_query_terms(self, query: str, max_expansions: int = 5) -> list[str]:
        """Expand query terms with related concepts and synonyms."""
        # Extract meaningful terms from query
        terms = self._extract_query_terms(query)

        # Start with original terms
        expanded_terms = set(terms)

        # Add synonyms and related terms
        for term in terms:
            related_terms = self._get_related_terms(term, max_expansions // len(terms))
            expanded_terms.update(related_terms)

        # Add domain-specific expansions
        domain_terms = self._apply_domain_expansions(terms)
        expanded_terms.update(domain_terms)

        return list(expanded_terms)

    async def expand_with_graph_context(self, query: str, max_depth: int = 2) -> list[str]:
        """Expand query using graph relationships from knowledge base."""
        if not self.graph_repository:
            return self.expand_query_terms(query)

        terms = self._extract_query_terms(query)
        expanded_terms = set(terms)

        for term in terms:
            try:
                # Find related entities in knowledge graph
                related_entities = await self.graph_repository.get_related_entities(
                    term, max_depth=max_depth
                )

                # Extract meaningful names from related entities
                for entity in related_entities[:3]:  # Limit to top 3 related
                    entity_name = entity.get("name", "").lower()
                    if entity_name and len(entity_name) > 2:
                        expanded_terms.add(entity_name)

            except Exception as e:
                logger.warning(f"Could not expand term '{term}' using graph: {e}")

        return list(expanded_terms)

    def suggest_query_refinements(self, query: str, search_results: list[dict]) -> list[str]:
        """Suggest query refinements based on search results analysis."""
        suggestions = []

        if not search_results:
            # No results - suggest broader terms
            suggestions.extend(self._suggest_broader_terms(query))
        elif len(search_results) > 100:
            # Too many results - suggest filters
            suggestions.extend(self._suggest_filters(search_results))
        else:
            # Good result count - suggest related queries
            suggestions.extend(self._suggest_related_queries(query, search_results))

        return suggestions[:5]  # Return top 5 suggestions

    def _extract_query_terms(self, query: str) -> list[str]:
        """Extract meaningful terms from a query string."""
        # Remove common stop words and extract meaningful terms
        stop_words = {
            "the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for",
            "of", "with", "by", "is", "are", "was", "were", "be", "been", "have",
            "has", "had", "do", "does", "did", "will", "would", "could", "should",
            "this", "that", "these", "those", "how", "what", "where", "when", "why"
        }

        # Extract words (including hyphenated terms)
        words = re.findall(r'\b[a-zA-Z][a-zA-Z0-9_-]*\b', query.lower())

        # Filter meaningful terms
        meaningful_terms = [
            word for word in words
            if len(word) > 2 and word not in stop_words
        ]

        return meaningful_terms

    def _get_related_terms(self, term: str, max_count: int = 2) -> list[str]:
        """Get related terms using predefined mappings and rules."""
        related = set()

        # Check synonym cache
        if term in self._synonym_cache:
            related.update(self._synonym_cache[term][:max_count])

        # Apply expansion rules
        for pattern, expansions in self.expansion_rules.items():
            if re.search(pattern, term, re.IGNORECASE):
                related.update(expansions[:max_count])

        return list(related)

    def _apply_domain_expansions(self, terms: list[str]) -> list[str]:
        """Apply domain-specific term expansions."""
        expanded = set()

        # Technology domain expansions
        tech_terms = {"api", "rest", "web", "http", "database", "sql"}
        if any(term in tech_terms for term in terms):
            if "api" in terms:
                expanded.update(["rest", "endpoint", "webservice"])
            if "database" in terms:
                expanded.update(["sql", "query", "schema"])
            if "web" in terms:
                expanded.update(["http", "browser", "frontend"])

        # Programming language expansions
        prog_langs = {"python", "javascript", "java", "go", "rust"}
        found_langs = [term for term in terms if term in prog_langs]
        if found_langs:
            for lang in found_langs:
                if lang == "python":
                    expanded.update(["flask", "django", "fastapi"])
                elif lang == "javascript":
                    expanded.update(["node", "react", "vue"])
                elif lang == "java":
                    expanded.update(["spring", "maven", "gradle"])

        return list(expanded)

    def _suggest_broader_terms(self, query: str) -> list[str]:
        """Suggest broader terms when no results found."""
        terms = self._extract_query_terms(query)
        suggestions = []

        for term in terms:
            # Suggest removing specific prefixes/suffixes
            if len(term) > 5:
                if term.endswith("ing"):
                    suggestions.append(term[:-3])
                elif term.endswith("ed"):
                    suggestions.append(term[:-2])
                elif term.startswith("micro"):
                    suggestions.append(term[5:])

        # Suggest removing one term from multi-term queries
        if len(terms) > 1:
            for i, term in enumerate(terms):
                reduced_query = " ".join(terms[:i] + terms[i+1:])
                suggestions.append(reduced_query)

        return suggestions

    def _suggest_filters(self, search_results: list[dict]) -> list[str]:
        """Suggest filters to narrow down too many results."""
        suggestions = []

        # Analyze common categories in results
        categories = [result.get("category") for result in search_results if result.get("category")]
        category_counts = Counter(categories)

        if category_counts:
            top_category = category_counts.most_common(1)[0][0]
            suggestions.append(f"category:{top_category}")

        # Analyze common tags
        all_tags = []
        for result in search_results:
            tags = result.get("tags", [])
            if isinstance(tags, list):
                all_tags.extend(tags)

        tag_counts = Counter(all_tags)
        if tag_counts:
            for tag, count in tag_counts.most_common(3):
                if count > len(search_results) * 0.1:  # Tag appears in >10% of results
                    suggestions.append(f"tag:{tag}")

        return suggestions

    def _suggest_related_queries(self, query: str, search_results: list[dict]) -> list[str]:
        """Suggest related queries based on successful search results."""
        suggestions = []

        # Extract common terms from result titles and content
        result_text = []
        for result in search_results[:10]:  # Analyze top 10 results
            if result.get("title"):
                result_text.append(result["title"])
            if result.get("content"):
                # Take first 100 chars of content
                result_text.append(result["content"][:100])

        # Find frequently occurring terms
        all_text = " ".join(result_text).lower()
        terms = self._extract_query_terms(all_text)
        term_counts = Counter(terms)

        query_terms = set(self._extract_query_terms(query))

        # Suggest terms that appear frequently but aren't in original query
        for term, count in term_counts.most_common(10):
            if term not in query_terms and count > 2:
                suggestions.append(f"{query} {term}")

        return suggestions

    def _initialize_expansion_rules(self):
        """Initialize pattern-based expansion rules."""
        self.expansion_rules = {
            r"\bapi\b": ["rest", "endpoint", "webservice", "http"],
            r"\bdatabase\b": ["sql", "query", "schema", "table"],
            r"\bweb\b": ["http", "browser", "frontend", "backend"],
            r"\bmachine.*learning\b": ["ml", "ai", "artificial intelligence", "algorithm"],
            r"\bauth\b": ["authentication", "authorization", "security", "login"],
            r"\bdocker\b": ["container", "containerization", "deployment"],
            r"\bkubernetes\b": ["k8s", "orchestration", "cluster"],
            r"\bmicroservice\b": ["service", "distributed", "architecture"],
            r"\btest\b": ["testing", "unittest", "pytest", "quality"]
        }

        # Initialize synonym cache
        self._synonym_cache = {
            "api": ["rest", "webservice", "endpoint"],
            "db": ["database", "sql", "storage"],
            "auth": ["authentication", "security", "login"],
            "k8s": ["kubernetes", "orchestration"],
            "ml": ["machine learning", "ai", "artificial intelligence"],
            "ui": ["user interface", "frontend", "gui"],
            "ux": ["user experience", "design", "usability"]
        }
