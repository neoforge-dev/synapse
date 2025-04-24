import logging
from typing import AsyncGenerator, Annotated, Optional, List, Dict, Any, Tuple
import asyncio
from functools import lru_cache

from fastapi import Depends, HTTPException, status, Request
# Remove if unused
# from fastapi.security import APIKeyHeader

# Configuration
from graph_rag.config import get_settings, Settings

# Core Interfaces and Engine
from graph_rag.core.interfaces import (
    GraphRepository, VectorStore, EntityExtractor, DocumentProcessor,
    KnowledgeGraphBuilder, VectorSearcher, KeywordSearcher, GraphSearcher,
    EmbeddingService, GraphRAGEngine as AbstractGraphRAGEngine
)
# Import domain models
from graph_rag.domain.models import Entity, Relationship, Document, Chunk, Node

# Import SimpleGraphRAGEngine instead of the concrete GraphRAGEngine
from graph_rag.core.graph_rag_engine import SimpleGraphRAGEngine
from graph_rag.llm.protocols import LLMService
from graph_rag.infrastructure.cache.protocols import CacheService
from graph_rag.llm.loader import load_llm

# Concrete Implementations (adjust paths as needed)
from graph_rag.infrastructure.graph_stores.memgraph_store import MemgraphGraphRepository
from graph_rag.infrastructure.vector_stores import SimpleVectorStore
# Only import the existing service
from graph_rag.services.embedding import SentenceTransformerEmbeddingService
from graph_rag.core.document_processor import SimpleDocumentProcessor, ChunkSplitter
# Import MockEntityExtractor if needed for fallback
from graph_rag.core.entity_extractor import SpacyEntityExtractor, MockEntityExtractor
from graph_rag.core.knowledge_graph_builder import SimpleKnowledgeGraphBuilder
# Remove PersistentKnowledgeGraphBuilder import if not used elsewhere
# from graph_rag.core.persistent_kg_builder import PersistentKnowledgeGraphBuilder
# Service Import
from graph_rag.services.ingestion import IngestionService
from graph_rag.services.search import SearchService
# Remove QueryEngine import
# from graph_rag.core.query_engine import QueryEngine

# Import cache implementations
from graph_rag.infrastructure.cache.memory_cache import MemoryCache

# Import MockLLMService
from graph_rag.llm import MockLLMService

# Define a Mock Embedding Service
class MockEmbeddingService(EmbeddingService):
    """Minimal implementation of a mock EmbeddingService."""
    def __init__(self, dimension: int = 10): # Add dimension
        self.dimension = dimension
        logger.info(f"Minimal MockEmbeddingService initialized with dimension {dimension}")

    async def encode(self, texts: List[str], **kwargs) -> List[List[float]]:
        logger.warning(f"MockEmbeddingService.encode called for {len(texts)} texts. Returning dummy vectors.")
        # Return dummy embeddings of the specified dimension
        return [[0.0] * self.dimension for _ in texts]

    def get_embedding_dimension(self) -> int:
        """Returns the configured embedding dimension."""
        return self.dimension

# Define minimal OpenAILLMService to satisfy import and factory
class OpenAILLMService(LLMService):
    """Minimal implementation of OpenAILLMService for dependency resolution."""
    def __init__(self, api_key: str, model_name: str):
        self.api_key = api_key
        self.model_name = model_name
        # Minimal initialization, actual OpenAI client setup would go here
        logger.info(f"Minimal OpenAILLMService initialized for model {model_name}")

    async def generate_response(self, prompt: str, **kwargs) -> str:
        logger.warning("OpenAILLMService.generate_response not implemented")
        # Actual implementation would call OpenAI API
        return f"Mock OpenAI response for: {prompt}"

    async def generate_response_stream(self, prompt: str, **kwargs) -> AsyncGenerator[str, None]:
        logger.warning("OpenAILLMService.generate_response_stream not implemented")
        yield f"Mock stream part 1 for: {prompt}"
        await asyncio.sleep(0.1) # Simulate async behavior
        yield " Mock stream part 2"
        # Actual implementation would stream from OpenAI API

    async def extract_entities_relationships(self, text: str, **kwargs) -> Tuple[List[Entity], List[Relationship]]:
        logger.warning("OpenAILLMService.extract_entities_relationships not implemented")
        # Actual implementation would use OpenAI functions/prompts for extraction
        return [], [] # Return empty lists

    async def embed_text(self, text: str, **kwargs) -> List[float]:
        logger.warning("OpenAILLMService.embed_text not implemented")
        # Actual implementation would call OpenAI embedding endpoint
        return [0.0] * 1536 # Return dummy embedding vector of expected size

    async def get_token_usage(self) -> Dict[str, int]:
        logger.warning("OpenAILLMService.get_token_usage not implemented")
        return {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}

