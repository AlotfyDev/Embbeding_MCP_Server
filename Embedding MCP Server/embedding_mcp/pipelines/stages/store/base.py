"""Storage stage base class."""
from __future__ import annotations

from abc import ABC, abstractmethod

from embedding_mcp.pipelines.base import PipelineStage, StageContext
from embedding_mcp.vector_db.base import VectorDB


class StoreStage(PipelineStage):
    """Base class for storage stages."""

    def __init__(self, vec_db: VectorDB | None = None):
        self._vec_db = vec_db

    @property
    @abstractmethod
    def name(self) -> str:
        ...

    def validate(self, ctx: StageContext) -> bool:
        if not self._vec_db:
            raise ValueError("VectorDB not injected")
        return True