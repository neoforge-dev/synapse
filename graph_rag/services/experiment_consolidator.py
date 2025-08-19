"""Implementation of experiment consolidation service for detecting and merging overlapping experimental documents."""

import asyncio
import hashlib
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from graph_rag.core.consolidation import (
    ArchitecturalPattern,
    ConsolidatedExperiment,
    ConsolidationCandidate,
    ConsolidationReport,
    EvidenceRanker,
    ExperimentConsolidator,
    MetricType,
    MetricsExtractor,
    PatternRecognizer,
    SimilarityDetector,
    SimilarityMatch,
    SimilarityThreshold,
    SuccessMetric,
)


class TextSimilarityDetector:
    """Implementation of similarity detection using text-based and semantic approaches."""
    
    def __init__(self):
        self._setup_patterns()
    
    def _setup_patterns(self):
        """Setup common text patterns for content comparison."""
        # Patterns for identifying content sections
        self.section_patterns = [
            r'#{1,6}\s+(.+)',  # Markdown headers
            r'\*\*(.+?)\*\*',  # Bold text (likely important concepts)
            r'`([^`]+)`',      # Code snippets
            r'\d+\.\s+(.+)',   # Numbered lists
            r'-\s+(.+)',       # Bullet points
        ]
    
    async def calculate_similarity(
        self, 
        content_a: str, 
        content_b: str,
        comparison_method: str = "semantic"
    ) -> float:
        """Calculate similarity score between two content pieces."""
        if comparison_method == "textual":
            return await self._textual_similarity(content_a, content_b)
        elif comparison_method == "structural":
            return await self._structural_similarity(content_a, content_b)
        else:  # semantic (default)
            return await self._semantic_similarity(content_a, content_b)
    
    async def _textual_similarity(self, content_a: str, content_b: str) -> float:
        """Calculate text-based similarity using word overlap."""
        words_a = set(self._normalize_text(content_a).split())
        words_b = set(self._normalize_text(content_b).split())
        
        if not words_a or not words_b:
            return 0.0
        
        intersection = words_a & words_b
        union = words_a | words_b
        
        return len(intersection) / len(union) if union else 0.0
    
    async def _structural_similarity(self, content_a: str, content_b: str) -> float:
        """Calculate similarity based on document structure."""
        structure_a = self._extract_structure(content_a)
        structure_b = self._extract_structure(content_b)
        
        if not structure_a or not structure_b:
            return 0.0
        
        # Compare structure patterns
        common_patterns = set(structure_a) & set(structure_b)
        all_patterns = set(structure_a) | set(structure_b)
        
        return len(common_patterns) / len(all_patterns) if all_patterns else 0.0
    
    async def _semantic_similarity(self, content_a: str, content_b: str) -> float:
        """Calculate semantic similarity (simplified implementation)."""
        # For now, combine textual and structural similarity
        # In a full implementation, this would use embeddings
        textual_sim = await self._textual_similarity(content_a, content_b)
        structural_sim = await self._structural_similarity(content_a, content_b)
        
        # Weight semantic similarity as combination
        return (textual_sim * 0.7) + (structural_sim * 0.3)
    
    async def find_similar_sections(
        self,
        content_a: str,
        content_b: str,
        threshold: float = 0.8
    ) -> List[tuple[str, str]]:
        """Find sections with high similarity between documents."""
        sections_a = self._extract_sections(content_a)
        sections_b = self._extract_sections(content_b)
        
        similar_sections = []
        
        for section_a in sections_a:
            for section_b in sections_b:
                similarity = await self._textual_similarity(section_a, section_b)
                if similarity >= threshold:
                    similar_sections.append((section_a[:200], section_b[:200]))
        
        return similar_sections
    
    def _normalize_text(self, text: str) -> str:
        """Normalize text for comparison."""
        # Remove markdown formatting
        text = re.sub(r'[#*`\-_]', '', text)
        # Convert to lowercase and remove extra whitespace
        text = ' '.join(text.lower().split())
        return text
    
    def _extract_structure(self, content: str) -> List[str]:
        """Extract structural patterns from content."""
        patterns = []
        for pattern in self.section_patterns:
            matches = re.findall(pattern, content, re.MULTILINE)
            patterns.extend(matches)
        return patterns
    
    def _extract_sections(self, content: str) -> List[str]:
        """Extract content sections for comparison."""
        # Split by headers and other structural elements
        sections = re.split(r'\n#{1,6}\s+', content)
        return [section.strip() for section in sections if section.strip()]


