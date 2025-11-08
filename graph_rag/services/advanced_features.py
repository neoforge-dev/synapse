from __future__ import annotations

import math
import re
from collections import Counter, defaultdict
from collections.abc import Iterable
from dataclasses import dataclass
from statistics import mean
from typing import Any

from pydantic import BaseModel

from graph_rag.core.interfaces import ChunkData, VectorStore
from graph_rag.domain.models import Chunk, Document, Entity, Relationship
from graph_rag.observability import ComponentType, get_component_logger

logger = get_component_logger(ComponentType.SERVICE, "advanced_features_service")


class GraphStats(BaseModel):
    total_nodes: int
    total_relationships: int
    node_types: dict[str, int]
    relationship_types: dict[str, int]
    graph_density: float
    connected_components: int


class GraphAnalysisResult(BaseModel):
    entities: list[dict[str, Any]]
    relationships: list[dict[str, Any]]
    subgraphs: list[dict[str, Any]]
    analysis_metrics: dict[str, Any]


class GraphVisualizationData(BaseModel):
    nodes: list[dict[str, Any]]
    edges: list[dict[str, Any]]
    metadata: dict[str, Any]


class HotTakeAnalysis(BaseModel):
    controversy_score: float
    engagement_prediction: dict[str, Any]
    risk_assessment: dict[str, Any]
    optimization_suggestions: list[str]
    viral_potential: float


class ViralPrediction(BaseModel):
    viral_score: float
    predicted_reach: int
    engagement_factors: list[dict[str, Any]]
    optimization_recommendations: list[str]


class QuickScore(BaseModel):
    engagement_score: float
    confidence: float
    factors: list[str]
    quick_recommendations: list[str]


class BrandSafetyAssessment(BaseModel):
    safety_score: float
    risk_categories: list[dict[str, Any]]
    flagged_content: list[str]
    recommendations: list[str]
    compliance_status: str


class ReasoningStep(BaseModel):
    step: int
    thought: str
    evidence: list[str]
    confidence: float


class ReasoningPlan(BaseModel):
    reasoning_chain: list[ReasoningStep]
    conclusion: str
    confidence_score: float
    supporting_evidence: list[str]
    alternative_viewpoints: list[str]


class ChunkInsight(BaseModel):
    chunk_id: str
    content_preview: str
    embedding_quality: float
    semantic_density: float
    relationships_count: int
    parent_document: str


class ChunkListing(BaseModel):
    chunks: list[dict[str, Any]]
    total: int
    limit: int
    skip: int


@dataclass(slots=True)
class _GraphSnapshot:
    documents: list[Document]
    chunks: list[Chunk]
    entities: list[Entity]
    relationships: list[Relationship]


