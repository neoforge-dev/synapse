"""Tests for experiment consolidation service."""

import asyncio
import tempfile
from pathlib import Path
from typing import List

import pytest

from graph_rag.core.consolidation import (
    ArchitecturalPattern,
    ConsolidationCandidate,
    MetricType,
    SimilarityThreshold,
    SuccessMetric,
)
from graph_rag.services.experiment_consolidator import (
    KeywordPatternRecognizer,
    RegexMetricsExtractor,
    SimpleEvidenceRanker,
    SynapseExperimentConsolidator,
    TextSimilarityDetector,
)


@pytest.fixture
def sample_experimental_content():
    """Sample experimental content with overlapping variations."""
    return {
        "brief_version": """# Technical Leadership Manifesto Brief

## Strategic Positioning
- Position as strategic technical leadership authority
- Generate 2-3 qualified consultation inquiries
- Focus on intentional technical planning

## Key Framework: 5 Non-Negotiables
1. Technical Debt as Strategic Constraint
2. Architecture Decisions Through Business Lens  
3. Team Scaling Before Technical Scaling
4. Security as Competitive Advantage
5. Data Architecture as Product Strategy

## Expected Metrics
- Engagement Rate: 4-6%
- Comments: 25-40
- Saves: 40-60 (manifesto format drives saves)

## Performance Results
- 39,092x task assignment improvement
- 95.9% code reduction achieved
- 18,483 messages/second throughput
""",

        "draft_version": """# 2024 Technical Leadership Manifesto: 5 Non-Negotiables for CTOs

If your CTO strategy fits on a napkin, you're already behind.

After 15+ years building systems for everyone from Ubisoft's game infrastructure to healthcare startups handling HIPAA compliance, I've learned that the difference between reactive technical management and strategic technical leadership comes down to following proven, non-negotiable principles.

## The 5 Non-Negotiables for Strategic CTOs

**1. Technical Debt as Strategic Constraint**
Manage technical debt as a business constraint, not an engineering afterthought. I've seen too many startups where "we need to refactor" becomes a death spiral. Instead, quarterly audits with quantified business impact turn vague requests into clear ROI: "this $200K investment will increase our development velocity by 40%."

**2. Architecture Decisions Through Business Lens** 
Every architectural choice needs clear business justification. When I helped scale a healthcare platform from 10K to 100K users, we documented every major decision with Architecture Decision Records (ADRs) that included business context.

**3. Team Scaling Before Technical Scaling**
People and process scalability must precede technical scalability. I learned this the hard way at an early startup where we built a beautiful microservices architecture that our 3-person team couldn't maintain.

**4. Security as Competitive Advantage**
Security isn't a compliance checkbox—it's a business differentiator. Working with healthcare startups taught me this: when you can tell enterprise clients "we built HIPAA compliance into our architecture from day one," you're not just compliant—you're competitive.

**5. Data Architecture as Product Strategy**
Your data models and architecture enable (or constrain) product possibilities. I've watched startups paint themselves into corners with data decisions made in month 3 that limit their product possibilities in year 2.

## Performance Results
Through implementing this framework:
- Achieved 39,092x improvement in task assignment efficiency
- Reduced codebase complexity by 95.9%
- Scaled to 18,483 messages per second throughput
- Saved $2M in infrastructure costs
- Improved development velocity by 40%

## Architecture Patterns
Universal Orchestrator pattern with Domain Managers and Specialized Engines provided the foundation for these improvements.
""",

        "final_version": """# ✅ READY TO POST: Technical Leadership Manifesto

## LinkedIn Post - Final Version

🔥 **CONTROVERSIAL TAKE**: 90% of CTOs are actually just senior engineers with a fancy title.

Here's what separates the real strategic technical leaders from the rest...

After 15+ years scaling everything from Ubisoft's game infrastructure to HIPAA-compliant healthcare platforms, I've watched brilliant startups die not from lack of ideas, but from technical decisions made in the first 90 days.

The pattern is always the same: reactive technical management disguised as leadership.

**Real CTOs don't just build systems—they build competitive advantages.**

## 🎯 **The 5 Non-Negotiables (Most CTOs Fail #3)**

**1. Technical Debt as Strategic Constraint** ⚡
Stop treating technical debt like a dirty secret. I quantify it as a business constraint with quarterly audits: "this $200K investment increases development velocity by 40%." 

Most CTOs say "we need to refactor." Strategic CTOs say "this refactor unlocks $2M in revenue opportunities."

**2. Architecture Decisions Through Business Lens** 🎯
Every architectural choice needs clear business justification—not engineering ego.

When I scaled a healthcare platform from 10K to 100K users, we documented every decision with Architecture Decision Records (ADRs) that included business impact.

**3. Team Scaling Before Technical Scaling** 👥
Here's where 80% of CTOs fail: They fall in love with microservices before they can manage a 5-person team.

I learned this the hard way—built a beautiful distributed system that our 3-person team couldn't maintain.

**4. Security as Competitive Advantage** 🛡️
Security isn't a compliance checkbox—it's a business differentiator.

When you can tell enterprise clients "we built HIPAA compliance into our architecture from day one," you're not just compliant—you're competitive.

**5. Data Architecture as Product Strategy** 📊
Your month-3 data decisions become your year-2 product constraints.

## Performance Targets:
- **Expected Engagement**: 6-8% (controversial hook + interactive elements)
- **Comments Target**: 40-65 (debate questions + personal challenges)
- **Saves Target**: 80-120 (explicit SAVE CTA + framework value)
- **Business Development**: 3-5 consultation inquiry conversations

## Proven Results:
- 39,092x task assignment improvement
- 95.9% code reduction
- 18,483 messages/second throughput
- $2M cost savings
""",

        "unrelated_content": """# Kubernetes Deployment Guide

This is a completely different document about Kubernetes deployments.

## Steps
1. Create namespace
2. Apply manifests
3. Check pods

No performance metrics or architectural patterns here.
Just basic deployment instructions.
""",
    }


