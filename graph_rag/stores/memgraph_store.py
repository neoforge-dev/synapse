import logging
import time
from typing import Any

import pymgclient as mgclient  # Memgraph client library
from graph_rag.core.graph_store import GraphStore
from graph_rag.models import Entity, Relationship

logger = logging.getLogger(__name__)


class MemgraphStore(GraphStore):
    """Implementation of GraphStore using Memgraph."""

    # Default connection parameters (consider making these configurable)
    DEFAULT_HOST = "127.0.0.1"
    DEFAULT_PORT = 7687
    DEFAULT_USER = None
    DEFAULT_PASSWORD = None
    DEFAULT_USE_SSL = False

    # Retry parameters
    MAX_RETRIES = 3
    RETRY_DELAY_SECONDS = 2

    def __init__(
        self,
        host: str = DEFAULT_HOST,
        port: int = DEFAULT_PORT,
        user: str | None = DEFAULT_USER,
        password: str | None = DEFAULT_PASSWORD,
        use_ssl: bool = DEFAULT_USE_SSL,
        max_retries: int = MAX_RETRIES,
        retry_delay: int = RETRY_DELAY_SECONDS,
        # Note: Connection pooling can be added in future for high-concurrency scenarios
        # (pool_size, pool_timeout, pool_recycle parameters)
    ):
        self.host = host
        self.port = port
        self.user = user
        self.password = password
        self.use_ssl = use_ssl
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self._conn: mgclient.Connection | None = None
        self._connect()
        logger.info(f"MemgraphStore initialized for {host}:{port}. SSL: {use_ssl}")

    def _connect(self):
        """Establishes a connection to the Memgraph database with retries."""
        attempt = 0
        while attempt < self.max_retries:
            attempt += 1
            try:
                logger.info(
                    f"Attempting to connect to Memgraph ({attempt}/{self.max_retries})..."
                )
                self._conn = mgclient.connect(
                    host=self.host,
                    port=self.port,
                    username=self.user,
                    password=self.password,
                    sslmode=mgclient.SSLMODE_REQUIRE
                    if self.use_ssl
                    else mgclient.SSLMODE_DISABLE,
                    # lazy=True # Consider lazy connection if appropriate
                )
                # Test connection by executing a simple query
                with self._conn.cursor() as cursor:
                    cursor.execute("RETURN 1")
                    cursor.fetchall()
                logger.info("Successfully connected to Memgraph.")
                return  # Exit loop on success
            except mgclient.OperationalError as e:
                logger.warning(f"Connection attempt {attempt} failed: {e}")
                if attempt < self.max_retries:
                    logger.info(f"Retrying in {self.retry_delay} seconds...")
                    time.sleep(self.retry_delay)
                else:
                    logger.error(
                        "Max connection retries reached. Failed to connect to Memgraph."
                    )
                    raise  # Re-raise the exception after max retries
            except Exception as e:
                logger.error(
                    f"An unexpected error occurred during connection: {e}",
                    exc_info=True,
                )
                raise  # Re-raise unexpected errors

    def close(self):
        """Closes the database connection."""
        if self._conn:
            try:
                self._conn.close()
                self._conn = None
                logger.info("Memgraph connection closed.")
            except Exception as e:
                logger.error(f"Error closing Memgraph connection: {e}", exc_info=True)

    def _execute_query(
        self,
        query: str,
        params: dict[str, Any] | None = None,
        *,
        read_only: bool = False,
    ) -> list[tuple]:
        """Executes a Cypher query with retry logic.

        Args:
            query: The Cypher query string.
            params: Optional dictionary of parameters.
            read_only: If True, uses a read-only transaction context (if supported by driver/DB).
                       Currently informational for pymgclient.

        Returns:
            A list of result tuples.
        """
        if not self._conn or self._conn.closed:
            logger.warning("Connection lost. Attempting to reconnect...")
            self._connect()

        if not self._conn:
            raise mgclient.OperationalError("No active Memgraph connection.")

        attempt = 0
        while attempt < self.max_retries:
            attempt += 1
            try:
                # TODO: Check if pymgclient offers explicit read-only transactions later
                with self._conn.cursor() as cursor:
                    logger.debug(
                        f"Executing Cypher: {query} with params: {params} (Read-only: {read_only})"
                    )
                    cursor.execute(query, params or {})
                    results = cursor.fetchall()
                    return results
            except (mgclient.OperationalError, mgclient.DatabaseError) as e:
                logger.warning(f"Query execution attempt {attempt} failed: {e}")
                if "deadlock detected" in str(e).lower() or attempt >= self.max_retries:
                    logger.error(
                        f"Query failed after {attempt} attempts or due to deadlock: {query}"
                    )
                    raise
                logger.info(f"Retrying query in {self.retry_delay} seconds...")
                time.sleep(self.retry_delay)
            except Exception as e:
                logger.error(
                    f"Unexpected error executing query '{query}': {e}", exc_info=True
                )
                raise
        raise mgclient.OperationalError(
            f"Query failed after {self.max_retries} retries: {query}"
        )

    def _node_to_entity(self, node: Any) -> Entity:
        """Converts an mgclient.Node to an Entity object."""
        props = node.properties
        entity_id = props.pop("id", None)  # Remove id from metadata
        if not entity_id:
            logger.warning(f"Node missing 'id' property: {node}")
            # Decide handling: raise error, assign default, skip?
            entity_id = str(node.id)  # Fallback to internal ID if property missing

        entity_name = props.pop(
            "name", "Unknown"
        )  # Remove name from metadata, provide default
        # Assuming the first label is the primary type
        entity_type = node.labels[0] if node.labels else "Unknown"

        # Remaining properties are metadata
        metadata = props

        return Entity(
            id=entity_id, name=entity_name, type=entity_type, metadata=metadata
        )

    def _relationship_to_relationship(
        self, rel: Any, source_map: dict[int, Entity], target_map: dict[int, Entity]
    ) -> Relationship | None:
        """Converts an mgclient.Relationship to a Relationship object."""
        source_node = source_map.get(rel.start_node.id)
        target_node = target_map.get(rel.end_node.id)

        if not source_node or not target_node:
            logger.warning(
                f"Could not find source/target entity for relationship {rel.id} ({rel.type}). Source ID: {rel.start_node.id}, Target ID: {rel.end_node.id}"
            )
            return None

        return Relationship(
            source=source_node,
            target=target_node,
            type=rel.type,
            metadata=rel.properties,
        )

    def add_entity(self, entity: Entity):
        """Adds or updates an entity (node) in Memgraph using MERGE.

        Assumes entity.id is the unique identifier.
        Properties are overwritten on MERGE.
        """
        # Use MERGE to create the node if it doesn't exist or match it if it does.
        # ON CREATE sets properties only when the node is first created.
        # ON MATCH sets properties when the node already exists (effectively updating it).
        cypher = (
            f"MERGE (n:{entity.type} {{id: $id}}) "
            f"ON CREATE SET n = $props, n.created_at = timestamp() "
            f"ON MATCH SET n = $props, n.updated_at = timestamp()"
        )

        # Prepare properties, including the ID within the properties map
        props = entity.metadata.copy()
        props["id"] = entity.id
        props["name"] = entity.name  # Ensure name is stored as a property
        # Add type as property? Optional, depends on schema needs.
        # props['type'] = entity.type

        params = {"id": entity.id, "props": props}

        try:
            self._execute_query(cypher, params, read_only=False)
            logger.info(
                f"Added/Updated entity {entity.id} ({entity.type}:{entity.name}) in Memgraph."
            )
        except Exception as e:
            logger.error(f"Failed to add/update entity {entity.id}: {e}")
            raise

    def add_relationship(self, relationship: Relationship):
        """Adds a relationship (edge) between two existing entities in Memgraph using MERGE."""
        # Assumes source and target entities already exist or will be created separately.
        # MERGE prevents creating duplicate relationships with the same type and properties
        # between the same two nodes.
        cypher = (
            f"MATCH (source {{id: $source_id}}), (target {{id: $target_id}}) "
            f"MERGE (source)-[r:{relationship.type}]->(target) "
            f"ON CREATE SET r = $props, r.created_at = timestamp() "  # Set props on creation
            f"ON MATCH SET r = $props, r.updated_at = timestamp() "  # Update props on match
        )

        params = {
            "source_id": relationship.source.id,
            "target_id": relationship.target.id,
            "props": relationship.metadata.copy(),  # Store metadata as relationship properties
        }

        try:
            self._execute_query(cypher, params, read_only=False)
            logger.info(
                f"Added/Updated relationship {relationship.source.id} -[{relationship.type}]-> {relationship.target.id} in Memgraph."
            )
        except Exception as e:
            logger.error(
                f"Failed to add/update relationship {relationship.source.id} -> {relationship.target.id}: {e}"
            )
            raise

    def add_entities_and_relationships(
        self, entities: list[Entity], relationships: list[Relationship]
    ):
        """Adds multiple entities and relationships within a single transaction (potentially using UNWIND)."""
        if not entities and not relationships:
            logger.info("No entities or relationships provided for bulk add.")
            return

        # Use UNWIND for efficient batching
        # Note: This approach assumes entity IDs are unique and handles conflicts via MERGE.
        entity_params = []
        for entity in entities:
            props = entity.metadata.copy()
            props["id"] = entity.id
            props["name"] = entity.name
            entity_params.append({"id": entity.id, "type": entity.type, "props": props})

        relationship_params = []
        for rel in relationships:
            relationship_params.append(
                {
                    "source_id": rel.source.id,
                    "target_id": rel.target.id,
                    "type": rel.type,
                    "props": rel.metadata.copy(),
                }
            )

        # Combine into a single transaction if possible
        # Need to handle potential errors carefully within transactions
        if not self._conn or self._conn.closed:
            logger.warning(
                "Connection lost before bulk operation. Attempting to reconnect..."
            )
            self._connect()

        if not self._conn:
            raise mgclient.OperationalError(
                "No active Memgraph connection for bulk operation."
            )

        try:
            with self._conn.cursor() as cursor:
                logger.info(
                    f"Starting bulk add transaction: {len(entities)} entities, {len(relationships)} relationships."
                )

                # Process Entities with UNWIND and MERGE
                if entity_params:
                    # Note: Using item.type directly in the label might require Memgraph Enterprise or specific config.
                    # A safer approach might be to run separate queries per entity type or use a generic label.
                    # For simplicity here, let's assume a generic :Entity label if type isn't directly usable.
                    # We'll adjust based on actual Memgraph capabilities / schema decisions.
                    # REVISED for simplicity/compatibility: Assume labels are known or added separately.
                    # This example uses the type *from the model* to determine the label string.
                    # We might need separate UNWIND calls per entity type for robustness.

                    # Simplified approach: MERGE each entity type separately or use a fixed label initially
                    # Let's stick to a simplified per-entity call for now to avoid UNWIND complexity with dynamic labels
                    logger.debug(
                        "Bulk adding entities individually within transaction..."
                    )
                    for entity in entities:
                        e_cypher = (
                            f"MERGE (n:{entity.type} {{id: $id}}) "
                            f"ON CREATE SET n = $props, n.created_at = timestamp() "
                            f"ON MATCH SET n = $props, n.updated_at = timestamp()"
                        )
                        e_props = entity.metadata.copy()
                        e_props["id"] = entity.id
                        e_props["name"] = entity.name
                        e_params = {"id": entity.id, "props": e_props}
                        logger.debug(
                            f"Executing in transaction: {e_cypher} with params {e_params}"
                        )
                        cursor.execute(e_cypher, e_params)
                        # cursor.fetchall() # Optional: consume results if needed
                    logger.info(f"Executed MERGE for {len(entities)} entities.")

                # Process Relationships with UNWIND and MERGE
                if relationship_params:
                    # Again, dynamic relationship type item.type might need care.
                    # Let's assume it works or adjust if Memgraph requires quoted type strings.
                    # REVISED for robustness: Execute per relationship type or use fixed type if dynamic is complex.
                    # Using UNWIND is generally better for relationships.
                    logger.debug("Bulk adding relationships via UNWIND...")
                    # Refined relationship Cypher - use dynamic type syntax
                    rel_cypher_unwind = (
                        "UNWIND $batch AS item "
                        "MATCH (source {id: item.source_id}), (target {id: item.target_id}) "
                        "CALL { WITH source, target, item "
                        "  WITH source, target, item, item.type AS rel_type "
                        "  CALL apoc.create.relationship(source, rel_type, item.props, target) YIELD rel "
                        "  RETURN count(rel) as rel_count "
                        "} RETURN sum(rel_count) as total_rels"
                    )
                    # This requires Memgraph 2.x+ for CALL subquery.
                    # If using older version, might need different approach (e.g. separate queries per type).

                    logger.debug(
                        f"Executing in transaction: {rel_cypher_unwind} with batch size {len(relationship_params)}"
                    )
                    cursor.execute(rel_cypher_unwind, {"batch": relationship_params})
                    cursor.fetchall()  # Consume results
                    logger.info(
                        f"Executed MERGE for {len(relationships)} relationships via UNWIND."
                    )

                # self._conn.commit() # pymgclient uses auto-commit by default
                logger.info("Bulk add transaction completed successfully.")

        except Exception as e:
            logger.error(f"Bulk add transaction failed: {e}", exc_info=True)
            # Consider attempting rollback if supported/needed, though auto-commit makes this complex.
            # pymgclient might handle transaction state implicitly on error.
            raise  # Re-raise the exception

    # --- Query Methods Implementation ---

    def get_entity_by_id(self, entity_id: str) -> Entity | None:
        """Retrieves a single entity by its unique ID property."""
        cypher = "MATCH (n {id: $id}) RETURN n"
        params = {"id": entity_id}
        try:
            results = self._execute_query(cypher, params, read_only=True)
            if not results:
                logger.info(f"Entity with id '{entity_id}' not found.")
                return None

            node = results[0][0]  # Result is a tuple containing the node
            if isinstance(node, mgclient.Node):
                entity = self._node_to_entity(node)
                logger.info(f"Found entity: {entity.id} ({entity.type}:{entity.name})")
                return entity
            else:
                logger.warning(
                    f"Expected mgclient.Node but got {type(node)} for id {entity_id}"
                )
                return None

        except Exception as e:
            logger.error(
                f"Failed to get entity by id '{entity_id}': {e}", exc_info=True
            )
            raise  # Re-raise exception after logging

    def get_neighbors(
        self,
        entity_id: str,
        relationship_types: list[str] | None = None,
        direction: str = "both",
    ) -> tuple[list[Entity], list[Relationship]]:
        """Retrieves direct neighbors using Cypher MATCH."""

        # Build MATCH pattern based on direction
        if direction == "outgoing":
            match_pattern = "MATCH (e {id: $id})-[r]->(n)"
        elif direction == "incoming":
            match_pattern = "MATCH (e {id: $id})<-[r]-(n)"
        elif direction == "both":
            match_pattern = "MATCH (e {id: $id})-[r]-(n)"
        else:
            raise ValueError(
                "Invalid direction specified. Use 'outgoing', 'incoming', or 'both'."
            )

        # Add relationship type filter if provided
        where_clause = "WHERE id(e) <> id(n)"  # Exclude self-loops from neighbors
        if relationship_types:
            # Ensure types are properly escaped if they contain special chars
            # For simplicity, assume basic types here.
            # Memgraph allows filtering by type: `WHERE type(r) IN $types`
            rel_types_str = " | ".join(
                [f":`{t}`" for t in relationship_types]
            )  # Build type string like :TYPE1|:TYPE2
            match_pattern = match_pattern.replace("-[r]-", f"-[r{rel_types_str}]-")
            match_pattern = match_pattern.replace("-[r]->", f"-[r{rel_types_str}]->")
            match_pattern = match_pattern.replace("<-[r]-", f"<-[r{rel_types_str}]-")
            # No WHERE clause needed for type if specified in pattern

        # Query to return neighbor nodes and relationships
        cypher = f"{match_pattern} {where_clause} RETURN n, r, e"  # Also return starting node `e` to build relationship correctly
        params = {"id": entity_id}

        entities: dict[int, Entity] = {}
        relationships: list[Relationship] = []

        try:
            results = self._execute_query(cypher, params, read_only=True)
            logger.debug(f"Found {len(results)} paths for neighbors of {entity_id}")

            if not results:
                return [], []

            # Process results
            start_node_map = {}  # Map internal ID to Entity for relationships
            neighbor_map = {}
            processed_rel_ids = set()

            for neighbor_node, rel, start_node in results:
                if (
                    isinstance(neighbor_node, mgclient.Node)
                    and isinstance(rel, mgclient.Relationship)
                    and isinstance(start_node, mgclient.Node)
                ):
                    # Process start node (only needs to be done once)
                    if start_node.id not in start_node_map:
                        start_node_map[start_node.id] = self._node_to_entity(start_node)

                    # Process neighbor node
                    neighbor_entity = self._node_to_entity(neighbor_node)
                    if neighbor_node.id not in neighbor_map:
                        neighbor_map[neighbor_node.id] = neighbor_entity
                        entities[neighbor_node.id] = (
                            neighbor_entity  # Add to final entity list
                        )

                    # Process relationship (avoid duplicates if direction='both' returns same rel twice)
                    if rel.id not in processed_rel_ids:
                        # Determine source/target based on relationship direction relative to the query
                        self._relationship_to_relationship(
                            rel,
                            {start_node.id: start_node_map[start_node.id]},
                            neighbor_map,
                        )
                        # Need to check start/end node IDs to map correctly
                        if rel.start_node.id == start_node.id:
                            source = start_node_map[start_node.id]
                            target = neighbor_map[neighbor_node.id]
                        else:  # Relationship is incoming
                            source = neighbor_map[neighbor_node.id]
                            target = start_node_map[start_node.id]

                        if source and target:
                            relationships.append(
                                Relationship(
                                    source=source,
                                    target=target,
                                    type=rel.type,
                                    metadata=rel.properties,
                                )
                            )
                            processed_rel_ids.add(rel.id)
                        else:
                            logger.warning(
                                f"Skipping relationship {rel.id} due to missing source/target mapping."
                            )

            logger.info(
                f"Retrieved {len(entities)} neighbors and {len(relationships)} relationships for entity {entity_id}."
            )
            return list(entities.values()), relationships

        except Exception as e:
            logger.error(
                f"Failed to get neighbors for entity '{entity_id}': {e}", exc_info=True
            )
            raise

    def search_entities_by_properties(
        self, properties: dict[str, Any], limit: int | None = None
    ) -> list[Entity]:
        """Searches for entities matching specific properties using Cypher.

        Assumes properties exist on the node and are indexed for performance.
        Handles 'type' as a special case to match node labels.
        """
        if not properties:
            logger.warning(
                "Attempted to search entities with empty properties dictionary."
            )
            return []

        # Separate label (type) from other properties
        entity_type = properties.get("type")
        match_props = {k: v for k, v in properties.items() if k != "type"}

        # Build MATCH and WHERE clauses
        label_match = (
            f":{entity_type}" if entity_type else ""
        )  # Match specific label if provided
        where_clauses = []
        params = {}

        # Add property checks to WHERE clause
        # Use placeholders like $prop_key for security and correctness
        for _i, (key, value) in enumerate(match_props.items()):
            # Sanitize key for parameter name (basic example)
            param_key = f"prop_{key.replace('-', '_').replace('.', '_')}"
            where_clauses.append(f"n.{key} = ${param_key}")
            params[param_key] = value

        # Base MATCH clause
        cypher = f"MATCH (n{label_match}) "

        # Add WHERE clause if properties were provided
        if where_clauses:
            cypher += "WHERE " + " AND ".join(where_clauses)

        # Add RETURN and LIMIT
        cypher += " RETURN n"
        if limit is not None and isinstance(limit, int) and limit > 0:
            cypher += f" LIMIT {limit}"  # Append limit directly as it's controlled
            params["limit_val"] = (
                limit  # Can also use parameter, but direct append is common for LIMIT
            )
        else:
            # Default limit to prevent accidental large queries?
            # cypher += " LIMIT 100"
            pass

        logger.debug(f"Executing entity search query: {cypher} with params: {params}")
        found_entities = []
        try:
            results = self._execute_query(cypher, params, read_only=True)
            for row in results:
                node = row[0]
                if isinstance(node, mgclient.Node):
                    found_entities.append(self._node_to_entity(node))
                else:
                    logger.warning(f"Search returned non-Node object: {row}")

            logger.info(
                f"Found {len(found_entities)} entities matching properties: {properties}"
            )
            return found_entities

        except Exception as e:
            logger.error(
                f"Failed to search entities by properties {properties}: {e}",
                exc_info=True,
            )
            raise  # Re-raise after logging

    # --- Placeholder for Other Query Methods ---

    # def get_subgraph(self, center_entity_id: str, hops: int = 1) -> Tuple[List[Entity], List[Relationship]]:
    #     # Implementation using Cypher MATCH and path expansion
    #     pass

    # def community_detection(self, config: Optional[Dict[str, Any]] = None):
    #     # Implementation using Memgraph MAGE library (e.g., Louvain)
    #     pass

    def __del__(self):
        """Ensure connection is closed when the object is destroyed."""
        self.close()
