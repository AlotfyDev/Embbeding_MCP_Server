"""Query embedding stage (search prefix)."""
from __future__ import annotations

from embedding_mcp.pipelines.stages.embed.base import EmbedStage
from embedding_mcp.pipelines.base import StageContext
from embedding_mcp.embedding_model import EmbeddingModel


class QueryEmbedStage(EmbedStage):
    """Embed query text with 'query: ' prefix."""

    @property
    def name(self) -> str:
        return "embed_query"

    def __init__(self, prefix: str = "query: ", model: EmbeddingModel | None = None):
        super().__init__(prefix)
        self._model = model

    def validate(self, ctx: StageContext) -> bool:
        if not self._model:
            raise ValueError("EmbeddingModel not injected")
        query = ctx.input_data.get("query")
        if query is None:
            raise ValueError("No query in input_data for embedding")
        return True

    def execute(self, ctx: StageContext) -> StageContext:
        """Embed query and store vector in output_data."""
        query = ctx.input_data.get("query", "")
        vector = self._model.embed_query(query)
        ctx.output_data["vector"] = vector
        ctx.output_data["dim"] = len(vector)
        return ctx