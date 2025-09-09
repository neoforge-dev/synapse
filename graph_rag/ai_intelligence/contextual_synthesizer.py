"""Contextual Synthesizer for Epic 17 - Advanced GraphRAG Intelligence.

Provides domain-aware synthesis for enterprise scenarios with:
- Enterprise context understanding and adaptation
- Industry-specific knowledge synthesis
- Business domain expertise integration  
- Contextual relevance scoring and optimization
- Multi-modal information synthesis
"""

import asyncio
import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple
from uuid import uuid4

import numpy as np
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class BusinessDomain(Enum):
    """Business domain categories for context awareness."""
    TECHNOLOGY = "technology"
    FINANCE = "finance"
    HEALTHCARE = "healthcare"
    MANUFACTURING = "manufacturing"
    RETAIL = "retail"
    CONSULTING = "consulting"
    LEGAL = "legal"
    GOVERNMENT = "government"
    EDUCATION = "education"
    MEDIA = "media"
    REAL_ESTATE = "real_estate"
    ENERGY = "energy"


class ContextType(Enum):
    """Types of context for synthesis."""
    STRATEGIC = "strategic"          # Strategic planning context
    OPERATIONAL = "operational"      # Day-to-day operations
    FINANCIAL = "financial"          # Financial analysis context
    TECHNICAL = "technical"          # Technical implementation
    REGULATORY = "regulatory"        # Compliance and legal
    MARKET = "market"               # Market analysis context
    ORGANIZATIONAL = "organizational" # People and structure
    RISK = "risk"                   # Risk management context


class SynthesisMode(Enum):
    """Modes of information synthesis."""
    EXECUTIVE_SUMMARY = "executive_summary"    # C-suite focused
    TECHNICAL_ANALYSIS = "technical_analysis"   # Technical deep-dive
    STRATEGIC_INSIGHTS = "strategic_insights"   # Strategic recommendations
    OPERATIONAL_GUIDANCE = "operational_guidance" # Action-oriented
    COMPARATIVE_ANALYSIS = "comparative_analysis" # Comparison focus
    TREND_ANALYSIS = "trend_analysis"          # Pattern and trend focus


@dataclass
class ContextProfile:
    """Profile defining context for synthesis."""
    profile_id: str = field(default_factory=lambda: str(uuid4()))
    domain: BusinessDomain = BusinessDomain.TECHNOLOGY
    context_type: ContextType = ContextType.STRATEGIC
    synthesis_mode: SynthesisMode = SynthesisMode.EXECUTIVE_SUMMARY
    
    # Context parameters
    organizational_level: str = "executive"  # executive, management, operational
    industry_specifics: List[str] = field(default_factory=list)
    stakeholder_focus: List[str] = field(default_factory=list)
    decision_timeframe: str = "medium_term"  # short_term, medium_term, long_term
    risk_tolerance: str = "moderate"  # low, moderate, high
    
    # Synthesis preferences
    detail_level: str = "high_level"  # detailed, high_level, summary
    presentation_style: str = "professional"  # professional, technical, executive
    include_alternatives: bool = True
    confidence_reporting: bool = True
    
    # Domain-specific parameters
    domain_expertise: Dict[str, float] = field(default_factory=dict)
    context_weights: Dict[str, float] = field(default_factory=dict)
    terminology_preferences: Dict[str, str] = field(default_factory=dict)


@dataclass
class SynthesisResult:
    """Result of contextual synthesis."""
    result_id: str = field(default_factory=lambda: str(uuid4()))
    query: str = ""
    context_profile: Optional[ContextProfile] = None
    
    # Synthesis outputs
    synthesized_content: str = ""
    executive_summary: str = ""
    key_insights: List[str] = field(default_factory=list)
    strategic_implications: List[str] = field(default_factory=list)
    recommended_actions: List[str] = field(default_factory=list)
    
    # Quality metrics
    contextual_relevance_score: float = 0.0
    synthesis_confidence: float = 0.0
    completeness_score: float = 0.0
    stakeholder_alignment_score: float = 0.0
    
    # Supporting information
    source_analysis: Dict[str, Any] = field(default_factory=dict)
    confidence_intervals: Dict[str, Tuple[float, float]] = field(default_factory=dict)
    alternative_perspectives: List[str] = field(default_factory=list)
    risk_considerations: List[str] = field(default_factory=list)
    
    # Metadata
    synthesis_timestamp: str = ""
    processing_time: float = 0.0
    sources_analyzed: int = 0
    context_adaptations: List[str] = field(default_factory=list)


