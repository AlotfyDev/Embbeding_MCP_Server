# Wave 5: Configuration and YAML Integration

## Objective
Parse YAML pipeline definitions and auto-wire components.

## Files to Create

### 1. `embedding_mcp/pipelines/config_loader.py`
```python
# load_pipeline_from_yaml(path: str, settings: Settings) -> CapabilityPipeline
# - Parse YAML file
# - Resolve ${variable} references
# - Instantiate pipeline with deps

# resolve_config_vars(config: dict, settings: Settings) -> dict
# - Replace ${field} with settings.field values

# build_stages(stages_config: list) -> list[Stage]
# - Create stage callables from config
```

### 2. `embedding_mcp/schema/validators.py`
```python
# Pydantic-style validators for FieldDef
# - validate_type(value, expected_type) -> value
# - validate_constraints(value, field_def) -> value
# - apply_defaults(data, schema) -> data
```

## YAML Structure

### Schema Section
```yaml
schema:
  name: DocumentIngestSchema
  required: [key, text]
  fields:
    key:
      type: string
      required: true
      regex: "^[a-zA-Z0-9_-]+$"
    text:
      type: string
      required: true
      max_length: 5000
    metadata.type:
      type: string
      enum: [doc, note, ticket, code]
      default: doc
```

### Pipeline Section
```yaml
pipeline:
  pre_process:
    - stage: strip
      config: {}
    - stage: normalize_whitespace
      config: {}
  embed:
    prefix: "passage: "
    model_field: embedding_model
    batch_size_field: max_batch_size
  store:
    db_type_field: vec_db_type
  post_process:
    - stage: response_projection
      config:
        fields_param: response_fields
    - stage: format_response
      config:
        fields: [status, key, dim]
```

## Variable Substitution

| Syntax | Resolution | Example |
|--------|------------|---------|
| `${max_batch_size}` | Settings.max_batch_size | 32 |
| `${embedding_model}` | Settings.embedding_model | "e5-small" |
| `${vec_db_type}` | Settings.vec_db_type | "faiss" |

## Directory Structure

```
pipelines/
├── document-ingest.yaml
├── batch-ingest.yaml
├── semantic-search.yaml
├── hybrid-search.yaml
├── document-compare.yaml
├── document-delete.yaml
├── document-count.yaml
└── system-health.yaml
```

## Verification
- YAML parsing tests
- Variable substitution tests
- Config-to-pipeline instantiation tests
- Missing field/default behavior tests