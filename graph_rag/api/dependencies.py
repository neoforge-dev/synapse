import logging
from typing import AsyncGenerator, Annotated, Optional, List, Dict, Any

from fastapi import Depends, HTTPException, status, Request
# Remove if unused
# from fastapi.security import APIKeyHeader

# Configuration
from graph_rag.config import get_settings, Settings

# Core Interfaces and Engine
from graph_rag.core.interfaces import (
    GraphRepository, VectorStore, EntityExtractor, DocumentProcessor,
    KnowledgeGraphBuilder, VectorSearcher, KeywordSearcher, GraphSearcher,
    EmbeddingService, GraphRAGEngine
)
from graph_rag.core.graph_rag_engine import GraphRAGEngine as ConcreteGraphRAGEngine
from graph_rag.llm.protocols import LLMService
from graph_rag.infrastructure.cache.protocols import CacheService

# Concrete Implementations (adjust paths as needed)
from graph_rag.infrastructure.graph_stores.memgraph_store import MemgraphGraphRepository
from graph_rag.infrastructure.vector_stores import SimpleVectorStore
from graph_rag.services.embedding import SentenceTransformerEmbeddingService
from graph_rag.core.document_processor import SimpleDocumentProcessor
from graph_rag.core.entity_extractor import SpacyEntityExtractor
from graph_rag.core.knowledge_graph_builder import SimpleKnowledgeGraphBuilder
from graph_rag.core.persistent_kg_builder import PersistentKnowledgeGraphBuilder
# Service Import
from graph_rag.services.ingestion import IngestionService
from graph_rag.services.search import SearchService
# Remove QueryEngine import
# from graph_rag.core.query_engine import QueryEngine

# Import cache implementations
from graph_rag.infrastructure.cache.memory_cache import MemoryCache

# Import MockLLMService
from graph_rag.llm import MockLLMService

# Initialize settings once
settings = get_settings()

logger = logging.getLogger(__name__)

# Use a dictionary to store singletons
_singletons: Dict[str, Any] = {}

# --- Singleton Instances (cached at application level if possible) ---
_embedding_service_instance: Optional[EmbeddingService] = None
_llm_service_instance: Optional[LLMService] = None
_graph_repository_instance: Optional[MemgraphGraphRepository] = None
_vector_store_instance: Optional[VectorStore] = None
_document_processor_instance: Optional[DocumentProcessor] = None
_entity_extractor_instance: Optional[EntityExtractor] = None
_cache_service_instance: Optional[CacheService] = None

def get_cache_service(settings: Settings = Depends(get_settings)) -> CacheService:
    global _cache_service_instance
    if _cache_service_instance is None:
        logger.info(f"Creating CacheService instance (type: {settings.cache_type})")
        if settings.cache_type == "memory":
            _cache_service_instance = MemoryCache()
        # elif settings.cache_type == "redis":
        #     _cache_service_instance = RedisCache(host=settings.redis_host, port=settings.redis_port)
        else:
            logger.warning(f"Unsupported cache type '{settings.cache_type}', falling back to MemoryCache.")
            _cache_service_instance = MemoryCache()
    return _cache_service_instance

# --- Factory Functions --- 

# These create instances when needed, potentially using settings or other dependencies.

def create_graph_repository(settings: Settings) -> MemgraphGraphRepository:
    """Provides a MemgraphGraphRepository instance. Expects resolved settings."""
    logger.debug(f"Creating MemgraphGraphRepository instance for {settings.MEMGRAPH_HOST}:{settings.MEMGRAPH_PORT}")
    from graph_rag.infrastructure.graph_stores.memgraph_store import MemgraphConnectionConfig
    config = MemgraphConnectionConfig(settings)
    repo = MemgraphGraphRepository(
        config=config
    )
    return repo

