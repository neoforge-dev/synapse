from fastapi import FastAPI, APIRouter, Request, HTTPException, status, Depends
import logging
import sys
from contextlib import asynccontextmanager
from graph_rag.config import get_settings
from graph_rag.api.routers import documents, chunks, ingestion, search, query
from graph_rag.api import dependencies as deps
from graph_rag.core.interfaces import GraphRAGEngine
from graph_rag.data_stores.memgraph_store import MemgraphStore, MemgraphStoreError
from graph_rag.core.document_processor import SimpleDocumentProcessor, DocumentProcessor, SentenceSplitter
from graph_rag.core.entity_extractor import SpacyEntityExtractor, EntityExtractor, MockEntityExtractor
from graph_rag.core.persistent_kg_builder import PersistentKnowledgeGraphBuilder
from graph_rag.core.graph_rag_engine import SimpleGraphRAGEngine
from graph_rag.core.knowledge_graph_builder import KnowledgeGraphBuilder, SimpleKnowledgeGraphBuilder
from graph_rag.core.graph_store import GraphStore, MockGraphStore
from graph_rag.core.vector_store import VectorStore, MockVectorStore
from graph_rag.infrastructure.vector_stores import SimpleVectorStore
from graph_rag.api.models import IngestRequest, IngestResponse
from graph_rag.services.ingestion import IngestionService
import uuid
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
from graph_rag.infrastructure.repositories.graph_repository import MemgraphRepository
from neo4j import AsyncGraphDatabase, AsyncDriver
from neo4j.exceptions import Neo4jError
from graph_rag.api.dependencies import get_graph_rag_engine
from typing import Annotated

# --- Logging Configuration ---
# Remove default handlers to prevent duplicate logs in some environments
# (like containers sending stdout/stderr directly)
logging.getLogger().handlers.clear()

# Call factory to get settings for logger setup
local_settings = get_settings()
logging.basicConfig(level=local_settings.api_log_level.upper(), # Use local_settings
                      format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                      handlers=[logging.StreamHandler(sys.stdout)])

logger = logging.getLogger(__name__) # Logger for this module

