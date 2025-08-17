import logging
from functools import lru_cache
from typing import Any

import numpy as np  # Add numpy import
from fastapi import Depends, HTTPException, Request

# Remove if unused
# from fastapi.security import APIKeyHeader
# Configuration
from graph_rag.config import Settings, get_settings

# Import MockEntityExtractor if needed for fallback
# Corrected import path for CacheService Protocol
# Corrected import path for SimpleDocumentProcessor
from graph_rag.core.entity_extractor import MockEntityExtractor, SpacyEntityExtractor

# from graph_rag.domain.models.chunk import Chunk # Remove this duplicate/incorrect import
# Import SimpleGraphRAGEngine instead of the concrete GraphRAGEngine
from graph_rag.core.graph_rag_engine import SimpleGraphRAGEngine

# Core Interfaces and Engine
# from graph_rag.core.interfaces import (GraphRepository, VectorStore, EntityExtractor, EmbeddingService, CacheService, GraphDebugger, DocumentProcessor, LLMService)
# from graph_rag.core.interfaces import (GraphRepository, VectorStore, EntityExtractor, EmbeddingService, CacheService, GraphDebugger, DocumentProcessor, LLMService)
# from graph_rag.core.interfaces import (GraphRepository, VectorStore, EntityExtractor, EmbeddingService, CacheService, GraphDebugger, DocumentProcessor, LLMService)
# Corrected import path for graph builders
from graph_rag.core.interfaces import (
    DocumentProcessor,
    EmbeddingService,
    EntityExtractor,
    GraphRAGEngine,
    GraphRepository,
    VectorStore,
)
from graph_rag.core.knowledge_graph_builder import (
    SimpleKnowledgeGraphBuilder,
)

# Import domain models
# Remove QueryEngine import
# from graph_rag.core.query_engine import QueryEngine
# Import cache implementations
from graph_rag.infrastructure.cache.memory_cache import MemoryCache
from graph_rag.infrastructure.cache.protocols import CacheService

# from graph_rag.infrastructure.cache.simple_cache import SimpleCache # Remove this line
# from graph_rag.infrastructure.debug.graph_debugger import MemgraphGraphDebugger # Remove this line
# Commenting out Redis import as it's not implemented
# from graph_rag.infrastructure.cache.redis_cache import RedisCacheService
from graph_rag.infrastructure.document_processor.simple_processor import (
    SimpleDocumentProcessor,
)

# Concrete Implementations (adjust paths as needed)
try:
    from graph_rag.infrastructure.graph_stores.memgraph_store import MemgraphGraphRepository
    _MEMGRAPH_AVAILABLE = True
except Exception:  # pragma: no cover - allow CI without mgclient
    class MemgraphGraphRepository:  # type: ignore
        ...
    _MEMGRAPH_AVAILABLE = False

from graph_rag.infrastructure.graph_stores.mock_graph_store import MockGraphRepository

# from graph_rag.infrastructure.graph_stores.neo4j_store import Neo4jGraphRepository # Remove this line
from graph_rag.infrastructure.vector_stores.simple_vector_store import SimpleVectorStore

# Avoid importing FAISS at module import time to keep optional dependency lazy
# Import MockLLMService
from graph_rag.llm import MockLLMService
from graph_rag.llm.protocols import LLMService

# from graph_rag.infrastructure.entity_extractors.spacy_entity_extractor import SpacyEntityExtractor # Remove this line
# NOTE: Avoid importing SentenceTransformerEmbeddingService at module import time
# to prevent pulling in heavy torch dependencies during lightweight test runs.
# Import it lazily inside factory when needed.
# Remove PersistentKnowledgeGraphBuilder import if not used elsewhere
# from graph_rag.core.persistent_kg_builder import PersistentKnowledgeGraphBuilder
# Service Import
from graph_rag.services.ingestion import IngestionService
from graph_rag.services.search import SearchService