# Initialize settings once
settings = get_settings()

logger = logging.getLogger(__name__)

# Use a dictionary to store singletons
_singletons: Dict[str, Any] = {}

# --- Singleton Instances (cached at application level if possible) ---
# Removed specific instance variables, relying on _singletons dictionary now
# _embedding_service_instance: Optional[EmbeddingService] = None
# _llm_service_instance: Optional[LLMService] = None
# _graph_repository_instance: Optional[MemgraphGraphRepository] = None
# _vector_store_instance: Optional[VectorStore] = None
# _document_processor_instance: Optional[DocumentProcessor] = None
# _entity_extractor_instance: Optional[EntityExtractor] = None
# _cache_service_instance: Optional[CacheService] = None

# --- Factory Functions ---

def get_cache_service(settings: Settings = Depends(get_settings)) -> CacheService:
    if "cache_service" not in _singletons:
        logger.info(f"Creating CacheService instance (type: {settings.cache_type})")
        if settings.cache_type == "memory":
            _singletons["cache_service"] = MemoryCache()
        # elif settings.cache_type == "redis":
        #     _cache_service_instance = RedisCache(host=settings.redis_host, port=settings.redis_port)
        else:
            logger.warning(f"Unsupported cache type '{settings.cache_type}', falling back to MemoryCache.")
            _singletons["cache_service"] = MemoryCache()
    return _singletons["cache_service"]


def create_graph_repository(settings: Settings) -> MemgraphGraphRepository:
    """Provides a MemgraphGraphRepository instance. Expects resolved settings."""
    logger.debug(f"Creating MemgraphGraphRepository instance for {settings.MEMGRAPH_HOST}:{settings.MEMGRAPH_PORT}")
    # Ensure MemgraphConnectionConfig is imported if used directly here
    # from graph_rag.infrastructure.graph_stores.memgraph_store import MemgraphConnectionConfig
    # config = MemgraphConnectionConfig(settings) # No longer need to create config here
    repo = MemgraphGraphRepository(
        settings_obj=settings # Pass the settings object directly
    )
    return repo

def create_llm_service(settings: Settings) -> LLMService: # Added factory function
    """Creates an LLMService instance based on settings. Expects resolved settings."""
    try:
        llm_type = settings.LLM_TYPE.lower()
        logger.info(f"Creating LLMService instance of type: {llm_type}")
        if llm_type == "openai":
            api_key = settings.OPENAI_API_KEY.get_secret_value() if settings.OPENAI_API_KEY else None
            if not api_key:
                logger.error("OpenAI API key is not configured.")
                raise HTTPException(status_code=503, detail="LLM Service (OpenAI) not configured: API key missing.")
            # Use OpenAILLMService
            instance = OpenAILLMService(api_key=api_key, model_name=settings.LLM_MODEL_NAME)
        elif llm_type == "mock":
            instance = MockLLMService()
        else:
            logger.warning(f"Unsupported LLM_TYPE '{settings.LLM_TYPE}'. Falling back to MockLLMService.")
            instance = MockLLMService()
    except AttributeError:
        logger.warning("LLM_TYPE not found in settings. Falling back to MockLLMService.")
        instance = MockLLMService()

    return instance

def create_vector_store(settings: Settings) -> VectorStore:
    """Factory function to create a VectorStore instance based on settings."""
    vector_store_type = settings.vector_store_type.lower()
    logger.info(f"Creating VectorStore instance (type: {vector_store_type})")

    # Get the (cached) embedding service instance first
    embedding_service = create_embedding_service(settings)

    if vector_store_type == 'simple':
        # Pass the embedding service instance, not the model name
        return SimpleVectorStore(embedding_service=embedding_service)
    # Add other vector store types here if needed
    # elif vector_store_type == 'qdrant':
    #    return QdrantVectorStore(...)
    else:
        logger.warning(f"Unsupported vector_store_type '{settings.vector_store_type}'. Falling back to SimpleVectorStore.")
        # Fallback still needs the embedding service instance
        return SimpleVectorStore(embedding_service=embedding_service)

