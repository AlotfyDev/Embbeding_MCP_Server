# Wave 1: Foundation Layer - Schema System

## Objective
Implement the Schema Enforcement Layer to validate pipeline inputs against typed definitions.

## Files to Create

### 1. `embedding_mcp/schema/field_def.py`
```python
# FieldType enum and FieldDef dataclass
# - Types: STRING, INTEGER, FLOAT, BOOLEAN, OBJECT, ARRAY
# - Constraints: required, enum, regex, min, max, max_length, default
# - Nested field support via dot notation
```

### 2. `embedding_mcp/schema/errors.py`
```python
# SchemaValidationError exception
# - message: str
# - field: str | None
# - code: str (default "SCHEMA_VIOLATION")
```

### 3. `embedding_mcp/schema/registry.py`
```python
# SchemaRegistry class
# - register(capability: str, schema: DocumentSchema)
# - get(capability: str) -> DocumentSchema | None
# - load_from_yaml(path: str) -> None

# DocumentSchema class  
# - name: str
# - fields: dict[str, FieldDef]
# - required: list[str]
# - validate(data: dict) -> dict
```

## Implementation Steps

1. Create FieldType enum with JSON schema equivalents
2. Create FieldDef dataclass with all constraints from spec
3. Create DocumentSchema.validate() with nested field resolution
4. Create SchemaRegistry with YAML loading support
5. Add deep field path helpers (_resolve_nested, _set_nested)

## Dependencies
- None (pure Python, no external deps)

## Verification
- Unit tests: validate field types, enums, regex patterns
- Unit tests: nested field resolution ("metadata.type" → data["metadata"]["type"])
- Unit tests: cross-field validation (dim matching model)