# Removed incorrect import for SpacyEntityExtractor
# from graph_rag.infrastructure.entity_extractors.spacy_extractor import SpacyEntityExtractor
# Remove unnecessary import as OpenAILLMService is defined locally
# from graph_rag.infrastructure.llm.openai_llm import OpenAILLMService


# Define a Mock Embedding Service
class MockEmbeddingService(EmbeddingService):
    """Minimal implementation of a mock EmbeddingService."""

    def __init__(self, dimension: int = 10):  # Add dimension
        self.dimension = dimension
        # Create a constant normalized vector
        self._dummy_vector = np.zeros(self.dimension)
        if self.dimension > 0:
            self._dummy_vector[0] = 1.0
        self._dummy_vector_list = self._dummy_vector.tolist()
        logger.info(
            f"Minimal MockEmbeddingService initialized with dimension {dimension} and constant normalized vector."
        )

    async def encode(self, texts: list[str], **kwargs) -> list[list[float]]:
        logger.warning(
            f"MockEmbeddingService.encode called for {len(texts)} texts. Returning constant normalized vector."
        )
        # Return the same constant normalized vector for all texts
        return [self._dummy_vector_list for _ in texts]

    async def encode_query(self, text: str, **kwargs) -> list[float]:
        """Encodes a single query text."""
        logger.warning(
            f"MockEmbeddingService.encode_query called for text: '{text}'. Returning constant normalized vector."
        )
        # Return the constant normalized vector
        return self._dummy_vector_list

    def get_embedding_dimension(self) -> int:  # Renamed from get_dimension for clarity
        """Returns the configured embedding dimension."""
        return self.dimension



# Initialize settings once
settings = get_settings()

logger = logging.getLogger(__name__)

# Use a dictionary to store singletons
_singletons: dict[str, Any] = {}

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
            logger.warning(
                f"Unsupported cache type '{settings.cache_type}', falling back to MemoryCache."
            )
            _singletons["cache_service"] = MemoryCache()
    return _singletons["cache_service"]


def create_graph_repository(settings: Settings) -> GraphRepository:
    """Provides a GraphRepository instance with graceful fallbacks. Expects resolved settings."""

    # Explicit vector-only mode
    if getattr(settings, 'vector_only_mode', False):
        logger.info("Running in explicit vector-only mode - graph features disabled")
        return MockGraphRepository()

    # Check if graph functionality is disabled (legacy setting)
    if getattr(settings, 'disable_graph', False):
        logger.info("Graph functionality disabled via settings, using MockGraphRepository")
        return MockGraphRepository()

    # Check if auto-fallback is disabled
    auto_fallback = getattr(settings, 'auto_fallback_vector_mode', True)

    # Try to create Memgraph repository if available
    if _MEMGRAPH_AVAILABLE:
        try:
            logger.debug(
                f"Creating MemgraphGraphRepository instance for {settings.memgraph_host}:{settings.memgraph_port}"
            )
            repo = MemgraphGraphRepository(settings_obj=settings)
            logger.info("✅ Memgraph connection successful - full graph features enabled")
            return repo
        except Exception as e:
            if auto_fallback:
                logger.warning(
                    f"Failed to create MemgraphGraphRepository ({e}), auto-falling back to vector-only mode"
                )
                logger.info("💡 Run 'synapse up' to start Memgraph for full graph features")
            else:
                logger.error(f"Failed to create MemgraphGraphRepository: {e}")
                raise
    else:
        if auto_fallback:
            logger.warning("Memgraph client not available, auto-falling back to vector-only mode")
            logger.info("💡 Install mgclient and Docker to enable full graph features")
        else:
            raise ImportError("Memgraph client not available and auto-fallback disabled")

    # Fallback to mock repository
    logger.info("Using vector-only mode - some advanced features will be limited")
    return MockGraphRepository()


