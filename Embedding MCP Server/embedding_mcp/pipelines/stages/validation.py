"""Input validation stage - validates params against schemas."""
from __future__ import annotations

from embedding_mcp.pipelines.base import PipelineStage, StageContext
from embedding_mcp.pipelines.base import StageValidationError


class ValidateInputStage(PipelineStage):
    """Validate input parameters against schema."""

    @property
    def name(self) -> str:
        return "validate_input"

    def __init__(self, schema=None):
        self._schema = schema

    def validate(self, ctx: StageContext) -> bool:
        if self._schema is None:
            return True
        return True

    def execute(self, ctx: StageContext) -> StageContext:
        """Validate input_data against schema."""
        if self._schema:
            try:
                validated = self._schema.validate(ctx.input_data)
                ctx.input_data = validated
                ctx.output_data = validated.copy()
            except Exception as e:
                raise StageValidationError(f"Validation failed: {e}")
        else:
            ctx.output_data = ctx.input_data.copy()
        return ctx