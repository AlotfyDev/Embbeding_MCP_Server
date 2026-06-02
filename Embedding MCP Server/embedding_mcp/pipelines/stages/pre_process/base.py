"""Pre-processing stage base class."""
from __future__ import annotations

import re
from abc import ABC, abstractmethod

from embedding_mcp.pipelines.base import PipelineStage, StageContext


class PreProcessStage(PipelineStage):
    """Base class for pre-processing stages.

    Pre-processing stages transform input data before embedding.
    """

    @abstractmethod
    def text_transform(self, text: str) -> str:
        """Transform text content.

        Args:
            text: Input text

        Returns:
            Transformed text
        """
        ...

    def execute(self, ctx: StageContext) -> StageContext:
        """Process input_data text field."""
        text = ctx.input_data.get("text", "")
        if text is not None:
            ctx.input_data["text"] = self.text_transform(text)
        ctx.output_data = ctx.input_data.copy()
        return ctx