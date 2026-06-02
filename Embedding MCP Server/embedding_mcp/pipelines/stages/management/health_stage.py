"""Health check management stage."""
from __future__ import annotations

from embedding_mcp.pipelines.stages.management.base import ManagementStage
from embedding_mcp.pipelines.base import StageContext
from embedding_mcp.embedding_model import EmbeddingModel
from embedding_mcp.vector_db.base import VectorDB


class HealthStage(ManagementStage):
    """Check health of model and vector database."""

    def __init__(self, model: EmbeddingModel | None = None, vec_db: VectorDB | None = None):
        self._model = model
        self._vec_db = vec_db

    @property
    def name(self) -> str:
        return "health"

    def validate(self, ctx: StageContext) -> bool:
        # Health check doesn't require dependencies - errors are captured in response
        return True

    def execute(self, ctx: StageContext) -> StageContext:
        """Check system health status."""
        status = {"status": "ok", "model": "unknown", "vector_db": "unknown"}

        # Check model
        if self._model:
            try:
                test_vec = self._model.embed("health check")
                status["model"] = {"status": "ok", "dim": len(test_vec)}
            except Exception as e:
                status["status"] = "error"
                status["model"] = {"status": "error", "error": str(e)}

        # Check vector DB
        if self._vec_db:
            try:
                count = self._vec_db.count()
                status["vector_db"] = {"status": "ok", "count": count}
            except Exception as e:
                status["status"] = "error"
                status["vector_db"] = {"status": "error", "error": str(e)}

        ctx.output_data.update(status)
        return ctx