def create_llm_service(settings: Settings) -> LLMService: # Remove Depends
    """Creates an LLMService instance based on settings. Expects resolved settings."""
    try:
        llm_type = settings.LLM_TYPE.lower()
        logger.info(f"Creating LLMService instance of type: {llm_type}")
        if llm_type == "openai":
            # Ensure API key is handled securely
            api_key = settings.OPENAI_API_KEY.get_secret_value() if settings.OPENAI_API_KEY else None
            if not api_key:
                logger.error("OpenAI API key is not configured.")
                raise HTTPException(status_code=503, detail="LLM Service (OpenAI) not configured: API key missing.")
            instance = SentenceTransformerEmbeddingService(api_key=api_key, model_name=settings.LLM_MODEL_NAME)
        elif llm_type == "mock":
            instance = MockLLMService()
        else:
            logger.warning(f"Unsupported LLM_TYPE '{settings.LLM_TYPE}'. Falling back to MockLLMService.")
            instance = MockLLMService()
    except AttributeError:
        # If LLM_TYPE is not defined in settings, use mock service
        logger.warning("LLM_TYPE not found in settings. Falling back to MockLLMService.")
        instance = MockLLMService()
        
    return instance

def create_vector_store(settings: Settings) -> VectorStore: # Remove Depends
    """Factory function to create a VectorStore instance based on settings."""
    vector_store_type = settings.vector_store_type.lower()
    
    if vector_store_type == 'simple':
        # Use the direct constructor with the embedding model name
        return SimpleVectorStore(embedding_model_name=settings.vector_store_embedding_model)
    else:
        logger.warning(f"Unsupported vector_store_type '{settings.vector_store_type}'. Using SimpleVectorStore.")
        return SimpleVectorStore(embedding_model_name=settings.vector_store_embedding_model)

def create_document_processor() -> DocumentProcessor:
    global _document_processor_instance
    if _document_processor_instance is None:
        logger.info("Creating DocumentProcessor instance (SimpleDocumentProcessor)")
        # Configure based on settings if needed
        _document_processor_instance = SimpleDocumentProcessor()
    return _document_processor_instance

def create_entity_extractor(settings: Settings) -> EntityExtractor: # Remove Depends
    """Creates an EntityExtractor instance based on settings. Expects resolved settings."""
    # global _entity_extractor_instance
    # if _entity_extractor_instance is None:
    extractor_type = settings.entity_extractor_type.lower()
    logger.info(f"Creating EntityExtractor instance of type: {extractor_type}")
    if extractor_type == 'spacy':
        instance = SpacyEntityExtractor(model_name=settings.entity_extractor_model)
    elif extractor_type == 'mock':
        instance = MockEntityExtractor()
    else:
        logger.warning(f"Unsupported entity_extractor_type '{settings.entity_extractor_type}'. Falling back to MockEntityExtractor.")
        instance = MockEntityExtractor()
    # _entity_extractor_instance = instance
    return instance
    # return _entity_extractor_instance

def create_kg_builder(
    graph_repo: MemgraphGraphRepository = Depends(create_graph_repository),
    entity_extractor: EntityExtractor = Depends(create_entity_extractor)
) -> KnowledgeGraphBuilder:
    logger.debug("Creating KnowledgeGraphBuilder instance")
    return KnowledgeGraphBuilder(graph_repo=graph_repo, entity_extractor=entity_extractor)

def create_search_service(
    graph_repo: MemgraphGraphRepository,
    vector_store: VectorStore
) -> SearchService:
    logger.debug("Creating SearchService instance")
    return SearchService(
        graph_repo=graph_repo,
        vector_store=vector_store
    )

def create_graph_rag_engine(
    llm_service: LLMService,
    embedding_service: EmbeddingService,
    graph_repository: MemgraphGraphRepository,
    vector_store: VectorStore,
    cache_service: CacheService,
    settings: Settings = Depends(get_settings)
) -> ConcreteGraphRAGEngine:
    logger.debug("Creating GraphRAGEngine instance")
    return ConcreteGraphRAGEngine(
        llm_service=llm_service,
        embedding_service=embedding_service,
        graph_repository=graph_repository,
        vector_store=vector_store,
        cache_service=cache_service,
        graph_context_tokens=settings.graph_context_max_tokens,
        vector_similarity_threshold=settings.vector_similarity_threshold,
        max_vector_results=settings.max_vector_results
    )

def create_ingestion_service(
    doc_processor: DocumentProcessor,
    entity_extractor: EntityExtractor,
    graph_repo: MemgraphGraphRepository,
    vector_store: VectorStore,
    embedding_service: EmbeddingService
) -> IngestionService:
    logger.debug("Creating IngestionService instance")
    # Get a chunk splitter from the document processor
    chunk_splitter = doc_processor.chunk_splitter
    
    return IngestionService(
        document_processor=doc_processor,
        entity_extractor=entity_extractor,
        graph_store=graph_repo,
        embedding_service=embedding_service,
        chunk_splitter=chunk_splitter
    )

