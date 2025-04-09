from fastapi import FastAPI, APIRouter, Request, HTTPException, status, Depends
import logging
import sys
from contextlib import asynccontextmanager
from graph_rag.config.settings import settings
from graph_rag.api.routers import documents, chunks, ingestion, search, query
from graph_rag.api import dependencies as deps
from graph_rag.data_stores.memgraph_store import MemgraphStore, MemgraphStoreError
from graph_rag.core.document_processor import SimpleDocumentProcessor, DocumentProcessor, SentenceSplitter
from graph_rag.core.entity_extractor import SpacyEntityExtractor, EntityExtractor, MockEntityExtractor
from graph_rag.core.persistent_kg_builder import PersistentKnowledgeGraphBuilder
from graph_rag.core.graph_rag_engine import SimpleGraphRAGEngine, QueryResult
from graph_rag.core.knowledge_graph_builder import KnowledgeGraphBuilder, SimpleKnowledgeGraphBuilder
from graph_rag.core.graph_store import GraphStore, MockGraphStore
from graph_rag.core.vector_store import VectorStore, MockVectorStore
from graph_rag.stores.simple_vector_store import SimpleVectorStore
from graph_rag.api.models import IngestRequest, IngestResponse
import uuid
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
from graph_rag.infrastructure.repositories.graph_repository import MemgraphRepository
from neo4j import AsyncGraphDatabase, AsyncDriver
from neo4j.exceptions import Neo4jError

# --- Logging Configuration ---
# Remove default handlers to prevent duplicate logs in some environments
# (like containers sending stdout/stderr directly)
logging.getLogger().handlers.clear()

# Configure root logger
log_level = logging.DEBUG if settings.DEBUG else logging.INFO
logging.basicConfig(
    level=log_level,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout) # Ensure logs go to stdout
    ]
)

logger = logging.getLogger(__name__) # Logger for this module

# --- Lifespan Management for Resources --- 
@asynccontextmanager
async def lifespan(app: FastAPI):
    # --- Startup --- 
    logger.info(f"Starting API... Config: {settings.model_dump(exclude={'memgraph_password'})}") # Log settings minus secrets
    app.state.settings = settings
    app.state.neo4j_driver: Optional[AsyncDriver] = None
    app.state.graph_repo: Optional[MemgraphGraphRepository] = None
    app.state.vector_store = None
    app.state.entity_extractor = None
    app.state.doc_processor = None
    app.state.kg_builder = None
    app.state.graph_rag_engine = None
    app.state.graph_repository = None

    # 1. Initialize Neo4j Driver
    try:
        driver = AsyncGraphDatabase.driver(
            settings.get_memgraph_uri(),
            auth=(settings.MEMGRAPH_USERNAME, settings.MEMGRAPH_PASSWORD.get_secret_value() if settings.MEMGRAPH_PASSWORD else None)
        )
        # Optional: Verify connectivity early
        # await driver.verify_connectivity()
        app.state.neo4j_driver = driver
        logger.info("Neo4j AsyncDriver initialized successfully.")
    except Exception as e:
        logger.critical(f"CRITICAL: Failed to initialize Neo4j AsyncDriver: {e}", exc_info=True)
        # Stop startup if driver fails
        raise RuntimeError("Failed to initialize database driver") from e

    # 2. Initialize MemgraphGraphRepository (using the driver)
    app.state.graph_repo = MemgraphGraphRepository(driver=app.state.neo4j_driver)
    logger.info("MemgraphGraphRepository initialized successfully.")

    # 3. Initialize VectorStore based on settings
    try:
        if settings.vector_store_type.lower() == 'simple':
            vector_store = SimpleVectorStore(embedding_model_name=settings.vector_store_embedding_model)
            app.state.vector_store = vector_store
            logger.info(f"Using SimpleVectorStore with model '{settings.vector_store_embedding_model}'.")
        # Example for Qdrant (requires installation and config)
        # elif settings.vector_store_type.lower() == 'qdrant':
        #     vector_store = QdrantVectorStore(
        #         host=settings.vector_store_host,
        #         port=settings.vector_store_port,
        #         api_key=settings.vector_store_api_key.get_secret_value() if settings.vector_store_api_key else None,
        #         collection_name=settings.vector_store_collection_name,
        #         embedding_model_name=settings.vector_store_embedding_model
        #     )
        #     app.state.vector_store = vector_store
        #     logger.info(f"Using QdrantVectorStore connecting to {settings.vector_store_host}:{settings.vector_store_port}")
        elif settings.vector_store_type.lower() == 'mock':
            app.state.vector_store = MockVectorStore()
            logger.info("Using MockVectorStore.")
        else:
            logger.warning(f"Unsupported vector_store_type '{settings.vector_store_type}'. Using MockVectorStore.")
            app.state.vector_store = MockVectorStore()
    except Exception as e:
        logger.error(f"Failed to initialize VectorStore: {e}. Using MockVectorStore as fallback.", exc_info=True)
        app.state.vector_store = MockVectorStore()

    # 4. Initialize EntityExtractor based on settings
    try:
        if settings.entity_extractor_type.lower() == 'spacy':
            app.state.entity_extractor = SpacyEntityExtractor(model_name=settings.entity_extractor_model)
            logger.info(f"Using SpacyEntityExtractor with model '{settings.entity_extractor_model}'.")
        elif settings.entity_extractor_type.lower() == 'mock':
            app.state.entity_extractor = MockEntityExtractor()
            logger.info("Using MockEntityExtractor.")
        else:
            logger.warning(f"Unsupported entity_extractor_type '{settings.entity_extractor_type}'. Using MockEntityExtractor.")
            app.state.entity_extractor = MockEntityExtractor()
    except Exception as e:
        logger.error(f"Failed to initialize EntityExtractor: {e}. Using MockEntityExtractor as fallback.", exc_info=True)
        app.state.entity_extractor = MockEntityExtractor()

    # 5. Initialize DocumentProcessor (configure splitter later if needed)
    # TODO: Make splitter configurable via settings.chunk_splitter_type
    app.state.doc_processor = SimpleDocumentProcessor(splitter=SentenceSplitter())
    logger.info("Using SimpleDocumentProcessor with SentenceSplitter.")

    # 6. Initialize KG Builder (only if graph store is available)
    if app.state.graph_repo:
        app.state.kg_builder = SimpleKnowledgeGraphBuilder(graph_store=app.state.graph_repo)
        logger.info("SimpleKnowledgeGraphBuilder initialized.")
    else:
        logger.error("Cannot initialize SimpleKnowledgeGraphBuilder: Graph Repository not available.")

    # 7. Initialize GraphRAGEngine (Simple version for MVP)
    # Requires graph_store, vector_store, and entity_extractor
    if (
        app.state.graph_repo and
        app.state.vector_store and
        app.state.entity_extractor
    ):
        try:
            # Use the Simple engine for MVP, injecting the initialized stores/extractor
            app.state.graph_rag_engine = SimpleGraphRAGEngine(
                graph_store=app.state.graph_repo,
                vector_store=app.state.vector_store,
                entity_extractor=app.state.entity_extractor
            )
            logger.info("SimpleGraphRAGEngine initialized successfully.")
        except Exception as e:
            logger.error(f"Failed to initialize SimpleGraphRAGEngine: {e}", exc_info=True)
    else:
        missing = []
        if not app.state.graph_repo: missing.append("GraphStore")
        if not app.state.vector_store: missing.append("VectorStore")
        if not app.state.entity_extractor: missing.append("EntityExtractor")
        logger.error(f"Cannot initialize SimpleGraphRAGEngine due to missing dependencies: {missing}")

    logger.info("Application startup dependencies initialized.")
    yield # Application runs here
    
    # --- Shutdown --- 
    logger.info("Shutting down API...")
    if app.state.neo4j_driver:
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
    app.state.graph_repo = None
    app.state.neo4j_driver = None
    app.state.settings = None
    app.state.graph_repository = None
    logger.info("Application shutdown complete.")

