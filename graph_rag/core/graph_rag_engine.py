import asyncio  # For potential concurrent processing
import time
import uuid
from collections import defaultdict  # Add this import
from collections.abc import AsyncGenerator
from dataclasses import dataclass, field
from typing import Any

from graph_rag.api.performance_optimization import (
    get_performance_monitor,
    get_query_optimizer,
)
from graph_rag.config import get_settings
from graph_rag.core.interfaces import (
    ChunkData,
    DocumentData,
    DocumentProcessor,
    EmbeddingService,
    ExtractedEntity,
    ExtractedRelationship,
    ExtractionResult,
    GraphRAGEngine,
    GraphRepository,
    KnowledgeGraphBuilder,
    SearchResultData,
    VectorStore,
)

# Remove incorrect/unused service imports that cause ModuleNotFound errors
# from graph_rag.services.chunking import ChunkingService
# from graph_rag.services.embedding import EmbeddingService # Protocol is imported from interfaces
# from graph_rag.services.entity_extraction import EntityExtractionService # Implementation likely from elsewhere
from graph_rag.llm import (
    MockLLMService,
)  # Corrected import: MockLLMService from llm package

# from graph_rag.core.node_factory import NodeFactory
from graph_rag.llm.protocols import LLMService  # Add LLMService import
from graph_rag.llm.response_models import EnhancedLLMResponse
from graph_rag.models import Chunk, Entity, Relationship

# Import structured logging and performance optimization
from graph_rag.observability import (
    ComponentType,
    LogContext,
    PerformanceTimer,
    get_component_logger,
)
from graph_rag.services.answer_validation import AnswerValidator, ValidationLevel
from graph_rag.services.citation import CitationService, CitationStyle
from graph_rag.services.memory import ContextManager
from graph_rag.services.prompt_optimization import PromptOptimizer
from graph_rag.services.rerank import CrossEncoderReranker
from graph_rag.services.search import (
    SearchResult,
)  # Import SearchResult model too

# from graph_rag.core.prompts import QnAPromptContext # Import QnAPromptContext
# from graph_rag.core.prompts as prompts # Corrected import alias
# from graph_rag.core.prompts import (
#     GRAPH_EXTRACTION_PROMPT,
#     GRAPH_REPORT_PROMPT,
# )

# Use structured logger for GraphRAG engine
logger = get_component_logger(ComponentType.ENGINE, "graph_rag_engine")
settings = get_settings()


@dataclass
class QueryResult:
    """Represents the result of a query."""

    relevant_chunks: list[Chunk] = field(default_factory=list)
    answer: str = ""
    llm_response: str = ""  # Added for test compatibility
    graph_context: tuple[list[Entity], list[Relationship]] | None | str = (
        None  # Support both tuple and string formats
    )
    metadata: dict[str, Any] = field(default_factory=dict)
    # Citation-enhanced fields
    answer_with_citations: str | None = None
    citations: list = field(default_factory=list)
    bibliography: dict = field(default_factory=dict)


