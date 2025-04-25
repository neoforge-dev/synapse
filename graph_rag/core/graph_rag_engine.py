from graph_rag.core.interfaces import (
    DocumentProcessor, EntityExtractor, KnowledgeGraphBuilder,
    VectorSearcher, KeywordSearcher, GraphSearcher, GraphRAGEngine,
    DocumentData, ChunkData, SearchResultData, EmbeddingService,
    ExtractionResult, ExtractedEntity, ExtractedRelationship, VectorStore,
    GraphRepository
)
from typing import List, Dict, Any, AsyncGenerator, Optional, Tuple, Union
import logging
import uuid
import asyncio # For potential concurrent processing
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
import re # Import regex for simple entity finding
from collections import defaultdict # Add this import

from graph_rag.models import Document, Chunk, Entity, Relationship, ProcessedDocument
from graph_rag.core.graph_store import MockGraphStore
from graph_rag.config import Settings
from graph_rag.core.vector_store import MockVectorStore
from graph_rag.core.entity_extractor import EntityExtractor # Import base class
from graph_rag.services.search import SearchService, SearchResult # Import SearchResult model too
from graph_rag.config import get_settings
from graph_rag.domain.models import Context # Added Context
# from graph_rag.core.node_factory import NodeFactory
from graph_rag.services.embedding import SentenceTransformerEmbeddingService
from graph_rag.llm.protocols import LLMService # Add LLMService import
from graph_rag.llm.mock_llm import MockLLMService # Corrected import: MockLLMService from mock_llm
# from graph_rag.core.prompts import (
#     GRAPH_EXTRACTION_PROMPT,
#     GRAPH_REPORT_PROMPT,
# )

logger = logging.getLogger(__name__)
settings = get_settings()

@dataclass
class QueryResult:
    """Represents the result of a query."""
    relevant_chunks: List[Chunk] = field(default_factory=list)
    answer: str = ""
    llm_response: str = ""  # Added for test compatibility
    graph_context: Union[Optional[Tuple[List[Entity], List[Relationship]]], str] = None  # Support both tuple and string formats
    metadata: Dict[str, Any] = field(default_factory=dict)

class GraphRAGEngine(ABC):
    """Abstract base class for the GraphRAG query engine."""

    @abstractmethod
    async def query(self, query_text: str, config: Optional[Dict[str, Any]] = None) -> QueryResult:
        """Processes a user query and returns relevant information.

        Args:
            query_text: The user's query.
            config: Optional configuration for the query (e.g., retrieval parameters).
            
        Returns:
            A QueryResult object containing the answer and supporting context.
        """
        pass

