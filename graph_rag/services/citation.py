"""Citation system for Graph RAG answer synthesis."""

import difflib
import logging
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from graph_rag.models import Chunk

logger = logging.getLogger(__name__)


class CitationStyle(Enum):
    """Supported citation styles."""
    APA = "apa"
    MLA = "mla"
    CHICAGO = "chicago"
    IEEE = "ieee"
    NUMERIC = "numeric"


@dataclass
class VerificationResult:
    """Result of chunk verification against answer content."""

    # Verification metrics
    is_verified: bool = False
    confidence_score: float = 0.0
    verification_method: str = "keyword_overlap"

    # Content analysis
    exact_matches: list[str] = field(default_factory=list)
    paraphrase_matches: list[str] = field(default_factory=list)
    keyword_overlap_ratio: float = 0.0

    # Context tracking
    answer_segments: list[str] = field(default_factory=list)  # Parts of answer that use this chunk
    chunk_segments: list[str] = field(default_factory=list)   # Parts of chunk that are referenced

    # Quality indicators
    hallucination_risk: bool = False
    unsupported_claims: list[str] = field(default_factory=list)


@dataclass
class CitationMetadata:
    """Metadata for a citation source."""

    # Core identification
    chunk_id: str
    document_id: str

    # Document metadata
    title: str | None = None
    author: str | None = None
    source: str | None = None
    url: str | None = None
    publication_date: str | None = None
    page_number: str | None = None

    # Context metadata
    relevance_score: float | None = None
    chunk_text: str | None = None
    context_snippet: str | None = None

    # Enhanced verification
    verification: VerificationResult = field(default_factory=VerificationResult)

    # Usage tracking
    used_in_answer: bool = True
    inline_references: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "chunk_id": self.chunk_id,
            "document_id": self.document_id,
            "title": self.title,
            "author": self.author,
            "source": self.source,
            "url": self.url,
            "publication_date": self.publication_date,
            "page_number": self.page_number,
            "relevance_score": self.relevance_score,
            "context_snippet": self.context_snippet,
            "verification": {
                "is_verified": self.verification.is_verified,
                "confidence_score": self.verification.confidence_score,
                "verification_method": self.verification.verification_method,
                "keyword_overlap_ratio": self.verification.keyword_overlap_ratio,
                "exact_matches": self.verification.exact_matches,
                "paraphrase_matches": self.verification.paraphrase_matches,
                "hallucination_risk": self.verification.hallucination_risk,
                "unsupported_claims": self.verification.unsupported_claims,
            },
            "used_in_answer": self.used_in_answer,
            "inline_references": self.inline_references,
        }


@dataclass
class CitationResult:
    """Result of citation processing."""

    # Enhanced answer with citation markers
    answer_with_citations: str

    # Citation metadata
    citations: list[CitationMetadata]

    # Formatted bibliography
    bibliography: dict[str, str]  # style -> formatted text

    # Processing metadata
    total_sources: int = 0
    sources_cited: int = 0
    citation_style: CitationStyle = CitationStyle.NUMERIC


class CitationFormatter(ABC):
    """Abstract base class for citation formatters."""

    @abstractmethod
    def format_inline_citation(self, citation_num: int, metadata: CitationMetadata) -> str:
        """Format an inline citation marker."""
        pass

    @abstractmethod
    def format_bibliography_entry(self, citation_num: int, metadata: CitationMetadata) -> str:
        """Format a bibliography entry."""
        pass


class NumericCitationFormatter(CitationFormatter):
    """Numeric citation formatter [1], [2], etc."""

    def format_inline_citation(self, citation_num: int, metadata: CitationMetadata) -> str:
        """Format as [1], [2], etc."""
        return f"[{citation_num}]"

    def format_bibliography_entry(self, citation_num: int, metadata: CitationMetadata) -> str:
        """Format bibliography entry."""
        parts = [f"[{citation_num}]"]

        if metadata.author:
            parts.append(f"{metadata.author}.")

        if metadata.title:
            parts.append(f'"{metadata.title}"')

        if metadata.source:
            parts.append(metadata.source)

        if metadata.publication_date:
            parts.append(f"({metadata.publication_date})")

        if metadata.url:
            parts.append(f"Available: {metadata.url}")

        return " ".join(parts)


