"""Answer validation service for Graph RAG synthesis."""

import logging
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple
import difflib

from graph_rag.models import Chunk
from graph_rag.services.citation import CitationMetadata, VerificationResult

logger = logging.getLogger(__name__)


class ValidationLevel(Enum):
    """Validation levels for answer quality."""
    STRICT = "strict"        # High threshold, minimal tolerance for inconsistencies
    MODERATE = "moderate"    # Balanced validation with reasonable tolerance
    LENIENT = "lenient"      # Lower threshold, more permissive


class ClaimType(Enum):
    """Types of claims that can be made in answers."""
    FACTUAL = "factual"         # Specific facts, numbers, dates
    DESCRIPTIVE = "descriptive" # Descriptions of concepts, processes
    RELATIONAL = "relational"   # Relationships between entities
    EVALUATIVE = "evaluative"   # Judgments, opinions, assessments


@dataclass
class ValidationIssue:
    """Represents a validation issue found in the answer."""
    
    # Issue identification
    issue_type: str  # e.g., "unsupported_claim", "factual_inconsistency", "missing_citation"
    severity: str    # "high", "medium", "low"
    
    # Content details
    claim_text: str
    claim_type: ClaimType
    
    # Source analysis
    supporting_chunks: List[str] = field(default_factory=list)
    conflicting_chunks: List[str] = field(default_factory=list)
    
    # Context
    answer_segment: str = ""
    suggested_fix: Optional[str] = None
    
    # Metrics
    confidence_impact: float = 0.0  # How much this affects overall confidence


@dataclass
class ValidationResult:
    """Result of answer validation against source chunks."""
    
    # Overall validation
    is_valid: bool = True
    validation_score: float = 1.0  # 0.0 to 1.0
    validation_level: ValidationLevel = ValidationLevel.MODERATE
    
    # Issues found
    issues: List[ValidationIssue] = field(default_factory=list)
    
    # Claim analysis
    total_claims: int = 0
    supported_claims: int = 0
    unsupported_claims: int = 0
    conflicting_claims: int = 0
    
    # Coverage analysis
    chunk_coverage: float = 0.0      # What portion of chunks are referenced
    answer_coverage: float = 0.0     # What portion of answer is supported
    
    # Quality indicators
    hallucination_risk: bool = False
    requires_fact_check: bool = False
    citation_completeness: float = 0.0
    
    # Recommendations
    recommendations: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "is_valid": self.is_valid,
            "validation_score": self.validation_score,
            "validation_level": self.validation_level.value,
            "issues": [
                {
                    "issue_type": issue.issue_type,
                    "severity": issue.severity,
                    "claim_text": issue.claim_text,
                    "claim_type": issue.claim_type.value,
                    "supporting_chunks": issue.supporting_chunks,
                    "conflicting_chunks": issue.conflicting_chunks,
                    "answer_segment": issue.answer_segment,
                    "suggested_fix": issue.suggested_fix,
                    "confidence_impact": issue.confidence_impact,
                }
                for issue in self.issues
            ],
            "total_claims": self.total_claims,
            "supported_claims": self.supported_claims,
            "unsupported_claims": self.unsupported_claims,
            "conflicting_claims": self.conflicting_claims,
            "chunk_coverage": self.chunk_coverage,
            "answer_coverage": self.answer_coverage,
            "hallucination_risk": self.hallucination_risk,
            "requires_fact_check": self.requires_fact_check,
            "citation_completeness": self.citation_completeness,
            "recommendations": self.recommendations,
        }


