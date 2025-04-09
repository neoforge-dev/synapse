from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any
from datetime import datetime
import logging # Import logging

# Use gqlalchemy for Memgraph interaction
from gqlalchemy import Memgraph, MemgraphConnectionException
from gqlalchemy.models import Node as GqlNode, Relationship as GqlRelationship

from graph_rag.config.settings import settings # Updated import
from graph_rag.core.interfaces import GraphRepository
from graph_rag.domain.models import Document, Chunk, Edge

logger = logging.getLogger(__name__) # Logger for this module

# --- IMPORTANT MAGE Requirement --- 
# The vector similarity search (`search_chunks_by_similarity`) relies on
# Memgraph Advanced Graph Extensions (MAGE), specifically the `node_similarity`
# module being available in the running Memgraph instance.
# Ensure Memgraph is started with MAGE (e.g., use the memgraph/memgraph-platform image).
# ----------------------------------

class GraphRepository(ABC):
    """Abstract base class for graph database operations."""
    
    @abstractmethod
    async def save_document(self, document: Document) -> str:
        """Save a document to the graph database."""
        pass
    
    @abstractmethod
    async def save_chunk(self, chunk: Chunk) -> str:
        """Save a text chunk to the graph database."""
        pass
    
    @abstractmethod
    async def create_relationship(self, edge: Edge) -> str:
        """Create a relationship between nodes."""
        pass
    
    @abstractmethod
    async def get_document(self, document_id: str) -> Optional[Document]:
        """Retrieve a document by ID."""
        pass
    
    @abstractmethod
    async def get_chunks_by_document(self, document_id: str) -> List[Chunk]:
        """Retrieve all chunks for a document."""
        pass

    @abstractmethod
    async def search_chunks_by_content(self, query: str, limit: int = 10) -> List[Chunk]:
        """Search for chunks based on content similarity or keywords."""
        pass

    @abstractmethod
    async def search_chunks_by_similarity(self, query_vector: List[float], limit: int = 10) -> List[tuple[Chunk, float]]:
        """Search for chunks based on vector similarity."""
        pass

    @abstractmethod
    async def delete_document(self, document_id: str) -> bool:
        """Delete a document and its associated chunks. Returns True if deleted, False otherwise."""
        pass

    @abstractmethod
    async def update_document_properties(self, document_id: str, properties_to_update: Dict[str, Any]) -> Optional[Document]:
        """Update specific properties of a document. Returns the updated document or None if not found."""
        pass


