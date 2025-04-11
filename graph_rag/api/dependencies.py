import logging
from typing import AsyncGenerator, Annotated

from fastapi import Depends, HTTPException, status, Request
# Remove if unused
# from fastapi.security import APIKeyHeader

# Configuration
from graph_rag.config import get_settings # Import factory

# Core Interfaces and Engine
from graph_rag.core.interfaces import (
    GraphRepository, VectorStore, EntityExtractor, DocumentProcessor,
    KnowledgeGraphBuilder, VectorSearcher, KeywordSearcher, GraphSearcher,
    EmbeddingService, GraphRAGEngine
)
from graph_rag.core.graph_rag_engine import GraphRAGEngine as ConcreteGraphRAGEngine

# Concrete Implementations (adjust paths as needed)
from graph_rag.infrastructure.graph_stores.memgraph_store import MemgraphGraphRepository
from graph_rag.stores.simple_vector_store import SimpleVectorStore
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


# Initialize settings once
settings = get_settings()

logger = logging.getLogger(__name__)


# --- Factory functions for dependencies --- 
# These functions create instances based on settings.
# In a real app, you might register these with the FastAPI app state or a DI container.

def create_graph_repository() -> GraphRepository:
    logger.debug("Creating MemgraphGraphRepository instance")
    return MemgraphGraphRepository(
        host=settings.MEMGRAPH_HOST,
        port=settings.MEMGRAPH_PORT,
        # Add user/password if configured
        # user=settings.MEMGRAPH_USER,
        # password=settings.MEMGRAPH_PASSWORD,
    )

def create_embedding_service() -> EmbeddingService:
    logger.debug("Creating SentenceTransformerEmbeddingService instance")
    # Use the actual service now
    return SentenceTransformerEmbeddingService(model_name=settings.EMBEDDING_MODEL)

def create_vector_store() -> VectorStore:
    logger.debug("Creating SimpleVectorStore instance")
    # Assuming SimpleVectorStore needs embedding dim or is self-contained
    # If it needs dim, we might need to get it from the embedding service
    # embedding_service = create_embedding_service() # Temporary instance if needed
    # dim = embedding_service.get_embedding_dim()
    return SimpleVectorStore(embedding_dim=settings.EMBEDDING_DIM) # Pass dim if needed

def create_entity_extractor() -> EntityExtractor:
    logger.debug("Creating SpacyEntityExtractor instance")
    # Instantiate the correct class - Assuming model name comes from settings
    # Update args if needed after checking file
    return SpacyEntityExtractor(model_name=settings.SPACY_MODEL)

def create_document_processor() -> DocumentProcessor:
    logger.debug("Creating SimpleDocumentProcessor instance")
    
    # Get strategy from settings, default to paragraph
    strategy = getattr(settings, 'CHUNK_STRATEGY', 'paragraph')
    # Use CHUNK_SIZE for tokens_per_chunk if strategy is 'token'
    tokens = getattr(settings, 'CHUNK_SIZE', 200) 

    logger.info(f"Using chunk strategy: {strategy}, tokens per chunk: {tokens}")
    
    # Instantiate the correct class with appropriate args
    return SimpleDocumentProcessor(
        chunk_strategy=strategy,
        tokens_per_chunk=tokens
        # chunk_overlap is not used by SimpleDocumentProcessor
    )

def create_kg_builder(graph_repo: GraphRepository, entity_extractor: EntityExtractor) -> KnowledgeGraphBuilder:
    logger.debug("Creating PersistentKnowledgeGraphBuilder instance")
    return PersistentKnowledgeGraphBuilder(graph_repository=graph_repo, entity_extractor=entity_extractor)

def create_search_service(
    graph_repo: GraphRepository = Depends(create_graph_repository) # Assumes MemgraphRepository compatible with GraphRepository
    # embedding_service: EmbeddingService = Depends(create_embedding_service) # SearchService init might need this
) -> SearchService:
    logger.debug("Creating SearchService instance")
    # Check SearchService constructor signature
    # Assuming it takes repository and potentially embedding service
    return SearchService(repository=graph_repo)