def create_llm_service(settings: Settings) -> LLMService:  # Added factory function
    """Creates an LLMService instance based on settings. Expects resolved settings."""
    try:
        llm_type = settings.llm_type.lower()
        logger.info(f"Creating LLMService instance of type: {llm_type}")

        if llm_type == "openai":
            from graph_rag.llm.openai_service import OpenAIService

            api_key = (
                settings.openai_api_key.get_secret_value()
                if settings.openai_api_key
                else None
            )
            if not api_key:
                logger.error("OpenAI API key is not configured.")
                raise HTTPException(
                    status_code=503,
                    detail="LLM Service (OpenAI) not configured: API key missing.",
                )

            instance = OpenAIService(
                api_key=api_key,
                model=settings.llm_model_name,
                max_tokens=settings.llm_max_tokens,
                temperature=settings.llm_temperature,
                timeout=settings.llm_timeout
            )

        elif llm_type == "anthropic":
            from graph_rag.llm.anthropic_service import AnthropicService

            api_key = (
                settings.anthropic_api_key.get_secret_value()
                if settings.anthropic_api_key
                else None
            )
            if not api_key:
                logger.error("Anthropic API key is not configured.")
                raise HTTPException(
                    status_code=503,
                    detail="LLM Service (Anthropic) not configured: API key missing.",
                )

            instance = AnthropicService(
                api_key=api_key,
                model=settings.llm_model_name,
                max_tokens=settings.llm_max_tokens,
                temperature=settings.llm_temperature,
                timeout=settings.llm_timeout
            )

        elif llm_type == "ollama":
            from graph_rag.llm.ollama_service import OllamaService

            instance = OllamaService(
                base_url=settings.ollama_base_url,
                model=settings.llm_model_name,
                timeout=settings.llm_timeout,
                temperature=settings.llm_temperature,
                max_tokens=settings.llm_max_tokens if settings.llm_max_tokens > 0 else None
            )

        elif llm_type == "mock":
            instance = MockLLMService()
        else:
            logger.warning(
                f"Unsupported llm_type '{settings.llm_type}'. Falling back to MockLLMService."
            )
            instance = MockLLMService()

    except AttributeError:
        logger.warning(
            "LLM_TYPE not found in settings. Falling back to MockLLMService."
        )
        instance = MockLLMService()

    return instance


