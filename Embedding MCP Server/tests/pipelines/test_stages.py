"""Tests for Pipeline Stages."""
from __future__ import annotations

import pytest

from embedding_mcp.pipelines.base import StageContext, StageValidationError
from embedding_mcp.pipelines.stages.pre_process.strip import StripStage
from embedding_mcp.pipelines.stages.pre_process.normalize import NormalizeWhitespaceStage
from embedding_mcp.pipelines.stages.post_process.response_projector import ResponseProjectorStage


class TestStripStage:
    """Test StripStage."""

    def test_strip_whitespace(self):
        stage = StripStage()
        ctx = StageContext(input_data={"text": "  hello world  "})
        result = stage.execute(ctx)
        assert result.input_data.get("text") == "hello world"

    def test_strip_empty(self):
        stage = StripStage()
        ctx = StageContext(input_data={"text": "   "})
        result = stage.execute(ctx)
        assert result.input_data.get("text") == ""


class TestNormalizeWhitespaceStage:
    """Test NormalizeWhitespaceStage."""

    def test_normalize_multiple_spaces(self):
        stage = NormalizeWhitespaceStage()
        ctx = StageContext(input_data={"text": "hello   world   test"})
        result = stage.execute(ctx)
        assert result.input_data.get("text") == "hello world test"

    def test_normalize_newlines(self):
        stage = NormalizeWhitespaceStage()
        ctx = StageContext(input_data={"text": "hello\n\nworld"})
        result = stage.execute(ctx)
        assert result.input_data.get("text") == "hello world"


class TestResponseProjectorStage:
    """Test ResponseProjectorStage."""

    def test_project_simple_fields(self):
        stage = ResponseProjectorStage()
        ctx = StageContext(
            input_data={"response_fields": ["key", "score"]},
            output_data={"key": "doc-001", "score": 0.95, "metadata": {"type": "doc"}}
        )
        result = stage.execute(ctx)
        assert "key" in result.output_data
        assert "score" in result.output_data
        assert "metadata" not in result.output_data

    def test_project_nested_fields(self):
        stage = ResponseProjectorStage()
        ctx = StageContext(
            input_data={"response_fields": ["key", "metadata.type"]},
            output_data={"key": "doc-001", "metadata": {"type": "doc", "source": "wiki"}}
        )
        result = stage.execute(ctx)
        assert result.output_data.get("key") == "doc-001"
        assert result.output_data.get("metadata", {}).get("type") == "doc"
        assert "source" not in result.output_data.get("metadata", {})

    def test_no_projection(self):
        stage = ResponseProjectorStage()
        ctx = StageContext(output_data={"key": "doc-001", "score": 0.95})
        result = stage.execute(ctx)
        assert result.output_data == {"key": "doc-001", "score": 0.95}