class MemgraphRepository(GraphRepository):
    """Memgraph implementation of the graph repository using gqlalchemy."""
    
    # Accept Memgraph instance via constructor for DI
    def __init__(self, memgraph_instance: Memgraph):
        self.memgraph = memgraph_instance
    
    # Note: gqlalchemy save methods are synchronous. 
    # For truly async operations with Memgraph, the official neo4j driver
    # or lower-level async libraries would be needed. 
    # We'll keep the async signature for the interface for now.
    async def save_document(self, document: Document) -> str:
        try:
            # Map domain model to gqlalchemy Node
            node = GqlNode(
                _id=document.id, # Use _id for gqlalchemy
                _labels={"Document"}, # Use labels set
                id=document.id,
                type=document.type,
                content=document.content,
                metadata=str(document.metadata), # Store dicts as strings or use Memgraph JSON type
                created_at=document.created_at.isoformat(),
                updated_at=document.updated_at.isoformat() if document.updated_at else None
            )
            self.memgraph.save_node(node)
            logger.debug(f"Saved document node {document.id}")
            return document.id
        except (MemgraphConnectionException, Exception) as e:
            logger.error(f"Failed to save document {document.id}: {e}", exc_info=True)
            raise # Re-raise exceptions for higher layers to handle
    
    async def save_chunk(self, chunk: Chunk) -> str:
        try:
            node = GqlNode(
                _id=chunk.id,
                _labels={"Chunk"},
                id=chunk.id,
                type=chunk.type,
                content=chunk.content,
                document_id=chunk.document_id,
                embedding=chunk.embedding, # Assumes Memgraph handles list<float>
                created_at=chunk.created_at.isoformat(),
                updated_at=chunk.updated_at.isoformat() if chunk.updated_at else None
            )
            self.memgraph.save_node(node)
            logger.debug(f"Saved chunk node {chunk.id}")
            return chunk.id
        except (MemgraphConnectionException, Exception) as e:
            logger.error(f"Failed to save chunk {chunk.id}: {e}", exc_info=True)
            raise
    
    async def create_relationship(self, edge: Edge) -> str:
        try:
            # gqlalchemy requires source and target nodes to exist
            # Ensure nodes are saved before creating relationships
            source_node = self.memgraph.load_node(GqlNode(_id=edge.source_id))
            target_node = self.memgraph.load_node(GqlNode(_id=edge.target_id))

            if not source_node or not target_node:
                # Log error and raise a more specific exception
                error_msg = f"Source ({edge.source_id}) or Target ({edge.target_id}) node not found for edge {edge.id}"
                logger.error(error_msg)
                raise ValueError(error_msg)

            relationship = GqlRelationship(
                _id=edge.id, 
                _type=edge.type,
                _start_node_id=source_node._id,
                _end_node_id=target_node._id,
                **(edge.properties if edge.properties else {}),
                id=edge.id,
                created_at=edge.created_at.isoformat(),
                updated_at=edge.updated_at.isoformat() if edge.updated_at else None
            )
            self.memgraph.save_relationship(relationship)
            logger.debug(f"Created relationship {edge.id} ({edge.type}) from {edge.source_id} to {edge.target_id}")
            return edge.id
        except (MemgraphConnectionException, ValueError, Exception) as e:
            logger.error(f"Failed to create relationship {edge.id}: {e}", exc_info=True)
            raise
    
    async def get_document(self, document_id: str) -> Optional[Document]:
        query = "MATCH (d:Document {id: $id}) RETURN d"
        try:
            result = self.memgraph.execute_and_fetch(query, parameters={"id": document_id})
            record = next(result, None)
            if not record:
                logger.debug(f"Document {document_id} not found.")
                return None
            
            node_data = record["d"]
            return self._map_node_data_to_document(node_data)
            
        except (MemgraphConnectionException, Exception) as e:
            logger.error(f"Error fetching document {document_id}: {e}", exc_info=True)
            # Don't raise here, return None as per function signature for not found / errors
            return None

    async def get_chunks_by_document(self, document_id: str) -> List[Chunk]:
        query = "MATCH (c:Chunk {document_id: $doc_id}) RETURN c"
        chunks = []
        try:
            result = self.memgraph.execute_and_fetch(query, parameters={"doc_id": document_id})
            for record in result:
                try:
                    node_data = record["c"]
                    chunks.append(self._map_node_data_to_chunk(node_data))
                except Exception as parse_e:
                    logger.error(f"Error parsing chunk node data for document {document_id}: {parse_e}", exc_info=True)
                    # Continue parsing other chunks
        except (MemgraphConnectionException, Exception) as e:
            logger.error(f"Error fetching chunks for document {document_id}: {e}", exc_info=True)
            # Return potentially partial list or empty list on query failure
        
        logger.debug(f"Found {len(chunks)} chunks for document {document_id}")
        return chunks

    async def search_chunks_by_content(self, query: str, limit: int = 10) -> List[Chunk]:
        cypher_query = f"""
        MATCH (c:Chunk)
        WHERE c.content CONTAINS $query_term
        RETURN c
        LIMIT $limit
        """
        chunks = []
        try:
            result = self.memgraph.execute_and_fetch(
                cypher_query, 
                parameters={"query_term": query, "limit": limit}
            )
            for record in result:
                try:
                    node_data = record["c"]
                    chunks.append(self._map_node_data_to_chunk(node_data))
                except Exception as parse_e:
                    logger.error(f"Error parsing chunk node data during content search for query '{query}': {parse_e}", exc_info=True)
        except (MemgraphConnectionException, Exception) as e:
            logger.error(f"Error executing content search query '{query}': {e}", exc_info=True)
        
        logger.debug(f"Content search for '{query}' returned {len(chunks)} chunks.")
        return chunks

    async def search_chunks_by_similarity(self, query_vector: List[float], limit: int = 10) -> List[tuple[Chunk, float]]:
        """Search for chunks using cosine similarity via MAGE node_similarity module."""
        # CRITICAL: Requires Memgraph MAGE node_similarity module.
        similarity_threshold = settings.VECTOR_SEARCH_SIMILARITY_THRESHOLD # Use config
        logger.debug(f"Performing vector search with threshold: {similarity_threshold}")
        
        cypher_query = f"""
        MATCH (c:Chunk)
        WHERE c.embedding IS NOT NULL
        WITH c, node_similarity.cosine(c.embedding, $query_vector) AS similarity // MAGE call
        WHERE similarity > $threshold // Use threshold from config
        RETURN c, similarity
        ORDER BY similarity DESC
        LIMIT $limit
        """
        results_with_scores = []
        try:
            result = self.memgraph.execute_and_fetch(
                cypher_query, 
                parameters={
                    "query_vector": query_vector, 
                    "limit": limit,
                    "threshold": similarity_threshold # Pass threshold as parameter
                }
            )
            for record in result:
                try:
                    node_data = record["c"]
                    similarity_score = record["similarity"]
                    chunk = self._map_node_data_to_chunk(node_data)
                    results_with_scores.append((chunk, float(similarity_score)))
                except Exception as parse_e:
                    logger.error(f"Error parsing chunk or similarity during vector search: {parse_e}", exc_info=True)
        except MemgraphConnectionException as conn_e:
             logger.error(f"Database connection error during vector search: {conn_e}", exc_info=True)
             # Raise a specific connection error or handle as needed
             raise
        except Exception as query_e:
            # Catch potential errors if MAGE procedure doesn't exist or query fails
            error_msg = str(query_e)
            if "Unknown function" in error_msg and "node_similarity.cosine" in error_msg:
                 logger.error(f"MAGE procedure node_similarity.cosine not found. Ensure Memgraph is running with MAGE. Error: {error_msg}", exc_info=True)
                 # Optionally raise a specific custom exception here
                 raise RuntimeError("Vector search dependency (MAGE node_similarity) not found.") from query_e
            else:
                logger.error(f"Error executing vector similarity query: {query_e}", exc_info=True)
                # Raise a generic query error or handle
                raise # Re-raise other query errors
        
        logger.debug(f"Similarity search returned {len(results_with_scores)} chunks.")
        return results_with_scores

    async def delete_document(self, document_id: str) -> bool:
        """Deletes a Document node and all connected Chunk nodes."""
        # This query first finds the document, then finds all chunks directly
        # connected to it via any relationship (e.g., CONTAINS), and deletes both
        # the document and the chunks. DETACH DELETE removes nodes and their relationships.
        cypher_query = """
        MATCH (d:Document {id: $doc_id})
        OPTIONAL MATCH (d)-[*]-(c:Chunk) // Find connected chunks (adjust relationship pattern if needed)
        DETACH DELETE d, c
        RETURN count(d) // Return the count of deleted documents (should be 0 or 1)
        """
        try:
            result = self.memgraph.execute_and_fetch(cypher_query, parameters={"doc_id": document_id})
            # Get the count of deleted documents from the result
            delete_count = result.single()[0] if result else 0 
            
            if delete_count > 0:
                logger.info(f"Successfully deleted document {document_id} and associated chunks.")
                return True
            else:
                logger.warning(f"Attempted to delete document {document_id}, but it was not found.")
                return False
        except MemgraphConnectionException as conn_e:
            logger.error(f"Database connection error deleting document {document_id}: {conn_e}", exc_info=True)
            raise # Re-raise connection errors
        except Exception as e:
            logger.error(f"Error deleting document {document_id}: {e}", exc_info=True)
            # Depending on requirements, could return False or raise an error
            return False # Indicate deletion failed

    async def update_document_properties(self, document_id: str, properties_to_update: Dict[str, Any]) -> Optional[Document]:
        """Updates allowed properties (currently only metadata) for a specific document."""
        if not properties_to_update: 
            logger.warning(f"Attempted update for document {document_id} with no properties. Fetching current state.")
            # Return current document if no properties to update, or should we update updated_at?
            # For now, just return current state.
            return await self.get_document(document_id)
            
        set_clauses = []
        params = {"doc_id": document_id}
        
        # --- Build SET clauses dynamically --- 
        # Only allow metadata update for now for simplicity and safety
        if "metadata" in properties_to_update:
            new_metadata = properties_to_update["metadata"]
            if isinstance(new_metadata, dict): # Basic type check
                # Store metadata as a serialized string
                params["new_metadata"] = str(new_metadata) 
                set_clauses.append("d.metadata = $new_metadata")
            else:
                logger.warning(f"Invalid metadata type provided for document {document_id}. Skipping metadata update.")
                # Optionally raise a ValueError here?
        
        # Always update the updated_at timestamp
        params["updated_at_ts"] = datetime.utcnow().isoformat()
        set_clauses.append("d.updated_at = $updated_at_ts")
        
        if not set_clauses or "d.metadata = $new_metadata" not in set_clauses: # Check if only updated_at is being set
             logger.warning(f"Update called for document {document_id} but only non-updatable or no properties specified.")
             # If only updated_at is being set, decide behavior.
             # Let's proceed to update only timestamp if no valid props were given but update was called.
             if "d.metadata = $new_metadata" not in set_clauses and "metadata" in properties_to_update:
                 # Don't proceed if metadata was provided but invalid
                 logger.error(f"Invalid metadata format for {document_id}. Aborting update.")
                 return await self.get_document(document_id) # Return current state
        
        set_clause_str = ", ".join(set_clauses)
        
        # --- Construct and execute query --- 
        cypher_query = f"""
        MATCH (d:Document {{id: $doc_id}})
        SET {set_clause_str}
        RETURN d
        """
        
        try:
            result = self.memgraph.execute_and_fetch(cypher_query, parameters=params)
            record = next(result, None)
            
            if not record:
                logger.warning(f"Document {document_id} not found for update.")
                return None
                
            node_data = record["d"]
            updated_doc = self._map_node_data_to_document(node_data)
            logger.info(f"Successfully updated properties for document {document_id}")
            return updated_doc
            
        except MemgraphConnectionException as conn_e:
            logger.error(f"Database connection error updating document {document_id}: {conn_e}", exc_info=True)
            raise
        except Exception as e:
            logger.error(f"Error updating document {document_id}: {e}", exc_info=True)
            # Indicate update failed
            return None 

    # --- Helper Private Methods --- 
    def _map_node_data_to_document(self, node_data: dict) -> Document:
        """Helper function to map raw node data (dict) to Document domain model."""
        try:
            # Handle potential eval errors or type issues
            metadata = node_data.get("metadata", "{}")
            if isinstance(metadata, str):
                try:
                    metadata = eval(metadata)
                except: 
                    logger.warning(f"Could not evaluate metadata string for document {node_data.get('id')}: {metadata}")
                    metadata = {}
            if not isinstance(metadata, dict):
                 logger.warning(f"Metadata for document {node_data.get('id')} is not a dict: {metadata}")
                 metadata = {}
                 
            return Document(
                id=node_data["id"],
                type=node_data.get("type", "Document"), 
                content=node_data["content"],
                metadata=metadata,
                created_at=datetime.fromisoformat(node_data["created_at"]),
                updated_at=datetime.fromisoformat(node_data["updated_at"]) if node_data.get("updated_at") else None
            )
        except KeyError as ke:
            logger.error(f"Missing expected key when mapping node data to Document: {ke}", exc_info=True)
            raise # Re-raise as this indicates a data integrity issue
        except Exception as e:
            logger.error(f"Generic error mapping node data to Document: {e}", exc_info=True)
            raise # Re-raise
            
    def _map_node_data_to_chunk(self, node_data: dict) -> Chunk:
        """Helper function to map raw node data (dict) to Chunk domain model."""
        try:
            return Chunk(
                id=node_data["id"],
                type=node_data.get("type", "Chunk"),
                content=node_data["content"],
                document_id=node_data["document_id"],
                embedding=node_data.get("embedding"),
                created_at=datetime.fromisoformat(node_data["created_at"]),
                updated_at=datetime.fromisoformat(node_data["updated_at"]) if node_data.get("updated_at") else None
            )
        except KeyError as ke:
            logger.error(f"Missing expected key when mapping node data to Chunk: {ke}", exc_info=True)
            raise
        except Exception as e:
            logger.error(f"Generic error mapping node data to Chunk: {e}", exc_info=True)
            raise 