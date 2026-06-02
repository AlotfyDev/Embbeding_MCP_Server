"""DocumentSchema implementation for input validation."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from embedding_mcp.schema.field_def import FieldDef, FieldType
from embedding_mcp.schema.errors import SchemaValidationError


def _resolve_nested(data: dict, path: str) -> Any:
    """Resolve 'metadata.type' → data['metadata']['type']."""
    parts = path.split(".")
    current = data
    for part in parts:
        if not isinstance(current, dict):
            return None
        current = current.get(part)
    return current


def _set_nested(data: dict, path: str, value: Any) -> None:
    """Set 'metadata.type' → data['metadata']['type'] = value."""
    parts = path.split(".")
    current = data
    for part in parts[:-1]:
        if part not in current:
            current[part] = {}
        current = current[part]
    current[parts[-1]] = value


@dataclass
class DocumentSchema:
    """Schema definition for a capability's input/output.

    Attributes:
        name: Schema name for registry
        fields: Field definitions keyed by field path
        required: List of required field paths
        version: Schema version (semver)
    """
    name: str
    fields: dict[str, FieldDef] = field(default_factory=dict)
    required: list[str] = field(default_factory=list)
    version: str = "1.0"

    def validate(self, data: dict) -> dict:
        """Validate data against this schema.

        Args:
            data: Input dictionary to validate

        Returns:
            Validated data with defaults applied

        Raises:
            SchemaValidationError: If validation fails
        """
        validated = {}

        # Check required fields (with deep path support)
        for field_path in self.required:
            value = _resolve_nested(data, field_path)
            if value is None:
                # Check direct key as fallback
                if field_path not in data or data[field_path] is None:
                    raise SchemaValidationError(
                        f"Missing required field: '{field_path}'",
                        field=field_path,
                    )

        # Validate each provided field
        for key, value in data.items():
            if key not in self.fields:
                # Check nested paths
                matched = False
                for field_path in self.fields:
                    if key == field_path or field_path.startswith(key + "."):
                        matched = True
                        break
                if not matched:
                    raise SchemaValidationError(
                        f"Unknown field: '{key}'",
                        field=key,
                    )

            field_def = self.fields[key]
            validated[key] = field_def.validate(value)

        # Apply defaults for optional missing fields
        for field_path, field_def in self.fields.items():
            if field_path not in validated and not field_def.required:
                if field_def.default is not None:
                    # Handle nested defaults
                    _set_nested(validated, field_path, field_def.default)

        return validated

    @classmethod
    def from_config(cls, config: dict) -> "DocumentSchema":
        """Create DocumentSchema from YAML config dict."""
        fields = {}
        required = config.get("required", [])

        for field_name, field_cfg in config.get("fields", {}).items():
            field_type = FieldType(field_cfg.get("type", "string"))
            fields[field_name] = FieldDef(
                name=field_name,
                type=field_type,
                required=field_name in required,
                enum=field_cfg.get("enum"),
                regex=field_cfg.get("regex"),
                min=field_cfg.get("min"),
                max=field_cfg.get("max"),
                max_length=field_cfg.get("max_length"),
                min_length=field_cfg.get("min_length"),
                default=field_cfg.get("default"),
                description=field_cfg.get("description", ""),
                items=FieldDef(
                    name="item",
                    type=FieldType(field_cfg.get("items", {}).get("type", "string")),
                ) if field_cfg.get("items") else None,
            )

        return cls(
            name=config.get("name", "unnamed"),
            fields=fields,
            required=required,
            version=config.get("version", "1.0"),
        )