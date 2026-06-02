"""Normalize whitespace pre-processing stage."""
from __future__ import annotations

import re
from embedding_mcp.pipelines.stages.pre_process.base import PreProcessStage
from embedding_mcp.pipelines.base import StageContext


class NormalizeWhitespaceStage(PreProcessStage):
    """Collapse multiple whitespace characters to single space."""

    @property
    def name(self) -> str:
        return "normalize_whitespace"

    @property
    def description(self) -> str:
        return "Collapse multiple whitespace to single space"

    def text_transform(self, text: str) -> str:
        return re.sub(r'\s+', ' ', text)

    def execute(self, ctx: StageContext) -> StageContext:
        """Normalize whitespace in text field."""
        text = ctx.input_data.get("text", "")
        if text:
            ctx.input_data["text"] = self.text_transform(text)
        ctx.output_data = ctx.input_data.copy()
        return ctx