# --- Lifespan Management for Resources --- 
@asynccontextmanager
async def lifespan(app: FastAPI):
    # --- Startup --- 
    # Get settings instance for lifespan context
    current_settings = get_settings()
    logger.info(f"Starting API... Config: {current_settings.model_dump(exclude={'memgraph_password'})}") # Use current_settings
    app.state.settings = current_settings # Store in state
    app.state.neo4j_driver: Optional[AsyncDriver] = None
    app.state.graph_repository: Optional[MemgraphRepository] = None
    app.state.vector_store = None
    app.state.entity_extractor = None
    app.state.doc_processor = None
    app.state.kg_builder = None
    app.state.graph_rag_engine = None
    app.state.ingestion_service = None

    # 1. Initialize Neo4j Driver
    if not hasattr(app.state, 'neo4j_driver') or app.state.neo4j_driver is None:
        try:
            driver = AsyncGraphDatabase.driver(
                current_settings.get_memgraph_uri(),
                auth=(current_settings.MEMGRAPH_USERNAME, current_settings.MEMGRAPH_PASSWORD.get_secret_value() if current_settings.MEMGRAPH_PASSWORD else None)
            )
            app.state.neo4j_driver = driver
            logger.info("Neo4j AsyncDriver initialized successfully.")
        except Exception as e:
            logger.critical(f"CRITICAL: Failed to initialize Neo4j AsyncDriver: {e}", exc_info=True)
            raise RuntimeError("Failed to initialize database driver") from e

    # 2. Initialize MemgraphGraphRepository (using the driver)
    if not hasattr(app.state, 'graph_repository') or app.state.graph_repository is None:
        if app.state.neo4j_driver:
            app.state.graph_repository = MemgraphRepository(driver=app.state.neo4j_driver)
            logger.info("MemgraphGraphRepository initialized successfully.")
        else:
            logger.error("Cannot initialize MemgraphGraphRepository: Neo4j driver not available.")
            raise RuntimeError("Failed to initialize graph repository due to missing driver")

    # 3. Initialize VectorStore based on settings
    if not hasattr(app.state, 'vector_store') or app.state.vector_store is None:
        try:
            if current_settings.vector_store_type.lower() == 'simple':
                vector_store = SimpleVectorStore(embedding_model_name=current_settings.vector_store_embedding_model)
                app.state.vector_store = vector_store
                logger.info(f"Using SimpleVectorStore with model '{current_settings.vector_store_embedding_model}'.")
            elif current_settings.vector_store_type.lower() == 'mock':
                app.state.vector_store = MockVectorStore()
                logger.info("Using MockVectorStore.")
            else:
                logger.warning(f"Unsupported vector_store_type '{current_settings.vector_store_type}'. Using MockVectorStore.")
                app.state.vector_store = MockVectorStore()
        except Exception as e:
            logger.error(f"Failed to initialize VectorStore: {e}. Using MockVectorStore as fallback.", exc_info=True)
            app.state.vector_store = MockVectorStore()

    # 4. Initialize EntityExtractor based on settings
    if not hasattr(app.state, 'entity_extractor') or app.state.entity_extractor is None:
        try:
            if current_settings.entity_extractor_type.lower() == 'spacy':
                app.state.entity_extractor = SpacyEntityExtractor(model_name=current_settings.entity_extractor_model)
                logger.info(f"Using SpacyEntityExtractor with model '{current_settings.entity_extractor_model}'.")
            elif current_settings.entity_extractor_type.lower() == 'mock':
                app.state.entity_extractor = MockEntityExtractor()
                logger.info("Using MockEntityExtractor.")
            else:
                logger.warning(f"Unsupported entity_extractor_type '{current_settings.entity_extractor_type}'. Using MockEntityExtractor.")
                app.state.entity_extractor = MockEntityExtractor()
        except Exception as e:
            logger.error(f"Failed to initialize EntityExtractor: {e}. Using MockEntityExtractor as fallback.", exc_info=True)
            app.state.entity_extractor = MockEntityExtractor()

    # 5. Initialize DocumentProcessor
    if not hasattr(app.state, 'doc_processor') or app.state.doc_processor is None:
        app.state.doc_processor = SimpleDocumentProcessor(splitter=SentenceSplitter())
        logger.info("Using SimpleDocumentProcessor with SentenceSplitter.")

    # 6. Initialize KG Builder
    if not hasattr(app.state, 'kg_builder') or app.state.kg_builder is None:
        if app.state.graph_repository:
            app.state.kg_builder = SimpleKnowledgeGraphBuilder(graph_store=app.state.graph_repository)
            logger.info("SimpleKnowledgeGraphBuilder initialized.")
        else:
            logger.error("Cannot initialize SimpleKnowledgeGraphBuilder: Graph Repository not available.")

    # 7. Initialize GraphRAGEngine
    if not hasattr(app.state, 'graph_rag_engine') or app.state.graph_rag_engine is None:
        if (
            app.state.graph_repository and
            app.state.vector_store and
            app.state.entity_extractor
        ):
            try:
                app.state.graph_rag_engine = SimpleGraphRAGEngine(
                    graph_store=app.state.graph_repository,
                    vector_store=app.state.vector_store,
                    entity_extractor=app.state.entity_extractor
                )
                logger.info("SimpleGraphRAGEngine initialized successfully.")
            except Exception as e:
                logger.error(f"Failed to initialize SimpleGraphRAGEngine: {e}", exc_info=True)
        else:
            missing = []
            if not app.state.graph_repository: missing.append("GraphRepository")
            if not app.state.vector_store: missing.append("VectorStore")
            if not app.state.entity_extractor: missing.append("EntityExtractor")
            logger.error(f"Cannot initialize SimpleGraphRAGEngine due to missing dependencies: {missing}")

    # 8. Initialize ingestion service
    if not hasattr(app.state, 'ingestion_service') or app.state.ingestion_service is None:
        if app.state.graph_repository:
            try:
                app.state.ingestion_service = IngestionService(repository=app.state.graph_repository)
                logger.info("IngestionService initialized successfully.")
            except Exception as e:
                logger.error(f"Failed to initialize IngestionService: {e}", exc_info=True)
        else:
            logger.error("Cannot initialize IngestionService: Graph Repository not available.")

    logger.info("Application startup dependencies initialized.")
    yield # Application runs here
    
    # --- Shutdown --- 
    logger.info("Shutting down API...")
    if hasattr(app.state, 'neo4j_driver') and app.state.neo4j_driver:
        try:
            await app.state.neo4j_driver.close()
            logger.info("Neo4j AsyncDriver closed.")
        except Exception as e:
            logger.error(f"Error closing Neo4j AsyncDriver: {e}", exc_info=True)
            
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
    logger.info("Application shutdown complete.")

