from graph_rag.core.interfaces import (
    DocumentProcessor, EntityExtractor, KnowledgeGraphBuilder,
    VectorSearcher, KeywordSearcher, GraphSearcher, GraphRAGEngine,
    DocumentData, ChunkData, SearchResultData, EmbeddingService,
    ExtractionResult, ExtractedEntity, ExtractedRelationship
)
from typing import List, Dict, Any, AsyncGenerator, Optional, Tuple
import logging
import uuid
import asyncio # For potential concurrent processing
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
import re # Import regex for simple entity finding

from graph_rag.models import Document, Chunk, Entity, Relationship, ProcessedDocument
from graph_rag.core.graph_store import GraphStore, MockGraphStore # Import Mock for check
from graph_rag.core.vector_store import VectorStore
from graph_rag.core.entity_extractor import EntityExtractor # Import base class
from graph_rag.services.search import SearchService, SearchResult # Import SearchResult model too

logger = logging.getLogger(__name__)

@dataclass
class QueryResult:
    """Represents the result of a query."""
    answer: str
    relevant_chunks: List[Chunk] = field(default_factory=list)
    graph_context: Optional[Tuple[List[Entity], List[Relationship]]] = None # Entities, Relationships
    metadata: Dict[str, Any] = field(default_factory=dict)

class GraphRAGEngine(ABC):
    """Abstract base class for the GraphRAG query engine."""

    @abstractmethod
    def query(self, query_text: str, config: Optional[Dict[str, Any]] = None) -> QueryResult:
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

    def __init__(self, graph_store: GraphStore, vector_store: VectorStore, entity_extractor: EntityExtractor):
        """Requires GraphStore, VectorStore, and EntityExtractor."""
        if not isinstance(graph_store, GraphStore):
            raise TypeError("graph_store must be an instance of GraphStore")
        if not isinstance(vector_store, VectorStore):
            raise TypeError("vector_store must be an instance of VectorStore")
        # if not isinstance(entity_extractor, EntityExtractor):
        #     raise TypeError("entity_extractor must be an instance of EntityExtractor")
            
        self._graph_store = graph_store
        self._vector_store = vector_store
        self._entity_extractor = entity_extractor # Store the extractor
        logger.info(f"SimpleGraphRAGEngine initialized with GraphStore: {type(graph_store).__name__}, VectorStore: {type(vector_store).__name__}, EntityExtractor: {type(entity_extractor).__name__}")

    async def _extract_entities_from_chunks(self, chunks: List[Chunk]) -> List[Entity]:
        """Extracts entities from a list of chunks using the configured extractor."""
        if not chunks:
            return []
        # Combine text from chunks. Decide if extractor works better on 
        # a larger block of text or internally processes it appropriately.
        # Alternatively, could process chunk by chunk, but might miss cross-chunk entities.
        combined_text = " ".join([c.text for c in chunks])
        # Create a dummy document ID for extraction purposes
        temp_doc_id = f"query-chunks-{hash(combined_text)}"
        # Assuming Document model takes content, not text
        # temp_doc = Document(id=temp_doc_id, text=combined_text, chunks=chunks) <-- Incorrect if Document uses content
        # Assuming graph_rag.models.Document requires content
        temp_doc = Document(id=temp_doc_id, content=combined_text, chunks=chunks) # Pass chunks if extractor uses them
        
        try:
            # Use the injected entity extractor
            # The extractor expects a Document and returns ProcessedDocument
            # Await the async call
            processed_doc = await self._entity_extractor.extract(temp_doc)
            if processed_doc: # Check if result is not None
                logger.info(f"Entity Extractor found {len(processed_doc.entities)} entities from combined text of {len(chunks)} chunks.")
                # Return the list of Entity objects
                return processed_doc.entities
            else:
                logger.warning("Entity extractor returned None.")
                return []
        except Exception as e:
            logger.error(f"Entity extraction during query failed: {e}", exc_info=True)
            return [] # Return empty list on failure
        
    def _find_entities_in_graph_by_properties(self, entities_from_extractor: List[Entity]) -> List[Entity]:
        """Looks up entities from the extractor in the graph store using their properties.
        
        Uses name and type for lookup. Requires the GraphStore to have 
        search_entities_by_properties implemented and potentially indexed properties.
        """
        if not entities_from_extractor:
            return []
            
        logger.debug(f"Attempting to find {len(entities_from_extractor)} entities in graph by properties (name, type)...")
        found_graph_entities = []
        processed_extractor_entities = set() # Avoid searching for the same name/type combo multiple times

        for entity in entities_from_extractor:
            search_key = (entity.name, entity.type)
            if not entity.name or not entity.type or search_key in processed_extractor_entities:
                continue # Skip if missing key info or already searched
                
            processed_extractor_entities.add(search_key)
            search_props = {"name": entity.name, "type": entity.type}
            
            try:
                # Use the graph store's property search method
                # Limit to 1 assuming name+type is reasonably unique, adjust if needed
                results = self._graph_store.search_entities_by_properties(search_props, limit=1)
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
        
    def _get_graph_context(self, entities: List[Entity]) -> Tuple[List[Entity], List[Relationship]]:
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
                neighbors, relationships = self._graph_store.get_neighbors(current_entity.id)
                logger.debug(f"Found {len(neighbors)} neighbors and {len(relationships)} relationships for {current_entity.id}")
                
                for neighbor in neighbors:
                    if neighbor.id not in all_neighbor_entities and len(all_neighbor_entities) < max_entities:
                         all_neighbor_entities[neighbor.id] = neighbor
                         # If the neighbor hasn't been expanded yet, add it to the queue
                         if neighbor.id not in processed_entity_ids:
                             entities_to_expand.append(neighbor)
                             processed_entity_ids.add(neighbor.id)
                             
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
        """Processes a query using vector search and graph context retrieval."""
        logger.info(f"Received query: '{query_text}' with config: {config}")
        config = config or {}
        k = config.get("k", 3)
        include_graph_context = config.get("include_graph", True)
        
        final_entities: List[Entity] = []
        final_relationships: List[Relationship] = []
        graph_context_tuple: Optional[Tuple[List[Entity], List[Relationship]]] = None
        
        try:
            # 1. Vector Search
            logger.debug(f"Performing vector search for: '{query_text}' (k={k})")
            relevant_chunks = self._vector_store.search(query_text, k=k)
            if not relevant_chunks:
                logger.warning(f"Vector search returned no relevant chunks for query: '{query_text}'")
                return QueryResult(answer="Could not find relevant information for your query.", metadata={"query": query_text, "config": config})
                
            logger.info(f"Found {len(relevant_chunks)} relevant chunks via vector search.")

            # 2. Graph Retrieval (if requested)
            if include_graph_context:
                logger.debug("Attempting to retrieve graph context...")
                # a. Extract entities from chunks using the configured EntityExtractor
                extracted_entities = await self._extract_entities_from_chunks(relevant_chunks)
                
                if extracted_entities:
                    # b. Find these entities in the graph using properties (name, type)
                    seed_entities = self._find_entities_in_graph_by_properties(extracted_entities)
                    
                    if seed_entities:
                        # c. Get neighborhood graph context for seed entities found in graph
                        final_entities, final_relationships = self._get_graph_context(seed_entities)
                        graph_context_tuple = (final_entities, final_relationships)
                        logger.info(f"Retrieved graph context with {len(final_entities)} entities and {len(final_relationships)} relationships.")
                    else:
                        logger.info(f"No matching seed entities found in graph using property search.")
                else:
                     logger.info("No entities extracted from chunks for graph lookup.")
            else:
                 logger.info("Graph context retrieval skipped by config.")

            # 3. Synthesize Answer (Placeholder - Needs integration with an LLM)
            # For now, combine chunk text and mention graph context if available
            context_str = " ".join([c.text for c in relevant_chunks])
            answer = f"Based on retrieved text: {context_str[:300]}..." 
            if graph_context_tuple:
                 graph_entities, graph_rels = graph_context_tuple
                 if graph_entities:
                     entity_names = [e.name for e in graph_entities[:5]] # Show first 5
                     answer += f" | Graph context includes entities like: {', '.join(entity_names)}{'...' if len(graph_entities) > 5 else ''}." 
                     if graph_rels:
                         answer += f" Found {len(graph_rels)} relationships connecting them."
                 else:
                     answer += " | No specific graph context found for related entities."
            else:
                 answer += " | Graph context was not retrieved or was empty."
                 
            logger.info("Synthesized basic answer.")

            return QueryResult(
                answer=answer,
                relevant_chunks=relevant_chunks,
                graph_context=graph_context_tuple,
                metadata={"query": query_text, "config": config, "vector_k": k, "used_graph": include_graph_context}
            )

        except Exception as e:
            logger.error(f"Error processing query '{query_text}': {e}", exc_info=True)
            # Provide a safe error response
            return QueryResult(answer=f"An error occurred while processing your query. Please check logs.", metadata={"query": query_text, "config": config, "error": str(e)})