class AnswerValidator:
    """Service for validating answers against source chunks."""
    
    def __init__(self, validation_level: ValidationLevel = ValidationLevel.MODERATE):
        self.validation_level = validation_level
        self.thresholds = self._get_validation_thresholds(validation_level)
        
    def _get_validation_thresholds(self, level: ValidationLevel) -> Dict[str, float]:
        """Get validation thresholds based on validation level."""
        if level == ValidationLevel.STRICT:
            return {
                "min_support_ratio": 0.8,
                "max_unsupported_ratio": 0.1,
                "min_chunk_coverage": 0.6,
                "factual_accuracy_threshold": 0.9,
                "citation_completeness_threshold": 0.8,
            }
        elif level == ValidationLevel.MODERATE:
            return {
                "min_support_ratio": 0.6,
                "max_unsupported_ratio": 0.2,
                "min_chunk_coverage": 0.4,
                "factual_accuracy_threshold": 0.7,
                "citation_completeness_threshold": 0.6,
            }
        else:  # LENIENT
            return {
                "min_support_ratio": 0.4,
                "max_unsupported_ratio": 0.3,
                "min_chunk_coverage": 0.2,
                "factual_accuracy_threshold": 0.5,
                "citation_completeness_threshold": 0.4,
            }
    
    def validate_answer(
        self,
        answer: str,
        chunks: List[Chunk],
        citations: List[CitationMetadata],
        context_texts: Optional[List[str]] = None
    ) -> ValidationResult:
        """
        Validate an answer against source chunks.
        
        Args:
            answer: The generated answer text
            chunks: Source chunks that were available
            citations: Citation metadata with verification results
            context_texts: Context texts that were provided to LLM
            
        Returns:
            ValidationResult with detailed analysis
        """
        logger.info(f"Validating answer with {len(chunks)} chunks and {len(citations)} citations")
        
        try:
            # 1. Extract and classify claims from the answer
            claims = self._extract_claims(answer)
            
            # 2. Validate each claim against source chunks
            claim_validations = []
            for claim in claims:
                validation = self._validate_claim(claim, chunks, citations, context_texts or [])
                claim_validations.append(validation)
            
            # 3. Analyze coverage and completeness
            chunk_coverage = self._calculate_chunk_coverage(answer, chunks)
            answer_coverage = self._calculate_answer_coverage(answer, chunks, citations)
            citation_completeness = self._calculate_citation_completeness(claims, citations)
            
            # 4. Identify validation issues
            issues = []
            for claim, validation in zip(claims, claim_validations):
                if not validation["is_supported"]:
                    issues.append(self._create_validation_issue(claim, validation, chunks))
            
            # 5. Check for additional quality issues
            additional_issues = self._check_quality_issues(answer, chunks, citations)
            issues.extend(additional_issues)
            
            # 6. Calculate overall metrics
            total_claims = len(claims)
            supported_claims = sum(1 for val in claim_validations if val["is_supported"])
            unsupported_claims = total_claims - supported_claims
            conflicting_claims = sum(1 for val in claim_validations if val.get("has_conflict", False))
            
            # 7. Determine overall validation result
            support_ratio = supported_claims / total_claims if total_claims > 0 else 1.0
            unsupported_ratio = unsupported_claims / total_claims if total_claims > 0 else 0.0
            
            is_valid = (
                support_ratio >= self.thresholds["min_support_ratio"] and
                unsupported_ratio <= self.thresholds["max_unsupported_ratio"] and
                chunk_coverage >= self.thresholds["min_chunk_coverage"]
            )
            
            # 8. Calculate validation score
            validation_score = self._calculate_validation_score(
                support_ratio, chunk_coverage, answer_coverage, citation_completeness, len(issues)
            )
            
            # 9. Assess risks and recommendations
            hallucination_risk = unsupported_ratio > 0.3 or len([i for i in issues if i.severity == "high"]) > 0
            requires_fact_check = conflicting_claims > 0 or support_ratio < 0.7
            
            recommendations = self._generate_recommendations(
                is_valid, issues, support_ratio, chunk_coverage, citation_completeness
            )
            
            return ValidationResult(
                is_valid=is_valid,
                validation_score=validation_score,
                validation_level=self.validation_level,
                issues=issues,
                total_claims=total_claims,
                supported_claims=supported_claims,
                unsupported_claims=unsupported_claims,
                conflicting_claims=conflicting_claims,
                chunk_coverage=chunk_coverage,
                answer_coverage=answer_coverage,
                hallucination_risk=hallucination_risk,
                requires_fact_check=requires_fact_check,
                citation_completeness=citation_completeness,
                recommendations=recommendations
            )
            
        except Exception as e:
            logger.error(f"Error during answer validation: {e}", exc_info=True)
            return ValidationResult(
                is_valid=False,
                validation_score=0.0,
                validation_level=self.validation_level,
                issues=[ValidationIssue(
                    issue_type="validation_error",
                    severity="high",
                    claim_text="Validation process failed",
                    claim_type=ClaimType.FACTUAL,
                    suggested_fix=f"Validation error: {e}"
                )],
                hallucination_risk=True,
                requires_fact_check=True,
                recommendations=["Validation failed - manual review required"]
            )
    
    def _extract_claims(self, answer: str) -> List[Dict[str, Any]]:
        """Extract claims from the answer text."""
        claims = []
        
        # Split into sentences
        sentences = re.split(r'(?<=[.!?])\s+', answer)
        
        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence or len(sentence) < 10:  # Skip very short sentences
                continue
            
            # Classify claim type
            claim_type = self._classify_claim(sentence)
            
            # Extract key entities and facts
            entities = self._extract_entities_from_sentence(sentence)
            facts = self._extract_facts_from_sentence(sentence)
            
            claims.append({
                "text": sentence,
                "type": claim_type,
                "entities": entities,
                "facts": facts,
                "requires_verification": self._requires_verification(sentence, claim_type)
            })
        
        return claims
    
    def _classify_claim(self, sentence: str) -> ClaimType:
        """Classify the type of claim made in a sentence."""
        sentence_lower = sentence.lower()
        
        # Factual patterns (specific facts, numbers, dates)
        factual_patterns = [
            r'\b\d+%\b',           # Percentages
            r'\b\d{4}\b',          # Years
            r'\b\d+\.\d+\b',       # Decimal numbers
            r'\bwas\s+born\b',     # Birth facts
            r'\bdied\s+in\b',      # Death facts
            r'\bfounded\s+in\b',   # Founding facts
            r'\baccording\s+to\b', # Attribution
        ]
        
        for pattern in factual_patterns:
            if re.search(pattern, sentence_lower):
                return ClaimType.FACTUAL
        
        # Relational patterns (relationships between entities)
        relational_patterns = [
            r'\bis\s+the\s+\w+\s+of\b',  # "is the author of"
            r'\bworked\s+with\b',        # "worked with"
            r'\brelated\s+to\b',         # "related to"
            r'\binfluenced\s+by\b',      # "influenced by"
        ]
        
        for pattern in relational_patterns:
            if re.search(pattern, sentence_lower):
                return ClaimType.RELATIONAL
        
        # Evaluative patterns (judgments, assessments)
        evaluative_patterns = [
            r'\bis\s+important\b',
            r'\bis\s+significant\b',
            r'\bsuggests\s+that\b',
            r'\bimplies\s+that\b',
        ]
        
        for pattern in evaluative_patterns:
            if re.search(pattern, sentence_lower):
                return ClaimType.EVALUATIVE
        
        # Default to descriptive
        return ClaimType.DESCRIPTIVE
    
    def _extract_entities_from_sentence(self, sentence: str) -> List[str]:
        """Extract named entities from a sentence (simplified)."""
        # This is a simplified implementation
        # In production, you might use spaCy or other NLP libraries
        
        # Look for capitalized words that might be entities
        entities = []
        words = sentence.split()
        
        for i, word in enumerate(words):
            if word[0].isupper() and len(word) > 2:
                # Check if it's a multi-word entity
                entity = word
                j = i + 1
                while j < len(words) and words[j][0].isupper() and len(words[j]) > 2:
                    entity += " " + words[j]
                    j += 1
                entities.append(entity.strip('.,!?'))
        
        return entities
    
    def _extract_facts_from_sentence(self, sentence: str) -> List[str]:
        """Extract factual statements from a sentence."""
        facts = []
        
        # Extract numbers, dates, percentages
        number_matches = re.findall(r'\b\d+(?:\.\d+)?(?:%|,\d{3})*\b', sentence)
        facts.extend(number_matches)
        
        # Extract years
        year_matches = re.findall(r'\b(19|20)\d{2}\b', sentence)
        facts.extend(year_matches)
        
        return facts
    
    def _requires_verification(self, sentence: str, claim_type: ClaimType) -> bool:
        """Determine if a claim requires verification against sources."""
        # Factual claims always require verification
        if claim_type == ClaimType.FACTUAL:
            return True
        
        # Evaluative claims might not require strict verification
        if claim_type == ClaimType.EVALUATIVE:
            return False
        
        # Check for verifiable content
        verifiable_patterns = [
            r'\b(first|second|third|last|most|least)\b',
            r'\b\d+\b',  # Any numbers
            r'\b(before|after|during|in)\s+\d{4}\b',  # Temporal references
        ]
        
        for pattern in verifiable_patterns:
            if re.search(pattern, sentence.lower()):
                return True
        
        return True  # Default to requiring verification
    
    def _validate_claim(
        self,
        claim: Dict[str, Any],
        chunks: List[Chunk],
        citations: List[CitationMetadata],
        context_texts: List[str]
    ) -> Dict[str, Any]:
        """Validate a single claim against source chunks."""
        claim_text = claim["text"]
        
        # Find supporting evidence in chunks
        supporting_chunks = []
        conflicting_chunks = []
        support_scores = []
        
        for chunk in chunks:
            if not chunk.text:
                continue
            
            # Check if claim content is supported by chunk
            support_score = self._calculate_claim_support(claim_text, chunk.text)
            
            if support_score > 0.6:  # Strong support
                supporting_chunks.append(chunk.id)
                support_scores.append(support_score)
            elif self._check_conflict(claim_text, chunk.text):
                conflicting_chunks.append(chunk.id)
        
        # Check if claim was in the context provided to LLM
        in_context = any(claim_text.lower() in context.lower() for context in context_texts)
        
        # Determine if claim is supported
        is_supported = len(supporting_chunks) > 0 and (not conflicting_chunks or len(supporting_chunks) > len(conflicting_chunks))
        
        # Check for exact fact matches
        has_exact_matches = any(
            entity in chunk.text for chunk in chunks if chunk.text
            for entity in claim.get("entities", [])
        )
        
        return {
            "is_supported": is_supported,
            "support_score": max(support_scores) if support_scores else 0.0,
            "supporting_chunks": supporting_chunks,
            "conflicting_chunks": conflicting_chunks,
            "has_conflict": len(conflicting_chunks) > 0,
            "in_context": in_context,
            "has_exact_matches": has_exact_matches,
        }
    
    def _calculate_claim_support(self, claim: str, chunk_text: str) -> float:
        """Calculate how well a chunk supports a claim."""
        # Simple keyword-based support calculation
        claim_words = set(self._extract_keywords(claim))
        chunk_words = set(self._extract_keywords(chunk_text))
        
        if not claim_words:
            return 0.0
        
        # Calculate overlap
        overlap = len(claim_words.intersection(chunk_words))
        overlap_ratio = overlap / len(claim_words)
        
        # Boost for entity matches
        entity_boost = 0.0
        claim_entities = self._extract_entities_from_sentence(claim)
        for entity in claim_entities:
            if entity.lower() in chunk_text.lower():
                entity_boost += 0.1
        
        return min(1.0, overlap_ratio + entity_boost)
    
    def _check_conflict(self, claim: str, chunk_text: str) -> bool:
        """Check if chunk text conflicts with the claim."""
        # Look for explicit contradictions (simplified)
        contradiction_patterns = [
            (r'\bis\s+not\b', r'\bis\b'),
            (r'\bdid\s+not\b', r'\bdid\b'),
            (r'\bwas\s+not\b', r'\bwas\b'),
            (r'\bcannot\b', r'\bcan\b'),
        ]
        
        claim_lower = claim.lower()
        chunk_lower = chunk_text.lower()
        
        for neg_pattern, pos_pattern in contradiction_patterns:
            # If claim has negative form and chunk has positive form (or vice versa)
            if re.search(neg_pattern, claim_lower) and re.search(pos_pattern, chunk_lower):
                return True
            if re.search(pos_pattern, claim_lower) and re.search(neg_pattern, chunk_lower):
                return True
        
        return False
    
    def _extract_keywords(self, text: str) -> List[str]:
        """Extract keywords from text (reuse from citation service)."""
        stop_words = {
            "the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for", "of", "with", "by",
            "is", "are", "was", "were", "be", "been", "being", "have", "has", "had", "do", "does", "did",
            "will", "would", "could", "should", "may", "might", "must", "can", "this", "that", "these", "those"
        }
        
        words = re.findall(r'\b[a-zA-Z]{3,}\b', text.lower())
        keywords = [word for word in words if word not in stop_words]
        return list(set(keywords))
    
    def _calculate_chunk_coverage(self, answer: str, chunks: List[Chunk]) -> float:
        """Calculate what portion of chunks are referenced in the answer."""
        if not chunks:
            return 1.0
        
        referenced_chunks = 0
        answer_keywords = set(self._extract_keywords(answer))
        
        for chunk in chunks:
            if not chunk.text:
                continue
            
            chunk_keywords = set(self._extract_keywords(chunk.text))
            overlap = len(answer_keywords.intersection(chunk_keywords))
            
            if overlap >= 2:  # At least 2 keyword matches
                referenced_chunks += 1
        
        return referenced_chunks / len(chunks)
    
    def _calculate_answer_coverage(
        self, 
        answer: str, 
        chunks: List[Chunk], 
        citations: List[CitationMetadata]
    ) -> float:
        """Calculate what portion of the answer is supported by chunks."""
        answer_sentences = re.split(r'(?<=[.!?])\s+', answer)
        supported_sentences = 0
        
        for sentence in answer_sentences:
            sentence = sentence.strip()
            if not sentence or len(sentence) < 10:
                continue
            
            # Check if sentence has supporting evidence
            has_support = False
            for citation in citations:
                if citation.verification.is_verified:
                    # Check if this citation's chunk supports this sentence
                    if citation.chunk_text:
                        support_score = self._calculate_claim_support(sentence, citation.chunk_text)
                        if support_score > 0.4:
                            has_support = True
                            break
            
            if has_support:
                supported_sentences += 1
        
        return supported_sentences / len(answer_sentences) if answer_sentences else 1.0
    
    def _calculate_citation_completeness(
        self, 
        claims: List[Dict[str, Any]], 
        citations: List[CitationMetadata]
    ) -> float:
        """Calculate how complete the citations are for the claims made."""
        verifiable_claims = [c for c in claims if c.get("requires_verification", True)]
        
        if not verifiable_claims:
            return 1.0
        
        cited_claims = 0
        for claim in verifiable_claims:
            # Check if claim has corresponding citation
            has_citation = any(
                citation.verification.is_verified and
                any(segment in claim["text"] for segment in citation.verification.answer_segments)
                for citation in citations
            )
            
            if has_citation:
                cited_claims += 1
        
        return cited_claims / len(verifiable_claims)
    
    def _create_validation_issue(
        self, 
        claim: Dict[str, Any], 
        validation: Dict[str, Any],
        chunks: List[Chunk]
    ) -> ValidationIssue:
        """Create a validation issue for an unsupported claim."""
        
        if validation.get("has_conflict", False):
            issue_type = "factual_inconsistency"
            severity = "high"
            suggested_fix = "Review conflicting information in sources"
        elif not validation.get("in_context", False):
            issue_type = "claim_not_in_context"
            severity = "high"
            suggested_fix = "Claim appears to be generated without source context"
        else:
            issue_type = "unsupported_claim"
            severity = "medium"
            suggested_fix = "Add citation or verify against source material"
        
        return ValidationIssue(
            issue_type=issue_type,
            severity=severity,
            claim_text=claim["text"],
            claim_type=claim["type"],
            supporting_chunks=validation.get("supporting_chunks", []),
            conflicting_chunks=validation.get("conflicting_chunks", []),
            answer_segment=claim["text"],
            suggested_fix=suggested_fix,
            confidence_impact=0.2 if severity == "high" else 0.1
        )
    
    def _check_quality_issues(
        self, 
        answer: str, 
        chunks: List[Chunk], 
        citations: List[CitationMetadata]
    ) -> List[ValidationIssue]:
        """Check for additional quality issues beyond claim validation."""
        issues = []
        
        # Check for missing citations on factual statements
        factual_patterns = [r'\b\d+%\b', r'\b\d{4}\b', r'\baccording to\b']
        sentences = re.split(r'(?<=[.!?])\s+', answer)
        
        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue
            
            # Check if sentence contains factual information but no citation
            has_factual_content = any(re.search(pattern, sentence.lower()) for pattern in factual_patterns)
            
            if has_factual_content:
                # Check if sentence has citation markers
                has_citation_marker = bool(re.search(r'\[[0-9]+\]|\([^)]*\d{4}[^)]*\)', sentence))
                
                if not has_citation_marker:
                    issues.append(ValidationIssue(
                        issue_type="missing_citation",
                        severity="medium",
                        claim_text=sentence,
                        claim_type=ClaimType.FACTUAL,
                        answer_segment=sentence,
                        suggested_fix="Add citation for factual claim",
                        confidence_impact=0.05
                    ))
        
        return issues
    
    def _calculate_validation_score(
        self, 
        support_ratio: float, 
        chunk_coverage: float, 
        answer_coverage: float, 
        citation_completeness: float,
        num_issues: int
    ) -> float:
        """Calculate overall validation score."""
        
        # Base score from support metrics
        base_score = (
            support_ratio * 0.4 +
            chunk_coverage * 0.2 +
            answer_coverage * 0.2 +
            citation_completeness * 0.2
        )
        
        # Penalty for issues
        issue_penalty = min(num_issues * 0.05, 0.3)  # Max 30% penalty
        
        final_score = max(0.0, base_score - issue_penalty)
        return min(1.0, final_score)
    
    def _generate_recommendations(
        self,
        is_valid: bool,
        issues: List[ValidationIssue],
        support_ratio: float,
        chunk_coverage: float,
        citation_completeness: float
    ) -> List[str]:
        """Generate recommendations for improving answer quality."""
        recommendations = []
        
        if not is_valid:
            recommendations.append("Answer validation failed - review and revise")
        
        if support_ratio < 0.6:
            recommendations.append("Increase support for claims by citing more relevant sources")
        
        if chunk_coverage < 0.4:
            recommendations.append("Utilize more of the available source material")
        
        if citation_completeness < 0.6:
            recommendations.append("Add citations for factual claims and statements")
        
        # Issue-specific recommendations
        high_severity_issues = [i for i in issues if i.severity == "high"]
        if high_severity_issues:
            recommendations.append("Address high-severity validation issues immediately")
        
        conflict_issues = [i for i in issues if i.issue_type == "factual_inconsistency"]
        if conflict_issues:
            recommendations.append("Resolve factual inconsistencies with source material")
        
        missing_citation_issues = [i for i in issues if i.issue_type == "missing_citation"]
        if len(missing_citation_issues) > 2:
            recommendations.append("Add comprehensive citations for factual statements")
        
        if not recommendations:
            recommendations.append("Answer validation passed - quality is acceptable")
        
        return recommendations