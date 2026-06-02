# Pipeline: document.ingest

## Capability

`document.ingest` — Embed and store a single document with metadata.

## Pipeline Stages

```
Input: {key, text, metadata?}
    │
    ▼
┌──────────────────────────────────────┐
│ 1. validate_input                    │
│    • key: non-empty string           │
│    • text: 1 ≤ len ≤ max_text_length │
│    • metadata: optional, against     │
│      registered DocumentSchema       │
└──────────────┬───────────────────────┘
               ▼
┌──────────────────────────────────────┐
│ 2. pre_process                       │
│    • strip whitespace from text      │
│    • normalize internal whitespace   │
│    • apply metadata defaults         │
└──────────────┬───────────────────────┘
               ▼
┌──────────────────────────────────────┐
│ 3. embed                             │
│    • prepend passage prefix          │
│    • model.embed(text) → vector      │
└──────────────┬───────────────────────┘
               ▼
┌──────────────────────────────────────┐
│ 4. store                             │
│    • vec_db.store(key, vec, metadata)│
└──────────────┬───────────────────────┘
               ▼
┌──────────────────────────────────────┐
│ 5. post_process                      │
│    • format response                 │
│    • {status, key, dim}              │
└──────────────────────────────────────┘
    │
    ▼
Output: {status: "stored", key: str, dim: int}
```

## Input Schema

| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| `key` | string | yes | non-empty, unique per vec_db |
| `text` | string | yes | 1 ≤ length ≤ max_text_length (5000 default) |
| `metadata` | object | no | validated against DocumentSchema |

## Schema Enforcement

```yaml
# Registered schema for document.ingest
name: DocumentIngestSchema
required_fields: ["key", "text"]
optional_fields:
  - "metadata.type"
  - "metadata.source"
  - "metadata.version"
metadata.type:
  type: string
  enum: ["doc", "note", "ticket", "code"]
  default: "doc"
metadata.source:
  type: string
  default: ""
metadata.version:
  type: integer
  default: 1
```

## Stages Detail

### 1. validate_input

```python
def validate_input(key: str, text: str, metadata: dict | None, schema: DocumentSchema) -> dict:
    if not key or not key.strip():
        raise ValidationError("key must be non-empty")
    if not text or not text.strip():
        raise ValidationError("text must be non-empty")
    if len(text) > max_text_length:
        raise ValidationError(f"text exceeds {max_text_length} characters")
    validated_meta = schema.validate(metadata or {})
    return {"key": key.strip(), "text": text.strip(), "metadata": validated_meta}
```

### 2. pre_process

```python
def pre_process(text: str) -> str:
    text = text.strip()
    text = re.sub(r'\s+', ' ', text)  # normalize whitespace
    return text
```

### 3. embed

```python
def embed(text: str, model: EmbeddingModel) -> list[float]:
    prefixed = "passage: " + text  # E5 passage prefix
    return model.embed(prefixed)
```

### 4. store

```python
def store(key: str, vector: list[float], metadata: dict, vec_db: VectorDB) -> None:
    vec_db.store(key, vector, metadata)
```

### 5. post_process

```python
def post_process(key: str, vector: list[float]) -> dict:
    return {"status": "stored", "key": key, "dim": len(vector)}
```

## Config Example

```yaml
# pipelines/document-ingest.yaml
capability: document.ingest
version: "1.0"
description: "Embed and store a single document"

schema:
  name: DocumentIngestSchema
  required: [key, text]
  fields:
    key: { type: string, description: "Unique document identifier" }
    text: { type: string, max_length: 5000, description: "Document content" }
    metadata.type: { type: string, enum: [doc, note, ticket, code], default: doc }
    metadata.source: { type: string, default: "" }
    metadata.version: { type: integer, default: 1 }

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

## Full Request/Response Example

```json
// Request
{
  "capability": "document.ingest",
  "params": {
    "key": "doc-001",
    "text": "Attention mechanism revolutionized NLP.",
    "metadata": {
      "type": "doc",
      "source": "arxiv"
    }
  }
}

// Response
{
  "status": "stored",
  "key": "doc-001",
  "dim": 384
}
```

## Error Cases

| Condition | Error | Code |
|-----------|-------|------|
| Empty key | ValidationError | INPUT_INVALID |
| Text exceeds max_text_length | ValidationError | TEXT_TOO_LONG |
| metadata.type not in enum | SchemaValidationError | SCHEMA_VIOLATION |
| Key already exists (unchecked by design) | — | — (upsert behavior depends on vec_db) |
| Model load failure | ModelLoadError | MODEL_FAILURE |
| VecDB write failure | VectorDBError | STORE_FAILURE |
