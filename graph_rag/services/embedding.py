import logging
from typing import Any, Optional

# DO NOT import SentenceTransformer at module level - lazy load on first use
# This saves ~3.5s startup time and ~1.2GB memory when not using sentence-transformers

# Change import to use the factory
from graph_rag.config import get_settings
from graph_rag.core.interfaces import EmbeddingService  # Import the protocol

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Instantiate settings using the factory
settings = get_settings()


class SentenceTransformerEmbeddingService(EmbeddingService):  # Implement the protocol
    """Service to handle text embedding generation using Sentence Transformers.

    Uses lazy loading to defer model loading until first use, saving ~3.5s startup time
    and ~1.2GB memory when the service is not actively used.
    """

    _model: Optional[Any]  # Will be SentenceTransformer once loaded
    _model_name: str

    def __init__(self, model_name: str = settings.vector_store_embedding_model):
        self._model_name = model_name
        self._model = None  # Deferred initialization - lazy load on first use

    def _ensure_model_loaded(self) -> None:
        """Lazy load SentenceTransformer model on first use.

        This method loads the heavy PyTorch + SentenceTransformer dependencies only when
        actually needed, reducing startup time by ~3.5s and memory by ~1.2GB.
        """
        if self._model is not None:
            return  # Already loaded

        logger.info(f"Loading embedding model: {self._model_name} (lazy initialization)")
        try:
            # Check if we should skip import (for lightweight test runs)
            skip_import = __import__("os").getenv("SKIP_SPACY_IMPORT") == "1"
            if skip_import:
                raise RuntimeError("SentenceTransformer unavailable (SKIP_SPACY_IMPORT=1)")

            # Lazy import - only load when actually needed
            from sentence_transformers import SentenceTransformer

            self._model = SentenceTransformer(self._model_name)
            logger.info("Embedding model loaded successfully (lazy initialization).")
        except ImportError as e:
            logger.error(
                f"Failed to import SentenceTransformer: {e}. Install with: pip install sentence-transformers",
                exc_info=True,
            )
            raise RuntimeError(
                "SentenceTransformer not available. Install with: pip install sentence-transformers"
            ) from e
        except Exception as e:
            logger.error(
                f"Failed to load embedding model '{self._model_name}': {e}",
                exc_info=True,
            )
            raise RuntimeError(
                f"Could not load embedding model: {self._model_name}"
            ) from e

    async def encode(self, text: str | list[str]) -> list[float] | list[list[float]]:
        """Encodes a single text or a list of texts into embeddings."""
        self._ensure_model_loaded()  # Lazy load model on first use
        try:
            # encode() returns numpy arrays, convert to list for JSON/DB compatibility
            embeddings = self._model.encode(text)
            if isinstance(text, str):
                # Ensure single embedding is returned as List[float]
                return embeddings.tolist()
            else:
                # Ensure list of embeddings is returned as List[List[float]]
                return [emb.tolist() for emb in embeddings]
        except Exception as e:
            logger.error(f"Failed to encode text: {e}", exc_info=True)
            # Propagate error
            raise RuntimeError("Embedding encoding failed") from e

    async def generate_embedding(self, text: str) -> list[float]:
        """Generates a vector embedding for the given text (protocol method)."""
        return await self.encode(text)

    async def encode_query(self, text: str) -> list[float]:
        """Encodes a query text into embeddings (compatibility method)."""
        return await self.generate_embedding(text)

    def get_embedding_dimension(self) -> int:
        """Returns the dimension of the embeddings produced by the model."""
        self._ensure_model_loaded()  # Lazy load model on first use
        dim = self._model.get_sentence_embedding_dimension()
        if dim is None:
            logger.error("Could not determine embedding dimension.")
            raise ValueError(
                "Embedding dimension is not available for the loaded model."
            )
        return dim

    def get_embedding_dim(self) -> int:
        """Returns the dimension of the embeddings produced by the model (compatibility method)."""
        return self.get_embedding_dimension()


# Remove classmethod decorators and _get_model calls within methods
# Remove example usage block
