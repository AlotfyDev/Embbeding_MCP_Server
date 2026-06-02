"""Integration tests for EmbeddingService — real FAISS + mock model."""
from __future__ import annotations

import pytest
from embedding_mcp.embedding_service.exceptions import DimensionMismatchError, ValidationError
from embedding_mcp.embedding_service.service import EmbeddingService


class TestServiceRealFlows:
    def test_full_embed_store_search_flow(self, service_with_faiss):
        service_with_faiss.embed_document("هذا نص تجريبي للاختبار", key="doc1", metadata={"lang": "ar"})
        service_with_faiss.embed_document("This is a test document", key="doc2", metadata={"lang": "en"})
        service_with_faiss.embed_document("تجربة أخرى", key="doc3", metadata={"lang": "ar"})

        results = service_with_faiss.search_similar("نص تجريبي", top_k=2)
        assert len(results) == 2
        assert results[0].score >= 0.0

    def test_embed_batch_documents(self, service_with_faiss):
        items = [
            {"text": f"Document number {i}", "key": f"doc{i}", "metadata": {"idx": i}}
            for i in range(5)
        ]
        count = service_with_faiss.embed_batch_documents(items)
        assert count == 5
        assert service_with_faiss.document_count() == 5

    def test_hybrid_search(self, service_with_faiss):
        service_with_faiss.embed_document("Python is a programming language", key="py", metadata={"topic": "python"})
        service_with_faiss.embed_document("Java is also a language", key="java", metadata={"topic": "java"})
        service_with_faiss.embed_document("I love programming in Python", key="py2", metadata={"topic": "python"})

        results = service_with_faiss.hybrid_search("programming language", keywords=["Python"], top_k=2)
        assert len(results) >= 1
        assert any("py" in r.key for r in results)

    def test_compare_docs_similar_text(self, service_with_faiss):
        text_a = "The quick brown fox jumps over the lazy dog"
        text_b = "The quick brown fox jumps over the lazy dog"
        similarity = service_with_faiss.compare_docs(text_a, text_b)
        assert abs(similarity - 1.0) < 0.001

    def test_document_count(self, service_with_faiss):
        assert service_with_faiss.document_count() == 0
        service_with_faiss.embed_document("doc1", key="k1")
        service_with_faiss.embed_document("doc2", key="k2")
        service_with_faiss.embed_document("doc3", key="k3")
        assert service_with_faiss.document_count() == 3

    def test_empty_text_validation_error(self, service_with_faiss):
        with pytest.raises(ValidationError, match="Text must not be empty"):
            service_with_faiss.embed_document("", key="empty")

        with pytest.raises(ValidationError, match="Text must not be empty"):
            service_with_faiss.search_similar("")

        with pytest.raises(ValidationError, match="Text must not be empty"):
            service_with_faiss.embed_text("   ")

    def test_dimension_mismatch_between_model_and_db(self, mock_model, faiss_db):
        from embedding_mcp.embedding_model import EmbeddingModel

        class Dim768Model(EmbeddingModel):
            def embed(self, text): return [0.0] * 768
            def embed_batch(self, texts): return [[0.0] * 768 for _ in texts]
            def embed_query(self, text): return [0.0] * 768
            @property
            def dim(self): return 768

        with pytest.raises(DimensionMismatchError):
            EmbeddingService(Dim768Model(), faiss_db)

    def test_health_check(self, service_with_faiss):
        health = service_with_faiss.health()
        assert health["status"] == "ok"
        assert "dim=" in health["model"]
        assert "count=" in health["vector_db"]

    def test_delete_and_count(self, service_with_faiss):
        service_with_faiss.embed_document("keep me", key="keep")
        service_with_faiss.embed_document("delete me", key="remove")
        assert service_with_faiss.document_count() == 2
        service_with_faiss.delete_document("remove")
        assert service_with_faiss.document_count() == 1
        results = service_with_faiss.search_similar("keep", top_k=5)
        assert all(r.key != "remove" for r in results)
