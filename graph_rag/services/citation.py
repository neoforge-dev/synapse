"""Citation system for Graph RAG answer synthesis."""

import json
import logging
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple, Union
from datetime import datetime

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
class CitationMetadata:
    """Metadata for a citation source."""
    
    # Core identification
    chunk_id: str
    document_id: str
    
    # Document metadata
    title: Optional[str] = None
    author: Optional[str] = None
    source: Optional[str] = None
    url: Optional[str] = None
    publication_date: Optional[str] = None
    page_number: Optional[str] = None
    
    # Context metadata
    relevance_score: Optional[float] = None
    chunk_text: Optional[str] = None
    context_snippet: Optional[str] = None
    
    # Usage tracking
    used_in_answer: bool = True
    inline_references: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
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
            "used_in_answer": self.used_in_answer,
            "inline_references": self.inline_references,
        }


@dataclass
class CitationResult:
    """Result of citation processing."""
    
    # Enhanced answer with citation markers
    answer_with_citations: str
    
    # Citation metadata
    citations: List[CitationMetadata]
    
    # Formatted bibliography
    bibliography: Dict[str, str]  # style -> formatted text
    
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
        chunks: List[Chunk],
        context_texts: Optional[List[str]] = None
    ) -> CitationResult:
        """
        Enhance an answer with citation markers and generate bibliography.
        
        Args:
            answer: The generated answer text
            chunks: List of chunks that were available for the answer
            context_texts: Optional list of context texts that were actually used
            
        Returns:
            CitationResult with enhanced answer and citation metadata
        """
        try:
            # Extract metadata from chunks
            all_citations = [self.extract_metadata_from_chunk(chunk) for chunk in chunks]
            
            # If context texts provided, try to match chunks that were actually used
            if context_texts:
                used_citations = self._identify_used_chunks(answer, all_citations, context_texts)
            else:
                # Use all chunks as potentially cited
                used_citations = all_citations
            
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
        citations: List[CitationMetadata],
        context_texts: List[str]
    ) -> List[CitationMetadata]:
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
        context_texts: List[str]
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
    
    def _extract_keywords(self, text: str) -> List[str]:
        """Extract keywords from text (simple implementation)."""
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
        citations: List[CitationMetadata]
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
        citations: List[CitationMetadata]
    ) -> Optional[CitationMetadata]:
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
        citations: List[CitationMetadata]
    ) -> Dict[str, str]:
        """Generate formatted bibliography for different citation styles."""
        bibliography = {}
        
        # Generate for current style
        entries = []
        for i, citation in enumerate(citations, 1):
            entry = self.formatter.format_bibliography_entry(i, citation)
            entries.append(entry)
        
        bibliography[self.citation_style.value] = "\n".join(entries)
        
        return bibliography