from graph_rag.core.interfaces import (
    DocumentProcessor, EntityExtractor, KnowledgeGraphBuilder,
    VectorSearcher, KeywordSearcher, GraphSearcher, GraphRAGEngine,
    DocumentData, ChunkData, SearchResultData, EmbeddingService
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
        if not isinstance(entity_extractor, EntityExtractor):
            raise TypeError("entity_extractor must be an instance of EntityExtractor")
            
        self._graph_store = graph_store
        self._vector_store = vector_store
        self._entity_extractor = entity_extractor # Store the extractor
        logger.info(f"SimpleGraphRAGEngine initialized with GraphStore: {type(graph_store).__name__}, VectorStore: {type(vector_store).__name__}, EntityExtractor: {type(entity_extractor).__name__}")

    def _extract_entities_from_chunks(self, chunks: List[Chunk]) -> List[Entity]:
        """Extracts entities from a list of chunks using the configured EntityExtractor."""
        # This approach re-processes chunk text. Ideally, entities would be 
        # extracted during ingestion and stored/linked to chunks.
        # For simplicity in this engine, we re-extract here.
        logger.debug(f"Extracting entities from {len(chunks)} chunks using {type(self._entity_extractor).__name__}")
        
        # Combine chunk text for the extractor. This assumes the extractor can handle 
        # a larger block of text or internally processes it appropriately.
        # Alternatively, could process chunk by chunk, but might miss cross-chunk entities.
        combined_text = " ".join([c.text for c in chunks])
        # Create a dummy document ID for extraction purposes
        temp_doc_id = f"query-chunks-{hash(combined_text)}"
        temp_doc = Document(id=temp_doc_id, content=combined_text, chunks=chunks) # Pass chunks if extractor uses them
        
        try:
            # Use the injected entity extractor
            # The extractor expects a Document and returns ProcessedDocument
            processed_doc = self._entity_extractor.extract(temp_doc)
            logger.info(f"Entity Extractor found {len(processed_doc.entities)} entities from combined text of {len(chunks)} chunks.")
            # Return the list of Entity objects
            return processed_doc.entities
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

    def query(self, query_text: str, config: Optional[Dict[str, Any]] = None) -> QueryResult:
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
                extracted_entities = self._extract_entities_from_chunks(relevant_chunks)
                
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
        vector_searcher: VectorSearcher,
        keyword_searcher: KeywordSearcher,
        graph_searcher: GraphSearcher
    ):
        self.document_processor = document_processor
        self.entity_extractor = entity_extractor
        self.kg_builder = kg_builder
        self.embedding_service = embedding_service
        self.vector_searcher = vector_searcher
        self.keyword_searcher = keyword_searcher
        self.graph_searcher = graph_searcher
        logger.info("GraphRAGEngine initialized.")
        
    async def process_and_store_document(self, doc_content: str, metadata: Dict[str, Any]) -> None:
        """Full pipeline: chunk, extract entities, build graph."""
        doc_id = str(uuid.uuid4()) # Generate ID upfront
        doc_data = DocumentData(id=doc_id, content=doc_content, metadata=metadata)
        logger.info(f"Processing document {doc_id}...")
        
        # 1. Add Document Node
        await self.kg_builder.add_document(doc_data)
        
        # 2. Chunk Document
        chunks = await self.document_processor.chunk_document(doc_data)
        if not chunks:
            logger.warning(f"No chunks generated for document {doc_id}. Aborting further processing.")
            return
            
        # 3. Generate Embeddings (concurrently?)
        try:
            chunk_texts = [c.text for c in chunks]
            # Assuming encode handles list input; could parallelize if needed
            embeddings = self.embedding_service.encode(chunk_texts)
            if len(embeddings) == len(chunks):
                for i, chunk in enumerate(chunks):
                    chunk.embedding = embeddings[i]
            else:
                 logger.error(f"Embedding count mismatch for doc {doc_id}. Proceeding without embeddings.")
        except Exception as e:
            logger.error(f"Embedding generation failed for doc {doc_id}: {e}. Proceeding without embeddings.", exc_info=True)
            # Ensure embeddings are None if generation failed
            for chunk in chunks:
                chunk.embedding = None
                
        # 4. Process Chunks: Add to KG, Extract Entities, Link
        # Can potentially run entity extraction in parallel for chunks
        tasks = []
        for chunk in chunks:
            tasks.append(self._process_chunk(chunk))
            
        await asyncio.gather(*tasks)
        logger.info(f"Finished processing document {doc_id}. {len(chunks)} chunks processed.")

    async def _process_chunk(self, chunk: ChunkData) -> None:
        """Process a single chunk: add to KG, extract entities, link."""
        try:
            # 4a. Add Chunk Node (with embedding if available)
            await self.kg_builder.add_chunk(chunk)
            
            # 4b. Extract Entities from Chunk Text
            extraction_result = await self.entity_extractor.extract(chunk.text)
            
            if not extraction_result.entities:
                logger.debug(f"No entities found in chunk {chunk.id}")
                return # Nothing more to do for this chunk
                
            # 4c. Add/Update Entities in KG
            entity_ids = []
            for entity in extraction_result.entities:
                await self.kg_builder.add_entity(entity)
                entity_ids.append(entity.id)
                
            # 4d. Add Relationships (if any were extracted)
            for relationship in extraction_result.relationships:
                await self.kg_builder.add_relationship(relationship)
                
            # 4e. Link Chunk to Entities
            if entity_ids:
                await self.kg_builder.link_chunk_to_entities(chunk.id, entity_ids)
                
        except Exception as e:
            logger.error(f"Failed to process chunk {chunk.id} for document {chunk.document_id}: {e}", exc_info=True)
            # Decide how to handle chunk processing errors (e.g., skip chunk, raise)

    async def retrieve_context(
        self, 
        query: str, 
        search_type: str = 'vector', 
        limit: int = 5
    ) -> List[SearchResultData]:
        """Retrieve relevant context chunks for a query (batch response)."""
        results = []
        async for result in self.stream_context(query, search_type, limit):
            results.append(result)
        return results

    async def stream_context(
        self,
        query: str,
        search_type: str = 'vector',
        limit: int = 5
    ) -> AsyncGenerator[SearchResultData, None]:
        """Retrieve relevant context chunks for a query, yielding results as a stream."""
        logger.info(f"Streaming context for query: '{query}' using search type: {search_type}, limit: {limit}")
        
        # Validate search type first
        if search_type not in ['vector', 'keyword']:
             logger.error(f"Unsupported search_type for streaming: {search_type}")
             raise ValueError(f"Invalid search_type specified: {search_type}")

        if search_type == 'vector':
            try:
                query_vector = self.embedding_service.encode(query)
                if isinstance(query_vector, list):
                    async for result in self.vector_searcher.search_similar_chunks(query_vector, limit):
                        yield result
                else:
                    logger.error("Failed to generate query embedding for vector search stream.")
                    # Yield nothing if embedding fails
                    return
            except Exception as e:
                 logger.error(f"Vector search stream failed: {e}", exc_info=True)
                 # Decide if we should raise or just stop yielding? Raising seems better.
                 raise RuntimeError("Vector search stream encountered an error") from e
                 
        elif search_type == 'keyword':
            try:
                async for result in self.keyword_searcher.search_chunks_by_keyword(query, limit):
                    yield result
            except Exception as e:
                 logger.error(f"Keyword search stream failed: {e}", exc_info=True)
                 raise RuntimeError("Keyword search stream encountered an error") from e

    async def answer_query(self, query: str) -> str:
        """Retrieve context and generate an answer (Requires LLM integration)."""
        logger.warning("answer_query requires LLM integration and is not implemented.")
        # 1. Retrieve context
        # context_chunks = await self.retrieve_context(query)
        # 2. Format context for LLM
        # formatted_context = "\n".join([c.chunk.text for c in context_chunks])
        # 3. Call LLM (placeholder)
        # answer = llm_service.generate(query, formatted_context)
        # return answer
        return "Placeholder: LLM generation not implemented." 