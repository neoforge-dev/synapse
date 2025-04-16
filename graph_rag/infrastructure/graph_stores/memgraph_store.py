"""Optimized Memgraph graph store implementation."""

import logging
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timezone
import asyncio
import uuid
import pytest
from pydantic import Field
from pydantic_settings import BaseSettings
import json
from dateutil.parser import isoparse

from neo4j import AsyncGraphDatabase, AsyncDriver
from neo4j.exceptions import Neo4jError, ServiceUnavailable, AuthError
import neo4j.time # Import neo4j.time for type checking
from tenacity import (
    AsyncRetrying,
    stop_after_attempt,
    wait_fixed,
    retry_if_exception_type,
    before_sleep_log,
    retry
)

from graph_rag.core.graph_store import GraphStore
from graph_rag.domain.models import Document, Chunk, Entity, Relationship, Node
from graph_rag.config import get_settings

import mgclient
# Import specific exceptions if needed, or catch the base mgclient.Error
# from mgclient import OperationalError, DatabaseError # Example

from unittest.mock import AsyncMock, MagicMock, patch # Ensure patch is imported

# Initialize settings
settings = get_settings()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Define exceptions to retry on using available mgclient errors
_RETRY_EXCEPTIONS = (mgclient.Error, ConnectionRefusedError, ConnectionError)

def _convert_neo4j_temporal_types(data: Dict[str, Any]) -> Dict[str, Any]:
    """Converts Neo4j temporal types to standard Python types."""
    converted_data = {}
    for key, value in data.items():
        if isinstance(value, (neo4j.time.DateTime, neo4j.time.Date, neo4j.time.Time)):
            converted_data[key] = value.to_native()
        else:
            converted_data[key] = value
    return converted_data

class MemgraphConnectionConfig:
    """Configuration specific to Memgraph connection (extracted from global settings)."""
    def __init__(self, settings_obj):
        # Use the passed settings object
        self.host = settings_obj.MEMGRAPH_HOST
        self.port = settings_obj.MEMGRAPH_PORT
        self.user = settings_obj.MEMGRAPH_USERNAME
        self.password = settings_obj.MEMGRAPH_PASSWORD.get_secret_value() if settings_obj.MEMGRAPH_PASSWORD else None
        self.use_ssl = settings_obj.MEMGRAPH_USE_SSL # Assuming this setting exists
        self.max_retries = settings_obj.MEMGRAPH_MAX_RETRIES
        self.retry_delay = settings_obj.MEMGRAPH_RETRY_WAIT_SECONDS