def create_document_processor() -> DocumentProcessor:
    # Simplified singleton access
    if "document_processor" not in _singletons:
        logger.info("Creating DocumentProcessor instance (SimpleDocumentProcessor)")
        _singletons["document_processor"] = SimpleDocumentProcessor()
    return _singletons["document_processor"]

def create_entity_extractor(settings: Settings) -> EntityExtractor:
    """Creates an EntityExtractor instance based on settings. Expects resolved settings."""
    extractor_type = settings.entity_extractor_type.lower()
    logger.info(f"Creating EntityExtractor instance of type: {extractor_type}")
    if extractor_type == 'spacy':
        instance = SpacyEntityExtractor(model_name=settings.entity_extractor_model)
    elif extractor_type == 'mock':
        instance = MockEntityExtractor()
    else:
        logger.warning(f"Unsupported entity_extractor_type '{settings.entity_extractor_type}'. Falling back to MockEntityExtractor.")
        instance = MockEntityExtractor()
    return instance

@lru_cache(maxsize=1)
def get_settings() -> Settings:
    # TODO: Remove this check later
    settings = Settings()
    logger.info(f"Returning settings: {settings.model_dump()}")
    return settings

# Use a simple dictionary for caching within this module
_dependency_cache = {}

def create_embedding_service(
    settings: Settings, # No longer needs Depends here, pass settings directly
) -> EmbeddingService:
    """Create embedding service based on settings."""
    cache_key = "embedding_service"
    if cache_key in _dependency_cache:
        return _dependency_cache[cache_key]

    logger.debug("Attempting to create embedding service...")
    embedding_provider = settings.embedding_provider.lower() if hasattr(settings, 'embedding_provider') else 'mock' # Default to mock if unset
    # Get cache instance - needs a way to access it or pass it
    # For now, assume MemoryCache if not explicitly passed, adjust if cache is needed
    # cache = get_cache_service(settings) # This would require settings to be passed via Depends
    cache = MemoryCache() # Simplified for factory logic, reconsider if cache needs DI
    logger.info(f"Creating EmbeddingService instance (type: {embedding_provider})")

    if embedding_provider == "openai":
        logger.warning("OpenAI embedding provider selected, but using MockEmbeddingService as placeholder.")
        instance = MockEmbeddingService(dimension=settings.EMBEDDING_DIMENSION) # Use mock for now
    elif embedding_provider == "sentence-transformers":
        instance = SentenceTransformerEmbeddingService(
            model_name=settings.EMBEDDING_MODEL,
            cache=cache
        )
    elif embedding_provider == "mock":
        instance = MockEmbeddingService(dimension=settings.EMBEDDING_DIMENSION)
    else:
        logger.error(f"Unsupported embedding_provider configured: '{settings.embedding_provider}'.")
        raise ValueError(f"Unsupported embedding provider type: {settings.embedding_provider}")

    _dependency_cache[cache_key] = instance
    logger.info(f"Embedding service instance ({type(instance).__name__}) created and cached.")
    return instance

# Note: FastAPI's Depends uses the function itself as the key for caching within a request scope.
# We don't need Depends here if we are managing the cache ourselves via _dependency_cache,
# but the function signature is kept for clarity on what it provides.
def get_embedding_service_dependency(settings: Settings) -> EmbeddingService:
    """Callable dependency for FastAPI to get the embedding service."""
    # This function now acts as a simple wrapper around the cached creation logic
    # It relies on the module-level cache in _dependency_cache managed by create_embedding_service
    return create_embedding_service(settings)

def get_vector_store_dependency(settings: Settings) -> any:
    """Dependency to create and cache the vector store."""
    cache_key = "vector_store"
    if cache_key not in _dependency_cache:
        logger.info("Creating vector store instance...")
        vector_store_provider = settings.vector_store_provider.lower()
        logger.info(f"Using vector store provider: {vector_store_provider}")
        vector_store = get_vector_store(
            provider=vector_store_provider, settings=settings
        )
        _dependency_cache[cache_key] = vector_store
        logger.info("Vector store instance created and cached.")
    return _dependency_cache[cache_key]

# Factory function for KnowledgeGraphBuilder
def create_knowledge_graph_builder(
    graph_repo: MemgraphGraphRepository,
    entity_extractor: EntityExtractor
) -> SimpleKnowledgeGraphBuilder:
    logger.debug("Creating SimpleKnowledgeGraphBuilder instance")
    # Ensure we have the correct class name SimpleKnowledgeGraphBuilder
    return SimpleKnowledgeGraphBuilder(graph_store=graph_repo, entity_extractor=entity_extractor)

