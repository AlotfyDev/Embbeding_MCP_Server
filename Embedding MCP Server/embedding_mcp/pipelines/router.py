"""Capability Router for pipeline execution."""
from __future__ import annotations

from typing import Any, Callable

from embedding_mcp.pipelines.base import Pipeline, StageContext
from embedding_mcp.pipelines.base import StageError


class UnknownCapabilityError(Exception):
    """Raised when capability string is not registered."""

    def __init__(self, capability: str, available: list[str]):
        message = f"Unknown capability: '{capability}'. Available: {available}"
        super().__init__(message)
        self.capability = capability
        self.available = available


class SchemaValidationMiddleware:
    """Middleware for schema validation before pipeline execution."""

    def __init__(self, schema_registry=None):
        self._registry = schema_registry

    def process(self, ctx: dict) -> dict:
        """Validate params against registered schema."""
        capability = ctx.get("capability")
        params = ctx.get("params", {})

        if self._registry and capability:
            schema = self._registry.get(capability)
            if schema:
                ctx["params"] = schema.validate(params)

        return ctx


class ErrorHandlingMiddleware:
    """Middleware for uniform error handling."""

    def process(self, ctx: dict) -> dict:
        """This middleware processes errors after pipeline execution."""
        return ctx


class CapabilityRouter:
    """Routes requests to the appropriate pipeline by capability name."""

    def __init__(self):
        self._pipelines: dict[str, Pipeline] = {}
        self._middleware: list[Callable[[dict], dict]] = []

    def register(self, pipeline: Pipeline) -> None:
        """Register a pipeline by its capability name."""
        if pipeline.capability in self._pipelines:
            raise ValueError(f"Pipeline '{pipeline.capability}' already registered")
        self._pipelines[pipeline.capability] = pipeline

    def unregister(self, capability: str) -> None:
        """Remove a registered pipeline."""
        self._pipelines.pop(capability, None)

    def add_middleware(self, middleware: Callable[[dict], dict]) -> None:
        """Add middleware to the chain."""
        self._middleware.append(middleware)

    def route(self, capability: str, **params) -> Any:
        """Execute a pipeline by capability name.

        Args:
            capability: e.g. "document.ingest", "search.semantic"
            **params: Pipeline-specific input parameters

        Returns:
            Pipeline output (dict or list)

        Raises:
            UnknownCapabilityError: If capability not registered
        """
        if capability not in self._pipelines:
            raise UnknownCapabilityError(
                capability,
                list(self._pipelines.keys())
            )

        pipeline = self._pipelines[capability]

        # Apply middleware chain
        ctx = {"capability": capability, "params": params}
        for mw in self._middleware:
            ctx = mw.process(ctx)

        # Execute pipeline
        result = pipeline.execute(**ctx["params"])

        return result

    @property
    def capabilities(self) -> list[str]:
        """List registered capabilities."""
        return list(self._pipelines.keys())