# Dependency Getters (Now rely solely on app state)
def get_graph_repository(request: Request) -> "MemgraphRepository":
    if not hasattr(request.app.state, 'graph_repository') or request.app.state.graph_repository is None:
        raise HTTPException(status_code=503, detail="Graph repository not initialized")
    return request.app.state.graph_repository

def get_entity_extractor(request: Request) -> "EntityExtractor":
    if not hasattr(request.app.state, 'entity_extractor') or request.app.state.entity_extractor is None:
        raise HTTPException(status_code=503, detail="Entity extractor not initialized")
    return request.app.state.entity_extractor

def get_doc_processor(request: Request) -> "SimpleDocumentProcessor":
    if not hasattr(request.app.state, 'doc_processor') or request.app.state.doc_processor is None:
        raise HTTPException(status_code=503, detail="Document processor not initialized")
    return request.app.state.doc_processor

def get_knowledge_graph_builder(request: Request) -> "SimpleKnowledgeGraphBuilder":
    if not hasattr(request.app.state, 'kg_builder') or request.app.state.kg_builder is None:
        raise HTTPException(status_code=503, detail="Knowledge graph builder not initialized")
    return request.app.state.kg_builder

def get_ingestion_service(request: Request) -> "IngestionService":
    if not hasattr(request.app.state, 'ingestion_service') or request.app.state.ingestion_service is None:
        raise HTTPException(status_code=503, detail="Ingestion service not initialized")
    return request.app.state.ingestion_service