class AdvancedFeaturesService:
    """Implements graph analytics, viral scoring, and brand safety heuristics."""

    def __init__(self, graph_repo: Any, vector_store: VectorStore | None = None):
        self._graph_repo = graph_repo
        self._vector_store = vector_store

    async def graph_stats(self) -> GraphStats:
        snapshot = await self._collect_snapshot()

        node_counter = Counter[str]()
        node_ids: set[str] = set()

        for document in snapshot.documents:
            node_counter["Document"] += 1
            node_ids.add(document.id)

        for chunk in snapshot.chunks:
            node_counter["Chunk"] += 1
            node_ids.add(chunk.id)

        for entity in snapshot.entities:
            node_type = getattr(entity, "type", "Entity") or "Entity"
            node_counter[node_type] += 1
            node_ids.add(entity.id)

        relationship_counter = Counter[str]()
        adjacency: dict[str, set[str]] = defaultdict(set)

        for relationship in snapshot.relationships:
            rel_type = getattr(relationship, "type", "RELATED_TO") or "RELATED_TO"
            source_id = getattr(relationship, "source_id", None) or getattr(relationship, "source", None)
            target_id = getattr(relationship, "target_id", None) or getattr(relationship, "target", None)

            if source_id and target_id:
                relationship_counter[rel_type] += 1
                adjacency[source_id].add(target_id)
                adjacency[target_id].add(source_id)

        total_nodes = sum(node_counter.values())
        total_relationships = sum(relationship_counter.values())
        graph_density = self._calculate_density(total_nodes, total_relationships)
        connected_components = self._count_components(node_ids, adjacency)

        return GraphStats(
            total_nodes=total_nodes,
            total_relationships=total_relationships,
            node_types=dict(node_counter),
            relationship_types=dict(relationship_counter),
            graph_density=graph_density,
            connected_components=connected_components,
        )

    async def analyze_graph(
        self,
        query: str,
        depth: int = 2,
        include_entities: bool = True,
        include_relationships: bool = True,
    ) -> GraphAnalysisResult:
        snapshot = await self._collect_snapshot()
        query_lower = query.lower().strip()

        matched_entities = self._filter_entities(snapshot.entities, query_lower)
        matched_ids = {entity.id for entity in matched_entities}

        matched_relationships = []
        if include_relationships:
            matched_relationships = [
                relationship
                for relationship in snapshot.relationships
                if relationship.source_id in matched_ids or relationship.target_id in matched_ids
            ]

        component_map = self._build_components(snapshot, matched_ids, depth)

        entities_payload = [self._serialize_entity(entity) for entity in (matched_entities if include_entities else [])]
        relationships_payload = [
            self._serialize_relationship(relationship) for relationship in matched_relationships
        ]
        subgraphs_payload = [
            {
                "id": f"component:{index}",
                "nodes": list(component_nodes),
                "density": self._calculate_density(len(component_nodes), component_edges),
                "cohesion": round(component_edges / max(1, len(component_nodes)), 2),
            }
            for index, (component_nodes, component_edges) in enumerate(component_map)
        ]

        analysis_metrics = {
            "query": query,
            "depth": depth,
            "entities_analyzed": len(entities_payload),
            "relationships_analyzed": len(relationships_payload),
            "components_detected": len(subgraphs_payload),
            "average_degree": self._average_degree(matched_relationships, matched_ids),
        }

        return GraphAnalysisResult(
            entities=entities_payload,
            relationships=relationships_payload,
            subgraphs=subgraphs_payload,
            analysis_metrics=analysis_metrics,
        )

    async def graph_visualization(self, query: str, max_nodes: int = 50) -> GraphVisualizationData:
        snapshot = await self._collect_snapshot()
        query_lower = query.lower().strip()

        node_scores: dict[str, float] = defaultdict(float)
        node_labels: dict[str, str] = {}
        node_types: dict[str, str] = {}

        def _score_match(text: str) -> float:
            if not query_lower:
                return 0.5
            return 1.0 if query_lower in text.lower() else 0.0

        for entity in snapshot.entities:
            label = getattr(entity, "name", None) or getattr(entity, "id", "entity")
            score = _score_match(label) + _score_match(str(getattr(entity, "properties", "")))
            if score > 0:
                node_scores[entity.id] = score
                node_labels[entity.id] = label
                node_types[entity.id] = getattr(entity, "type", "Entity") or "Entity"

        for document in snapshot.documents:
            score = _score_match(document.content)
            if score > 0 or not query_lower:
                node_scores[document.id] += max(0.3, score)
                node_labels[document.id] = document.metadata.get("title", document.id.split(":")[-1])
                node_types[document.id] = "Document"

        for chunk in snapshot.chunks:
            score = _score_match(chunk.text)
            if score > 0.2:
                node_scores[chunk.id] += score
                node_labels[chunk.id] = f"Chunk:{chunk.id.split(':')[-1]}"
                node_types[chunk.id] = "Chunk"

        ranked_nodes = sorted(node_scores.items(), key=lambda item: item[1], reverse=True)[:max_nodes]
        selected_ids = {node_id for node_id, _ in ranked_nodes}

        edges_payload: list[dict[str, Any]] = []
        for relationship in snapshot.relationships:
            if relationship.source_id in selected_ids and relationship.target_id in selected_ids:
                edges_payload.append(
                    {
                        "from": relationship.source_id,
                        "to": relationship.target_id,
                        "type": getattr(relationship, "type", "CONNECTED_TO"),
                        "weight": getattr(relationship, "properties", {}).get("weight", 0.5),
                    }
                )

        nodes_payload = [
            {
                "id": node_id,
                "label": node_labels.get(node_id, node_id),
                "type": node_types.get(node_id, "Entity"),
                "size": max(10, round(node_scores[node_id] * 20, 1)),
            }
            for node_id, _ in ranked_nodes
        ]

        metadata = {
            "query": query,
            "total_nodes": len(nodes_payload),
            "visualization_type": "force_directed",
        }

        return GraphVisualizationData(nodes=nodes_payload, edges=edges_payload, metadata=metadata)

    async def get_chunk_analysis(self, chunk_id: str) -> ChunkInsight:
        snapshot = await self._collect_snapshot()
        chunk = next((c for c in snapshot.chunks if c.id == chunk_id), None)
        document_id = chunk.document_id if chunk else "unknown"
        relationships = [
            relationship
            for relationship in snapshot.relationships
            if relationship.source_id == chunk_id or relationship.target_id == chunk_id
        ]

        chunk_data: ChunkData | None = None
        if self._vector_store:
            chunk_data = await self._vector_store.get_chunk_by_id(chunk_id)

        text = chunk_data.text if chunk_data else getattr(chunk, "text", "")
        embedding_quality = self._embedding_quality(chunk_data)
        semantic_density = self._semantic_density(text)

        return ChunkInsight(
            chunk_id=chunk_id,
            content_preview=self._preview_text(text),
            embedding_quality=embedding_quality,
            semantic_density=semantic_density,
            relationships_count=len(relationships),
            parent_document=document_id,
        )

    async def list_chunks(self, limit: int = 50, skip: int = 0, document_id: str | None = None) -> ChunkListing:
        snapshot = await self._collect_snapshot()
        chunks = snapshot.chunks

        if document_id:
            chunks = [chunk for chunk in chunks if chunk.document_id == document_id]

        paginated = chunks[skip : skip + limit]
        payload = [
            {
                "chunk_id": chunk.id,
                "document_id": chunk.document_id,
                "content_preview": self._preview_text(chunk.text),
                "size": len(chunk.text or ""),
                "metadata": getattr(chunk, "metadata", {}),
            }
            for chunk in paginated
        ]

        return ChunkListing(chunks=payload, total=len(chunks), limit=limit, skip=skip)

    async def analyze_hot_take(self, content: str, platform: str, analysis_depth: str) -> HotTakeAnalysis:
        tokens = self._tokenize(content)
        length_factor = min(1.0, len(tokens) / 120)
        exclamation_factor = min(0.3, content.count("!") * 0.05)
        uppercase_factor = min(0.25, sum(1 for token in tokens if token.isupper()) * 0.02)
        emotional_keywords = {"revolutionary", "dominate", "insane", "explosive", "outrage", "controversial"}
        emotion_hits = sum(1 for token in tokens if token in emotional_keywords)
        controversy_score = round(min(1.0, 0.35 * length_factor + exclamation_factor + uppercase_factor + 0.08 * emotion_hits), 2)

        base_engagement = 80 + int(40 * length_factor) + int(25 * emotion_hits)
        engagement_prediction = {
            "expected": max(35, base_engagement),
            "likes": {"expected": max(15, int(base_engagement * 0.45))},
            "comments": {"expected": max(5, int(base_engagement * 0.12))},
            "shares": {"expected": max(2, int(base_engagement * 0.08))},
        }

        risk_assessment = {
            "brand_risk": "medium" if controversy_score > 0.6 else "low",
            "tone_risk": "elevated" if uppercase_factor > 0.2 else "controlled",
            "platform_alignment": platform,
        }

        optimization_suggestions = self._suggest_hot_take_improvements(tokens, controversy_score)
        viral_potential = round(min(1.0, 0.4 * length_factor + 0.3 * emotion_hits + 0.2 * uppercase_factor + 0.2), 2)

        return HotTakeAnalysis(
            controversy_score=controversy_score,
            engagement_prediction=engagement_prediction,
            risk_assessment=risk_assessment,
            optimization_suggestions=optimization_suggestions,
            viral_potential=viral_potential,
        )

    async def quick_score(self, content: str, platform: str) -> QuickScore:
        tokens = self._tokenize(content)
        has_metrics = any(token.endswith("%") or re.match(r"\$?\d+(?:,\d+)?", token) for token in tokens)
        has_call_to_action = any(phrase in content.lower() for phrase in ["join", "learn more", "discover", "download"])

        base_score = 0.55
        if has_metrics:
            base_score += 0.12
        if has_call_to_action:
            base_score += 0.08
        if len(tokens) > 80:
            base_score += 0.05
        if "graph" in tokens or "rag" in tokens:
            base_score += 0.05

        engagement_score = min(0.95, round(base_score, 2))
        factors = [
            "Metric-driven" if has_metrics else "Add measurable outcomes",
            "Call-to-action present" if has_call_to_action else "Include a call-to-action",
            "Platform" + f": {platform}",
        ]

        recommendations = []
        if not has_metrics:
            recommendations.append("Reference quantitative impact to build credibility")
        if not has_call_to_action:
            recommendations.append("Close with a direct call-to-action to prompt engagement")
        if len(tokens) < 60:
            recommendations.append("Expand the narrative with a concrete example")

        return QuickScore(
            engagement_score=engagement_score,
            confidence=0.78,
            factors=factors,
            quick_recommendations=recommendations or ["Solid structure – minor refinements only"],
        )

    async def predict_viral_potential(self, content: str, platform: str) -> ViralPrediction:
        tokens = self._tokenize(content)
        novelty_keywords = {"first", "new", "breakthrough", "unseen", "exclusive"}
        novelty_hits = sum(1 for token in tokens if token in novelty_keywords)
        storytelling = any(phrase in content.lower() for phrase in ["we discovered", "lessons learned", "step-by-step"])

        base_score = 0.42 + novelty_hits * 0.05 + (0.07 if storytelling else 0)
        viral_score = round(min(0.95, base_score), 2)
        predicted_reach = int(9000 + novelty_hits * 1500 + (2500 if storytelling else 0))

        engagement_factors = [
            {
                "factor": "novelty",
                "impact": round(min(1.0, 0.6 + novelty_hits * 0.1), 2),
                "description": "Fresh perspective with differentiated angle" if novelty_hits else "Opportunity to add differentiated insight",
            },
            {
                "factor": "storytelling",
                "impact": 0.72 if storytelling else 0.45,
                "description": "Narrative arc creates stronger retention" if storytelling else "Incorporate narrative framing for better retention",
            },
            {
                "factor": "clarity",
                "impact": round(min(0.95, len(tokens) / 120), 2),
                "description": "Clear, concise delivery aids shareability",
            },
        ]

        optimization_recommendations = [
            "Publish during mid-week peak engagement (Tuesday/Thursday 8-10 AM local)",
            "Add an insight-driven visual showing transformation outcomes",
            "Provide a provocative question at the end to stimulate comments",
        ]

        return ViralPrediction(
            viral_score=viral_score,
            predicted_reach=predicted_reach,
            engagement_factors=engagement_factors,
            optimization_recommendations=optimization_recommendations,
        )

    async def check_brand_safety(self, content: str, safety_level: str) -> BrandSafetyAssessment:
        tokens = self._tokenize(content)
        lower_content = content.lower()
        red_flags = {"exploit", "mercilessly", "loophole", "illegal", "deceive"}
        caution_flags = {"dominate", "aggressive", "crush", "destroy"}

        red_hits = sum(1 for token in tokens if token in red_flags)
        caution_hits = sum(1 for token in tokens if token in caution_flags)

        base_score = 0.95 - 0.35 * red_hits - 0.2 * caution_hits
        safety_score = max(0.0, round(base_score, 2))

        risk_categories = []
        if red_hits:
            risk_categories.append(
                {
                    "category": "compliance",
                    "risk_level": "high",
                    "score": max(0.1, 0.5 - 0.1 * red_hits),
                    "details": "Language suggests regulatory or ethical violations.",
                }
            )
        if caution_hits:
            risk_categories.append(
                {
                    "category": "ethics",
                    "risk_level": "medium",
                    "score": round(0.6 - caution_hits * 0.1, 2),
                    "details": "Tone indicates potentially aggressive messaging.",
                }
            )
        if not risk_categories:
            risk_categories.append(
                {
                    "category": "overall",
                    "risk_level": "low",
                    "score": safety_score,
                    "details": "Content aligns with professional brand standards.",
                }
            )

        flagged_content = [token for token in tokens if token in red_flags or token in caution_flags]
        recommendations = []
        if red_hits or caution_hits:
            recommendations.append("Replace aggressive or non-compliant phrases with supportive, outcome-oriented language.")
        if "loophole" in lower_content:
            recommendations.append("Clarify compliance stance to avoid perceived regulatory evasion.")
        if not recommendations:
            recommendations.append("Content is compliant. Maintain current review cadence.")

        compliance_status = "high_risk" if red_hits else ("review" if caution_hits or safety_level == "strict" else "approved")

        return BrandSafetyAssessment(
            safety_score=safety_score,
            risk_categories=risk_categories,
            flagged_content=flagged_content,
            recommendations=recommendations,
            compliance_status=compliance_status,
        )

    async def reason(self, query: str, context: str | None = None, reasoning_type: str = "logical") -> ReasoningPlan:
        context_tokens = self._tokenize(context or "")
        query_tokens = self._tokenize(query)

        reasoning_chain = [
            ReasoningStep(
                step=1,
                thought="Identify primary objective and business impact described in the query.",
                evidence=[query],
                confidence=0.72,
            ),
            ReasoningStep(
                step=2,
                thought="Extract supporting constraints or opportunities from provided context.",
                evidence=context_tokens[:5] if context_tokens else [],
                confidence=0.68,
            ),
            ReasoningStep(
                step=3,
                thought="Synthesize recommended action that balances speed, risk, and value delivery.",
                evidence=["industry benchmarks", "internal capability assessment"],
                confidence=0.74,
            ),
        ]

        conclusion = "Pursue a pilot initiative with tight feedback loops to validate value while mitigating delivery risk."
        if reasoning_type == "causal":
            conclusion = "Link graph consolidation to revenue protection metrics before expanding, ensuring causal accountability."

        alternative_viewpoints = [
            "Evaluate phased adoption if immediate resource alignment is constrained.",
            "Consider stakeholder readiness to avoid change fatigue.",
        ]

        return ReasoningPlan(
            reasoning_chain=reasoning_chain,
            conclusion=conclusion,
            confidence_score=0.73,
            supporting_evidence=[token for token in query_tokens[:3]],
            alternative_viewpoints=alternative_viewpoints,
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    async def _collect_snapshot(self) -> _GraphSnapshot:
        documents = await self._safe_collect("_documents", "list_documents", Document)
        chunks = await self._safe_collect("_chunks", "list_chunks", Chunk)
        entities = await self._safe_collect("_entities", "list_entities", Entity)
        relationships = await self._safe_collect("_relationships", "list_relationships", Relationship)

        return _GraphSnapshot(
            documents=list(documents),
            chunks=list(chunks),
            entities=list(entities),
            relationships=list(relationships),
        )

    async def _safe_collect(self, attr_name: str, method_name: str, model_type: Any) -> Iterable[Any]:
        if hasattr(self._graph_repo, method_name):
            collector = getattr(self._graph_repo, method_name)
            try:
                items = await collector() if callable(collector) else []
                return items or []
            except Exception as exc:  # pragma: no cover - defensive
                logger.debug("Failed collecting via method %s: %s", method_name, exc)

        if hasattr(self._graph_repo, attr_name):
            storage = getattr(self._graph_repo, attr_name)
            if isinstance(storage, dict):
                return storage.values()
            if isinstance(storage, list):
                return storage

        return []

    @staticmethod
    def _calculate_density(total_nodes: int, total_relationships: int) -> float:
        if total_nodes <= 1:
            return 0.0
        possible_edges = total_nodes * (total_nodes - 1)
        return round(total_relationships / possible_edges, 4)

    @staticmethod
    def _count_components(node_ids: set[str], adjacency: dict[str, set[str]]) -> int:
        if not node_ids:
            return 0

        unexplored = set(node_ids)
        components = 0

        while unexplored:
            components += 1
            stack = [unexplored.pop()]
            while stack:
                current = stack.pop()
                neighbors = adjacency.get(current, set())
                for neighbor in neighbors:
                    if neighbor in unexplored:
                        unexplored.remove(neighbor)
                        stack.append(neighbor)

        return components

    @staticmethod
    def _filter_entities(entities: Iterable[Entity], query_lower: str) -> list[Entity]:
        if not query_lower:
            return list(entities)

        matched = [
            entity
            for entity in entities
            if query_lower in (getattr(entity, "name", "") or "").lower()
            or query_lower in getattr(entity, "id", "").lower()
            or query_lower in str(getattr(entity, "properties", "")).lower()
        ]

        if matched:
            return matched

        # Fallback: return top 10 entities if nothing matched
        return list(entities)[:10]

    @staticmethod
    def _serialize_entity(entity: Entity) -> dict[str, Any]:
        properties = getattr(entity, "properties", {}) or {}
        name = getattr(entity, "name", None) or properties.get("name") or entity.id
        return {
            "id": entity.id,
            "type": getattr(entity, "type", "Entity") or "Entity",
            "name": name,
            "properties": properties,
        }

    @staticmethod
    def _serialize_relationship(relationship: Relationship) -> dict[str, Any]:
        return {
            "from": relationship.source_id,
            "to": relationship.target_id,
            "type": getattr(relationship, "type", "RELATED_TO") or "RELATED_TO",
            "properties": getattr(relationship, "properties", {}) or {},
        }

    @staticmethod
    def _build_components(snapshot: _GraphSnapshot, matched_ids: set[str], depth: int) -> list[tuple[set[str], int]]:
        adjacency: dict[str, set[str]] = defaultdict(set)
        for relationship in snapshot.relationships:
            adjacency[relationship.source_id].add(relationship.target_id)
            adjacency[relationship.target_id].add(relationship.source_id)

        components: list[tuple[set[str], int]] = []
        seen: set[str] = set()

        seeds = matched_ids or {entity.id for entity in snapshot.entities}
        for seed in seeds:
            if seed in seen:
                continue

            nodes: set[str] = set()
            edges = 0
            frontier = [(seed, 0)]
            while frontier:
                current, depth_so_far = frontier.pop()
                if current in seen or depth_so_far > depth:
                    continue

                seen.add(current)
                nodes.add(current)
                neighbors = adjacency.get(current, set())
                edges += len(neighbors)
                for neighbor in neighbors:
                    frontier.append((neighbor, depth_so_far + 1))

            if nodes:
                components.append((nodes, edges // 2))

        return components

    @staticmethod
    def _average_degree(relationships: Iterable[Relationship], matched_ids: set[str]) -> float:
        if not matched_ids:
            return 0.0
        degree: Counter[str] = Counter()
        for relationship in relationships:
            degree[relationship.source_id] += 1
            degree[relationship.target_id] += 1
        if not degree:
            return 0.0
        values = [degree[node_id] for node_id in matched_ids if node_id in degree]
        return round(mean(values) if values else 0.0, 2)

    @staticmethod
    def _tokenize(content: str) -> list[str]:
        return re.findall(r"[A-Za-z0-9%$]+", content or "")

    @staticmethod
    def _preview_text(text: str | None, limit: int = 160) -> str:
        if not text:
            return ""
        cleaned = " ".join(text.split())
        return cleaned[: limit - 3] + "..." if len(cleaned) > limit else cleaned

    @staticmethod
    def _semantic_density(text: str | None) -> float:
        if not text:
            return 0.0
        tokens = [token.lower() for token in re.findall(r"[A-Za-z]+", text)]
        if not tokens:
            return 0.0
        unique_tokens = len(set(tokens))
        return round(unique_tokens / len(tokens), 3)

    @staticmethod
    def _embedding_quality(chunk_data: ChunkData | None) -> float:
        if not chunk_data or not chunk_data.embedding:
            return 0.35
        magnitude = math.sqrt(sum(value * value for value in chunk_data.embedding))
        return round(min(0.99, 0.6 + 0.1 * math.log1p(magnitude)), 3)

    @staticmethod
    def _suggest_hot_take_improvements(tokens: list[str], controversy_score: float) -> list[str]:
        suggestions = []
        if controversy_score < 0.4:
            suggestions.append("Introduce a provocative question to spark dialogue.")
        if controversy_score > 0.7:
            suggestions.append("Balance strong claims with evidence to maintain credibility.")
        if not any(token.isupper() for token in tokens):
            suggestions.append("Highlight a key insight in uppercase for emphasis.")
        if "roi" not in tokens:
            suggestions.append("Quantify ROI to appeal to executive stakeholders.")
        return suggestions[:4]
