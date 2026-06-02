"""Document comparison pipeline."""
from __future__ import annotations

from embedding_mcp.pipelines.base import StageValidationError
from embedding_mcp.embedding_model import EmbeddingModel


class DocumentComparePipeline:
    """Document comparison pipeline using cosine similarity."""
    capability = "document.compare"
    version = "1.0"
    description = "Compare two documents via cosine similarity"

    def __init__(self, model: EmbeddingModel, vec_db=None, schema=None):
        self._model = model
        self._vec_db = vec_db
        self._schema = schema

    def execute(self, **params) -> dict:
        """Execute document comparison.

        Args:
            key_a: First document key or text
            key_b: Second document key or text

        Returns:
            {"similarity": float, "key_a": str, "key_b": str}
        """
        key_a = params.get("key_a", "")
        key_b = params.get("key_b", "")

        # Validate
        if not key_a or not key_a.strip():
            raise StageValidationError("key_a must be non-empty")
        if not key_b or not key_b.strip():
            raise StageValidationError("key_b must be non-empty")

        # Embed both (current implementation treats as text)
        vec_a = self._model.embed(key_a)
        vec_b = self._model.embed(key_b)

        # Cosine similarity
        dot = sum(a * b for a, b in zip(vec_a, vec_b))
        norm_a = sum(a**2 for a in vec_a) ** 0.5
        norm_b = sum(b**2 for b in vec_b) ** 0.5
        similarity = dot / (norm_a * norm_b) if norm_a > 0 and norm_b > 0 else 0.0

        return {
            "similarity": round(similarity, 6),
            "key_a": key_a,
            "key_b": key_b,
        }