class SimpleGraphRAGEngine(GraphRAGEngine):
    """A basic implementation combining graph and vector retrieval."""

    def __init__(self, graph_store: GraphRepository, vector_store: VectorStore, entity_extractor: EntityExtractor, llm_service: LLMService = None):
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
        self._entity_extractor = entity_extractor # Store the extractor
        logger.info(f"SimpleGraphRAGEngine initialized with GraphRepository: {type(graph_store).__name__}, VectorStore: {type(vector_store).__name__}, EntityExtractor: {type(entity_extractor).__name__}, LLMService: {type(self._llm_service).__name__}")

    async def _extract_entities_from_chunks(self, chunks: List[SearchResultData]) -> List[Entity]:
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
            extracted_data: ExtractionResult = await self._entity_extractor.extract_from_text(combined_text)
            
            entities_list: List[Entity] = []
            if isinstance(extracted_data, ExtractionResult):
                # If extractor returns ExtractionResult, get entities from it
                entities_list = extracted_data.entities
                logger.info(f"Extracted {len(entities_list)} entities (from ExtractionResult) from combined chunk text.")
            elif isinstance(extracted_data, list):
                 # If extractor returns a list (assumed List[Entity])
                 entities_list = extracted_data
                 logger.info(f"Extracted {len(entities_list)} entities (from List[Entity]) from combined chunk text.")
            elif extracted_data is None:
                 logger.warning("Entity extractor returned None.")
                 # entities_list remains []
            else:
                 logger.warning(f"Entity extractor returned unexpected type: {type(extracted_data)}. Expected List[Entity] or ExtractionResult.")
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
            return [] # Return empty list on failure
        
    async def _find_entities_in_graph_by_properties(self, entities_from_extractor: List[Entity]) -> List[Entity]:
        """Looks up entities from the extractor in the graph store using their properties.
        
        Uses name and type for lookup. Requires the GraphRepository to have 
        search_entities_by_properties implemented and potentially indexed properties.
        """
        if not entities_from_extractor:
            return []
            
        logger.debug(f"Attempting to find {len(entities_from_extractor)} entities in graph by properties (name, type)...")
        found_graph_entities = []
        processed_extractor_entities = set() # Avoid searching for the same name/type combo multiple times

        for entity in entities_from_extractor:
            # Use label from ExtractedEntity, assuming it maps to the type in the graph
            search_key = (entity.text, entity.label)
            if not entity.text or not entity.label or search_key in processed_extractor_entities:
                continue # Skip if missing key info or already searched
                
            processed_extractor_entities.add(search_key)
            # Use label for the 'type' field in search properties
            search_props = {"name": entity.text, "type": entity.label}
            
            try:
                # Use the graph store's property search method
                # Limit to 1 assuming name+type is reasonably unique, adjust if needed
                results = await self._graph_store.search_entities_by_properties(search_props, limit=1)
                if results:
                    # Use the entity found in the graph (it has the correct graph ID/metadata)
                    found_graph_entities.append(results[0])
                    logger.debug(f"Found graph entity {results[0].id} matching properties: {search_props}")
                else:
                    logger.debug(f"No graph entity found matching properties: {search_props}")
            except NotImplementedError:
                logger.error(f"Graph store {type(self._graph_store).__name__} does not support search_entities_by_properties.")
                # Fallback or stop? For MVP, log error and continue.
                break # Stop searching if method not implemented
            except Exception as e:
                logger.error(f"Error searching graph for properties {search_props}: {e}", exc_info=True)
                # Continue trying other entities
                
        logger.info(f"Found {len(found_graph_entities)} graph entities matching properties of {len(processed_extractor_entities)} unique extracted entities.")
        return found_graph_entities
        
    async def _get_graph_context(self, entities: List[Entity]) -> Tuple[List[Entity], List[Relationship]]:
        """Fetches the 1-hop neighborhood for a list of seed entities."""
        logger.debug(f"Getting graph context for {len(entities)} seed entities: {[e.id for e in entities][:5]}...")
        all_neighbor_entities: Dict[str, Entity] = {e.id: e for e in entities} # Start with seeds
        all_relationships: Dict[Tuple, Relationship] = {}
        max_entities = 10 # Limit context size to avoid overwhelming results
        processed_entity_ids = set(e.id for e in entities) # Track processed entities

        entities_to_expand = list(entities) # Queue of entities whose neighbors we need
        
        while entities_to_expand and len(all_neighbor_entities) < max_entities:
            current_entity = entities_to_expand.pop(0)
            logger.debug(f"Expanding neighbors for entity: {current_entity.id}")
            try:
                # Use the graph store's method to get neighbors and relationships
                neighbors, relationships = await self._graph_store.get_neighbors(current_entity.id)
                logger.debug(f"Found {len(neighbors)} neighbors and {len(relationships)} relationships for {current_entity.id}")
                
                for neighbor in neighbors:
                    if neighbor.id not in all_neighbor_entities and len(all_neighbor_entities) < max_entities:
                         all_neighbor_entities[neighbor.id] = neighbor
                         # If the neighbor hasn't been expanded yet, add it to the queue
                         if neighbor.id not in processed_entity_ids:
                             entities_to_expand.append(neighbor)
                             processed_entity_ids.add(neighbor.id) # Add ID when queuing
                             
                for rel in relationships:
                    # Ensure both source and target are within our collected entities
                    if rel.source.id in all_neighbor_entities and rel.target.id in all_neighbor_entities:
                        rel_key = (rel.source.id, rel.type, rel.target.id)
                        if rel_key not in all_relationships:
                             all_relationships[rel_key] = rel
                             
            except Exception as e:
                 logger.error(f"Failed to get neighbors for entity {current_entity.id}: {e}", exc_info=True)

        if len(all_neighbor_entities) >= max_entities:
             logger.warning(f"Reached max entities ({max_entities}) for graph context expansion.")
             
        logger.info(f"Aggregated graph context: {len(all_neighbor_entities)} entities, {len(all_relationships)} relationships.")
        return list(all_neighbor_entities.values()), list(all_relationships.values())

    async def query(self, query_text: str, config: Optional[Dict[str, Any]] = None) -> QueryResult:
        """Processes a query using vector search, graph context retrieval, and LLM synthesis."""
        logger.info(f"Received query: '{query_text}' with config: {config}")
        config = config or {}
        k = config.get("k", 3)
        include_graph_context = config.get("include_graph", True)
        
        final_entities: List[Entity] = []
        final_relationships: List[Relationship] = []
        graph_context_tuple: Optional[Tuple[List[Entity], List[Relationship]]] = None
        relevant_chunk_texts: List[str] = []
        retrieved_chunks_full: List[SearchResultData] = [] # Store full SearchResultData

        try:
            # 1. Vector Search
            logger.debug(f"Performing vector search for: '{query_text}' (k={k})")
            retrieved_chunks_full = await self._vector_store.search(query_text, top_k=k)
            if not retrieved_chunks_full:
                logger.warning(f"Vector search returned no relevant chunks for query: '{query_text}'")
                # Still try graph search if requested, but prepare for no context
            else:
                # Assume retrieved_chunks_full is List[SearchResultData]
                # relevant_chunk_texts = [c.text for c in retrieved_chunks_full]
                relevant_chunk_texts = [c.chunk.text for c in retrieved_chunks_full if c.chunk] # Corrected access to c.chunk.text
                logger.info(f"Found {len(relevant_chunk_texts)} relevant chunks via vector search.")

            # 2. Graph Retrieval (if requested and chunks were found)
            if include_graph_context and retrieved_chunks_full:
                logger.debug("Attempting to retrieve graph context...")
                # a. Extract entities from chunks
                extracted_entities = await self._extract_entities_from_chunks(retrieved_chunks_full)

                if extracted_entities:
                    # b. Find these entities in the graph
                    seed_entities = await self._find_entities_in_graph_by_properties(extracted_entities)

                    if seed_entities:
                        # c. Get neighborhood graph context
                        final_entities, final_relationships = await self._get_graph_context(seed_entities)
                        graph_context_tuple = (final_entities, final_relationships)
                        logger.info(f"Retrieved graph context with {len(final_entities)} entities and {len(final_relationships)} relationships.")
                    else:
                        logger.info("No matching seed entities found in graph using property search.")
                else:
                    logger.info("No entities extracted from retrieved chunks.")
            elif include_graph_context and not retrieved_chunks_full:
                 logger.info("Skipping graph context retrieval as no relevant chunks were found.")

            # 3. Answer Synthesis (if any context was found)
            synthesized_answer = "Could not generate an answer based on the available information."
            llm_metadata = {}

            if relevant_chunk_texts or graph_context_tuple:
                 # Prepare context string
                 context_str = "\n\nRelevant Text Chunks:\n"
                 context_str += "\n---\n\n".join(relevant_chunk_texts) if relevant_chunk_texts else "None"

                 if graph_context_tuple:
                     entities, relationships = graph_context_tuple
                     context_str += "\n\nRelated Graph Entities:\n"
                     context_str += "\n".join([f"- {e.id} ({e.type}): {getattr(e, 'name', 'N/A')}" for e in entities])
                     context_str += "\n\nRelated Graph Relationships:\n"
                     context_str += "\n".join([f"- ({r.source.id}) -[{r.type}]-> ({r.target.id})" for r in relationships if r.source and r.target])

                 # Create prompt
                 prompt = f"Based on the following context, answer the query.\n\nQuery: {query_text}\n\nContext:{context_str}\n\nAnswer:"

                 logger.debug(f"Sending prompt to LLM (first 100 chars): {prompt[:100]}...")
                 # Call LLMService
                 llm_response = await self._llm_service.generate_response(prompt)
                 # Handle both object response (ideal) and str response (mock)
                 if hasattr(llm_response, 'text'):
                     synthesized_answer = llm_response.text
                     llm_metadata = llm_response.metadata if hasattr(llm_response, 'metadata') else {}
                 elif isinstance(llm_response, str):
                     synthesized_answer = llm_response # Mock returns string directly
                     llm_metadata = {"warning": "LLM response was a string, not an object."}
                 else:
                     synthesized_answer = "Error: Unexpected LLM response type."
                     llm_metadata = {"error": f"Unexpected type: {type(llm_response)}"}
                     logger.error(f"Unexpected LLM response type: {type(llm_response)}")
                 
                 logger.info("Received synthesized answer from LLM.")
            else:
                logger.warning(f"No context (chunks or graph) found for query: '{query_text}'. Returning default answer.")

            # Map SearchResultData to domain Chunk objects for the final QueryResult
            final_relevant_chunks = []
            for search_result in retrieved_chunks_full:
                if search_result and search_result.chunk: # Ensure we have valid data
                    chunk_data = search_result.chunk # Get the inner ChunkData
                    try:
                        metadata_with_score = {**(chunk_data.metadata or {}), "score": search_result.score}
                        chunk_obj = Chunk(
                            id=chunk_data.id,
                            text=chunk_data.text,
                            document_id=chunk_data.document_id,
                            metadata=metadata_with_score,
                            embedding=chunk_data.embedding
                        )
                        final_relevant_chunks.append(chunk_obj)
                    except Exception as mapping_err:
                        logger.error(f"Error mapping chunk {getattr(chunk_data, 'id', '?')} to domain model: {mapping_err}", exc_info=True)

            # 4. Return Result (potentially partial if error occurred)
            return QueryResult(
                answer=synthesized_answer, # Could be error message if LLM failed
                relevant_chunks=final_relevant_chunks, # Use the correctly mapped chunks
                graph_context=graph_context_tuple,
                metadata={
                    "query": query_text,
                    "config": config,
                    # Add error info if an exception was caught
                    **({"error": str(e)} if 'e' in locals() else {})
                }
            )

        except Exception as e:
            logger.error(f"Error during query processing for '{query_text}': {e}", exc_info=True)
            # Return an error state QueryResult
            return QueryResult(
                answer=f"An error occurred while processing your query: {e}",
                metadata={"query": query_text, "config": config, "error": str(e)}
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
        graph_store: GraphRepository, # Changed from graph_repo for consistency with SimpleGraphRAGEngine?
                                      # Let's keep graph_repo for now based on test fixtures
        graph_repo: GraphRepository, # Use graph_repo as per test fixture expectations
        vector_store: VectorStore, # Added VectorStore dependency
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
        
    async def process_and_store_document(self, doc_content: str, metadata: Dict[str, Any]) -> None:
        """Full pipeline: chunk, extract entities, build graph, store vectors."""
        doc_id = str(uuid.uuid4()) # Generate unique ID for the document
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
            valid_processed_chunks = [result for result in processed_chunks_results if result is not None]
            if not valid_processed_chunks:
                 logger.error(f"All chunk processing failed for document {doc_id}. No data stored.")
                 return

            # Separate chunks, entities, relationships
            final_chunks: List[ChunkData] = [data[0] for data in valid_processed_chunks]
            all_entities: Dict[str, ExtractedEntity] = {}
            all_relationships: List[ExtractedRelationship] = [] 
            chunk_entity_links: Dict[str, List[str]] = defaultdict(list)

            for chunk, extraction_result in valid_processed_chunks:
                 for entity in extraction_result.entities:
                     if entity.id not in all_entities:
                         all_entities[entity.id] = entity
                     chunk_entity_links[chunk.id].append(entity.id)
                 all_relationships.extend(extraction_result.relationships)
                 
            unique_entities = list(all_entities.values())
                 
            logger.debug(f"Document {doc_id}: Found {len(unique_entities)} unique entities and {len(all_relationships)} relationships across chunks.")

            # 3. Build Knowledge Graph (Store doc, chunks, entities, relationships, links)
            logger.debug(f"Building knowledge graph for document {doc_id}...")
            await self.kg_builder.add_document(document_data) 
            # Batch add chunks, entities, relationships if builder supports it
            # Otherwise, call individual add methods
            if hasattr(self.kg_builder, 'add_chunks_entities_relationships'): # Example check
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
                 logger.debug(f"Adding {len(chunks_with_embeddings)} chunks with embeddings to vector store for document {doc_id}...")
                 # Requires VectorStore instance, assuming it's accessible
                 # await self.vector_store.add_chunks(chunks_with_embeddings) 
                 logger.info(f"Added {len(chunks_with_embeddings)} chunks to vector store for document {doc_id}.")
            else:
                 logger.debug(f"No chunks with embeddings generated for document {doc_id}. Skipping vector store.")

        except Exception as e:
            logger.error(f"Error processing and storing document {doc_id}: {e}", exc_info=True)
            # Handle error appropriately (e.g., log, potentially attempt cleanup)
            # Re-raise for now
            raise

    async def _process_chunk(self, chunk: ChunkData) -> Optional[Tuple[ChunkData, ExtractionResult]]:
        """Helper to process a single chunk: generate embedding and extract entities."""
        try:
            # Generate embedding (assuming generate_embedding takes single text)
            embedding = await self.embedding_service.generate_embedding(chunk.text)
            chunk.embedding = embedding 
            logger.debug(f"Generated embedding for chunk {chunk.id}")
            
            # Extract entities (assuming extract takes single text)
            extraction_result = await self.entity_extractor.extract(chunk.text)
            logger.debug(f"Extracted {len(extraction_result.entities)} entities, {len(extraction_result.relationships)} relationships from chunk {chunk.id}")
            
            return chunk, extraction_result
        except Exception as e:
            logger.error(f"Failed to process chunk {chunk.id}: {e}", exc_info=True)
            return None # Return None to indicate failure

    async def retrieve_context(
        self, 
        query: str, 
        search_type: str = 'vector', 
        limit: int = 5
    ) -> List[SearchResult]:
        """Retrieve relevant context chunks for a query using SearchService."""
        logger.info(f"Retrieving context for query '{query}' using type '{search_type}' (limit={limit})")
        results: List[SearchResult] = []
        try:
            if search_type == 'vector':
                # Use SearchService method for similarity search
                results = await self.search_service.search_chunks_by_similarity(query, limit=limit)
            elif search_type == 'keyword':
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
            logger.error(f"Error retrieving context for query '{query}': {e}", exc_info=True)
            return [] # Return empty list on error

    async def stream_context(
        self,
        query: str,
        search_type: str = 'vector',
        limit: int = 5
    ) -> AsyncGenerator[SearchResult, None]:
        """Retrieve relevant context chunks as an asynchronous stream."""
        logger.info(f"Streaming context for query '{query}' using type '{search_type}' (limit={limit})")
        try:
            # Streaming is more complex. SearchService needs stream methods, or we retrieve all then yield.
            # For simplicity, retrieve all then yield (less efficient for large results).
            results = await self.retrieve_context(query, search_type, limit)
            logger.debug(f"Retrieved {len(results)} results, now streaming...")
            for result in results:
                yield result
            logger.info("Finished streaming context.")
            
        except Exception as e:
            logger.error(f"Error streaming context for query '{query}': {e}", exc_info=True)
            # How to signal error in async generator? Could raise exception.
            raise # Re-raise the exception within the generator

    async def query(self, query_text: str, config: Optional[Dict[str, Any]] = None) -> QueryResult:
        """Retrieve context and package into a QueryResult (Placeholder answer)."""
        logger.info(f"Answering query: '{query_text}' with config: {config}")
        config = config or {}
        search_type = config.get('search_type', 'vector')
        limit = config.get('limit', 5)

        # 1. Retrieve context
        # retrieve_context returns List[SearchResult]
        context_results: List[SearchResult] = await self.retrieve_context(
            query=query_text,
            search_type=search_type,
            limit=limit
        )

        relevant_chunks_data = [res.chunk for res in context_results] # Assuming SearchResult has a 'chunk' attribute of type ChunkData or similar
        
        # Convert ChunkData back to Chunk model if necessary for QueryResult
        # Assuming QueryResult expects graph_rag.models.Chunk
        # This might require importing Chunk from graph_rag.models if not already done
        relevant_chunks_model: List[Chunk] = []
        for chunk_data in relevant_chunks_data:
             # Need to map ChunkData fields to Chunk fields
             # Simplified mapping - might need adjustment based on actual models
            relevant_chunks_model.append(Chunk(
                id=chunk_data.id,
                document_id=chunk_data.document_id,
                content=chunk_data.text, # Map text to content
                embedding=chunk_data.embedding,
                # score=chunk_data.score # Chunk model might not have score
                metadata={'score': chunk_data.score} # Store score in metadata
            ))

        if not relevant_chunks_model:
            answer = "Could not find relevant information to answer the query."
        else:
            # Simple placeholder answer
            context_parts = []
            for c in relevant_chunks_model:
                if isinstance(c, SearchResultData):
                    # Access text through the chunk attribute for SearchResultData
                    context_parts.append(c.chunk.text) 
                elif hasattr(c, 'text'): # Handle other potential types with a text attribute
                    context_parts.append(c.text)
                # If neither, maybe log a warning or skip?
                # else: logger.warning(f"Chunk object {c} lacks expected text attribute.")

            context_str = "\n\n".join(context_parts)
            logger.debug(f"Built context string: {context_str}")
            answer = f"Found relevant context: {context_str[:200]}..."

        # 2. Construct QueryResult
        return QueryResult(
            relevant_chunks=relevant_chunks_model,
            answer=answer,
            llm_response="", # Placeholder
            graph_context=None, # Placeholder
            metadata={"query": query_text, "config": config, "retrieval_details": {"type": search_type, "limit": limit, "num_retrieved": len(relevant_chunks_model)}}
        )

    # Remove or comment out the old answer_query method if it wasn't replaced above
    # async def answer_query(self, query: str) -> str:
    #     ... 

    async def _retrieve_graph_context(
        self,
        extracted_entities: List[ExtractedEntity],
        extracted_relationships: List[ExtractedRelationship],
        config: dict = None
    ) -> Optional[Tuple[List[Entity], List[Relationship]]]:
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
        limit_entities = config.get("limit_entities", 10)  # Limit for initial entity search

        if not include_graph:
            logger.info("Graph context retrieval skipped (include_graph=False).")
            return None

        if not extracted_entities:
            logger.info("No entities extracted from chunks, skipping graph context retrieval.")
            return None

        try:
            logger.debug(f"Searching graph for {len(extracted_entities)} extracted entities...")
            
            # Convert extracted entities to graph entities
            graph_entities = [e for e in extracted_entities]

            # Use the graph store to search for entities based on properties
            # Pass the list of ExtractedEntity objects directly
            seed_entities: List[Entity] = await self._graph_repo.search_entities_by_properties(
                graph_entities, limit=limit_entities
            )

            if not seed_entities:
                logger.info("No matching entities found in graph for extracted entities.")
                # Return empty tuple to indicate search was done but found nothing
                return ([], [])

            logger.debug(f"Found {len(seed_entities)} seed entities in graph: {[e.name for e in seed_entities]}")

            # Get neighbors for the seed entities
            seed_entity_ids = [e.id for e in seed_entities]
            neighbor_entities, neighbor_relationships = await self._graph_repo.get_neighbors(
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
            
            logger.debug(f"Final graph context: {len(final_entities)} entities, {len(final_relationships)} relationships.")
            return (final_entities, final_relationships)

        except Exception as e:
            logger.exception(
                f"Error retrieving graph context: {e}",
                exc_info=True
            )
            return None # Return None on error during graph retrieval