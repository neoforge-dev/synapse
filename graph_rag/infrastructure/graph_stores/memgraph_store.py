"""Optimized Memgraph graph store implementation."""

import logging
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timezone
import asyncio

from neo4j import AsyncGraphDatabase, AsyncDriver
from neo4j.exceptions import Neo4jError, ServiceUnavailable, AuthError
import neo4j.time # Import neo4j.time for type checking
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from graph_rag.core.graph_store import GraphStore
from graph_rag.domain.models import Document, Chunk, Entity, Relationship, Node
from graph_rag.config import settings

logger = logging.getLogger(__name__)

# Define retryable exceptions
_RETRY_EXCEPTIONS = (Neo4jError, ServiceUnavailable, ConnectionError, AuthError)

def _convert_neo4j_temporal_types(data: Dict[str, Any]) -> Dict[str, Any]:
    """Converts neo4j.time objects in a dictionary to Python datetime."""
    converted = {}
    for key, value in data.items():
        if isinstance(value, (neo4j.time.DateTime, neo4j.time.Date, neo4j.time.Time)):
            try:
                # Use to_native() for conversion
                converted_value = value.to_native()
                # Ensure timezone awareness for datetime objects if conversion results in naive
                if isinstance(converted_value, datetime) and converted_value.tzinfo is None:
                     # Attempt to use original timezone if available, otherwise assume UTC
                     original_tz = getattr(value, 'tzinfo', None)
                     if original_tz:
                         # pytz might be needed for full Neo4j timezone compatibility
                         # For simplicity here, we'll assume UTC if conversion is naive
                         # Or handle specific known tz types if needed.
                         # This part might need refinement depending on Neo4j timezone usage.
                         # Defaulting to UTC if conversion yields naive datetime.
                         converted_value = converted_value.replace(tzinfo=timezone.utc) 
                     else:
                         # If original had no tz and native is naive, it's likely Local[Date]Time
                         pass # Keep as naive
                converted[key] = converted_value
            except Exception as e:
                logger.warning(f"Could not convert neo4j temporal type for key '{key}': {e}. Keeping original.")
                converted[key] = value # Keep original if conversion fails
        elif isinstance(value, dict):
            converted[key] = _convert_neo4j_temporal_types(value) # Recursively convert nested dicts
        elif isinstance(value, list):
             # Convert temporal types within lists if necessary (simple check)
             converted[key] = [
                 item.to_native() if isinstance(item, (neo4j.time.DateTime, neo4j.time.Date, neo4j.time.Time)) else item 
                 for item in value
             ]
        else:
            converted[key] = value
    return converted

