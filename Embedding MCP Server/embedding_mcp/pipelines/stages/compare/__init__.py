"""Comparison stages for document similarity."""
from embedding_mcp.pipelines.stages.compare.base import CompareStage
from embedding_mcp.pipelines.stages.compare.cosine_similarity import CosineSimilarityStage

__all__ = ["CompareStage", "CosineSimilarityStage"]