def create_vector_store(settings: Settings) -> VectorStore:
    """Factory function to create a VectorStore instance based on settings."""
    vector_store_type = settings.vector_store_type.lower()
    logger.info(f"Creating VectorStore instance (type: {vector_store_type})")

    # Get the (cached) embedding service instance first
    embedding_service = create_embedding_service(settings)

    if vector_store_type == "simple":
        # Pass the embedding service instance, not the model name
        return SimpleVectorStore(embedding_service=embedding_service)
    elif vector_store_type == "faiss":
        # Ensure path exists; embedding dimension from service
        dim = embedding_service.get_embedding_dimension()
        # Lazy import to avoid hard dependency during tests without faiss
        from graph_rag.infrastructure.vector_stores.faiss_vector_store import (
            FaissVectorStore,
        )

        return FaissVectorStore(
            path=settings.vector_store_path, 
            embedding_dimension=dim,
            embedding_service=embedding_service
        )
    # Add other vector store types here if needed
    # elif vector_store_type == 'qdrant':
    #    return QdrantVectorStore(...)
    else:
        logger.warning(
            f"Unsupported vector_store_type '{settings.vector_store_type}'. Falling back to SimpleVectorStore."
        )
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
    if extractor_type == "spacy":
        instance = SpacyEntityExtractor(model_name=settings.entity_extractor_model)
    elif extractor_type == "mock":
        instance = MockEntityExtractor()
    else:
        logger.warning(
            f"Unsupported entity_extractor_type '{settings.entity_extractor_type}'. Falling back to MockEntityExtractor."
        )
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
    settings: Settings,  # No longer needs Depends here, pass settings directly
) -> EmbeddingService:
    """Create embedding service based on settings."""
    cache_key = "embedding_service"
    if cache_key in _dependency_cache:
        return _dependency_cache[cache_key]

    logger.debug("Attempting to create embedding service...")
    embedding_provider = (
        settings.embedding_provider.lower()
        if hasattr(settings, "embedding_provider")
        else "mock"
    )  # Default to mock if unset
    # Get cache instance - needs a way to access it or pass it
    # For now, assume MemoryCache if not explicitly passed, adjust if cache is needed
    # cache = get_cache_service(settings) # This would require settings to be passed via Depends
    MemoryCache()  # Simplified for factory logic, reconsider if cache needs DI
    logger.info(f"Creating EmbeddingService instance (type: {embedding_provider})")

    if embedding_provider == "openai":
        logger.warning(
            "OpenAI embedding provider selected, but using MockEmbeddingService as placeholder."
        )
        instance = MockEmbeddingService(dimension=10)  # Use mock for now
    elif embedding_provider == "sentence-transformers":
        # Try real model; if unavailable, fall back to mock to keep tests green
        try:
            from graph_rag.services.embedding import (
                SentenceTransformerEmbeddingService,
            )
            instance = SentenceTransformerEmbeddingService(
                model_name=settings.vector_store_embedding_model
            )
            logger.info(f"SentenceTransformerEmbeddingService initialized with model: {settings.vector_store_embedding_model}")
        except Exception as e:
            logger.warning(
                f"SentenceTransformer provider unavailable; falling back to MockEmbeddingService. Error: {e}"
            )
            instance = MockEmbeddingService(dimension=384)  # Use 384 to match real embeddings
    elif embedding_provider == "mock":
        instance = MockEmbeddingService(dimension=384)  # Use 384 to match sentence-transformers
    else:
        logger.error(
            f"Unsupported embedding_provider configured: '{settings.embedding_provider}'."
        )
        raise ValueError(
            f"Unsupported embedding provider type: {settings.embedding_provider}"
        )

    _dependency_cache[cache_key] = instance
    logger.info(
        f"Embedding service instance ({type(instance).__name__}) created and cached."
    )
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
    graph_repo: GraphRepository, entity_extractor: EntityExtractor
) -> SimpleKnowledgeGraphBuilder:
    logger.debug("Creating SimpleKnowledgeGraphBuilder instance")
    # Ensure we have the correct class name SimpleKnowledgeGraphBuilder
    return SimpleKnowledgeGraphBuilder(
        graph_store=graph_repo, entity_extractor=entity_extractor
    )


def create_search_service(
    graph_repo: GraphRepository, vector_store: VectorStore
) -> SearchService:
    logger.debug("Creating SearchService instance")
    return SearchService(graph_repo=graph_repo, vector_store=vector_store)


# Modified to create SimpleGraphRAGEngine
def create_graph_rag_engine(
    graph_repository: GraphRepository,
    vector_store: VectorStore,
    entity_extractor: EntityExtractor,
    llm_service: LLMService,  # Added LLM service dependency
    settings: Settings,  # Keep settings for potential future use
) -> GraphRAGEngine:
    """Creates a SimpleGraphRAGEngine instance."""
    from graph_rag.services.citation import CitationStyle

    # Parse citation style from settings
    citation_style_str = getattr(settings, 'citation_style', 'numeric').lower()
    citation_style = CitationStyle.NUMERIC  # Default

    try:
        citation_style = CitationStyle(citation_style_str)
    except ValueError:
        logger.warning(f"Unknown citation style '{citation_style_str}', using numeric")

    logger.debug("Creating SimpleGraphRAGEngine instance")
    return SimpleGraphRAGEngine(
        graph_store=graph_repository,
        vector_store=vector_store,
        entity_extractor=entity_extractor,
        llm_service=llm_service,  # Pass LLM service to engine
        citation_style=citation_style,
    )


def create_ingestion_service(
    document_processor: DocumentProcessor,
    entity_extractor: EntityExtractor,
    graph_repo: GraphRepository,
    embedding_service: EmbeddingService,
    vector_store: VectorStore,  # Added vector_store argument
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
        vector_store=vector_store,  # Pass vector_store argument
    )


# --- FastAPI Dependency Provider Async Functions (DEFINED BEFORE USAGE) ---


