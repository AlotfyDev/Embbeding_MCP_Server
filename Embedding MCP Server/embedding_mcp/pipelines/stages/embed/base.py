"""Embedding stage base class."""
from __future__ import annotations

from abc import ABC, abstractmethod

from embedding_mcp.pipelines.base import PipelineStage, StageContext


class EmbedStage(PipelineStage):
    """Base class for embedding stages.

    Args:
        prefix: E5 model prefix ("passage: " or "query: ")
        model_field: Settings attribute for model (optional)
    """

    def __init__(self, prefix: str = "passage: "):
        self._prefix = prefix

    @property
    def prefix(self) -> str:
        return self._prefix

    @property
    @abstractmethod
    def name(self) -> str:
        ...

    @property
    def description(self) -> str:
        return f"Generate embedding with prefix: '{self._prefix}'"