class MemgraphGraphRepository(GraphStore):
    """Optimized Memgraph implementation of the GraphStore interface."""

    def __init__(self, driver: Optional[AsyncDriver] = None):
        """
        Initializes the repository with an optional Neo4j driver instance.
        If no driver is provided, one will be created using settings.
        """
        self._driver = driver
        self._retry_decorator = retry(
            stop=stop_after_attempt(settings.MEMGRAPH_RETRY_ATTEMPTS),
            wait=wait_exponential(
                multiplier=settings.MEMGRAPH_RETRY_WAIT_SECONDS,
                min=1,
                max=10
            ),
            retry=retry_if_exception_type(_RETRY_EXCEPTIONS),
            before_sleep=lambda retry_state: logger.warning(
                f"Retrying operation due to {retry_state.outcome.exception()}, "
                f"attempt {retry_state.attempt_number}..."
            )
        )
        self._is_connected = False
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

    async def _execute_write_query(self, query: str, parameters: Optional[Dict[str, Any]] = None) -> None:
        """Executes a write query with retry logic and transaction support."""
        @self._retry_decorator
        async def _execute():
            async with self._get_driver.session() as session:
                try:
                    await session.run(query, parameters or {})
                except Neo4jError as e:
                    logger.error(f"Write query failed: {e} | Query: {query} | Params: {parameters}")
                    raise
        await _execute()

    async def _execute_read_query(self, query: str, parameters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Executes a read query with retry logic and transaction support."""
        @self._retry_decorator
        async def _execute():
            async with self._get_driver.session() as session:
                try:
                    result = await session.run(query, parameters or {})
                    return [record.data() async for record in result]
                except Neo4jError as e:
                    logger.error(f"Read query failed: {e} | Query: {query} | Params: {parameters}")
                    raise
        return await _execute()

    async def clear_all_data(self) -> None:
        """Deletes all nodes and relationships from the graph."""
        logger.warning("Clearing all data from Memgraph database!")
        await self._execute_write_query("MATCH (n) DETACH DELETE n")
        logger.info("Cleared all data from Memgraph database.")

    async def add_document(self, document: Document):
        """Adds a document node to the graph."""
        logger.debug(f"Adding document {document.id}")
        # Use model_dump() for Pydantic models
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
        # Use model_dump() for Pydantic models
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

        # Use model_dump() for entities
        entity_params = [
            {
                "id": e.id,
                "type": e.type, # Pass type for label creation
                # Entity model doesn't have properties field directly, get from model_dump if needed
                # Or assume properties are handled by the base Node logic if inherited
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
            # Assuming Entity maps to nodes with label 'Entity' or use get_node_by_id
            node = await self.get_node_by_id(entity_id)
            if node and isinstance(node, Entity): # Check if the returned node is actually an Entity
                 return node
            elif node: # If it's a Node but not specifically Entity, log warning or handle as needed
                 logger.warning(f"Retrieved node {entity_id} is of type {node.type}, not Entity.")
                 # Optionally return None or try to cast if appropriate
            return None
        except Exception as e:
            logger.error(f"Failed to get entity {entity_id}: {e}")
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
        
        results = await self._execute_read_query(query, {"id": entity_id})
        
        entities = []
        relationships = []
        processed_node_ids = set()
        processed_rel_ids = set()
        
        for result in results:
            # Process neighbor node
            neighbor_node_data = result["n"]
            neighbor_id = neighbor_node_data.get('id')
            if neighbor_id and neighbor_id not in processed_node_ids:
                 converted_neighbor_props = _convert_neo4j_temporal_types(neighbor_node_data)
                 neighbor_labels = await self._execute_read_query("MATCH (n {id:$id}) RETURN labels(n) as lbls", {"id": neighbor_id})
                 neighbor_type = neighbor_labels[0]['lbls'][0] if neighbor_labels and neighbor_labels[0]['lbls'] else 'Node'
                 # Pop base fields from props 
                 created_at = converted_neighbor_props.pop("created_at", None)
                 updated_at = converted_neighbor_props.pop("updated_at", None)
                 # Reconstruct appropriate model type (Node or Entity etc.) based on label
                 # For simplicity, use Node; ideally map labels to domain models
                 neighbor_model = Node(
                     id=neighbor_id,
                     type=neighbor_type,
                     properties=converted_neighbor_props, # Pass remaining as properties
                     created_at=created_at,
                     updated_at=updated_at
                 )
                 entities.append(neighbor_model) # Add Node or specific type like Entity
                 processed_node_ids.add(neighbor_id)
            else:
                 neighbor_model = next((ent for ent in entities if ent.id == neighbor_id), None)
                
            # Process source node (only need its ID for relationship)
            source_node_data = result["e"]
            source_id = source_node_data.get('id')

            # Process relationship
            rel_data = result["r"] # This is a neo4j.graph.Relationship object
            rel_id = rel_data.id # Get internal Neo4j ID
            if rel_id not in processed_rel_ids and source_id and neighbor_id:
                rel_props = dict(rel_data) # Convert properties to dict
                converted_rel_props = _convert_neo4j_temporal_types(rel_props)
                created_at = converted_rel_props.pop("created_at", None)
                updated_at = converted_rel_props.pop("updated_at", None)
                rel_type = rel_data.type
                
                # Determine actual source/target based on relationship direction relative to query
                # The query MATCH (e)-[r]-(n) means r could be outgoing or incoming from e
                actual_source_id = rel_data.start_node.element_id.split(':')[-1] # Get node ID
                actual_target_id = rel_data.end_node.element_id.split(':')[-1]
                
                # We need to map Neo4j's internal element IDs back to our application IDs ('id' property)
                # This part is tricky without getting node properties. Assuming e.id and n.id are correct.
                # The query returns e (source anchor) and n (neighbor). Rel direction defines source/target.
                # Let's assume the Relationship model uses OUR IDs (doc_id, chunk_id etc.)
                # We need to fetch these IDs if not directly available. Simplification: use e.id and n.id
                
                rel_model = Relationship(
                    id=str(rel_id), # Use neo4j internal ID or generate one if needed
                    source_id=source_id if rel_data.start_node.element_id == result["e"].element_id else neighbor_id,
                    target_id=neighbor_id if rel_data.end_node.element_id == result["n"].element_id else source_id,
                    type=rel_type,
                    properties=converted_rel_props,
                    created_at=created_at,
                    updated_at=updated_at
                )
                relationships.append(rel_model)
                processed_rel_ids.add(rel_id)
            
        return entities, relationships

    async def search_entities_by_properties(
        self,
        properties: Dict[str, Any],
        limit: Optional[int] = None
    ) -> List[Entity]:
        """Searches for entities matching specific properties."""
        where_clauses = [f"n.{k} = ${k}" for k in properties.keys()]
        query = f"""
        MATCH (n)
        WHERE {' AND '.join(where_clauses)}
        RETURN n
        """
        if limit:
            query += f" LIMIT {limit}"
            
        results = await self._execute_read_query(query, properties)
        # Process results similarly to get_node_by_id, converting temporals
        entities_found = []
        for result in results:
             node_data = result["n"]
             converted_data = _convert_neo4j_temporal_types(node_data)
             entity_id = converted_data.pop('id', None)
             if not entity_id: continue
             # Determine type from labels if possible, default to Entity
             # This part needs refinement if labels are stored/retrieved
             node_type = 'Entity' # Default or determine from labels
             created_at = converted_data.pop("created_at", None)
             updated_at = converted_data.pop("updated_at", None)
             entities_found.append(Entity(
                 id=entity_id, \
                 type=node_type, \
                 properties=converted_data,\
                 created_at=created_at,\
                 updated_at=updated_at\
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
