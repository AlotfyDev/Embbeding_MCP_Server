# Pipeline: document.compare

## Capability

`document.compare` — Compare two documents and return cosine similarity.

## Pipeline Stages

```
Input: {key_a, key_b}
    │
    ▼
┌────────────────────────────────────────────┐
│ 1. validate_input                          │
│    • key_a: non-empty string               │
│    • key_b: non-empty string               │
└──────────────────┬─────────────────────────┘
                   ▼
┌────────────────────────────────────────────┐
│ 2. embed_a                                 │
│    • passage prefix + model.embed(key_a)   │
└──────────────────┬─────────────────────────┘
                   ▼
┌────────────────────────────────────────────┐
│ 3. embed_b                                 │
│    • passage prefix + model.embed(key_b)   │
└──────────────────┬─────────────────────────┘
                   ▼
┌────────────────────────────────────────────┐
│ 4. compute_similarity                      │
│    • cosine similarity between vec_a, vec_b│
│    • range: [-1, 1] → typically [0, 1]     │
└──────────────────┬─────────────────────────┘
                   ▼
┌────────────────────────────────────────────┐
│ 5. format                                  │
│    • {similarity, key_a, key_b}            │
└────────────────────────────────────────────┘
    │
    ▼
Output: {similarity: float, key_a: str, key_b: str}
```

## Important Design Note

**Current behavior:** `compare_docs()` receives `key_a` and `key_b` but uses them as raw text to embed, **not** as keys to fetch from the vector DB. This is a temporary limitation.

**Future behavior:** When `VectorDB.get_vector_by_key()` is implemented, the pipeline will:
1. Fetch both vectors from DB
2. Compute cosine similarity on fetched vectors
3. Skip re-embedding entirely

The pipeline design accommodates both paths via a config flag.

## Input Schema

| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| `key_a` | string | yes | non-empty |
| `key_b` | string | yes | non-empty |

## Stages Detail

### 1. validate_input

```python
def validate_input(key_a: str, key_b: str) -> dict:
    if not key_a or not key_a.strip():
        raise ValidationError("key_a must be non-empty")
    if not key_b or not key_b.strip():
        raise ValidationError("key_b must be non-empty")
    return {"key_a": key_a.strip(), "key_b": key_b.strip()}
```

### 2 & 3. embed_a / embed_b

```python
def embed_document(text: str, model: EmbeddingModel) -> list[float]:
    return model.embed("passage: " + text)  # current: text == key
```

### 4. compute_similarity

```python
def cosine_similarity(vec_a: list[float], vec_b: list[float]) -> float:
    dot = sum(a * b for a, b in zip(vec_a, vec_b))
    norm_a = sum(a**2 for a in vec_a) ** 0.5
    norm_b = sum(b**2 for b in vec_b) ** 0.5
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)
```

### 5. format

```python
def format_response(key_a: str, key_b: str, similarity: float) -> dict:
    return {
        "similarity": round(similarity, 6),
        "key_a": key_a,
        "key_b": key_b,
    }
```

## Config Example

```yaml
# pipelines/document-compare.yaml
capability: document.compare
version: "1.0"
description: "Compare two documents via cosine similarity"

schema:
  name: DocumentCompareSchema
  required: [key_a, key_b]
  fields:
    key_a: { type: string, description: "First document key (or text)" }
    key_b: { type: string, description: "Second document key (or text)" }

pipeline:
  embed:
    prefix: "passage: "
    model_field: embedding_model
    source: text  # "text" | "vec_db" (future)

  compute:
    metric: cosine
    normalize: true  # L2 vectors → cosine already normalized

  post_process:
    - stage: format_response
      config:
        fields: [similarity, key_a, key_b]
```

## Full Request/Response Example

```json
// Request
{
  "capability": "document.compare",
  "params": {
    "key_a": "Attention mechanism revolutionized NLP.",
    "key_b": "Transformer models use self-attention."
  }
}

// Response
{
  "similarity": 0.8734,
  "key_a": "Attention mechanism revolutionized NLP.",
  "key_b": "Transformer models use self-attention."
}
```

## Future: Vector Fetch Mode

When `VectorDB.get_vector_by_key()` is added (see `vector_db/base.py` — `find_similar_to_doc` is already `NotImplementedError`), the pipeline adds an optional fetch stage:

```yaml
pipeline:
  fetch:
    source: vec_db
    db_type_field: vec_db_type
    require_keys: true

  embed:
    # only runs if fetch fails to find one or both keys
    source: text
    fallback: true
```

The merged pipeline would be:

```
Input: {key_a, key_b}
    │
    ▼
1. validate_input
    │
    ▼
2. fetch_vectors (opt-in, future)
   ├─ vec_a = vec_db.get_vector(key_a)
   ├─ vec_b = vec_db.get_vector(key_b)
   └─ if both found → skip embed
    │
    ▼
3. embed_a (if fetch failed or not configured)
4. embed_b (if fetch failed or not configured)
    │
    ▼
5. compute_similarity
6. format
```

## Error Cases

| Condition | Error | Code |
|-----------|-------|------|
| Empty key_a | ValidationError | INPUT_INVALID |
| Empty key_b | ValidationError | INPUT_INVALID |
| Identical keys (allowed, similarity=1.0) | — | — |
| Vec dimension mismatch | DimensionMismatchError | DIM_MISMATCH |
