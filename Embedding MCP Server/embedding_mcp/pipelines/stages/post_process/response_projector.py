"""Response projection stage - field filtering."""
from __future__ import annotations

from typing import Any

from embedding_mcp.pipelines.stages.post_process.base import PostProcessStage
from embedding_mcp.pipelines.base import StageContext


def _resolve_path(data: dict, path: str) -> Any:
    """Resolve dot-notation path in nested dict."""
    parts = path.split(".")
    current = data
    for part in parts:
        if isinstance(current, dict) and part in current:
            current = current[part]
        else:
            return None
    return current


def project_response(data: dict | list, fields: list[str] | None) -> dict | list:
    """Filter response data to only include specified fields.

    Args:
        data: Response dict or list of dicts
        fields: Dot-notation field paths, e.g. ["key", "metadata.type"]

    Returns:
        Filtered response (same structure as input)
    """
    if fields is None or len(fields) == 0:
        return data

    if isinstance(data, list):
        return [project_response(item, fields) for item in data]

    if not isinstance(data, dict):
        return data

    result = {}
    for field in fields:
        parts = field.split(".")
        current = data
        valid = True

        for part in parts:
            if isinstance(current, dict) and part in current:
                current = current[part]
            else:
                valid = False
                break

        if valid:
            target = result
            for i, part in enumerate(parts):
                if i == len(parts) - 1:
                    target[part] = current
                elif isinstance(current, dict) or isinstance(target.get(part), dict):
                    if part not in target:
                        target[part] = {}
                    target = target[part]

    return result


class ResponseProjectorStage(PostProcessStage):
    """Filter output fields based on response_fields parameter."""

    @property
    def name(self) -> str:
        return "response_projection"

    @property
    def description(self) -> str:
        return "Filter response to include only specified fields"

    def __init__(self, fields_param: str = "response_fields"):
        self._fields_param = fields_param

    def execute(self, ctx: StageContext) -> StageContext:
        """Project output to requested fields."""
        response_fields = ctx.input_data.get(self._fields_param)
        if response_fields:
            ctx.output_data = project_response(ctx.output_data, response_fields)
        return ctx