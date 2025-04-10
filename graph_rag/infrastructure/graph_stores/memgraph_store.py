"""Optimized Memgraph graph store implementation."""

import logging
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timezone
import asyncio
import uuid

from neo4j import AsyncGraphDatabase, AsyncDriver
from neo4j.exceptions import Neo4jError, ServiceUnavailable, AuthError
import neo4j.time # Import neo4j.time for type checking
from tenacity import (
    AsyncRetrying,
    stop_after_attempt,
    wait_fixed,
    retry_if_exception_type,
    before_sleep_log
)

from graph_rag.core.graph_store import GraphStore
from graph_rag.domain.models import Document, Chunk, Entity, Relationship, Node
from graph_rag.config import settings

logger = logging.getLogger(__name__)

# Define exceptions to retry on
_RETRY_EXCEPTIONS = (ConnectionError, ServiceUnavailable)

def _convert_neo4j_temporal_types(data: Dict[str, Any]) -> Dict[str, Any]:
    """Converts Neo4j temporal types to standard Python types."""
    converted_data = {}
    for key, value in data.items():
        if isinstance(value, (neo4j.time.DateTime, neo4j.time.Date, neo4j.time.Time)):
            converted_data[key] = value.to_native()
        else:
            converted_data[key] = value
    return converted_data