class DomainKnowledgeBase(BaseModel):
    """Knowledge base for domain-specific synthesis."""
    domain: BusinessDomain
    knowledge_areas: Dict[str, List[str]] = Field(default_factory=dict)
    terminology: Dict[str, str] = Field(default_factory=dict)
    best_practices: List[str] = Field(default_factory=list)
    common_patterns: List[str] = Field(default_factory=list)
    stakeholder_priorities: Dict[str, List[str]] = Field(default_factory=dict)
    decision_frameworks: List[str] = Field(default_factory=list)
    risk_factors: List[str] = Field(default_factory=list)
    success_metrics: List[str] = Field(default_factory=list)


class ContextualSynthesizer:
    """Advanced contextual synthesizer for enterprise scenarios."""
    
    def __init__(
        self,
        semantic_reasoning_engine=None,
        graph_repository=None,
        vector_store=None,
        llm_service=None
    ):
        """Initialize the contextual synthesizer."""
        self.semantic_reasoning_engine = semantic_reasoning_engine
        self.graph_repository = graph_repository
        self.vector_store = vector_store
        self.llm_service = llm_service
        
        # Domain knowledge bases
        self.domain_knowledge = self._initialize_domain_knowledge()
        
        # Context profiles cache
        self.context_profiles: Dict[str, ContextProfile] = {}
        self.synthesis_cache: Dict[str, SynthesisResult] = {}
        
        # Performance tracking
        self.synthesis_stats = {
            "syntheses_performed": 0,
            "avg_contextual_relevance": 0.0,
            "avg_synthesis_confidence": 0.0,
            "avg_processing_time": 0.0,
            "domain_usage": {domain.value: 0 for domain in BusinessDomain}
        }
    
    def _initialize_domain_knowledge(self) -> Dict[BusinessDomain, DomainKnowledgeBase]:
        """Initialize domain-specific knowledge bases."""
        knowledge_bases = {}
        
        # Technology domain
        knowledge_bases[BusinessDomain.TECHNOLOGY] = DomainKnowledgeBase(
            domain=BusinessDomain.TECHNOLOGY,
            knowledge_areas={
                "software_development": ["agile", "devops", "architecture", "testing"],
                "infrastructure": ["cloud", "security", "scalability", "monitoring"],
                "data_management": ["databases", "analytics", "governance", "privacy"],
                "emerging_tech": ["ai", "blockchain", "iot", "quantum"]
            },
            terminology={
                "scalability": "ability to handle increased workload",
                "devops": "development and operations integration",
                "microservices": "architectural approach with small services"
            },
            best_practices=[
                "Implement continuous integration/deployment",
                "Follow security-first design principles", 
                "Maintain comprehensive documentation",
                "Regular security audits and updates"
            ],
            stakeholder_priorities={
                "CTO": ["technical excellence", "innovation", "scalability"],
                "CEO": ["business value", "competitive advantage", "ROI"],
                "CISO": ["security", "compliance", "risk management"]
            },
            decision_frameworks=[
                "Technology Readiness Level (TRL)",
                "Total Cost of Ownership (TCO)",
                "Return on Investment (ROI)",
                "Risk-Benefit Analysis"
            ]
        )
        
        # Finance domain
        knowledge_bases[BusinessDomain.FINANCE] = DomainKnowledgeBase(
            domain=BusinessDomain.FINANCE,
            knowledge_areas={
                "financial_analysis": ["ratios", "forecasting", "budgeting", "variance"],
                "risk_management": ["credit", "market", "operational", "liquidity"],
                "compliance": ["regulations", "reporting", "audit", "governance"],
                "investment": ["valuation", "portfolio", "derivatives", "strategy"]
            },
            terminology={
                "liquidity": "ability to convert assets to cash quickly",
                "leverage": "use of borrowed money to increase investment",
                "diversification": "risk reduction through varied investments"
            },
            stakeholder_priorities={
                "CFO": ["financial performance", "risk management", "compliance"],
                "CEO": ["profitability", "growth", "shareholder value"],
                "Board": ["governance", "oversight", "strategic direction"]
            }
        )
        
        # Consulting domain
        knowledge_bases[BusinessDomain.CONSULTING] = DomainKnowledgeBase(
            domain=BusinessDomain.CONSULTING,
            knowledge_areas={
                "strategy": ["competitive_analysis", "market_positioning", "growth"],
                "operations": ["process_improvement", "efficiency", "transformation"],
                "change_management": ["organizational", "cultural", "technology"],
                "analytics": ["data_driven_insights", "predictive_modeling", "kpis"]
            },
            terminology={
                "value_proposition": "unique benefit offered to clients",
                "change_management": "structured approach to organizational change",
                "stakeholder_engagement": "active involvement of key parties"
            },
            stakeholder_priorities={
                "Partner": ["client_satisfaction", "revenue_growth", "reputation"],
                "Principal": ["project_delivery", "team_development", "expertise"],
                "Manager": ["execution_excellence", "resource_optimization", "quality"]
            }
        )
        
        return knowledge_bases
    
    async def synthesize_with_context(
        self,
        query: str,
        retrieved_information: List[Dict[str, Any]],
        context_profile: ContextProfile,
        reasoning_chain=None
    ) -> SynthesisResult:
        """Perform contextual synthesis with enterprise domain awareness."""
        start_time = asyncio.get_event_loop().time()
        
        result = SynthesisResult(
            query=query,
            context_profile=context_profile,
            synthesis_timestamp=str(asyncio.get_event_loop().time())
        )
        
        try:
            # Step 1: Analyze and adapt information to context
            adapted_info = await self._adapt_information_to_context(
                retrieved_information, context_profile
            )
            
            # Step 2: Apply domain-specific knowledge
            domain_enhanced_info = await self._enhance_with_domain_knowledge(
                adapted_info, context_profile.domain
            )
            
            # Step 3: Perform contextual synthesis
            synthesized_content = await self._synthesize_information(
                query, domain_enhanced_info, context_profile, reasoning_chain
            )
            
            # Step 4: Generate executive summary and insights
            executive_summary, insights = await self._generate_executive_insights(
                synthesized_content, context_profile
            )
            
            # Step 5: Extract strategic implications and actions
            implications, actions = await self._extract_strategic_elements(
                synthesized_content, context_profile
            )
            
            # Step 6: Calculate quality metrics
            quality_scores = await self._calculate_synthesis_quality(
                result, adapted_info, context_profile
            )
            
            # Step 7: Generate alternative perspectives
            alternatives = await self._generate_alternative_perspectives(
                synthesized_content, context_profile
            )
            
            # Populate result
            result.synthesized_content = synthesized_content
            result.executive_summary = executive_summary
            result.key_insights = insights
            result.strategic_implications = implications
            result.recommended_actions = actions
            result.alternative_perspectives = alternatives
            
            # Quality metrics
            result.contextual_relevance_score = quality_scores["contextual_relevance"]
            result.synthesis_confidence = quality_scores["synthesis_confidence"]
            result.completeness_score = quality_scores["completeness"]
            result.stakeholder_alignment_score = quality_scores["stakeholder_alignment"]
            
            # Processing metadata
            result.processing_time = asyncio.get_event_loop().time() - start_time
            result.sources_analyzed = len(retrieved_information)
            
            # Update performance stats
            self._update_synthesis_stats(result)
            
            # Cache the result
            self.synthesis_cache[result.result_id] = result
            
            logger.info(f"Contextual synthesis completed for query: {query[:100]}... "
                       f"Relevance: {result.contextual_relevance_score:.3f}, "
                       f"Confidence: {result.synthesis_confidence:.3f}")
            
            return result
            
        except Exception as e:
            logger.error(f"Error in contextual synthesis: {str(e)}")
            result.synthesized_content = f"Synthesis failed: {str(e)}"
            result.synthesis_confidence = 0.0
            return result
    
    async def _adapt_information_to_context(
        self,
        information: List[Dict[str, Any]],
        context_profile: ContextProfile
    ) -> List[Dict[str, Any]]:
        """Adapt retrieved information to the specific context."""
        adapted_info = []
        
        # Get domain knowledge for context adaptation
        domain_kb = self.domain_knowledge.get(context_profile.domain)
        
        for info_item in information:
            adapted_item = info_item.copy()
            
            # Apply context-specific weights
            relevance_score = self._calculate_contextual_relevance(
                info_item, context_profile, domain_kb
            )
            adapted_item["contextual_relevance"] = relevance_score
            
            # Adapt terminology for domain
            if domain_kb:
                adapted_item["content"] = self._adapt_terminology(
                    info_item.get("content", ""), domain_kb.terminology
                )
            
            # Tag with context type
            adapted_item["context_tags"] = self._generate_context_tags(
                info_item, context_profile
            )
            
            adapted_info.append(adapted_item)
        
        # Sort by contextual relevance
        adapted_info.sort(key=lambda x: x.get("contextual_relevance", 0.0), reverse=True)
        
        return adapted_info
    
    def _calculate_contextual_relevance(
        self,
        info_item: Dict[str, Any],
        context_profile: ContextProfile,
        domain_kb: Optional[DomainKnowledgeBase]
    ) -> float:
        """Calculate how relevant information is to the specific context."""
        base_relevance = info_item.get("relevance_score", 0.5)
        
        # Domain alignment score
        domain_score = 0.0
        if domain_kb:
            content = info_item.get("content", "").lower()
            domain_keywords = []
            for knowledge_area in domain_kb.knowledge_areas.values():
                domain_keywords.extend(knowledge_area)
            
            keyword_matches = sum(1 for keyword in domain_keywords if keyword in content)
            domain_score = min(1.0, keyword_matches / max(len(domain_keywords), 1))
        
        # Context type alignment
        context_score = 0.0
        context_keywords = {
            ContextType.STRATEGIC: ["strategy", "strategic", "vision", "goals", "objectives"],
            ContextType.OPERATIONAL: ["operations", "process", "workflow", "execution"],
            ContextType.FINANCIAL: ["financial", "cost", "budget", "revenue", "profit"],
            ContextType.TECHNICAL: ["technical", "technology", "implementation", "system"],
            ContextType.REGULATORY: ["compliance", "regulation", "policy", "governance"],
            ContextType.MARKET: ["market", "competitive", "customer", "industry"],
            ContextType.ORGANIZATIONAL: ["organization", "team", "people", "culture"],
            ContextType.RISK: ["risk", "threat", "vulnerability", "mitigation"]
        }
        
        context_words = context_keywords.get(context_profile.context_type, [])
        content = info_item.get("content", "").lower()
        context_matches = sum(1 for word in context_words if word in content)
        context_score = min(1.0, context_matches / max(len(context_words), 1))
        
        # Organizational level alignment
        level_multiplier = {
            "executive": 1.0 if context_profile.organizational_level == "executive" else 0.8,
            "management": 1.0 if context_profile.organizational_level == "management" else 0.9,
            "operational": 1.0 if context_profile.organizational_level == "operational" else 0.9
        }
        
        # Combine scores
        contextual_relevance = (
            base_relevance * 0.4 +
            domain_score * 0.3 +
            context_score * 0.2 +
            level_multiplier.get(context_profile.organizational_level, 0.8) * 0.1
        )
        
        return min(1.0, contextual_relevance)
    
    def _adapt_terminology(self, content: str, terminology: Dict[str, str]) -> str:
        """Adapt content terminology for domain-specific understanding."""
        adapted_content = content
        
        # Replace technical terms with domain-appropriate explanations
        for term, explanation in terminology.items():
            if term in adapted_content.lower():
                # Add explanation in parentheses after first occurrence
                adapted_content = adapted_content.replace(
                    term, f"{term} ({explanation})", 1
                )
        
        return adapted_content
    
    def _generate_context_tags(
        self, 
        info_item: Dict[str, Any], 
        context_profile: ContextProfile
    ) -> List[str]:
        """Generate context-specific tags for information items."""
        tags = []
        
        # Domain tags
        tags.append(f"domain:{context_profile.domain.value}")
        
        # Context type tags
        tags.append(f"context:{context_profile.context_type.value}")
        
        # Organizational level tags
        tags.append(f"level:{context_profile.organizational_level}")
        
        # Content type analysis
        content = info_item.get("content", "").lower()
        if any(word in content for word in ["recommend", "suggest", "propose"]):
            tags.append("actionable")
        if any(word in content for word in ["risk", "concern", "issue"]):
            tags.append("risk-related")
        if any(word in content for word in ["opportunity", "potential", "advantage"]):
            tags.append("opportunity")
        
        return tags
    
    async def _enhance_with_domain_knowledge(
        self,
        adapted_info: List[Dict[str, Any]],
        domain: BusinessDomain
    ) -> List[Dict[str, Any]]:
        """Enhance information with domain-specific knowledge."""
        domain_kb = self.domain_knowledge.get(domain)
        if not domain_kb:
            return adapted_info
        
        enhanced_info = []
        
        for info_item in adapted_info:
            enhanced_item = info_item.copy()
            
            # Add relevant best practices
            relevant_practices = self._find_relevant_practices(
                info_item, domain_kb.best_practices
            )
            enhanced_item["relevant_best_practices"] = relevant_practices
            
            # Add applicable patterns
            relevant_patterns = self._find_relevant_patterns(
                info_item, domain_kb.common_patterns
            )
            enhanced_item["relevant_patterns"] = relevant_patterns
            
            # Add risk considerations
            relevant_risks = self._find_relevant_risks(
                info_item, domain_kb.risk_factors
            )
            enhanced_item["risk_considerations"] = relevant_risks
            
            enhanced_info.append(enhanced_item)
        
        return enhanced_info
    
    def _find_relevant_practices(
        self, 
        info_item: Dict[str, Any], 
        best_practices: List[str]
    ) -> List[str]:
        """Find best practices relevant to the information item."""
        content = info_item.get("content", "").lower()
        relevant = []
        
        for practice in best_practices:
            # Simple keyword matching - can be enhanced with semantic similarity
            practice_keywords = practice.lower().split()
            if any(keyword in content for keyword in practice_keywords):
                relevant.append(practice)
        
        return relevant[:3]  # Limit to top 3
    
    def _find_relevant_patterns(
        self, 
        info_item: Dict[str, Any], 
        patterns: List[str]
    ) -> List[str]:
        """Find patterns relevant to the information item."""
        # Similar to best practices but for common patterns
        return []  # Simplified for demo
    
    def _find_relevant_risks(
        self, 
        info_item: Dict[str, Any], 
        risk_factors: List[str]
    ) -> List[str]:
        """Find risk factors relevant to the information item."""
        # Similar to best practices but for risk factors
        return []  # Simplified for demo
    
    async def _synthesize_information(
        self,
        query: str,
        enhanced_info: List[Dict[str, Any]],
        context_profile: ContextProfile,
        reasoning_chain=None
    ) -> str:
        """Synthesize information with contextual awareness."""
        if not enhanced_info:
            return "No relevant information available for synthesis."
        
        if self.llm_service:
            # Build comprehensive synthesis prompt
            synthesis_prompt = self._build_synthesis_prompt(
                query, enhanced_info, context_profile, reasoning_chain
            )
            
            try:
                response = await self.llm_service.generate(synthesis_prompt)
                return response.content if hasattr(response, 'content') else str(response)
            except Exception as e:
                logger.warning(f"LLM synthesis failed, using fallback: {str(e)}")
                return self._fallback_synthesis(query, enhanced_info, context_profile)
        else:
            return self._fallback_synthesis(query, enhanced_info, context_profile)
    
    def _build_synthesis_prompt(
        self,
        query: str,
        enhanced_info: List[Dict[str, Any]],
        context_profile: ContextProfile,
        reasoning_chain=None
    ) -> str:
        """Build comprehensive synthesis prompt for LLM."""
        prompt = f"""
        Synthesize the following information to answer the query with domain-specific expertise:
        
        Query: {query}
        
        Context Profile:
        - Domain: {context_profile.domain.value}
        - Context Type: {context_profile.context_type.value}
        - Synthesis Mode: {context_profile.synthesis_mode.value}
        - Organizational Level: {context_profile.organizational_level}
        - Detail Level: {context_profile.detail_level}
        
        Retrieved Information:
        """
        
        for i, info in enumerate(enhanced_info[:5]):  # Limit to top 5
            prompt += f"""
        
        Source {i+1}:
        Content: {info.get('content', '')[:500]}...
        Contextual Relevance: {info.get('contextual_relevance', 0.0):.2f}
        Best Practices: {', '.join(info.get('relevant_best_practices', []))}
        Risk Considerations: {', '.join(info.get('risk_considerations', []))}
        """
        
        if reasoning_chain:
            prompt += f"""
        
        Related Reasoning:
        {reasoning_chain.final_conclusion}
        (Confidence: {reasoning_chain.overall_confidence:.2f})
        """
        
        prompt += f"""
        
        Please provide a {context_profile.synthesis_mode.value} that:
        1. Directly addresses the query with domain expertise
        2. Incorporates relevant best practices and patterns
        3. Considers risk factors and mitigation strategies
        4. Provides actionable insights appropriate for {context_profile.organizational_level} level
        5. Maintains {context_profile.presentation_style} tone and style
        
        Structure your response with:
        - Executive Summary (2-3 sentences)
        - Key Insights (3-5 bullet points)
        - Strategic Implications (2-4 points)
        - Recommended Actions (3-5 actionable items)
        """
        
        return prompt
    
    def _fallback_synthesis(
        self, 
        query: str, 
        enhanced_info: List[Dict[str, Any]], 
        context_profile: ContextProfile
    ) -> str:
        """Fallback synthesis when LLM is unavailable."""
        # Extract top insights from enhanced information
        top_info = enhanced_info[:3]
        
        synthesis = f"Analysis for {context_profile.domain.value} domain:\n\n"
        
        for i, info in enumerate(top_info):
            synthesis += f"Key Point {i+1}: {info.get('content', '')[:200]}...\n"
            
            practices = info.get('relevant_best_practices', [])
            if practices:
                synthesis += f"Best Practice: {practices[0]}\n"
            
            risks = info.get('risk_considerations', [])
            if risks:
                synthesis += f"Risk Consideration: {risks[0]}\n"
            
            synthesis += "\n"
        
        synthesis += f"\nSynthesis confidence based on {len(enhanced_info)} sources "
        synthesis += f"with average relevance {np.mean([info.get('contextual_relevance', 0.0) for info in enhanced_info]):.2f}"
        
        return synthesis
    
    async def _generate_executive_insights(
        self, 
        synthesized_content: str, 
        context_profile: ContextProfile
    ) -> Tuple[str, List[str]]:
        """Generate executive summary and key insights."""
        # Extract key sentences for summary
        sentences = synthesized_content.split('. ')
        
        # Simple executive summary (first few sentences)
        executive_summary = '. '.join(sentences[:3]) + '.'
        
        # Extract insights (look for bullet points or numbered lists)
        insights = []
        for sentence in sentences:
            if any(keyword in sentence.lower() for keyword in ["key", "important", "significant", "critical"]):
                insights.append(sentence.strip())
        
        return executive_summary, insights[:5]
    
    async def _extract_strategic_elements(
        self, 
        synthesized_content: str, 
        context_profile: ContextProfile
    ) -> Tuple[List[str], List[str]]:
        """Extract strategic implications and recommended actions."""
        sentences = synthesized_content.split('. ')
        
        implications = []
        actions = []
        
        for sentence in sentences:
            sentence_lower = sentence.lower()
            
            # Look for implications
            if any(keyword in sentence_lower for keyword in ["implication", "means", "suggests", "indicates"]):
                implications.append(sentence.strip())
            
            # Look for actions
            if any(keyword in sentence_lower for keyword in ["recommend", "should", "need to", "action", "implement"]):
                actions.append(sentence.strip())
        
        return implications[:4], actions[:5]
    
    async def _calculate_synthesis_quality(
        self,
        result: SynthesisResult,
        adapted_info: List[Dict[str, Any]],
        context_profile: ContextProfile
    ) -> Dict[str, float]:
        """Calculate quality metrics for the synthesis."""
        scores = {}
        
        # Contextual relevance (average of source relevance scores)
        if adapted_info:
            scores["contextual_relevance"] = np.mean([
                info.get("contextual_relevance", 0.0) for info in adapted_info
            ])
        else:
            scores["contextual_relevance"] = 0.0
        
        # Synthesis confidence (based on content length and source quality)
        content_length = len(result.synthesized_content)
        source_quality = np.mean([info.get("relevance_score", 0.5) for info in adapted_info]) if adapted_info else 0.5
        scores["synthesis_confidence"] = min(1.0, (content_length / 1000) * source_quality)
        
        # Completeness (based on expected elements)
        completeness_elements = [
            bool(result.executive_summary),
            bool(result.key_insights),
            len(result.key_insights) >= 3,
            content_length > 500
        ]
        scores["completeness"] = sum(completeness_elements) / len(completeness_elements)
        
        # Stakeholder alignment (based on context profile matching)
        scores["stakeholder_alignment"] = 0.8  # Simplified - would analyze content alignment in practice
        
        return scores
    
    async def _generate_alternative_perspectives(
        self, 
        synthesized_content: str, 
        context_profile: ContextProfile
    ) -> List[str]:
        """Generate alternative perspectives on the synthesis."""
        alternatives = []
        
        # Generate alternatives based on different organizational levels
        if context_profile.organizational_level != "executive":
            alternatives.append("Executive perspective: Focus on strategic implications and ROI")
        
        if context_profile.organizational_level != "operational":
            alternatives.append("Operational perspective: Emphasize implementation and process changes")
        
        # Generate alternatives based on different time horizons
        if context_profile.decision_timeframe != "short_term":
            alternatives.append("Short-term focus: Immediate actions and quick wins")
        
        if context_profile.decision_timeframe != "long_term":
            alternatives.append("Long-term view: Strategic positioning and sustainable advantages")
        
        # Risk-based alternative
        alternatives.append("Risk-averse approach: Conservative recommendations with lower uncertainty")
        
        return alternatives[:5]
    
    def _update_synthesis_stats(self, result: SynthesisResult):
        """Update synthesis performance statistics."""
        self.synthesis_stats["syntheses_performed"] += 1
        
        # Update averages
        count = self.synthesis_stats["syntheses_performed"]
        
        # Contextual relevance
        old_relevance = self.synthesis_stats["avg_contextual_relevance"]
        new_relevance = ((old_relevance * (count - 1)) + result.contextual_relevance_score) / count
        self.synthesis_stats["avg_contextual_relevance"] = new_relevance
        
        # Synthesis confidence
        old_confidence = self.synthesis_stats["avg_synthesis_confidence"]
        new_confidence = ((old_confidence * (count - 1)) + result.synthesis_confidence) / count
        self.synthesis_stats["avg_synthesis_confidence"] = new_confidence
        
        # Processing time
        old_time = self.synthesis_stats["avg_processing_time"]
        new_time = ((old_time * (count - 1)) + result.processing_time) / count
        self.synthesis_stats["avg_processing_time"] = new_time
        
        # Domain usage
        if result.context_profile:
            domain = result.context_profile.domain.value
            self.synthesis_stats["domain_usage"][domain] += 1
    
    def create_context_profile(
        self,
        domain: BusinessDomain,
        context_type: ContextType,
        synthesis_mode: SynthesisMode,
        **kwargs
    ) -> ContextProfile:
        """Create a new context profile for synthesis."""
        profile = ContextProfile(
            domain=domain,
            context_type=context_type,
            synthesis_mode=synthesis_mode,
            **kwargs
        )
        
        self.context_profiles[profile.profile_id] = profile
        return profile
    
    def get_synthesis_result(self, result_id: str) -> Optional[SynthesisResult]:
        """Retrieve a synthesis result by ID."""
        return self.synthesis_cache.get(result_id)
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """Get synthesizer performance statistics."""
        return {
            **self.synthesis_stats,
            "cached_results": len(self.synthesis_cache),
            "context_profiles": len(self.context_profiles),
            "domain_knowledge_bases": len(self.domain_knowledge)
        }
    
    async def add_domain_knowledge(
        self, 
        domain: BusinessDomain, 
        knowledge_base: DomainKnowledgeBase
    ) -> bool:
        """Add or update domain-specific knowledge base."""
        try:
            self.domain_knowledge[domain] = knowledge_base
            logger.info(f"Added domain knowledge for {domain.value}")
            return True
        except Exception as e:
            logger.error(f"Failed to add domain knowledge: {str(e)}")
            return False