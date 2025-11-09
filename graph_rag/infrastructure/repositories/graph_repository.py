import logging
from datetime import datetime
from typing import Any

import neo4j.time  # Import neo4j.time for type checking
from neo4j import (
    AsyncDriver,  # <-- IMPORT AsyncDriver
    Record,
)
from neo4j.exceptions import Neo4jError  # <-- IMPORT Neo4jError
from neo4j.graph import Node as Neo4jNode
from neo4j.graph import Relationship as Neo4jRelationship

# import mgclient # <-- REMOVE old sync driver import
from graph_rag.core.graph_store import GraphStore
from graph_rag.core.interfaces import ChunkData, SearchResultData
from graph_rag.domain.models import Chunk, Document, Entity, Relationship

logger = logging.getLogger(__name__)


def _convert_neo4j_temporal_types(value: Any) -> Any:
    """Converts Neo4j temporal types to standard Python types."""
    if isinstance(value, neo4j.time.DateTime | neo4j.time.Date | neo4j.time.Time):
        return value.to_native()
    return value


class MemgraphRepository(GraphStore):
    """Repository for interacting with the Memgraph graph database using the neo4j async driver."""

    def __init__(self, driver: AsyncDriver):
        if driver is None:
            raise ValueError("AsyncDriver instance is required.")
        self._driver = driver
        logger.info("MemgraphRepository initialized with neo4j AsyncDriver.")

    async def add_entity(self, entity: Entity):
        """Adds or updates an entity (node) in the graph, replacing existing properties."""
        # Prepare properties map for SET clause (replaces existing properties)
        properties_map = {**entity.properties}
        properties_map["id"] = (
            entity.id
        )  # Ensure ID is part of the properties for MERGE/SET
        properties_map["updated_at"] = datetime.now()  # Add/update timestamp

        # Escape the node type/label
        safe_type = entity.type.replace("`", "").replace(":", "")

        query = f"""
        MERGE (e:`{safe_type}` {{id: $id}})
        SET e = $properties_map
        RETURN e.id
        """
        # Use the entity ID for MERGE and pass the full map for SET
        params = {"id": entity.id, "properties_map": properties_map}
        await self._driver.execute_query(query, params)

    async def add_relationship(self, relationship: Relationship):
        """Adds or updates a relationship (edge) between two entities, replacing existing properties."""
        # First, check if both nodes exist to provide better error messages
        query_check = """
        OPTIONAL MATCH (source {id: $source_id})
        OPTIONAL MATCH (target {id: $target_id})
        RETURN source IS NOT NULL as source_exists, target IS NOT NULL as target_exists
        """
        params_check = {
            "source_id": relationship.source_id,
            "target_id": relationship.target_id,
        }

        try:
            result, summary, keys = await self._driver.execute_query(
                query_check, params_check
            )
            if result and result[0]:
                source_exists = result[0]["source_exists"]
                target_exists = result[0]["target_exists"]

                if not source_exists and not target_exists:
                    raise ValueError(
                        f"Failed to add/update relationship {relationship.id}: Both source node {relationship.source_id} and target node {relationship.target_id} do not exist. Source or target node may not exist."
                    )
                elif not source_exists:
                    raise ValueError(
                        f"Failed to add/update relationship {relationship.id}: Source node {relationship.source_id} does not exist. Source or target node may not exist."
                    )
                elif not target_exists:
                    raise ValueError(
                        f"Failed to add/update relationship {relationship.id}: Target node {relationship.target_id} does not exist. Source or target node may not exist."
                    )

            # If we get here, both nodes exist, so proceed with the relationship creation
            # Prepare properties map for SET clause (replaces existing properties)
            properties_map = {**relationship.properties}
            properties_map["id"] = (
                relationship.id
            )  # Ensure ID is part of the properties for MERGE/SET
            properties_map["updated_at"] = datetime.now()  # Add/update timestamp

            # Escape the relationship type
            safe_type = relationship.type.replace("`", "").replace(":", "")

            query = f"""
            MATCH (source {{id: $source_id}}), (target {{id: $target_id}})
            MERGE (source)-[r:`{safe_type}` {{id: $id}}]->(target)
            SET r = $properties_map
            RETURN r.id
            """

            # Combine MATCH/MERGE params and SET params
            params = {
                "id": relationship.id,
                "source_id": relationship.source_id,
                "target_id": relationship.target_id,
                "properties_map": properties_map,
            }
            await self._driver.execute_query(query, params)

        except Neo4jError as e:
            # Wrap Neo4j errors with more context
            logger.error(
                f"Neo4j error adding relationship {relationship.id}: {e}", exc_info=True
            )
            raise ValueError(
                f"Failed to add/update relationship {relationship.id}: {e}. Source or target node may not exist."
            ) from e
        except ValueError as e:
            # Re-raise ValueError exceptions (from our own checks)
            logger.error(
                f"Error adding relationship {relationship.id}: {e}", exc_info=True
            )
            raise
        except Exception as e:
            # Wrap other exceptions
            logger.error(
                f"Unexpected error adding relationship {relationship.id}: {e}",
                exc_info=True,
            )
            raise ValueError(
                f"Failed to add/update relationship {relationship.id} due to an unexpected error: {e}"
            ) from e

    async def add_entities_and_relationships(
        self, entities: list[Entity], relationships: list[Relationship]
    ):
        """Adds multiple entities and relationships using a transaction."""
        async with self._driver.session() as session:
            try:
                # Add Entities
                if entities:
                    for entity in entities:
                        # node_properties = {**entity.properties}
                        # node_properties.pop('id', None)
                        safe_type = entity.type.replace("`", "").replace(":", "")
                        # Build SET clause dynamically
                        # set_clause, set_params = self._build_set_clause(node_properties, 'e')
                        # single_entity_query = f"MERGE (e:`{safe_type}` {{id: $id}}) SET {set_clause}"
                        # params = {"id": entity.id, **set_params}

                        # Use SET = $map logic consistent with add_entity
                        node_properties = {**entity.properties}  # Start with user props
                        node_properties["id"] = entity.id  # Ensure ID is in map
                        node_properties["updated_at"] = datetime.now()
                        single_entity_query = f"MERGE (e:`{safe_type}` {{id: $id}}) SET e = $properties_map"
                        params = {"id": entity.id, "properties_map": node_properties}
                        await session.run(single_entity_query, params)

                # Add Relationships
                if relationships:
                    for rel in relationships:
                        # rel_properties = {**rel.properties}
                        # rel_properties.pop('id', None)
                        safe_type = rel.type.replace("`", "").replace(":", "")
                        # Build SET clause dynamically
                        # set_clause, set_params = self._build_set_clause(rel_properties, 'r')
                        # single_rel_query = f"""
                        # MATCH (source {{id: $source_id}}), (target {{id: $target_id}})
                        # MERGE (source)-[r:`{safe_type}` {{id: $id}}]->(target)
                        # SET {set_clause}
                        # """
                        # params = {
                        #     "id": rel.id,
                        #     "source_id": rel.source_id,
                        #     "target_id": rel.target_id,
                        #     **set_params
                        # }

                        # Use SET = $map logic consistent with add_relationship
                        rel_properties = {**rel.properties}  # Start with user props
                        rel_properties["id"] = rel.id  # Ensure ID is in map
                        rel_properties["updated_at"] = datetime.now()
                        single_rel_query = f"""
                        MATCH (source {{id: $source_id}}), (target {{id: $target_id}})
                        MERGE (source)-[r:`{safe_type}` {{id: $id}}]->(target)
                        SET r = $properties_map
                        """
                        params = {
                            "id": rel.id,
                            "source_id": rel.source_id,
                            "target_id": rel.target_id,
                            "properties_map": rel_properties,
                        }
                        await session.run(single_rel_query, params)

                logger.info(
                    f"Bulk added {len(entities)} entities and {len(relationships)} relationships."
                )

            except Exception as e:
                logger.error(
                    f"Error during bulk operation: {e}. Transaction will be rolled back.",
                    exc_info=True,
                )
                raise  # Re-raise the original exception (session context manager handles rollback)

    def _map_node_to_entity(self, node_data: Any) -> Entity:
        """Maps a dictionary representation OR a neo4j.graph.Node to an Entity object."""
        properties = {}
        node_id = None
        node_type = "Unknown"
        created_at = None
        updated_at = None

        if isinstance(node_data, Neo4jNode):
            # Handle neo4j.graph.Node
            labels = list(node_data.labels)
            node_type = labels[0] if labels else "Unknown"
            properties = dict(node_data)
            node_id = str(properties.pop("id", None))  # Get app ID from properties
            created_at = _convert_neo4j_temporal_types(
                properties.pop("created_at", None)
            )
            updated_at = _convert_neo4j_temporal_types(
                properties.pop("updated_at", None)
            )
            # properties dict now contains only user-defined properties
            if node_id is None:
                # Use Neo4j's internal element_id if app 'id' is missing
                logger.warning(
                    f"Node {node_data.element_id} of type {node_type} is missing 'id' property! Using element_id."
                )
                node_id = node_data.element_id

        elif isinstance(node_data, Record):
            # Handle neo4j.Record (commonly returned by execute_query)
            data = node_data.data()
            node_id = str(data.get("id"))
            node_type = data.get(
                "type", "Unknown"
            )  # Assuming 'type' alias was used in query
            if not node_type and "labels" in data:
                node_type = data["labels"][0] if data["labels"] else "Unknown"
            properties = data.get(
                "properties", {}
            )  # Assuming 'properties' alias was used
            if not isinstance(properties, dict):
                properties = {}
            created_at = _convert_neo4j_temporal_types(data.get("created_at"))
            updated_at = _convert_neo4j_temporal_types(data.get("updated_at"))
            # Remove internal keys if they exist in properties
            properties.pop("id", None)
            properties.pop("created_at", None)
            properties.pop("updated_at", None)

        elif isinstance(node_data, dict):
            # Handle dictionary
            node_id = str(node_data.get("id"))
            node_type = node_data.get("type", "Unknown")
            properties = node_data.get("properties", {})
            if not isinstance(properties, dict):
                properties = {}
            created_at = _convert_neo4j_temporal_types(node_data.get("created_at"))
            updated_at = _convert_neo4j_temporal_types(node_data.get("updated_at"))
            properties.pop("id", None)
            properties.pop("created_at", None)
            properties.pop("updated_at", None)

        else:
            logger.error(
                f"Cannot map data of type {type(node_data)} to Entity: {node_data}"
            )
            raise TypeError(
                f"Unsupported data type for node mapping: {type(node_data)}"
            )

        return Entity(
            id=str(node_id),
            type=str(node_type),
            properties=properties,
            created_at=created_at,
            updated_at=updated_at,
        )

    async def get_entity_by_id(self, entity_id: str) -> Entity | None:
        """Retrieves a single entity by its unique ID using async execution."""
        # Fetch the node itself and its labels for type
        query = """
        MATCH (e {id: $id})
        RETURN e as node, labels(e) as labels
        LIMIT 1
        """
        params = {"id": entity_id}

        try:
            result, summary, keys = await self._driver.execute_query(query, params)

            if result:
                record = result[0]
                node_obj = record["node"]  # Get the neo4j.graph.Node object
                # Pass the Node object directly to the mapping function
                return self._map_node_to_entity(node_obj)
            return None  # No matching entity found
        except Neo4jError as e:
            logger.error(
                f"Neo4jError retrieving entity {entity_id}: {e.message} (Code: {e.code})",
                exc_info=True,
            )
            raise
        except Exception as e:
            logger.error(
                f"Unexpected error retrieving entity {entity_id}: {e}", exc_info=True
            )
            raise

    def _map_edge_to_relationship(
        self, edge_record: Record | Neo4jRelationship
    ) -> Relationship:
        """Maps a neo4j Record or neo4j.graph.Relationship to a domain Relationship object."""
        properties = {}
        rel_id = None
        rel_type = "UNKNOWN"
        source_id = None
        target_id = None
        created_at = None
        updated_at = None

        if isinstance(edge_record, Neo4jRelationship):
            # Handle neo4j.graph.Relationship
            rel_obj = edge_record
            rel_type = rel_obj.type
            properties = dict(rel_obj)
            rel_id = str(properties.pop("id", None))  # Get app ID from properties
            # Get source/target IDs from the nodes connected by the relationship
            # Assuming node objects have an 'id' property defined by the application
            source_id = (
                str(rel_obj.start_node.get("id")) if rel_obj.start_node else None
            )
            target_id = str(rel_obj.end_node.get("id")) if rel_obj.end_node else None
            created_at = _convert_neo4j_temporal_types(
                properties.pop("created_at", None)
            )
            updated_at = _convert_neo4j_temporal_types(
                properties.pop("updated_at", None)
            )
            if rel_id is None:
                logger.warning(
                    f"Relationship {rel_obj.element_id} of type {rel_type} is missing 'id' property! Using element_id."
                )
                rel_id = rel_obj.element_id
            if source_id is None:
                logger.warning(
                    f"Relationship {rel_id} is missing start node 'id' property!"
                )
            if target_id is None:
                logger.warning(
                    f"Relationship {rel_id} is missing end node 'id' property!"
                )

        elif isinstance(edge_record, Record):
            # Handle neo4j.Record (assuming aliases like 'r', 'sourceId', 'targetId')
            data = edge_record.data()
            rel_data = data.get("r", {})  # Assuming relationship data is under 'r'
            if isinstance(rel_data, Neo4jRelationship):
                # If the record directly contains the Relationship object
                return self._map_edge_to_relationship(rel_data)
            elif isinstance(rel_data, dict):
                # If relationship properties are in a dict under 'r'
                properties = rel_data
                rel_id = str(
                    properties.pop("id", data.get("relId", None))
                )  # Check for alias 'relId'
                rel_type = data.get("relType", "UNKNOWN")  # Check for alias 'relType'
                source_id = str(data.get("sourceId"))
                target_id = str(data.get("targetId"))
                created_at = _convert_neo4j_temporal_types(
                    properties.pop("created_at", None)
                )
                updated_at = _convert_neo4j_temporal_types(
                    properties.pop("updated_at", None)
                )
            else:
                logger.error(f"Cannot map Record data to Relationship: {data}")
                raise TypeError(
                    f"Unsupported Record structure for relationship mapping: {data}"
                )
        else:
            logger.error(
                f"Cannot map data of type {type(edge_record)} to Relationship: {edge_record}"
            )
            raise TypeError(
                f"Unsupported data type for relationship mapping: {type(edge_record)}"
            )

        return Relationship(
            id=str(rel_id),
            source_id=str(source_id),
            target_id=str(target_id),
            type=str(rel_type),
            properties=properties,
            created_at=created_at,
            updated_at=updated_at,
        )

    async def get_neighbors(
        self,
        entity_id: str,
        relationship_types: list[str] | None = None,
        direction: str = "both",
    ) -> tuple[list[Entity], list[Relationship]]:
        """Retrieves neighbors and relationships connected to an entity."""
        # Build relationship type filter for the query
        rel_filter = ""
        if relationship_types:
            # Escape and format types correctly: |:REL_A|:REL_B
            safe_types = [
                rt.replace("`", "").replace(":", "") for rt in relationship_types
            ]
            rel_filter = ":`" + "`|:`".join(safe_types) + "`"

        # Build query based on direction
        if direction == "outgoing":
            query = f"MATCH (start {{id: $id}})-[r{rel_filter}]->(neighbor) RETURN start, r, neighbor"
        elif direction == "incoming":
            query = f"MATCH (neighbor)-[r{rel_filter}]->(start {{id: $id}}) RETURN start, r, neighbor"
        else:  # both
            query = f"MATCH (start {{id: $id}})-[r{rel_filter}]-(neighbor) RETURN start, r, neighbor"

        params = {"id": entity_id}
        neighbors = []
        relationships = []

        try:
            result, summary, keys = await self._driver.execute_query(query, params)
            processed_neighbor_ids = set()
            processed_rel_ids = set()

            for record in result:
                neighbor_node = record["neighbor"]  # Get the neighbor Node object
                rel_obj = record["r"]  # Get the Relationship object

                if neighbor_node.element_id not in processed_neighbor_ids:
                    neighbor_entity = self._map_node_to_entity(neighbor_node)
                    neighbors.append(neighbor_entity)
                    processed_neighbor_ids.add(neighbor_node.element_id)

                if rel_obj.element_id not in processed_rel_ids:
                    # Pass the Relationship object directly
                    relationship_entity = self._map_edge_to_relationship(rel_obj)
                    relationships.append(relationship_entity)
                    processed_rel_ids.add(rel_obj.element_id)

            return neighbors, relationships
        except Exception as e:
            logger.error(
                f"Error getting neighbors for entity {entity_id}: {e}", exc_info=True
            )
            return [], []  # Return empty lists on error

    async def search_entities_by_properties(
        self, properties: dict[str, Any], limit: int | None = None
    ) -> list[Entity]:
        """Searches for entities matching specific properties."""
        # Check if 'type' is specified to use as a label constraint
        node_type = None
        if "type" in properties:
            node_type = properties.pop(
                "type"
            )  # Remove 'type' from properties to avoid using it as a property filter

        # Build the label filter
        label_filter = f":`{node_type}`" if node_type else ""

        # Build property filters
        where_clauses = []
        params = {}
        for i, (key, value) in enumerate(properties.items()):
            param_name = f"prop_val_{i}"
            # Escape key if needed, though properties don't usually need escaping like labels/types
            safe_key = key  # Assume keys are safe for now
            where_clauses.append(f"e.`{safe_key}` = ${param_name}")
            params[param_name] = value

        # Build the WHERE clause
        where_clause = " AND ".join(where_clauses)
        where_part = f"WHERE {where_clause}" if where_clauses else ""

        # Build the LIMIT clause
        limit_clause = f"LIMIT {int(limit)}" if limit is not None and limit > 0 else ""

        # Modified query to use the label filter
        query = f"""
        MATCH (e{label_filter})
        {where_part}
        RETURN e as node, labels(e) as labels
        {limit_clause}
        """

        entities = []
        try:
            result, summary, keys = await self._driver.execute_query(query, params)
            for record in result:
                node_obj = record["node"]  # Get the neo4j.graph.Node object
                entities.append(self._map_node_to_entity(node_obj))
            return entities
        except Exception as e:
            logger.error(
                f"Error searching entities by properties {properties}: {e}",
                exc_info=True,
            )
            return []  # Return empty list on error

    async def close(self) -> None:
        """Closes the Neo4j driver connection."""
        if self._driver:
            try:
                await self._driver.close()
                # Log database name if available (check driver attributes or connection details)
                # Since database name isn't directly on AsyncBoltDriver, log URI instead or omit DB name.
                logger.info("Neo4j AsyncDriver closed.")
            except Exception as e:
                logger.error(f"Error closing Neo4j AsyncDriver: {e}", exc_info=True)
        else:
            logger.warning("Close called but no active AsyncDriver found.")

    async def delete_document(self, document_id: str) -> bool:
        """Deletes a Document node and its associated Chunk nodes (via CONTAINS relationship)."""
        # First, check if the document exists
        existing_doc = await self.get_entity_by_id(document_id)

        # <<< ADD DETAILED DEBUG LOGGING >>>
        logger.debug(
            f"[Delete Check] For ID '{document_id}', get_entity_by_id returned: {existing_doc!r} (Type: {type(existing_doc)})"
        )

        if not existing_doc or existing_doc.type != "Document":
            logger.warning(
                f"Attempted to delete non-existent document {document_id}. Returning False based on check."
            )
            return False  # Return False if check fails

        # If check passes, document exists. Try deleting it.
        logger.info(f"Document {document_id} found. Proceeding with deletion query.")
        query = (
            "MATCH (d:Document {id: $doc_id}) "
            "OPTIONAL MATCH (d)-[:CONTAINS]->(c:Chunk) "
            "DETACH DELETE d, c"
        )
        try:
            results, summary, keys = await self._driver.execute_query(
                query, {"doc_id": document_id}
            )
            nodes_deleted = summary.counters.nodes_deleted
            if nodes_deleted > 0:
                logger.info(
                    f"Deletion query successful for {document_id}, nodes deleted: {nodes_deleted}. Returning True."
                )
                return True  # Return True ONLY if deletion query ran AND deleted nodes
            else:
                # This case might indicate an issue if the doc existed but wasn't deleted.
                logger.warning(
                    f"Document {document_id} existed but deletion query reported 0 nodes deleted. Returning False."
                )
                return (
                    False  # Return False if deletion query deleted nothing (unexpected)
                )

        except Exception as e:
            logger.error(
                f"Error during deletion query for document {document_id}: {e}",
                exc_info=True,
            )
            # Re-raise a more specific error or return False, depending on desired API behavior
            # Sticking with original raise: signals DB/query error vs simple 'not found'
            raise ValueError(
                f"Failed to delete document {document_id} during query execution: {e}"
            ) from e

    async def add_document(self, document: Document):
        """Adds or updates a document node in the graph."""
        # Placeholder implementation
        logger.info(f"[Placeholder] Adding/updating document {document.id}")
        # In a real implementation, you'd use MERGE/SET like add_entity
        # Ensure you handle document properties and timestamps correctly
        # MERGE (d:Document {id: $id}) SET d = $properties_map
        # await self._driver.execute_query(query, params)
        await self.add_entity(document)  # Reuse add_entity for now

    async def add_chunk(self, chunk: Chunk):
        """Adds or updates a chunk node and links it to its document."""
        # Placeholder implementation
        logger.info(
            f"[Placeholder] Adding/updating chunk {chunk.id} for document {chunk.document_id}"
        )
        # In a real implementation:
        # 1. Add/Update the chunk node (MERGE (c:Chunk {id: $id}) SET c = $chunk_props)
        # 2. Find the document node (MATCH (d:Document {id: $doc_id}))
        # 3. Create the relationship (MERGE (d)-[:HAS_CHUNK]->(c))
        # Ensure transactional consistency
        await self.add_entity(chunk)  # Reuse add_entity for the node for now
        # Add relationship logic (placeholder)
        query = """
        MATCH (d:Document {id: $doc_id})
        MATCH (c:Chunk {id: $chunk_id})
        MERGE (d)-[:HAS_CHUNK]->(c)
        """
        params = {"doc_id": chunk.document_id, "chunk_id": chunk.id}
        try:
            await self._driver.execute_query(query, params)
            logger.debug(f"Linked chunk {chunk.id} to document {chunk.document_id}")
        except Exception as e:
            logger.error(
                f"Failed to link chunk {chunk.id} to document {chunk.document_id}: {e}",
                exc_info=True,
            )
            # Decide if this should raise an error

    async def get_document_by_id(self, document_id: str) -> Document | None:
        """Retrieves a document by its ID."""
        # Placeholder implementation
        logger.info(f"[Placeholder] Getting document by ID {document_id}")
        # Real implementation would query the graph:
        # query = "MATCH (d:Document {id: $id}) RETURN d"
        # result, _, _ = await self._driver.execute_query(query, {"id": document_id})
        # if result and result[0]:
        #     node_data = result[0]['d']
        #     # Map node_data to Document object (similar to _map_node_to_entity)
        #     # return Document(...)
        # return None
        entity = await self.get_entity_by_id(document_id)
        if entity and isinstance(entity, Document):
            return entity
        elif entity:
            logger.warning(
                f"Found entity {document_id}, but it is not a Document instance (type: {type(entity)})"
            )
        return None  # Return None if not found or not a Document

    async def keyword_search(
        self, query: str, limit: int = 10
    ) -> list["SearchResultData"]:
        """Performs keyword search across chunk text content using case-insensitive CONTAINS."""
        # Simple keyword search using Cypher CONTAINS for case-insensitive text matching
        # This could be enhanced with full-text indexing in production
        query_lower = query.lower()

        # Use toLower() instead of (?i) for Memgraph compatibility
        cypher_query = """
        MATCH (c:Chunk)
        WHERE toLower(c.text) CONTAINS $query_lower
        RETURN c
        ORDER BY size(c.text) ASC
        LIMIT $limit
        """

        params = {"query_lower": query_lower, "limit": limit}

        try:
            result, _, _ = await self._driver.execute_query(cypher_query, params)
            search_results = []

            for record in result:
                chunk_node = record["c"]

                # Extract properties from the node
                if hasattr(chunk_node, "properties"):
                    props = chunk_node.properties

                    # Create ChunkData from node properties
                    chunk_data = ChunkData(
                        id=props.get("id", ""),
                        text=props.get("text", ""),
                        document_id=props.get("document_id", ""),
                        metadata=props.get("metadata", {}),
                        embedding=props.get("embedding"),
                    )

                    # Calculate simple score based on keyword matches
                    # This is a basic scoring - could be enhanced with TF-IDF or BM25
                    text_lower = chunk_data.text.lower()
                    score = text_lower.count(query_lower) / max(len(text_lower.split()), 1)

                    search_result = SearchResultData(
                        chunk=chunk_data,
                        score=score
                    )
                    search_results.append(search_result)

            logger.debug(f"Keyword search for '{query}' returned {len(search_results)} results")
            return search_results

        except Exception as e:
            logger.error(f"Error performing keyword search for '{query}': {e}", exc_info=True)
            return []

    # === Helper Methods ===