class RegexMetricsExtractor:
    """Implementation of metrics extraction using regex patterns."""
    
    def __init__(self):
        self._setup_patterns()
    
    def _setup_patterns(self):
        """Setup regex patterns for extracting different metric types."""
        self.metric_patterns = {
            MetricType.PERFORMANCE_IMPROVEMENT: [
                r'(\d{1,3}(?:,\d{3})*)\s*x\s+(?:improvement|faster|better|increase)',
                r'(\d+(?:\.\d+)?)\s*times?\s+(?:faster|better|improvement)',
                r'improved?\s+by\s+(\d{1,3}(?:,\d{3})*)\s*x',
            ],
            MetricType.PERCENTAGE_GAIN: [
                r'(\d+(?:\.\d+)?)\s*%\s+(?:improvement|increase|reduction|faster|better)',
                r'increased?\s+by\s+(\d+(?:\.\d+)?)\s*%',
                r'reduced?\s+by\s+(\d+(?:\.\d+)?)\s*%',
            ],
            MetricType.THROUGHPUT_METRIC: [
                r'(\d{1,3}(?:,\d{3})*)\s+(?:messages?|requests?|operations?|transactions?)[\/\s]+(?:second|sec|minute|min|hour|hr)',
                r'(\d+(?:\.\d+)?)\s*(?:k|K|M|million|thousand)\s+(?:messages?|requests?|ops)[\/\s]+(?:second|sec)',
            ],
            MetricType.COST_REDUCTION: [
                r'\$(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)\s*(?:K|M|million|thousand)?\s+(?:savings?|saved|reduction)',
                r'saved?\s+\$(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)\s*(?:K|M)?',
            ],
            MetricType.TIME_SAVINGS: [
                r'(\d+(?:\.\d+)?)\s*%\s+faster',
                r'reduced?\s+(?:time|duration)\s+by\s+(\d+(?:\.\d+)?)\s*%',
                r'(\d+)\s+(?:hours?|minutes?|days?)\s+(?:faster|saved)',
            ],
            MetricType.ENGAGEMENT_METRIC: [
                r'(\d+(?:\.\d+)?)\s*%\s+engagement',
                r'engagement\s+rate[:\s]+(\d+(?:\.\d+)?)\s*%',
                r'(\d+(?:\.\d+)?)-(\d+(?:\.\d+)?)\s*%\s+engagement',
            ],
        }
    
    async def extract_metrics(self, content: str) -> List[SuccessMetric]:
        """Extract quantifiable metrics from text content."""
        metrics = []
        
        for metric_type, patterns in self.metric_patterns.items():
            for pattern in patterns:
                matches = re.finditer(pattern, content, re.IGNORECASE)
                for match in matches:
                    metric = self._create_metric_from_match(
                        metric_type, match, content
                    )
                    if metric:
                        metrics.append(metric)
        
        return metrics
    
    async def extract_performance_numbers(self, content: str) -> List[SuccessMetric]:
        """Extract performance improvement numbers like '39,092x' or '95.9%'."""
        performance_metrics = []
        
        # Focus on performance-related metric types
        performance_types = [
            MetricType.PERFORMANCE_IMPROVEMENT,
            MetricType.PERCENTAGE_GAIN,
            MetricType.THROUGHPUT_METRIC,
        ]
        
        for metric_type in performance_types:
            if metric_type in self.metric_patterns:
                for pattern in self.metric_patterns[metric_type]:
                    matches = re.finditer(pattern, content, re.IGNORECASE)
                    for match in matches:
                        metric = self._create_metric_from_match(
                            metric_type, match, content
                        )
                        if metric:
                            performance_metrics.append(metric)
        
        return performance_metrics
    
    def _create_metric_from_match(
        self, 
        metric_type: MetricType, 
        match: re.Match,
        content: str
    ) -> Optional[SuccessMetric]:
        """Create a SuccessMetric from a regex match."""
        try:
            # Extract numeric value
            value_str = match.group(1).replace(',', '')
            value = float(value_str)
            
            # Determine unit based on metric type
            unit = self._get_unit_for_metric_type(metric_type, match.group(0))
            
            # Extract context around the match
            start = max(0, match.start() - 50)
            end = min(len(content), match.end() + 50)
            context = content[start:end].strip()
            
            # Calculate confidence based on context quality
            confidence = self._calculate_confidence(match.group(0), context)
            
            return SuccessMetric(
                metric_type=metric_type,
                value=value,
                unit=unit,
                context=context,
                source_location=f"Character {match.start()}-{match.end()}",
                confidence_score=confidence,
            )
        except (ValueError, IndexError):
            return None
    
    def _get_unit_for_metric_type(self, metric_type: MetricType, match_text: str) -> str:
        """Determine the appropriate unit for a metric type."""
        if metric_type == MetricType.PERFORMANCE_IMPROVEMENT:
            return "x"
        elif metric_type == MetricType.PERCENTAGE_GAIN:
            return "%"
        elif metric_type == MetricType.THROUGHPUT_METRIC:
            if "/second" in match_text or "/sec" in match_text:
                return "/second"
            elif "/minute" in match_text:
                return "/minute"
            else:
                return "/unit_time"
        elif metric_type == MetricType.COST_REDUCTION:
            return "$"
        elif metric_type == MetricType.TIME_SAVINGS:
            if "%" in match_text:
                return "%"
            elif "hours" in match_text:
                return "hours"
            elif "minutes" in match_text:
                return "minutes"
            else:
                return "time_units"
        elif metric_type == MetricType.ENGAGEMENT_METRIC:
            return "%"
        else:
            return "units"
    
    def _calculate_confidence(self, match_text: str, context: str) -> float:
        """Calculate confidence score for metric extraction."""
        confidence = 0.5  # Base confidence
        
        # Higher confidence for specific contexts
        high_confidence_keywords = [
            "improvement", "increase", "faster", "better", "reduced", 
            "performance", "throughput", "engagement", "savings"
        ]
        
        for keyword in high_confidence_keywords:
            if keyword.lower() in context.lower():
                confidence += 0.1
        
        # Lower confidence for vague contexts
        low_confidence_keywords = ["approximately", "around", "about", "roughly"]
        for keyword in low_confidence_keywords:
            if keyword.lower() in context.lower():
                confidence -= 0.2
        
        return max(0.0, min(1.0, confidence))


