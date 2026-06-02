"""Schema registry for managing and discovering schemas."""
from __future__ import annotations

import yaml
from pathlib import Path
from typing import Any

from embedding_mcp.schema.base import DocumentSchema
from embedding_mcp.schema.errors import SchemaValidationError


class SchemaRegistry:
    """Central registry for all capability schemas.

    Manages schema registration, retrieval, and YAML loading.
    """

    def __init__(self):
        self._schemas: dict[str, DocumentSchema] = {}

    def register(self, capability: str, schema: DocumentSchema) -> None:
        """Register a schema for a capability.

        Args:
            capability: Capability identifier (e.g., "document.ingest")
            schema: DocumentSchema instance
        """
        self._schemas[capability] = schema

    def get(self, capability: str) -> DocumentSchema | None:
        """Get schema for a capability.

        Args:
            capability: Capability identifier

        Returns:
            DocumentSchema if registered, None otherwise
        """
        return self._schemas.get(capability)

    def load_from_config(self, config: dict[str, Any]) -> None:
        """Load schemas from pipeline YAML configs.

        Args:
            config: Dict mapping capability names to schema configs
        """
        for capability, schema_cfg in config.items():
            fields = {}
            required = schema_cfg.get("required", [])

            for field_name, field_cfg in schema_cfg.get("fields", {}).items():
                from embedding_mcp.schema.field_def import FieldDef, FieldType
                fields[field_name] = FieldDef(
                    name=field_name,
                    type=FieldType(field_cfg.get("type", "string")),
                    required=field_name in required,
                    enum=field_cfg.get("enum"),
                    regex=field_cfg.get("regex"),
                    min=field_cfg.get("min"),
                    max=field_cfg.get("max"),
                    max_length=field_cfg.get("max_length"),
                    min_length=field_cfg.get("min_length"),
                    default=field_cfg.get("default"),
                    description=field_cfg.get("description", ""),
                )

            schema = DocumentSchema(
                name=schema_cfg.get("name", capability),
                fields=fields,
                required=required,
                version=schema_cfg.get("version", "1.0"),
            )
            self.register(capability, schema)

    def load_from_yaml(self, path: str | Path) -> None:
        """Load schemas from a YAML file.

        Args:
            path: Path to schema YAML file
        """
        path = Path(path)
        if not path.exists():
            return

        with open(path) as f:
            config = yaml.safe_load(f)

        if config:
            self.load_from_config(config)

    def validate(self, capability: str, data: dict) -> dict:
        """Validate data against a capability's schema.

        Args:
            capability: Capability identifier
            data: Input data to validate

        Returns:
            Validated data

        Raises:
            SchemaValidationError: If schema not found or validation fails
        """
        schema = self.get(capability)
        if not schema:
            raise SchemaValidationError(
                f"No schema registered for capability: '{capability}'",
                code="SCHEMA_NOT_FOUND",
            )
        return schema.validate(data)