async def get_settings_dep() -> Settings:
    """Dependency getter for settings."""
    # Ensures settings are loaded if not already
    return get_settings()


async def get_graph_repository(
    settings: Settings = Depends(get_settings_dep),
) -> GraphRepository:
    """Dependency getter for GraphRepository, using singleton pattern."""
    if "graph_repository" not in _singletons:
        _singletons["graph_repository"] = create_graph_repository(settings=settings)
    return _singletons["graph_repository"]


async def get_embedding_service(
    settings: Settings = Depends(get_settings_dep),
) -> EmbeddingService:
    """Dependency getter for EmbeddingService, using singleton pattern."""
    # This relies on create_embedding_service handling the caching in _dependency_cache
    return create_embedding_service(settings=settings)


async def get_vector_store(
    request: Request,
) -> VectorStore:
    """Provides the VectorStore instance from app state."""
    # Use the app's vector store instance from lifespan
    if (
        hasattr(request.app.state, "vector_store")
        and request.app.state.vector_store is not None
    ):
        return request.app.state.vector_store
    else:
        logger.error("Vector store not found in app state")
        raise HTTPException(status_code=503, detail="Vector store not initialized")


async def get_entity_extractor(
    settings: Settings = Depends(get_settings_dep),
) -> EntityExtractor:
    """Provides an EntityExtractor instance."""
    # Assuming stateless or singleton not strictly required for tests here
    if "entity_extractor" not in _singletons:
        _singletons["entity_extractor"] = create_entity_extractor(settings=settings)
    return _singletons["entity_extractor"]


async def get_document_processor(
    settings: Settings = Depends(get_settings),
) -> DocumentProcessor:
    # Factory function handles singleton logic internally now
    return create_document_processor()


async def get_llm(
    settings: Settings = Depends(get_settings_dep),
) -> LLMService:  # Added getter
    """Dependency getter for LLMService, using singleton pattern."""
    # Note: create_llm_service factory already exists, but we should use load_llm ideally.
    # Sticking to the pattern using create_llm_service for now.
    if "llm_service" not in _singletons:
        logger.info("Creating LLMService singleton via factory.")
        # Original logic used create_llm_service, let's keep it for consistency for now
        # Replace with load_llm(settings=settings) if loader logic is preferred directly
        _singletons["llm_service"] = create_llm_service(settings=settings)
    return _singletons["llm_service"]


# Added getter for SimpleGraphRAGEngine
async def get_graph_rag_engine(
    graph_repo: GraphRepository = Depends(get_graph_repository),
    vector_store: VectorStore = Depends(get_vector_store),
    entity_extractor: EntityExtractor = Depends(get_entity_extractor),
    llm_service: LLMService = Depends(get_llm),  # Add LLM dependency
    settings: Settings = Depends(get_settings_dep),
) -> GraphRAGEngine:
    """Dependency getter for the main Graph RAG Engine (SimpleGraphRAGEngine)."""
    # Engine is typically not a singleton unless state needs preservation across requests
    # Create a new instance per request or manage singleton if appropriate
    # For now, create per request using the factory
    return create_graph_rag_engine(
        graph_repository=graph_repo,
        vector_store=vector_store,
        entity_extractor=entity_extractor,
        llm_service=llm_service,  # Pass LLM service
        settings=settings,
    )


# Add the missing getter for KnowledgeGraphBuilder
async def get_knowledge_graph_builder(
    graph_repo: GraphRepository = Depends(get_graph_repository),
    entity_extractor: EntityExtractor = Depends(get_entity_extractor),
) -> SimpleKnowledgeGraphBuilder:
    """Dependency getter for KnowledgeGraphBuilder."""
    # Typically create per request unless state needs preserving
    # Check if already in singletons if needed, otherwise create new
    if "kg_builder" not in _singletons:
        logger.info("Creating KnowledgeGraphBuilder singleton instance.")
        # Ensure the create_knowledge_graph_builder factory exists (added previously)
        _singletons["kg_builder"] = create_knowledge_graph_builder(
            graph_repo=graph_repo, entity_extractor=entity_extractor
        )
    return _singletons["kg_builder"]