def create_knowledge_graph_builder(
    graph_repo: MemgraphGraphRepository = Depends(create_graph_repository),
    # entity_extractor: EntityExtractor = Depends(create_entity_extractor), # Not needed for SimpleKGB constructor
    # embedding_service: EmbeddingService = Depends(create_embedding_service) # Not needed for SimpleKGB constructor
) -> KnowledgeGraphBuilder:
     logger.debug("Creating SimpleKnowledgeGraphBuilder instance")
     # Instantiate with only the graph_store/graph_repository
     return SimpleKnowledgeGraphBuilder(
         graph_store=graph_repo
         # entity_extractor=entity_extractor, # Removed
         # embedding_service=embedding_service # Removed
     )

# --- FastAPI Dependency Provider Async Functions (DEFINED BEFORE USAGE) ---
# These use the factory functions or return cached singletons.

async def get_graph_repository(settings: Settings = Depends(get_settings)) -> MemgraphGraphRepository:
    """Dependency getter for GraphRepository, using singleton pattern."""
    if "graph_repository" not in _singletons:
        # Pass the resolved settings object to the creation function
        _singletons["graph_repository"] = create_graph_repository(settings=settings)
    return _singletons["graph_repository"]

async def get_embedding_service() -> EmbeddingService:
    """Dependency getter for EmbeddingService, using singleton pattern."""
    if "embedding_service" not in _singletons:
        # Create a mock embedding service for now
        from graph_rag.services.embedding import SentenceTransformerEmbeddingService
        logger.info("Creating EmbeddingService instance (SentenceTransformerEmbeddingService)")
        # Reuse the setting for vector store embedding model
        settings_obj = get_settings()
        _singletons["embedding_service"] = SentenceTransformerEmbeddingService(
            model_name=settings_obj.vector_store_embedding_model
        )
    return _singletons["embedding_service"]

async def get_vector_store(settings: Settings = Depends(get_settings)) -> VectorStore:
    """Dependency getter for VectorStore, using singleton pattern."""
    if "vector_store" not in _singletons:
        _singletons["vector_store"] = create_vector_store(settings=settings)
    return _singletons["vector_store"]

async def get_entity_extractor(settings: Settings = Depends(get_settings)) -> EntityExtractor:
    """Dependency getter for EntityExtractor, using singleton pattern."""
    if "entity_extractor" not in _singletons:
        _singletons["entity_extractor"] = create_entity_extractor(settings=settings)
    return _singletons["entity_extractor"]

async def get_document_processor() -> DocumentProcessor:
    if "document_processor" not in _singletons:
        _singletons["document_processor"] = create_document_processor()
    return _singletons["document_processor"]

async def get_llm_service(settings: Settings = Depends(get_settings)) -> LLMService:
    """Dependency getter for LLMService, using singleton pattern."""
    if "llm_service" not in _singletons:
        _singletons["llm_service"] = create_llm_service(settings=settings)
    return _singletons["llm_service"]

async def get_kg_builder(
    entity_extractor: EntityExtractor = Depends(get_entity_extractor),
    embedding_service: EmbeddingService = Depends(get_embedding_service),
    graph_repo: MemgraphGraphRepository = Depends(get_graph_repository)
) -> KnowledgeGraphBuilder:
    """DEPRECATED: Use get_knowledge_graph_builder instead for consistency."""
    import warnings
    warnings.warn(
        "get_kg_builder is deprecated and will be removed in a future version. "
        "Please use get_knowledge_graph_builder instead.",
        DeprecationWarning,
        stacklevel=2
    )
    logger.debug("Creating PersistentKnowledgeGraphBuilder instance")
    return PersistentKnowledgeGraphBuilder(
        graph_repository=graph_repo,
        entity_extractor=entity_extractor,
        embedding_service=embedding_service
    )

async def get_search_service(
    graph_repo: MemgraphGraphRepository = Depends(get_graph_repository),
    vector_store: VectorStore = Depends(get_vector_store)
) -> SearchService:
    if "search_service" not in _singletons:
        _singletons["search_service"] = create_search_service(graph_repo, vector_store)
    return _singletons["search_service"]

