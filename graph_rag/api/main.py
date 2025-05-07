import asyncio
import logging
import time
import uuid
from contextlib import asynccontextmanager
from typing import TYPE_CHECKING, Optional, Dict, Any, List

from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.routing import APIRouter
from fastapi.responses import JSONResponse, RedirectResponse
from neo4j import AsyncDriver, AsyncGraphDatabase

# Local application imports
from graph_rag.config import Settings, get_settings
from graph_rag.api.routers import documents, ingestion, search, query
from graph_rag.api import schemas
from graph_rag.api import dependencies as deps # Alias for dependencies

# Import Core Interfaces/Base Classes directly from their modules
from graph_rag.core.interfaces import (
    GraphRAGEngine,
    KnowledgeGraphBuilder,
    EntityExtractor,
    DocumentProcessor,
    VectorStore,
    GraphRepository,
    EmbeddingService
)

# Import Factory Functions from dependencies module
from graph_rag.api.dependencies import (
    create_ingestion_service,
    create_entity_extractor,
    create_vector_store,
    create_embedding_service,
    create_document_processor,
    create_knowledge_graph_builder,
    create_graph_repository, 
    get_settings_dep,
    get_settings, close_graph_repository, get_graph_repository, get_llm, get_embedding_service, get_vector_store, get_entity_extractor
)

# Import Concrete Implementations needed for lifespan setup
from graph_rag.core.graph_rag_engine import SimpleGraphRAGEngine
from graph_rag.infrastructure.cache.memory_cache import MemoryCache
from graph_rag.infrastructure.graph_stores.memgraph_store import MemgraphGraphRepository
from graph_rag.infrastructure.vector_stores.simple_vector_store import SimpleVectorStore
from graph_rag.core.vector_store import MockVectorStore
from graph_rag.core.entity_extractor import MockEntityExtractor, SpacyEntityExtractor
from graph_rag.infrastructure.document_processor.simple_processor import SimpleDocumentProcessor
from graph_rag.core.knowledge_graph_builder import SimpleKnowledgeGraphBuilder
from graph_rag.services.ingestion import IngestionService # Needed for type hint
from graph_rag.services.embedding import SentenceTransformerEmbeddingService 
from graph_rag.api.dependencies import MockEmbeddingService # Import from dependencies

# Configure logging
logger = logging.getLogger(__name__)

# --- Application State ---
app_state = {} # Use a dictionary for app state

