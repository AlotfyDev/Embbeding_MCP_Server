"""Cosine similarity comparison stage."""
from __future__ import annotations

from embedding_mcp.pipelines.stages.compare.base import CompareStage
from embedding_mcp.pipelines.base import StageContext


class CosineSimilarityStage(CompareStage):
    """Compute cosine similarity between two vectors."""

    @property
    def name(self) -> str:
        return "compute_similarity"

    @property
    def description(self) -> str:
        return "Compute cosine similarity between two document embeddings"

    def validate(self, ctx: StageContext) -> bool:
        if "vec_a" not in ctx.output_data or "vec_b" not in ctx.output_data:
            raise ValueError("Missing vectors for comparison - run embed stages first")
        return True

    def execute(self, ctx: StageContext) -> StageContext:
        """Calculate cosine similarity."""
        vec_a = ctx.output_data.get("vec_a", [])
        vec_b = ctx.output_data.get("vec_b", [])

        dot = sum(a * b for a, b in zip(vec_a, vec_b))
        norm_a = sum(a**2 for a in vec_a) ** 0.5
        norm_b = sum(b**2 for b in vec_b) ** 0.5

        similarity = dot / (norm_a * norm_b) if norm_a > 0 and norm_b > 0 else 0.0

        ctx.output_data["similarity"] = round(similarity, 6)
        return ctx