async def get_graph_rag_engine(
    llm_service: LLMService = Depends(get_llm_service),
    embedding_service: EmbeddingService = Depends(get_embedding_service),
    graph_repository: GraphRepository = Depends(get_graph_repository),
    vector_store: VectorStore = Depends(get_vector_store),
    cache_service: CacheService = Depends(get_cache_service),
    settings: Settings = Depends(get_settings)
) -> ConcreteGraphRAGEngine:
    if "graph_rag_engine" not in _singletons:
        _singletons["graph_rag_engine"] = create_graph_rag_engine(
            llm_service=llm_service,
            embedding_service=embedding_service,
            graph_repository=graph_repository,
            vector_store=vector_store,
            cache_service=cache_service,
            settings=settings
        )
    return _singletons["graph_rag_engine"]

async def get_ingestion_service(
    doc_processor: DocumentProcessor = Depends(get_document_processor),
    entity_extractor: EntityExtractor = Depends(get_entity_extractor),
    graph_repo: GraphRepository = Depends(get_graph_repository),
    vector_store: VectorStore = Depends(get_vector_store),
    embedding_service: EmbeddingService = Depends(get_embedding_service),
) -> IngestionService:
    logger.warning("Ingestion service not found in app state, creating new instance.")
    return create_ingestion_service(
        doc_processor=doc_processor,
        entity_extractor=entity_extractor,
        graph_repo=graph_repo,
        vector_store=vector_store,
        embedding_service=embedding_service
    )

async def get_knowledge_graph_builder(
    graph_repo: MemgraphGraphRepository = Depends(get_graph_repository),
    # If this is meant to be the Simple one, use its factory
) -> KnowledgeGraphBuilder:
    if "simple_kg_builder" not in _singletons:
         _singletons["simple_kg_builder"] = create_knowledge_graph_builder(graph_repo=graph_repo)
    return _singletons["simple_kg_builder"]

# --- Annotated Dependencies (USING ABOVE PROVIDERS) ---

GraphRepositoryDep = Annotated[GraphRepository, Depends(get_graph_repository)]
VectorStoreDep = Annotated[VectorStore, Depends(get_vector_store)]
EmbeddingServiceDep = Annotated[EmbeddingService, Depends(get_embedding_service)]
EntityExtractorDep = Annotated[EntityExtractor, Depends(get_entity_extractor)]
DocumentProcessorDep = Annotated[DocumentProcessor, Depends(get_document_processor)]
LLMServiceDep = Annotated[LLMService, Depends(get_llm_service)]
KnowledgeGraphBuilderDep = Annotated[KnowledgeGraphBuilder, Depends(get_knowledge_graph_builder)]
CacheServiceDep = Annotated[CacheService, Depends(get_cache_service)]
IngestionServiceDep = Annotated[IngestionService, Depends(get_ingestion_service)]
SearchServiceDep = Annotated[SearchService, Depends(get_search_service)]
GraphRAGEngineDep = Annotated[GraphRAGEngine, Depends(get_graph_rag_engine)]

# Assuming VectorStore implements VectorSearcher, GraphStore implements Graph/KeywordSearcher
# These should ideally point to the async providers if using singletons
VectorSearcherDep = Annotated[VectorSearcher, Depends(get_vector_store)]
KeywordSearcherDep = Annotated[KeywordSearcher, Depends(get_graph_repository)] 
GraphSearcherDep = Annotated[GraphSearcher, Depends(get_graph_repository)]


# --- Old Provider Functions (Removed as they are defined above now) ---
# async def get_graph_repository() -> MemgraphRepository:
# async def get_embedding_service() -> EmbeddingService:
# async def get_vector_store() -> VectorStore:
# async def get_entity_extractor() -> EntityExtractor:
# async def get_document_processor() -> DocumentProcessor:
# async def get_kg_builder(...): # This one seems duplicated/confusing
# async def get_search_service(...):
# async def get_graph_rag_engine(...):
# async def get_ingestion_service(...):
# async def get_knowledge_graph_builder(...):


# Remove QueryEngine provider
# async def get_query_engine(...):
#     ...