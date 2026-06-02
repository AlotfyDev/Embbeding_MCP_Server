"""Passage embedding stage (document prefix)."""
from __future__ import annotations

from embedding_mcp.pipelines.stages.embed.base import EmbedStage
from embedding_mcp.pipelines.base import StageContext
from embedding_mcp.embedding_model import EmbeddingModel


class PassageEmbedStage(EmbedStage):
    """Embed document text with 'passage: ' prefix."""

    @property
    def name(self) -> str:
        return "embed"

    def __init__(self, prefix: str = "passage: ", model: EmbeddingModel | None = None):
        super().__init__(prefix)
        self._model = model

    def validate(self, ctx: StageContext) -> bool:
        if not self._model:
            raise ValueError("EmbeddingModel not injected")
        text = ctx.input_data.get("text")
        if text is None:
            raise ValueError("No text in input_data for embedding")
        return True

    def execute(self, ctx: StageContext) -> StageContext:
        """Embed text and store vector in output_data."""
        text = ctx.input_data.get("text", "")
        vector = self._model.embed(text)
        ctx.output_data["vector"] = vector
        ctx.output_data["dim"] = len(vector)
        return ctx