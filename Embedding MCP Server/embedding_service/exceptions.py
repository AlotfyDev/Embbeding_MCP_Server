"""Embedding service error hierarchy."""
from __future__ import annotations


class EmbeddingError(Exception):
    """Base exception for embedding operations."""
    def __init__(self, message: str, code: str = "EMBEDDING_ERROR"):
        self.code = code
        super().__init__(message)


class ModelLoadError(EmbeddingError):
    """Failed to load embedding model."""
    pass


class VectorDBError(EmbeddingError):
    """Vector database operation failed."""
    pass


class DimensionMismatchError(EmbeddingError):
    """Vector dimension mismatch."""
    pass


class ValidationError(EmbeddingError):
    """Input validation failed."""
    pass