def create_search_service(
    graph_repo: MemgraphGraphRepository,
    vector_store: VectorStore
) -> SearchService:
    logger.debug("Creating SearchService instance")
    return SearchService(
        graph_repo=graph_repo,
        vector_store=vector_store
    )

# Modified to create SimpleGraphRAGEngine
def create_graph_rag_engine(
    graph_repository: MemgraphGraphRepository,
    vector_store: VectorStore,
    entity_extractor: EntityExtractor,
    llm_service: LLMService, # Added LLM service dependency
    settings: Settings # Keep settings for potential future use
) -> AbstractGraphRAGEngine:
    """Creates a SimpleGraphRAGEngine instance."""
    logger.debug("Creating SimpleGraphRAGEngine instance")
    return SimpleGraphRAGEngine(
        graph_store=graph_repository,
        vector_store=vector_store,
        entity_extractor=entity_extractor
    )

def create_ingestion_service(
    document_processor: DocumentProcessor,
    entity_extractor: EntityExtractor,
    graph_repo: MemgraphGraphRepository,
    embedding_service: EmbeddingService,
    vector_store: VectorStore  # Added vector_store argument
) -> IngestionService:
    logger.debug("Creating IngestionService instance")
    
    # Get chunk splitter from the document processor's property
    # try:
    #     chunk_splitter = document_processor.chunk_splitter
    #     if not isinstance(chunk_splitter, ChunkSplitter):
    #         raise TypeError(f"document_processor.chunk_splitter is not a ChunkSplitter instance, got {type(chunk_splitter)}")
    # except AttributeError:
    #     logger.error(f"DocumentProcessor of type {type(document_processor)} does not have a chunk_splitter property.")
    #     # Handle error appropriately, maybe raise an HTTPException or return a default/mock service
    #     # For now, raising an error to make the problem explicit
    #     raise ValueError("Configured DocumentProcessor lacks a required chunk_splitter property.")
    # Removed chunk_splitter logic above
    
    return IngestionService(
        document_processor=document_processor,
        entity_extractor=entity_extractor,
        graph_store=graph_repo,
        embedding_service=embedding_service,
        # Removed chunk_splitter=chunk_splitter,
        vector_store=vector_store  # Pass vector_store argument
    )

# --- FastAPI Dependency Provider Async Functions (DEFINED BEFORE USAGE) ---

async def get_settings_dep() -> Settings:
    """Dependency getter for settings."""
    # Ensures settings are loaded if not already
    return get_settings()

async def get_graph_repository(settings: Settings = Depends(get_settings_dep)) -> MemgraphGraphRepository:
    """Dependency getter for GraphRepository, using singleton pattern."""
    if "graph_repository" not in _singletons:
        _singletons["graph_repository"] = create_graph_repository(settings=settings)
    return _singletons["graph_repository"]

async def get_embedding_service(settings: Settings = Depends(get_settings_dep)) -> EmbeddingService:
    """Dependency getter for EmbeddingService, using singleton pattern."""
    # This relies on create_embedding_service handling the caching in _dependency_cache
    return create_embedding_service(settings=settings)

async def get_vector_store(settings: Settings = Depends(get_settings_dep)) -> VectorStore:
    """Provides a shared VectorStore instance, creating it if necessary."""
    cache_key = "vector_store"
    if cache_key not in _dependency_cache:
        logger.info("Creating and caching VectorStore instance.")
        # Call the updated factory function to create the instance
        _dependency_cache[cache_key] = create_vector_store(settings)
    # Return the cached instance
    return _dependency_cache[cache_key]

async def get_entity_extractor(settings: Settings = Depends(get_settings_dep)) -> EntityExtractor:
    """Provides an EntityExtractor instance."""
    # Assuming stateless or singleton not strictly required for tests here
    if "entity_extractor" not in _singletons:
        _singletons["entity_extractor"] = create_entity_extractor(settings=settings)
    return _singletons["entity_extractor"]

async def get_document_processor(settings: Settings = Depends(get_settings)) -> DocumentProcessor:
    # Factory function handles singleton logic internally now
    return create_document_processor()

async def get_llm(settings: Settings = Depends(get_settings_dep)) -> LLMService: # Added getter
    """Dependency getter for LLMService, using singleton pattern."""
    # Note: create_llm_service factory already exists, but we should use load_llm ideally.
    # Sticking to the pattern using create_llm_service for now.
    if "llm_service" not in _singletons:
        logger.info(f"Creating LLMService singleton via factory.")
        # Original logic used create_llm_service, let's keep it for consistency for now
        # Replace with load_llm(settings=settings) if loader logic is preferred directly
        _singletons["llm_service"] = create_llm_service(settings=settings)
    return _singletons["llm_service"]