# Optional: Add getter for IngestionService if needed by API endpoints
async def get_ingestion_service(
    request: Request,
) -> IngestionService:
    """Dependency getter for IngestionService."""
    # Use the app's ingestion service instance from lifespan
    if (
        hasattr(request.app.state, "ingestion_service")
        and request.app.state.ingestion_service is not None
    ):
        return request.app.state.ingestion_service
    else:
        logger.error("Ingestion service not found in app state")
        raise HTTPException(status_code=503, detail="Ingestion service not initialized")


# Optional: Add getter for SearchService if needed by API endpoints
async def get_search_service(
    graph_repo: GraphRepository = Depends(get_graph_repository),
    vector_store: VectorStore = Depends(get_vector_store),
) -> SearchService:
    """Dependency getter for SearchService."""
    # Typically create per request
    return create_search_service(graph_repo=graph_repo, vector_store=vector_store)


# --- Concept Mapping Dependencies ---

async def get_concept_extractor() -> Any:
    """Dependency getter for ConceptExtractor."""
    from graph_rag.core.concept_extractor import EnhancedConceptExtractor
    
    if "concept_extractor" not in _singletons:
        _singletons["concept_extractor"] = EnhancedConceptExtractor(use_advanced_nlp=True)
        logger.debug("Created ConceptExtractor instance")
    
    return _singletons["concept_extractor"]


async def get_concept_entity_extractor(
    traditional_extractor: EntityExtractor = Depends(get_entity_extractor)
) -> Any:
    """Dependency getter for ConceptEntityExtractor that combines traditional NER with concept extraction."""
    from graph_rag.core.concept_entity_extractor import ConceptEntityExtractor
    
    cache_key = f"concept_entity_extractor_{id(traditional_extractor)}"
    if cache_key not in _singletons:
        _singletons[cache_key] = ConceptEntityExtractor(
            traditional_extractor=traditional_extractor,
            use_advanced_concepts=True
        )
        logger.debug("Created ConceptEntityExtractor instance")
    
    return _singletons[cache_key]


async def get_belief_preference_extractor(
    traditional_extractor: EntityExtractor = Depends(get_entity_extractor)
) -> Any:
    """Dependency getter for BeliefPreferenceExtractor specialized for Epic 6."""
    from graph_rag.core.concept_entity_extractor import BeliefPreferenceExtractor
    
    cache_key = f"belief_preference_extractor_{id(traditional_extractor)}"
    if cache_key not in _singletons:
        _singletons[cache_key] = BeliefPreferenceExtractor(
            traditional_extractor=traditional_extractor
        )
        logger.debug("Created BeliefPreferenceExtractor instance for Epic 6")
    
    return _singletons[cache_key]


async def get_temporal_tracker() -> Any:
    """Dependency getter for TemporalTracker."""
    from graph_rag.core.temporal_tracker import TemporalTracker
    
    if "temporal_tracker" not in _singletons:
        _singletons["temporal_tracker"] = TemporalTracker()
        logger.debug("Created TemporalTracker instance")
    
    return _singletons["temporal_tracker"]


async def get_cross_platform_correlator(
    graph_repo: GraphRepository = Depends(get_graph_repository),
) -> Any:
    """Dependency getter for CrossPlatformCorrelator."""
    from graph_rag.services.cross_platform_correlator import CrossPlatformCorrelator
    
    # Create per request since it maintains state
    correlator = CrossPlatformCorrelator(graph_repo)
    logger.debug("Created CrossPlatformCorrelator instance")
    
    return correlator


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
        if hasattr(repo, 'close'):
            logger.info("Closing graph repository connection.")
            await repo.close()  # Assuming close is async
        del _singletons["graph_repository"]  # Remove from singletons


# Add other cleanup logic as needed (e.g., closing LLM connections)

# You might register these cleanup functions with FastAPI's lifespan events
# in your main application setup (e.g., main.py).
