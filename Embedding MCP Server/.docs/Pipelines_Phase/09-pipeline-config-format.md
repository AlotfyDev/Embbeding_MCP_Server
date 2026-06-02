# Pipeline Config Format — صيغة تعريف pipeline في YAML

## Overview

Every pipeline is defined as a YAML file. The YAML declares:
- **Metadata**: capability name, version, description
- **Schema**: input validation rules
- **Pipeline**: ordered stages with configuration
- **Embed/Store**: model and vector DB field references

## Top-Level Structure

```yaml
# pipelines/<capability>.yaml
capability: <string>          # unique capability identifier
version: <string>             # schema version (semver)
description: <string>         # human-readable description

schema:                       # input validation rules
  name: <string>              # schema name for registry
  required: [<field>, ...]    # required field names
  fields:                     # field definitions
    <field_name>:
      type: <string>          # string | integer | float | boolean | object | array
      required: <bool>        # overrides 'required' list
      description: <string>
      # type-specific constraints:
      max_length: <int>       # string
      regex: <string>         # string
      enum: [<value>, ...]    # any type
      min: <number>           # numeric
      max: <number>           # numeric
      default: <any>          # default value
      items:                  # array item definition
        type: <string>
      optional: <bool>        # convenience flag

pipeline:                     # ordered stage definitions
  pre_process:                # cleaning / normalization
    - stage: <stage_name>
      config: <dict>
  embed:                      # embedding configuration
    prefix: <string>          # "passage: " or "query: "
    model_field: <string>     # Settings field for model type
    batch_size_field: <string># Settings field for batch size
  store:                      # storage configuration
    db_type_field: <string>   # Settings field for vec_db type
    batch_size_field: <string># optional, for batch ops
  search:                     # search configuration
    db_type_field: <string>
  post_process:               # response formatting
    - stage: <stage_name>
      config: <dict>
```

## Complete Example: document.ingest

```yaml
# pipelines/document-ingest.yaml
capability: document.ingest
version: "1.0"
description: "Embed and store a single document"

schema:
  name: DocumentIngestSchema
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

pipeline:
  pre_process:
    - stage: strip
      config: {}
    - stage: normalize_whitespace
      config: {}
    - stage: apply_metadata_defaults
      config:
        schema: DocumentIngestSchema

  embed:
    prefix: "passage: "
    model_field: embedding_model
    batch_size: 1

  store:
    db_type_field: vec_db_type

  post_process:
    - stage: format_response
      config:
        fields: [status, key, dim]
```

## Complete Example: search.semantic

```yaml
# pipelines/semantic-search.yaml
capability: search.semantic
version: "1.0"
description: "Semantic search using query embedding"

schema:
  name: SemanticSearchSchema
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
      optional: true
    response_fields:
      type: array
      items:
        type: string
      optional: true

pipeline:
  embed:
    prefix: "query: "
    model_field: embedding_model

  search:
    db_type_field: vec_db_type

  post_process:
    - stage: normalize_scores
      config:
        enabled: false
    - stage: response_projection
      config:
        fields_param: response_fields
    - stage: format_response
      config:
        type: json_array
```

## Complete Example: system.health

```yaml
# pipelines/system-health.yaml
capability: system.health
version: "1.0"
description: "Check system health status"

schema:
  name: HealthSchema
  required: []
  fields: {}

pipeline:
  checks:
    - stage: check_embedding_model
      config:
        model_field: embedding_model
        probe_text: "health check"
    - stage: check_vector_db
      config:
        db_type_field: vec_db_type

  post_process:
    - stage: aggregate_health
      config:
        status_field: status
    - stage: format_response
      config:
        fields: [status, model, vector_db]
```

## Config Field Reference

### Stage Types

| Stage | Category | Description |
|-------|----------|-------------|
| `strip` | pre_process | Trim whitespace |
| `normalize_whitespace` | pre_process | Collapse multiple spaces |
| `apply_metadata_defaults` | pre_process | Fill missing metadata fields |
| `validate_schema` | pre_process | Validate against schema |
| `format_response` | post_process | Shape output dict |
| `normalize_scores` | post_process | Rescale scores to [0,1] |
| `response_projection` | post_process | Filter response fields |
| `aggregate_health` | post_process | Merge component statuses |

### Embed Config

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `prefix` | string | Text prefix for E5 models | `"passage: "` |
| `model_field` | string | Settings attribute for model | `embedding_model` |
| `batch_size_field` | string | Settings attribute for batch | `max_batch_size` |
| `batch_size` | int | Fixed batch size (overrides field) | `32` |

### Store/Search Config

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `db_type_field` | string | Settings attribute for vec_db | `vec_db_type` |

### Config Variable Substitution

Values wrapped in `${}` reference `Settings` fields at runtime:

```yaml
embed:
  prefix: "passage: "
  model_field: embedding_model          # → Settings().embedding_model
  batch_size_field: max_batch_size      # → Settings().max_batch_size
```

This allows pipelines to be environment-agnostic — the same YAML works with different models and databases.

## File Organization

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

Each file maps to one capability. The file name convention is `<category>-<action>.yaml`.

## Loading Pipelines from Config

```python
# concept
def load_pipeline_from_yaml(path: str, settings: Settings) -> CapabilityPipeline:
    with open(path) as f:
        config = yaml.safe_load(f)

    # Resolve ${variable} references
    resolved = resolve_config_vars(config, settings)

    # Build pipeline from resolved config
    pipeline = CapabilityPipeline(
        capability=resolved["capability"],
        version=resolved.get("version", "1.0"),
        schema=DocumentSchema.from_config(resolved["schema"]),
        stages=build_stages(resolved["pipeline"]),
    )
    return pipeline
```

## Schema Inheritance (Optional)

```yaml
# pipelines/extended-ingest.yaml
capability: document.ingest.extended
version: "1.0"
extends: document.ingest           # inherit schema + pipeline

schema:
  # add extra fields on top of inherited
  fields:
    metadata.tenant_id:
      type: string
      required: true
    metadata.priority:
      type: integer
      min: 0
      max: 5
      default: 0

pipeline:
  pre_process:
    - stage: validate_tenant
      config: {}
```
