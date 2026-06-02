"""Embedding Model Layer - Abstract base class."""
from __future__ import annotations

from abc import ABC, abstractmethod


class EmbeddingModel(ABC):
    """Abstract interface for embedding models - pluggable architecture."""

    @abstractmethod
    def embed(self, text: str) -> list[float]:
        """Embed a single text as document (passage)."""
        ...

    @abstractmethod
    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Embed multiple texts in batch for performance."""
        ...

    @abstractmethod
    def embed_query(self, text: str) -> list[float]:
        """Embed a query with query prefix for semantic search."""
        ...

    @property
    @abstractmethod
    def dim(self) -> int:
        """Return embedding dimension."""
        ...