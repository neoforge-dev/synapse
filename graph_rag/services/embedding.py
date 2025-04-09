from sentence_transformers import SentenceTransformer
from typing import List, Union
import logging

from graph_rag.config.settings import settings # Updated import
from graph_rag.core.interfaces import EmbeddingService # Import the protocol

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SentenceTransformerEmbeddingService(EmbeddingService): # Implement the protocol
    """Service to handle text embedding generation using Sentence Transformers."""
    _model: SentenceTransformer
    _model_name: str

    def __init__(self, model_name: str = settings.EMBEDDING_MODEL_NAME):
        self._model_name = model_name
        self._load_model() # Load model on initialization

    def _load_model(self) -> None:
        """Loads the Sentence Transformer model."""
        logger.info(f"Loading embedding model: {self._model_name}")
        try:
            # Keep disabled components if only embeddings needed
            self._model = SentenceTransformer(self._model_name)
            logger.info("Embedding model loaded successfully.")
        except Exception as e:
            logger.error(f"Failed to load embedding model '{self._model_name}': {e}", exc_info=True)
            # Let the application decide how to handle this critical failure
            raise RuntimeError(f"Could not load embedding model: {self._model_name}") from e

    def encode(self, text: str | List[str]) -> List[float] | List[List[float]]:
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

    def get_embedding_dim(self) -> int:
        """Returns the dimension of the embeddings produced by the model."""
        dim = self._model.get_sentence_embedding_dimension()
        if dim is None:
             logger.error("Could not determine embedding dimension.")
             raise ValueError("Embedding dimension is not available for the loaded model.")
        return dim

# Remove classmethod decorators and _get_model calls within methods
# Remove example usage block 