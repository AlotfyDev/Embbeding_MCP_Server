"""Embedding Service package."""
from embedding_mcp.embedding_service.service import EmbeddingService
from embedding_mcp.embedding_service.exceptions import (
    EmbeddingError,
    ModelLoadError,
    VectorDBError,
    DimensionMismatchError,
    ValidationError,
)

__all__ = [
    "EmbeddingService",
    "EmbeddingError",
    "ModelLoadError",
    "VectorDBError",
    "DimensionMismatchError",
    "ValidationError",
]