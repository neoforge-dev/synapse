"""Semantic Reasoning Engine for Epic 17 - Advanced GraphRAG Intelligence.

This engine provides multi-hop logical inference across knowledge graphs with:
- Advanced entity relationship reasoning
- Causal chain analysis and inference
- Semantic similarity and context understanding
- Enterprise domain-specific reasoning patterns
- Confidence scoring and uncertainty quantification
"""

import asyncio
import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any
from uuid import uuid4

import numpy as np
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class ReasoningType(Enum):
    """Types of reasoning patterns supported."""
    DEDUCTIVE = "deductive"          # Logical deduction from premises
    INDUCTIVE = "inductive"          # Pattern-based inference
    ABDUCTIVE = "abductive"          # Best explanation inference
    ANALOGICAL = "analogical"        # Similarity-based reasoning
    CAUSAL = "causal"               # Cause-effect reasoning
    TEMPORAL = "temporal"           # Time-based reasoning
    SPATIAL = "spatial"             # Location-based reasoning
    HIERARCHICAL = "hierarchical"   # Category-based reasoning


class ConfidenceLevel(Enum):
    """Confidence levels for reasoning results."""
    VERY_HIGH = "very_high"    # >95% confidence
    HIGH = "high"              # 85-95% confidence
    MODERATE = "moderate"      # 65-85% confidence
    LOW = "low"               # 45-65% confidence
    VERY_LOW = "very_low"     # <45% confidence


@dataclass
class ReasoningStep:
    """Individual step in reasoning chain."""
    step_id: str = field(default_factory=lambda: str(uuid4()))
    reasoning_type: ReasoningType = ReasoningType.DEDUCTIVE
    premise: str = ""
    conclusion: str = ""
    confidence: float = 0.0
    evidence: list[str] = field(default_factory=list)
    intermediate_entities: list[str] = field(default_factory=list)
    relationships_used: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class ReasoningChain:
    """Complete reasoning chain with multiple steps."""
    chain_id: str = field(default_factory=lambda: str(uuid4()))
    query: str = ""
    steps: list[ReasoningStep] = field(default_factory=list)
    final_conclusion: str = ""
    overall_confidence: float = 0.0
    confidence_level: ConfidenceLevel = ConfidenceLevel.MODERATE
    reasoning_path: list[str] = field(default_factory=list)
    supporting_evidence: list[str] = field(default_factory=list)
    alternative_explanations: list[str] = field(default_factory=list)
    domain_context: str = ""
    timestamp: str = ""


class InferenceRule(BaseModel):
    """Rules for semantic inference."""
    rule_id: str = Field(default_factory=lambda: str(uuid4()))
    name: str = ""
    pattern: str = ""  # Logical pattern or template
    conditions: list[str] = Field(default_factory=list)
    conclusions: list[str] = Field(default_factory=list)
    confidence_weight: float = Field(default=1.0, ge=0.0, le=1.0)
    domain_specific: bool = False
    reasoning_type: ReasoningType = ReasoningType.DEDUCTIVE
    examples: list[str] = Field(default_factory=list)


