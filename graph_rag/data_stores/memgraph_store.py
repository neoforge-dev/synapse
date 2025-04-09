import logging
from typing import List, Dict, Any, Optional, Tuple, AsyncGenerator
import asyncio
from datetime import datetime
import json

from neo4j import AsyncGraphDatabase, AsyncDriver, exceptions as neo4j_exceptions
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from graph_rag.data_stores.graph_store import GraphStore # Import the interface
from graph_rag.config.settings import Settings # Correct import for the class
from graph_rag.core.interfaces import ( # Import searcher interfaces
    VectorSearcher, KeywordSearcher, GraphSearcher, 
    SearchResultData, ChunkData, DocumentData
)

logger = logging.getLogger(__name__)

# Define retry strategy for transient errors
_RETRY_EXCEPTIONS = (
    neo4j_exceptions.ServiceUnavailable,
    neo4j_exceptions.SessionExpired,
    neo4j_exceptions.TransientError,
    TimeoutError,
    OSError, # Catch potential DNS/network issues
)

class MemgraphStore(GraphStore, VectorSearcher, KeywordSearcher): # Implement searcher interfaces
    """Memgraph implementation of the GraphStore interface using the neo4j driver.
       Also implements VectorSearcher and KeywordSearcher interfaces.
    """

    # Remove gqlalchemy specific attributes
    # _instance: Optional[Memgraph] = None 
    _settings: Settings # Store settings used for initialization
    _driver: Optional[AsyncDriver] = None
    _auth: Optional[Tuple[str, str]] = None
    _retry_decorator: Any # For tenacity retry

    def __init__(self, settings: Settings):
        if not isinstance(settings, Settings):
            raise TypeError("Expected Settings object for MemgraphStore initialization.")
        self._settings = settings
        # Initialize driver to None, connect() must be called explicitly
        self._driver = None 
        self._auth = (
            (self._settings.MEMGRAPH_USERNAME, self._settings.MEMGRAPH_PASSWORD) 
            if self._settings.MEMGRAPH_USERNAME and self._settings.MEMGRAPH_PASSWORD 
            else None
        )
        # Configure retry decorator using settings
        self._retry_decorator = retry(
            stop=stop_after_attempt(self._settings.MEMGRAPH_RETRY_ATTEMPTS),
            wait=wait_exponential(multiplier=self._settings.MEMGRAPH_RETRY_WAIT_SECONDS, min=1, max=10), # Example exponential backoff
            retry=retry_if_exception_type(_RETRY_EXCEPTIONS),
            before_sleep=lambda retry_state: logger.warning(
                f"Retrying connection/query due to {retry_state.outcome.exception()}, attempt {retry_state.attempt_number}..."
            )
        )
        logger.info(f"MemgraphStore configured for URI: {self._settings.get_memgraph_uri()}")

    # Remove gqlalchemy specific methods
    # @classmethod
    # def get_instance(cls, settings: Settings) -> Memgraph: ...
    # def _connect(self) -> Memgraph: ...

    async def connect(self) -> None:
        """Establishes and verifies the connection driver using neo4j driver."""
        if self._driver is not None:
            logger.debug("Driver already initialized.")
            return
            
        uri = self._settings.get_memgraph_uri()
        logger.info(f"Attempting to connect to Memgraph at {uri} using neo4j driver...")
        
        # Apply retry logic to the connection attempt itself
        @self._retry_decorator
        async def _attempt_connection():
            try:
                driver = AsyncGraphDatabase.driver(
                    uri,
                    auth=self._auth,
                    max_connection_pool_size=self._settings.MEMGRAPH_MAX_POOL_SIZE,
                    connection_timeout=self._settings.MEMGRAPH_CONNECTION_TIMEOUT
                    # Add other relevant neo4j driver options if needed
                )
                # Verify connectivity
                await driver.verify_connectivity()
                logger.info("Successfully connected to Memgraph and verified connectivity via neo4j driver.")
                return driver
            except neo4j_exceptions.AuthError as e:
                 logger.error(f"Memgraph authentication failed for user '{self._settings.MEMGRAPH_USERNAME}': {e}")
                 raise # Re-raise auth errors immediately, no retry
            except Exception as e:
                 logger.error(f"Failed to connect to Memgraph at {uri}: {e}", exc_info=True)
                 raise # Re-raise other connection errors for retry decorator to handle

        try:
            self._driver = await _attempt_connection()
        except Exception as e:
            logger.error(f"Could not connect to Memgraph via neo4j driver after retries: {e}")
            self._driver = None # Ensure driver is None on final failure
            # Re-raise the final exception to signal connection failure
            raise ConnectionError(f"Failed to connect to Memgraph after retries: {e}") from e


    async def close(self) -> None:
        """Closes the database driver connection."""
        if self._driver:
            logger.info("Closing Memgraph neo4j driver connection...")
            await self._driver.close()
            self._driver = None
            logger.info("Memgraph neo4j driver closed.")
            
    def _get_driver(self) -> AsyncDriver:
         """Ensures the driver is initialized."""
         if self._driver is None:
             # This should ideally not happen if connect() is called appropriately
             logger.error("Memgraph driver accessed before connect() was called or after close().")
             raise ConnectionError("Memgraph driver is not initialized. Call connect() first.")
         return self._driver

    # Decorate execute methods with retry logic
    @property
    def execute_read_with_retry(self):
        # Ensure retry decorator is applied correctly
        async def decorated_read(*args, **kwargs):
            return await self.execute_read(*args, **kwargs)
        return self._retry_decorator(decorated_read)
        
    @property
    def execute_write_with_retry(self):
         # Ensure retry decorator is applied correctly
        async def decorated_write(*args, **kwargs):
            return await self.execute_write(*args, **kwargs)
        return self._retry_decorator(decorated_write)

    async def execute_read(self, query: str, parameters: Optional[Dict[str, Any]] = None) -> List[Any]:
        """Executes a read query within an async session and transaction."""
        driver = self._get_driver()
        records = []
        session = None # Ensure session is defined for finally block
        try:
            session = driver.session()
            result = await session.execute_read(
                lambda tx: tx.run(query, parameters).data() # Use execute_read for managed transaction
            )
            records = result # result is already the list of dicts
        except Exception as e:
            logger.error(f"Read query failed: {query} | Params: {parameters} | Error: {e}", exc_info=True)
            raise # Re-raise after logging
        finally:
            if session:
                await session.close()
        return records

    async def execute_write(self, query: str, parameters: Optional[Dict[str, Any]] = None) -> Any:
        """Executes a write query within an async session and transaction."""
        driver = self._get_driver()
        summary = None
        session = None # Ensure session is defined for finally block
        try:
            session = driver.session()
            result = await session.execute_write(
                 lambda tx: tx.run(query, parameters).consume() # Consume to ensure execution
            )
            summary = result # Return summary for potential info
        except Exception as e:
            logger.error(f"Write query failed: {query} | Params: {parameters} | Error: {e}", exc_info=True)
            raise # Re-raise after logging
        finally:
            if session:
                await session.close()
        return summary

    # --- Interface Implementation --- 

    async def add_node(self, label: str, properties: Dict[str, Any]) -> str:
        """Adds or merges node using MERGE based on 'id' property."""
        if "id" not in properties:
            raise ValueError("Node properties must include an 'id' for merging.")
            
        # Escape label properly if needed, though parameters usually handle this.
        # For safety with dynamic labels, basic alphanumeric check or proper escaping needed.
        # Assuming label is safe here.
        query = f"""
        MERGE (n:{label} {{id: $props.id}})
        ON CREATE SET n = $props
        ON MATCH SET n += $props_on_match
        RETURN n.id as id
        """
        # Ensure we don't overwrite the ID on match
        props_on_match = {k: v for k, v in properties.items() if k != 'id'}
        params = {"props": properties, "props_on_match": props_on_match}
        
        try:
             # Use the retry-wrapped version
             # Assuming execute_write returns summary, need to adapt if it returns results directly
             # For MERGE returning ID, maybe use execute_read if write transaction isn't strictly needed?
             # Sticking to write for MERGE semantics.
             # We need the result, so can't just consume(). Let's run directly.
             driver = self._get_driver()
             async with driver.session() as session:
                 result = await session.run(query, parameters=params)
                 record = await result.single()
                 if record and record["id"]:
                     return record["id"]
                 else:
                     # This case should be unlikely if MERGE succeeds
                     logger.error(f"Failed to get ID after merging node with id {properties['id']}")
                     raise RuntimeError("Node ID retrieval failed after MERGE.")
        except Exception as e:
             logger.error(f"Failed to add/merge node {properties.get('id')}: {e}", exc_info=True)
             raise

    async def add_relationship(
        self, 
        source_node_id: str, 
        target_node_id: str, 
        rel_type: str, 
        properties: Optional[Dict[str, Any]] = None
    ) -> None:
        """Adds relationship using MERGE."""
        # Assume labels aren't needed for matching if ID is unique
        query = f"""
        MATCH (a {{id: $source_id}}), (b {{id: $target_id}})
        MERGE (a)-[r:{rel_type}]->(b)
        ON CREATE SET r = $props
        ON MATCH SET r += $props
        """
        params = {
            "source_id": source_node_id,
            "target_id": target_node_id,
            "props": properties or {}
        }
        await self.execute_write_with_retry(query, params)

    async def get_node_by_id(self, node_id: str) -> Optional[Dict[str, Any]]:
        """Retrieves node properties by ID."""
        query = "MATCH (n {id: $node_id}) RETURN properties(n) as props"
        params = {"node_id": node_id}
        result_data = await self.execute_read_with_retry(query, params)
        if result_data:
            return result_data[0].get("props")
        return None

    async def query_subgraph(
        self, 
        start_node_id: str, 
        max_depth: int = 1,
        relationship_types: Optional[List[str]] = None
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """Uses variable-length paths to get subgraph nodes and relationships."""
        rel_pattern = "*" # Default: match all relationship types
        if relationship_types:
            # Format: :REL1|:REL2...
            rel_pattern = f"*:[{'|'.join(relationship_types)}]" 
            
        # Query to get nodes and relationships within depth
        # Uses APOC path expander for potentially better control/performance if available
        # Falling back to variable path for simplicity without APOC assumption
        query = f"""
        MATCH path = (startNode {{id: $start_id}})-[{rel_pattern}*1..{max_depth}]-(connectedNode)
        WITH COLLECT(DISTINCT startNode) + COLLECT(DISTINCT connectedNode) as nodes_list,
             COLLECT(DISTINCT relationships(path)) as rels_nested_list
        UNWIND nodes_list as n
        WITH COLLECT(DISTINCT n) as unique_nodes, rels_nested_list
        UNWIND rels_nested_list as rels_in_path
        UNWIND rels_in_path as r 
        WITH unique_nodes, COLLECT(DISTINCT r) as unique_rels
        RETURN 
            [node in unique_nodes | properties(node)] as nodes,
            [rel in unique_rels | {{ source: startNode(rel).id, target: endNode(rel).id, type: type(rel), properties: properties(rel) }}] as relationships
        """
        params = {"start_id": start_node_id}
        
        result_data = await self.execute_read_with_retry(query, params)
        
        if not result_data:
            return ([], [])
            
        # Result should be a single record containing nodes and relationships
        nodes = result_data[0].get("nodes", [])
        relationships = result_data[0].get("relationships", [])
        return (nodes, relationships)

    async def detect_communities(
        self, 
        algorithm: str = "louvain", 
        write_property: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Runs community detection using MAGE procedures."""
        # Requires MAGE `community_detection` module
        # Example uses Louvain, adjust CALL based on desired algorithm
        if algorithm.lower() != "louvain":
             logger.warning(f"Only 'louvain' community detection algorithm currently supported by this method.")
             raise NotImplementedError(f"Algorithm '{algorithm}' not implemented.")
        
        # Determine if writing back to the graph
        write_clause = f"write: true, writeProperty: '{write_property}'" if write_property else "write: false"
        
        query = f"""
        CALL community_detection.louvain() YIELD node, community_id
        RETURN properties(node) as node_props, community_id
        """
        # Note: The actual CALL might need parameters for weights, iterations etc.
        # Example CALL might be: CALL community_detection.louvain(null, null, {{ {write_clause} }})
        # Sticking to simpler call for now.
        
        results = await self.execute_read_with_retry(query)
        # Format results
        nodes_with_communities = [
            {**record["node_props"], "community_id": record["community_id"]}
            for record in results
        ]
        if write_property:
             logger.info(f"Community detection ({algorithm}) complete. Community IDs written to property '{write_property}'.")
        else:
             logger.info(f"Community detection ({algorithm}) complete. Returning nodes with community IDs.")
        return nodes_with_communities

    async def apply_schema_constraints(self) -> None:
        """Applies uniqueness constraints based on 'id' property."""
        logger.info("Applying schema constraints...")
        # Example: Ensure all nodes with an 'id' property have unique IDs
        # This constraint might be too broad; refine based on actual node types
        # query_unique_id = "CREATE CONSTRAINT IF NOT EXISTS FOR (n) REQUIRE n.id IS UNIQUE"
        
        # More specific constraints are usually better:
        queries = [
            "CREATE CONSTRAINT unique_document_id IF NOT EXISTS FOR (d:Document) REQUIRE d.id IS UNIQUE",
            "CREATE CONSTRAINT unique_chunk_id IF NOT EXISTS FOR (c:Chunk) REQUIRE c.id IS UNIQUE",
            # Add constraints for entity types if needed
            # "CREATE CONSTRAINT unique_person_id IF NOT EXISTS FOR (p:Person) REQUIRE p.id IS UNIQUE",
            # "CREATE CONSTRAINT unique_org_id IF NOT EXISTS FOR (o:Organization) REQUIRE o.id IS UNIQUE",
        ]
        
        for query in queries:
            try:
                await self.execute_write_with_retry(query)
                logger.info(f"Applied constraint: {query.split(' IF NOT EXISTS')[0]}") # Log cleaned query
            except Exception as e:
                # Catch potential errors if constraints already exist or other issues
                logger.error(f"Failed to apply constraint: {query}. Error: {e}", exc_info=True)
                # Decide if this is critical; for now, log and continue
        logger.info("Schema constraint application finished.") 

    # --- Searcher Interface Implementations (Modified for Streaming) --- 

    async def search_similar_chunks(self, query_vector: List[float], limit: int = 10) -> AsyncGenerator[SearchResultData, None]: # Return AsyncGenerator
        """Search for chunks using cosine similarity via MAGE, yielding results."""
        similarity_threshold = self._settings.VECTOR_SEARCH_SIMILARITY_THRESHOLD
        logger.debug(f"Performing vector search with threshold: {similarity_threshold}, limit: {limit}")
        
        cypher_query = f"""
        MATCH (c:Chunk)
        WHERE c.embedding IS NOT NULL
        WITH c, node_similarity.cosine(c.embedding, $query_vector) AS similarity
        WHERE similarity > $threshold
        OPTIONAL MATCH (c)<-[:CONTAINS]-(d:Document)
        RETURN c, similarity, d
        ORDER BY similarity DESC
        LIMIT $limit
        """
        
        session = None
        try:
            search_params = {
                "query_vector": query_vector, 
                "limit": limit,
                "threshold": similarity_threshold
            }
            driver = self._get_driver()
            session = driver.session()
            result_cursor = await session.run(cypher_query, search_params) # Get cursor
            
            count = 0
            async for record in result_cursor: # Iterate over cursor
                if count >= limit: # Ensure we respect the limit even if DB returns more initially
                    break
                try:
                    chunk_props = record.get("c")
                    doc_props = record.get("d")
                    similarity_score = record.get("similarity")
                    
                    if not chunk_props or similarity_score is None:
                        logger.warning("Skipping vector search result stream item due to missing data.")
                        continue
                        
                    chunk_data = self._map_props_to_chunk_data(chunk_props)
                    document_data = self._map_props_to_document_data(doc_props) if doc_props else None
                    
                    if chunk_data: # Ensure mapping was successful
                         yield SearchResultData(
                             chunk=chunk_data,
                             score=float(similarity_score),
                             document=document_data
                         )
                         count += 1
                    else:
                        logger.warning(f"Failed to map chunk properties during vector search stream: {chunk_props}")

                except Exception as parse_e:
                    logger.error(f"Error parsing record during vector search stream: {parse_e}", exc_info=True)
            logger.debug(f"Vector similarity search stream yielded {count} chunks.")
                    
        except neo4j_exceptions.ClientError as ce:
             error_msg = str(ce)
             if "Unknown function" in error_msg and "node_similarity.cosine" in error_msg:
                 logger.error(f"MAGE procedure node_similarity.cosine not found. Error: {error_msg}", exc_info=True)
                 raise RuntimeError("Vector search dependency (MAGE node_similarity) not found.") from ce
             else:
                 logger.error(f"Database client error during vector search stream: {error_msg}", exc_info=True)
                 raise
        except Exception as e:
            logger.error(f"Unexpected error during vector similarity search stream: {e}", exc_info=True)
            raise
        finally:
            if session:
                await session.close()

    async def search_chunks_by_keyword(self, query: str, limit: int = 10) -> AsyncGenerator[SearchResultData, None]: # Return AsyncGenerator
        """Search for chunks based on keyword matching, yielding results."""
        logger.debug(f"Performing keyword search for '{query}', limit: {limit}")
        cypher_query = f"""
        MATCH (c:Chunk)
        WHERE c.text CONTAINS $query_term // Match on 'text' property
        WITH c, 1.0 AS score 
        OPTIONAL MATCH (c)<-[:CONTAINS]-(d:Document)
        RETURN c, score, d
        LIMIT $limit
        """
        session = None
        try:
            search_params = {"query_term": query, "limit": limit}
            driver = self._get_driver()
            session = driver.session()
            result_cursor = await session.run(cypher_query, search_params)
            
            count = 0
            async for record in result_cursor:
                if count >= limit:
                    break
                try:
                    chunk_props = record.get("c")
                    doc_props = record.get("d")
                    score = record.get("score", 0.0)
                    
                    if not chunk_props:
                        logger.warning("Skipping keyword search result stream item due to missing chunk data.")
                        continue
                        
                    chunk_data = self._map_props_to_chunk_data(chunk_props)
                    document_data = self._map_props_to_document_data(doc_props) if doc_props else None
                    
                    if chunk_data:
                        yield SearchResultData(
                            chunk=chunk_data,
                            score=float(score),
                            document=document_data
                        )
                        count += 1
                    else:
                         logger.warning(f"Failed to map chunk properties during keyword search stream: {chunk_props}")

                except Exception as parse_e:
                    logger.error(f"Error parsing record during keyword search stream for query '{query}': {parse_e}", exc_info=True)

            logger.debug(f"Keyword search stream for '{query}' yielded {count} chunks.")
        except Exception as e:
            logger.error(f"Error executing keyword search stream query '{query}': {e}", exc_info=True)
            raise
        finally:
            if session:
                await session.close() 

    # --- Helper Private Methods for Mapping --- 
    def _map_props_to_document_data(self, node_props: Optional[Dict[str, Any]]) -> Optional[DocumentData]:
        """Helper function to map raw node properties (dict) to DocumentData model."""
        if not node_props:
            return None
        try:
            metadata_str = node_props.get("metadata", "{}")
            metadata = {}
            if isinstance(metadata_str, str):
                try:
                    # TODO: Replace eval with safer json.loads if metadata is stored as JSON string
                    metadata = eval(metadata_str) if metadata_str else {}
                except Exception as eval_e:
                    logger.warning(f"Could not evaluate metadata string for document {node_props.get('id')}: {metadata_str}. Error: {eval_e}")
                    metadata = {}
            elif isinstance(metadata_str, dict):
                metadata = metadata_str # Already a dict
            
            if not isinstance(metadata, dict):
                 logger.warning(f"Parsed metadata for document {node_props.get('id')} is not a dict: {type(metadata)}. Resetting to empty dict.")
                 metadata = {}
                 
            return DocumentData(
                id=node_props["id"],
                content=node_props.get("content", ""), # Handle potential missing content
                metadata=metadata,
                # created_at/updated_at might not be stored directly as properties in this example
                # If they are, parse them here: e.g., datetime.fromisoformat(node_props["created_at"])
            )
        except KeyError as ke:
            logger.error(f"Missing expected key when mapping node properties to DocumentData: {ke} in props {node_props}", exc_info=True)
            return None # Return None on mapping failure
        except Exception as e:
            logger.error(f"Generic error mapping node properties to DocumentData: {e} for props {node_props}", exc_info=True)
            return None # Return None on mapping failure
            
    def _map_props_to_chunk_data(self, node_props: Optional[Dict[str, Any]]) -> Optional[ChunkData]:
        """Helper function to map raw node properties (dict) to ChunkData model."""
        if not node_props:
            return None
        try:
            return ChunkData(
                id=node_props["id"],
                text=node_props.get("text", node_props.get("content", "")), # Allow 'text' or 'content' property
                document_id=node_props["document_id"],
                embedding=node_props.get("embedding"), # Will be None if not present
                 # created_at/updated_at might not be stored directly as properties
            )
        except KeyError as ke:
            logger.error(f"Missing expected key when mapping node properties to ChunkData: {ke} in props {node_props}", exc_info=True)
            return None # Return None on mapping failure
        except Exception as e:
            logger.error(f"Generic error mapping node properties to ChunkData: {e} for props {node_props}", exc_info=True)
            return None # Return None on mapping failure

# Ensure MemgraphStoreError exists if needed, or remove if not used
class MemgraphStoreError(Exception):
    """Custom exception for MemgraphStore errors."""
    pass 