class GraphRAGEngine(GraphRAGEngine):
    """Orchestrates document processing, graph building, and retrieval."""
    
    def __init__(
        self,
        document_processor: DocumentProcessor,
        entity_extractor: EntityExtractor,
        kg_builder: KnowledgeGraphBuilder,
        embedding_service: EmbeddingService,
        search_service: SearchService # Add SearchService
    ):
        self.document_processor = document_processor
        self.entity_extractor = entity_extractor
        self.kg_builder = kg_builder
        self.embedding_service = embedding_service
        self.search_service = search_service
        logger.info("GraphRAGEngine initialized with core components and SearchService.")
        
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

    async def answer_query(self, query: str) -> str:
        """Retrieve context and generate an answer (Requires LLM integration - Placeholder)."""
        logger.info(f"Answering query: '{query}'")
        # 1. Retrieve context (default to vector search)
        context_results = await self.retrieve_context(query, search_type='vector', limit=5)
        if not context_results:
            return "Could not find relevant information to answer the query."
        
        # 2. Format context for LLM
        context_text = "\n".join([f"Chunk {i+1}: {result.content}" for i, result in enumerate(context_results)])
        
        # 3. Call LLM (Placeholder)
        logger.warning("LLM integration not implemented. Returning context summary.")
        # llm_service = load_llm() # Get LLM service instance
        # answer = await llm_service.generate_answer(query, context_text)
        answer = f"Found {len(context_results)} relevant chunks. Context summary: {context_text[:200]}..." # Placeholder answer
        
        return answer 