import asyncio  # For potential concurrent processing
import logging
import uuid
from collections import defaultdict  # Add this import
from collections.abc import AsyncGenerator
from dataclasses import dataclass, field
from typing import Any, Optional, Union

from graph_rag.config import get_settings
from graph_rag.core.entity_extractor import EntityExtractor  # Import base class
from graph_rag.core.interfaces import (
    ChunkData,
    DocumentData,
    DocumentProcessor,
    EmbeddingService,
    EntityExtractor,
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
from graph_rag.models import Chunk, Entity, Relationship
from graph_rag.services.search import (
    SearchResult,
)  # Import SearchResult model too

# from graph_rag.core.prompts import QnAPromptContext # Import QnAPromptContext
# from graph_rag.core.prompts as prompts # Corrected import alias
# from graph_rag.core.prompts import (
#     GRAPH_EXTRACTION_PROMPT,
#     GRAPH_REPORT_PROMPT,
# )

logger = logging.getLogger(__name__)
settings = get_settings()


@dataclass
class QueryResult:
    """Represents the result of a query."""

    relevant_chunks: list[Chunk] = field(default_factory=list)
    answer: str = ""
    llm_response: str = ""  # Added for test compatibility
    graph_context: Union[Optional[tuple[list[Entity], list[Relationship]]], str] = (
        None  # Support both tuple and string formats
    )
    metadata: dict[str, Any] = field(default_factory=dict)


class SimpleGraphRAGEngine(GraphRAGEngine):
    """A basic implementation combining graph and vector retrieval."""

    def __init__(
        self,
        graph_store: GraphRepository,
        vector_store: VectorStore,
        entity_extractor: EntityExtractor,
        llm_service: LLMService = None,
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
        logger.info(
            f"SimpleGraphRAGEngine initialized with GraphRepository: {type(graph_store).__name__}, VectorStore: {type(vector_store).__name__}, EntityExtractor: {type(entity_extractor).__name__}, LLMService: {type(self._llm_service).__name__}"
        )

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
        self, query_text: str, config: Optional[dict[str, Any]] = None
    ) -> tuple[
        list[SearchResultData], Optional[tuple[list[Entity], list[Relationship]]]
    ]:
        """Internal method to perform vector search and graph context retrieval. DOES NOT call LLM."""
        logger.info(f"Retrieving context for: '{query_text}' with config: {config}")
        config = config or {}
        k = config.get("k", 3)
        include_graph = config.get("include_graph", True)

        final_entities: list[Entity] = []
        final_relationships: list[Relationship] = []
        graph_context_tuple: Optional[tuple[list[Entity], list[Relationship]]] = None
        relevant_chunk_texts: list[str] = []
        retrieved_chunks_full: list[
            SearchResultData
        ] = []  # Store full SearchResultData

        try:
            # 1. Vector Search
            logger.debug(f"Performing vector search for: '{query_text}' (k={k})")
            retrieved_chunks_full = await self._vector_store.search(query_text, top_k=k)
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

            # 2. Graph Retrieval (if requested and chunks were found)
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

            # 3. Return the retrieved context
            logger.info(
                f"Context retrieval finished. Found {len(retrieved_chunks_full)} chunks and {len(final_entities) if graph_context_tuple else 0} graph entities."
            )
            return retrieved_chunks_full, graph_context_tuple

        except Exception as e:
            logger.error(
                f"Error during query processing for '{query_text}': {e}", exc_info=True
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
        """Stream relevant context chunks.

        Minimal vector-only implementation to support API streaming paths.
        """
        if search_type != "vector":
            raise ValueError(f"Unsupported search type for streaming: {search_type}")
        logger.info(
            f"Streaming context (vector) for query '{query}' (limit={limit})"
        )
        results = await self._vector_store.search(query, top_k=limit)
        for item in results:
            yield item

    async def answer_query(
        self,
        query_text: str,
        config: Optional[dict[str, Any]] = None,
        # Allow passing pre-fetched context
        _retrieved_chunks_data: Optional[list[SearchResultData]] = None,
        _graph_context_tuple: Optional[tuple[list[Entity], list[Relationship]]] = None,
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
            return "Could not find relevant information to answer the query."

        # 3. Create Prompt and Call LLM
        prompt = f"Based on the following context, answer the query.\\n\\nQuery: {query_text}\\n\\nContext:{context_str}\\n\\nAnswer:"
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
            return answer_text
        except Exception as llm_err:
            logger.error(
                f"Error generating response from LLM: {llm_err}", exc_info=True
            )
            return f"Error generating answer: {llm_err}"

    async def query(
        self, query_text: str, config: Optional[dict[str, Any]] = None
    ) -> QueryResult:
        logger.info(f"[DEBUG] Entered SimpleGraphRAGEngine.query for: '{query_text}'")
        config = config or {}

        retrieved_chunks_data: list[SearchResultData] = []
        graph_context_tuple: Optional[tuple[list[Entity], list[Relationship]]] = None
        answer_text: str = "Failed to process query."
        error_info: Optional[str] = None

        # 1. Retrieve context ONCE
        try:
            (
                retrieved_chunks_data,
                graph_context_tuple,
            ) = await self._retrieve_and_build_context(query_text, config)
        except Exception as context_err:
            logger.error(
                f"Failed to retrieve context during query: {context_err}", exc_info=True
            )
            error_info = f"Context retrieval failed: {context_err}"
            answer_text = f"Error retrieving context: {context_err}"
            # Fall through to return QueryResult with error

        # 2. Generate answer ONCE, passing the retrieved context
        if (
            error_info is None
        ):  # Only attempt to generate answer if context retrieval was successful
            try:
                answer_text = await self.answer_query(
                    query_text,
                    config,
                    _retrieved_chunks_data=retrieved_chunks_data,
                    _graph_context_tuple=graph_context_tuple,
                )
            except Exception as answer_err:
                logger.error(
                    f"Failed to generate answer during query: {answer_err}",
                    exc_info=True,
                )
                error_info = (
                    f"Answer generation failed: {answer_err}"  # Overwrite or append?
                )
                answer_text = f"Error generating answer: {answer_err}"  # Ensure answer reflects error

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

        # 4. Construct and return QueryResult
        final_metadata = {
            "query": query_text,
            "config": config,
            "engine_type": self.__class__.__name__,
        }
        if error_info:
            final_metadata["error"] = error_info

        logger.info(
            f"[DEBUG] Returning QueryResult from SimpleGraphRAGEngine.query for: '{query_text}' with answer: {answer_text}"
        )
        return QueryResult(
            answer=answer_text,
            relevant_chunks=final_relevant_chunks,
            graph_context=graph_context_tuple,
            metadata=final_metadata,
        )


# Renaming this class to avoid conflict with the ABC above
class GraphRAGEngineOrchestrator(GraphRAGEngine):
    """Orchestrates the processing, storage, and retrieval using various components.

    Implements both document processing/storage and query capabilities.
    """

    # Add type hints for clarity and validation
    def __init__(
        self,
        document_processor: DocumentProcessor,
        entity_extractor: EntityExtractor,
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
    ) -> Optional[tuple[ChunkData, ExtractionResult]]:
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
        self, query_text: str, config: Optional[dict[str, Any]] = None
    ) -> QueryResult:
        """Retrieve context and package into a QueryResult (Placeholder answer)."""
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
                    content=chunk_data.text,  # Map text to content
                    embedding=chunk_data.embedding,
                    # score=chunk_data.score # Chunk model might not have score
                    metadata={"score": chunk_data.score},  # Store score in metadata
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
        config: Optional[dict] = None,
    ) -> Optional[tuple[list[Entity], list[Relationship]]]:
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
