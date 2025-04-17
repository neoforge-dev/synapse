from typing import Protocol, List, Dict, Any, Tuple, AsyncGenerator, Optional, runtime_checkable
from pydantic import BaseModel, Field

# Use TYPE_CHECKING to avoid runtime circular imports
# Using string forward references instead now
# from typing import TYPE_CHECKING
# if TYPE_CHECKING:
#     from graph_rag.domain.models import Document, ProcessedDocument

# --- Data Structures ---

class ChunkData(BaseModel):
    id: str
    text: str
    document_id: str
    embedding: Optional[List[float]] = None
    # Add other relevant chunk metadata if needed

class DocumentData(BaseModel):
    id: str
    content: str
    metadata: Dict[str, Any]

class ExtractedEntity(BaseModel):
    id: str # e.g., normalized name or unique ID
    label: str # e.g., PER, ORG, LOC
    text: str # The original text span
    name: Optional[str] = None # Display name, defaults to text if not provided
    # Add confidence scores or other relevant info if needed

class ExtractedRelationship(BaseModel):
    source_entity_id: str
    target_entity_id: str
    label: str # e.g., WORKS_AT, LOCATED_IN
    # Add confidence scores or other relevant info if needed

class ExtractionResult(BaseModel):
    entities: List[ExtractedEntity]
    relationships: List[ExtractedRelationship]

class SearchResultData(BaseModel):
    chunk: ChunkData
    score: float
    document: Optional[DocumentData] = None # Optionally include parent doc info


# --- Component Interfaces ---

class DocumentProcessor(Protocol):
    """Interface for processing documents into chunks."""
    
    async def chunk_document(self, doc: DocumentData) -> List[ChunkData]:
        """Splits a document into manageable chunks."""
        ...

@runtime_checkable
class EntityExtractor(Protocol):
    """Protocol for extracting entities and relationships from text or documents."""

    # Use string forward reference for Document and ProcessedDocument
    def extract(self, document: 'Document') -> 'ProcessedDocument':
        """Extracts entities and relationships from an entire document object.

        Deprecated: Prefer extract_from_text or process documents chunk by chunk.
        Processes all chunks within the document.
        """
        ...

    async def extract_from_text(self, text: str, context: Optional[Dict[str, Any]] = None) -> ExtractionResult:
        """Extracts entities and relationships from a single text string.

        Args:
            text: The input text string.
            context: Optional context dictionary (e.g., chunk_id, doc_id).

        Returns:
            An ExtractionResult containing lists of extracted entities and relationships.
        """
        ...

class KnowledgeExtractor(Protocol):
    """Interface for extracting knowledge from text."""
    
    async def extract(self, text: str) -> ExtractionResult:
        """Extracts entities and relationships from a given text block."""
        ...

class KnowledgeGraphBuilder(Protocol):
    """Interface for building and updating the knowledge graph."""
    
    async def add_document(self, doc: DocumentData) -> None:
        """Adds a document node to the graph."""
        ...
        
    async def add_chunk(self, chunk: ChunkData) -> None:
        """Adds a chunk node and links it to its document."""
        ...
        
    async def add_entity(self, entity: ExtractedEntity) -> None:
        """Adds or updates an entity node in the graph."""
        ...
        
    async def add_relationship(self, relationship: ExtractedRelationship) -> None:
        """Adds a relationship edge between two entities."""
        ...
        
    async def link_chunk_to_entities(self, chunk_id: str, entity_ids: List[str]) -> None:
        """Creates relationships (e.g., MENTIONS) between a chunk and entities."""
        ...

# Note: For RAG engine, defining a clear interface is harder without knowing the exact inputs/outputs
# Let's define potential search/retrieval interfaces it might *use*.

class VectorSearcher(Protocol):
    """Interface for vector similarity search."""
    async def search_similar_chunks(self, query_vector: List[float], limit: int = 10) -> List[SearchResultData]:
        ...