# --- Lifespan Management for Resources --- 
@asynccontextmanager
async def lifespan(app: FastAPI):
    # --- Startup --- 
    # Get settings instance for lifespan context
    current_settings = get_settings()
    logger.info(f"LIFESPAN START: Starting API... Config: {current_settings.model_dump(exclude={'memgraph_password'})}") # Use current_settings
    app.state.settings = current_settings # Store in state
    app.state.neo4j_driver: Optional[AsyncDriver] = None
    app.state.graph_repository: Optional[MemgraphGraphRepository] = None
    app.state.vector_store = None
    app.state.entity_extractor = None
    app.state.doc_processor = None
    app.state.kg_builder = None
    app.state.graph_rag_engine = None
    app.state.ingestion_service = None
    embedding_service = None # Initialize embedding_service variable

    # 1. Initialize Neo4j Driver
    logger.info("LIFESPAN: Initializing Neo4j AsyncDriver...")
    if not hasattr(app.state, 'neo4j_driver') or app.state.neo4j_driver is None:
        try:
            driver = AsyncGraphDatabase.driver(
                current_settings.get_memgraph_uri(),
                auth=(current_settings.MEMGRAPH_USERNAME, current_settings.MEMGRAPH_PASSWORD.get_secret_value() if current_settings.MEMGRAPH_PASSWORD else None)
            )
            # Verify connection eagerly
            await driver.verify_connectivity()
            app.state.neo4j_driver = driver
            logger.info("LIFESPAN: Neo4j AsyncDriver initialized and verified successfully.")
        except Exception as e:
            logger.critical(f"LIFESPAN CRITICAL: Failed to initialize or verify Neo4j AsyncDriver: {e}", exc_info=True)
            # Decide whether to raise or allow fallback (currently raises implicitly)
            raise RuntimeError("Failed to initialize database driver") from e
    else:
        logger.info("LIFESPAN: Neo4j AsyncDriver already initialized.")

    # 2. Initialize MemgraphGraphRepository (using the driver)
    logger.info("LIFESPAN: Initializing Graph Repository...")
    if not hasattr(app.state, 'graph_repository') or app.state.graph_repository is None:
        try:
            # Pass the already initialized driver if needed, or rely on internal settings lookup
            app.state.graph_repository = MemgraphGraphRepository(settings_obj=current_settings) 
            # Optional: Add a check method to repository if needed
            # await app.state.graph_repository.check_connection() 
            logger.info(f"LIFESPAN: Initialized Graph Repository: {type(app.state.graph_repository)}")
        except Exception as e:
            logger.critical(f"LIFESPAN CRITICAL: Failed to initialize Graph Repository: {e}", exc_info=True)
            raise RuntimeError("Failed to initialize graph repository") from e
    else:
        logger.info("LIFESPAN: Graph Repository already initialized.")
        
    # 2.5 Initialize Embedding Service (needed by VectorStore)
    logger.info("LIFESPAN: Initializing Embedding Service...")
    try:
        if current_settings.embedding_provider.lower() == 'sentencetransformers':
            embedding_service = SentenceTransformerEmbeddingService(model_name=current_settings.vector_store_embedding_model)
            logger.info(f"LIFESPAN: Initialized SentenceTransformerEmbeddingService with model '{current_settings.vector_store_embedding_model}'.")
        elif current_settings.embedding_provider.lower() == 'mock':
             embedding_service = MockEmbeddingService() # Assuming MockEmbeddingService exists
             logger.info("LIFESPAN: Initialized MockEmbeddingService.")
        # Add other providers like OpenAI here if needed
        # elif current_settings.embedding_provider.lower() == 'openai':
        #     embedding_service = OpenAIEmbeddingService(...) # Requires implementation
        #     logger.info("LIFESPAN: Initialized OpenAIEmbeddingService.")
        else:
            logger.warning(f"LIFESPAN: Unsupported embedding_provider '{current_settings.embedding_provider}'. Using MockEmbeddingService.")
            embedding_service = MockEmbeddingService()
    except Exception as e:
        logger.critical(f"LIFESPAN CRITICAL: Failed to initialize Embedding Service: {e}. Using Mock as fallback.", exc_info=True)
        embedding_service = MockEmbeddingService()
        
    if embedding_service is None:
         logger.critical("LIFESPAN CRITICAL: Embedding Service could not be initialized.")
         raise RuntimeError("Failed to initialize embedding service")

    # 3. Initialize VectorStore based on settings
    logger.info("LIFESPAN: Initializing Vector Store...")
    if not hasattr(app.state, 'vector_store') or app.state.vector_store is None:
        try:
            if current_settings.vector_store_type.lower() == 'simple':
                # Use the embedding_service instance created above
                vector_store = SimpleVectorStore(embedding_service=embedding_service)
                app.state.vector_store = vector_store
                logger.info(f"LIFESPAN: Initialized SimpleVectorStore with provided embedding service.")
            elif current_settings.vector_store_type.lower() == 'mock':
                app.state.vector_store = MockVectorStore()
                logger.info("LIFESPAN: Initialized MockVectorStore.")
            else:
                logger.warning(f"LIFESPAN: Unsupported vector_store_type '{current_settings.vector_store_type}'. Using MockVectorStore.")
                app.state.vector_store = MockVectorStore()
        except Exception as e:
            logger.critical(f"LIFESPAN CRITICAL: Failed to initialize VectorStore: {e}. Using MockVectorStore as fallback.", exc_info=True)
            app.state.vector_store = MockVectorStore()
    else:
        logger.info("LIFESPAN: Vector Store already initialized.")

    # 4. Initialize EntityExtractor based on settings
    logger.info("LIFESPAN: Initializing Entity Extractor...")
    if not hasattr(app.state, 'entity_extractor') or app.state.entity_extractor is None:
        try:
            if current_settings.entity_extractor_type.lower() == 'spacy':
                app.state.entity_extractor = SpacyEntityExtractor(model_name=current_settings.entity_extractor_model)
                logger.info(f"LIFESPAN: Initialized SpacyEntityExtractor with model '{current_settings.entity_extractor_model}'.")
            elif current_settings.entity_extractor_type.lower() == 'mock':
                app.state.entity_extractor = MockEntityExtractor()
                logger.info("LIFESPAN: Initialized MockEntityExtractor.")
            else:
                logger.warning(f"LIFESPAN: Unsupported entity_extractor_type '{current_settings.entity_extractor_type}'. Using MockEntityExtractor.")
                app.state.entity_extractor = MockEntityExtractor()
        except Exception as e:
            logger.critical(f"LIFESPAN CRITICAL: Failed to initialize EntityExtractor: {e}. Using MockEntityExtractor as fallback.", exc_info=True)
            app.state.entity_extractor = MockEntityExtractor()
    else:
        logger.info("LIFESPAN: Entity Extractor already initialized.")

    # 5. Initialize DocumentProcessor
    logger.info("LIFESPAN: Initializing Document Processor...")
    if not hasattr(app.state, 'doc_processor') or app.state.doc_processor is None:
        try:
            app.state.doc_processor = SimpleDocumentProcessor()
            logger.info("LIFESPAN: Initialized SimpleDocumentProcessor.")
        except Exception as e:
            logger.critical(f"LIFESPAN CRITICAL: Failed to initialize Document Processor: {e}", exc_info=True)
            raise RuntimeError("Failed to initialize document processor") from e
    else:
        logger.info("LIFESPAN: Document Processor already initialized.")

    # 6. Initialize KG Builder
    logger.info("LIFESPAN: Initializing Knowledge Graph Builder...")
    if not hasattr(app.state, 'kg_builder') or app.state.kg_builder is None:
        if app.state.graph_repository:
            try:
                app.state.kg_builder = SimpleKnowledgeGraphBuilder(graph_store=app.state.graph_repository)
                logger.info("LIFESPAN: Initialized SimpleKnowledgeGraphBuilder.")
            except Exception as e:
                logger.critical(f"LIFESPAN CRITICAL: Failed to initialize Knowledge Graph Builder: {e}", exc_info=True)
                raise RuntimeError("Failed to initialize knowledge graph builder") from e
        else:
            logger.error("LIFESPAN: Cannot initialize SimpleKnowledgeGraphBuilder: Graph Repository not available.")
            raise RuntimeError("Graph Repository not available for KG Builder")
    else:
        logger.info("LIFESPAN: Knowledge Graph Builder already initialized.")

    # 7. Initialize GraphRAGEngine
    logger.info("LIFESPAN: Initializing Graph RAG Engine...")
    if not hasattr(app.state, 'graph_rag_engine') or app.state.graph_rag_engine is None:
        if not all([app.state.graph_repository, app.state.vector_store, app.state.entity_extractor]):
            logger.critical("LIFESPAN CRITICAL: Cannot initialize GraphRAGEngine due to missing dependencies (GraphRepo, VectorStore, or EntityExtractor).")
            raise RuntimeError("Missing dependencies for GraphRAGEngine initialization")
        try:
            app.state.graph_rag_engine = SimpleGraphRAGEngine(
                graph_store=app.state.graph_repository,
                vector_store=app.state.vector_store,
                entity_extractor=app.state.entity_extractor
                # Add LLM service here if needed by the engine constructor
                # llm_service=get_llm(settings=current_settings) # Or fetch from state if initialized earlier
            )
            logger.info("LIFESPAN: Initialized SimpleGraphRAGEngine.")
        except Exception as e:
            logger.critical(f"LIFESPAN CRITICAL: Failed to initialize SimpleGraphRAGEngine: {e}", exc_info=True)
            # Allow startup to continue? Or raise? Let's raise for now.
            raise RuntimeError("Failed to initialize Graph RAG Engine") from e
    else:
        logger.info("LIFESPAN: Graph RAG Engine already initialized.")

    # 8. Initialize ingestion service
    logger.info("LIFESPAN: Initializing Ingestion Service...")
    if not hasattr(app.state, 'ingestion_service') or app.state.ingestion_service is None:
        if not all([app.state.doc_processor, app.state.entity_extractor, app.state.graph_repository, embedding_service, app.state.vector_store]):
             logger.critical("LIFESPAN CRITICAL: Cannot initialize IngestionService due to missing dependencies.")
             raise RuntimeError("Missing dependencies for IngestionService initialization")
        try:
            app.state.ingestion_service = IngestionService(
                document_processor=app.state.doc_processor,
                entity_extractor=app.state.entity_extractor,
                graph_store=app.state.graph_repository,
                embedding_service=embedding_service, # Use the initialized instance
                vector_store=app.state.vector_store
            )
            logger.info("LIFESPAN: Initialized IngestionService.")
        except Exception as e:
            logger.critical(f"LIFESPAN CRITICAL: Failed to initialize IngestionService: {e}", exc_info=True)
            # Allow startup to continue? Or raise? Let's raise for now.
            raise RuntimeError("Failed to initialize Ingestion Service") from e
    else:
        logger.info("LIFESPAN: Ingestion Service already initialized.")

    logger.info("LIFESPAN END: Application startup dependencies initialized successfully.")
    yield # Application runs here
    
    # --- Shutdown --- 
    logger.info("LIFESPAN SHUTDOWN: Shutting down API...")
    if hasattr(app.state, 'neo4j_driver') and app.state.neo4j_driver:
        try:
            await app.state.neo4j_driver.close()
            logger.info("LIFESPAN SHUTDOWN: Neo4j AsyncDriver closed.")
        except Exception as e:
            logger.error(f"LIFESPAN SHUTDOWN: Error closing Neo4j AsyncDriver: {e}", exc_info=True)
            
    # Clear state (optional but good practice)
    app.state.graph_rag_engine = None
    app.state.kg_builder = None
    app.state.entity_extractor = None
    app.state.doc_processor = None
    app.state.vector_store = None
    app.state.graph_repository = None
    app.state.neo4j_driver = None
    app.state.settings = None
    app.state.ingestion_service = None
    logger.info("LIFESPAN SHUTDOWN: Application shutdown complete.")

