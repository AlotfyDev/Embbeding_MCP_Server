"""Tests for EmbeddingService — core business logic with validation."""
from __future__ import annotations

import pytest

from embedding_mcp.embedding_service.exceptions import ValidationError, DimensionMismatchError
from embedding_mcp.embedding_service.service import EmbeddingService, MAX_TEXT_LENGTH


class TestEmbeddingService:
    def test_embed_text_valid(self, service):
        vec = service.embed_text("hello world")
        assert isinstance(vec, list)
        assert len(vec) == service._model.dim
        assert all(isinstance(v, float) for v in vec)

    def test_embed_text_empty_raises(self, service):
        with pytest.raises(ValidationError, match="not be empty"):
            service.embed_text("")
        with pytest.raises(ValidationError, match="not be empty"):
            service.embed_text("   ")

    def test_embed_text_too_long_raises(self, service):
        long_text = "a" * (MAX_TEXT_LENGTH + 1)
        with pytest.raises(ValidationError, match="exceeds"):
            service.embed_text(long_text)

    def test_embed_text_custom_max_length(self, mock_model, mock_vec_db):
        svc = EmbeddingService(mock_model, mock_vec_db, max_text_length=10)
        with pytest.raises(ValidationError, match="exceeds 10"):
            svc.embed_text("a" * 11)
        vec = svc.embed_text("a" * 10)
        assert isinstance(vec, list)

    def test_embed_document_stores_in_db(self, mock_model, mock_vec_db):
        svc = EmbeddingService(mock_model, mock_vec_db)
        svc.embed_document("some text", "key1", {"source": "test"})
        assert mock_vec_db.count() == 1
        assert mock_model.embed_calls == ["some text"]

    def test_embed_batch_documents_stores_all(self, mock_model, mock_vec_db):
        svc = EmbeddingService(mock_model, mock_vec_db)
        items = [
            {"text": "doc1", "key": "k1", "metadata": {"idx": 0}},
            {"text": "doc2", "key": "k2", "metadata": {"idx": 1}},
            {"text": "doc3", "key": "k3"},
        ]
        count = svc.embed_batch_documents(items)
        assert count == 3
        assert mock_vec_db.count() == 3

    def test_embed_batch_splits_large_batches(self, mock_model, mock_vec_db):
        svc = EmbeddingService(mock_model, mock_vec_db, max_batch_size=2)
        items = [{"text": f"doc{i}", "key": f"k{i}"} for i in range(5)]
        count = svc.embed_batch_documents(items)
        assert count == 5
        assert mock_vec_db.count() == 5
        assert len(mock_model.embed_batch_calls) == 3
        assert mock_model.embed_batch_calls[0] == ["doc0", "doc1"]
        assert mock_model.embed_batch_calls[1] == ["doc2", "doc3"]
        assert mock_model.embed_batch_calls[2] == ["doc4"]

    def test_embed_batch_empty_list(self, mock_model, mock_vec_db):
        svc = EmbeddingService(mock_model, mock_vec_db)
        count = svc.embed_batch_documents([])
        assert count == 0

    def test_search_similar_returns_results(self, service, mock_vec_db):
        dim = service._model.dim
        mock_vec_db.store("doc1", [0.1] * dim, {"text": "hello world"})
        mock_vec_db.store("doc2", [0.9] * dim, {"text": "goodbye world"})
        results = service.search_similar("hello")
        assert len(results) > 0
        assert all(r.score >= 0 for r in results)

    def test_search_similar_empty_query_raises(self, service):
        with pytest.raises(ValidationError, match="not be empty"):
            service.search_similar("")
        with pytest.raises(ValidationError, match="not be empty"):
            service.search_similar("   ")

    def test_find_similar_to_doc_not_implemented(self, service):
        with pytest.raises(NotImplementedError):
            service.find_similar_to_doc("some_key")

    def test_hybrid_search_boosts_keywords(self, service, mock_vec_db):
        dim = service._model.dim
        mock_vec_db.store("a", [0.5] * dim, {"text": "python programming language"})
        mock_vec_db.store("b", [0.5] * dim, {"text": "java programming language"})
        results = service.hybrid_search("programming", keywords=["python"])
        assert results[0].key == "a"
        assert results[0].score > results[1].score

    def test_hybrid_search_no_keywords(self, service, mock_vec_db):
        dim = service._model.dim
        mock_vec_db.store("a", [0.1] * dim, {"text": "some content"})
        results = service.hybrid_search("test", keywords=[])
        assert len(results) == 1

    def test_compare_docs_similarity(self, mock_model, mock_vec_db):
        svc = EmbeddingService(mock_model, mock_vec_db)
        sim = svc.compare_docs("doc_a", "doc_b")
        assert isinstance(sim, float)
        assert 0.0 <= sim <= 1.0

    def test_health_returns_status(self, service):
        status = service.health()
        assert isinstance(status, dict)
        assert status["status"] == "ok"
        assert "model" in status
        assert "vector_db" in status

    def test_health_model_error(self, mock_vec_db):
        broken_model = type("BrokenModel", (), {
            "embed": lambda self, t: (_ for _ in ()).throw(Exception("model failure")),
            "dim": 384,
        })()
        svc = EmbeddingService(broken_model, mock_vec_db)
        status = svc.health()
        assert status["status"] == "error"
        assert "model_error" in status

    def test_dimension_mismatch_raises_at_init(self, mock_model):
        wrong_dim_db = type("WrongDimDB", (), {"dim": 999})()
        with pytest.raises(DimensionMismatchError, match="does not match"):
            EmbeddingService(mock_model, wrong_dim_db)

    def test_delete_document(self, service, mock_vec_db):
        mock_vec_db.store("del_key", [0.1] * service._model.dim)
        assert mock_vec_db.count() == 1
        service.delete_document("del_key")
        assert mock_vec_db.count() == 0

    def test_document_count(self, service, mock_vec_db):
        assert service.document_count() == 0
        mock_vec_db.store("k", [0.1] * service._model.dim)
        assert service.document_count() == 1