# Dependency Getters (Using string literals for type hints)
def get_graph_repo(request: Request) -> "MemgraphGraphRepository":
    if not hasattr(request.app.state, 'graph_repo') or request.app.state.graph_repo is None:
        raise HTTPException(status_code=503, detail="Graph repository not initialized")
    return request.app.state.graph_repo

def get_entity_extractor(request: Request) -> "EntityExtractor":
    if not hasattr(request.app.state, 'entity_extractor') or request.app.state.entity_extractor is None:
        raise HTTPException(status_code=503, detail="Entity extractor not initialized")
    return request.app.state.entity_extractor

def get_doc_processor(request: Request) -> "SimpleDocumentProcessor":
    if not hasattr(request.app.state, 'doc_processor') or request.app.state.doc_processor is None:
        raise HTTPException(status_code=503, detail="Document processor not initialized")
    return request.app.state.doc_processor

def get_kg_builder(request: Request) -> "SimpleKnowledgeGraphBuilder":
    if not hasattr(request.app.state, 'kg_builder') or request.app.state.kg_builder is None:
        raise HTTPException(status_code=503, detail="Knowledge graph builder not initialized")
    return request.app.state.kg_builder

# --- FastAPI App Creation --- 
def create_app() -> FastAPI:
    """Factory function to create the FastAPI application with all dependencies."""
    app = FastAPI(
        title="GraphRAG API",
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

    # Routers use dependency injection functions defined above
    # Note: Routers themselves don't need the request object passed during creation.
    # Dependency injection handles passing request context when the endpoint is called.
    ingestion_router = ingestion.create_ingestion_router(
        # Pass the *dependency functions* themselves
        doc_processor_dep=get_doc_processor,
        entity_extractor_dep=get_entity_extractor,
        kg_builder_dep=get_kg_builder,
        graph_repository_dep=get_graph_repo # Use correct getter
    )

    # Create query router with dependencies
    query_router = query.create_query_router()

    # Include routers
    app.include_router(ingestion_router, prefix="/api/v1/ingestion", tags=["ingestion"])
    app.include_router(query_router, prefix="/api/v1/query", tags=["query"])
    app.include_router(documents.router, prefix="/api/v1/documents", tags=["documents"])

    # --- API Routers --- 
    @app.get("/", tags=["Root"], include_in_schema=False)
    async def read_root():
        return RedirectResponse(url="/docs")

    @app.get("/health", tags=["Status"], status_code=status.HTTP_200_OK)
    async def health_check(request: Request):
        # Simplified health check: Check if engine is available
        if not hasattr(request.app.state, 'graph_rag_engine') or request.app.state.graph_rag_engine is None:
             raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Core RAG engine not available.")
        
        # Optional: Add a quick check to the database itself
        try:
             if request.app.state.neo4j_driver:
                 await request.app.state.neo4j_driver.verify_connectivity()
        except Exception as e:
             logger.warning(f"Health check: DB connection failed: {e}")
             raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Database connection failed.")
             
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

# --- Run Command --- 
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "graph_rag.api.main:create_app", 
        factory=True, # Important: Use factory pattern when create_app is used
        host=settings.api_host, 
        port=settings.api_port, 
        log_level=settings.api_log_level.lower(), 
        reload=True
    )

# Create and export the app instance
app = create_app()