# Dependency Getters (Now rely solely on app state)
def get_graph_repository(request: Request) -> "MemgraphGraphRepository":
    if not hasattr(request.app.state, 'graph_repository') or request.app.state.graph_repository is None:
        logger.error("Dependency Error: Graph repository requested but not initialized.")
        raise HTTPException(status_code=503, detail="Graph repository not initialized")
    return request.app.state.graph_repository

def get_entity_extractor(request: Request) -> "EntityExtractor":
    if not hasattr(request.app.state, 'entity_extractor') or request.app.state.entity_extractor is None:
        logger.error("Dependency Error: Entity extractor requested but not initialized.")
        raise HTTPException(status_code=503, detail="Entity extractor not initialized")
    return request.app.state.entity_extractor

def get_doc_processor(request: Request) -> "SimpleDocumentProcessor":
    if not hasattr(request.app.state, 'doc_processor') or request.app.state.doc_processor is None:
        logger.error("Dependency Error: Document processor requested but not initialized.")
        raise HTTPException(status_code=503, detail="Document processor not initialized")
    return request.app.state.doc_processor

def get_knowledge_graph_builder(request: Request) -> "SimpleKnowledgeGraphBuilder":
    if not hasattr(request.app.state, 'kg_builder') or request.app.state.kg_builder is None:
        logger.error("Dependency Error: Knowledge graph builder requested but not initialized.")
        raise HTTPException(status_code=503, detail="Knowledge graph builder not initialized")
    return request.app.state.kg_builder