class MemgraphGraphRepository(GraphStore):
    """Optimized Memgraph implementation of the GraphStore interface."""

    def __init__(self, driver: Optional[AsyncDriver] = None):
        """
        Initializes the repository with an optional Neo4j driver instance.
        If no driver is provided, one will be created using settings.
        """
        if driver:
            self._driver = driver
            self._is_connected = True # Assume connected if driver is provided
        else:
            # If no driver is provided, initialize later in connect()
            self._driver = None
            self._is_connected = False
        self.retryer = AsyncRetrying(
            stop=stop_after_attempt(settings.MEMGRAPH_RETRY_ATTEMPTS),
            wait=wait_fixed(settings.MEMGRAPH_RETRY_WAIT_SECONDS),
            retry=retry_if_exception_type((ConnectionError, ServiceUnavailable)),
            before_sleep=before_sleep_log(logger, logging.WARNING, exc_info=True), # Log exceptions before retrying
            reraise=True,
        )
        logger.info("MemgraphGraphRepository initialized.")

    async def connect(self) -> None:
        """Establishes connection to Memgraph if no driver is provided."""
        if self._driver is not None and self._is_connected:
            return

        uri = settings.get_memgraph_uri()
        auth = (
            (settings.MEMGRAPH_USERNAME, settings.MEMGRAPH_PASSWORD)
            if settings.MEMGRAPH_USERNAME and settings.MEMGRAPH_PASSWORD
            else None
        )

        try:
            self._driver = AsyncGraphDatabase.driver(
                uri,
                auth=auth,
                max_connection_pool_size=settings.MEMGRAPH_MAX_POOL_SIZE,
                connection_timeout=settings.MEMGRAPH_CONNECTION_TIMEOUT
            )
            await self._driver.verify_connectivity()
            self._is_connected = True
            logger.info(f"Connected to Memgraph at {uri}")
        except AuthError as e:
            logger.error(f"Authentication failed for Memgraph: {e}")
            raise
        except Exception as e:
            logger.error(f"Failed to connect to Memgraph: {e}")
            self._is_connected = False
            raise

    async def close(self) -> None:
        """Closes the connection driver."""
        if self._driver:
            try:
                await self._driver.close()
                self._driver = None
                self._is_connected = False
                logger.info("Memgraph driver closed.")
            except Exception as e:
                logger.error(f"Error closing Memgraph driver: {e}")
                raise

    @property
    def _get_driver(self) -> AsyncDriver:
        """Ensures driver is initialized and connected."""
        if not self._driver or not self._is_connected:
            raise ConnectionError("Memgraph driver not initialized or not connected. Call connect() first.")
        return self._driver

    async def get_driver(self) -> AsyncDriver:
        """Ensures driver is initialized and connected."""
        if not self._driver or not self._is_connected:
            raise ConnectionError("Memgraph driver not initialized or not connected. Call connect() first.")
        return self._driver

    async def _execute_write_query(self, query: str, parameters: Optional[Dict[str, Any]] = None) -> None:
        """Executes a write query with retry logic and transaction support."""
        async def _task_to_retry():
            driver = await self.get_driver()
            async with driver.session() as session:
                try:
                    await session.run(query, parameters or {})
                except Neo4jError as e:
                    logger.error(f"Write query failed: {e} | Query: {query} | Params: {parameters}")
                    raise
        await self.retryer(_task_to_retry)

    async def _execute_read_query(self, query: str, parameters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Executes a read query with retry logic and transaction support."""
        async def _task_to_retry():
            driver = await self.get_driver()
            async with driver.session() as session:
                try:
                    result = await session.run(query, parameters or {})
                    # Ensure result processing happens within the retry block if needed
                    # Convert records immediately
                    data = [record.data() async for record in result]
                    return data # Return processed data
                except Neo4jError as e:
                    logger.error(f"Read query failed: {e} | Query: {query} | Params: {parameters}")
                    raise
        return await self.retryer(_task_to_retry)

    async def clear_all_data(self) -> None:
        """Deletes all nodes and relationships from the graph."""
        logger.warning("Clearing all data from Memgraph database!")
        await self._execute_write_query("MATCH (n) DETACH DELETE n")
        logger.info("Cleared all data from Memgraph database.")

    async def add_document(self, document: Document):
        """Adds a document node to the graph."""
        logger.debug(f"Adding document {document.id}")
        # Use .model_dump() for Pydantic v2 models
        props = {k: v for k, v in document.model_dump().items() if k not in {"id", "chunks", "type", "properties"}}
        # Ensure basic properties exist, add default or raise if needed
        # 'content' and 'metadata' should be handled by model_dump() if they are fields
        # props["content"] = document.content
        # props["metadata"] = document.metadata
        # Handle potential naive datetime from Pydantic default_factory
        created_at = props.get("created_at", datetime.now(timezone.utc))
        if created_at.tzinfo is None:
            created_at = created_at.replace(tzinfo=timezone.utc)
        props["created_at"] = created_at
        # Updated_at should be set by the database ideally, or handled in model_dump logic
        updated_at = datetime.now(timezone.utc) # Set updated_at on add/update
        props["updated_at"] = updated_at

        # Use MERGE for idempotency
        query = """
        MERGE (d:Document {id: $id})
        ON CREATE SET d += $props, d.created_at = $created_at
        ON MATCH SET d += $props, d.updated_at = $updated_at
        """
        params = {
            "id": document.id, 
            "props": props, 
            "created_at": props["created_at"],
            "updated_at": props["updated_at"]
        }
        try:
            await self._execute_write_query(query, params)
            logger.info(f"Successfully added/updated document {document.id}")
        except Exception as e:
            logger.error(f"Failed to add document {document.id}: {e}", exc_info=True)
            raise

    async def get_document_by_id(self, doc_id: str) -> Optional[Document]:
        """Retrieves a Document node by ID."""
        query = "MATCH (d:Document {id: $id}) RETURN properties(d) as props"
        results = await self._execute_read_query(query, {"id": doc_id})
        if results:
            node_data = results[0]["props"]
            converted_data = _convert_neo4j_temporal_types(node_data)
            # Ensure 'id' is present for model creation
            if 'id' not in converted_data:
                converted_data['id'] = doc_id
            return Document(**converted_data)
        return None

    async def add_chunk(self, chunk: Chunk):
        """Adds a chunk node and links it to its document."""
        logger.debug(f"Adding chunk {chunk.id} for document {chunk.document_id}")
        # Use .model_dump() for Pydantic v2 models
        props = {k: v for k, v in chunk.model_dump().items() if k not in {"id", "document_id", "type", "properties"}}
        # Ensure basic properties exist
        # props["content"] = chunk.content # Use content as per model
        # props["metadata"] = chunk.metadata
        # props["embedding"] = chunk.embedding
        created_at = props.get("created_at", datetime.now(timezone.utc))
        if created_at.tzinfo is None:
            created_at = created_at.replace(tzinfo=timezone.utc)
        props["created_at"] = created_at
        updated_at = datetime.now(timezone.utc) # Set updated_at on add/update
        if updated_at.tzinfo is None:
            updated_at = updated_at.replace(tzinfo=timezone.utc)
        props["updated_at"] = updated_at

        query = """
        MATCH (d:Document {id: $doc_id})
        MERGE (c:Chunk {id: $chunk_id})
        ON CREATE SET c += $props, c.created_at = $created_at
        ON MATCH SET c += $props, c.updated_at = $updated_at
        MERGE (d)-[:CONTAINS]->(c)
        """
        params = {
            "doc_id": chunk.document_id,
            "chunk_id": chunk.id,
            "props": props,
            "created_at": props["created_at"],
            "updated_at": props["updated_at"]
        }
        try:
            await self._execute_write_query(query, params)
            logger.info(f"Successfully added/updated chunk {chunk.id} linked to doc {chunk.document_id}")
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
            await self._execute_write_query(query, params)
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
            await self._execute_write_query(query, params)
            logger.info(f"Successfully added/updated {len(nodes)} nodes with type {first_node_type}.")
        except Exception as e:
            logger.error(f"Failed to bulk add nodes: {e}", exc_info=True)
            raise

    async def get_node_by_id(self, node_id: str) -> Optional[Node]:
        """Retrieves a node by its ID, reconstructing the Node model."""
        logger.debug(f"Getting node by ID: {node_id}")
        query = "MATCH (n {id: $id}) RETURN properties(n) as props, labels(n) as labels"
        params = {"id": node_id}
        try:
            result = await self._execute_read_query(query, params)
            if not result:
                return None
            
            node_props = result[0]["props"]
            labels = result[0]["labels"]
            # Find the most specific label (excluding base labels like _Node if any)
            node_type = labels[0] if labels else "Unknown" # Simple approach
            if len(labels) > 1:
                 # Prioritize non-internal labels if needed
                 specific_labels = [l for l in labels if not l.startswith('_')]
                 if specific_labels:
                     node_type = specific_labels[0]
            
            # Convert temporal types before creating Node model
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
        params = properties.copy()
        
        for key, value in properties.items():
            # Simple equality check for now
            where_clauses.append(f"n.`{key}` = ${key}")
            
        where_clause = " AND ".join(where_clauses) if where_clauses else ""
        if where_clause:
            where_clause = f"WHERE {where_clause}"
            
        query = f"""
        MATCH (n{label_filter}) {where_clause}
        RETURN properties(n) as props, labels(n) as labels
        LIMIT toInteger($limit)
        """
        params["limit"] = limit
        
        nodes = []
        try:
            results = await self._execute_read_query(query, params)
            for record in results:
                node_props = record["props"]
                labels = record["labels"]
                converted_props = _convert_neo4j_temporal_types(node_props)
                
                node_id_prop = converted_props.pop("id", None)
                if not node_id_prop: continue # Skip nodes without ID?
                
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
            await self._execute_write_query(
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
                      await self._execute_write_query(entity_query_part.replace("WITH collect(n) as nodes_processed, $relationships as rels", ""), {"entities": entity_params})
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
            await self._execute_write_query(
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
            rel_types = "|".join(relationship_types)
            rel_pattern = f":{rel_types}"
        
        # Build direction pattern
        if direction == "outgoing":
            pattern = f"-[r{rel_pattern}]->"
        elif direction == "incoming":
            pattern = f"<-[r{rel_pattern}]-"
        else:  # both
            pattern = f"-[r{rel_pattern}]-"

        query = f"""
        MATCH (e {{id: $id}}){pattern}(n)
        RETURN n, r, e
        """
        
        # Execute query but get raw records, not just data()
        records = []
        async def _task_to_retry():
            async with self._get_driver.session() as session:
                try:
                    result = await session.run(query, {"id": entity_id})
                    # Collect raw records
                    nonlocal records
                    records = [record async for record in result]
                except Neo4jError as e:
                    logger.error(f"Read query failed: {e} | Query: {query} | Params: {{'id': entity_id}}")
                    raise
        await self.retryer(_task_to_retry)

        # Process raw records
        entities: List[Entity] = []
        relationships: List[Relationship] = []
        processed_node_ids = set()
        processed_rel_ids = set()
        
        for record in records: # Iterate through neo4j.ResultRecord objects
            # Process neighbor node (convert properties from node object)
            neighbor_node_obj = record["n"] # neo4j.graph.Node
            neighbor_id = neighbor_node_obj.get('id') # Access properties via get()
            if neighbor_id and neighbor_id not in processed_node_ids:
                 neighbor_props = dict(neighbor_node_obj) # Convert all properties
                 converted_neighbor_props = _convert_neo4j_temporal_types(neighbor_props)
                 neighbor_labels = list(neighbor_node_obj.labels)
                 # Determine type, prioritize non-generic labels if present
                 neighbor_type = 'Entity' # Default if no specific label
                 specific_labels = [l for l in neighbor_labels if not l.startswith('_') and l != 'Node']
                 if specific_labels:
                     neighbor_type = specific_labels[0]
                 
                 # Pop base fields from props 
                 created_at = converted_neighbor_props.pop("created_at", None)
                 updated_at = converted_neighbor_props.pop("updated_at", None)
                 # Remove internal id if present
                 converted_neighbor_props.pop("id", None) 
                 # Extract name if present, else use ID
                 name = converted_neighbor_props.pop("name", neighbor_id) 
                 
                 # Construct Entity object
                 neighbor_entity = Entity(
                     id=neighbor_id,
                     name=name, # Use extracted or default name
                     type=neighbor_type,
                     metadata=converted_neighbor_props, # Remaining items are metadata
                     created_at=created_at,
                     updated_at=updated_at
                 )
                 entities.append(neighbor_entity) # Append Entity object
                 processed_node_ids.add(neighbor_id)
                
            # Process source node (only need its ID for relationship)
            source_node_obj = record["e"] # neo4j.graph.Node
            source_id = source_node_obj.get('id')

            # Process relationship (use neo4j.graph.Relationship object)
            # --- DEBUG --- START ---
            try:
                print(f"[DEBUG] Type of record['r']: {type(record['r'])}")
                print(f"[DEBUG] Repr of record['r']: {repr(record['r'])}")
            except Exception as e:
                print(f"[DEBUG] Error printing debug info for record['r']: {e}")
            # --- DEBUG --- END ---
            rel_obj = record["r"] # neo4j.graph.Relationship
            # Use element_id for a unique internal ID if needed, or generate UUID
            rel_internal_id = rel_obj.element_id 
            if rel_internal_id not in processed_rel_ids and source_id and neighbor_id:
                rel_props = dict(rel_obj) # Convert properties to dict
                converted_rel_props = _convert_neo4j_temporal_types(rel_props)
                created_at = converted_rel_props.pop("created_at", None)
                updated_at = converted_rel_props.pop("updated_at", None)
                rel_type = rel_obj.type
                
                # Determine actual source/target based on relationship object nodes
                actual_source_node_id = rel_obj.start_node.get('id')
                actual_target_node_id = rel_obj.end_node.get('id')
                
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
            
        return entities, relationships

    async def search_entities_by_properties(
        self,
        properties: Dict[str, Any],
        limit: Optional[int] = None
    ) -> List[Entity]:
        """Searches for entities matching specific properties."""
        where_clauses = [f"n.`{k}` = ${k}" for k in properties.keys()]
        query = f"""
        MATCH (n)
        WHERE {' AND '.join(where_clauses)}
        RETURN properties(n) as props, labels(n) as labels
        """
        if limit:
            query += f" LIMIT {limit}"
            
        # Use a copy for parameters to avoid modifying the input dict
        params = properties.copy()
        if limit:
            params["limit"] = limit # Add limit to params if needed for query

        results = await self._execute_read_query(query, params)
        entities_found = []
        for record in results: # Process each record
             node_props = record["props"]
             labels = record["labels"]
             converted_data = _convert_neo4j_temporal_types(node_props)
             entity_id = converted_data.pop('id', None)
             if not entity_id: continue
             
             # Determine type, prioritize specific labels
             entity_type = 'Entity' # Default
             specific_labels = [l for l in labels if not l.startswith('_') and l != 'Node']
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
                 name=name, # Use extracted or default name
                 type=entity_type,
                 metadata=metadata,
                 created_at=created_at,
                 updated_at=updated_at
                 ))
        return entities_found

    async def add_entity(self, entity: Entity):
        """Adds or updates an Entity node to the graph."""
        # Reuse the add_node logic, ensuring the type is correctly handled
        # The Entity model already sets type='Entity'
        await self.add_node(entity)

    async def __aenter__(self):
        """Context manager entry."""
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        await self.close()

def escape_cypher_string(value: str) -> str:
    """Escapes characters in a string for safe use in Cypher labels/types."""
    # Basic escaping, might need refinement based on Memgraph label rules
    return value.replace("`", "``").replace("\"", "\\\"").replace("'", "\\'")
