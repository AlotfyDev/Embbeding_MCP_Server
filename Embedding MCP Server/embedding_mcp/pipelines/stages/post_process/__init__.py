"""Post-processing stages for output transformation."""
from embedding_mcp.pipelines.stages.post_process.base import PostProcessStage
from embedding_mcp.pipelines.stages.post_process.response_projector import ResponseProjectorStage

__all__ = ["PostProcessStage", "ResponseProjectorStage"]