class SimpleGraphRAGEngine(GraphRAGEngine):
    """A basic implementation combining graph and vector retrieval."""

    def __init__(
        self,
        graph_store: GraphRepository,
        vector_store: VectorStore,
        entity_extractor,
        llm_service: LLMService = None,
        context_manager: ContextManager = None,
        citation_style: CitationStyle = CitationStyle.NUMERIC,
        validation_level: ValidationLevel = ValidationLevel.MODERATE,
    ):
        """Requires GraphRepository, VectorStore, EntityExtractor, and optionally LLMService."""
        if not isinstance(graph_store, GraphRepository):
            raise TypeError("graph_store must implement the GraphRepository protocol")
        if not isinstance(vector_store, VectorStore):
            raise TypeError("vector_store must be an instance of VectorStore")
        # if not isinstance(entity_extractor, EntityExtractor):
        #     raise TypeError("entity_extractor must be an instance of EntityExtractor")

        # Use provided LLMService or default to MockLLMService
        self._llm_service = llm_service if llm_service else MockLLMService()

        self._graph_store = graph_store
        self._vector_store = vector_store
        self._entity_extractor = entity_extractor  # Store the extractor
        self._reranker = CrossEncoderReranker()
        self._context_manager = context_manager
        self._citation_service = CitationService(citation_style)
        self._answer_validator = AnswerValidator(validation_level)
        self._prompt_optimizer = PromptOptimizer()

        # Performance optimization components
        self._performance_monitor = get_performance_monitor()
        self._query_optimizer = get_query_optimizer()
        # Log initialization with structured context
        context = LogContext(
            component=ComponentType.ENGINE,
            operation="initialization",
            metadata={
                "graph_store_type": type(graph_store).__name__,
                "vector_store_type": type(vector_store).__name__,
                "entity_extractor_type": type(entity_extractor).__name__,
                "llm_service_type": type(self._llm_service).__name__,
                "citation_style": citation_style.value,
                "validation_level": validation_level.value,
            }
        )
        logger.info("SimpleGraphRAGEngine initialized successfully", context)

    async def _extract_entities_from_chunks(
        self, chunks: list[SearchResultData]
    ) -> list[Entity]:
        """Extracts entities from a list of chunk data using the configured EntityExtractor."""
        if not chunks:
            return []

        logger.debug(f"Extracting entities from {len(chunks)} chunks...")
        # Combine text from chunks
        combined_text = " ".join([c.chunk.text for c in chunks if c.chunk])

        if not combined_text.strip():
            logger.warning("No text found in chunks to extract entities from.")
            return []

        try:
            # Use the entity extractor's async method for text
            extracted_data: ExtractionResult = (
                await self._entity_extractor.extract_from_text(combined_text)
            )

            entities_list: list[Entity] = []
            if isinstance(extracted_data, ExtractionResult):
                # If extractor returns ExtractionResult, get entities from it
                entities_list = extracted_data.entities
                logger.info(
                    f"Extracted {len(entities_list)} entities (from ExtractionResult) from combined chunk text."
                )
            elif isinstance(extracted_data, list):
                # If extractor returns a list (assumed List[Entity])
                entities_list = extracted_data
                logger.info(
                    f"Extracted {len(entities_list)} entities (from List[Entity]) from combined chunk text."
                )
            elif extracted_data is None:
                logger.warning("Entity extractor returned None.")
                # entities_list remains []
            else:
                logger.warning(
                    f"Entity extractor returned unexpected type: {type(extracted_data)}. Expected List[Entity] or ExtractionResult."
                )
                # entities_list remains []

            return entities_list

            # Original logic:
            # extracted_entities = await self._entity_extractor.extract(combined_text)
            # if extracted_entities:
            #     # Assuming extractor returns List[Entity] directly
            #     logger.info(f"Extracted {len(extracted_entities)} entities from combined chunk text.")
            #     return extracted_entities
            # else:
            #     logger.warning("Entity extractor returned no entities or None.")
            #     return []
        except Exception as e:
            logger.error(f"Entity extraction during query failed: {e}", exc_info=True)
            return []  # Return empty list on failure

    async def _find_entities_in_graph_by_properties(
        self, entities_from_extractor: list[Entity]
    ) -> list[Entity]:
        """Looks up entities from the extractor in the graph store using their properties.

        Uses name and type for lookup. Requires the GraphRepository to have
        search_entities_by_properties implemented and potentially indexed properties.
        """
        if not entities_from_extractor:
            return []

        logger.debug(
            f"Attempting to find {len(entities_from_extractor)} entities in graph by properties (name, type)..."
        )
        found_graph_entities = []
        processed_extractor_entities = (
            set()
        )  # Avoid searching for the same name/type combo multiple times

        for entity in entities_from_extractor:
            # Use label from ExtractedEntity, assuming it maps to the type in the graph
            search_key = (entity.text, entity.label)
            if (
                not entity.text
                or not entity.label
                or search_key in processed_extractor_entities
            ):
                continue  # Skip if missing key info or already searched

            processed_extractor_entities.add(search_key)
            # Use label for the 'type' field in search properties
            search_props = {"name": entity.text, "type": entity.label}

            try:
                # Use the graph store's property search method
                # Limit to 1 assuming name+type is reasonably unique, adjust if needed
                results = await self._graph_store.search_entities_by_properties(
                    search_props, limit=1
                )
                if results:
                    # Use the entity found in the graph (it has the correct graph ID/metadata)
                    found_graph_entities.append(results[0])
                    logger.debug(
                        f"Found graph entity {results[0].id} matching properties: {search_props}"
                    )
                else:
                    logger.debug(
                        f"No graph entity found matching properties: {search_props}"
                    )
            except NotImplementedError:
                logger.error(
                    f"Graph store {type(self._graph_store).__name__} does not support search_entities_by_properties."
                )
                # Fallback or stop? For MVP, log error and continue.
                break  # Stop searching if method not implemented
            except Exception as e:
                logger.error(
                    f"Error searching graph for properties {search_props}: {e}",
                    exc_info=True,
                )
                # Continue trying other entities

        logger.info(
            f"Found {len(found_graph_entities)} graph entities matching properties of {len(processed_extractor_entities)} unique extracted entities."
        )
        return found_graph_entities

    async def _get_graph_context(
        self, entities: list[Entity]
    ) -> tuple[list[Entity], list[Relationship]]:
        """Fetches neighbors for a list of seed entities to build a graph context."""
        if not entities:
            return [], []

        logger.debug(
            f"Getting graph context for {len(entities)} seed entities: {[e.id for e in entities][:5]}..."
        )
        all_neighbor_entities: dict[str, Entity] = {
            e.id: e for e in entities
        }  # Start with seeds
        # Use a set to avoid duplicate relationship checks if get_neighbors returns overlapping edges
        # The key is (source_id, type, target_id) to uniquely identify a relationship instance
        all_relationships_dict: dict[tuple[str, str, str], Relationship] = {}
        filtered_relationships_list: list[
            Relationship
        ] = []  # Initialize the list to be returned

        entity_ids_to_expand = [e.id for e in entities]

        # Fetch neighbors for the current batch of entities
        neighbor_tasks = [
            self._graph_store.get_neighbors(entity_id)
            for entity_id in entity_ids_to_expand
        ]
        neighbor_results = await asyncio.gather(*neighbor_tasks, return_exceptions=True)

        for _i, result in enumerate(neighbor_results):
            # ... (exception handling for result) ...
            current_neighbor_entities, current_relationships = result
            all_neighbor_entities.update(
                {
                    e.id: e
                    for e in current_neighbor_entities
                    if e.id not in all_neighbor_entities
                }
            )

            for rel in current_relationships:
                if (
                    rel.source_id in all_neighbor_entities
                    and rel.target_id in all_neighbor_entities
                ):
                    rel_key = (rel.source_id, rel.type, rel.target_id)
                    if rel_key not in all_relationships_dict:
                        all_relationships_dict[rel_key] = rel
                        filtered_relationships_list.append(rel)  # Append to the list

        logger.info(
            f"Aggregated graph context: {len(all_neighbor_entities)} entities, {len(filtered_relationships_list)} relationships."
        )
        return list(
            all_neighbor_entities.values()
        ), filtered_relationships_list  # Return the list

    async def _retrieve_and_build_context(
        self, query_text: str, config: dict[str, Any] | None = None
    ) -> tuple[
        list[SearchResultData], tuple[list[Entity], list[Relationship]] | None
    ]:
        """Internal method to perform vector search and graph context retrieval. DOES NOT call LLM."""
        # Create context for this retrieval operation
        retrieval_context = LogContext(
            component=ComponentType.ENGINE,
            operation="context_retrieval",
            metadata={
                "query_length": len(query_text),
                "config": config or {},
            }
        )
        logger.info("Starting context retrieval", retrieval_context, query=query_text[:100])
        config = config or {}
        k = config.get("k", 3)
        include_graph = config.get("include_graph", True)

        final_entities: list[Entity] = []
        final_relationships: list[Relationship] = []
        graph_context_tuple: tuple[list[Entity], list[Relationship]] | None = None
        relevant_chunk_texts: list[str] = []
        retrieved_chunks_full: list[
            SearchResultData
        ] = []  # Store full SearchResultData

        try:
            # 1. Retrieval: handle search_type parameter for vector, keyword, or hybrid search
            logger.info(f"SimpleGraphRAGEngine: Performing retrieval for: '{query_text}' (k={k})")
            search_type = config.get("search_type", "vector").lower()
            logger.info(f"SimpleGraphRAGEngine: Search type: {search_type}")
            blend_keyword_weight = float(config.get("blend_keyword_weight", 0.0))
            no_answer_min_score = float(config.get("no_answer_min_score", 0.0))

            if search_type == "vector":
                # Vector-only search
                logger.info("SimpleGraphRAGEngine: Using vector-only search")
                logger.info(f"SimpleGraphRAGEngine: Calling vector store search with query: '{query_text}'")
                logger.info(f"SimpleGraphRAGEngine: Vector store type: {type(self._vector_store).__name__}")
                retrieved = await self._vector_store.search(query_text, top_k=k, search_type="vector")
                logger.info(f"SimpleGraphRAGEngine: Vector store search returned {len(retrieved)} results")
                if retrieved:
                    logger.info(f"SimpleGraphRAGEngine: First result score: {retrieved[0].score}")
                retrieved_chunks_full = retrieved

            elif search_type == "keyword":
                # Keyword-only search
                logger.debug("Using keyword-only search")
                retrieved = await self._vector_store.search(query_text, top_k=k, search_type="keyword")
                retrieved_chunks_full = retrieved

            elif search_type == "hybrid":
                # Hybrid search: blend vector and keyword results
                logger.debug(f"Using hybrid search with blend_keyword_weight={blend_keyword_weight}")

                # Get results from both search types
                results_vector = await self._vector_store.search(query_text, top_k=k, search_type="vector")
                results_keyword = await self._vector_store.search(query_text, top_k=k, search_type="keyword")

                # Convert to dict by chunk id for blending
                vec_scores = {r.chunk.id: r.score for r in results_vector if r and r.chunk}
                kw_scores = {r.chunk.id: r.score for r in results_keyword if r and r.chunk}

                # Combine all chunks from both searches
                combined: dict[str, SearchResultData] = {}
                for r in results_vector:
                    if r and r.chunk:
                        combined[r.chunk.id] = r
                for r in results_keyword:
                    if r and r.chunk:
                        combined.setdefault(r.chunk.id, r)

                # Recompute blended scores: (1-blend_keyword_weight) * vector + blend_keyword_weight * keyword
                alpha = 1.0 - blend_keyword_weight  # vector weight
                beta = blend_keyword_weight  # keyword weight

                blended: list[SearchResultData] = []
                for rid, item in combined.items():
                    vs = vec_scores.get(rid, 0.0)
                    ks = kw_scores.get(rid, 0.0)
                    score = alpha * vs + beta * ks

                    chunk = item.chunk
                    meta = dict(chunk.metadata or {})
                    meta["score_vector"] = vs
                    meta["score_keyword"] = ks
                    meta["score_blended"] = score

                    blended.append(
                        SearchResultData(
                            chunk=ChunkData(
                                id=chunk.id,
                                text=chunk.text,
                                document_id=chunk.document_id,
                                metadata=meta,
                                embedding=chunk.embedding,
                                score=score,
                            ),
                            score=score,
                        )
                    )

                # Sort by blended score
                blended.sort(key=lambda r: r.score, reverse=True)
                retrieved_chunks_full = blended[:k]

            else:
                # Fallback to vector search for unknown search types
                logger.warning(f"Unknown search_type '{search_type}', falling back to vector search")
                retrieved = await self._vector_store.search(query_text, top_k=k, search_type="vector")
                retrieved_chunks_full = retrieved

            # Apply no-answer threshold check
            if no_answer_min_score > 0.0 and retrieved_chunks_full:
                top_score = retrieved_chunks_full[0].score if retrieved_chunks_full[0].score is not None else 0.0
                if top_score < no_answer_min_score:
                    logger.info(f"Top result score {top_score:.3f} below threshold {no_answer_min_score:.3f}, returning no-answer")
                    retrieved_chunks_full = []
            if not retrieved_chunks_full:
                logger.warning(
                    f"Vector search returned no relevant chunks for query: '{query_text}'"
                )
                # Still try graph search if requested, but prepare for no context
            else:
                # Assume retrieved_chunks_full is List[SearchResultData]
                # relevant_chunk_texts = [c.text for c in retrieved_chunks_full]
                relevant_chunk_texts = [
                    c.chunk.text for c in retrieved_chunks_full if c.chunk
                ]  # Corrected access to c.chunk.text
                logger.info(
                    f"Found {len(relevant_chunk_texts)} relevant chunks via vector search."
                )

            # 2. Rerank and diversify (optional)
            if retrieved_chunks_full:
                # Optional rerank via cross-encoder
                if bool(config.get("rerank", False)):
                    retrieved_chunks_full = await self._reranker.rerank(
                        query_text, retrieved_chunks_full, k
                    )
                # MMR diversification over the texts
                mmr_lambda = float(config.get("mmr_lambda", 0.0))
                if 0.0 < mmr_lambda <= 1.0 and len(retrieved_chunks_full) > 2:
                    selected: list[SearchResultData] = []
                    candidates = retrieved_chunks_full.copy()
                    # Greedy MMR on cosine similarity of embeddings; fallback to text overlap if no embeddings
                    def _sim(a: SearchResultData, b: SearchResultData) -> float:
                        try:
                            ea = a.chunk.embedding or []
                            eb = b.chunk.embedding or []
                            if ea and eb and len(ea) == len(eb):
                                import numpy as _np

                                va = _np.array(ea)
                                vb = _np.array(eb)
                                norm = float(_np.linalg.norm(va) * _np.linalg.norm(vb)) or 1.0
                                return float(va.dot(vb) / norm)
                            # Fallback to Jaccard on tokens
                            sa = set((a.chunk.text or "").lower().split())
                            sb = set((b.chunk.text or "").lower().split())
                            inter = len(sa & sb)
                            union = len(sa | sb) or 1
                            return inter / union
                        except Exception:
                            return 0.0

                    while candidates and len(selected) < k:
                        if not selected:
                            best = max(candidates, key=lambda r: r.score)
                            selected.append(best)
                            candidates.remove(best)
                        else:
                            # For each candidate, compute mmr = lambda*relevance - (1-lambda)*max_sim(selected)
                            scored: list[tuple[float, SearchResultData]] = []
                            for c in candidates:
                                max_sim = max((_sim(c, s) for s in selected), default=0.0)
                                mmr = mmr_lambda * c.score - (1.0 - mmr_lambda) * max_sim
                                scored.append((mmr, c))
                            best = max(scored, key=lambda t: t[0])[1]
                            selected.append(best)
                            candidates.remove(best)
                    retrieved_chunks_full = selected

            # 3. Graph Retrieval (if requested and chunks were found)
            if include_graph and retrieved_chunks_full:
                logger.debug("Attempting to retrieve graph context...")
                # a. Extract entities from chunks
                extracted_entities = await self._extract_entities_from_chunks(
                    retrieved_chunks_full
                )

                if extracted_entities:
                    # b. Find these entities in the graph
                    seed_entities = await self._find_entities_in_graph_by_properties(
                        extracted_entities
                    )

                    if seed_entities:
                        # c. Get neighborhood graph context
                        (
                            final_entities,
                            final_relationships,
                        ) = await self._get_graph_context(seed_entities)
                        graph_context_tuple = (final_entities, final_relationships)
                        logger.info(
                            f"Retrieved graph context with {len(final_entities)} entities and {len(final_relationships)} relationships."
                        )
                    else:
                        logger.info(
                            "No matching seed entities found in graph using property search."
                        )
                else:
                    logger.info("No entities extracted from retrieved chunks.")
            elif include_graph and not retrieved_chunks_full:
                logger.info(
                    "Skipping graph context retrieval as no relevant chunks were found."
                )

            # 4. Optional relationship extraction via LLM and merge/persist into context
            try:
                if retrieved_chunks_full and config.get("extract_relationships", True):
                    combined_text = "\n".join([r.chunk.text for r in retrieved_chunks_full if r and r.chunk and r.chunk.text])
                    # Use LLM protocol to extract entity/relationship hints
                    llm_entities, llm_relationships = await self._llm_service.extract_entities_relationships(combined_text)
                    # Counters (local; integrate with metrics later if enabled)
                    llm_inferred = 0
                    llm_persisted = 0

                    # Map existing graph entities by canonical lowercase name
                    name_to_entity = {}
                    for e in (final_entities or []):
                        key = str(getattr(e, "name", None) or e.properties.get("name") or e.id).lower()
                        if key:
                            name_to_entity[key] = e

                    # Build domain relationships between known graph entities if names match
                    from graph_rag.domain.models import Relationship as Edge

                    # Settings and gating
                    min_conf = float(settings.llm_rel_min_confidence)
                    dry_run_only = bool(config.get("extract_relationships_dry_run", False))
                    allow_persist = (
                        bool(settings.enable_llm_relationships)
                        and bool(config.get("extract_relationships_persist", False))
                        and not dry_run_only
                    )

                    # Dedup set for session: (src_id, type, tgt_id, extractor)
                    seen_keys: set[tuple[str, str, str, str]] = set()

                    for rel in llm_relationships or []:
                        # Normalized names
                        src_name = (
                            rel.get("source_name")
                            or rel.get("source")
                            or rel.get("source_id")
                            or ""
                        ).strip().lower()
                        tgt_name = (
                            rel.get("target_name")
                            or rel.get("target")
                            or rel.get("target_id")
                            or ""
                        ).strip().lower()
                        rel_type = (rel.get("type") or rel.get("label") or "RELATED_TO").strip() or "RELATED_TO"
                        confidence = float(rel.get("confidence", rel.get("score", 0.0)) or 0.0)

                        src_ent = name_to_entity.get(src_name)
                        tgt_ent = name_to_entity.get(tgt_name)
                        if not (src_ent and tgt_ent):
                            continue

                        llm_inferred += 1
                        # Always add to in-memory graph_context for the response
                        final_relationships.append(
                            Edge(
                                id=str(uuid.uuid4()),
                                type=rel_type,
                                source_id=src_ent.id,
                                target_id=tgt_ent.id,
                                properties={
                                    "extractor": "llm",
                                    "confidence": confidence,
                                    "source_name": src_name,
                                    "target_name": tgt_name,
                                },
                            )
                        )

                        # Optionally persist to graph store with gating and dedupe
                        if allow_persist and confidence >= min_conf:
                            dedupe_key = (src_ent.id, rel_type, tgt_ent.id, "llm")
                            if dedupe_key in seen_keys:
                                continue
                            seen_keys.add(dedupe_key)
                            try:
                                # Use MERGE with evidence_count increment on match
                                cypher = f"""
                                MATCH (s {{id: $src}}),(t {{id: $tgt}})
                                MERGE (s)-[r:`{rel_type}`]->(t)
                                ON CREATE SET r = $props, r.created_at = timestamp()
                                ON MATCH SET r.evidence_count = coalesce(r.evidence_count, 0) + 1, r += $props, r.updated_at = timestamp()
                                """
                                await self._graph_store.execute_query(
                                    cypher,
                                    {
                                        "src": src_ent.id,
                                        "tgt": tgt_ent.id,
                                        "props": {
                                            "id": str(uuid.uuid4()),
                                            "extractor": "llm",
                                            "confidence": confidence,
                                            "source_name": src_name,
                                            "target_name": tgt_name,
                                            "evidence_count": 1,
                                        },
                                    },
                                )
                                llm_persisted += 1
                            except Exception as persist_err:
                                logger.debug(
                                    f"Skipping persist for LLM rel {src_ent.id}-[{rel_type}]->{tgt_ent.id}: {persist_err}"
                                )
                        elif dry_run_only and confidence >= min_conf:
                            # Record planned write in config for the API to surface if desired
                            try:
                                plan = config.setdefault("llm_relationships_planned", [])
                                plan.append(
                                    {
                                        "source_id": src_ent.id,
                                        "target_id": tgt_ent.id,
                                        "type": rel_type,
                                        "confidence": confidence,
                                        "extractor": "llm",
                                    }
                                )
                            except Exception:
                                pass

                    if final_entities or final_relationships:
                        graph_context_tuple = ((final_entities or []), (final_relationships or []))
                    # Log simple counters; Prometheus integration handled by API layer
                    if llm_inferred:
                        logger.info(
                            f"LLM relations inferred={llm_inferred} persisted={llm_persisted} (min_conf={min_conf}, enabled={allow_persist})"
                        )
                        # Expose counts via config so API layer can publish metrics
                        try:
                            config["llm_relations_inferred_total"] = (
                                config.get("llm_relations_inferred_total", 0) + llm_inferred
                            )
                            config["llm_relations_persisted_total"] = (
                                config.get("llm_relations_persisted_total", 0) + llm_persisted
                            )
                        except Exception:
                            pass
            except Exception as e:
                logger.debug(f"LLM relationship extraction skipped due to error: {e}")

            # 5. Return the retrieved context
            # Update retrieval context with results
            retrieval_context.chunk_count = len(retrieved_chunks_full)
            retrieval_context.metadata.update({
                "chunks_found": len(retrieved_chunks_full),
                "graph_entities_found": len(final_entities) if graph_context_tuple else 0,
                "graph_relationships_found": len(final_relationships) if graph_context_tuple else 0,
                "search_type": config.get("search_type", "vector"),
                "include_graph": include_graph,
            })

            logger.info(
                "Context retrieval completed successfully",
                retrieval_context,
                chunks_found=len(retrieved_chunks_full),
                graph_entities=len(final_entities) if graph_context_tuple else 0
            )
            return retrieved_chunks_full, graph_context_tuple

        except Exception as e:
            logger.error(
                "Error during context retrieval processing",
                retrieval_context,
                error=e
            )
            # Return an empty or error state
            return retrieved_chunks_full, None  # Indicate failure or no context

    async def retrieve_context(
        self, query: str, search_type: str = "vector", limit: int = 5
    ) -> list[SearchResultData]:
        """Retrieve relevant context chunks for a query. Does not call LLM."""
        logger.info(
            f"Retrieving context via SimpleGraphRAGEngine for query: '{query}' (limit={limit})"
        )
        config = {
            "k": limit,
            "include_graph": False,
        }  # Exclude graph by default for simple context retrieval
        retrieved_chunks, _ = await self._retrieve_and_build_context(query, config)
        return retrieved_chunks

    async def stream_context(
        self, query: str, search_type: str = "vector", limit: int = 5
    ) -> AsyncGenerator[SearchResultData, None]:
        """Stream relevant context chunks for vector or keyword search.

        For now, retrieve all results once and yield sequentially to keep behavior
        deterministic and tests predictable. This can be optimized later to true
        incremental streaming when backends support it.
        """
        if search_type not in {"vector", "keyword"}:
            raise ValueError(f"Unsupported search type for streaming: {search_type}")
        logger.info(
            f"Streaming context ({search_type}) for query '{query}' (limit={limit})"
        )
        results = await self._vector_store.search(
            query, top_k=limit, search_type=search_type
        )
        for item in results:
            yield item

    async def answer_query(
        self,
        query_text: str,
        config: dict[str, Any] | None = None,
        # Allow passing pre-fetched context
        _retrieved_chunks_data: list[SearchResultData] | None = None,
        _graph_context_tuple: tuple[list[Entity], list[Relationship]] | None = None,
        conversation_id: str | None = None,
    ) -> str:
        """Retrieve context (if not provided), format prompt, and generate an answer using the LLM."""
        logger.info(
            f"Generating answer via SimpleGraphRAGEngine for query: '{query_text}'"
        )
        config = config or {}

        retrieved_chunks_data = _retrieved_chunks_data
        graph_context_tuple = _graph_context_tuple

        # 1. Retrieve context if not already provided
        if retrieved_chunks_data is None and graph_context_tuple is None:
            logger.debug("Context not provided to answer_query, retrieving it now.")
            try:
                (
                    retrieved_chunks_data,
                    graph_context_tuple,
                ) = await self._retrieve_and_build_context(query_text, config)
            except Exception as context_err:
                logger.error(
                    f"Failed to retrieve context for answer_query: {context_err}",
                    exc_info=True,
                )
                return f"Error retrieving context: {context_err}"
        else:
            logger.debug("Using pre-fetched context for answer_query.")

        # 2. Prepare context for LLM
        context_str = ""
        relevant_chunk_texts = []
        if retrieved_chunks_data:
            relevant_chunk_texts = [
                c.chunk.text for c in retrieved_chunks_data if c.chunk
            ]
            context_str += "\n\nRelevant Text Chunks:\n"
            context_str += "\n---\n\n".join(relevant_chunk_texts)

        if graph_context_tuple:
            entities, relationships = graph_context_tuple
            context_str += "\n\nRelated Graph Entities:\n"
            context_str += "\n".join(
                [f"- {e.id} ({e.type}): {getattr(e, 'name', 'N/A')}" for e in entities]
            )
            context_str += "\n\nRelated Graph Relationships:\n"
            context_str += "\n".join(
                [
                    f"- ({r.source_id}) -[{r.type}]-> ({r.target_id})"
                    for r in relationships
                ]
            )  # Use r.source_id and r.target_id

        if not context_str:
            logger.warning(f"No context found for answer_query: '{query_text}'.")
            # Check if this was due to no-answer threshold
            no_answer_min_score = (config or {}).get("no_answer_min_score", 0.0)
            if no_answer_min_score > 0.0:
                return "No relevant information found"
            return "Could not find relevant information to answer the query."

        # 3. Get conversation context if available
        conversation_context = ""
        if conversation_id and self._context_manager:
            try:
                conversation_context = await self._context_manager.get_conversation_context(conversation_id)
                if conversation_context:
                    conversation_context = f"\n\n{conversation_context}\n\n"
            except Exception as e:
                logger.warning(f"Failed to get conversation context: {e}")

        # 4. Create Optimized Prompt and Call LLM
        style_str = (config or {}).get("style", "analytical")
        style = self._prompt_optimizer.get_style_from_string(style_str)

        # Create optimized prompt using the prompt optimizer
        prompt = self._prompt_optimizer.optimize_prompt_for_context(
            query=query_text,
            context=context_str,
            style=style,
            conversation_history=conversation_context,
            confidence_scoring=False,  # Basic query doesn't need confidence scoring
            citation_required=True,
            max_length=(config or {}).get("max_response_length")
        )
        logger.debug(f"Sending prompt to LLM (first 100 chars): {prompt[:100]}...")
        try:
            llm_response = await self._llm_service.generate_response(prompt)
            if hasattr(llm_response, "text"):
                answer_text = llm_response.text
            elif isinstance(llm_response, str):
                answer_text = llm_response
            else:
                logger.error(f"Unexpected LLM response type: {type(llm_response)}")
                answer_text = "Error: Could not process response from language model."
            logger.info("Received synthesized answer from LLM.")

            # Store context for citation processing
            self._last_answer = answer_text
            self._last_chunks = [c.chunk for c in retrieved_chunks_data if c.chunk] if retrieved_chunks_data else []
            self._last_context_texts = relevant_chunk_texts

            return answer_text
        except Exception as llm_err:
            logger.error(
                f"Error generating response from LLM: {llm_err}", exc_info=True
            )
            return f"Error generating answer: {llm_err}"

    async def answer_query_enhanced(
        self,
        query_text: str,
        config: dict[str, Any] | None = None,
        context_data: tuple | None = None,
    ) -> EnhancedLLMResponse:
        """Generate a synthesized answer with confidence scoring and enhanced metadata.
        
        Args:
            query_text: The user's query
            config: Optional configuration (search_type, limit, etc.)
            context_data: Optional pre-fetched context data
            
        Returns:
            EnhancedLLMResponse with confidence metrics and metadata
        """
        config = config or {}
        conversation_id = config.get("conversation_id")
        logger.info(f"Generating enhanced answer for query: '{query_text}'")

        # 1. Retrieve context if not provided
        retrieved_chunks_data = None
        graph_context_tuple = None
        if context_data is None:
            try:
                (
                    retrieved_chunks_data,
                    graph_context_tuple,
                ) = await self._retrieve_and_build_context(query_text, config)
            except Exception as context_err:
                logger.error(
                    f"Failed to retrieve context for enhanced answer: {context_err}",
                    exc_info=True,
                )
                # Return error response with low confidence
                from graph_rag.llm.response_models import ConfidenceLevel, ConfidenceMetrics
                error_confidence = ConfidenceMetrics(
                    overall_score=0.1,
                    level=ConfidenceLevel.VERY_LOW,
                    context_coverage=0.0,
                    context_relevance=0.0,
                    uncertainty_indicators=["context_retrieval_error"],
                    reasoning=f"Context retrieval failed: {context_err}"
                )
                return EnhancedLLMResponse(
                    text=f"Error retrieving context: {context_err}",
                    confidence=error_confidence,
                    has_hallucination_risk=True,
                    requires_verification=True
                )
        else:
            retrieved_chunks_data, graph_context_tuple = context_data
            logger.debug("Using pre-fetched context for enhanced answer.")

        # 2. Prepare context for LLM
        context_str = ""
        relevant_chunk_texts = []
        if retrieved_chunks_data:
            relevant_chunk_texts = [
                c.chunk.text for c in retrieved_chunks_data if c.chunk
            ]
            context_str += "\n\nRelevant Text Chunks:\n"
            context_str += "\n---\n\n".join(relevant_chunk_texts)

        if graph_context_tuple:
            entities, relationships = graph_context_tuple
            context_str += "\n\nRelated Graph Entities:\n"
            context_str += "\n".join(
                [f"- {e.id} ({e.type}): {getattr(e, 'name', 'N/A')}" for e in entities]
            )

        # 3. Add conversation context if available
        conversation_context = ""
        if conversation_id and hasattr(self, '_context_manager'):
            try:
                conversation_context = await self._context_manager.get_conversation_context(conversation_id)
                if conversation_context:
                    conversation_context = f"\n\n{conversation_context}\n\n"
            except Exception as e:
                logger.warning(f"Failed to get conversation context: {e}")

        # 4. Create Enhanced Optimized Prompt for confidence scoring
        style_str = config.get("style", "analytical")
        style = self._prompt_optimizer.get_style_from_string(style_str)

        # Create enhanced optimized prompt with confidence scoring enabled
        prompt = self._prompt_optimizer.optimize_prompt_for_context(
            query=query_text,
            context=context_str,
            style=style,
            conversation_history=conversation_context,
            confidence_scoring=True,  # Enable confidence scoring for enhanced responses
            citation_required=True,
            max_length=config.get("max_response_length")
        )

        logger.debug(f"Sending enhanced prompt to LLM (first 100 chars): {prompt[:100]}...")

        try:
            # Check if LLM service supports enhanced responses
            if hasattr(self._llm_service, 'generate_enhanced_response'):
                # Get the chunks for confidence calculation
                context_chunks = [c.chunk for c in retrieved_chunks_data if c.chunk] if retrieved_chunks_data else []

                enhanced_response = await self._llm_service.generate_enhanced_response(
                    prompt=prompt,
                    context=context_str,
                    context_chunks=context_chunks,
                    query=query_text,
                    context_texts=relevant_chunk_texts
                )

                logger.info(f"Generated enhanced answer with confidence: {enhanced_response.confidence.level.value} ({enhanced_response.confidence.overall_score:.2f})")

                # Store context for citation processing
                self._last_answer = enhanced_response.text
                self._last_chunks = context_chunks
                self._last_context_texts = relevant_chunk_texts

                return enhanced_response

            else:
                # Fallback to standard response with manual confidence calculation
                logger.info("LLM service doesn't support enhanced responses, using fallback")
                answer_text = await self._llm_service.generate_response(prompt)

                # Calculate confidence manually
                from graph_rag.llm.response_models import ConfidenceCalculator
                context_chunks = [c.chunk for c in retrieved_chunks_data if c.chunk] if retrieved_chunks_data else []

                confidence = ConfidenceCalculator.calculate_confidence(
                    answer_text=answer_text,
                    context_chunks=context_chunks,
                    query=query_text,
                    context_texts=relevant_chunk_texts
                )

                # Store context for citation processing
                self._last_answer = answer_text
                self._last_chunks = context_chunks
                self._last_context_texts = relevant_chunk_texts

                return EnhancedLLMResponse(
                    text=answer_text,
                    confidence=confidence,
                    has_hallucination_risk=confidence.overall_score < 0.5,
                    requires_verification=confidence.level.value in ["low", "very_low"]
                )

        except Exception as llm_err:
            logger.error(f"Error generating enhanced response: {llm_err}", exc_info=True)

            # Return error response with very low confidence
            from graph_rag.llm.response_models import ConfidenceLevel, ConfidenceMetrics
            error_confidence = ConfidenceMetrics(
                overall_score=0.1,
                level=ConfidenceLevel.VERY_LOW,
                context_coverage=0.0,
                context_relevance=0.0,
                uncertainty_indicators=["llm_error"],
                reasoning=f"LLM error: {llm_err}"
            )

            return EnhancedLLMResponse(
                text=f"Error generating answer: {llm_err}",
                confidence=error_confidence,
                has_hallucination_risk=True,
                requires_verification=True
            )

    async def stream_answer(
        self,
        query_text: str,
        config: dict[str, Any] | None = None,
    ) -> AsyncGenerator[str, None]:
        """Stream a synthesized answer using the LLM's streaming interface.

        Retrieves context once, builds the same prompt as answer_query, and then
        yields chunks from the LLM provider as they arrive.
        """
        config = config or {}
        conversation_id = config.get("conversation_id")

        try:
            retrieved_chunks_data, graph_context_tuple = await self._retrieve_and_build_context(
                query_text, config
            )
        except Exception as context_err:
            logger.error(
                f"Failed to retrieve context for stream_answer: {context_err}",
                exc_info=True,
            )
            yield f"Error retrieving context: {context_err}"
            return

        context_str = ""
        if retrieved_chunks_data:
            context_str += "\n\nRelevant Text Chunks:\n"
            context_str += "\n---\n\n".join(
                [c.chunk.text for c in retrieved_chunks_data if c.chunk]
            )
        if graph_context_tuple:
            entities, relationships = graph_context_tuple
            context_str += "\n\nRelated Graph Entities:\n"
            context_str += "\n".join(
                [f"- {e.id} ({e.type}): {getattr(e, 'name', 'N/A')}" for e in entities]
            )
            context_str += "\n\nRelated Graph Relationships:\n"
            context_str += "\n".join(
                [f"- ({r.source_id}) -[{r.type}]-> ({r.target_id})" for r in relationships]
            )

        if not context_str:
            yield "Could not find relevant information to answer the query."
            return

        # Get conversation context if available
        conversation_context = ""
        if conversation_id and self._context_manager:
            try:
                conversation_context = await self._context_manager.get_conversation_context(conversation_id)
                if conversation_context:
                    conversation_context = f"\n\n{conversation_context}\n\n"
            except Exception as e:
                logger.warning(f"Failed to get conversation context for streaming: {e}")

        # Create optimized prompt for streaming
        style_str = (config or {}).get("style", "conversational")
        style = self._prompt_optimizer.get_style_from_string(style_str)

        prompt = self._prompt_optimizer.optimize_prompt_for_context(
            query=query_text,
            context=context_str,
            style=style,
            conversation_history=conversation_context,
            confidence_scoring=False,  # Streaming responses don't typically include confidence scoring
            citation_required=True,
            max_length=(config or {}).get("max_response_length")
        )
        try:
            async for chunk in self._llm_service.generate_response_stream(prompt):
                yield chunk
        except Exception as llm_err:
            logger.error(
                f"Error streaming response from LLM: {llm_err}", exc_info=True
            )
            yield f"\n[error] {llm_err}"

    async def query(
        self, query_text: str, config: dict[str, Any] | None = None
    ) -> QueryResult:
        """Execute a complete query pipeline with retrieval, synthesis, and response generation.
        
        This method orchestrates the full GraphRAG query process including:
        - Context retrieval from vector and graph stores
        - LLM-based answer synthesis with citations
        - Performance optimization and caching
        - Advanced memory management and conversation context
        
        Args:
            query_text: The user's natural language query
            config: Optional configuration dict with keys:
                - k: Number of chunks to retrieve (default: optimized based on query)
                - search_type: "vector", "keyword", or "hybrid" (default: "hybrid")
                - include_graph: Whether to include graph context (default: True)
                - conversation_id: For conversation memory tracking
                - cache_enabled: Whether to use query caching
                - citation_style: Citation format preference
                
        Returns:
            QueryResult containing:
                - answer: Synthesized answer with citations
                - relevant_chunks: Retrieved context chunks
                - graph_context: Related entities and relationships
                - metadata: Performance metrics and processing details
                
        Raises:
            Exception: If context retrieval or LLM synthesis fails
        """
        config = config or {}
        conversation_id = config.get("conversation_id")
        query_id = str(uuid.uuid4())

        # Optimize query parameters based on patterns
        if self._query_optimizer.should_use_cache(query_text):
            config.setdefault("cache_enabled", True)

        optimal_k = self._query_optimizer.get_optimal_k(query_text)
        config.setdefault("k", optimal_k)

        # Start advanced performance tracking
        perf_context = self._performance_monitor.start_query_tracking(
            query_id,
            config.get("search_type", "hybrid")
        )

        # Create structured logging context for this query
        query_context = LogContext(
            component=ComponentType.ENGINE,
            operation="query",
            query_id=query_id,
            metadata={
                "query_length": len(query_text),
                "conversation_id": conversation_id,
                "optimal_k": optimal_k,
                "config": {k: v for k, v in config.items() if k not in ["conversation_id"]},  # Avoid duplication
            }
        )

        logger.info("Starting GraphRAG query processing", query_context, query=query_text[:100], optimal_k=optimal_k)

        retrieved_chunks_data: list[SearchResultData] = []
        graph_context_tuple: tuple[list[Entity], list[Relationship]] | None = None
        answer_text: str = "Failed to process query."
        error_info: str | None = None

        # Performance tracking variables
        retrieval_start = time.time()
        retrieval_duration_ms = 0.0
        processing_duration_ms = 0.0
        llm_duration_ms = 0.0

        # 1. Retrieve context ONCE with performance timing
        try:
            with PerformanceTimer(
                logger,
                "context_retrieval",
                context=query_context,
                threshold_ms=1000.0  # Log if context retrieval takes > 1 second
            ):
                (
                    retrieved_chunks_data,
                    graph_context_tuple,
                ) = await self._retrieve_and_build_context(query_text, config)

            retrieval_duration_ms = (time.time() - retrieval_start) * 1000

        except Exception as context_err:
            logger.error(
                "Failed to retrieve context during query",
                query_context,
                error=context_err
            )
            error_info = f"Context retrieval failed: {context_err}"
            answer_text = f"Error retrieving context: {context_err}"
            # Fall through to return QueryResult with error

        # 2. Generate answer ONCE, passing the retrieved context
        if (
            error_info is None
        ):  # Only attempt to generate answer if context retrieval was successful
            try:
                llm_start = time.time()
                answer_text = await self.answer_query(
                    query_text,
                    config,
                    _retrieved_chunks_data=retrieved_chunks_data,
                    _graph_context_tuple=graph_context_tuple,
                    conversation_id=conversation_id,
                )
                llm_duration_ms = (time.time() - llm_start) * 1000

            except Exception as answer_err:
                logger.error(
                    f"Failed to generate answer during query: {answer_err}",
                    exc_info=True,
                )
                error_info = (
                    f"Answer generation failed: {answer_err}"  # Overwrite or append?
                )
                answer_text = f"Error generating answer: {answer_err}"  # Ensure answer reflects error

        # 2.5. Add interaction to conversation memory if successful
        if conversation_id and self._context_manager and not error_info:
            try:
                await self._context_manager.add_interaction(conversation_id, query_text, answer_text)
                logger.debug(f"Added interaction to conversation {conversation_id}")
            except Exception as memory_err:
                logger.warning(f"Failed to save interaction to conversation memory: {memory_err}")

        # 3. Map SearchResultData to domain Chunk for QueryResult
        final_relevant_chunks: list[Chunk] = []
        if retrieved_chunks_data:
            for search_result in retrieved_chunks_data:
                if search_result and search_result.chunk:
                    chunk_data = search_result.chunk
                    try:
                        metadata_with_score = {
                            **(chunk_data.metadata or {}),
                            "score": search_result.score,
                        }
                        chunk_obj = Chunk(
                            id=chunk_data.id,
                            text=chunk_data.text,
                            document_id=chunk_data.document_id,
                            metadata=metadata_with_score,
                            embedding=chunk_data.embedding,
                        )
                        final_relevant_chunks.append(chunk_obj)
                    except Exception as mapping_err:
                        logger.error(
                            f"Error mapping chunk {getattr(chunk_data, 'id', '?')} to domain model: {mapping_err}",
                            exc_info=True,
                        )

        # 4. Process citations if answer generation was successful
        answer_with_citations = answer_text
        citations = []
        bibliography = {}

        if not error_info and final_relevant_chunks and hasattr(self, '_last_answer'):
            try:
                citation_result = self._citation_service.enhance_answer_with_citations(
                    answer_text,
                    final_relevant_chunks,
                    getattr(self, '_last_context_texts', None),
                    enable_verification=True  # Enable enhanced verification
                )
                answer_with_citations = citation_result.answer_with_citations
                citations = [c.to_dict() for c in citation_result.citations]
                bibliography = citation_result.bibliography

                logger.info(f"Enhanced answer with {citation_result.sources_cited}/{citation_result.total_sources} citations")

                # 5. Validate answer against source chunks
                try:
                    validation_result = self._answer_validator.validate_answer(
                        answer_text,
                        final_relevant_chunks,
                        citation_result.citations,
                        getattr(self, '_last_context_texts', None)
                    )

                    # Store validation results for metadata
                    self._last_validation_result = validation_result

                    logger.info(f"Answer validation: score={validation_result.validation_score:.2f}, valid={validation_result.is_valid}")

                except Exception as validation_err:
                    logger.error(f"Error during answer validation: {validation_err}", exc_info=True)
                    # Continue without validation if it fails

            except Exception as citation_err:
                logger.error(f"Error processing citations: {citation_err}", exc_info=True)
                # Continue with original answer if citation processing fails

        # 5. Construct and return QueryResult
        final_metadata = {
            "query": query_text,
            "config": config,
            "engine_type": self.__class__.__name__,
            "citations": citations,  # Add citations to metadata for backward compatibility
        }

        # Add validation results if available
        if hasattr(self, '_last_validation_result'):
            final_metadata.update({
                "validation": self._last_validation_result.to_dict(),
                "answer_quality": {
                    "is_valid": self._last_validation_result.is_valid,
                    "validation_score": self._last_validation_result.validation_score,
                    "hallucination_risk": self._last_validation_result.hallucination_risk,
                    "requires_fact_check": self._last_validation_result.requires_fact_check,
                }
            })
        if error_info:
            final_metadata["error"] = error_info

        # Update query context with final results
        query_context.chunk_count = len(retrieved_chunks_data)
        query_context.metadata.update({
            "chunks_retrieved": len(retrieved_chunks_data),
            "graph_entities": len(graph_context_tuple[0]) if graph_context_tuple else 0,
            "graph_relationships": len(graph_context_tuple[1]) if graph_context_tuple else 0,
            "has_error": bool(error_info),
            "answer_length": len(answer_text),
        })

        # Complete performance tracking
        try:
            cache_hit = config.get("cache_enabled", False) and not error_info

            performance_metrics = self._performance_monitor.finish_query_tracking(
                perf_context,
                retrieval_duration_ms=retrieval_duration_ms,
                processing_duration_ms=processing_duration_ms,
                llm_duration_ms=llm_duration_ms,
                chunks_retrieved=len(retrieved_chunks_data),
                entities_found=len(graph_context_tuple[0]) if graph_context_tuple else 0,
                relationships_found=len(graph_context_tuple[1]) if graph_context_tuple else 0,
                response_length=len(answer_text),
                cache_hit=cache_hit,
                cache_key=query_context.query_id
            )

            # Analyze query pattern for future optimization
            if not error_info:
                total_duration_ms = performance_metrics.total_duration_ms
                self._query_optimizer.analyze_query_pattern(
                    query_text,
                    len(retrieved_chunks_data),
                    total_duration_ms
                )

        except Exception as perf_err:
            logger.warning(f"Performance tracking error: {perf_err}")

        logger.info(
            "Completed GraphRAG query processing",
            query_context,
            success=not bool(error_info),
            answer_preview=answer_text[:100],
            total_duration_ms=retrieval_duration_ms + llm_duration_ms + processing_duration_ms
        )
        return QueryResult(
            answer=answer_text,
            relevant_chunks=final_relevant_chunks,
            graph_context=graph_context_tuple,
            metadata=final_metadata,
            answer_with_citations=answer_with_citations,
            citations=citations,
            bibliography=bibliography,
        )

    async def reason(
        self,
        question: str,
        steps: list[str | Any] | None = None,
        config: dict[str, Any] | None = None
    ) -> Any:
        """
        Perform multi-step reasoning for complex questions.
        
        This method creates a MultiStepReasoningEngine and uses it to break down
        complex questions into reasoning steps, execute each step, and synthesize
        a comprehensive answer.
        
        Args:
            question: The complex question to answer
            steps: List of reasoning steps to execute, or None to auto-generate
            config: Configuration options for reasoning
            
        Returns:
            ReasoningResult with the complete reasoning process and final answer
        """
        # Import here to avoid circular imports
        from graph_rag.core.reasoning_engine import MultiStepReasoningEngine

        reasoning_engine = MultiStepReasoningEngine(self)
        return await reasoning_engine.reason(question=question, steps=steps, config=config)


