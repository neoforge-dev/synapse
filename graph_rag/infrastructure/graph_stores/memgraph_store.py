"""Optimized Memgraph graph store implementation."""

import logging
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
import asyncio
from dataclasses import asdict

from neo4j import AsyncGraphDatabase, AsyncDriver
from neo4j.exceptions import Neo4jError, ServiceUnavailable, AuthError
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from graph_rag.core.graph_store import GraphStore
from graph_rag.models import Document, Chunk, Entity, Relationship
from graph_rag.config import settings

logger = logging.getLogger(__name__)

# Define retryable exceptions
_RETRY_EXCEPTIONS = (Neo4jError, ServiceUnavailable, ConnectionError, AuthError)

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

    async def add_document(self, document: Document) -> None:
        """Adds a Document node to Memgraph with error handling."""
        try:
            query = """
            MERGE (d:Document {id: $id})
            ON CREATE SET d += $props, d.created_at = timestamp()
            ON MATCH SET d += $props, d.updated_at = timestamp()
            """
            props = {k: v for k, v in asdict(document).items() if k not in {"id", "chunks"}}
            await self._execute_write_query(query, {"id": document.id, "props": props})
            logger.debug(f"Added/Updated Document node: {document.id}")
        except Exception as e:
            logger.error(f"Failed to add document {document.id}: {e}")
            raise

    async def get_document_by_id(self, doc_id: str) -> Optional[Document]:
        """Retrieves a Document node by ID."""
        query = "MATCH (d:Document {id: $id}) RETURN d"
        results = await self._execute_read_query(query, {"id": doc_id})
        if results:
            node_data = results[0]["d"]
            return Document(**node_data)
        return None

    async def add_chunk(self, chunk: Chunk) -> None:
        """Adds a Chunk node and links it to its Document with error handling."""
        try:
            query = """
            MATCH (d:Document {id: $doc_id})
            MERGE (c:Chunk {id: $id})
            ON CREATE SET c += $props, c.created_at = timestamp()
            ON MATCH SET c += $props, c.updated_at = timestamp()
            MERGE (d)-[:CONTAINS]->(c)
            """
            props = {k: v for k, v in asdict(chunk).items() if k not in {"id", "document_id"}}
            await self._execute_write_query(
                query,
                {
                    "id": chunk.id,
                    "doc_id": chunk.document_id,
                    "props": props
                }
            )
            logger.debug(f"Added/Updated Chunk node: {chunk.id}")
        except Exception as e:
            logger.error(f"Failed to add chunk {chunk.id}: {e}")
            raise

    async def add_entity(self, entity: Entity) -> None:
        """Adds or updates an entity with error handling."""
        try:
            query = f"""
            MERGE (n:{entity.type} {{id: $id}})
            ON CREATE SET n += $props, n.created_at = timestamp()
            ON MATCH SET n += $props, n.updated_at = timestamp()
            """
            props = {k: v for k, v in asdict(entity).items() if k not in {"id", "type"}}
            await self._execute_write_query(query, {"id": entity.id, "props": props})
            logger.debug(f"Added/Updated Entity node: {entity.id}")
        except Exception as e:
            logger.error(f"Failed to add entity {entity.id}: {e}")
            raise

    async def add_relationship(self, relationship: Relationship) -> None:
        """Adds a relationship between entities with error handling."""
        try:
            query = f"""
            MATCH (source {{id: $source_id}}), (target {{id: $target_id}})
            MERGE (source)-[r:{relationship.type}]->(target)
            ON CREATE SET r += $props, r.created_at = timestamp()
            ON MATCH SET r += $props, r.updated_at = timestamp()
            """
            props = {k: v for k, v in asdict(relationship).items() if k not in {"source", "target", "type"}}
            await self._execute_write_query(
                query,
                {
                    "source_id": relationship.source.id,
                    "target_id": relationship.target.id,
                    "props": props
                }
            )
            logger.debug(f"Added/Updated relationship: {relationship.source.id} -[{relationship.type}]-> {relationship.target.id}")
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

        query = """
        UNWIND $entities AS entity
        MERGE (n:Entity {id: entity.id})
        ON CREATE SET n += entity.props, n.created_at = timestamp()
        ON MATCH SET n += entity.props, n.updated_at = timestamp()
        """
        
        entity_params = [
            {
                "id": e.id,
                "props": {k: v for k, v in asdict(e).items() if k not in {"id", "type"}}
            }
            for e in entities
        ]

        if relationships:
            query += """
            WITH n
            UNWIND $relationships AS rel
            MATCH (source {id: rel.source_id}), (target {id: rel.target_id})
            MERGE (source)-[r:RELATED_TO]->(target)
            ON CREATE SET r += rel.props, r.created_at = timestamp()
            ON MATCH SET r += rel.props, r.updated_at = timestamp()
            """
            
            rel_params = [
                {
                    "source_id": r.source.id,
                    "target_id": r.target.id,
                    "props": {k: v for k, v in asdict(r).items() if k not in {"source", "target", "type"}}
                }
                for r in relationships
            ]
        else:
            rel_params = []

        await self._execute_write_query(
            query,
            {
                "entities": entity_params,
                "relationships": rel_params
            }
        )
        logger.debug(f"Bulk added {len(entities)} entities and {len(relationships)} relationships")

    async def get_entity_by_id(self, entity_id: str) -> Optional[Entity]:
        """Retrieves a single entity by its unique ID with error handling."""
        try:
            query = "MATCH (n {id: $id}) RETURN n"
            results = await self._execute_read_query(query, {"id": entity_id})
            if results:
                node_data = results[0]["n"]
                return Entity(**node_data)
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
        for result in results:
            neighbor = Entity(**result["n"])
            source = Entity(**result["e"])
            rel = Relationship(
                source=source,
                target=neighbor,
                type=result["r"].type,
                **result["r"]
            )
            entities.append(neighbor)
            relationships.append(rel)
            
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
        return [Entity(**result["n"]) for result in results]

    async def __aenter__(self):
        """Context manager entry."""
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        await self.close()
