"""Strip whitespace pre-processing stage."""
from __future__ import annotations

from embedding_mcp.pipelines.stages.pre_process.base import PreProcessStage
from embedding_mcp.pipelines.base import StageContext


class StripStage(PreProcessStage):
    """Trim leading and trailing whitespace."""

    @property
    def name(self) -> str:
        return "strip"

    @property
    def description(self) -> str:
        return "Trim leading and trailing whitespace from text"

    def text_transform(self, text: str) -> str:
        return text.strip()

    def execute(self, ctx: StageContext) -> StageContext:
        """Strip all string values in input_data."""
        for key, value in ctx.input_data.items():
            if isinstance(value, str):
                ctx.input_data[key] = value.strip()
        ctx.output_data = ctx.input_data.copy()
        return ctx