def get_graph_rag_engine(request: Request) -> "GraphRAGEngine":
    if not hasattr(request.app.state, 'graph_rag_engine') or request.app.state.graph_rag_engine is None:
        raise HTTPException(status_code=503, detail="Graph RAG engine not initialized")
    return request.app.state.graph_rag_engine

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
    ingestion_router = ingestion.create_ingestion_router(
        doc_processor_dep=deps.get_document_processor,
        entity_extractor_dep=deps.get_entity_extractor,
        kg_builder_dep=deps.get_knowledge_graph_builder,
        graph_repository_dep=deps.get_graph_repository
    )

    # Create query router
    query_router = query.create_query_router()

    # Create documents router - Use the factory function
    documents_router = documents.create_documents_router() # Use the factory function

    # Create chunks router (Assuming a similar factory exists or we use the router directly)
    # chunks_router = chunks.create_chunks_router() # If factory exists
    # Or if the router is defined directly in the module:
    # from graph_rag.api.routers import chunks as chunks_router_module

    # Create search router - import directly
    # search_router = search.create_search_router() # Assuming similar pattern
    search_router = search.create_search_router() # Use the factory function

    # Include all routers
    api_v1_router = APIRouter(prefix="/api/v1")
    api_v1_router.include_router(ingestion_router, prefix="/ingestion", tags=["Ingestion"])
    api_v1_router.include_router(query_router, prefix="/query", tags=["Query"])
    # api_v1_router.include_router(documents_router, prefix="/documents", tags=["Documents"])
    api_v1_router.include_router(documents_router, prefix="/documents", tags=["Documents"]) # Include the router created by the factory
    # api_v1_router.include_router(chunks_router, prefix="/chunks", tags=["Chunks"]) # Uncomment if chunks router is ready
    api_v1_router.include_router(search_router, prefix="/search", tags=["Search"]) # Include the router created by the factory

    app.include_router(api_v1_router)
    # app.include_router(ingestion.router, prefix=\"/api/v1\", tags=[\"Ingestion\"])
    # app.include_router(query.router, prefix=\"/api/v1\", tags=[\"Query\"])
    # app.include_router(documents.router, prefix=\"/api/v1/documents\", tags=[\"Documents\"])
    # app.include_router(chunks.router, prefix=\"/api/v1/chunks\", tags=[\"Chunks\"])
    # app.include_router(search.router, prefix=\"/api/v1/search\", tags=[\"Search\"])

    # --- API Routers --- 
    @app.get("/", tags=["Root"], include_in_schema=False)
    async def read_root():
        return RedirectResponse(url="/docs")

    @app.get("/health", tags=["Status"], status_code=status.HTTP_200_OK)
    async def health_check(
        request: Request, 
        graph_rag_engine: GraphRAGEngine = Depends(get_graph_rag_engine) # Use Depends
    ):
        # Check core engine availability via state
        # if not hasattr(request.app.state, 'graph_rag_engine') or request.app.state.graph_rag_engine is None:
        # Use the injected dependency instead of checking state directly
        if graph_rag_engine is None: # Dependency will raise 503 if it cannot be created
             logger.warning("Health check failed: Core RAG engine not available.")
             # This part might be redundant if get_graph_rag_engine already raises 503
             raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Core RAG engine not available.")
        
        # Check database driver connectivity via state
        # This part might still need state access or a separate DB health check dependency
        if hasattr(request.app.state, 'neo4j_driver') and request.app.state.neo4j_driver:
            try:
                 await request.app.state.neo4j_driver.verify_connectivity()
                 logger.debug("Health check: DB connection verified.")
            except Exception as e:
                 logger.warning(f"Health check failed: DB connection failed: {e}")
                 raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Database connection failed.")
        else:
            # If testing with mock driver in state, this check passes implicitly if mock doesn't raise
            logger.debug("Health check: Neo4j driver not found in state (might be test mock).")
            # Decide if this should be an error in production vs test
            # For now, let it pass if the engine is available
             
        return {"status": "healthy"}

    # --- Middleware --- 
    @app.middleware("http")
    async def add_request_id(request: Request, call_next):
        request_id = str(uuid.uuid4())
        logger.info(f"rid={request_id} path={request.url.path} method={request.method}")
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response

    # --- Exception Handlers --- 
    @app.exception_handler(Exception)
    async def generic_exception_handler(request: Request, exc: Exception):
        logger.error(f"Unhandled exception for request {request.url}: {exc}", exc_info=True)
        return JSONResponse(status_code=500, content={"detail": "Internal Server Error"})

    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        logger.warning(f"HTTP exception for {request.url}: {exc.status_code} - {exc.detail}")
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})

    return app

# Add this if block for direct execution support (uvicorn graph_rag.api.main:app)
if __name__ == "__main__":
    import uvicorn
    # Get settings again for running directly
    run_settings = get_settings()
    uvicorn.run(
        "graph_rag.api.main:create_app", 
        host=run_settings.api_host,
        port=run_settings.api_port,
        log_level=run_settings.api_log_level.lower(),
        reload=run_settings.DEBUG, # Enable reload if DEBUG is True
        factory=True # Indicate uvicorn should call create_app
    )

# Create and export the app instance
app = create_app()