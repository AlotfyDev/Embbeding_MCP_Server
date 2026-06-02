"""Delete document management stage."""
from __future__ import annotations

from embedding_mcp.pipelines.stages.management.base import ManagementStage
from embedding_mcp.pipelines.base import StageContext
from embedding_mcp.vector_db.base import VectorDB


class DeleteStage(ManagementStage):
    """Delete a document from vector database."""

    def __init__(self, vec_db: VectorDB | None = None):
        self._vec_db = vec_db

    @property
    def name(self) -> str:
        return "delete"

    def validate(self, ctx: StageContext) -> bool:
        if not self._vec_db:
            raise ValueError("VectorDB not injected")
        if "key" not in ctx.input_data:
            raise ValueError("No key in input_data for deletion")
        return True

    def execute(self, ctx: StageContext) -> StageContext:
        """Delete document by key."""
        key = ctx.input_data.get("key")
        self._vec_db.delete(key)
        ctx.output_data["status"] = "deleted"
        ctx.output_data["key"] = key
        return ctx