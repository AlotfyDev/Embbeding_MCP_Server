# Pipeline: document.ingest.batch

## Capability

`document.ingest.batch` — Embed and store multiple documents in a single batch operation.

## Pipeline Stages

```
Input: {items: [{key, text, metadata?}, ...]}
    │
    ▼
┌────────────────────────────────────────────┐
│ 1. validate_input                          │
│    • items must be non-empty array         │
│    • each item validated against           │
│      DocumentIngestSchema                  │
│    • batch_size ≤ max_batch_size (32)      │
└──────────────────┬─────────────────────────┘
                   ▼
┌────────────────────────────────────────────┐
│ 2. pre_process (batch)                     │
│    • strip + normalize for each item       │
│    • apply metadata defaults               │
└──────────────────┬─────────────────────────┘
                   ▼
┌────────────────────────────────────────────┐
│ 3. embed (batch)                           │
│    • passage prefix on all texts           │
│    • model.embed_batch(texts) → vectors[]  │
│    • chunked by max_batch_size             │
└──────────────────┬─────────────────────────┘
                   ▼
┌────────────────────────────────────────────┐
│ 4. store (batch)                           │
│    • vec_db.store_batch(items)             │
│    • chunked by max_batch_size             │
└──────────────────┬─────────────────────────┘
                   ▼
┌────────────────────────────────────────────┐
│ 5. post_process                            │
│    • {status: "stored", count: int}        │
└────────────────────────────────────────────┘
    │
    ▼
Output: {status: "stored", count: int}
```

## Input Schema

| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| `items` | array | yes | 1 ≤ len ≤ max_batch_size |
| `items[].key` | string | yes | non-empty, unique per vec_db |
| `items[].text` | string | yes | 1 ≤ len ≤ max_text_length |
| `items[].metadata` | object | no | validated against DocumentSchema |

## Schema Enforcement

Same schema as `document.ingest` (`DocumentIngestSchema`), applied per item.

```yaml
schema:
  name: BatchIngestSchema
  required: [items]
  items:
    type: array
    max_length: ${max_batch_size}
    item_schema:
      ref: DocumentIngestSchema
```

## Stages Detail

### 1. validate_input

```python
def validate_input(items: list[dict], batch_schema: DocumentSchema, max_batch: int) -> list[dict]:
    if not items:
        raise ValidationError("items must be non-empty")
    if len(items) > max_batch:
        raise ValidationError(f"batch exceeds max_batch_size={max_batch}")
    validated = []
    for item in items:
        v = batch_schema.validate(item)
        validated.append(v)
    return validated
```

### 2. pre_process (batch)

```python
def pre_process_batch(items: list[dict]) -> list[dict]:
    for item in items:
        item["text"] = item["text"].strip()
        item["text"] = re.sub(r'\s+', ' ', item["text"])
    return items
```

### 3. embed (batch)

```python
def embed_batch(items: list[dict], model: EmbeddingModel, max_batch: int) -> list[list[float]]:
    texts = ["passage: " + item["text"] for item in items]
    return model.embed_batch(texts)  # internally chunks by max_batch
```

### 4. store (batch)

```python
def store_batch(items: list[dict], vectors: list[list[float]], vec_db: VectorDB) -> None:
    db_items = [
        (item["key"], vectors[i], item.get("metadata"))
        for i, item in enumerate(items)
    ]
    vec_db.store_batch(db_items)
```

### 5. post_process

```python
def post_process(count: int) -> dict:
    return {"status": "stored", "count": count}
```

## Config Example

```yaml
# pipelines/batch-ingest.yaml
capability: document.ingest.batch
version: "1.0"
description: "Embed and store multiple documents in batch"

schema:
  name: BatchIngestSchema
  required: [items]
  items:
    type: array
    max_length_field: max_batch_size
    item_schema:
      ref: DocumentIngestSchema

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
    batch_size_field: max_batch_size

  store:
    db_type_field: vec_db_type
    batch_size_field: max_batch_size

  post_process:
    - stage: format_response
      config:
        fields: [status, count]
```

## Full Request/Response Example

```json
// Request
{
  "capability": "document.ingest.batch",
  "params": {
    "items": [
      {
        "key": "doc-001",
        "text": "Attention mechanism revolutionized NLP.",
        "metadata": {"type": "doc", "source": "arxiv"}
      },
      {
        "key": "doc-002",
        "text": "Transformers are sequence-to-sequence models.",
        "metadata": {"type": "doc", "source": "arxiv"}
      },
      {
        "key": "note-001",
        "text": "Review: read the BERT paper.",
        "metadata": {"type": "note"}
      }
    ]
  }
}

// Response
{
  "status": "stored",
  "count": 3
}
```

## Chunking Behavior

When `len(items) > max_batch_size`, the pipeline splits into multiple sub-batches:

```python
for i in range(0, len(items), max_batch_size):
    sub_batch = items[i : i + max_batch_size]
    vectors = model.embed_batch(sub_batch_texts)
    vec_db.store_batch([(k, v, m) for ...])
```

## Error Cases

| Condition | Error | Code |
|-----------|-------|------|
| Empty items array | ValidationError | INPUT_INVALID |
| Items > max_batch_size | ValidationError | BATCH_TOO_LARGE |
| One item has invalid metadata | SchemaValidationError | SCHEMA_VIOLATION |
| One item exceeds text length | ValidationError | TEXT_TOO_LONG |
| Partial failure (middle of batch) | VectorDBError | STORE_FAILURE |

### Partial Failure Strategy

Current design: **all-or-nothing**. If any item fails validation, the entire batch is rejected. If a vec_db store fails mid-batch, the error propagates (no rollback — vec_db adapter responsibility).

Future consideration: transactional batches with rollback.
