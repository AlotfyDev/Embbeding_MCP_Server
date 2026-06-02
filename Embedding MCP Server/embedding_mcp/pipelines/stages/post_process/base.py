"""Post-processing stage base class."""
from __future__ import annotations

from abc import ABC

from embedding_mcp.pipelines.base import PipelineStage, StageContext


class PostProcessStage(PipelineStage):
    """Base class for post-processing stages.

    Post-processing stages transform pipeline output after main operations.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        ...

    @property
    def description(self) -> str:
        return "Post-process pipeline output"