class KeywordPatternRecognizer:
    """Implementation of architectural pattern recognition using keyword matching."""
    
    def __init__(self):
        self._setup_patterns()
    
    def _setup_patterns(self):
        """Setup known architectural patterns and their indicators."""
        self.architectural_patterns = {
            "Universal Orchestrator": {
                "keywords": ["orchestrator", "universal", "coordinator", "central controller"],
                "benefits": ["Centralized control", "Simplified coordination", "Clear responsibility"],
                "challenges": ["Single point of failure", "Scalability bottleneck"],
                "use_cases": ["Workflow orchestration", "Service coordination"],
            },
            "Microservices Architecture": {
                "keywords": ["microservices", "distributed", "service mesh", "decomposition"],
                "benefits": ["Independent scaling", "Technology diversity", "Team autonomy"],
                "challenges": ["Complexity", "Network latency", "Data consistency"],
                "use_cases": ["Large teams", "Complex domains", "Independent deployments"],
            },
            "Event-Driven Architecture": {
                "keywords": ["event-driven", "events", "messaging", "pub-sub", "asynchronous"],
                "benefits": ["Loose coupling", "Scalability", "Real-time processing"],
                "challenges": ["Event ordering", "Eventual consistency", "Debugging complexity"],
                "use_cases": ["Real-time systems", "Reactive applications"],
            },
            "Domain-Driven Design": {
                "keywords": ["domain", "bounded context", "aggregate", "ubiquitous language"],
                "benefits": ["Business alignment", "Clear boundaries", "Maintainable code"],
                "challenges": ["Complexity", "Learning curve", "Design overhead"],
                "use_cases": ["Complex business domains", "Large applications"],
            },
            "CQRS Pattern": {
                "keywords": ["CQRS", "command query", "read model", "write model"],
                "benefits": ["Performance optimization", "Scalability", "Clear separation"],
                "challenges": ["Complexity", "Eventual consistency", "Data synchronization"],
                "use_cases": ["High-performance systems", "Different read/write patterns"],
            },
        }
    
    async def identify_patterns(self, content: str) -> List[ArchitecturalPattern]:
        """Identify architectural patterns mentioned in content."""
        patterns = []
        content_lower = content.lower()
        
        for pattern_name, pattern_info in self.architectural_patterns.items():
            # Check if pattern keywords are present
            keyword_matches = sum(
                1 for keyword in pattern_info["keywords"]
                if keyword.lower() in content_lower
            )
            
            if keyword_matches > 0:
                # Calculate evidence strength based on keyword frequency
                evidence_strength = min(1.0, keyword_matches / len(pattern_info["keywords"]))
                
                pattern = ArchitecturalPattern(
                    pattern_name=pattern_name,
                    description=f"Architectural pattern identified from content analysis",
                    benefits=pattern_info["benefits"],
                    challenges=pattern_info["challenges"],
                    use_cases=pattern_info["use_cases"],
                    evidence_strength=evidence_strength,
                )
                patterns.append(pattern)
        
        return patterns
    
    async def extract_best_practices(self, content: str) -> List[str]:
        """Extract best practices and proven approaches."""
        best_practices = []
        
        # Patterns for identifying best practices
        best_practice_patterns = [
            r'best practice[:\s]+(.+?)(?:\.|$)',
            r'proven approach[:\s]+(.+?)(?:\.|$)',
            r'recommendation[:\s]+(.+?)(?:\.|$)',
            r'key insight[:\s]+(.+?)(?:\.|$)',
            r'lesson learned[:\s]+(.+?)(?:\.|$)',
        ]
        
        for pattern in best_practice_patterns:
            matches = re.finditer(pattern, content, re.IGNORECASE | re.MULTILINE)
            for match in matches:
                practice = match.group(1).strip()
                if len(practice) > 10:  # Filter out very short matches
                    best_practices.append(practice)
        
        return best_practices


