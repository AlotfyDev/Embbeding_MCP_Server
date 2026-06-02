"""Comparison stage base class."""
from __future__ import annotations

from abc import ABC

from embedding_mcp.pipelines.base import PipelineStage, StageContext


class CompareStage(PipelineStage):
    """Base class for comparison stages."""

    @property
    @abstractmethod
    def name(self) -> str:
        ...

    @property
    def description(self) -> str:
        return "Compare documents and compute similarity"