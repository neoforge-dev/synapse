from graph_rag.infrastructure.vector_stores.simple_vector_store import SimpleVectorStore

# Import FAISS stores conditionally
try:
    from graph_rag.infrastructure.vector_stores.faiss_vector_store import FaissVectorStore
    from graph_rag.infrastructure.vector_stores.optimized_faiss_vector_store import (
        OptimizedFaissVectorStore,
    )
    __all__ = ["SimpleVectorStore", "FaissVectorStore", "OptimizedFaissVectorStore"]
except ImportError:
    # FAISS not available
    __all__ = ["SimpleVectorStore"]
