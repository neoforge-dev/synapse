from fastapi import FastAPI, APIRouter, Request, HTTPException, status, Depends
import logging
import sys
from contextlib import asynccontextmanager
from graph_rag.config.settings import settings
from graph_rag.api.routers import documents, chunks, ingestion, search
from graph_rag.api import dependencies as deps
from graph_rag.data_stores.memgraph_store import MemgraphStore, MemgraphStoreError
from graph_rag.services.embedding import SentenceTransformerEmbeddingService
from graph_rag.core.document_processor import SimpleDocumentProcessor, DocumentProcessor, SentenceSplitter
from graph_rag.core.entity_extractor import SpacyEntityExtractor, EntityExtractor, MockEntityExtractor
from graph_rag.core.persistent_kg_builder import PersistentKnowledgeGraphBuilder
from graph_rag.core.graph_rag_engine import GraphRAGEngine as ConcreteGraphRAGEngine, SimpleGraphRAGEngine, QueryResult
from graph_rag.core.knowledge_graph_builder import KnowledgeGraphBuilder, SimpleKnowledgeGraphBuilder
from graph_rag.core.graph_store import GraphStore, MockGraphStore
from graph_rag.core.vector_store import VectorStore, MockVectorStore
from graph_rag.api.models import IngestRequest, IngestResponse
import uuid
from fastapi.responses import JSONResponse, RedirectResponse

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
    logger.info(f"Starting {settings.APP_NAME} v{settings.APP_VERSION}...")
    logger.info(f"Debug mode: {settings.DEBUG}")
    
    # 1. Initialize Settings (already loaded globally, but can store in state)
    app.state.settings = settings
    
    # 2. Initialize and Connect MemgraphStore
    app.state.memgraph_store = None # Initialize as None
    try:
        store = MemgraphStore(settings=settings)
        await store.connect() # Establish connection
        # Apply constraints on startup?
        # await store.apply_schema_constraints() 
        app.state.memgraph_store = store
        logger.info(f"Successfully connected to Memgraph at {settings.get_memgraph_uri()}")
    except (MemgraphStoreError, ConnectionError) as e:
        logger.critical(f"CRITICAL: Failed to connect to Memgraph: {e}", exc_info=True)
        # Application cannot function without the graph store
        # Allow app to start but log critical failure. Endpoints depending on store will fail.
        # Alternatively, could raise an exception here to prevent FastAPI startup.
    except Exception as e:
        logger.critical(f"CRITICAL: An unexpected error occurred during MemgraphStore initialization: {e}", exc_info=True)
        
    # 3. Initialize Embedding Service
    app.state.embedding_service = None
    try:
        app.state.embedding_service = SentenceTransformerEmbeddingService(model_name=settings.EMBEDDING_MODEL_NAME)
        # Trigger model loading & get dimension to check it works
        _ = app.state.embedding_service.get_embedding_dim() 
        logger.info(f"Embedding service initialized with model: {settings.EMBEDDING_MODEL_NAME}")
    except Exception as e:
        logger.error(f"Failed to initialize Embedding Service: {e}", exc_info=True)
        # Decide if this is critical? Maybe allow startup but log error.
        
    # 4. Initialize other components
    app.state.doc_processor = DocumentProcessor(splitter=SentenceSplitter())
    
    # Initialize Entity Extractor based on settings
    if settings.entity_extractor_type.lower() == 'spacy':
        try:
            app.state.entity_extractor = SpacyEntityExtractor(model_name=settings.entity_extractor_model)
            logger.info(f"Using SpacyEntityExtractor with model '{settings.entity_extractor_model}'.")
        except Exception as e:
             logger.error(f"Failed to initialize SpacyEntityExtractor: {e}. Falling back to MockEntityExtractor.", exc_info=True)
             app.state.entity_extractor = MockEntityExtractor()
    elif settings.entity_extractor_type.lower() == 'mock':
        app.state.entity_extractor = MockEntityExtractor()
        logger.info("Using MockEntityExtractor.")
    else:
        logger.warning(f"Unsupported entity_extractor_type '{settings.entity_extractor_type}'. Using MockEntityExtractor.")
        app.state.entity_extractor = MockEntityExtractor()
        
    # 5. Initialize KG Builder (requires connected store)
    app.state.kg_builder = None
    if app.state.memgraph_store:
        app.state.kg_builder = PersistentKnowledgeGraphBuilder(graph_store=app.state.memgraph_store)
        logger.info("Persistent Knowledge Graph Builder initialized.")
    else:
        logger.error("Cannot initialize PersistentKnowledgeGraphBuilder: MemgraphStore connection failed.")

    # 6. Initialize GraphRAGEngine (requires all components)
    app.state.graph_rag_engine = None
    if (
        app.state.memgraph_store and
        app.state.embedding_service and 
        app.state.doc_processor and
        app.state.entity_extractor and
        app.state.kg_builder
    ):
        try:
            # MemgraphStore implements the searcher protocols
            app.state.graph_rag_engine = ConcreteGraphRAGEngine(
                document_processor=app.state.doc_processor,
                entity_extractor=app.state.entity_extractor,
                kg_builder=app.state.kg_builder,
                embedding_service=app.state.embedding_service,
                vector_searcher=app.state.memgraph_store, # Store acts as searcher
                keyword_searcher=app.state.memgraph_store, # Store acts as searcher
                graph_searcher=app.state.memgraph_store    # Store *could* act as graph searcher if implemented
            )
            logger.info("GraphRAGEngine initialized successfully.")
        except Exception as e:
            logger.error(f"Failed to initialize GraphRAGEngine: {e}", exc_info=True)
    else:
        logger.error("Cannot initialize GraphRAGEngine due to missing dependencies.")

    logger.info("Application startup complete.")
    yield # Application runs here
    
    # --- Shutdown --- 
    logger.info(f"Shutting down {settings.APP_NAME}...")
    # Close Memgraph connection
    if app.state.memgraph_store:
        try:
            await app.state.memgraph_store.close()
            logger.info("Memgraph connection closed.")
        except Exception as e:
            logger.error(f"Error closing Memgraph connection: {e}", exc_info=True)
            
    # Add any other cleanup (e.g., close file handles, release resources)
    # Clear state (optional)
    app.state.graph_rag_engine = None
    app.state.kg_builder = None
    app.state.entity_extractor = None
    app.state.doc_processor = None
    app.state.embedding_service = None
    app.state.memgraph_store = None
    app.state.settings = None
    logger.info("Application shutdown complete.")

