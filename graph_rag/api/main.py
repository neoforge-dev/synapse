from fastapi import FastAPI, APIRouter, Request, HTTPException, status, Depends
import logging
import sys
from contextlib import asynccontextmanager
from graph_rag.config.settings import settings
from graph_rag.api.routers import documents, chunks, ingestion, search, health
from graph_rag.api import dependencies as deps
from graph_rag.data_stores.memgraph_store import MemgraphStore, MemgraphStoreError
from graph_rag.core.document_processor import SimpleDocumentProcessor, DocumentProcessor, SentenceSplitter
from graph_rag.core.entity_extractor import SpacyEntityExtractor, EntityExtractor, MockEntityExtractor
from graph_rag.core.persistent_kg_builder import PersistentKnowledgeGraphBuilder
from graph_rag.core.graph_rag_engine import SimpleGraphRAGEngine, QueryResult
from graph_rag.core.knowledge_graph_builder import KnowledgeGraphBuilder
from graph_rag.core.graph_store import GraphStore, MockGraphStore
from graph_rag.core.vector_store import VectorStore, MockVectorStore
from graph_rag.stores.simple_vector_store import SimpleVectorStore
from graph_rag.api.models import IngestRequest, IngestResponse
import uuid
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
from graph_rag.infrastructure.repositories.graph_repository import GraphRepository

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
    app.state.memgraph_store = None
    app.state.vector_store = None
    app.state.entity_extractor = None
    app.state.doc_processor = None
    app.state.kg_builder = None
    app.state.graph_rag_engine = None

    # 1. Initialize GraphStore (Memgraph)
    try:
        graph_store = MemgraphStore(
            host=settings.memgraph_host,
            port=settings.memgraph_port,
            user=settings.memgraph_user,
            password=settings.memgraph_password.get_secret_value() if settings.memgraph_password else None,
            use_ssl=settings.memgraph_use_ssl,
            max_retries=settings.memgraph_max_retries,
            retry_delay=settings.memgraph_retry_delay
        )
        # await graph_store.connect() # Connect called in constructor now
        app.state.memgraph_store = graph_store
        logger.info(f"MemgraphStore initialized for {settings.memgraph_host}:{settings.memgraph_port}")
    except Exception as e:
        logger.critical(f"CRITICAL: Failed to initialize MemgraphStore: {e}", exc_info=True)
        # Consider stopping startup if Memgraph is essential

    # 2. Initialize VectorStore based on settings
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

    # 3. Initialize EntityExtractor based on settings
    try:
        if settings.entity_extractor_type.lower() == 'spacy':
            entity_extractor = SpacyEntityExtractor(model_name=settings.entity_extractor_model)
            app.state.entity_extractor = entity_extractor
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

    # 4. Initialize DocumentProcessor (configure splitter later if needed)
    # TODO: Make splitter configurable via settings.chunk_splitter_type
    app.state.doc_processor = SimpleDocumentProcessor(splitter=SentenceSplitter())
    logger.info("Using SimpleDocumentProcessor with SentenceSplitter.")

    # 5. Initialize KG Builder (only if graph store is available)
    if app.state.memgraph_store:
        app.state.kg_builder = PersistentKnowledgeGraphBuilder(graph_store=app.state.memgraph_store)
        logger.info("Persistent Knowledge Graph Builder initialized.")
    else:
        logger.error("Cannot initialize PersistentKnowledgeGraphBuilder: MemgraphStore not available.")

    # 6. Initialize GraphRAGEngine (Simple version for MVP)
    # Requires graph_store, vector_store, and entity_extractor
    if (
        app.state.memgraph_store and
        app.state.vector_store and
        app.state.entity_extractor
    ):
        try:
            # Use the Simple engine for MVP, injecting the initialized stores/extractor
            app.state.graph_rag_engine = SimpleGraphRAGEngine(
                graph_store=app.state.memgraph_store,
                vector_store=app.state.vector_store,
                entity_extractor=app.state.entity_extractor
            )
            logger.info("SimpleGraphRAGEngine initialized successfully.")
        except Exception as e:
            logger.error(f"Failed to initialize SimpleGraphRAGEngine: {e}", exc_info=True)
    else:
        missing = []
        if not app.state.memgraph_store: missing.append("GraphStore")
        if not app.state.vector_store: missing.append("VectorStore")
        if not app.state.entity_extractor: missing.append("EntityExtractor")
        logger.error(f"Cannot initialize SimpleGraphRAGEngine due to missing dependencies: {missing}")

    logger.info("Application startup complete.")
    yield # Application runs here
    
    # --- Shutdown --- 
    logger.info("Shutting down API...")
    if app.state.memgraph_store:
        try:
            # Use close method defined in MemgraphStore
            app.state.memgraph_store.close() 
            logger.info("Memgraph connection closed.")
        except Exception as e:
            logger.error(f"Error closing Memgraph connection: {e}", exc_info=True)
            
    # Clear state (optional but good practice)
    app.state.graph_rag_engine = None
    app.state.kg_builder = None
    app.state.entity_extractor = None
    app.state.doc_processor = None
    app.state.vector_store = None
    app.state.memgraph_store = None
    app.state.settings = None
    logger.info("Application shutdown complete.")

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

    # Create dependencies
    graph_repository = GraphRepository()
    doc_processor = SimpleDocumentProcessor()
    entity_extractor = SpacyEntityExtractor()
    kg_builder = KnowledgeGraphBuilder(graph_repository)

    # Create routers with dependencies
    ingestion_router = ingestion.create_ingestion_router(
        doc_processor_dep=lambda: doc_processor,
        entity_extractor_dep=lambda: entity_extractor,
        kg_builder_dep=lambda: kg_builder,
        graph_repository_dep=lambda: graph_repository
    )

    search_router = search.create_search_router(
        graph_repository_dep=lambda: graph_repository
    )

    # Include routers
    app.include_router(ingestion_router, prefix="/api/v1/ingestion", tags=["ingestion"])
    app.include_router(search_router, prefix="/api/v1/search", tags=["search"])
    app.include_router(health.router, prefix="/api/v1", tags=["health"])

    # --- API Routers --- 
    @app.get("/", tags=["Root"], include_in_schema=False)
    async def read_root():
        return RedirectResponse(url="/docs")

    @app.get("/health", tags=["Status"], status_code=status.HTTP_200_OK)
    async def health_check(request: Request):
        # Simplified health check: Check if engine is available
        if not hasattr(request.app.state, 'graph_rag_engine') or request.app.state.graph_rag_engine is None:
             raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Core RAG engine not available.")
        # Optional: Add quick checks for Memgraph/Vector store connectivity if needed
        # try:
        #     if request.app.state.memgraph_store: await request.app.state.memgraph_store.execute_read("RETURN 1")
        #     # Add vector store check if it has a ping/health method
        # except Exception as e:
        #     logger.error(f"Health check failed during dependency check: {e}")
        #     raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Core dependency connectivity issue.")
        return {"status": "healthy"}

    api_router = APIRouter(prefix="/api/v1")
    # TODO: Wire up actual endpoints using dependency injection
    # Example: api_router.include_router(search.router, prefix="/query", tags=["Query"])
    # Need to create/update routers (e.g., ingestion, search) to use the DI functions below

    app.include_router(api_router)

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

    # --- Dependency Injection Functions (Getters) --- 
    def get_vector_store(request: Request) -> VectorStore:
        if not request.app.state.vector_store:
            raise HTTPException(status_code=503, detail="Vector Store not available.")
        return request.app.state.vector_store

    def get_graph_store(request: Request) -> GraphStore:
        if not request.app.state.memgraph_store:
            raise HTTPException(status_code=503, detail="Graph Store not available.")
        return request.app.state.memgraph_store
        
    def get_entity_extractor(request: Request) -> EntityExtractor:
        if not request.app.state.entity_extractor:
            raise HTTPException(status_code=503, detail="Entity Extractor not available.")
        return request.app.state.entity_extractor
        
    # Removed get_kg_builder, get_doc_processor as they are mainly for ingestion path
    # The RAG engine encapsulates the core query logic
    def get_rag_engine(request: Request) -> SimpleGraphRAGEngine:
        # Ensure we return the correct engine type (SimpleGraphRAGEngine for now)
        if not request.app.state.graph_rag_engine or not isinstance(request.app.state.graph_rag_engine, SimpleGraphRAGEngine):
            raise HTTPException(status_code=503, detail="Simple RAG Engine not available.")
        return request.app.state.graph_rag_engine

    # --- Wire Up Routers Using Dependencies --- 
    # Example: Query Router using the RAG engine
    query_router = APIRouter()
    @query_router.post("/", response_model=QueryResult)
    async def handle_query(
        query_text: str = Body(..., embed=True),
        k: int = Body(3, embed=True),
        include_graph: bool = Body(True, embed=True),
        rag_engine: SimpleGraphRAGEngine = Depends(get_rag_engine)
    ):
        logger.info(f"Received API query: '{query_text}'")
        config = {"k": k, "include_graph": include_graph}
        try:
            result = rag_engine.query(query_text=query_text, config=config)
            return result
        except Exception as e:
            logger.error(f"Error handling query via API: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail="Error processing query.")
            
    app.include_router(query_router, prefix="/api/v1/query", tags=["Query"])

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