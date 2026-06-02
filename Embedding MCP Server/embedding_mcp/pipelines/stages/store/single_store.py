"""Single document storage stage."""
from __future__ import annotations

from embedding_mcp.pipelines.stages.store.base import StoreStage
from embedding_mcp.pipelines.base import StageContext


class SingleStoreStage(StoreStage):
    """Store a single document vector."""

    @property
    def name(self) -> str:
        return "store"

    def validate(self, ctx: StageContext) -> bool:
        super().validate(ctx)
        if "key" not in ctx.input_data and "key" not in ctx.output_data:
            raise ValueError("No key for storage")
        if "vector" not in ctx.output_data:
            raise ValueError("No vector to store - run embed stage first")
        return True

    def execute(self, ctx: StageContext) -> StageContext:
        """Store vector in vector database."""
        key = ctx.input_data.get("key") or ctx.output_data.get("key")
        vector = ctx.output_data.get("vector")
        metadata = ctx.input_data.get("metadata") or ctx.output_data.get("metadata", {})

        self._vec_db.store(key, vector, metadata)
        ctx.output_data["status"] = "stored"
        return ctx