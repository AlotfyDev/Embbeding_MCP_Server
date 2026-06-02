"""Management stage base class."""
from __future__ import annotations

from abc import ABC

from embedding_mcp.pipelines.base import PipelineStage, StageContext


class ManagementStage(PipelineStage):
    """Base class for management operations (delete, count, health)."""

    @property
    @abstractmethod
    def name(self) -> str:
        ...

    @property
    def description(self) -> str:
        return "System management operation"