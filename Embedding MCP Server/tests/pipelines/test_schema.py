"""Tests for Pipelines Phase schema system."""
from __future__ import annotations

import pytest

from embedding_mcp.schema.field_def import FieldType, FieldDef
from embedding_mcp.schema.base import DocumentSchema
from embedding_mcp.schema.errors import SchemaValidationError
from embedding_mcp.schema.registry import SchemaRegistry


class TestFieldType:
    """Test FieldType enum."""

    def test_field_type_values(self):
        assert FieldType.STRING.value == "string"
        assert FieldType.INTEGER.value == "integer"
        assert FieldType.FLOAT.value == "float"
        assert FieldType.BOOLEAN.value == "boolean"
        assert FieldType.OBJECT.value == "object"
        assert FieldType.ARRAY.value == "array"


class TestFieldDef:
    """Test FieldDef validation."""

    def test_string_validation(self):
        field = FieldDef(name="text", type=FieldType.STRING)
        assert field.validate("hello") == "hello"

    def test_string_max_length(self):
        field = FieldDef(name="text", type=FieldType.STRING, max_length=10)
        with pytest.raises(SchemaValidationError):
            field.validate("a" * 15)

    def test_string_regex(self):
        field = FieldDef(name="key", type=FieldType.STRING, regex="^[a-z]+$")
        field.validate("abc")  # Should pass
        with pytest.raises(SchemaValidationError):
            field.validate("ABC")  # Should fail

    def test_integer_validation(self):
        field = FieldDef(name="count", type=FieldType.INTEGER)
        assert field.validate(42) == 42

    def test_integer_range(self):
        field = FieldDef(name="count", type=FieldType.INTEGER, min=0, max=100)
        with pytest.raises(SchemaValidationError):
            field.validate(150)

    def test_enum_validation(self):
        field = FieldDef(name="type", type=FieldType.STRING, enum=["doc", "note"])
        field.validate("doc")  # Should pass
        with pytest.raises(SchemaValidationError):
            field.validate("invalid")

    def test_default_value(self):
        field = FieldDef(name="type", type=FieldType.STRING, default="doc")
        assert field.default == "doc"


class TestDocumentSchema:
    """Test DocumentSchema validation."""

    def test_validate_required_fields(self):
        schema = DocumentSchema(
            name="TestSchema",
            fields={"key": FieldDef(name="key", type=FieldType.STRING, required=True)},
            required=["key"]
        )
        with pytest.raises(SchemaValidationError):
            schema.validate({"text": "hello"})

    def test_validate_with_defaults(self):
        schema = DocumentSchema(
            name="TestSchema",
            fields={"type": FieldDef(name="type", type=FieldType.STRING, default="doc")},
            required=[]
        )
        result = schema.validate({})
        assert result.get("type") == "doc"

    def test_from_config(self):
        config = {
            "name": "TestSchema",
            "required": ["key"],
            "fields": {
                "key": {"type": "string", "required": True},
                "value": {"type": "integer", "default": 0}
            }
        }
        schema = DocumentSchema.from_config(config)
        assert schema.name == "TestSchema"
        assert "key" in schema.fields
        assert schema.fields["value"].default == 0


class TestSchemaRegistry:
    """Test SchemaRegistry operations."""

    def test_register_and_get(self):
        registry = SchemaRegistry()
        schema = DocumentSchema(
            name="Test",
            fields={"key": FieldDef(name="key", type=FieldType.STRING)}
        )
        registry.register("test.capability", schema)
        assert registry.get("test.capability") is schema

    def test_validate_against_registry(self):
        registry = SchemaRegistry()
        schema = DocumentSchema(
            name="Test",
            fields={"query": FieldDef(name="query", type=FieldType.STRING, required=True)},
            required=["query"]
        )
        registry.register("test.search", schema)

        result = registry.validate("test.search", {"query": "hello"})
        assert result.get("query") == "hello"