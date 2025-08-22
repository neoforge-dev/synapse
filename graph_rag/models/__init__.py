"""Models package for graph_rag."""

# Import from main models module using absolute import to avoid circular imports
import importlib.util
import os

# Get the path to models.py
models_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'models.py')
spec = importlib.util.spec_from_file_location("main_models", models_path)
main_models = importlib.util.module_from_spec(spec)
spec.loader.exec_module(main_models)

# Export the main model classes
Chunk = main_models.Chunk
Document = main_models.Document
Entity = main_models.Entity
Relationship = main_models.Relationship
ProcessedDocument = main_models.ProcessedDocument

# Import from consolidated_response module
from .consolidated_response import (
    ArchitecturalPatternResponse,
    ConsolidatedAnswerResponse,
    ConsolidatedQueryRequest,
    MachineReadableResponse,
    SourceResponse,
    SuccessMetricResponse,
    VectorStoreStatusResponse,
)

__all__ = [
    # Main models
    "Chunk",
    "Document",
    "Entity",
    "Relationship",
    "ProcessedDocument",
    # Consolidated response models
    "ConsolidatedAnswerResponse",
    "ConsolidatedQueryRequest",
    "VectorStoreStatusResponse",
    "ArchitecturalPatternResponse",
    "SuccessMetricResponse",
    "MachineReadableResponse",
    "SourceResponse",
]