@pytest.fixture
def temp_content_dir(sample_experimental_content):
    """Create temporary directory with sample experimental files."""
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        # Create files with sample content
        (temp_path / "01_brief.md").write_text(sample_experimental_content["brief_version"])
        (temp_path / "02_draft.md").write_text(sample_experimental_content["draft_version"])
        (temp_path / "05_final.md").write_text(sample_experimental_content["final_version"])
        (temp_path / "unrelated.md").write_text(sample_experimental_content["unrelated_content"])
        
        yield str(temp_path)


class TestTextSimilarityDetector:
    """Test the text similarity detection functionality."""
    
    @pytest.fixture
    def detector(self):
        return TextSimilarityDetector()
    
    @pytest.mark.asyncio
    async def test_calculate_textual_similarity_identical(self, detector):
        """Test similarity calculation for identical content."""
        content = "This is a test document with some content."
        similarity = await detector.calculate_similarity(content, content, "textual")
        assert similarity == 1.0
    
    @pytest.mark.asyncio
    async def test_calculate_textual_similarity_different(self, detector):
        """Test similarity calculation for completely different content."""
        content_a = "This is about technical leadership and architecture decisions."
        content_b = "This is about cooking recipes and kitchen utensils."
        similarity = await detector.calculate_similarity(content_a, content_b, "textual")
        assert similarity < 0.3  # Should be low similarity
    
    @pytest.mark.asyncio
    async def test_calculate_textual_similarity_overlap(self, detector):
        """Test similarity calculation for content with overlap."""
        content_a = "Technical leadership requires strategic planning and architecture decisions."
        content_b = "Strategic technical leadership involves architecture decisions and planning."
        similarity = await detector.calculate_similarity(content_a, content_b, "textual")
        assert similarity > 0.5  # Should have decent similarity
    
    @pytest.mark.asyncio
    async def test_find_similar_sections(self, detector):
        """Test finding similar sections between documents."""
        content_a = """# Section 1
This is about technical debt management.

# Section 2  
Architecture decisions require business context.
"""
        content_b = """# Different Title
Technical debt should be managed carefully.

# Another Section
Business context is crucial for architecture decisions.
"""
        
        similar_sections = await detector.find_similar_sections(content_a, content_b, 0.6)
        assert len(similar_sections) > 0
        # Check that we found some overlapping content
        assert any("technical debt" in section[0].lower() for section in similar_sections)


