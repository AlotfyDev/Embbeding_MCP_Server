"""Tests for VectorDB abstract interface and SearchResult dataclass."""
from __future__ import annotations

import pytest

from embedding_mcp.embedding_service.exceptions import DimensionMismatchError
from embedding_mcp.vector_db.base import SearchResult


class TestSearchResult:
    def test_search_result_to_dict(self):
        sr = SearchResult(key="k1", score=0.95, metadata={"title": "test"})
        assert sr.to_dict() == {"key": "k1", "score": 0.95, "metadata": {"title": "test"}}

    def test_search_result_repr(self):
        sr = SearchResult(key="k1", score=0.95, metadata={})
        assert "k1" in repr(sr)


class TestVectorDB:
    def test_store_and_search(self, mock_vec_db):
        dim = mock_vec_db.dim
        mock_vec_db.store("doc1", [1.0] * dim, {"title": "first"})
        mock_vec_db.store("doc2", [0.0] * dim, {"title": "second"})
        results = mock_vec_db.search([1.0] * dim, top_k=5)
        assert len(results) == 2
        assert results[0].key == "doc1"
        assert results[0].score > results[1].score

    def test_search_returns_top_k(self, mock_vec_db):
        dim = mock_vec_db.dim
        for i in range(10):
            vec = [float(i)] * dim
            mock_vec_db.store(f"doc{i}", vec)
        results = mock_vec_db.search([1.0] * dim, top_k=3)
        assert len(results) == 3

    def test_delete_removes_vector(self, mock_vec_db):
        mock_vec_db.store("doc1", [1.0] * mock_vec_db.dim)
        mock_vec_db.store("doc2", [1.0] * mock_vec_db.dim)
        mock_vec_db.delete("doc1")
        results = mock_vec_db.search([1.0] * mock_vec_db.dim)
        keys = [r.key for r in results]
        assert "doc1" not in keys
        assert "doc2" in keys

    def test_delete_nonexistent_raises(self, mock_vec_db):
        with pytest.raises(KeyError, match="not found"):
            mock_vec_db.delete("nonexistent")

    def test_count_after_store(self, mock_vec_db):
        assert mock_vec_db.count() == 0
        mock_vec_db.store("a", [1.0] * mock_vec_db.dim)
        assert mock_vec_db.count() == 1
        mock_vec_db.store("b", [1.0] * mock_vec_db.dim)
        assert mock_vec_db.count() == 2

    def test_clear_resets_all(self, mock_vec_db):
        mock_vec_db.store("a", [1.0] * mock_vec_db.dim)
        mock_vec_db.store("b", [1.0] * mock_vec_db.dim)
        mock_vec_db.clear()
        assert mock_vec_db.count() == 0
        assert mock_vec_db.search([1.0] * mock_vec_db.dim) == []

    def test_store_batch(self, mock_vec_db):
        dim = mock_vec_db.dim
        items = [
            ("k1", [0.1] * dim, {"tag": "a"}),
            ("k2", [0.2] * dim, {"tag": "b"}),
            ("k3", [0.3] * dim, None),
        ]
        mock_vec_db.store_batch(items)
        assert mock_vec_db.count() == 3

    def test_search_with_filters(self, mock_vec_db):
        dim = mock_vec_db.dim
        mock_vec_db.store("a", [1.0] * dim, {"type": "animal", "name": "cat"})
        mock_vec_db.store("b", [0.5] * dim, {"type": "animal", "name": "dog"})
        mock_vec_db.store("c", [0.0] * dim, {"type": "plant", "name": "tree"})
        results = mock_vec_db.search([1.0] * dim, filters={"type": "animal"})
        assert len(results) == 2
        assert all(r.metadata["type"] == "animal" for r in results)

    def test_dim_mismatch_raises_on_store(self, mock_vec_db):
        with pytest.raises(DimensionMismatchError):
            mock_vec_db.store("bad", [1.0, 2.0, 3.0])

    def test_search_empty_db(self, mock_vec_db):
        results = mock_vec_db.search([1.0] * mock_vec_db.dim)
        assert results == []

    def test_store_overwrites_existing_key(self, mock_vec_db):
        dim = mock_vec_db.dim
        mock_vec_db.store("dup", [0.0] * dim, {"version": 1})
        mock_vec_db.store("dup", [1.0] * dim, {"version": 2})
        results = mock_vec_db.search([1.0] * dim)
        assert results[0].key == "dup"
        assert results[0].metadata["version"] == 2
