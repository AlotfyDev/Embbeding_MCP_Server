"""Pipeline Stage Abstract Base Classes."""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


class StageError(Exception):
    """Base error for stage failures."""

    def __init__(self, message: str, code: str = "STAGE_ERROR"):
        self.code = code
        super().__init__(message)


class StageValidationError(StageError):
    """Validation failure - stops pipeline execution."""

    def __init__(self, message: str, field: str | None = None):
        self.field = field
        super().__init__(message, code="VALIDATION_ERROR")


class StageSkip(StageError):
    """Graceful skip - continues pipeline without error."""

    def __init__(self, message: str = "Stage skipped"):
        super().__init__(message, code="STAGE_SKIP")


@dataclass
class StageContext:
    """Data bus shared between pipeline stages.

    Attributes:
        input_data: Original input parameters
        output_data: Pipeline output (accumulated)
        metadata: Shared context for stages
        errors: Errors encountered (for error handling)
    """
    input_data: dict = field(default_factory=dict)
    output_data: dict = field(default_factory=dict)
    metadata: dict = field(default_factory=dict)
    errors: list[Exception] = field(default_factory=list)


class PipelineStage(ABC):
    """Abstract interface for all pipeline stages.

    Each stage:
    - Receives StageContext as input
    - Validates/processes context
    - Modifies context in place
    - Raises StageValidationError to stop pipeline
    - Raises StageSkip for graceful skip
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Stage identifier for config references."""
        ...

    @property
    def description(self) -> str:
        """Human-readable stage description."""
        return ""

    def validate(self, ctx: StageContext) -> bool:
        """Validate stage prerequisites.

        Args:
            ctx: Stage context to validate

        Returns:
            True if valid

        Raises:
            StageValidationError: If validation fails
        """
        return True

    @abstractmethod
    def execute(self, ctx: StageContext) -> StageContext:
        """Execute stage logic.

        Args:
            ctx: Stage context

        Returns:
            Modified context
        """
        ...

    def cleanup(self, ctx: StageContext) -> None:
        """Cleanup hook - called after execute regardless of errors.

        Args:
            ctx: Stage context
        """
        pass


class CompositeStage(PipelineStage):
    """Groups multiple sub-stages into one logical stage."""

    def __init__(self, name: str, stages: list[PipelineStage]):
        self._name = name
        self._stages = stages

    @property
    def name(self) -> str:
        return self._name

    def execute(self, ctx: StageContext) -> StageContext:
        """Execute all sub-stages in sequence."""
        for stage in self._stages:
            if ctx.errors:
                break
            try:
                stage.validate(ctx)
                ctx = stage.execute(ctx)
            except StageSkip:
                continue
        return ctx


@dataclass
class Pipeline:
    """Orchestrator for executing ordered stages.

    Attributes:
        capability: Capability identifier
        stages: Ordered list of stages to execute
        version: Pipeline version
        description: Human-readable description
    """
    capability: str
    stages: list[PipelineStage]
    version: str = "1.0"
    description: str = ""

    def execute(self, **params) -> Any:
        """Execute pipeline with input parameters.

        Args:
            **params: Input parameters

        Returns:
            Pipeline output data

        Raises:
            StageValidationError: If validation fails
            StageError: If stage execution fails
        """
        ctx = StageContext(input_data=params)

        for stage in self.stages:
            try:
                stage.validate(ctx)
                ctx = stage.execute(ctx)
            except StageValidationError:
                raise
            except StageSkip:
                continue
            except Exception as e:
                ctx.errors.append(e)
                raise StageError(f"Stage '{stage.name}' failed: {e}")

        return ctx.output_data