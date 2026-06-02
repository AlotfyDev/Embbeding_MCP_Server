"""Semantic search stage."""
from __future__ import annotations

from embedding_mcp.pipelines.stages.search.base import SearchStage
from embedding_mcp.pipelines.base import StageContext


class SemanticSearchStage(SearchStage):
    """Perform semantic search using vector similarity."""

    @property
    def name(self) -> str:
        return "search"

    def validate(self, ctx: StageContext) -> bool:
        super().validate(ctx)
        if "vector" not in ctx.output_data:
            raise ValueError("No query vector - run embed_query stage first")
        return True

    def execute(self, ctx: StageContext) -> StageContext:
        """Search for similar vectors."""
        vector = ctx.output_data["vector"]
        top_k = ctx.input_data.get("top_k", 10)
        filters = ctx.input_data.get("filters")

        results = self._vec_db.search(vector, top_k, filters)
        ctx.output_data["results"] = results
        ctx.output_data["result_count"] = len(results)
        return ctx