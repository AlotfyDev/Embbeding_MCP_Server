"""Tests for MCP tool definitions."""
from __future__ import annotations

from embedding_mcp.mcp_local.tools import TOOL_DEFINITIONS


class TestToolDefinitions:
    def test_tool_definitions_structure(self):
        for name, definition in TOOL_DEFINITIONS.items():
            assert "description" in definition, f"{name} missing description"
            assert "input_schema" in definition, f"{name} missing input_schema"
            schema = definition["input_schema"]
            assert isinstance(schema, dict)
            assert "type" in schema
            assert "properties" in schema

    def test_tool_definitions_all_tools_present(self):
        expected = {
            "embed_text",
            "search_similar",
            "store_document",
            "store_batch",
            "delete_document",
            "count_documents",
            "health",
        }
        assert set(TOOL_DEFINITIONS.keys()) == expected