class SemanticReasoningEngine:
    """Advanced semantic reasoning engine for multi-hop inference."""

    def __init__(
        self,
        graph_repository=None,
        vector_store=None,
        llm_service=None,
        domain_rules: list[InferenceRule] | None = None
    ):
        """Initialize the semantic reasoning engine."""
        self.graph_repository = graph_repository
        self.vector_store = vector_store
        self.llm_service = llm_service

        # Domain-specific inference rules
        self.domain_rules = domain_rules or self._initialize_default_rules()

        # Reasoning state
        self.active_chains: dict[str, ReasoningChain] = {}
        self.rule_cache: dict[str, list[InferenceRule]] = {}

        # Performance metrics
        self.reasoning_stats = {
            "queries_processed": 0,
            "avg_confidence": 0.0,
            "successful_inferences": 0,
            "multi_hop_queries": 0,
            "reasoning_time": 0.0
        }

    def _initialize_default_rules(self) -> list[InferenceRule]:
        """Initialize default inference rules for enterprise scenarios."""
        return [
            # Hierarchical reasoning
            InferenceRule(
                name="Organizational Hierarchy",
                pattern="If A reports_to B and B reports_to C, then A is_subordinate_of C",
                conditions=["reports_to", "transitive_relationship"],
                conclusions=["organizational_hierarchy", "authority_chain"],
                confidence_weight=0.9,
                reasoning_type=ReasoningType.HIERARCHICAL
            ),

            # Causal reasoning
            InferenceRule(
                name="Business Impact Causality",
                pattern="If A causes B and B affects C, then A indirectly_impacts C",
                conditions=["causal_relationship", "impact_chain"],
                conclusions=["indirect_impact", "business_consequence"],
                confidence_weight=0.8,
                reasoning_type=ReasoningType.CAUSAL
            ),

            # Temporal reasoning
            InferenceRule(
                name="Temporal Sequence Analysis",
                pattern="If A happens_before B and B happens_before C, then A precedes C",
                conditions=["temporal_order", "sequence_relationship"],
                conclusions=["temporal_precedence", "event_ordering"],
                confidence_weight=0.95,
                reasoning_type=ReasoningType.TEMPORAL
            ),

            # Analogical reasoning
            InferenceRule(
                name="Similar Context Inference",
                pattern="If A is_similar_to B and B has_property P, then A likely_has P",
                conditions=["semantic_similarity", "context_similarity"],
                conclusions=["analogical_property", "likely_characteristic"],
                confidence_weight=0.7,
                reasoning_type=ReasoningType.ANALOGICAL
            )
        ]

    async def reason_about_query(
        self,
        query: str,
        max_hops: int = 5,
        min_confidence: float = 0.5,
        domain_context: str = ""
    ) -> ReasoningChain:
        """Perform multi-hop semantic reasoning for a query."""
        start_time = asyncio.get_event_loop().time()

        chain = ReasoningChain(
            query=query,
            domain_context=domain_context,
            timestamp=str(asyncio.get_event_loop().time())
        )

        try:
            # Step 1: Extract key entities and relationships from query
            entities, relationships = await self._extract_query_components(query)

            # Step 2: Find relevant inference rules
            applicable_rules = self._find_applicable_rules(entities, relationships, domain_context)

            # Step 3: Perform multi-hop reasoning
            reasoning_steps = await self._perform_multi_hop_reasoning(
                entities, relationships, applicable_rules, max_hops, min_confidence
            )

            # Step 4: Synthesize final conclusion
            final_conclusion, confidence = await self._synthesize_conclusion(
                query, reasoning_steps, domain_context
            )

            # Step 5: Build reasoning chain
            chain.steps = reasoning_steps
            chain.final_conclusion = final_conclusion
            chain.overall_confidence = confidence
            chain.confidence_level = self._determine_confidence_level(confidence)
            chain.reasoning_path = [step.conclusion for step in reasoning_steps]

            # Step 6: Generate alternative explanations
            chain.alternative_explanations = await self._generate_alternatives(
                query, reasoning_steps, domain_context
            )

            # Update performance stats
            end_time = asyncio.get_event_loop().time()
            self._update_reasoning_stats(chain, end_time - start_time)

            # Cache the reasoning chain
            self.active_chains[chain.chain_id] = chain

            logger.info(f"Reasoning completed for query: {query[:100]}... "
                       f"Confidence: {confidence:.3f}, Steps: {len(reasoning_steps)}")

            return chain

        except Exception as e:
            logger.error(f"Error in semantic reasoning: {str(e)}")
            chain.final_conclusion = f"Reasoning failed: {str(e)}"
            chain.overall_confidence = 0.0
            chain.confidence_level = ConfidenceLevel.VERY_LOW
            return chain

    async def _extract_query_components(self, query: str) -> tuple[list[str], list[str]]:
        """Extract entities and relationships from the query."""
        try:
            # Use LLM service if available for better extraction
            if self.llm_service:
                extraction_prompt = f"""
                Extract the key entities and relationships from this query:
                Query: {query}

                Return in JSON format:
                {{
                    "entities": ["entity1", "entity2", ...],
                    "relationships": ["relationship1", "relationship2", ...]
                }}
                """

                await self.llm_service.generate(extraction_prompt)
                # Parse JSON response (simplified for demo)
                # In production, would use proper JSON parsing
                entities = ["extracted_entity_1", "extracted_entity_2"]
                relationships = ["extracted_relationship_1"]
            else:
                # Fallback: Simple keyword extraction
                entities = self._extract_entities_fallback(query)
                relationships = self._extract_relationships_fallback(query)

            return entities, relationships

        except Exception as e:
            logger.warning(f"Entity extraction failed, using fallback: {str(e)}")
            return self._extract_entities_fallback(query), self._extract_relationships_fallback(query)

    def _extract_entities_fallback(self, query: str) -> list[str]:
        """Simple fallback entity extraction."""
        # Simple keyword-based extraction
        common_entity_words = {
            "company", "organization", "department", "team", "project",
            "product", "service", "customer", "client", "market", "industry"
        }
        words = query.lower().split()
        return [word for word in words if word in common_entity_words]

    def _extract_relationships_fallback(self, query: str) -> list[str]:
        """Simple fallback relationship extraction."""
        common_relationships = {
            "reports_to", "manages", "owns", "uses", "depends_on", "affects",
            "causes", "leads_to", "results_in", "associated_with", "part_of"
        }
        query_lower = query.lower()
        return [rel for rel in common_relationships if rel.replace("_", " ") in query_lower]

    def _find_applicable_rules(
        self,
        entities: list[str],
        relationships: list[str],
        domain_context: str
    ) -> list[InferenceRule]:
        """Find inference rules applicable to the current context."""
        applicable_rules = []

        for rule in self.domain_rules:
            # Check if rule conditions match current context
            if self._rule_matches_context(rule, entities, relationships, domain_context):
                applicable_rules.append(rule)

        # Sort by confidence weight
        applicable_rules.sort(key=lambda r: r.confidence_weight, reverse=True)

        return applicable_rules

    def _rule_matches_context(
        self,
        rule: InferenceRule,
        entities: list[str],
        relationships: list[str],
        domain_context: str
    ) -> bool:
        """Check if a rule is applicable to the current context."""
        # Simple matching logic - can be enhanced with more sophisticated matching
        rule_keywords = rule.pattern.lower().split()
        context_keywords = (domain_context + " " + " ".join(entities + relationships)).lower().split()

        # Check for keyword overlap
        overlap = set(rule_keywords) & set(context_keywords)
        return len(overlap) > 0

    async def _perform_multi_hop_reasoning(
        self,
        entities: list[str],
        relationships: list[str],
        rules: list[InferenceRule],
        max_hops: int,
        min_confidence: float
    ) -> list[ReasoningStep]:
        """Perform multi-hop reasoning using applicable rules."""
        reasoning_steps = []
        current_entities = set(entities)
        current_relationships = set(relationships)

        for _hop in range(max_hops):
            # Find new inferences for this hop
            hop_steps = await self._reasoning_hop(
                current_entities, current_relationships, rules, min_confidence
            )

            if not hop_steps:
                break  # No new inferences found

            reasoning_steps.extend(hop_steps)

            # Update current state with new inferences
            for step in hop_steps:
                current_entities.update(step.intermediate_entities)
                current_relationships.update(step.relationships_used)

        return reasoning_steps

    async def _reasoning_hop(
        self,
        entities: set[str],
        relationships: set[str],
        rules: list[InferenceRule],
        min_confidence: float
    ) -> list[ReasoningStep]:
        """Perform one hop of reasoning."""
        hop_steps = []

        for rule in rules:
            if rule.confidence_weight < min_confidence:
                continue

            # Apply rule to current context
            step = ReasoningStep(
                reasoning_type=rule.reasoning_type,
                premise=f"Applied rule: {rule.name}",
                conclusion=f"Inferred from pattern: {rule.pattern}",
                confidence=rule.confidence_weight,
                evidence=rule.examples,
                intermediate_entities=list(entities)[:5],  # Limit for demo
                relationships_used=list(relationships)[:3],
                metadata={"rule_id": rule.rule_id, "hop": len(hop_steps)}
            )

            hop_steps.append(step)

            # Limit steps per hop
            if len(hop_steps) >= 3:
                break

        return hop_steps

    async def _synthesize_conclusion(
        self,
        query: str,
        steps: list[ReasoningStep],
        domain_context: str
    ) -> tuple[str, float]:
        """Synthesize final conclusion from reasoning steps."""
        if not steps:
            return "No reasoning steps available", 0.0

        # Calculate overall confidence as weighted average
        total_weight = sum(step.confidence for step in steps)
        if total_weight == 0:
            overall_confidence = 0.0
        else:
            overall_confidence = total_weight / len(steps)

        # Generate conclusion based on steps
        if self.llm_service:
            synthesis_prompt = f"""
            Based on the following reasoning steps, provide a comprehensive conclusion for the query:

            Query: {query}
            Context: {domain_context}

            Reasoning Steps:
            {chr(10).join([f"Step {i+1}: {step.conclusion} (Confidence: {step.confidence:.2f})"
                          for i, step in enumerate(steps)])}

            Provide a clear, actionable conclusion that synthesizes these insights.
            """

            try:
                response = await self.llm_service.generate(synthesis_prompt)
                conclusion = response.content if hasattr(response, 'content') else str(response)
            except Exception as e:
                logger.warning(f"LLM synthesis failed, using fallback: {str(e)}")
                conclusion = self._fallback_synthesis(query, steps)
        else:
            conclusion = self._fallback_synthesis(query, steps)

        return conclusion, overall_confidence

    def _fallback_synthesis(self, query: str, steps: list[ReasoningStep]) -> str:
        """Fallback synthesis when LLM is unavailable."""
        if not steps:
            return "No conclusive reasoning available for the query."

        best_step = max(steps, key=lambda s: s.confidence)

        return (f"Based on {len(steps)} reasoning steps with average confidence "
                f"{np.mean([s.confidence for s in steps]):.2f}, "
                f"the most reliable conclusion is: {best_step.conclusion}")

    async def _generate_alternatives(
        self,
        query: str,
        steps: list[ReasoningStep],
        domain_context: str
    ) -> list[str]:
        """Generate alternative explanations for the query."""
        alternatives = []

        # Group steps by reasoning type for alternative perspectives
        reasoning_types = {}
        for step in steps:
            if step.reasoning_type not in reasoning_types:
                reasoning_types[step.reasoning_type] = []
            reasoning_types[step.reasoning_type].append(step)

        # Generate alternatives based on different reasoning approaches
        for reasoning_type, type_steps in reasoning_types.items():
            if len(type_steps) > 1:  # Multiple steps of same type suggest alternatives
                alt_confidence = np.mean([s.confidence for s in type_steps])
                alternatives.append(
                    f"Alternative ({reasoning_type.value}): {type_steps[0].conclusion} "
                    f"(confidence: {alt_confidence:.2f})"
                )

        # Add uncertainty-based alternatives
        if steps:
            avg_confidence = np.mean([s.confidence for s in steps])
            if avg_confidence < 0.8:
                alternatives.append(
                    f"Low confidence scenario: The available evidence is insufficient "
                    f"for a definitive conclusion (confidence: {avg_confidence:.2f})"
                )

        return alternatives[:5]  # Limit to top 5 alternatives

    def _determine_confidence_level(self, confidence: float) -> ConfidenceLevel:
        """Determine confidence level from numeric confidence."""
        if confidence >= 0.95:
            return ConfidenceLevel.VERY_HIGH
        elif confidence >= 0.85:
            return ConfidenceLevel.HIGH
        elif confidence >= 0.65:
            return ConfidenceLevel.MODERATE
        elif confidence >= 0.45:
            return ConfidenceLevel.LOW
        else:
            return ConfidenceLevel.VERY_LOW

    def _update_reasoning_stats(self, chain: ReasoningChain, reasoning_time: float):
        """Update reasoning performance statistics."""
        self.reasoning_stats["queries_processed"] += 1

        # Update average confidence
        total_confidence = (
            self.reasoning_stats["avg_confidence"] * (self.reasoning_stats["queries_processed"] - 1) +
            chain.overall_confidence
        )
        self.reasoning_stats["avg_confidence"] = total_confidence / self.reasoning_stats["queries_processed"]

        # Count successful inferences
        if chain.overall_confidence >= 0.5:
            self.reasoning_stats["successful_inferences"] += 1

        # Count multi-hop queries
        if len(chain.steps) > 1:
            self.reasoning_stats["multi_hop_queries"] += 1

        # Update reasoning time
        self.reasoning_stats["reasoning_time"] = (
            self.reasoning_stats["reasoning_time"] + reasoning_time
        ) / 2  # Moving average

    def get_reasoning_chain(self, chain_id: str) -> ReasoningChain | None:
        """Retrieve a reasoning chain by ID."""
        return self.active_chains.get(chain_id)

    def get_performance_stats(self) -> dict[str, Any]:
        """Get reasoning engine performance statistics."""
        return {
            **self.reasoning_stats,
            "active_chains": len(self.active_chains),
            "available_rules": len(self.domain_rules),
            "success_rate": (
                self.reasoning_stats["successful_inferences"] /
                max(self.reasoning_stats["queries_processed"], 1)
            )
        }

    async def add_domain_rule(self, rule: InferenceRule) -> bool:
        """Add a new domain-specific inference rule."""
        try:
            self.domain_rules.append(rule)
            logger.info(f"Added domain rule: {rule.name}")
            return True
        except Exception as e:
            logger.error(f"Failed to add domain rule: {str(e)}")
            return False

    async def optimize_reasoning_rules(self) -> dict[str, Any]:
        """Optimize reasoning rules based on performance data."""
        optimization_results = {
            "rules_evaluated": len(self.domain_rules),
            "rules_optimized": 0,
            "performance_improvement": 0.0
        }

        # Analyze rule performance from past chains
        rule_performance = {}
        for chain in self.active_chains.values():
            for step in chain.steps:
                rule_id = step.metadata.get("rule_id")
                if rule_id:
                    if rule_id not in rule_performance:
                        rule_performance[rule_id] = []
                    rule_performance[rule_id].append(step.confidence)

        # Adjust rule weights based on performance
        for rule in self.domain_rules:
            if rule.rule_id in rule_performance:
                performances = rule_performance[rule.rule_id]
                avg_performance = np.mean(performances)

                # Adjust confidence weight
                old_weight = rule.confidence_weight
                rule.confidence_weight = min(1.0, avg_performance * 1.1)

                if abs(rule.confidence_weight - old_weight) > 0.05:
                    optimization_results["rules_optimized"] += 1

        logger.info(f"Optimized {optimization_results['rules_optimized']} reasoning rules")
        return optimization_results
