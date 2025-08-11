import logging

try:
    if __import__("os").getenv("SKIP_SPACY_IMPORT") == "1":
        # During hot-path coverage runs, avoid importing torch via sentence-transformers
        SentenceTransformer = None  # type: ignore[assignment]
    else:
        from sentence_transformers import SentenceTransformer
except Exception:
    # Fallback to None if import fails; actual use will raise
    SentenceTransformer = None  # type: ignore[assignment]

# Change import to use the factory
from graph_rag.config import get_settings
from graph_rag.core.interfaces import EmbeddingService  # Import the protocol

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Instantiate settings using the factory
settings = get_settings()


class SentenceTransformerEmbeddingService(EmbeddingService):  # Implement the protocol
    """Service to handle text embedding generation using Sentence Transformers."""

    _model: SentenceTransformer
    _model_name: str

    def __init__(self, model_name: str = settings.vector_store_embedding_model):
        self._model_name = model_name
        self._load_model()  # Load model on initialization

    def _load_model(self) -> None:
        """Loads the Sentence Transformer model."""
        logger.info(f"Loading embedding model: {self._model_name}")
        try:
            # Keep disabled components if only embeddings needed
            if SentenceTransformer is None:
                raise RuntimeError("SentenceTransformer unavailable in this environment")
            self._model = SentenceTransformer(self._model_name)
            logger.info("Embedding model loaded successfully.")
        except Exception as e:
            logger.error(
                f"Failed to load embedding model '{self._model_name}': {e}",
                exc_info=True,
            )
            # Let the application decide how to handle this critical failure
            raise RuntimeError(
                f"Could not load embedding model: {self._model_name}"
            ) from e

    async def encode(self, text: str | list[str]) -> list[float] | list[list[float]]:
        """Encodes a single text or a list of texts into embeddings."""
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