# --- FastAPI App Setup ---
def create_app() -> FastAPI:
    app = FastAPI(
        title="Synapse API",
        description="API for ingesting documents and querying the Synapse Graph-Enhanced RAG system.",
        version=settings.model_dump().get('version', '0.1.0'),
        lifespan=lifespan
    )

    # --- API Routers --- 
    # Root endpoint
    @app.get("/", tags=["Root"], include_in_schema=False)
    async def read_root():
        # Redirect to docs or return basic info
        return RedirectResponse(url="/docs")
        # return {"message": "Welcome to the Synapse API", "version": settings.model_dump().get('version', '0.1.0')}

    # Health check endpoint - Now checks essential component availability
    @app.get("/health", tags=["Status"], status_code=status.HTTP_200_OK)
    async def health_check(request: Request):
        # Check if critical components initialized correctly during lifespan startup
        if (
            not hasattr(request.app.state, 'memgraph_store') or request.app.state.memgraph_store is None or
            not hasattr(request.app.state, 'embedding_service') or request.app.state.embedding_service is None or
            not hasattr(request.app.state, 'graph_rag_engine') or request.app.state.graph_rag_engine is None
        ):
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Core components not available.")
        
        # Optionally add a quick check to the DB
        try:
            store: MemgraphStore = request.app.state.memgraph_store
            # A simple, fast query to check liveness
            await store.execute_read("RETURN 1") 
        except Exception as e:
            logger.error(f"Health check failed during DB query: {e}")
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Graph database connectivity issue.")
        
        return {"status": "healthy"}

    # Include routers
    api_router = APIRouter(prefix="/api/v1")
    api_router.include_router(documents.router, prefix="/documents", tags=["Documents"])
    api_router.include_router(chunks.router, prefix="/chunks", tags=["Chunks"])
    api_router.include_router(ingestion.router, prefix="/ingestion", tags=["Ingestion"])
    api_router.include_router(search.router, prefix="/search", tags=["Search"])

    app.include_router(api_router)

    # --- Middleware --- 
    @app.middleware("http")
    async def add_request_id(request: Request, call_next):
        request_id = str(uuid.uuid4())
        # You can store this request ID in logs or pass it down
        logger.info(f"rid={request_id} path={request.url.path} method={request.method}")
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response

    # --- Exception Handlers --- 
    @app.exception_handler(Exception)
    async def generic_exception_handler(request: Request, exc: Exception):
        logger.error(f"Unhandled exception for request {request.url}: {exc}", exc_info=True)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": "An internal server error occurred.", "error_type": type(exc).__name__},
        )

    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        # Keep FastAPI's default behavior for HTTPExceptions but log it
        logger.warning(f"HTTP exception for request {request.url}: {exc.status_code} - {exc.detail}")
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.detail},
            headers=getattr(exc, "headers", None),
        )

    # --- Dependency Injection Functions --- 
    # These functions retrieve instances from app.state, setup during lifespan
    def get_doc_processor(request: Request) -> DocumentProcessor:
        if not request.app.state.doc_processor:
            raise HTTPException(status_code=503, detail="Document Processor not available.")
        return request.app.state.doc_processor
        
    def get_entity_extractor(request: Request) -> EntityExtractor:
        if not request.app.state.entity_extractor:
            raise HTTPException(status_code=503, detail="Entity Extractor not available.")
        return request.app.state.entity_extractor
        
    def get_kg_builder(request: Request) -> KnowledgeGraphBuilder:
        if not request.app.state.kg_builder:
            raise HTTPException(status_code=503, detail="Knowledge Graph Builder not available.")
        return request.app.state.kg_builder
        
    def get_rag_engine(request: Request) -> GraphRAGEngine:
        if not request.app.state.graph_rag_engine:
            raise HTTPException(status_code=503, detail="RAG Engine not available.")
        return request.app.state.graph_rag_engine

    # --- Routers --- 
    # Pass dependency *functions* using Depends() within the router's endpoints
    # Or pass the functions to the router factory if designed that way
    app.include_router(
        ingestion.create_ingestion_router(
            # Pass the dependency getter functions
            doc_processor_dep=lambda: Depends(get_doc_processor), 
            entity_extractor_dep=lambda: Depends(get_entity_extractor),
            kg_builder_dep=lambda: Depends(get_kg_builder),
        ), 
        prefix="/api/v1/ingestion", 
        tags=["Ingestion"]
    )

    return app

# --- Run Command (for local development) --- 
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "graph_rag.api.main:create_app", 
        host=settings.api_host, 
        port=settings.api_port, 
        log_level=settings.api_log_level.lower(), 
        reload=True # Enable reload for development
    )