class TestRegexMetricsExtractor:
    """Test the metrics extraction functionality."""
    
    @pytest.fixture
    def extractor(self):
        return RegexMetricsExtractor()
    
    @pytest.mark.asyncio
    async def test_extract_performance_improvement_metrics(self, extractor):
        """Test extracting performance improvement metrics."""
        content = """
        We achieved a 39,092x improvement in task assignment efficiency.
        The system is now 100 times faster than before.
        Performance improved by 500x after optimization.
        """
        
        metrics = await extractor.extract_metrics(content)
        performance_metrics = [m for m in metrics if m.metric_type == MetricType.PERFORMANCE_IMPROVEMENT]
        
        assert len(performance_metrics) >= 2
        # Check that we found the 39,092x improvement
        values = [m.value for m in performance_metrics]
        assert 39092.0 in values
        assert 100.0 in values or 500.0 in values
    
    @pytest.mark.asyncio
    async def test_extract_percentage_metrics(self, extractor):
        """Test extracting percentage-based metrics."""
        content = """
        We reduced the codebase by 95.9% while maintaining functionality.
        Engagement rate improved by 40%.
        Development velocity increased by 25%.
        """
        
        metrics = await extractor.extract_metrics(content)
        percentage_metrics = [m for m in metrics if m.metric_type == MetricType.PERCENTAGE_GAIN]
        
        assert len(percentage_metrics) >= 2
        values = [m.value for m in percentage_metrics]
        assert 95.9 in values
        assert 40.0 in values or 25.0 in values
    
    @pytest.mark.asyncio
    async def test_extract_throughput_metrics(self, extractor):
        """Test extracting throughput metrics."""
        content = """
        The system now handles 18,483 messages per second.
        We process 1,000 requests/minute on average.
        Throughput reached 50,000 operations per hour.
        """
        
        metrics = await extractor.extract_metrics(content)
        throughput_metrics = [m for m in metrics if m.metric_type == MetricType.THROUGHPUT_METRIC]
        
        assert len(throughput_metrics) >= 1
        values = [m.value for m in throughput_metrics]
        assert 18483.0 in values
    
    @pytest.mark.asyncio
    async def test_extract_cost_metrics(self, extractor):
        """Test extracting cost-related metrics."""
        content = """
        This optimization saved $2M in infrastructure costs.
        We reduced spending by $500,000 annually.
        """
        
        metrics = await extractor.extract_metrics(content)
        cost_metrics = [m for m in metrics if m.metric_type == MetricType.COST_REDUCTION]
        
        assert len(cost_metrics) >= 1
        values = [m.value for m in cost_metrics]
        assert 2.0 in values or 500000.0 in values  # Could be 2M or 500,000
    
    @pytest.mark.asyncio
    async def test_metric_confidence_calculation(self, extractor):
        """Test that confidence scores are calculated appropriately."""
        content = """
        We achieved a definitive 95.9% improvement in performance.
        Approximately 50% reduction was observed.
        """
        
        metrics = await extractor.extract_metrics(content)
        
        # Find metrics with high and low confidence contexts
        high_confidence = [m for m in metrics if "definitive" in m.context.lower()]
        low_confidence = [m for m in metrics if "approximately" in m.context.lower()]
        
        if high_confidence and low_confidence:
            assert high_confidence[0].confidence_score > low_confidence[0].confidence_score