def get_ingestion_service(request: Request) -> "IngestionService":
    if not hasattr(request.app.state, 'ingestion_service') or request.app.state.ingestion_service is None:
        logger.error("Dependency Error: Ingestion service requested but not initialized.")
        raise HTTPException(status_code=503, detail="Ingestion service not initialized")
    return request.app.state.ingestion_service

def get_graph_rag_engine(request: Request) -> "GraphRAGEngine":
    if not hasattr(request.app.state, 'graph_rag_engine') or request.app.state.graph_rag_engine is None:
        logger.error("Dependency Error: Graph RAG engine requested but not initialized.")
        raise HTTPException(status_code=503, detail="Graph RAG engine not initialized")
    return request.app.state.graph_rag_engine
    
# New getters for vector store and embedding service if needed directly
def get_vector_store(request: Request) -> "VectorStore":
    if not hasattr(request.app.state, 'vector_store') or request.app.state.vector_store is None:
        logger.error("Dependency Error: Vector Store requested but not initialized.")
        raise HTTPException(status_code=503, detail="Vector Store not initialized")
    return request.app.state.vector_store

# Note: EmbeddingService is usually an internal dependency, but provide getter if needed
def get_embedding_service(request: Request) -> "EmbeddingService":
    # Attempt to get from vector store first, as it holds the instance used
    if hasattr(request.app.state, 'vector_store') and request.app.state.vector_store:
        if hasattr(request.app.state.vector_store, 'embedding_service'):
            return request.app.state.vector_store.embedding_service
            
    # Fallback or if needed directly (though initialization logic puts it with vector store)
    logger.warning("Attempting to get EmbeddingService directly from state or fallback - may not be the instance used by VectorStore")
    # Placeholder - logic to retrieve/create might be needed here if not tied to vector store
    raise HTTPException(status_code=503, detail="Embedding Service not directly retrievable or initialized")