class SimpleEvidenceRanker:
    """Implementation of evidence-based ranking for consolidated experiments."""
    
    async def rank_by_evidence(
        self, 
        consolidated_experiments: List[ConsolidatedExperiment]
    ) -> List[ConsolidatedExperiment]:
        """Rank consolidated experiments by strength of supporting evidence."""
        # Calculate evidence scores for each experiment
        scored_experiments = []
        for experiment in consolidated_experiments:
            evidence_score = await self.calculate_evidence_score(
                experiment.proven_metrics, 
                experiment.architectural_patterns
            )
            experiment.evidence_ranking = evidence_score
            scored_experiments.append(experiment)
        
        # Sort by evidence ranking (highest first)
        return sorted(scored_experiments, key=lambda x: x.evidence_ranking, reverse=True)
    
    async def calculate_evidence_score(
        self, 
        metrics: List[SuccessMetric],
        patterns: List[ArchitecturalPattern]
    ) -> float:
        """Calculate overall evidence strength score."""
        if not metrics and not patterns:
            return 0.0
        
        # Weight metrics more heavily than patterns
        metrics_score = self._calculate_metrics_score(metrics) * 0.7
        patterns_score = self._calculate_patterns_score(patterns) * 0.3
        
        return min(1.0, metrics_score + patterns_score)
    
    def _calculate_metrics_score(self, metrics: List[SuccessMetric]) -> float:
        """Calculate score based on success metrics quality."""
        if not metrics:
            return 0.0
        
        # Weight by confidence and metric type importance
        type_weights = {
            MetricType.PERFORMANCE_IMPROVEMENT: 1.0,
            MetricType.PERCENTAGE_GAIN: 0.8,
            MetricType.THROUGHPUT_METRIC: 0.9,
            MetricType.COST_REDUCTION: 0.7,
            MetricType.TIME_SAVINGS: 0.6,
            MetricType.ENGAGEMENT_METRIC: 0.5,
        }
        
        total_weighted_score = 0.0
        total_weight = 0.0
        
        for metric in metrics:
            weight = type_weights.get(metric.metric_type, 0.5)
            score = metric.confidence_score * weight
            total_weighted_score += score
            total_weight += weight
        
        return total_weighted_score / total_weight if total_weight > 0 else 0.0
    
    def _calculate_patterns_score(self, patterns: List[ArchitecturalPattern]) -> float:
        """Calculate score based on architectural patterns quality."""
        if not patterns:
            return 0.0
        
        # Average evidence strength across all patterns
        total_evidence = sum(pattern.evidence_strength for pattern in patterns)
        return total_evidence / len(patterns)