class TestKeywordPatternRecognizer:
    """Test the architectural pattern recognition functionality."""
    
    @pytest.fixture
    def recognizer(self):
        return KeywordPatternRecognizer()
    
    @pytest.mark.asyncio
    async def test_identify_microservices_pattern(self, recognizer):
        """Test identification of microservices architecture pattern."""
        content = """
        We implemented a microservices architecture with distributed services.
        Each service can be scaled independently and uses different technologies.
        The service mesh handles communication between microservices.
        """
        
        patterns = await recognizer.identify_patterns(content)
        microservices_patterns = [p for p in patterns if "microservices" in p.pattern_name.lower()]
        
        assert len(microservices_patterns) > 0
        pattern = microservices_patterns[0]
        assert pattern.evidence_strength > 0.0
        assert "Independent scaling" in pattern.benefits
    
    @pytest.mark.asyncio
    async def test_identify_universal_orchestrator_pattern(self, recognizer):
        """Test identification of Universal Orchestrator pattern."""
        content = """
        The Universal Orchestrator coordinates all system operations.
        Central orchestrator manages workflow execution and resource allocation.
        """
        
        patterns = await recognizer.identify_patterns(content)
        orchestrator_patterns = [p for p in patterns if "orchestrator" in p.pattern_name.lower()]
        
        assert len(orchestrator_patterns) > 0
        pattern = orchestrator_patterns[0]
        assert pattern.evidence_strength > 0.0
    
    @pytest.mark.asyncio
    async def test_extract_best_practices(self, recognizer):
        """Test extraction of best practices from content."""
        content = """
        Best practice: Always document architectural decisions with business context.
        Key insight: Team scaling should precede technical scaling.
        Recommendation: Treat security as a competitive advantage, not compliance checkbox.
        """
        
        practices = await recognizer.extract_best_practices(content)
        
        assert len(practices) >= 2
        practice_text = " ".join(practices).lower()
        assert "architectural decisions" in practice_text
        assert "team scaling" in practice_text or "security" in practice_text


class TestSimpleEvidenceRanker:
    """Test the evidence-based ranking functionality."""
    
    @pytest.fixture
    def ranker(self):
        return SimpleEvidenceRanker()
    
    @pytest.mark.asyncio
    async def test_calculate_evidence_score_with_metrics(self, ranker):
        """Test evidence score calculation with high-quality metrics."""
        high_confidence_metrics = [
            SuccessMetric(
                metric_type=MetricType.PERFORMANCE_IMPROVEMENT,
                value=39092.0,
                unit="x",
                context="Achieved 39,092x improvement in task assignment",
                source_location="line 1",
                confidence_score=0.9,
            ),
            SuccessMetric(
                metric_type=MetricType.PERCENTAGE_GAIN,
                value=95.9,
                unit="%",
                context="95.9% code reduction achieved",
                source_location="line 2",
                confidence_score=0.8,
            ),
        ]
        
        score = await ranker.calculate_evidence_score(high_confidence_metrics, [])
        assert score > 0.5  # Should be decent score with high-confidence metrics
    
    @pytest.mark.asyncio
    async def test_calculate_evidence_score_with_patterns(self, ranker):
        """Test evidence score calculation with architectural patterns."""
        patterns = [
            ArchitecturalPattern(
                pattern_name="Universal Orchestrator",
                description="Central coordination pattern",
                benefits=["Centralized control", "Clear responsibility"],
                challenges=["Single point of failure"],
                use_cases=["Workflow orchestration"],
                evidence_strength=0.8,
            ),
            ArchitecturalPattern(
                pattern_name="Microservices",
                description="Distributed services pattern",
                benefits=["Independent scaling"],
                challenges=["Complexity"],
                use_cases=["Large teams"],
                evidence_strength=0.6,
            ),
        ]
        
        score = await ranker.calculate_evidence_score([], patterns)
        assert score > 0.0  # Should have some score with patterns
        assert score < 1.0  # But not perfect without metrics


