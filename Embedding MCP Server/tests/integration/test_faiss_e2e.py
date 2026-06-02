"""Integration tests for FAISSAdapter — real FAISS, no mocks."""
from __future__ import annotations

import pytest
from embedding_mcp.embedding_service.exceptions import DimensionMismatchError
from embedding_mcp.vector_db.faiss_adapter import FAISSAdapter


class TestFAISSCRUD:
    def test_full_crud_flow(self, temp_dir):
        db = FAISSAdapter(temp_dir, dim=384)
        vec = [0.1] * 384

        db.store("k1", vec, {"name": "doc1"})
        assert db.count() == 1

        results = db.search(vec, top_k=5)
        assert len(results) == 1
        assert results[0].key == "k1"

        db.delete("k1")
        results = db.search(vec, top_k=5)
        assert len(results) == 0

        db.clear()
        assert db.count() == 0

    def test_store_batch_and_search_top_k(self, temp_dir):
        db = FAISSAdapter(temp_dir, dim=384)
        import numpy as np
        rng = np.random.RandomState(42)

        items = []
        for i in range(10):
            v = rng.randn(384).astype(np.float32)
            v = (v / np.linalg.norm(v)).tolist()
            items.append((f"doc{i}", v, {"idx": i}))
        db.store_batch(items)
        assert db.count() == 10

        query = rng.randn(384).astype(np.float32)
        query = (query / np.linalg.norm(query)).tolist()
        results = db.search(query, top_k=5)
        assert len(results) == 5

    def test_filters(self, temp_dir):
        db = FAISSAdapter(temp_dir, dim=384)
        vec = [0.1 + i * 0.001 for i in range(384)]

        db.store("doc1", vec, {"type": "doc", "project": "a"})
        db.store("note1", [0.2 + i * 0.001 for i in range(384)], {"type": "note", "project": "a"})
        db.store("doc2", [0.15 + i * 0.001 for i in range(384)], {"type": "doc", "project": "b"})

        results = db.search(vec, top_k=10, filters={"type": "doc"})
        assert len(results) == 2
        assert all(r.metadata["type"] == "doc" for r in results)

        results = db.search(vec, top_k=10, filters={"type": "doc", "project": "a"})
        assert len(results) == 1
        assert results[0].key == "doc1"

    def test_persist_across_instances(self, temp_dir):
        db1 = FAISSAdapter(temp_dir, dim=384)
        vec = [0.1] * 384
        db1.store("persist_key", vec, {"tag": "test"})
        db1.store("persist_key2", [0.2] * 384, {"tag": "test2"})
        count1 = db1.count()
        del db1

        db2 = FAISSAdapter(temp_dir, dim=384)
        assert db2.count() == count1
        results = db2.search([0.1] * 384, top_k=5)
        keys = [r.key for r in results]
        assert "persist_key" in keys

    def test_dimension_mismatch_on_store(self, temp_dir):
        db = FAISSAdapter(temp_dir, dim=384)
        with pytest.raises(DimensionMismatchError):
            db.store("bad", [0.1] * 128)

    def test_delete_nonexistent_key(self, temp_dir):
        db = FAISSAdapter(temp_dir, dim=384)
        db.store("k1", [0.1] * 384)
        with pytest.raises(KeyError):
            db.delete("nonexistent")

    def test_large_batch(self, temp_dir):
        db = FAISSAdapter(temp_dir, dim=384)
        items = [(f"doc{i}", [(i % 100) / 100.0] * 384, {"idx": i}) for i in range(100)]
        db.store_batch(items)
        assert db.count() == 100
