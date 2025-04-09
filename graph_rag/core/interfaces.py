from typing import Protocol, List, Dict, Any, Tuple, AsyncGenerator
from pydantic import BaseModel

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

class EntityExtractor(Protocol):
    """Interface for extracting entities and relationships from text."""
    
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

class KeywordSearcher(Protocol):
    """Interface for keyword-based search."""
    async def search_chunks_by_keyword(self, query: str, limit: int = 10) -> List[SearchResultData]:
        ...
        
class GraphSearcher(Protocol):
    """Interface for graph traversal based search/retrieval."""
    async def find_related_chunks(self, entity_id: str, limit: int = 10) -> List[SearchResultData]:
        # Example: Find chunks mentioning a specific entity
        ...

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