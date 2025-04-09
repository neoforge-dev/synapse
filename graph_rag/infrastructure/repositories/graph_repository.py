import logging
from typing import List, Dict, Any, Optional
from neo4j import AsyncGraphDatabase
from graph_rag.core.interfaces import KnowledgeGraphBuilder, DocumentData, ChunkData, ExtractedEntity, ExtractedRelationship
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)

class GraphRepository(ABC):
    """Abstract base class for graph repositories."""
    
    @abstractmethod
    async def add_document(self, document_id: str, content: str, metadata: Optional[Dict[str, Any]] = None) -> None:
        """Add a document to the graph."""
        pass
    
    @abstractmethod
    async def get_document_by_id(self, document_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve a document by its ID."""
        pass
    
    @abstractmethod
    async def execute_read_query(self, query: str, params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Execute a read query on the graph."""
        pass
    
    @abstractmethod
    async def execute_write_query(self, query: str, params: Optional[Dict[str, Any]] = None) -> None:
        """Execute a write query on the graph."""
        pass

class MemgraphRepository(GraphRepository, KnowledgeGraphBuilder):
    """Repository for interacting with the Memgraph graph database."""
    
    def __init__(self, uri: str, user: str, password: str):
        self.driver = AsyncGraphDatabase.driver(uri, auth=(user, password))
        logger.info(f"MemgraphRepository initialized with URI: {uri}")
    
    async def add_document(self, doc: DocumentData) -> None:
        """Adds a document node to the graph."""
        async with self.driver.session() as session:
            await session.run(
                """
                MERGE (d:Document {id: $id})
                SET d.content = $content,
                    d.metadata = $metadata
                """,
                id=doc.id,
                content=doc.content,
                metadata=doc.metadata
            )
    
    async def add_chunk(self, chunk: ChunkData) -> None:
        """Adds a chunk node and links it to its document."""
        async with self.driver.session() as session:
            await session.run(
                """
                MATCH (d:Document {id: $document_id})
                MERGE (c:Chunk {id: $id})
                SET c.text = $text,
                    c.embedding = $embedding
                MERGE (d)-[:CONTAINS]->(c)
                """,
                id=chunk.id,
                text=chunk.text,
                document_id=chunk.document_id,
                embedding=chunk.embedding
            )
    
    async def add_entity(self, entity: ExtractedEntity) -> None:
        """Adds or updates an entity node in the graph."""
        async with self.driver.session() as session:
            await session.run(
                """
                MERGE (e:Entity {id: $id})
                SET e.label = $label,
                    e.text = $text
                """,
                id=entity.id,
                label=entity.label,
                text=entity.text
            )
    
    async def add_relationship(self, relationship: ExtractedRelationship) -> None:
        """Adds a relationship edge between two entities."""
        async with self.driver.session() as session:
            await session.run(
                """
                MATCH (source:Entity {id: $source_id})
                MATCH (target:Entity {id: $target_id})
                MERGE (source)-[r:RELATIONSHIP {label: $label}]->(target)
                """,
                source_id=relationship.source_entity_id,
                target_id=relationship.target_entity_id,
                label=relationship.label
            )
    
    async def link_chunk_to_entities(self, chunk_id: str, entity_ids: List[str]) -> None:
        """Creates relationships (e.g., MENTIONS) between a chunk and entities."""
        async with self.driver.session() as session:
            for entity_id in entity_ids:
                await session.run(
                    """
                    MATCH (c:Chunk {id: $chunk_id})
                    MATCH (e:Entity {id: $entity_id})
                    MERGE (c)-[:MENTIONS]->(e)
                    """,
                    chunk_id=chunk_id,
                    entity_id=entity_id
                )
    
    async def get_context_for_entities(self, entity_texts: List[str]) -> Dict[str, Any]:
        """
        Retrieves context (entities, relationships, chunks) related to a list of entity texts.
        Finds entities containing any of the texts (case-insensitive) and chunks mentioning them.
        """
        if not entity_texts:
            return {"entities": [], "relationships": [], "chunks": []}

        # Build a case-insensitive matching clause for entity texts
        match_clauses = [f"toLower(e.text) CONTAINS toLower(${param_name})" for i, param_name in enumerate([f"text_{j}" for j in range(len(entity_texts))])]
        entity_match_clause = " OR ".join(match_clauses)
        
        params = {f"text_{i}": text for i, text in enumerate(entity_texts)}

        # Query to find entities matching the text and chunks mentioning them
        query = f"""
        MATCH (e:Entity)
        WHERE {entity_match_clause}
        OPTIONAL MATCH (c:Chunk)-[:MENTIONS]->(e)
        RETURN e as entity, collect(c) as chunks
        """
        
        logger.debug(f"Executing get_context_for_entities query: {{query}} with params: {{params}}")

        async with self.driver.session() as session:
            result = await session.run(query, params)
            records = await result.data()

        found_entities = []
        found_chunks_map = {}

        for record in records:
            entity_node = record.get('entity')
            chunk_nodes = record.get('chunks', [])

            if entity_node:
                # Convert Neo4j Node to dictionary
                entity_data = dict(entity_node.items())
                # Ensure required fields for API model exist, even if None
                entity_data.setdefault('id', None) 
                entity_data.setdefault('label', 'Unknown')
                entity_data.setdefault('text', 'Unknown')
                found_entities.append(entity_data)

            for chunk_node in chunk_nodes:
                if chunk_node:
                    # Convert Neo4j Node to dictionary
                    chunk_data = dict(chunk_node.items())
                    chunk_id = chunk_data.get('id')
                    if chunk_id and chunk_id not in found_chunks_map:
                         # Add default values if properties are missing
                        chunk_data.setdefault('text', '')
                        chunk_data.setdefault('document_id', 'unknown')
                        chunk_data.setdefault('metadata', {})
                        chunk_data.setdefault('score', None)
                        found_chunks_map[chunk_id] = chunk_data

        found_chunks = list(found_chunks_map.values())
        logger.info(f"Found {{len(found_entities)}} entities and {{len(found_chunks)}} unique chunks for texts: {{entity_texts}}")

        # Relationships are not explicitly queried in this basic version
        return {"entities": found_entities, "relationships": [], "chunks": found_chunks}
    
    async def close(self) -> None:
        """Closes the database connection."""
        logger.info("Closing Memgraph connection.")
        await self.driver.close()

    async def execute_query(self, query: str, params: Optional[Dict[str, Any]] = None, write: bool = False) -> List[Dict[str, Any]]:
        """Executes a query and returns results if it's a read query."""
        if params is None:
            params = {}
        
        async with self.driver.session() as session:
            if write:
                 await session.run(query, params)
                 return []
            else:
                 result = await session.run(query, params)
                 return await result.data()

    async def get_document_by_id(self, document_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve a document by its ID."""
        logger.debug(f"Attempting to retrieve document with id: {document_id}")
        query = "MATCH (d:Document {id: $doc_id}) RETURN d"
        results = await self.execute_query(query, params={"doc_id": document_id}, write=False)
        if results and results[0].get('d'):
             doc_node = results[0]['d']
             # Convert Neo4j Node to dictionary
             doc_data = dict(doc_node.items()) 
             # Ensure standard fields exist
             doc_data.setdefault('id', document_id)
             doc_data.setdefault('content', '')
             doc_data.setdefault('metadata', {})
             logger.debug(f"Found document: {doc_data}")
             return doc_data
        logger.warning(f"Document with id {document_id} not found.")
        return None

    async def execute_read_query(self, query: str, params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
         logger.debug(f"Executing read query: {{query}} with params {{params}}")
         return await self.execute_query(query, params, write=False)

    async def execute_write_query(self, query: str, params: Optional[Dict[str, Any]] = None) -> None:
         logger.debug(f"Executing write query: {{query}} with params {{params}}")
         await self.execute_query(query, params, write=True) 