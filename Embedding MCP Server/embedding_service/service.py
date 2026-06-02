"""Embedding Service - Core business logic layer."""
from __future__ import annotations

import logging

from embedding_mcp.embedding_model import EmbeddingModel
from embedding_mcp.vector_db.base import SearchResult

logger = logging.getLogger(__name__)

MAX_TEXT_LENGTH = 5000


class EmbeddingService:
    """Core embedding service with business logic.

    Handles text embedding, storage, and similarity search.
    Uses dependency injection for model and vector DB.
    """

    def __init__(self, model: EmbeddingModel, vec_db, max_batch_size: int = 32):
        self._model = model
        self._vec_db = vec_db
        self._max_batch_size = max_batch_size

    def _validate_text(self, text: str) -> None:
        if not text or not text.strip():
            raise ValueError("Text must not be empty")
        if len(text) > MAX_TEXT_LENGTH:
            raise ValueError(f"Text exceeds {MAX_TEXT_LENGTH} characters")

    def embed_text(self, text: str) -> list[float]:
        """Embed a single text as document."""
        self._validate_text(text)
        return self._model.embed(text)

    def embed_document(self, text: str, key: str, metadata: dict | None = None) -> None:
        """Embed and store a document."""
        self._validate_text(text)
        vector = self._model.embed(text)
        self._vec_db.store(key, vector, metadata)

    def embed_batch_documents(self, items: list[dict]) -> int:
        """Embed and store multiple documents.

        Args:
            items: [{"text": str, "key": str, "metadata": dict}, ...]

        Returns:
            Number of documents stored.
        """
        for item in items:
            self._validate_text(item["text"])

        stored = 0
        for i in range(0, len(items), self._max_batch_size):
            batch = items[i : i + self._max_batch_size]
            texts = [b["text"] for b in batch]
            vectors = self._model.embed_batch(texts)
            db_items = [(b["key"], vectors[j], b.get("metadata")) for j, b in enumerate(batch)]
            self._vec_db.store_batch(db_items)
            stored += len(db_items)
        return stored

    def search_similar(self, query: str, top_k: int = 10, filters: dict | None = None) -> list[SearchResult]:
        """Semantic search using embedding query."""
        self._validate_text(query)
        query_vec = self._model.embed_query(query)
        return self._vec_db.search(query_vec, top_k, filters)

    def hybrid_search(self, query: str, keywords: list[str], top_k: int = 10) -> list[SearchResult]:
        """Semantic + keyword hybrid search with boosting."""
        results = self.search_similar(query, top_k * 2)

        for r in results:
            text_content = r.metadata.get("text", "")
            keyword_matches = sum(1 for kw in keywords if kw.lower() in text_content.lower())
            r.score += keyword_matches * 0.1

        return sorted(results, key=lambda r: r.score, reverse=True)[:top_k]

    def compare_docs(self, key_a: str, key_b: str) -> float:
        """Calculate cosine similarity between two stored documents."""
        vec_a = self._model.embed(key_a)
        vec_b = self._model.embed(key_b)
        dot = sum(a * b for a, b in zip(vec_a, vec_b))
        norm_a = sum(a**2 for a in vec_a) ** 0.5
        norm_b = sum(b**2 for b in vec_b) ** 0.5
        return dot / (norm_a * norm_b) if norm_a > 0 and norm_b > 0 else 0.0

    def delete_document(self, key: str) -> None:
        """Delete a document by key."""
        self._vec_db.delete(key)

    def document_count(self) -> int:
        """Return total stored documents."""
        return self._vec_db.count()

    def health(self) -> dict:
        """Return health status of model and vector DB."""
        status = {"status": "ok", "model": "unknown", "vector_db": "unknown"}

        try:
            test_vec = self._model.embed("health check")
            status["model"] = f"dim={len(test_vec)}"
        except Exception as e:
            status["status"] = "error"
            status["model_error"] = str(e)

        try:
            status["vector_db"] = f"count={self._vec_db.count()}"
        except Exception as e:
            status["status"] = "error"
            status["vector_db_error"] = str(e)

        return status