class MemgraphGraphRepository(GraphStore):
    """Optimized Memgraph implementation of the GraphStore interface."""

    def __init__(self, config: Optional[MemgraphConnectionConfig] = None):
        """Initializes the repository, establishing connection parameters."""
        if config is None:
            self.config = MemgraphConnectionConfig(settings) # Use global settings if no config provided
        else:
            self.config = config
        
        self._connection: Optional[mgclient.Connection] = None # Added connection attribute
        # mgclient uses synchronous connect, connection pooling is handled internally or needs manual management
        # We don't store a persistent driver/connection object here in this sync implementation
        logger.info(f"MemgraphGraphRepository initialized for {self.config.host}:{self.config.port}")

    async def connect(self):
        """Establishes and stores a connection for reuse."""
        # Assume connection is None or needs re-establishing if connect is called
        # Rely on mgclient to raise errors if operations are attempted on a closed connection
        if self._connection is None:
            loop = asyncio.get_running_loop()
            try:
                self._connection = await loop.run_in_executor(None, self._get_connection)
                logger.info("Persistent connection established.")
            except Exception as e:
                logger.error(f"Failed to establish persistent connection: {e}", exc_info=True)
                self._connection = None # Ensure it's None on failure
                raise # Re-raise the connection error

    async def close(self):
        """Closes the stored connection if it exists."""
        # Directly attempt to close if connection exists
        if self._connection:
            loop = asyncio.get_running_loop()
            try:
                await loop.run_in_executor(None, self._connection.close)
                logger.info("Persistent connection closed.")
            except Exception as e:
                logger.error(f"Failed to close persistent connection: {e}", exc_info=True)
            finally:
                self._connection = None

    @retry(stop=stop_after_attempt(settings.MEMGRAPH_MAX_RETRIES), 
           wait=wait_fixed(settings.MEMGRAPH_RETRY_WAIT_SECONDS),
           retry=retry_if_exception_type(_RETRY_EXCEPTIONS),
           reraise=True)
    def _get_connection(self) -> mgclient.Connection:
        """Establishes and returns a new synchronous connection to Memgraph."""
        try:
            logger.debug(f"Attempting to connect to Memgraph at {self.config.host}:{self.config.port}...")
            # Ensure username and password are strings, even if empty, for positional args
            db_user = self.config.user if self.config.user is not None else ""
            db_password = self.config.password if self.config.password is not None else ""
            
            conn = mgclient.Connection(
                host=self.config.host,
                port=self.config.port,
                username=db_user,      # Use sanitized user
                password=db_password,  # Use sanitized password
                # sslmode is keyword-only if supported, or might need specific positioning
                # sslmode=mgclient.SSLMODE.REQUIRE if self.config.use_ssl else mgclient.SSLMODE.DISABLE 
            )
            logger.debug("Connection successful.")
            return conn
        except mgclient.Error as e:
            logger.error(f"Failed to connect to Memgraph: {e}", exc_info=True)
            raise # Re-raise to allow tenacity to handle retries
        except Exception as e:
             logger.error(f"An unexpected error occurred during connection: {e}", exc_info=True)
             raise

    async def execute_query(self, query: str, params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Executes a Cypher query and returns results.
           Uses the existing connection if available, otherwise creates a temporary one.
        """
        loop = asyncio.get_running_loop()
        conn_to_use: Optional[mgclient.Connection] = None
        cursor: Optional[mgclient.Cursor] = None
        is_temporary_connection = False

        try:
            # Use existing connection if available
            if self._connection:
                conn_to_use = self._connection
                logger.debug("Using existing persistent connection for query.")
            else:
                # Create a temporary connection for this query
                conn_to_use = await loop.run_in_executor(None, self._get_connection)
                is_temporary_connection = True
                logger.debug("Created temporary connection for query.")
            
            if not conn_to_use: # Safety check
                 raise ConnectionError("Failed to get a database connection.")

            cursor = conn_to_use.cursor()
            logger.debug(f"Executing query: {query} with params: {params}")
            await loop.run_in_executor(None, cursor.execute, query, params or {})
            
            column_names = [desc.name for desc in cursor.description] if cursor.description else []
            results_raw = await loop.run_in_executor(None, cursor.fetchall)
            dict_results = [dict(zip(column_names, row)) for row in results_raw]
            
            # Restore automatic commit
            await loop.run_in_executor(None, conn_to_use.commit) 
            logger.debug(f"Query executed and committed successfully, {len(dict_results)} results fetched. Temp: {is_temporary_connection}")

            return dict_results
        except (mgclient.Error, ConnectionError) as e:
            logger.error(f"Error executing query: {query} | Params: {params} | Error: {e}", exc_info=True)
            # Only attempt rollback on the connection we actually used
            if conn_to_use:
                try:
                    await loop.run_in_executor(None, conn_to_use.rollback) # Rollback on error
                except Exception as rb_exc:
                     logger.error(f"Failed to rollback transaction: {rb_exc}", exc_info=True)
            raise # Re-raise the original error
        except Exception as e:
            logger.error(f"Unexpected error during query execution: {e}", exc_info=True)
            # Check if conn_to_use is not None before attempting rollback
            if conn_to_use:
                 try:
                    await loop.run_in_executor(None, conn_to_use.rollback)
                 except Exception as rb_exc:
                     logger.error(f"Failed to rollback transaction: {rb_exc}", exc_info=True)
            raise
        finally:
            # Close cursor always
            if cursor:
                 try:
                     await loop.run_in_executor(None, cursor.close) # Close cursor
                 except Exception as c_exc:
                     logger.error(f"Failed to close cursor: {c_exc}", exc_info=True)
            # Only close the connection if it was temporary
            if is_temporary_connection and conn_to_use:
                try:
                     await loop.run_in_executor(None, conn_to_use.close) # Close temporary connection
                     logger.debug("Temporary connection closed.")
                except Exception as conn_exc:
                     logger.error(f"Failed to close temporary connection: {conn_exc}", exc_info=True)

    async def add_document(self, document: Document):
        """Adds a document node to the graph."""
        logger.debug(f"Adding document {document.id}")
        
        # Prepare parameters, ensuring timezone aware datetimes
        created_at_dt = document.created_at or datetime.now(timezone.utc)
        if created_at_dt.tzinfo is None:
            created_at_dt = created_at_dt.replace(tzinfo=timezone.utc)
            
        updated_at_dt = datetime.now(timezone.utc)

        params = {
            "id": document.id,
            "content": document.content,
            "metadata": document.metadata if document.metadata else {}, # Pass metadata as a map parameter
            "created_at": created_at_dt, 
            "updated_at": updated_at_dt 
        }

        # Use individual property assignments in SET clauses
        query = """
        MERGE (d:Document {id: $id})
        ON CREATE SET 
            d.content = $content, 
            d.metadata = $metadata, 
            d.created_at = $created_at, 
            d.updated_at = $updated_at
        ON MATCH SET 
            d.content = $content, 
            d.metadata = $metadata, 
            d.updated_at = $updated_at 
        """
        
        try:
            # Execute query assumes commit happens within or implicitly
            await self.execute_query(query, params)
            logger.info(f"Successfully added/updated document {document.id}")
        except Exception as e:
            logger.error(f"Failed to add document {document.id}: {e}", exc_info=True)
            raise

    async def get_document_by_id(self, document_id: str) -> Optional[Document]:
        """Retrieves a document by its ID."""
        logger.debug(f"Attempting to retrieve document with ID: {document_id}")
        query = (
            "MATCH (d:Document {id: $doc_id}) "
            "RETURN d.id as id, d.content as content, d.metadata as metadata, "
            "d.created_at as created_at, d.updated_at as updated_at"
        )
        params = {"doc_id": document_id}
        try:
            results = await self.execute_query(query, params)
            if results and results[0]:
                doc_data = results[0]
                # Convert datetime strings to datetime objects if necessary
                if isinstance(doc_data.get('created_at'), str):
                    doc_data['created_at'] = isoparse(doc_data['created_at'])
                if isinstance(doc_data.get('updated_at'), str):
                    doc_data['updated_at'] = isoparse(doc_data['updated_at'])

                # Ensure metadata is a dictionary
                metadata = doc_data.get('metadata')
                if isinstance(metadata, str):
                    try:
                        metadata = json.loads(metadata)
                    except json.JSONDecodeError:
                        logger.warning(f"Could not parse metadata for document {document_id}: {metadata}")
                        metadata = {}
                elif not isinstance(metadata, dict):
                    metadata = {}

                document = Document(
                    id=doc_data['id'],
                    content=doc_data.get('content', ''),
                    metadata=metadata,
                    created_at=doc_data.get('created_at'),
                    updated_at=doc_data.get('updated_at'),
                )
                logger.debug(f"Successfully retrieved document: {document_id}")
                return document
            else:
                logger.warning(f"Document not found with ID: {document_id}")
                return None
        except Exception as e:
            logger.error(f"Error retrieving document {document_id}: {e}", exc_info=True)
            return None

    async def add_chunk(self, chunk: Chunk) -> None:
        """Adds a chunk node and links it to its parent document.
           Ensures the parent document exists before creating the chunk.
        """
        logger.debug(f"Attempting to add chunk {chunk.id} for document {chunk.document_id}")
        query = (
            "MATCH (d:Document {id: $doc_id}) "
            "WITH d " # Pass the matched document (or null if no match)
            "WHERE d IS NOT NULL " # Proceed only if document was found
            "MERGE (c:Chunk {id: $chunk_id}) "
            "ON CREATE SET c.id = $chunk_id, c.document_id = $doc_id, c.text = $text, c.embedding = $embedding, c.created_at = $created_at, c.updated_at = $updated_at "
            "ON MATCH SET c.text = $text, c.embedding = $embedding, c.updated_at = $updated_at "
            "MERGE (d)-[:CONTAINS]->(c) "
            "RETURN count(c) > 0 AS chunk_created_or_updated"
        )
        params = {
            "doc_id": chunk.document_id,
            "chunk_id": chunk.id,
            "text": chunk.text,
            "embedding": chunk.embedding,
            "created_at": chunk.created_at or datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
        }
        try:
            results = await self.execute_query(query, params)
            if results and results[0].get('chunk_created_or_updated'):
                logger.info(f"Successfully added/updated chunk {chunk.id} for document {chunk.document_id}")
            else:
                logger.warning(f"Failed to add chunk {chunk.id}: Document {chunk.document_id} not found.")
                raise ValueError(f"Document {chunk.document_id} not found, cannot add chunk {chunk.id}.")
        except Exception as e:
            logger.error(f"Failed to add chunk {chunk.id}: {e}", exc_info=True)
            raise

    async def add_node(self, node: Node):
        """Adds or updates a generic node to the graph using its type as the label."""
        logger.debug(f"Adding/updating node {node.id} ({node.type})")
        # Access properties directly from the Node model instance
        props_to_set = node.properties.copy() if node.properties else {} 
        
        # Add/update timestamps, ensuring timezone awareness
        created_at = node.created_at
        if isinstance(created_at, datetime) and created_at.tzinfo is None:
            created_at = created_at.replace(tzinfo=timezone.utc)
        # Only set created_at on create
        # props_to_set["created_at"] = created_at 

        updated_at = datetime.now(timezone.utc)
        props_to_set["updated_at"] = updated_at # Always set updated_at on match
        
        # Dynamically create/update node with label from node.type
        query = f"""
        MERGE (n:{escape_cypher_string(node.type)} {{id: $id}})
        ON CREATE SET n += $props, n.created_at = $created_at
        ON MATCH SET n += $props, n.updated_at = $updated_at
        RETURN n
        """
        params = {
            "id": node.id, 
            "props": props_to_set,
            "created_at": created_at, # Pass explicitly for ON CREATE
            "updated_at": updated_at  # Pass explicitly for ON MATCH
            }
        try:
            await self.execute_query(query, params)
            logger.info(f"Successfully added/updated node {node.id} with type {node.type}")
        except Exception as e:
            logger.error(f"Failed to add node {node.id}: {e}", exc_info=True)
            raise
            
    async def add_nodes(self, nodes: List[Node]):
        """Adds multiple nodes in a single transaction using UNWIND."""
        if not nodes:
            return
            
        logger.debug(f"Adding/updating {len(nodes)} nodes in bulk.")
        nodes_data = []
        for node in nodes:
            props_to_set = node.properties.copy() if node.properties else {}
            created_at = node.created_at
            if isinstance(created_at, datetime) and created_at.tzinfo is None:
                 created_at = created_at.replace(tzinfo=timezone.utc)
            updated_at = datetime.now(timezone.utc)
            props_to_set["updated_at"] = updated_at
            
            nodes_data.append({
                "id": node.id,
                "type": node.type, # Need type for label
                "props": props_to_set,
                "created_at": created_at,
                "updated_at": updated_at
            })
            
        # Note: This Cypher query assumes all nodes have the same type/label.
        # If nodes can have different types, this needs a more complex approach 
        # (e.g., grouping by type or using APOC).
        # For now, assume a common label or handle error if types differ.
        first_node_type = nodes[0].type
        if not all(n.type == first_node_type for n in nodes):
             logger.error("Bulk add_nodes currently only supports nodes of the same type.")
             # Fallback to individual adds for mixed types
             for node in nodes:
                 await self.add_node(node)
             return

        query = f"""
        UNWIND $nodes as node_data
        MERGE (n:{escape_cypher_string(first_node_type)} {{id: node_data.id}})
        ON CREATE SET n += node_data.props, n.created_at = node_data.created_at
        ON MATCH SET n += node_data.props, n.updated_at = node_data.updated_at
        """
        params = {"nodes": nodes_data}
        try:
            await self.execute_query(query, params)
            logger.info(f"Successfully added/updated {len(nodes)} nodes with type {first_node_type}.")
        except Exception as e:
            logger.error(f"Failed to bulk add nodes: {e}", exc_info=True)
            raise

    async def get_node_by_id(self, node_id: str) -> Optional[Node]:
        """Retrieves a node by its ID, reconstructing the Node model."""
        logger.debug(f"Getting node by ID: {node_id}")
        # Query now returns the node object itself, not just properties
        query = "MATCH (n {id: $id}) RETURN n" 
        params = {"id": node_id}
        try:
            result = await self.execute_query(query, params)
            if not result:
                return None
            
            # Assuming execute_query returns [{'n': <mgclient_node>}]
            node_obj = result[0].get("n") 
            if not node_obj:
                 logger.warning(f"Node object not found in query result for ID {node_id}")
                 return None

            # Extract properties and labels directly from the mgclient.Node object
            # Use node_obj.properties and node_obj.labels
            node_props = node_obj.properties if hasattr(node_obj, 'properties') else {}
            labels = node_obj.labels if hasattr(node_obj, 'labels') else set()
            
            # Find the most specific label (excluding base labels like _Node if any)
            # Convert set to list to access by index, or iterate
            labels_list = list(labels)
            node_type = labels_list[0] if labels_list else "Unknown" # Simple approach
            if len(labels_list) > 1:
                 # Prioritize non-internal labels if needed
                 specific_labels = [l for l in labels_list if not l.startswith('_')]
                 if specific_labels:
                     node_type = specific_labels[0]
            
            # Convert temporal types before creating Node model
            # Apply conversion directly to the extracted properties
            converted_props = _convert_neo4j_temporal_types(node_props) 
            
            # Pop base fields from props to avoid passing them to properties dict
            node_id_prop = converted_props.pop("id", node_id) # Use ID from query param if not in props
            created_at = converted_props.pop("created_at", None)
            updated_at = converted_props.pop("updated_at", None)
            # Name might be top-level or in properties, handle potential inconsistency
            name_prop = converted_props.pop("name", None) 
            if name_prop and "name" not in converted_props:
                converted_props["name"] = name_prop # Put it back if it was only top-level
                
            # Reconstruct the Node object
            return Node(
                id=node_id_prop, 
                type=node_type, 
                properties=converted_props, # Remaining items are node-specific properties
                created_at=created_at,
                updated_at=updated_at
            )
        except Exception as e:
            logger.error(f"Failed to get node by ID {node_id}: {e}", exc_info=True)
            raise
            
    async def search_nodes_by_properties(self, properties: Dict[str, Any], node_type: Optional[str] = None, limit: int = 10) -> List[Node]:
        """Searches for nodes matching given properties, optionally filtering by type."""
        logger.debug(f"Searching nodes by properties: {properties}, type: {node_type}, limit: {limit}")
        
        label_filter = f":{escape_cypher_string(node_type)}" if node_type else ""
        where_clauses = []
        params = {} # Start with empty params
        prop_index = 0
        for key, value in properties.items():
            # Use parameterized props for safety
            param_name = f"prop_{prop_index}"
            where_clauses.append(f"n.`{escape_cypher_string(key)}` = ${param_name}")
            params[param_name] = value
            prop_index += 1
            
        where_clause = " AND ".join(where_clauses) if where_clauses else ""
        if where_clause:
            where_clause = f"WHERE {where_clause}"
            
        # Query returns the node object directly
        query = f"""
        MATCH (n{label_filter}) {where_clause}
        RETURN n
        LIMIT toInteger($limit)
        """
        params["limit"] = limit
        
        nodes = []
        try:
            results = await self.execute_query(query, params)
            for record in results:
                # Extract node object from result dict
                node_obj = record.get("n") 
                if not node_obj:
                    continue

                # Extract properties and labels from node object
                node_props = node_obj.properties if hasattr(node_obj, 'properties') else {}
                labels = node_obj.labels if hasattr(node_obj, 'labels') else set()
                converted_props = _convert_neo4j_temporal_types(node_props)
                
                node_id_prop = converted_props.pop("id", None)
                if not node_id_prop: continue # Skip nodes without ID?
                
                # Determine type
                found_node_type = labels[0] if labels else "Unknown"
                if len(labels) > 1:
                     specific_labels = [l for l in labels if not l.startswith('_')]
                     if specific_labels:
                         found_node_type = specific_labels[0]
                
                created_at = converted_props.pop("created_at", None)
                updated_at = converted_props.pop("updated_at", None)
                name_prop = converted_props.pop("name", None) 
                if name_prop and "name" not in converted_props:
                    converted_props["name"] = name_prop

                nodes.append(Node(
                    id=node_id_prop,
                    type=found_node_type,
                    properties=converted_props,
                    created_at=created_at,
                    updated_at=updated_at
                ))
            return nodes
        except Exception as e:
            logger.error(f"Failed to search nodes by properties: {e}", exc_info=True)
            raise

    async def add_relationship(self, relationship: Relationship):
        """Adds a relationship between two nodes."""
        try:
            # Relationship is an alias for Edge, which has properties field
            props = relationship.properties.copy() if relationship.properties else {}
            # Handle timestamps for the relationship itself
            created_at = relationship.created_at
            if isinstance(created_at, datetime) and created_at.tzinfo is None:
                 created_at = created_at.replace(tzinfo=timezone.utc)
            updated_at = datetime.now(timezone.utc)
            props["updated_at"] = updated_at # Set updated_at on match/create
            
            query = f"""
            MATCH (source {{id: $source_id}}), (target {{id: $target_id}})
            MERGE (source)-[r:{escape_cypher_string(relationship.type)}]->(target)
            ON CREATE SET r += $props, r.created_at = $created_at
            ON MATCH SET r += $props, r.updated_at = $updated_at
            """
            await self.execute_query(
                query,
                {
                    "source_id": relationship.source_id, # Use source_id from Edge model
                    "target_id": relationship.target_id, # Use target_id from Edge model
                    "props": props,
                    "created_at": created_at,
                    "updated_at": props["updated_at"]
                }
            )
            logger.debug(f"Added/Updated relationship: {relationship.source_id} -[{relationship.type}]-> {relationship.target_id}")
        except Exception as e:
            logger.error(f"Failed to add relationship: {e}")
            raise

    async def add_entities_and_relationships(
        self,
        entities: List[Entity],
        relationships: List[Relationship]
    ) -> None:
        """Adds multiple entities and relationships in a single transaction."""
        if not entities and not relationships:
            return

        # Use .model_dump() for Pydantic v2 entities
        entity_params = [
            {
                "id": e.id,
                "type": e.type, # Pass type for label creation
                # Entity model doesn't have properties field directly, get from .model_dump() if needed
                "props": e.model_dump(exclude={'id', 'type', 'created_at', 'updated_at'}, exclude_none=True)
            }
            for e in entities
        ]
        
        query = f"""
        UNWIND $entities AS entity_data
        MERGE (n:{entities[0].type if entities else 'Entity'} {{id: entity_data.id}})
        ON CREATE SET n = entity_data.props, n.created_at = timestamp()
        ON MATCH SET n = entity_data.props, n.updated_at = timestamp()
        """

        if relationships:
            query += """
            WITH n
            UNWIND $relationships AS rel_data
            MATCH (source {{id: rel_data.source_id}}), (target {{id: rel_data.target_id}})
            MERGE (source)-[r:{relationships[0].type}]->(target) # Assuming all rels same type
            ON CREATE SET r = rel_data.props, r.created_at = timestamp()
            ON MATCH SET r = rel_data.props, r.updated_at = timestamp()
            """
            # Use properties field from Edge model
            rel_params = [
                {
                    "source_id": r.source_id,
                    "target_id": r.target_id,
                    "type": r.type, # Pass type for relationship creation
                    "props": r.properties.copy() if r.properties else {}
                }
                for r in relationships
            ]
        else:
            rel_params = []

        # Need to handle potentially different entity types in bulk merge/create
        # This requires a more complex query, potentially using APOC or multiple statements.
        # Simplified approach for now: assuming all entities have the same type or handling error/fallback.
        if entities:
            first_entity_type = entities[0].type
            if not all(e.type == first_entity_type for e in entities):
                 logger.warning("Bulk add_entities_and_relationships processing mixed entity types individually.")
                 # Fallback to individual adds
                 for entity in entities:
                     await self.add_node(entity) # Reuse add_node which handles types
                 entity_query_part = "" # Skip bulk entity query part
            else:
                entity_query_part = f"""
                UNWIND $entities AS entity_data
                MERGE (n:{escape_cypher_string(first_entity_type)} {{id: entity_data.id}})
                ON CREATE SET n = entity_data.props, n.created_at = timestamp()
                ON MATCH SET n += entity_data.props, n.updated_at = timestamp()
                WITH collect(n) as nodes_processed, $relationships as rels
                """ # Added WITH clause to pass relationships
        else:
            entity_query_part = "WITH $relationships as rels\n" # Start with relationships if no entities

        if relationships:
             # Assuming all relationships have the same type for simplicity in MERGE
             first_rel_type = relationships[0].type
             if not all(r.type == first_rel_type for r in relationships):
                 logger.warning("Bulk add_entities_and_relationships processing mixed relationship types individually.")
                 # Fallback for relationships
                 rel_query_part = "" # Skip bulk rel part
                 # Handle entities first if they exist
                 if entity_query_part:
                      await self.execute_query(entity_query_part.replace("WITH collect(n) as nodes_processed, $relationships as rels", ""), {"entities": entity_params})
                 # Add relationships individually
                 for rel in relationships:
                     await self.add_relationship(rel)
                 # Set final query to empty if handled individually
                 query = "" 
             else:
                  rel_query_part = f"""
                  UNWIND rels AS rel_data
                  MATCH (source {{id: rel_data.source_id}}), (target {{id: rel_data.target_id}})
                  MERGE (source)-[r:{escape_cypher_string(first_rel_type)}]->(target)
                  ON CREATE SET r = rel_data.props, r.created_at = timestamp()
                  ON MATCH SET r += rel_data.props, r.updated_at = timestamp()
                  """
             query = entity_query_part + rel_query_part
        else:
            query = entity_query_part.replace(", $relationships as rels","") # Remove rels if no relationships

        if query: # Only execute if query is not empty (not handled individually)
            await self.execute_query(
                query,
                {
                    "entities": entity_params,
                    "relationships": rel_params
                }
            )
        logger.debug(f"Bulk processed {len(entities)} entities and {len(relationships)} relationships")

    async def get_entity_by_id(self, entity_id: str) -> Optional[Entity]:
        """Retrieves a single entity by its unique ID with error handling."""
        try:
            node = await self.get_node_by_id(entity_id)
            if node:
                # Attempt to convert the retrieved Node to an Entity
                try:
                    # Ensure properties is a dict even if None initially
                    node_properties = node.properties if node.properties else {}
                    # Extract name, default to id. Use pop to remove from dict.
                    name = node_properties.pop("name", node.id)
                    # Remaining items in node_properties are metadata
                    entity = Entity(
                        id=node.id,
                        name=name, 
                        type=node.type, # Use the actual type retrieved from the node
                        metadata=node_properties, # Pass remaining properties as metadata
                        created_at=node.created_at,
                        updated_at=node.updated_at
                    )
                    # Optional: Log successful conversion for clarity
                    # logger.debug(f"Successfully converted Node {entity_id} to Entity.")
                    return entity
                except Exception as conversion_error:
                     logger.error(f"Failed to convert retrieved Node {entity_id} to Entity: {conversion_error}", exc_info=True)
                     return None # Return None if conversion fails
            # If node is None initially
            return None
        except Exception as e:
            logger.error(f"Failed to get entity {entity_id}: {e}", exc_info=True)
            raise

    async def get_neighbors(
        self,
        entity_id: str,
        relationship_types: Optional[List[str]] = None,
        direction: str = "both"
    ) -> Tuple[List[Entity], List[Relationship]]:
        """Retrieves direct neighbors of a given entity."""
        # Build relationship pattern
        rel_pattern = ""
        if relationship_types:
            # Escape each type individually before joining
            escaped_types = [escape_cypher_string(rt) for rt in relationship_types]
            rel_types = "|".join(escaped_types)
            rel_pattern = f":`{rel_types}`" # Use backticks for safety with potentially special chars in types
        
        # Build direction pattern
        if direction == "outgoing":
            pattern = f"-[r{rel_pattern}]->"
        elif direction == "incoming":
            pattern = f"<-[r{rel_pattern}]-"
        else:  # both
            pattern = f"-[r{rel_pattern}]-"

        # Query returns the nodes and relationship objects directly
        query = f"""
        MATCH (e {{id: $id}}){pattern}(n)
        RETURN n, r, e
        """
        params = {"id": entity_id}
        
        entities: List[Entity] = []
        relationships: List[Relationship] = []
        processed_node_ids = set()
        processed_rel_ids = set() # Use internal mgclient ID for deduplication during processing

        try:
            # Execute query and get list of dictionaries [{ 'n': node, 'r': rel, 'e': source_node }, ...]
            results = await self.execute_query(query, params)
            
            for record in results:
                # Extract objects from the result dictionary using .get()
                neighbor_node_obj = record.get("n")
                rel_obj = record.get("r")
                source_node_obj = record.get("e")
                
                # Basic validation: ensure all parts are present
                if not all([neighbor_node_obj, rel_obj, source_node_obj]):
                    logger.warning(f"Skipping incomplete neighbor record for entity {entity_id}")
                    continue

                # --- Process Neighbor Node --- 
                neighbor_props = neighbor_node_obj.properties
                neighbor_labels = neighbor_node_obj.labels
                neighbor_id = neighbor_props.get('id') # Get ID from properties

                if neighbor_id and neighbor_id not in processed_node_ids:
                     # Determine type, prioritize specific labels
                     neighbor_type = 'Entity' # Default
                     specific_labels = [l for l in neighbor_labels if not l.startswith('_')]
                     if specific_labels:
                         neighbor_type = specific_labels[0]
                     
                     # Convert temporal types & pop base fields
                     converted_neighbor_props = _convert_neo4j_temporal_types(neighbor_props)
                     created_at = converted_neighbor_props.pop("created_at", None)
                     updated_at = converted_neighbor_props.pop("updated_at", None)
                     # Remove internal id if present in props
                     converted_neighbor_props.pop("id", None) 
                     # Extract name if present, else use ID
                     name = converted_neighbor_props.pop("name", neighbor_id) 
                     
                     # Construct Entity object
                     neighbor_entity = Entity(
                         id=neighbor_id,
                         name=name,
                         type=neighbor_type,
                         metadata=converted_neighbor_props, # Remaining props are metadata
                         created_at=created_at,
                         updated_at=updated_at
                     )
                     entities.append(neighbor_entity)
                     processed_node_ids.add(neighbor_id)
                    
                # --- Process Relationship --- 
                # Use internal id for deduplication during this processing step
                rel_internal_id = rel_obj.id # mgclient uses .id for internal id
                if rel_internal_id not in processed_rel_ids:
                    rel_props = rel_obj.properties
                    converted_rel_props = _convert_neo4j_temporal_types(rel_props)
                    created_at = converted_rel_props.pop("created_at", None)
                    updated_at = converted_rel_props.pop("updated_at", None)
                    rel_type = rel_obj.type
                    
                    # Get start/end node IDs directly from the relationship object
                    actual_source_node_id = rel_obj.start_node.properties.get('id')
                    actual_target_node_id = rel_obj.end_node.properties.get('id')
                    
                    # Validate we have the IDs needed
                    if not actual_source_node_id or not actual_target_node_id:
                        logger.warning(f"Skipping relationship processing due to missing start/end node ID. Rel internal ID: {rel_internal_id}")
                        continue
                        
                    rel_model = Relationship(
                        id=str(uuid.uuid4()), # Generate app-level ID
                        source_id=actual_source_node_id,
                        target_id=actual_target_node_id,
                        type=rel_type,
                        properties=converted_rel_props,
                        created_at=created_at,
                        updated_at=updated_at
                    )
                    relationships.append(rel_model)
                    processed_rel_ids.add(rel_internal_id)
                
        except Exception as e:
            logger.error(f"Failed to get neighbors for entity {entity_id}: {e}", exc_info=True)
            raise # Re-raise after logging
            
        return entities, relationships

    async def search_entities_by_properties(
        self,
        properties: Dict[str, Any],
        limit: Optional[int] = None
    ) -> List[Entity]:
        """Searches for entities matching specific properties."""
        # Reuse search_nodes_by_properties logic
        # We expect Entity nodes to have a label matching their type
        # For now, assume a generic search and then filter/convert
        # A more optimized approach might filter by label in the query if possible
        logger.debug(f"Searching entities by properties: {properties}, limit: {limit}")

        # Parameterize properties for safety
        where_clauses = []
        params = {}
        prop_index = 0
        for key, value in properties.items():
            param_name = f"prop_{prop_index}"
            where_clauses.append(f"n.`{escape_cypher_string(key)}` = ${param_name}")
            params[param_name] = value
            prop_index += 1

        where_clause = " AND ".join(where_clauses) if where_clauses else ""
        if where_clause:
            where_clause = f"WHERE {where_clause}"

        # Query returns the node object directly
        query = f"""
        MATCH (n) {where_clause} 
        RETURN n
        """ # Removed LIMIT here, apply later if needed
        
        if limit:
            query += f" LIMIT $limit"
            params["limit"] = limit

        entities_found = []
        try:
            results = await self.execute_query(query, params)
            for record in results: # Process each record dictionary
                 node_obj = record.get("n") # Extract node object
                 if not node_obj: continue

                 node_props = node_obj.properties if hasattr(node_obj, 'properties') else {}
                 labels = node_obj.labels if hasattr(node_obj, 'labels') else set()
                 converted_data = _convert_neo4j_temporal_types(node_props)
                 entity_id = converted_data.pop('id', None)
                 if not entity_id: continue
                 
                 # Determine type, prioritize specific labels
                 entity_type = 'Entity' # Default
                 specific_labels = [l for l in labels if not l.startswith('_')]
                 if specific_labels:
                     entity_type = specific_labels[0]
                     
                 created_at = converted_data.pop("created_at", None)
                 updated_at = converted_data.pop("updated_at", None)
                 # Extract name if present, else use ID
                 name = converted_data.pop("name", entity_id) 
                 
                 # Remaining properties go into metadata
                 metadata = converted_data
                 
                 entities_found.append(Entity(
                     id=entity_id,
                     name=name,
                     type=entity_type,
                     metadata=metadata,
                     created_at=created_at,
                     updated_at=updated_at
                     ))
        except Exception as e:
             logger.error(f"Failed during entity search: {e}", exc_info=True)
             raise # Re-raise the error
             
        return entities_found

    async def add_entity(self, entity: Entity):
        """Adds or updates an Entity node to the graph."""
        # Reuse the add_node logic, ensuring the type is correctly handled
        # The Entity model already sets type='Entity'
        await self.add_node(entity)

    async def delete_document(self, document_id: str) -> bool:
        """Deletes a document and its associated chunks.
        
        Returns:
            bool: True if the document was found and deleted, False otherwise.
        """
        logger.debug(f"Deleting document {document_id} and its chunks.")
        # Use OPTIONAL MATCH, attempt delete, return explicit boolean based on existence before delete
        query = """
        OPTIONAL MATCH (d:Document {id: $id})
        WITH d 
        DETACH DELETE d
        RETURN d IS NOT NULL AS deleted
        """
        params = {"id": document_id}
        try:
            results = await self.execute_query(query, params)
            # Explicitly handle empty results (no row returned)
            if not results:
                logger.warning(f"Document {document_id} not found, nothing deleted (no result row).")
                status_to_return = False
                logger.debug(f"Repo delete_document returning: {status_to_return}")
                return status_to_return
            # Check if the query returned a result and the 'deleted' flag is True
            if results[0].get('deleted') is True:
                logger.info(f"Successfully deleted document {document_id}.")
                status_to_return = True
                logger.debug(f"Repo delete_document returning: {status_to_return}")
                return status_to_return
            else:
                # Handles document not found (d was null, deleted is false)
                logger.warning(f"Document {document_id} not found, nothing deleted (deleted flag false).")
                status_to_return = False
                logger.debug(f"Repo delete_document returning: {status_to_return}")
                return status_to_return
        except Exception as e:
            logger.error(f"Failed to delete document {document_id}: {e}", exc_info=True)
            raise

    async def __aenter__(self):
        """Context manager entry."""
        await self.execute_query("RETURN 1")
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        pass

    async def get_chunks_by_document_id(self, document_id: str) -> list[Chunk]:
        """Retrieve all chunks linked to a given document by its id."""
        logger.debug(f"Retrieving chunks for document {document_id}")
        query = (
            "MATCH (d:Document {id: $doc_id})-[:CONTAINS]->(c:Chunk) "
            "RETURN c"
        )
        params = {"doc_id": document_id}
        try:
            results = await self.execute_query(query, params)
            chunks = []
            for record in results:
                node_obj = record.get("c")
                if not node_obj:
                    continue
                node_props = node_obj.properties if hasattr(node_obj, 'properties') else {}
                # Convert temporal types if needed
                created_at = node_props.get("created_at")
                updated_at = node_props.get("updated_at")
                # Ensure embedding is a list of floats
                embedding = node_props.get("embedding")
                if embedding is not None and not isinstance(embedding, list):
                    try:
                        embedding = list(embedding)
                    except Exception:
                        embedding = None
                chunk = Chunk(
                    id=node_props.get("id"),
                    text=node_props.get("text", ""),
                    document_id=node_props.get("document_id"),
                    embedding=embedding,
                    created_at=created_at,
                    updated_at=updated_at
                )
                chunks.append(chunk)
            return chunks
        except Exception as e:
            logger.error(f"Failed to retrieve chunks for document {document_id}: {e}", exc_info=True)
            raise

def escape_cypher_string(value: str) -> str:
    """Escapes characters in a string for safe use in Cypher labels/types."""
    # Basic escaping, might need refinement based on Memgraph label rules
    return value.replace("`", "``").replace("\"", "\\\"").replace("'", "\\'")
