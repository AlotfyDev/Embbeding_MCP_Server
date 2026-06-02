"""Vector DB Adapter Layer - Abstract base class."""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class SearchResult:
    """Result from vector similarity search."""
    key: str
    score: float
    metadata: dict

    def to_dict(self) -> dict:
        return {"key": self.key, "score": self.score, "metadata": self.metadata}


class VectorDB(ABC):
    """Abstract interface for vector databases - adapter pattern."""

    @abstractmethod
    def store(self, key: str, vector: list[float], metadata: dict | None = None) -> None:
        """Store a vector with associated key and metadata."""
        ...

    @abstractmethod
    def store_batch(self, items: list[tuple[str, list[float], dict | None]]) -> None:
        """Store multiple vectors in batch."""
        ...

    @abstractmethod
    def search(self, vector: list[float], top_k: int = 10, filters: dict | None = None) -> list[SearchResult]:
        """Find nearest neighbors to the query vector."""
        ...

    @abstractmethod
    def delete(self, key: str) -> None:
        """Delete a vector by key."""
        ...

    @abstractmethod
    def count(self) -> int:
        """Return total number of vectors stored."""
        ...

    @abstractmethod
    def clear(self) -> None:
        """Clear all vectors from the database."""
        ...