def create_graph_rag_engine(
    graph_repository: GraphRepository = Depends(create_graph_repository),
    vector_store: VectorStore = Depends(create_vector_store),
    embedding_service: EmbeddingService = Depends(create_embedding_service),
    entity_extractor: EntityExtractor = Depends(create_entity_extractor),
    document_processor: DocumentProcessor = Depends(create_document_processor),
    kg_builder: KnowledgeGraphBuilder = Depends(create_kg_builder),
    search_service: SearchService = Depends(create_search_service) # Add SearchService dependency
) -> GraphRAGEngine:
    logger.debug("Creating ConcreteGraphRAGEngine instance")
    # Update constructor call for ConcreteGraphRAGEngine
    return ConcreteGraphRAGEngine(
        graph_repository=graph_repository,
        vector_store=vector_store,
        embedding_service=embedding_service,
        entity_extractor=entity_extractor,
        document_processor=document_processor,
        kg_builder=kg_builder,
        # Pass search_service instead of individual searchers
        search_service=search_service
        # vector_searcher=vector_searcher,
        # keyword_searcher=keyword_searcher,
        # graph_searcher=graph_searcher,
    )

def create_ingestion_service(
    graph_repo: GraphRepository,
    vector_store: VectorStore,
    doc_processor: DocumentProcessor,
    entity_extractor: EntityExtractor
) -> IngestionService:
    logger.debug("Creating IngestionService instance")
    return IngestionService(
        graph_repo=graph_repo,
        vector_store=vector_store,
        document_processor=doc_processor,
        entity_extractor=entity_extractor
    )

# Remove QueryEngine factory
# def create_query_engine(...):
#     ...

