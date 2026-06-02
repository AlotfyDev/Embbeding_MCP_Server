"""Count documents management stage."""
from __future__ import annotations

from embedding_mcp.pipelines.stages.management.base import ManagementStage
from embedding_mcp.pipelines.base import StageContext
from embedding_mcp.vector_db.base import VectorDB


class CountStage(ManagementStage):
    """Count total documents in vector database."""

    def __init__(self, vec_db: VectorDB | None = None):
        self._vec_db = vec_db

    @property
    def name(self) -> str:
        return "count"

    def validate(self, ctx: StageContext) -> bool:
        if not self._vec_db:
            raise ValueError("VectorDB not injected")
        return True

    def execute(self, ctx: StageContext) -> StageContext:
        """Return document count."""
        count = self._vec_db.count()
        ctx.output_data["count"] = count
        return ctx