# Added getter for SimpleGraphRAGEngine
async def get_graph_rag_engine(
    graph_repo: MemgraphGraphRepository = Depends(get_graph_repository),
    vector_store: VectorStore = Depends(get_vector_store),
    entity_extractor: EntityExtractor = Depends(get_entity_extractor),
    llm_service: LLMService = Depends(get_llm), # Add LLM dependency
    settings: Settings = Depends(get_settings_dep)
) -> AbstractGraphRAGEngine:
    """Dependency getter for the main Graph RAG Engine (SimpleGraphRAGEngine)."""
    # Engine is typically not a singleton unless state needs preservation across requests
    # Create a new instance per request or manage singleton if appropriate
    # For now, create per request using the factory
    return create_graph_rag_engine(
        graph_repository=graph_repo,
        vector_store=vector_store,
        entity_extractor=entity_extractor,
        llm_service=llm_service, # Pass LLM service
        settings=settings
    )

# Add the missing getter for KnowledgeGraphBuilder
async def get_knowledge_graph_builder(
    graph_repo: MemgraphGraphRepository = Depends(get_graph_repository),
    entity_extractor: EntityExtractor = Depends(get_entity_extractor),
) -> SimpleKnowledgeGraphBuilder:
    """Dependency getter for KnowledgeGraphBuilder."""
    # Typically create per request unless state needs preserving
    # Check if already in singletons if needed, otherwise create new
    if "kg_builder" not in _singletons:
        logger.info("Creating KnowledgeGraphBuilder singleton instance.")
        # Ensure the create_knowledge_graph_builder factory exists (added previously)
        _singletons["kg_builder"] = create_knowledge_graph_builder(
            graph_repo=graph_repo,
            entity_extractor=entity_extractor
        )
    return _singletons["kg_builder"]

# Optional: Add getter for IngestionService if needed by API endpoints
async def get_ingestion_service(
    doc_processor: DocumentProcessor = Depends(get_document_processor),
    entity_extractor: EntityExtractor = Depends(get_entity_extractor),
    graph_repo: MemgraphGraphRepository = Depends(get_graph_repository),
    embedding_service: EmbeddingService = Depends(get_embedding_service),
    vector_store: VectorStore = Depends(get_vector_store) # Added vector_store dependency
) -> IngestionService:
    """Dependency getter for IngestionService."""
    # Removed logic to get chunk_splitter separately
    return create_ingestion_service(
        document_processor=doc_processor,
        entity_extractor=entity_extractor,
        graph_repo=graph_repo,
        embedding_service=embedding_service,
        vector_store=vector_store # Pass vector_store dependency
        # Removed chunk_splitter argument
    )

# Optional: Add getter for SearchService if needed by API endpoints
async def get_search_service(
    graph_repo: MemgraphGraphRepository = Depends(get_graph_repository),
    vector_store: VectorStore = Depends(get_vector_store)
) -> SearchService:
     """Dependency getter for SearchService."""
     # Typically create per request
     return create_search_service(
         graph_repo=graph_repo,
         vector_store=vector_store
     )

# --- Authentication Dependencies (Example) ---
# Example API Key Auth (adjust as needed)
# api_key_header = APIKeyHeader(name="X-API-KEY", auto_error=False)

# async def get_api_key(
#     api_key: str = Security(api_key_header),
#     settings: Settings = Depends(get_settings)
# ) -> str:
#     if settings.API_KEY and api_key == settings.API_KEY.get_secret_value():
#         return api_key
#     else:
#         logger.warning("Invalid or missing API Key provided.")
#         raise HTTPException(
#             status_code=status.HTTP_401_UNAUTHORIZED,
#             detail="Invalid or missing API Key",
#         )


# --- Cleanup / Shutdown Logic ---
# Example: Ensure graph connection is closed on shutdown
async def close_graph_repository():
    if "graph_repository" in _singletons:
        repo = _singletons["graph_repository"]
        if isinstance(repo, MemgraphGraphRepository):
            logger.info("Closing Memgraph connection.")
            await repo.close() # Assuming close is async
        del _singletons["graph_repository"] # Remove from singletons

# Add other cleanup logic as needed (e.g., closing LLM connections)

# You might register these cleanup functions with FastAPI's lifespan events
# in your main application setup (e.g., main.py).