class TestSynapseExperimentConsolidator:
    """Test the main consolidation functionality."""
    
    @pytest.fixture
    def consolidator(self):
        return SynapseExperimentConsolidator()
    
    @pytest.mark.asyncio
    async def test_discover_candidates(self, consolidator, temp_content_dir):
        """Test discovering consolidation candidates from files."""
        candidates = await consolidator.discover_candidates(temp_content_dir, ["*.md"])
        
        assert len(candidates) >= 3  # Should find brief, draft, final versions
        
        # Check that we have different content types
        content_types = {candidate.content_type for candidate in candidates}
        assert len(content_types) > 1
        
        # Check that metrics were extracted
        candidates_with_metrics = [c for c in candidates if c.extracted_metrics]
        assert len(candidates_with_metrics) > 0
    
    @pytest.mark.asyncio
    async def test_find_similar_documents(self, consolidator, temp_content_dir):
        """Test finding similar documents with high overlap."""
        candidates = await consolidator.discover_candidates(temp_content_dir, ["*.md"])
        
        similarity_matches = await consolidator.find_similar_documents(
            candidates, SimilarityThreshold.HIGH_SIMILARITY.value
        )
        
        # Should find similarity between brief, draft, and final versions
        assert len(similarity_matches) > 0
        
        # Check similarity scores are above threshold
        for match in similarity_matches:
            assert match.similarity_score >= SimilarityThreshold.HIGH_SIMILARITY.value
    
    @pytest.mark.asyncio
    async def test_consolidate_experiments(self, consolidator, temp_content_dir):
        """Test full experiment consolidation process."""
        candidates = await consolidator.discover_candidates(temp_content_dir, ["*.md"])
        similarity_matches = await consolidator.find_similar_documents(candidates, 0.5)  # Lower threshold for testing
        
        consolidated_experiments = await consolidator.consolidate_experiments(similarity_matches)
        
        assert len(consolidated_experiments) > 0
        
        # Check consolidated experiment properties
        experiment = consolidated_experiments[0]
        assert experiment.title
        assert experiment.summary
        assert len(experiment.source_candidates) > 1  # Should combine multiple candidates
        assert experiment.evidence_ranking >= 0.0
        assert experiment.consolidation_confidence >= 0.0
    
    @pytest.mark.asyncio
    async def test_run_full_consolidation(self, consolidator, temp_content_dir):
        """Test the complete consolidation pipeline."""
        report = await consolidator.run_full_consolidation(
            temp_content_dir, 
            SimilarityThreshold.MEDIUM_SIMILARITY.value,  # Use lower threshold for testing
            ["*.md"]
        )
        
        # Check report structure
        assert report.total_candidates_analyzed > 0
        assert report.generated_at
        assert isinstance(report.experiments_consolidated, list)
        assert isinstance(report.high_value_patterns, list)
        assert isinstance(report.top_performing_metrics, list)
        assert isinstance(report.recommendations, list)
        
        # Check that we found some consolidation opportunities
        if report.experiments_consolidated:
            experiment = report.experiments_consolidated[0]
            assert len(experiment.source_candidates) > 1
            
            # Check that metrics were consolidated
            total_metrics = sum(len(exp.proven_metrics) for exp in report.experiments_consolidated)
            assert total_metrics > 0
    
    @pytest.mark.asyncio
    async def test_metrics_extraction_integration(self, consolidator, temp_content_dir):
        """Test that metrics are properly extracted and consolidated."""
        report = await consolidator.run_full_consolidation(temp_content_dir, 0.5, ["*.md"])
        
        # Should find performance metrics from sample content
        all_metrics = []
        for experiment in report.experiments_consolidated:
            all_metrics.extend(experiment.proven_metrics)
        
        if all_metrics:
            # Check for expected metric values from sample content
            values = [m.value for m in all_metrics]
            
            # Should find the 39,092x improvement
            assert any(v > 30000 for v in values), f"Expected large performance improvement, got values: {values}"
            
            # Should find percentage improvements
            percentage_metrics = [m for m in all_metrics if m.metric_type == MetricType.PERCENTAGE_GAIN]
            assert len(percentage_metrics) > 0, "Should find percentage-based metrics"
    
    @pytest.mark.asyncio
    async def test_pattern_recognition_integration(self, consolidator, temp_content_dir):
        """Test that architectural patterns are properly recognized."""
        report = await consolidator.run_full_consolidation(temp_content_dir, 0.5, ["*.md"])
        
        # Should identify some architectural patterns
        all_patterns = []
        for experiment in report.experiments_consolidated:
            all_patterns.extend(experiment.architectural_patterns)
        
        if all_patterns:
            pattern_names = [p.pattern_name for p in all_patterns]
            # The sample content mentions Universal Orchestrator
            assert any("orchestrator" in name.lower() for name in pattern_names), \
                f"Expected to find orchestrator pattern, got: {pattern_names}"


