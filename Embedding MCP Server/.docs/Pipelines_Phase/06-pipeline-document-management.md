# Pipeline: Document Management (delete, count, health)

## Overview

Three lightweight capabilities grouped together because each is a single-stage pipeline with no embedding step.

---

## 6.1 Capability: `document.delete`

### Description

Delete a document from the vector database by key.

### Pipeline Stages

```
Input: {key}
    │
    ▼
┌──────────────────────────────────────────┐
│ 1. validate_key                          │
│    • key: non-empty string               │
└──────────────────┬───────────────────────┘
                   ▼
┌──────────────────────────────────────────┐
│ 2. vec_db.delete(key)                    │
└──────────────────┬───────────────────────┘
                   ▼
┌──────────────────────────────────────────┐
│ 3. format response                       │
│    • {status: "deleted", key}            │
└──────────────────────────────────────────┘
    │
    ▼
Output: {status: "deleted", key: str}
```

### Input Schema

| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| `key` | string | yes | non-empty |

### Stages Detail

```python
def validate_key(key: str) -> str:
    if not key or not key.strip():
        raise ValidationError("key must be non-empty")
    return key.strip()

def delete(key: str, vec_db: VectorDB) -> None:
    vec_db.delete(key)

def format_response(key: str) -> dict:
    return {"status": "deleted", "key": key}
```

### Config

```yaml
capability: document.delete
version: "1.0"
description: "Delete a document by key"

schema:
  required: [key]
  fields:
    key: { type: string, description: "Document key to delete" }

pipeline:
  validate:
    - stage: validate_key
  execute:
    - stage: vec_db_delete
      config:
        db_type_field: vec_db_type
  post_process:
    - stage: format_response
      config:
        fields: [status, key]
```

### Example

```json
// Request
{"capability": "document.delete", "params": {"key": "doc-001"}}

// Response
{"status": "deleted", "key": "doc-001"}

// Response (key not found — vec_db.delete is idempotent)
{"status": "deleted", "key": "doc-001"}  // same response
```

### Error Cases

| Condition | Error | Code |
|-----------|-------|------|
| Empty key | ValidationError | INPUT_INVALID |
| VecDB delete fails | VectorDBError | DELETE_FAILURE |

Note: `vec_db.delete()` is **idempotent** — deleting a non-existent key is not an error.

---

## 6.2 Capability: `document.count`

### Description

Return the total number of documents stored in the vector database.

### Pipeline Stages

```
Input: (none)
    │
    ▼
┌──────────────────────────────────────────┐
│ 1. vec_db.count()                        │
└──────────────────┬───────────────────────┘
                   ▼
┌──────────────────────────────────────────┐
│ 2. format                                │
│    • {count: int}                        │
└──────────────────────────────────────────┘
    │
    ▼
Output: {count: int}
```

### Config

```yaml
capability: document.count
version: "1.0"
description: "Count stored documents"

schema:
  required: []
  fields: {}

pipeline:
  execute:
    - stage: vec_db_count
      config:
        db_type_field: vec_db_type
  post_process:
    - stage: format_response
      config:
        fields: [count]
```

### Example

```json
// Request
{"capability": "document.count", "params": {}}

// Response
{"count": 42}
```

### Error Cases

| Condition | Error | Code |
|-----------|-------|------|
| VecDB count fails | VectorDBError | COUNT_FAILURE |

---

## 6.3 Capability: `system.health`

### Description

Check the health of the embedding model and vector database.

### Pipeline Stages

```
Input: (none)
    │
    ▼
┌──────────────────────────────────────────┐
│ 1. check_model                           │
│    • model.embed("health check")         │
│    • if success: dim=N                   │
│    • if fail: error message              │
└──────────────────┬───────────────────────┘
                   ▼
┌──────────────────────────────────────────┐
│ 2. check_vec_db                          │
│    • vec_db.count()                      │
│    • if success: count=N                 │
│    • if fail: error message              │
└──────────────────┬───────────────────────┘
                   ▼
┌──────────────────────────────────────────┐
│ 3. aggregate                             │
│    • overall status: ok/error            │
│    • merge component statuses            │
└──────────────────────────────────────────┘
    │
    ▼
Output: {status, model, vector_db, ...}
```

### Stages Detail

```python
def check_model(model: EmbeddingModel) -> dict:
    try:
        test_vec = model.embed("health check")
        return {"status": "ok", "dim": len(test_vec)}
    except Exception as e:
        return {"status": "error", "error": str(e)}

def check_vec_db(vec_db: VectorDB) -> dict:
    try:
        count = vec_db.count()
        return {"status": "ok", "count": count}
    except Exception as e:
        return {"status": "error", "error": str(e)}

def aggregate(model_status: dict, db_status: dict) -> dict:
    overall = "ok" if model_status["status"] == "ok" and db_status["status"] == "ok" else "error"
    return {
        "status": overall,
        "model": model_status,
        "vector_db": db_status,
    }
```

### Config

```yaml
capability: system.health
version: "1.0"
description: "Check system health"

schema:
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
  aggregate:
    - stage: aggregate_health
      config:
        status_field: status
```

### Example

```json
// Request
{"capability": "system.health", "params": {}}

// Response (healthy)
{
  "status": "ok",
  "model": {"status": "ok", "dim": 384},
  "vector_db": {"status": "ok", "count": 42}
}

// Response (model failed)
{
  "status": "error",
  "model": {"status": "error", "error": "Model not loaded"},
  "vector_db": {"status": "ok", "count": 42}
}
```

### Error Cases

Non-fatal by design — individual component failures are reported in the response rather than raising exceptions.

---

## Summary

| Capability | Input | Output | Embedding Required |
|-----------|-------|--------|--------------------|
| `document.delete` | `key` | `{status, key}` | no |
| `document.count` | (none) | `{count}` | no |
| `system.health` | (none) | `{status, model, vector_db}` | yes (probe only) |
