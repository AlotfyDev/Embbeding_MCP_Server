"""Semantic search pipeline."""
from __future__ import annotations

from typing import Any

from embedding_mcp.pipelines.base import PipelineStage, StageContext, StageValidationError
from embedding_mcp.embedding_model import EmbeddingModel
from embedding_mcp.vector_db.base import VectorDB


class SemanticSearchPipeline:
    """Semantic search pipeline.

    Validates query, embeds, searches, and projects results.
    """
    capability = "search.semantic"
    version = "1.0"
    description = "Semantic search using query embedding"

    def __init__(self, model: EmbeddingModel, vec_db: VectorDB,
                 max_text_length: int = 5000, schema=None):
        self._model = model
        self._vec_db = vec_db
        self._max_text_length = max_text_length
        self._schema = schema

    def execute(self, **params) -> list[dict]:
        """Execute semantic search.

        Args:
            query: Search query string
            top_k: Number of results (default 10)
            filters: Optional metadata filters
            response_fields: Optional field projection

        Returns:
            List of {"key": str, "score": float, "metadata": dict}
        """
        query = params.get("query", "")
        top_k = params.get("top_k", 10)
        filters = params.get("filters")
        response_fields = params.get("response_fields")

        # Validate
        if not query or not query.strip():
            raise StageValidationError("query must be non-empty", field="query")

        if len(query) > self._max_text_length:
            raise StageValidationError(
                f"query exceeds {self._max_text_length} characters",
                field="query"
            )

        if top_k < 1 or top_k > 100:
            raise StageValidationError("top_k must be between 1 and 100")

        # Embed query
        query_vec = self._model.embed_query(query)

        # Search
        results = self._vec_db.search(query_vec, top_k, filters)

        # Convert to dicts
        output = [r.to_dict() for r in results]

        # Project response fields
        if response_fields:
            output = self._project_response(output, response_fields)

        return output

    def _project_response(self, data: list, fields: list) -> list:
        """Project fields on list of results."""
        from embedding_mcp.pipelines.stages.post_process.response_projector import project_response
        return project_response(data, fields)