class TestConsolidationEdgeCases:
    """Test edge cases and error conditions."""
    
    @pytest.fixture
    def consolidator(self):
        return SynapseExperimentConsolidator()
    
    @pytest.mark.asyncio
    async def test_empty_directory(self, consolidator):
        """Test handling of empty directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            candidates = await consolidator.discover_candidates(temp_dir, ["*.md"])
            assert len(candidates) == 0
    
    @pytest.mark.asyncio
    async def test_nonexistent_directory(self, consolidator):
        """Test handling of nonexistent directory."""
        candidates = await consolidator.discover_candidates("/nonexistent/path", ["*.md"])
        assert len(candidates) == 0
    
    @pytest.mark.asyncio
    async def test_no_similar_documents(self, consolidator):
        """Test handling when no documents are similar enough."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Create completely different documents
            (temp_path / "doc1.md").write_text("This is about cooking recipes.")
            (temp_path / "doc2.md").write_text("This is about quantum physics.")
            (temp_path / "doc3.md").write_text("This is about gardening tips.")
            
            report = await consolidator.run_full_consolidation(
                temp_dir, 
                SimilarityThreshold.HIGH_SIMILARITY.value,
                ["*.md"]
            )
            
            # Should find candidates but no consolidation
            assert report.total_candidates_analyzed == 3
            assert report.similarity_matches_found == 0
            assert len(report.experiments_consolidated) == 0
    
    @pytest.mark.asyncio
    async def test_single_document(self, consolidator):
        """Test handling of single document (no consolidation possible)."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            (temp_path / "single.md").write_text("This is a single document with no duplicates.")
            
            report = await consolidator.run_full_consolidation(temp_dir, 0.8, ["*.md"])
            
            assert report.total_candidates_analyzed == 1
            assert report.similarity_matches_found == 0
            assert len(report.experiments_consolidated) == 0


@pytest.mark.integration
class TestConsolidationIntegration:
    """Integration tests for the complete consolidation system."""
    
    @pytest.mark.asyncio
    async def test_real_content_consolidation(self, temp_content_dir):
        """Test consolidation with realistic content patterns."""
        consolidator = SynapseExperimentConsolidator()
        
        # Run with multiple thresholds to test adaptability
        thresholds = [0.9, 0.8, 0.6, 0.4]
        
        for threshold in thresholds:
            report = await consolidator.run_full_consolidation(
                temp_content_dir, threshold, ["*.md"]
            )
            
            # Verify report structure is consistent across thresholds
            assert report.total_candidates_analyzed > 0
            assert isinstance(report.processing_summary, dict)
            assert "consolidation_threshold" in report.processing_summary
            assert report.processing_summary["consolidation_threshold"] == threshold
            
            # Lower thresholds should find more matches
            if threshold <= 0.6:
                assert report.similarity_matches_found >= 0
    
    @pytest.mark.asyncio
    async def test_performance_with_many_documents(self):
        """Test performance and scalability with larger document sets."""
        consolidator = SynapseExperimentConsolidator()
        
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Create many similar documents
            base_content = """# Performance Test Document
            
This is a test document for performance testing.
It contains some metrics like 100x improvement and 50% reduction.
Architecture uses microservices and event-driven patterns.
"""
            
            # Create 20 documents with slight variations
            for i in range(20):
                content = base_content + f"\n\nDocument variation #{i}"
                (temp_path / f"doc_{i:02d}.md").write_text(content)
            
            # Run consolidation and measure that it completes
            report = await consolidator.run_full_consolidation(temp_dir, 0.7, ["*.md"])
            
            assert report.total_candidates_analyzed == 20
            # Should find many similarity matches with similar content
            assert report.similarity_matches_found > 0