def create_knowledge_graph_builder(
    # Only need the graph repository for SimpleKnowledgeGraphBuilder
    graph_repo: GraphRepository = Depends(create_graph_repository),
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

# --- FastAPI Dependency Provider Functions --- 
# These functions are used by FastAPI's Depends() to inject instances into route handlers.
# They call the factory functions above.

async def get_graph_repository() -> GraphRepository:
    if "graph_repository" not in _singletons:
        _singletons["graph_repository"] = create_graph_repository()
    return _singletons["graph_repository"]

async def get_embedding_service() -> EmbeddingService:
    if "embedding_service" not in _singletons:
        _singletons["embedding_service"] = create_embedding_service()
    return _singletons["embedding_service"]

async def get_vector_store() -> VectorStore:
    if "vector_store" not in _singletons:
        _singletons["vector_store"] = create_vector_store()
    return _singletons["vector_store"]

async def get_entity_extractor() -> EntityExtractor:
    if "entity_extractor" not in _singletons:
        _singletons["entity_extractor"] = create_entity_extractor()
    return _singletons["entity_extractor"]

async def get_document_processor() -> DocumentProcessor:
    if "document_processor" not in _singletons:
        _singletons["document_processor"] = create_document_processor()
    return _singletons["document_processor"]

async def get_kg_builder(
    graph_repo: GraphRepository = Depends(get_graph_repository),
    entity_extractor: EntityExtractor = Depends(get_entity_extractor),
    embedding_service: EmbeddingService = Depends(get_embedding_service)
) -> KnowledgeGraphBuilder:
    logger.debug("Creating PersistentKnowledgeGraphBuilder instance")
    return PersistentKnowledgeGraphBuilder(
        graph_repository=graph_repo,
        entity_extractor=entity_extractor,
        embedding_service=embedding_service
    )

# Assuming VectorStore implements VectorSearcher, GraphStore implements Graph/KeywordSearcher
VectorSearcherDep = Annotated[VectorSearcher, Depends(get_vector_store)]
KeywordSearcherDep = Annotated[KeywordSearcher, Depends(get_graph_repository)] 
GraphSearcherDep = Annotated[GraphSearcher, Depends(get_graph_repository)]

async def get_search_service(
    graph_repo: GraphRepository = Depends(get_graph_repository)
    # embedding_service: EmbeddingService = Depends(get_embedding_service)
) -> SearchService:
    # Decide if singleton or fresh instance
    if "search_service" not in _singletons:
        _singletons["search_service"] = create_search_service(graph_repo)
    return _singletons["search_service"]

async def get_graph_rag_engine(
    graph_repository: GraphRepository = Depends(get_graph_repository),
    vector_store: VectorStore = Depends(get_vector_store),
    embedding_service: EmbeddingService = Depends(get_embedding_service),
    entity_extractor: EntityExtractor = Depends(get_entity_extractor),
    document_processor: DocumentProcessor = Depends(get_document_processor),
    kg_builder: KnowledgeGraphBuilder = Depends(get_kg_builder),
    search_service: SearchService = Depends(get_search_service) # Add SearchService dependency
) -> GraphRAGEngine:
    # Decide if Engine should be singleton (likely yes if it holds state or is expensive)
    if "graph_rag_engine" not in _singletons:
        _singletons["graph_rag_engine"] = create_graph_rag_engine(
            graph_repository=graph_repository,
            vector_store=vector_store,
            embedding_service=embedding_service,
            entity_extractor=entity_extractor,
            document_processor=document_processor,
            kg_builder=kg_builder,
            search_service=search_service
        )
    return _singletons["graph_rag_engine"]

async def get_ingestion_service(
    graph_repo: GraphRepository = Depends(get_graph_repository),
    vector_store: VectorStore = Depends(get_vector_store),
    doc_processor: DocumentProcessor = Depends(get_document_processor),
    entity_extractor: EntityExtractor = Depends(get_entity_extractor)
) -> IngestionService:
    logger.warning("Ingestion service not found in app state, creating new instance.")
    return IngestionService(
        graph_repo=graph_repo,
        vector_store=vector_store,
        document_processor=doc_processor,
        entity_extractor=entity_extractor
    )

# Remove QueryEngine provider
# async def get_query_engine(...):
#     ...

# --- Removed incorrect functions from previous edit attempt ---

# Use a dictionary to store singletons
_singletons = {}

# --- Annotated Dependencies ---

GraphRepositoryDep = Annotated[GraphRepository, Depends(get_graph_repository)]
VectorStoreDep = Annotated[VectorStore, Depends(get_vector_store)]
EmbeddingServiceDep = Annotated[EmbeddingService, Depends(get_embedding_service)]
EntityExtractorDep = Annotated[EntityExtractor, Depends(get_entity_extractor)]
DocumentProcessorDep = Annotated[DocumentProcessor, Depends(get_document_processor)]
KnowledgeGraphBuilderDep = Annotated[KnowledgeGraphBuilder, Depends(get_kg_builder)]
# Remove individual searcher deps
# VectorSearcherDep = Annotated[VectorSearcher, Depends(get_vector_searcher)]
# KeywordSearcherDep = Annotated[KeywordSearcher, Depends(get_keyword_searcher)]
# GraphSearcherDep = Annotated[GraphSearcher, Depends(get_graph_searcher)]
# Add SearchService dep
SearchServiceDep = Annotated[SearchService, Depends(get_search_service)]
GraphRAGEngineDep = Annotated[GraphRAGEngine, Depends(get_graph_rag_engine)]


# Optional: API Key Verification Dependency
# api_key_header = APIKeyHeader(name="X-API-KEY", auto_error=False)

# async def verify_api_key(api_key: str = Depends(api_key_header)):
#     if not api_key:
#         raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="API key is missing")
#     if api_key != settings.API_KEY:
#         raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid API key")
#     return api_key

# # Usage in endpoints: Depends(verify_api_key)

async def get_knowledge_graph_builder(
    graph_repo: GraphRepository = Depends(get_graph_repository),
    # entity_extractor: EntityExtractor = Depends(get_entity_extractor), # Ensure these aren't passed down if not needed
    # embedding_service: EmbeddingService = Depends(get_embedding_service)
) -> KnowledgeGraphBuilder:
     # Pass only the required dependency
     return create_knowledge_graph_builder(graph_repo)