class EmbeddingService(Protocol):
    """Interface for generating embeddings from text."""
    async def generate_embedding(self, text: str) -> List[float]:
        """Generates a vector embedding for the given text."""
        ...

class KeywordSearcher(Protocol):
    """Interface for keyword-based search."""
    async def search_chunks_by_keyword(self, query: str, limit: int = 10) -> List[SearchResultData]:
        ...

class VectorStore(Protocol):
    """Interface defining operations for interacting with a vector store."""
    
    async def add_chunks(self, chunks: List['ChunkData']) -> None:
        """Adds or updates chunk data and their embeddings."""
        ...
        
    async def search_similar_chunks(self, query_vector: List[float], limit: int = 10, threshold: Optional[float] = None) -> List['SearchResultData']:
        """Searches for chunks with embeddings similar to the query vector."""
        ...
        
    async def get_chunk_by_id(self, chunk_id: str) -> Optional['ChunkData']:
        """Retrieves a chunk by its ID (optional method)."""
        ...
        
    async def delete_chunks(self, chunk_ids: List[str]) -> None:
        """Deletes chunks by their IDs (optional method)."""
        ...

    async def delete_store(self) -> None:
        """Deletes the entire vector store collection (optional method)."""
        ...

class GraphSearcher(Protocol):
    """Interface for graph traversal based search/retrieval."""
    async def find_related_chunks(self, entity_id: str, limit: int = 10) -> List[SearchResultData]:
        # Example: Find chunks mentioning a specific entity
        ...

class GraphRepository(Protocol):
    """Interface defining operations for interacting with the graph store."""
    
    async def execute_query(self, query: str, params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Executes a raw Cypher query and returns results."""
        ...

    async def add_document(self, document: 'Document') -> None:
        """Adds or updates a document node."""
        ...
        
    async def get_document_by_id(self, document_id: str) -> Optional['Document']:
        """Retrieves a document by its ID."""
        ...
        
    async def add_chunk(self, chunk: 'Chunk') -> None:
        """Adds or updates a chunk node and links it to its document."""
        ...

    async def add_chunks(self, chunks: List['Chunk']) -> None:
        """Adds or updates multiple chunk nodes."""
        ...
        
    async def get_chunk_by_id(self, chunk_id: str) -> Optional['Chunk']:
        """Retrieves a chunk by its ID."""
        ...
        
    async def add_entity(self, entity: 'Entity') -> None:
        """Adds or updates an entity node."""
        ...
        
    async def add_relationship(self, relationship: 'Relationship') -> None:
        """Adds or updates a relationship edge between nodes."""
        ...
        
    async def get_neighbors(self, node_id: str, relationship_type: Optional[str] = None, direction: str = "out") -> List[Dict]:
        """Retrieves neighbor nodes for a given node."""
        ...
        
    async def update_node_properties(self, node_id: str, properties: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Updates properties of an existing node."""
        ...
        
    async def delete_document(self, document_id: str) -> bool:
        """Deletes a document and its associated chunks/relationships."""
        ...

    async def close(self) -> None:
        """Closes any open connections or resources."""
        ...

    # Add other necessary graph operations as needed...

class GraphRAGEngine(Protocol):
    """Orchestrates the GraphRAG process."""
    
    async def process_and_store_document(self, doc_content: str, metadata: Dict[str, Any]) -> None:
        """Full pipeline: chunk, extract entities, build graph."""
        ...
        
    async def retrieve_context(self, query: str, search_type: str = 'vector', limit: int = 5) -> List[SearchResultData]:
        """Retrieve relevant context chunks for a query."""
        ...
        
    async def answer_query(self, query: str) -> str:
        """Retrieve context and generate an answer (Requires LLM integration - Placeholder)."""
        ...

# Forward references need types defined or imported if not using strings
# from graph_rag.models import Document, Chunk, Entity, Relationship 
# This might cause circular imports, using string hints is safer here. 