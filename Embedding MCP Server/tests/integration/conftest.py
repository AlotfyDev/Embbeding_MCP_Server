"""Fixtures for integration tests — real FAISS + mock model."""
from __future__ import annotations

import hashlib
import tempfile

import numpy as np
import pytest

from embedding_mcp.embedding_model import EmbeddingModel


class IntegrationMockModel(EmbeddingModel):
    """Deterministic mock model producing normalized vectors of real dim."""

    def __init__(self, dim: int = 384):
        self._dim = dim

    def _make_vec(self, text: str, prefix: str = "") -> list[float]:
        seed = int(hashlib.md5((prefix + text).encode()).hexdigest(), 16) % (2**31)
        rng = np.random.RandomState(seed)
        vec = rng.randn(self._dim).astype(np.float32)
        norm = float(np.linalg.norm(vec))
        return (vec / norm).tolist() if norm > 0 else [0.0] * self._dim

    def embed(self, text: str) -> list[float]:
        return self._make_vec(text)

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        return [self.embed(t) for t in texts]

    def embed_query(self, text: str) -> list[float]:
        return self._make_vec(text, prefix="query: ")

    @property
    def dim(self) -> int:
        return self._dim


@pytest.fixture
def temp_dir():
    with tempfile.TemporaryDirectory() as tmp:
        yield tmp


@pytest.fixture
def faiss_db(temp_dir):
    from embedding_mcp.vector_db.faiss_adapter import FAISSAdapter
    return FAISSAdapter(temp_dir, dim=384)


@pytest.fixture
def mock_model():
    return IntegrationMockModel(dim=384)


@pytest.fixture
def service_with_faiss(mock_model, faiss_db):
    from embedding_mcp.embedding_service.service import EmbeddingService
    return EmbeddingService(mock_model, faiss_db)