class APACitationFormatter(CitationFormatter):
    """APA style citation formatter."""

    def format_inline_citation(self, citation_num: int, metadata: CitationMetadata) -> str:
        """Format APA inline citation."""
        if metadata.author and metadata.publication_date:
            return f"({metadata.author}, {metadata.publication_date})"
        elif metadata.author:
            return f"({metadata.author})"
        elif metadata.title:
            return f"(\"{metadata.title}\")"
        else:
            return f"[{citation_num}]"

    def format_bibliography_entry(self, citation_num: int, metadata: CitationMetadata) -> str:
        """Format APA bibliography entry."""
        parts = []

        if metadata.author:
            parts.append(f"{metadata.author}")

        if metadata.publication_date:
            parts.append(f"({metadata.publication_date}).")

        if metadata.title:
            parts.append(f"{metadata.title}.")

        if metadata.source:
            parts.append(f"*{metadata.source}*")

        if metadata.url:
            parts.append(f"Retrieved from {metadata.url}")

        return " ".join(parts)


class CitationService:
    """Service for managing citations in answer synthesis."""

    def __init__(self, citation_style: CitationStyle = CitationStyle.NUMERIC):
        self.citation_style = citation_style
        self.formatter = self._get_formatter(citation_style)

    def _get_formatter(self, style: CitationStyle) -> CitationFormatter:
        """Get appropriate formatter for citation style."""
        if style == CitationStyle.NUMERIC:
            return NumericCitationFormatter()
        elif style == CitationStyle.APA:
            return APACitationFormatter()
        else:
            # Default to numeric
            logger.warning(f"Unsupported citation style: {style}. Using numeric.")
            return NumericCitationFormatter()

    def extract_metadata_from_chunk(self, chunk: Chunk) -> CitationMetadata:
        """Extract citation metadata from a chunk."""
        properties = chunk.metadata or {}

        # Extract metadata from chunk properties
        title = properties.get("title") or properties.get("document_title")
        author = properties.get("author") or properties.get("document_author")
        source = properties.get("source") or properties.get("document_source")
        url = properties.get("url") or properties.get("document_url")
        publication_date = properties.get("publication_date") or properties.get("created_at")
        page_number = properties.get("page_number") or properties.get("page")
        relevance_score = properties.get("score")

        # Create context snippet (first 200 chars)
        context_snippet = None
        if chunk.text and len(chunk.text) > 50:
            context_snippet = chunk.text[:200] + "..." if len(chunk.text) > 200 else chunk.text

        return CitationMetadata(
            chunk_id=chunk.id,
            document_id=chunk.document_id,
            title=title,
            author=author,
            source=source,
            url=url,
            publication_date=publication_date,
            page_number=page_number,
            relevance_score=relevance_score,
            chunk_text=chunk.text,
            context_snippet=context_snippet,
        )

    def enhance_answer_with_citations(
        self,
        answer: str,
        chunks: list[Chunk],
        context_texts: list[str] | None = None,
        enable_verification: bool = True
    ) -> CitationResult:
        """
        Enhance an answer with citation markers and generate bibliography.
        
        Args:
            answer: The generated answer text
            chunks: List of chunks that were available for the answer
            context_texts: Optional list of context texts that were actually used
            enable_verification: Whether to enable enhanced chunk verification
            
        Returns:
            CitationResult with enhanced answer and citation metadata
        """
        try:
            # Extract metadata from chunks
            all_citations = [self.extract_metadata_from_chunk(chunk) for chunk in chunks]

            # Enhanced verification if enabled
            if enable_verification:
                all_citations = self._verify_chunk_usage(answer, all_citations, context_texts or [])

            # If context texts provided, try to match chunks that were actually used
            if context_texts:
                used_citations = self._identify_used_chunks_enhanced(answer, all_citations, context_texts)
            else:
                # Use all verified chunks as potentially cited
                used_citations = [c for c in all_citations if c.verification.is_verified] or all_citations

            # Add inline citations to answer
            enhanced_answer = self._add_inline_citations(answer, used_citations)

            # Generate bibliography
            bibliography = self._generate_bibliography(used_citations)

            # Mark which citations were actually used
            for citation in used_citations:
                citation.used_in_answer = True

            return CitationResult(
                answer_with_citations=enhanced_answer,
                citations=all_citations,
                bibliography=bibliography,
                total_sources=len(all_citations),
                sources_cited=len(used_citations),
                citation_style=self.citation_style
            )

        except Exception as e:
            logger.error(f"Error enhancing answer with citations: {e}", exc_info=True)
            # Return basic result on error
            return CitationResult(
                answer_with_citations=answer,
                citations=[self.extract_metadata_from_chunk(chunk) for chunk in chunks],
                bibliography={},
                total_sources=len(chunks),
                sources_cited=0,
                citation_style=self.citation_style
            )

    def _identify_used_chunks(
        self,
        answer: str,
        citations: list[CitationMetadata],
        context_texts: list[str]
    ) -> list[CitationMetadata]:
        """
        Identify which chunks were likely used in generating the answer.
        
        Uses text similarity and keyword matching to determine usage.
        """
        used_citations = []

        # Simple approach: check if chunk content appears to be referenced in answer
        for citation in citations:
            if self._is_chunk_referenced(answer, citation, context_texts):
                used_citations.append(citation)

        # If no chunks identified as used, include all (conservative approach)
        if not used_citations:
            used_citations = citations

        return used_citations

    def _is_chunk_referenced(
        self,
        answer: str,
        citation: CitationMetadata,
        context_texts: list[str]
    ) -> bool:
        """
        Determine if a chunk appears to be referenced in the answer.
        
        Uses keyword overlap and content similarity heuristics.
        """
        if not citation.chunk_text:
            return True  # Conservative: include if no text to check

        # Check if the chunk text was part of the context provided to LLM
        chunk_in_context = any(citation.chunk_text in context for context in context_texts)

        if not chunk_in_context:
            return False

        # Extract key phrases from chunk (simple approach)
        chunk_keywords = set(self._extract_keywords(citation.chunk_text))
        answer_keywords = set(self._extract_keywords(answer))

        # Check for keyword overlap
        overlap = len(chunk_keywords.intersection(answer_keywords))
        overlap_ratio = overlap / len(chunk_keywords) if chunk_keywords else 0

        # Consider chunk referenced if significant keyword overlap
        return overlap_ratio > 0.3  # 30% keyword overlap threshold

    def _extract_keywords(self, text: str) -> list[str]:
        """Extract keywords from text (simple implementation)."""
        # Handle None or empty text
        if not text:
            return []
            
        # Remove common stop words and extract meaningful terms
        stop_words = {
            "the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for", "of", "with", "by",
            "is", "are", "was", "were", "be", "been", "being", "have", "has", "had", "do", "does", "did",
            "will", "would", "could", "should", "may", "might", "must", "can", "this", "that", "these", "those"
        }

        # Extract words (simple tokenization)
        words = re.findall(r'\b[a-zA-Z]{3,}\b', text.lower())
        keywords = [word for word in words if word not in stop_words]

        # Return unique keywords
        return list(set(keywords))

    def _add_inline_citations(
        self,
        answer: str,
        citations: list[CitationMetadata]
    ) -> str:
        """
        Add inline citation markers to the answer text.
        
        Uses sentence-based citation placement.
        """
        if not citations:
            return answer

        # Split answer into sentences
        sentences = re.split(r'(?<=[.!?])\s+', answer)

        # Add citations to sentences based on content similarity
        enhanced_sentences = []

        for sentence in sentences:
            # Find best matching citation for this sentence
            best_citation = self._find_best_citation_for_sentence(sentence, citations)

            if best_citation:
                citation_num = citations.index(best_citation) + 1
                citation_marker = self.formatter.format_inline_citation(citation_num, best_citation)
                enhanced_sentence = f"{sentence.strip()} {citation_marker}"
                best_citation.inline_references.append(sentence.strip()[:50] + "...")
            else:
                enhanced_sentence = sentence.strip()

            enhanced_sentences.append(enhanced_sentence)

        return " ".join(enhanced_sentences)

    def _find_best_citation_for_sentence(
        self,
        sentence: str,
        citations: list[CitationMetadata]
    ) -> CitationMetadata | None:
        """
        Find the best citation for a given sentence based on content similarity.
        """
        best_citation = None
        best_score = 0.0

        sentence_keywords = set(self._extract_keywords(sentence))

        for citation in citations:
            if not citation.chunk_text:
                continue

            chunk_keywords = set(self._extract_keywords(citation.chunk_text))
            overlap = len(sentence_keywords.intersection(chunk_keywords))

            if sentence_keywords:
                score = overlap / len(sentence_keywords)
                if score > best_score and score > 0.2:  # 20% overlap threshold
                    best_score = score
                    best_citation = citation

        return best_citation

    def _generate_bibliography(
        self,
        citations: list[CitationMetadata]
    ) -> dict[str, str]:
        """Generate formatted bibliography for different citation styles."""
        bibliography = {}

        # Generate for current style
        entries = []
        for i, citation in enumerate(citations, 1):
            entry = self.formatter.format_bibliography_entry(i, citation)
            entries.append(entry)

        bibliography[self.citation_style.value] = "\n".join(entries)

        return bibliography

    def _verify_chunk_usage(
        self,
        answer: str,
        citations: list[CitationMetadata],
        context_texts: list[str]
    ) -> list[CitationMetadata]:
        """
        Perform enhanced verification of chunk usage against answer content.
        
        Uses multiple verification methods including exact matching,
        paraphrase detection, and contextual analysis.
        """
        verified_citations = []

        for citation in citations:
            verification = self._perform_enhanced_verification(answer, citation, context_texts)
            citation.verification = verification
            verified_citations.append(citation)

            # Log verification results for debugging
            if verification.is_verified:
                logger.debug(f"Verified chunk {citation.chunk_id}: score={verification.confidence_score:.2f}")
            else:
                logger.debug(f"Failed to verify chunk {citation.chunk_id}")

        return verified_citations

    def _perform_enhanced_verification(
        self,
        answer: str,
        citation: CitationMetadata,
        context_texts: list[str]
    ) -> VerificationResult:
        """
        Perform comprehensive verification of a single chunk against the answer.
        """
        if not citation.chunk_text:
            return VerificationResult(
                is_verified=False,
                confidence_score=0.0,
                verification_method="no_content"
            )

        # 1. Check if chunk was in the context provided to LLM
        chunk_in_context = any(citation.chunk_text in context for context in context_texts)
        if not chunk_in_context:
            return VerificationResult(
                is_verified=False,
                confidence_score=0.0,
                verification_method="not_in_context"
            )

        # 2. Exact phrase matching
        exact_matches = self._find_exact_matches(answer, citation.chunk_text)

        # 3. Paraphrase detection (semantic similarity)
        paraphrase_matches = self._find_paraphrase_matches(answer, citation.chunk_text)

        # 4. Keyword overlap analysis
        overlap_ratio = self._calculate_keyword_overlap(answer, citation.chunk_text)

        # 5. Segment analysis
        answer_segments = self._find_answer_segments(answer, citation.chunk_text)
        chunk_segments = self._find_chunk_segments(citation.chunk_text, answer)

        # 6. Hallucination risk assessment
        hallucination_risk, unsupported_claims = self._assess_hallucination_risk(
            answer, citation.chunk_text, exact_matches, paraphrase_matches
        )

        # Calculate overall confidence score
        confidence_score = self._calculate_verification_confidence(
            exact_matches, paraphrase_matches, overlap_ratio, len(answer_segments)
        )

        # Determine if verified (threshold-based)
        is_verified = confidence_score >= 0.3 and not hallucination_risk

        return VerificationResult(
            is_verified=is_verified,
            confidence_score=confidence_score,
            verification_method="enhanced_multi_factor",
            exact_matches=exact_matches,
            paraphrase_matches=paraphrase_matches,
            keyword_overlap_ratio=overlap_ratio,
            answer_segments=answer_segments,
            chunk_segments=chunk_segments,
            hallucination_risk=hallucination_risk,
            unsupported_claims=unsupported_claims
        )

    def _find_exact_matches(self, answer: str, chunk_text: str, min_length: int = 10) -> list[str]:
        """Find exact phrase matches between answer and chunk."""
        exact_matches = []
        
        # Handle None values
        if not answer or not chunk_text:
            return exact_matches

        # Split into sentences and phrases
        chunk_sentences = re.split(r'[.!?]+', chunk_text)

        for sentence in chunk_sentences:
            sentence = sentence.strip()
            if len(sentence) >= min_length and sentence.lower() in answer.lower():
                exact_matches.append(sentence)

        # Also check for exact multi-word phrases
        chunk_words = chunk_text.split()
        for i in range(len(chunk_words) - 2):  # At least 3-word phrases
            for j in range(i + 3, min(i + 15, len(chunk_words) + 1)):  # Up to 15-word phrases
                phrase = ' '.join(chunk_words[i:j])
                if len(phrase) >= min_length and phrase.lower() in answer.lower():
                    exact_matches.append(phrase)

        return list(set(exact_matches))  # Remove duplicates

    def _find_paraphrase_matches(self, answer: str, chunk_text: str) -> list[str]:
        """
        Find potential paraphrases using sequence matching.
        
        This is a simplified implementation. In production, you might use
        more sophisticated NLP models for semantic similarity.
        """
        paraphrase_matches = []
        
        # Handle None values
        if not answer or not chunk_text:
            return paraphrase_matches

        # Split into sentences
        answer_sentences = re.split(r'[.!?]+', answer)
        chunk_sentences = re.split(r'[.!?]+', chunk_text)

        for chunk_sentence in chunk_sentences:
            chunk_sentence = chunk_sentence.strip()
            if len(chunk_sentence) < 20:  # Skip very short sentences
                continue

            for answer_sentence in answer_sentences:
                answer_sentence = answer_sentence.strip()
                if len(answer_sentence) < 20:
                    continue

                # Use sequence matching to find similar sentences
                similarity = difflib.SequenceMatcher(
                    None,
                    chunk_sentence.lower().split(),
                    answer_sentence.lower().split()
                ).ratio()

                if similarity > 0.6:  # 60% similarity threshold
                    paraphrase_matches.append(f"Chunk: '{chunk_sentence}' → Answer: '{answer_sentence}'")

        return paraphrase_matches

    def _calculate_keyword_overlap(self, answer: str, chunk_text: str) -> float:
        """Calculate keyword overlap ratio between answer and chunk."""
        chunk_keywords = set(self._extract_keywords(chunk_text))
        answer_keywords = set(self._extract_keywords(answer))

        if not chunk_keywords:
            return 0.0

        overlap = len(chunk_keywords.intersection(answer_keywords))
        return overlap / len(chunk_keywords)

    def _find_answer_segments(self, answer: str, chunk_text: str) -> list[str]:
        """Find segments of the answer that appear to use information from the chunk."""
        segments = []

        chunk_keywords = set(self._extract_keywords(chunk_text))
        answer_sentences = re.split(r'[.!?]+', answer)

        for sentence in answer_sentences:
            sentence = sentence.strip()
            if not sentence:
                continue

            sentence_keywords = set(self._extract_keywords(sentence))
            overlap = len(chunk_keywords.intersection(sentence_keywords))

            if overlap >= 2:  # At least 2 keyword matches
                segments.append(sentence)

        return segments

    def _find_chunk_segments(self, chunk_text: str, answer: str) -> list[str]:
        """Find segments of the chunk that appear to be referenced in the answer."""
        segments = []

        answer_keywords = set(self._extract_keywords(answer))
        chunk_sentences = re.split(r'[.!?]+', chunk_text)

        for sentence in chunk_sentences:
            sentence = sentence.strip()
            if not sentence:
                continue

            sentence_keywords = set(self._extract_keywords(sentence))
            overlap = len(answer_keywords.intersection(sentence_keywords))

            if overlap >= 2:  # At least 2 keyword matches
                segments.append(sentence)

        return segments

    def _assess_hallucination_risk(
        self,
        answer: str,
        chunk_text: str,
        exact_matches: list[str],
        paraphrase_matches: list[str]
    ) -> tuple[bool, list[str]]:
        """
        Assess potential hallucination risk by identifying unsupported claims.
        """
        unsupported_claims = []

        # Extract factual claims from answer (simplified approach)
        answer_sentences = re.split(r'[.!?]+', answer)
        chunk_keywords = set(self._extract_keywords(chunk_text))

        for sentence in answer_sentences:
            sentence = sentence.strip()
            if not sentence:
                continue

            # Check if sentence makes factual claims not supported by chunk
            if self._is_factual_claim(sentence):
                sentence_keywords = set(self._extract_keywords(sentence))
                support_ratio = len(sentence_keywords.intersection(chunk_keywords)) / len(sentence_keywords) if sentence_keywords else 0

                # If very low keyword support and no exact/paraphrase matches
                if support_ratio < 0.3 and not any(match in sentence for match in exact_matches):
                    unsupported_claims.append(sentence)

        # Determine hallucination risk
        hallucination_risk = len(unsupported_claims) > 2 or (len(unsupported_claims) > 0 and len(exact_matches) == 0)

        return hallucination_risk, unsupported_claims

    def _is_factual_claim(self, sentence: str) -> bool:
        """Determine if a sentence makes a factual claim (simplified heuristic)."""
        # Handle None or empty sentence
        if not sentence:
            return False
            
        # Look for patterns that suggest factual statements
        factual_patterns = [
            r'\b(is|are|was|were|has|have|will|did|does)\b',
            r'\b(according to|research shows|studies indicate)\b',
            r'\b\d+(\.\d+)?%\b',  # Percentages
            r'\b\d{4}\b',  # Years
            r'\b(first|second|third|last|most|least)\b'
        ]

        for pattern in factual_patterns:
            if re.search(pattern, sentence.lower()):
                return True

        return False

    def _calculate_verification_confidence(
        self,
        exact_matches: list[str],
        paraphrase_matches: list[str],
        overlap_ratio: float,
        answer_segments_count: int
    ) -> float:
        """Calculate overall verification confidence score."""

        # Base score from keyword overlap
        confidence = overlap_ratio * 0.4

        # Boost for exact matches
        if exact_matches:
            confidence += min(len(exact_matches) * 0.2, 0.4)

        # Boost for paraphrase matches
        if paraphrase_matches:
            confidence += min(len(paraphrase_matches) * 0.1, 0.2)

        # Boost for answer segments that use the chunk
        if answer_segments_count > 0:
            confidence += min(answer_segments_count * 0.05, 0.2)

        return min(1.0, confidence)

    def _identify_used_chunks_enhanced(
        self,
        answer: str,
        citations: list[CitationMetadata],
        context_texts: list[str]
    ) -> list[CitationMetadata]:
        """Enhanced version of chunk identification using verification results."""

        # Filter to verified chunks first
        verified_citations = [c for c in citations if c.verification.is_verified]

        if not verified_citations:
            # Fallback to original method if no chunks verified
            return self._identify_used_chunks(answer, citations, context_texts)

        # Sort by verification confidence
        verified_citations.sort(key=lambda c: c.verification.confidence_score, reverse=True)

        return verified_citations
