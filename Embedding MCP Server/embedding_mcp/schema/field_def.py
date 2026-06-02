"""Field definition types and constraints for schema validation."""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class FieldType(Enum):
    """Supported field types for schema validation."""
    STRING = "string"
    INTEGER = "integer"
    FLOAT = "float"
    BOOLEAN = "boolean"
    OBJECT = "object"
    ARRAY = "array"


@dataclass
class FieldDef:
    """Definition of a single field in a schema.

    Attributes:
        name: Field name (supports dot notation for nested fields)
        type: Field type from FieldType enum
        required: Whether field is required
        enum: Allowed values (optional)
        regex: Pattern for string validation (optional)
        min: Minimum value for numeric fields (optional)
        max: Maximum value for numeric fields (optional)
        max_length: Maximum length for string fields (optional)
        min_length: Minimum length for string fields (optional)
        default: Default value for optional fields (optional)
        description: Human-readable description (optional)
        items: Item definition for array fields (optional)
    """
    name: str
    type: FieldType
    required: bool = False
    enum: list[Any] | None = None
    regex: str | None = None
    min: float | None = None
    max: float | None = None
    max_length: int | None = None
    min_length: int | None = None
    default: Any | None = None
    description: str = ""
    items: FieldDef | None = None

    def validate(self, value: Any) -> Any:
        """Validate a value against this field definition.

        Args:
            value: Value to validate

        Returns:
            Validated value (may have defaults applied)

        Raises:
            SchemaValidationError: If validation fails
        """
        # Type check
        if self.type == FieldType.STRING:
            if not isinstance(value, str):
                raise SchemaValidationError(
                    f"Field '{self.name}' must be string, got {type(value).__name__}",
                    field=self.name,
                )
            if self.max_length is not None and len(value) > self.max_length:
                raise SchemaValidationError(
                    f"Field '{self.name}' exceeds max_length={self.max_length}",
                    field=self.name,
                )
            if self.min_length is not None and len(value) < self.min_length:
                raise SchemaValidationError(
                    f"Field '{self.name}' below min_length={self.min_length}",
                    field=self.name,
                )
            if self.regex is not None and not re.match(self.regex, value or ""):
                raise SchemaValidationError(
                    f"Field '{self.name}' does not match pattern {self.regex}",
                    field=self.name,
                )

        elif self.type == FieldType.INTEGER:
            if not isinstance(value, int) or isinstance(value, bool):
                raise SchemaValidationError(
                    f"Field '{self.name}' must be integer",
                    field=self.name,
                )
            if self.min is not None and value < self.min:
                raise SchemaValidationError(
                    f"Field '{self.name}' < min={self.min}",
                    field=self.name,
                )
            if self.max is not None and value > self.max:
                raise SchemaValidationError(
                    f"Field '{self.name}' > max={self.max}",
                    field=self.name,
                )

        elif self.type == FieldType.FLOAT:
            if not isinstance(value, (int, float)) or isinstance(value, bool):
                raise SchemaValidationError(
                    f"Field '{self.name}' must be numeric",
                    field=self.name,
                )
            num_value = float(value)
            if self.min is not None and num_value < self.min:
                raise SchemaValidationError(
                    f"Field '{self.name}' < min={self.min}",
                    field=self.name,
                )
            if self.max is not None and num_value > self.max:
                raise SchemaValidationError(
                    f"Field '{self.name}' > max={self.max}",
                    field=self.name,
                )

        elif self.type == FieldType.BOOLEAN:
            if not isinstance(value, bool):
                raise SchemaValidationError(
                    f"Field '{self.name}' must be boolean",
                    field=self.name,
                )

        elif self.type == FieldType.OBJECT:
            if not isinstance(value, dict):
                raise SchemaValidationError(
                    f"Field '{self.name}' must be object",
                    field=self.name,
                )

        elif self.type == FieldType.ARRAY:
            if not isinstance(value, list):
                raise SchemaValidationError(
                    f"Field '{self.name}' must be array",
                    field=self.name,
                )
            # Optionally validate items
            if self.items is not None:
                for item in value:
                    self.items.validate(item)

        # Enum check
        if self.enum is not None and value not in self.enum:
            raise SchemaValidationError(
                f"Field '{self.name}' must be one of {self.enum}, got '{value}'",
                field=self.name,
            )

        return value