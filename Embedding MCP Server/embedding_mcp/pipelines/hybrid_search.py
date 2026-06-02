"""Hybrid search pipeline."""
from __future__ import annotations

from embedding_mcp.pipelines.base import StageValidationError
from embedding_mcp.embedding_model import EmbeddingModel
from embedding_mcp.vector_db.base import VectorDB


class HybridSearchPipeline:
    """Hybrid search pipeline with semantic + keyword boosting."""
    capability = "search.hybrid"
    version = "1.0"
    description = "Hybrid search with semantic + keyword boosting"

    def __init__(self, model: EmbeddingModel, vec_db: VectorDB,
                 max_text_length: int = 5000, schema=None):
        self._model = model
        self._vec_db = vec_db
        self._max_text_length = max_text_length
        self._schema = schema

    def execute(self, **params) -> list[dict]:
        """Execute hybrid search.

        Args:
            query: Search query
            keywords: List of keywords for boosting
            top_k: Number of results (default 10)
            boost_factor: Score boost per keyword match (default 0.1)
            response_fields: Optional field projection

        Returns:
            List of search results with boosted scores
        """
        query = params.get("query", "")
        keywords = params.get("keywords", [])
        top_k = params.get("top_k", 10)
        boost_factor = params.get("boost_factor", 0.1)
        response_fields = params.get("response_fields")

        # Validate
        if not query or not query.strip():
            raise StageValidationError("query must be non-empty")

        if not keywords:
            raise StageValidationError("keywords must be non-empty array")

        # Semantic search with over-fetch
        query_vec = self._model.embed_query(query)
        semantic_results = self._vec_db.search(query_vec, top_k * 2)

        # Keyword boost
        for r in semantic_results:
            text_content = r.metadata.get("text", "")
            matches = sum(
                1 for kw in keywords
                if kw.lower() in text_content.lower()
            )
            r.score += matches * boost_factor

        # Re-sort and truncate
        sorted_results = sorted(
            semantic_results, key=lambda r: r.score, reverse=True
        )[:top_k]

        output = [r.to_dict() for r in sorted_results]

        # Project response fields
        if response_fields:
            output = self._project_response(output, response_fields)

        return output

    def _project_response(self, data: list, fields: list) -> list:
        """Project fields on list of results."""
        from embedding_mcp.pipelines.stages.post_process.response_projector import project_response
        return project_response(data, fields)