# --- FastAPI App Creation --- 
def create_app() -> FastAPI:
    """Factory function to create the FastAPI application with all dependencies."""
    app = FastAPI(
        # Use settings obtained at module level for initial app config if needed
        # title=local_settings.APP_NAME, 
        title="GraphRAG API", # Or keep hardcoded
        description="API for the GraphRAG system",
        version="1.0.0",
        lifespan=lifespan
    )

    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Routers now use dependencies that pull from app.state
    api_router = APIRouter(prefix="/api/v1")

    # Use factory functions to get routers
    from graph_rag.api.routers import documents, ingestion, search, query # Ensure modules are imported
    
    documents_router = documents.create_documents_router()
    ingestion_router = ingestion.create_ingestion_router(
        doc_processor_dep=get_doc_processor,
        entity_extractor_dep=get_entity_extractor,
        kg_builder_dep=get_knowledge_graph_builder,
        graph_repository_dep=get_graph_repository
    )
    search_router = search.create_search_router()
    query_router = query.create_query_router()

    # Routers - Prefixes are defined within the factory's router
    api_router.include_router(documents_router, prefix="/documents", tags=["Documents"])
    api_router.include_router(ingestion_router, prefix="/ingestion", tags=["Ingestion"])
    api_router.include_router(search_router, prefix="/search", tags=["Search"])
    api_router.include_router(query_router, prefix="/query", tags=["Query"]) # Assuming query router needs prefix too

    app.include_router(api_router) # Remove prefix="/api/v1" here

    # --- Base Routes ---
    @app.get("/", tags=["Root"], include_in_schema=False)
    async def read_root():
        # Redirect root to API docs
        return RedirectResponse(url="/docs")

    @app.get("/health", tags=["Status"], status_code=status.HTTP_200_OK)
    async def health_check(
        request: Request, 
        # Use Depends with the state-aware getters
        graph_rag_engine: GraphRAGEngine = Depends(get_graph_rag_engine) 
    ):
        """Performs a health check on the application and its core dependencies."""
        # Basic check: If the dependency injection worked, the engine is available.
        # More specific checks can be added here (e.g., check DB connection status)
        checked_dependencies = []
        if graph_rag_engine: # Check if injection succeeded
             checked_dependencies.append("graph_rag_engine")
        # Add checks for other critical dependencies if needed
        # e.g., try: await graph_repo.ping(); checked_dependencies.append("graph_db") except:
        # ... handle failure to ping
        
        # If the dependency injection itself failed, the HTTPException(503) would be raised
        # by the `get_graph_rag_engine` function.
        return {"status": "ok", "dependencies": checked_dependencies}

    # --- Middleware --- 
    @app.middleware("http")
    async def add_request_id(request: Request, call_next):
        """Adds a unique request ID to each incoming request for tracing."""
        request_id = str(uuid.uuid4())
        # You might want to store the request_id in request.state for access in endpoints
        request.state.request_id = request_id 
        start_time = time.time()
        
        # Log request start
        logger.info(f"rid={request_id} path={request.url.path} method={request.method}")
        
        response = await call_next(request)
        
        process_time = time.time() - start_time
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Process-Time"] = str(process_time)
        logger.info(f"rid={request_id} path={request.url.path} method={request.method} status={response.status_code} duration={process_time:.4f}s")
        return response
        
    @app.exception_handler(Exception)
    async def generic_exception_handler(request: Request, exc: Exception):
        request_id = getattr(request.state, 'request_id', 'N/A')
        logger.exception(f"rid={request_id} Unhandled exception: {exc}", exc_info=True)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": f"Internal server error: {exc}", "request_id": request_id},
        )

    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        request_id = getattr(request.state, 'request_id', 'N/A')
        logger.warning(f"rid={request_id} HTTP exception for {request.url}: {exc.status_code} - {exc.detail}")
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.detail, "request_id": request_id},
            headers=exc.headers,
        )

    return app

# --- Main Execution Block (for running with uvicorn directly) ---
# This part is usually not needed when using a process manager like Gunicorn
# or when running tests, but can be useful for direct execution.
if __name__ == "__main__":
    import uvicorn
    # Load settings for direct execution
    exec_settings = get_settings() 
    # Basic logging config for direct run
    logging.basicConfig(level=exec_settings.api_log_level.upper())
    # Create the app instance
    app_instance = create_app() 
    # Run with uvicorn
    uvicorn.run(
        app_instance, 
        host=exec_settings.api_host, 
        port=exec_settings.api_port, 
        log_level=exec_settings.api_log_level.lower()
    )