from typing import List, Dict, Any, Optional
from neo4j import AsyncGraphDatabase
from graph_rag.core.interfaces import KnowledgeGraphBuilder, DocumentData, ChunkData, ExtractedEntity, ExtractedRelationship
from abc import ABC, abstractmethod

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
    """Repository for interacting with the Neo4j graph database."""
    
    def __init__(self, uri: str, user: str, password: str):
        self.driver = AsyncGraphDatabase.driver(uri, auth=(user, password))
    
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
    
    async def close(self) -> None:
        """Closes the database connection."""
        await self.driver.close()

    async def execute_read(self, query: str, params: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """Executes a read-only query and returns the results as a list of dictionaries."""
        if params is None:
            params = {}
            
        async with self.driver.session() as session:
            result = await session.run(query, params)
            records = await result.data()
            return records 