class SynapseExperimentConsolidator(ExperimentConsolidator):
    """Main implementation of experiment consolidation for the Synapse system."""
    
    def __init__(
        self,
        similarity_detector: Optional[SimilarityDetector] = None,
        metrics_extractor: Optional[MetricsExtractor] = None,
        pattern_recognizer: Optional[PatternRecognizer] = None,
        evidence_ranker: Optional[EvidenceRanker] = None,
    ):
        self.similarity_detector = similarity_detector or TextSimilarityDetector()
        self.metrics_extractor = metrics_extractor or RegexMetricsExtractor()
        self.pattern_recognizer = pattern_recognizer or KeywordPatternRecognizer()
        self.evidence_ranker = evidence_ranker or SimpleEvidenceRanker()
    
    async def discover_candidates(
        self, 
        search_path: str,
        file_patterns: List[str] = None
    ) -> List[ConsolidationCandidate]:
        """Discover documents that are candidates for consolidation."""
        if file_patterns is None:
            file_patterns = ["*.md", "*.txt", "*.rst"]
        
        candidates = []
        search_path_obj = Path(search_path)
        
        if not search_path_obj.exists():
            return candidates
        
        # Find all matching files
        for pattern in file_patterns:
            for file_path in search_path_obj.rglob(pattern):
                if file_path.is_file():
                    candidate = await self._create_candidate_from_file(file_path)
                    if candidate:
                        candidates.append(candidate)
        
        return candidates
    
    async def _create_candidate_from_file(self, file_path: Path) -> Optional[ConsolidationCandidate]:
        """Create a consolidation candidate from a file."""
        try:
            content = file_path.read_text(encoding='utf-8')
            
            # Generate content hash for deduplication
            content_hash = hashlib.md5(content.encode()).hexdigest()
            
            # Extract title from first line or filename
            lines = content.split('\n')
            title = ""
            for line in lines:
                if line.strip() and not line.startswith('#'):
                    title = line.strip()[:100]
                    break
                elif line.startswith('#'):
                    title = line.strip('#').strip()[:100]
                    break
            
            if not title:
                title = file_path.stem
            
            # Extract metrics and patterns
            metrics = await self.metrics_extractor.extract_metrics(content)
            patterns = await self.pattern_recognizer.identify_patterns(content)
            
            # Determine content type from path/name
            content_type = self._determine_content_type(file_path)
            
            return ConsolidationCandidate(
                document_id=str(file_path),
                file_path=str(file_path),
                content_hash=content_hash,
                title=title,
                content_preview=content[:500],
                extracted_metrics=metrics,
                architectural_patterns=patterns,
                metadata={
                    "file_size": file_path.stat().st_size,
                    "file_extension": file_path.suffix,
                    "relative_path": str(file_path.relative_to(file_path.parents[0])),
                },
                created_at=datetime.fromtimestamp(file_path.stat().st_mtime),
                content_type=content_type,
            )
        except (UnicodeDecodeError, OSError) as e:
            # Skip files that can't be read
            return None
    
    def _determine_content_type(self, file_path: Path) -> str:
        """Determine content type from file path patterns."""
        path_str = str(file_path).lower()
        
        if 'draft' in path_str:
            return 'draft'
        elif 'final' in path_str:
            return 'final'
        elif 'brief' in path_str:
            return 'brief'
        elif any(pattern in path_str for pattern in ['experiment', 'test', 'trial']):
            return 'experimental'
        else:
            return 'document'
    
    async def find_similar_documents(
        self,
        candidates: List[ConsolidationCandidate],
        similarity_threshold: float = SimilarityThreshold.HIGH_SIMILARITY.value
    ) -> List[SimilarityMatch]:
        """Find documents with high content similarity."""
        similarity_matches = []
        
        # Compare each pair of candidates
        for i, candidate_a in enumerate(candidates):
            for candidate_b in candidates[i + 1:]:
                # Skip identical files
                if candidate_a.content_hash == candidate_b.content_hash:
                    continue
                
                # Calculate similarity
                similarity_score = await self.similarity_detector.calculate_similarity(
                    candidate_a.content_preview, 
                    candidate_b.content_preview
                )
                
                if similarity_score >= similarity_threshold:
                    # Find similar sections for detailed analysis
                    similar_sections = await self.similarity_detector.find_similar_sections(
                        candidate_a.content_preview,
                        candidate_b.content_preview
                    )
                    
                    match = SimilarityMatch(
                        candidate_a=candidate_a,
                        candidate_b=candidate_b,
                        similarity_score=similarity_score,
                        matching_sections=[section[0] for section in similar_sections],
                        overlap_percentage=similarity_score,  # Simplified
                    )
                    similarity_matches.append(match)
        
        return similarity_matches
    
    async def consolidate_experiments(
        self,
        similarity_matches: List[SimilarityMatch]
    ) -> List[ConsolidatedExperiment]:
        """Consolidate similar documents into unified experiments."""
        consolidated_experiments = []
        processed_candidates = set()
        
        # Group similar documents together
        similarity_groups = self._group_similar_matches(similarity_matches)
        
        for group in similarity_groups:
            # Skip if any candidate already processed
            if any(candidate.document_id in processed_candidates for candidate in group):
                continue
            
            # Consolidate the group
            consolidated = await self._consolidate_candidate_group(group)
            consolidated_experiments.append(consolidated)
            
            # Mark candidates as processed
            for candidate in group:
                processed_candidates.add(candidate.document_id)
        
        # Rank by evidence strength
        ranked_experiments = await self.evidence_ranker.rank_by_evidence(
            consolidated_experiments
        )
        
        return ranked_experiments
    
    def _group_similar_matches(
        self, 
        similarity_matches: List[SimilarityMatch]
    ) -> List[List[ConsolidationCandidate]]:
        """Group similarity matches into candidate clusters."""
        # Build adjacency map
        adjacency = {}
        for match in similarity_matches:
            a_id = match.candidate_a.document_id
            b_id = match.candidate_b.document_id
            
            if a_id not in adjacency:
                adjacency[a_id] = set()
            if b_id not in adjacency:
                adjacency[b_id] = set()
            
            adjacency[a_id].add(b_id)
            adjacency[b_id].add(a_id)
        
        # Find connected components
        visited = set()
        groups = []
        
        # Create candidate lookup
        candidate_lookup = {}
        for match in similarity_matches:
            candidate_lookup[match.candidate_a.document_id] = match.candidate_a
            candidate_lookup[match.candidate_b.document_id] = match.candidate_b
        
        for candidate_id in adjacency:
            if candidate_id not in visited:
                group = []
                self._dfs_group(candidate_id, adjacency, visited, group, candidate_lookup)
                if group:
                    groups.append(group)
        
        return groups
    
    def _dfs_group(
        self, 
        candidate_id: str, 
        adjacency: Dict[str, set], 
        visited: set, 
        group: List[ConsolidationCandidate],
        candidate_lookup: Dict[str, ConsolidationCandidate]
    ):
        """Depth-first search to find connected candidate groups."""
        if candidate_id in visited:
            return
        
        visited.add(candidate_id)
        if candidate_id in candidate_lookup:
            group.append(candidate_lookup[candidate_id])
        
        for neighbor_id in adjacency.get(candidate_id, set()):
            self._dfs_group(neighbor_id, adjacency, visited, group, candidate_lookup)
    
    async def _consolidate_candidate_group(
        self, 
        candidates: List[ConsolidationCandidate]
    ) -> ConsolidatedExperiment:
        """Consolidate a group of similar candidates into a single experiment."""
        # Combine all metrics and patterns
        all_metrics = []
        all_patterns = []
        all_best_practices = []
        
        for candidate in candidates:
            all_metrics.extend(candidate.extracted_metrics)
            all_patterns.extend(candidate.architectural_patterns)
        
        # Deduplicate patterns by name
        unique_patterns = {}
        for pattern in all_patterns:
            if pattern.pattern_name not in unique_patterns:
                unique_patterns[pattern.pattern_name] = pattern
            else:
                # Merge evidence strength
                existing = unique_patterns[pattern.pattern_name]
                existing.evidence_strength = max(
                    existing.evidence_strength, 
                    pattern.evidence_strength
                )
        
        # Generate consolidated title and summary
        titles = [candidate.title for candidate in candidates]
        consolidated_title = f"Consolidated Experiment: {titles[0]}"
        
        summary = f"Consolidated analysis of {len(candidates)} similar experimental documents"
        
        # Calculate evidence ranking
        evidence_score = await self.evidence_ranker.calculate_evidence_score(
            all_metrics, list(unique_patterns.values())
        )
        
        # Generate recommendations based on patterns and metrics
        recommendations = self._generate_recommendations(all_metrics, list(unique_patterns.values()))
        
        return ConsolidatedExperiment(
            consolidated_id=f"consolidated_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            title=consolidated_title,
            summary=summary,
            source_candidates=candidates,
            proven_metrics=all_metrics,
            architectural_patterns=list(unique_patterns.values()),
            recommendations=recommendations,
            evidence_ranking=evidence_score,
            consolidation_confidence=min(1.0, len(candidates) * 0.2),  # Simple confidence calculation
        )
    
    def _generate_recommendations(
        self, 
        metrics: List[SuccessMetric], 
        patterns: List[ArchitecturalPattern]
    ) -> List[str]:
        """Generate recommendations based on extracted metrics and patterns."""
        recommendations = []
        
        # Recommendations based on high-confidence metrics
        high_confidence_metrics = [m for m in metrics if m.confidence_score > 0.7]
        if high_confidence_metrics:
            recommendations.append(
                f"Focus on proven performance improvements with {len(high_confidence_metrics)} high-confidence metrics"
            )
        
        # Recommendations based on architectural patterns
        high_evidence_patterns = [p for p in patterns if p.evidence_strength > 0.6]
        if high_evidence_patterns:
            pattern_names = [p.pattern_name for p in high_evidence_patterns]
            recommendations.append(
                f"Consider implementing proven patterns: {', '.join(pattern_names)}"
            )
        
        # General recommendations
        if metrics:
            recommendations.append("Prioritize approaches with quantifiable business impact")
        
        if patterns:
            recommendations.append("Follow established architectural patterns for reduced risk")
        
        return recommendations
    
    async def generate_report(
        self,
        candidates: List[ConsolidationCandidate],
        consolidated_experiments: List[ConsolidatedExperiment]
    ) -> ConsolidationReport:
        """Generate a comprehensive consolidation report."""
        # Find high-value patterns across all experiments
        all_patterns = []
        all_metrics = []
        
        for experiment in consolidated_experiments:
            all_patterns.extend(experiment.architectural_patterns)
            all_metrics.extend(experiment.proven_metrics)
        
        # Get top patterns by evidence strength
        high_value_patterns = sorted(
            all_patterns, 
            key=lambda p: p.evidence_strength, 
            reverse=True
        )[:10]
        
        # Get top metrics by confidence
        top_metrics = sorted(
            all_metrics, 
            key=lambda m: m.confidence_score, 
            reverse=True
        )[:10]
        
        # Generate summary recommendations
        summary_recommendations = [
            f"Analyzed {len(candidates)} experimental documents",
            f"Found {len(consolidated_experiments)} consolidation opportunities",
            f"Identified {len(high_value_patterns)} high-value architectural patterns",
            f"Extracted {len(top_metrics)} quantifiable success metrics",
        ]
        
        # Calculate similarity matches found
        similarity_matches_count = sum(
            len(exp.source_candidates) - 1 for exp in consolidated_experiments
        )
        
        return ConsolidationReport(
            total_candidates_analyzed=len(candidates),
            similarity_matches_found=similarity_matches_count,
            experiments_consolidated=consolidated_experiments,
            high_value_patterns=high_value_patterns,
            top_performing_metrics=top_metrics,
            recommendations=summary_recommendations,
            processing_summary={
                "consolidation_threshold": SimilarityThreshold.HIGH_SIMILARITY.value,
                "patterns_identified": len(all_patterns),
                "metrics_extracted": len(all_metrics),
                "average_evidence_score": sum(exp.evidence_ranking for exp in consolidated_experiments) / len(consolidated_experiments) if consolidated_experiments else 0.0,
            },
        )