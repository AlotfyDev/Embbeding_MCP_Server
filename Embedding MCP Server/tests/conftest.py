"""Shared fixtures for all unit tests."""
from __future__ import annotations

import sys
from pathlib import Path

_src = Path(__file__).resolve().parent.parent
if str(_src) not in sys.path:
    sys.path.insert(0, str(_src))

if "embedding_mcp" not in sys.modules:
    import importlib.util
    _spec = importlib.util.spec_from_file_location(
        "embedding_mcp", _src / "__init__.py",
        submodule_search_locations=[str(_src)],
    )
    _embedding_mcp = importlib.util.module_from_spec(_spec)
    sys.modules["embedding_mcp"] = _embedding_mcp
    _spec.loader.exec_module(_embedding_mcp)

import numpy as np
import pytest

from embedding_mcp.embedding_model import EmbeddingModel
from embedding_mcp.embedding_service.exceptions import DimensionMismatchError
from embedding_mcp.vector_db.base import VectorDB, SearchResult


class MockEmbeddingModel(EmbeddingModel):
    """Mock model that returns deterministic text-dependent vectors (no ONNX)."""

    def __init__(self, dim: int = 384):
        self._dim = dim
        self.embed_calls: list[str] = []
        self.embed_batch_calls: list[list[str]] = []
        self.embed_query_calls: list[str] = []

    def _make_vec(self, text: str, offset: float = 0.0) -> list[float]:
        val = (sum(ord(c) for c in text) % 100) / 100.0 + offset
        return [val] * self._dim

    def embed(self, text: str) -> list[float]:
        self.embed_calls.append(text)
        return self._make_vec(text)

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        self.embed_batch_calls.append(texts)
        return [self._make_vec(t) for t in texts]

    def embed_query(self, text: str) -> list[float]:
        self.embed_query_calls.append(text)
        return self._make_vec(text, offset=0.5)

    @property
    def dim(self) -> int:
        return self._dim


class MockVectorDB(VectorDB):
    """Mock vector DB that stores in-memory dict (no FAISS)."""

    def __init__(self, dim: int = 384):
        self._dim = dim
        self._data: dict[str, tuple[list[float], dict]] = {}

    def _check_dim(self, vector: list[float]) -> None:
        if len(vector) != self._dim:
            raise DimensionMismatchError(
                f"Vector length {len(vector)} != expected {self._dim}"
            )

    def store(self, key: str, vector: list[float], metadata: dict | None = None) -> None:
        self._check_dim(vector)
        self._data[key] = (vector, metadata or {})

    def store_batch(self, items: list[tuple[str, list[float], dict | None]]) -> None:
        for key, vector, metadata in items:
            self._check_dim(vector)
            self._data[key] = (vector, metadata or {})

    def search(self, vector: list[float], top_k: int = 10, filters: dict | None = None) -> list[SearchResult]:
        self._check_dim(vector)
        query = np.array(vector, dtype=np.float32)
        scored: list[tuple[float, str, dict]] = []
        for key, (vec, meta) in self._data.items():
            if filters and not self._matches_filters(meta, filters):
                continue
            score = float(np.dot(query, np.array(vec, dtype=np.float32)))
            scored.append((score, key, meta))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [SearchResult(key=k, score=s, metadata=m) for s, k, m in scored[:top_k]]

    def delete(self, key: str) -> None:
        if key not in self._data:
            raise KeyError(f"Key {key} not found")
        del self._data[key]

    def count(self) -> int:
        return len(self._data)

    @property
    def dim(self) -> int:
        return self._dim

    def clear(self) -> None:
        self._data.clear()

    def _matches_filters(self, metadata: dict, filters: dict) -> bool:
        for key, value in filters.items():
            if key not in metadata or metadata[key] != value:
                return False
        return True


@pytest.fixture
def mock_model():
    return MockEmbeddingModel()


@pytest.fixture
def mock_vec_db():
    return MockVectorDB()


@pytest.fixture
def service(mock_model, mock_vec_db):
    from embedding_mcp.embedding_service.service import EmbeddingService
    return EmbeddingService(mock_model, mock_vec_db)


@pytest.fixture
def sample_config():
    from embedding_mcp.config.settings import Settings
    return Settings()
