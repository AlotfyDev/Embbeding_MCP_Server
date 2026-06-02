# Schema Enforcement Layer — فرض schemas على ingestion/output

## Concept

A centralized schema registry that validates pipeline inputs and outputs against registered schemas. Decouples validation rules from pipeline logic — schemas are defined in config, not code.

## Core Types

```python
# concept — design only, not implementation
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class FieldType(Enum):
    STRING = "string"
    INTEGER = "integer"
    FLOAT = "float"
    BOOLEAN = "boolean"
    OBJECT = "object"
    ARRAY = "array"


@dataclass
class FieldDef:
    """Definition of a single field in a schema."""
    name: str
    type: FieldType
    required: bool = False
    enum: list[Any] | None = None        # allowed values
    regex: str | None = None             # string pattern
    min: float | None = None             # numeric min
    max: float | None = None             # numeric max
    max_length: int | None = None        # string max length
    default: Any | None = None           # default value
    description: str = ""


@dataclass
class DocumentSchema:
    """Schema definition for a capability's input/output."""
    name: str
    fields: dict[str, FieldDef]
    required: list[str]
    version: str = "1.0"

    def validate(self, data: dict) -> dict:
        """Validate data against this schema.

        Returns validated data (with defaults applied).
        Raises SchemaValidationError on violation.
        """
        validated = {}

        # Check required fields
        for field_name in self.required:
            if field_name not in data or data[field_name] is None:
                raise SchemaValidationError(
                    f"Missing required field: '{field_name}'",
                    field=field_name,
                )

        # Validate each provided field
        for key, value in data.items():
            if key not in self.fields:
                raise SchemaValidationError(
                    f"Unknown field: '{key}'",
                    field=key,
                )

            field_def = self.fields[key]
            validated[key] = self._validate_field(key, value, field_def)

        # Apply defaults for optional missing fields
        for field_name, field_def in self.fields.items():
            if field_name not in validated and not field_def.required:
                if field_def.default is not None:
                    validated[field_name] = field_def.default

        return validated

    def _validate_field(self, name: str, value: Any, field_def: FieldDef) -> Any:
        """Validate a single field value."""

        # Type check
        if field_def.type == FieldType.STRING:
            if not isinstance(value, str):
                raise SchemaValidationError(
                    f"Field '{name}' must be string, got {type(value).__name__}",
                    field=name,
                )
            if field_def.max_length and len(value) > field_def.max_length:
                raise SchemaValidationError(
                    f"Field '{name}' exceeds max_length={field_def.max_length}",
                    field=name,
                )
            if field_def.regex and not re.match(field_def.regex, value):
                raise SchemaValidationError(
                    f"Field '{name}' does not match pattern {field_def.regex}",
                    field=name,
                )

        elif field_def.type == FieldType.INTEGER:
            if not isinstance(value, int) or isinstance(value, bool):
                raise SchemaValidationError(
                    f"Field '{name}' must be integer",
                    field=name,
                )
            if field_def.min is not None and value < field_def.min:
                raise SchemaValidationError(
                    f"Field '{name}' < min={field_def.min}",
                    field=name,
                )
            if field_def.max is not None and value > field_def.max:
                raise SchemaValidationError(
                    f"Field '{name}' > max={field_def.max}",
                    field=name,
                )

        # Enum check
        if field_def.enum is not None and value not in field_def.enum:
            raise SchemaValidationError(
                f"Field '{name}' must be one of {field_def.enum}, got '{value}'",
                field=name,
            )

        return value
```

## Schema Registry

```python
# concept
class SchemaRegistry:
    """Central registry for all capability schemas."""

    def __init__(self):
        self._schemas: dict[str, DocumentSchema] = {}

    def register(self, capability: str, schema: DocumentSchema) -> None:
        self._schemas[capability] = schema

    def get(self, capability: str) -> DocumentSchema | None:
        return self._schemas.get(capability)

    def load_from_config(self, config: dict) -> None:
        """Load schemas from pipeline YAML configs."""
        for capability, schema_cfg in config.items():
            fields = {}
            required = schema_cfg.get("required", [])
            for field_name, field_cfg in schema_cfg.get("fields", {}).items():
                fields[field_name] = FieldDef(
                    name=field_name,
                    type=FieldType(field_cfg.get("type", "string")),
                    required=field_name in required,
                    enum=field_cfg.get("enum"),
                    max_length=field_cfg.get("max_length"),
                    min=field_cfg.get("min"),
                    max=field_cfg.get("max"),
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
```

## Schema Error

```python
class SchemaValidationError(Exception):
    """Raised when input/output violates a schema."""

    def __init__(self, message: str, field: str | None = None, code: str = "SCHEMA_VIOLATION"):
        self.field = field
        self.code = code
        super().__init__(message)
```

## Schema from YAML — Examples

```yaml
# schemas/document-ingest.yaml
name: DocumentIngestSchema
version: "1.0"
required: [key, text]
fields:
  key:
    type: string
    required: true
    description: "Unique document identifier"
    regex: "^[a-zA-Z0-9_-]+$"
  text:
    type: string
    required: true
    max_length: 5000
    description: "Document content"
  metadata.type:
    type: string
    enum: [doc, note, ticket, code]
    default: doc
  metadata.source:
    type: string
    default: ""
  metadata.version:
    type: integer
    min: 1
    max: 999
    default: 1
```

```yaml
# schemas/semantic-search.yaml
name: SemanticSearchSchema
version: "1.0"
required: [query]
fields:
  query:
    type: string
    required: true
    max_length: 5000
  top_k:
    type: integer
    min: 1
    max: 100
    default: 10
  filters:
    type: object
  response_fields:
    type: array
    items:
      type: string
```

## Deep Field Paths

Metadata fields use dot notation for nested validation:

```yaml
fields:
  metadata.type:        # → data["metadata"]["type"]
    type: string
    enum: [doc, note, ticket, code]
  metadata.source:      # → data["metadata"]["source"]
    type: string
```

```python
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
```

## Schema Versioning (Optional)

```yaml
# schemas/document-ingest-v2.yaml
name: DocumentIngestSchema
version: "2.0"
extends: "1.0"        # inherit from v1
required: [key, text, metadata.tenant_id]  # added required field
fields:
  metadata.tenant_id:
    type: string
    required: true
    regex: "^tenant_[a-z0-9]+$"
```

Each capability can declare which schema version it expects:

```python
router.register(pipeline, schema_version="1.0")
# or
pipeline:
  capability: document.ingest
  schema_version: "2.0"
```

## Integration with Router

```python
# concept — wiring schema enforcement into route()
router = CapabilityRouter()
registry = SchemaRegistry()
registry.load_from_config("schemas/")

router.add_middleware(SchemaValidationMiddleware(registry))
```

The middleware runs before pipeline execution:

```
Request → SchemaValidationMiddleware → Pipeline.execute() → Response
               │                           │
           validates                    schema also available
           params against               for output projection
           DocumentSchema                (optional validation)
```

## Output Schema Validation (Optional)

Schemas can also validate pipeline outputs:

```python
pipeline:
  schema:
    input: DocumentIngestSchema
    output:                          # optional output schema
      type: object
      fields: [status, key, dim]
      required: [status, key]
```

This is useful for contract testing and API versioning.
