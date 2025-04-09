from typing import Annotated, AsyncGenerator
import logging
from contextlib import asynccontextmanager

from fastapi import Depends, HTTPException, status, Request

# Configuration
from graph_rag.config.settings import Settings, settings as global_settings

# Core Interfaces and Engine
from graph_rag.core.interfaces import (
    DocumentProcessor, EntityExtractor, KnowledgeGraphBuilder,
    VectorSearcher, KeywordSearcher, GraphSearcher, EmbeddingService,
    GraphRAGEngine
)
from graph_rag.core.graph_rag_engine import GraphRAGEngine as ConcreteGraphRAGEngine

# Concrete Implementations
from graph_rag.data_stores.memgraph_store import MemgraphStore, MemgraphStoreError
from graph_rag.services.embedding import SentenceTransformerEmbeddingService
from graph_rag.core.document_processor import SimpleDocumentProcessor
from graph_rag.core.entity_extractor import SpacyEntityExtractor
from graph_rag.core.persistent_kg_builder import PersistentKnowledgeGraphBuilder

logger = logging.getLogger(__name__)

# --- Application State Management (using Lifespan) --- 
# We will manage the engine and its dependencies within the app's state 
# using FastAPI's lifespan context manager in main.py. 
# Dependencies here will retrieve components from the app state.

# --- Dependency Getters --- 

def get_settings(request: Request) -> Settings:
    # Retrieve settings if stored in app state, otherwise use global
    # This allows overriding settings per request/test if needed later
    return request.app.state.settings if hasattr(request.app.state, 'settings') else global_settings

def get_memgraph_store(request: Request) -> MemgraphStore:
    if not hasattr(request.app.state, 'memgraph_store') or request.app.state.memgraph_store is None:
        logger.error("MemgraphStore not found in application state. Was lifespan startup successful?")
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Graph database connection not available.")
    return request.app.state.memgraph_store

def get_embedding_service(request: Request) -> EmbeddingService:
    if not hasattr(request.app.state, 'embedding_service') or request.app.state.embedding_service is None:
         logger.error("EmbeddingService not found in application state.")
         raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Embedding service not available.")
    return request.app.state.embedding_service

def get_document_processor(request: Request) -> DocumentProcessor:
    # Assuming a single processor instance managed by lifespan
    if not hasattr(request.app.state, 'document_processor'):
         logger.error("DocumentProcessor not found in application state.")
         raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Document processing service not available.")
    return request.app.state.document_processor

def get_entity_extractor(request: Request) -> EntityExtractor:
    # Assuming a single extractor instance managed by lifespan
    if not hasattr(request.app.state, 'entity_extractor'):
         logger.error("EntityExtractor not found in application state.")
         raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Entity extraction service not available.")
    return request.app.state.entity_extractor

def get_kg_builder(request: Request) -> KnowledgeGraphBuilder:
     # Assuming a single builder instance managed by lifespan
    if not hasattr(request.app.state, 'kg_builder'):
         logger.error("KnowledgeGraphBuilder not found in application state.")
         raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Knowledge graph service not available.")
    return request.app.state.kg_builder

def get_graph_rag_engine(request: Request) -> GraphRAGEngine:
    """Provides the central GraphRAGEngine instance from app state."""
    if not hasattr(request.app.state, 'graph_rag_engine') or request.app.state.graph_rag_engine is None:
        logger.error("GraphRAGEngine not found in application state. Lifespan setup likely failed.")
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Core RAG engine is not available.")
    return request.app.state.graph_rag_engine

# --- Dependency Type Aliases for Routers --- 
SettingsDep = Annotated[Settings, Depends(get_settings)]
MemgraphStoreDep = Annotated[MemgraphStore, Depends(get_memgraph_store)]
EmbeddingServiceDep = Annotated[EmbeddingService, Depends(get_embedding_service)]
DocumentProcessorDep = Annotated[DocumentProcessor, Depends(get_document_processor)]
EntityExtractorDep = Annotated[EntityExtractor, Depends(get_entity_extractor)]
KnowledgeGraphBuilderDep = Annotated[KnowledgeGraphBuilder, Depends(get_kg_builder)]
GraphRAGEngineDep = Annotated[GraphRAGEngine, Depends(get_graph_rag_engine)]

# VectorSearcher, KeywordSearcher, GraphSearcher are usually implemented by the store/repo
# We inject the store and the engine uses it for searching.
VectorSearcherDep = Annotated[VectorSearcher, Depends(get_memgraph_store)]
KeywordSearcherDep = Annotated[KeywordSearcher, Depends(get_memgraph_store)]
# GraphSearcherDep = Annotated[GraphSearcher, Depends(get_memgraph_store)] # Add if GraphSearcher implemented in store 