# Renaming this class to avoid conflict with the ABC above
class GraphRAGEngineOrchestrator(GraphRAGEngine):
    """Orchestrates the processing, storage, and retrieval using various components.

    Implements both document processing/storage and query capabilities.
    """

    # Add type hints for clarity and validation
    def __init__(
        self,
        document_processor: DocumentProcessor,
        entity_extractor,
        kg_builder: KnowledgeGraphBuilder,
        embedding_service: EmbeddingService,
        graph_store: GraphRepository,  # Changed from graph_repo for consistency with SimpleGraphRAGEngine?
        # Let's keep graph_repo for now based on test fixtures
        graph_repo: GraphRepository,  # Use graph_repo as per test fixture expectations
        vector_store: VectorStore,  # Added VectorStore dependency
        # search_service: Optional[SearchService] = None # Keep optional for now
    ):
        logger.info("Initializing GraphRAGEngineOrchestrator...")
        self.document_processor = document_processor
        self.entity_extractor = entity_extractor
        self.kg_builder = kg_builder
        self.embedding_service = embedding_service
        self.graph_store = graph_store
        self.graph_repo = graph_repo
        self.vector_store = vector_store
        # self.search_service = search_service
        logger.info("GraphRAGEngineOrchestrator initialized with core components.")

    async def process_and_store_document(
        self, doc_content: str, metadata: dict[str, Any]
    ) -> None:
        """Full pipeline: chunk, extract entities, build graph, store vectors."""
        doc_id = str(uuid.uuid4())  # Generate unique ID for the document
        document_data = DocumentData(id=doc_id, content=doc_content, metadata=metadata)
        logger.info(f"Processing document {doc_id}...")

        try:
            # 1. Chunk Document
            chunks = await self.document_processor.chunk_document(document_data)
            if not chunks:
                logger.warning(f"Document {doc_id} resulted in 0 chunks.")
                # Optionally add the document node even if no chunks? Depends on requirements.
                # await self.kg_builder.add_document(document_data) # Example
                return
            logger.debug(f"Document {doc_id} split into {len(chunks)} chunks.")

            # 2. Process Chunks concurrently (Extract entities, generate embeddings)
            processed_chunks_results = await asyncio.gather(
                *[self._process_chunk(chunk) for chunk in chunks]
            )

            # Filter out None results (errors during processing)
            valid_processed_chunks = [
                result for result in processed_chunks_results if result is not None
            ]
            if not valid_processed_chunks:
                logger.error(
                    f"All chunk processing failed for document {doc_id}. No data stored."
                )
                return

            # Separate chunks, entities, relationships
            final_chunks: list[ChunkData] = [data[0] for data in valid_processed_chunks]
            all_entities: dict[str, ExtractedEntity] = {}
            all_relationships: list[ExtractedRelationship] = []
            chunk_entity_links: dict[str, list[str]] = defaultdict(list)

            for chunk, extraction_result in valid_processed_chunks:
                for entity in extraction_result.entities:
                    if entity.id not in all_entities:
                        all_entities[entity.id] = entity
                    chunk_entity_links[chunk.id].append(entity.id)
                all_relationships.extend(extraction_result.relationships)

            unique_entities = list(all_entities.values())

            logger.debug(
                f"Document {doc_id}: Found {len(unique_entities)} unique entities and {len(all_relationships)} relationships across chunks."
            )

            # 3. Build Knowledge Graph (Store doc, chunks, entities, relationships, links)
            logger.debug(f"Building knowledge graph for document {doc_id}...")
            await self.kg_builder.add_document(document_data)
            # Batch add chunks, entities, relationships if builder supports it
            # Otherwise, call individual add methods
            if hasattr(
                self.kg_builder, "add_chunks_entities_relationships"
            ):  # Example check
                await self.kg_builder.add_chunks_entities_relationships(
                    final_chunks, unique_entities, all_relationships, chunk_entity_links
                )
            else:
                for chunk in final_chunks:
                    await self.kg_builder.add_chunk(chunk)
                for entity in unique_entities:
                    await self.kg_builder.add_entity(entity)
                for rel in all_relationships:
                    await self.kg_builder.add_relationship(rel)
                for chunk_id, entity_ids in chunk_entity_links.items():
                    await self.kg_builder.link_chunk_to_entities(chunk_id, entity_ids)
            logger.info(f"Knowledge graph updated for document {doc_id}.")

            # 4. Add chunks to Vector Store (if embeddings were generated)
            chunks_with_embeddings = [c for c in final_chunks if c.embedding]
            if chunks_with_embeddings:
                logger.debug(
                    f"Adding {len(chunks_with_embeddings)} chunks with embeddings to vector store for document {doc_id}..."
                )
                # Requires VectorStore instance, assuming it's accessible
                # await self.vector_store.add_chunks(chunks_with_embeddings)
                logger.info(
                    f"Added {len(chunks_with_embeddings)} chunks to vector store for document {doc_id}."
                )
            else:
                logger.debug(
                    f"No chunks with embeddings generated for document {doc_id}. Skipping vector store."
                )

        except Exception as e:
            logger.error(
                f"Error processing and storing document {doc_id}: {e}", exc_info=True
            )
            # Handle error appropriately (e.g., log, potentially attempt cleanup)
            # Re-raise for now
            raise

    async def _process_chunk(
        self, chunk: ChunkData
    ) -> tuple[ChunkData, ExtractionResult] | None:
        """Helper to process a single chunk: generate embedding and extract entities."""
        try:
            # Generate embedding (assuming generate_embedding takes single text)
            embedding = await self.embedding_service.generate_embedding(chunk.text)
            chunk.embedding = embedding
            logger.debug(f"Generated embedding for chunk {chunk.id}")

            # Extract entities (assuming extract takes single text)
            extraction_result = await self.entity_extractor.extract(chunk.text)
            logger.debug(
                f"Extracted {len(extraction_result.entities)} entities, {len(extraction_result.relationships)} relationships from chunk {chunk.id}"
            )

            return chunk, extraction_result
        except Exception as e:
            logger.error(f"Failed to process chunk {chunk.id}: {e}", exc_info=True)
            return None  # Return None to indicate failure

    async def retrieve_context(
        self, query: str, search_type: str = "vector", limit: int = 5
    ) -> list[SearchResult]:
        """Retrieve relevant context chunks for a query using SearchService."""
        logger.info(
            f"Retrieving context for query '{query}' using type '{search_type}' (limit={limit})"
        )
        results: list[SearchResult] = []
        try:
            if search_type == "vector":
                # Use SearchService method for similarity search
                results = await self.search_service.search_chunks_by_similarity(
                    query, limit=limit
                )
            elif search_type == "keyword":
                # Use SearchService method for keyword search
                results = await self.search_service.search_chunks(query, limit=limit)
            # Remove graph search for now as SearchService doesn't directly support it
            # elif search_type == 'graph':
            #     # Requires graph traversal logic, possibly using entity extraction first
            #     # Placeholder: Extract entities from query, then use graph_searcher
            #     logger.warning("Graph search not fully implemented via SearchService yet.")
            #     # extraction = await self.entity_extractor.extract(query)
            #     # if extraction.entities:
            #     #     first_entity_id = extraction.entities[0].id # Simple example
            #     #     results = await self.graph_searcher.find_related_chunks(first_entity_id, limit=limit)
            #     pass # No results for now
            else:
                raise ValueError(f"Unsupported search type: {search_type}")

            logger.info(f"Retrieved {len(results)} results using {search_type} search.")

            # Convert SearchResult to SearchResultData if needed by downstream consumers
            # For now, return SearchResult as defined in search.py
            # return [SearchResultData(chunk=ChunkData(**r.dict()), score=r.score) for r in results] # Example conversion
            return results

        except Exception as e:
            logger.error(
                f"Error retrieving context for query '{query}': {e}", exc_info=True
            )
            return []  # Return empty list on error

    async def stream_context(
        self, query: str, search_type: str = "vector", limit: int = 5
    ) -> AsyncGenerator[SearchResult, None]:
        """Retrieve relevant context chunks as an asynchronous stream."""
        logger.info(
            f"Streaming context for query '{query}' using type '{search_type}' (limit={limit})"
        )
        try:
            # Streaming is more complex. SearchService needs stream methods, or we retrieve all then yield.
            # For simplicity, retrieve all then yield (less efficient for large results).
            results = await self.retrieve_context(query, search_type, limit)
            logger.debug(f"Retrieved {len(results)} results, now streaming...")
            for result in results:
                yield result
            logger.info("Finished streaming context.")

        except Exception as e:
            logger.error(
                f"Error streaming context for query '{query}': {e}", exc_info=True
            )
            # How to signal error in async generator? Could raise exception.
            raise  # Re-raise the exception within the generator

    async def query(
        self, query_text: str, config: dict[str, Any] | None = None
    ) -> QueryResult:
        """Retrieve context and generate a basic query response with placeholder LLM answer.
        
        This is a simplified implementation that focuses on context retrieval without
        full LLM integration. Used primarily for testing and development scenarios.
        
        Args:
            query_text: The user's natural language query
            config: Optional configuration dict with keys:
                - search_type: "vector" or "keyword" (default: "vector")
                - limit: Number of chunks to retrieve (default: 5)
                
        Returns:
            QueryResult with retrieved chunks and placeholder answer
        """
        logger.info(f"Answering query: '{query_text}' with config: {config}")
        config = config or {}
        search_type = config.get("search_type", "vector")
        limit = config.get("limit", 5)

        # 1. Retrieve context
        # retrieve_context returns List[SearchResult]
        context_results: list[SearchResult] = await self.retrieve_context(
            query=query_text, search_type=search_type, limit=limit
        )

        relevant_chunks_data = [
            res.chunk for res in context_results
        ]  # Assuming SearchResult has a 'chunk' attribute of type ChunkData or similar

        # Convert ChunkData back to Chunk model if necessary for QueryResult
        # Assuming QueryResult expects graph_rag.models.Chunk
        # This might require importing Chunk from graph_rag.models if not already done
        relevant_chunks_model: list[Chunk] = []
        for chunk_data in relevant_chunks_data:
            # Need to map ChunkData fields to Chunk fields
            # Simplified mapping - might need adjustment based on actual models
            relevant_chunks_model.append(
                Chunk(
                    id=chunk_data.id,
                    document_id=chunk_data.document_id,
                    text=chunk_data.text,  # Map text to content
                    embedding=chunk_data.embedding,
                    score=chunk_data.score,  # Set score directly on the chunk
                    metadata={"score": chunk_data.score},  # Also store score in metadata for backward compatibility
                )
            )

        if not relevant_chunks_model:
            answer = "Could not find relevant information to answer the query."
        else:
            # Simple placeholder answer
            context_parts = []
            for c in relevant_chunks_model:
                if isinstance(c, SearchResultData):
                    # Access text through the chunk attribute for SearchResultData
                    context_parts.append(c.chunk.text)
                elif hasattr(
                    c, "text"
                ):  # Handle other potential types with a text attribute
                    context_parts.append(c.text)
                # If neither, maybe log a warning or skip?
                # else: logger.warning(f"Chunk object {c} lacks expected text attribute.")

            context_str = "\n\n".join(context_parts)
            logger.debug(f"Built context string: {context_str}")
            answer = f"Found relevant context: {context_str[:200]}..."

        # 2. Construct QueryResult
        return QueryResult(
            answer=answer,
            relevant_chunks=relevant_chunks_model,
            graph_context=None,  # Placeholder
            metadata={
                "query": query_text,
                "config": config,
                "retrieval_details": {
                    "type": search_type,
                    "limit": limit,
                    "num_retrieved": len(relevant_chunks_model),
                },
            },
        )

    # Remove or comment out the old answer_query method if it wasn't replaced above
    # async def answer_query(self, query: str) -> str:
    #     ...

    async def _retrieve_graph_context(
        self,
        extracted_entities: list[ExtractedEntity],
        extracted_relationships: list[ExtractedRelationship],
        config: dict | None = None,
    ) -> tuple[list[Entity], list[Relationship]] | None:
        """
        Retrieves related entities and relationships from the graph store
        based on the entities extracted from the vector search results.

        Args:
            extracted_entities: Entities extracted from relevant chunks.
            extracted_relationships: Relationships extracted from relevant chunks.
            config: Query configuration dictionary.

        Returns:
            A tuple containing lists of related entities and relationships from the graph,
            or None if graph retrieval is disabled or fails.
        """
        config = config or {}
        include_graph = config.get("include_graph", True)
        limit_neighbors = config.get("limit_neighbors", 10)
        limit_entities = config.get(
            "limit_entities", 10
        )  # Limit for initial entity search

        if not include_graph:
            logger.info("Graph context retrieval skipped (include_graph=False).")
            return None

        if not extracted_entities:
            logger.info(
                "No entities extracted from chunks, skipping graph context retrieval."
            )
            return None

        try:
            logger.debug(
                f"Searching graph for {len(extracted_entities)} extracted entities..."
            )

            # Convert extracted entities to graph entities
            graph_entities = [e for e in extracted_entities]

            # Use the graph store to search for entities based on properties
            # Pass the list of ExtractedEntity objects directly
            seed_entities: list[
                Entity
            ] = await self._graph_repo.search_entities_by_properties(
                graph_entities, limit=limit_entities
            )

            if not seed_entities:
                logger.info(
                    "No matching entities found in graph for extracted entities."
                )
                # Return empty tuple to indicate search was done but found nothing
                return ([], [])

            logger.debug(
                f"Found {len(seed_entities)} seed entities in graph: {[e.name for e in seed_entities]}"
            )

            # Get neighbors for the seed entities
            seed_entity_ids = [e.id for e in seed_entities]
            (
                neighbor_entities,
                neighbor_relationships,
            ) = await self._graph_repo.get_neighbors(
                seed_entity_ids, limit=limit_neighbors
            )
            logger.debug(
                f"Retrieved {len(neighbor_entities)} neighbor entities and "
                f"{len(neighbor_relationships)} relationships."
            )

            # Combine seed entities and neighbor entities, removing duplicates
            all_entities_dict = {e.id: e for e in seed_entities + neighbor_entities}
            final_entities = list(all_entities_dict.values())

            # Combine extracted relationships (if any) and neighbor relationships, removing duplicates
            # TODO: Potentially map extracted_relationships to graph relationship IDs if needed
            all_relationships_dict = {r.id: r for r in neighbor_relationships}
            final_relationships = list(all_relationships_dict.values())

            logger.debug(
                f"Final graph context: {len(final_entities)} entities, {len(final_relationships)} relationships."
            )
            return (final_entities, final_relationships)

        except Exception as e:
            logger.exception(f"Error retrieving graph context: {e}", exc_info=True)
            return None  # Return None on error during graph retrieval
