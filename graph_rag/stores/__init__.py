import warnings

# Re-export SimpleVectorStore from the infrastructure layer
from graph_rag.infrastructure.vector_stores import SimpleVectorStore

# Issue deprecation warning for direct imports from this location
warnings.warn(
    "Importing SimpleVectorStore from graph_rag.stores is deprecated. "
    "Please import from graph_rag.infrastructure.vector_stores instead.",
    DeprecationWarning,
    stacklevel=2
)

# Re-export symbols for backward compatibility
__all__ = ["SimpleVectorStore"] 