# Pipeline: search.semantic

## Capability

`search.semantic` — Semantic search using query embedding against stored vectors.

## Pipeline Stages

```
Input: {query, top_k?, filters?, response_fields?}
    │
    ▼
┌────────────────────────────────────────────┐
│ 1. validate_input                          │
│    • query: non-empty, ≤ max_text_length   │
│    • top_k: 1 ≤ k ≤ 100 (default 10)       │
│    • filters: optional dict                │
│    • response_fields: optional array       │
└──────────────────┬─────────────────────────┘
                   ▼
┌────────────────────────────────────────────┐
│ 2. embed_query                             │
│    • query prefix: "query: "               │
│    • model.embed_query(query) → vec        │
└──────────────────┬─────────────────────────┘
                   ▼
┌────────────────────────────────────────────┐
│ 3. search                                  │
│    • vec_db.search(vec, top_k, filters)    │
│    → list[SearchResult]                    │
└──────────────────┬─────────────────────────┘
                   ▼
┌────────────────────────────────────────────┐
│ 4. post_process                            │
│    a. score normalization (optional)       │
│       • rescale scores to [0, 1] range     │
│    b. response_projection (if fields       │
│       specified)                           │
│       • filter result fields               │
└────────────────────────────────────────────┘
    │
    ▼
Output: list[{key, score, metadata?, ...}]
```

## Input Schema

| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| `query` | string | yes | 1 ≤ len ≤ max_text_length |
| `top_k` | int | no | 1–100, default 10 |
| `filters` | object | no | metadata filter conditions |
| `response_fields` | array[string] | no | field projection (see 10-response-projection-format.md) |

## Stages Detail

### 1. validate_input

```python
def validate_input(query: str, top_k: int, filters: dict | None) -> dict:
    if not query or not query.strip():
        raise ValidationError("query must be non-empty")
    if len(query) > max_text_length:
        raise ValidationError(f"query exceeds {max_text_length} characters")
    if top_k < 1 or top_k > 100:
        raise ValidationError("top_k must be between 1 and 100")
    return {
        "query": query.strip(),
        "top_k": top_k or 10,
        "filters": filters or {},
    }
```

### 2. embed_query

```python
def embed_query(query: str, model: EmbeddingModel) -> list[float]:
    prefixed = "query: " + query  # E5 query prefix
    return model.embed_query(prefixed)
```

### 3. search

```python
def search(query_vec: list[float], top_k: int, filters: dict, vec_db: VectorDB) -> list[SearchResult]:
    return vec_db.search(query_vec, top_k, filters)
```

### 4. post_process

```python
def post_process(
    results: list[SearchResult],
    response_fields: list[str] | None = None,
    normalize_scores: bool = False,
) -> list[dict]:
    if normalize_scores and results:
        max_score = max(r.score for r in results)
        if max_score > 0:
            for r in results:
                r.score = r.score / max_score

    projected = [r.to_dict() for r in results]

    if response_fields:
        projected = [project_result(r, response_fields) for r in projected]

    return projected
```

## Score Normalization

When `normalize_scores: true` in config:

```
normalized_score = raw_score / max(raw_scores)
```

This rescales all scores to [0, 1] relative to the result set, making results comparable across queries.

## Response Projection

See `10-response-projection-format.md` for full specification.

```python
# Without response_fields:
{"key": "doc1", "score": 0.95, "metadata": {"type": "doc", "source": "wiki"}}

# With response_fields=["key", "score"]:
{"key": "doc1", "score": 0.95}

# With response_fields=["key", "metadata.type"]:
{"key": "doc1", "metadata": {"type": "doc"}}
```

## Config Example

```yaml
# pipelines/semantic-search.yaml
capability: search.semantic
version: "1.0"
description: "Semantic search using query embedding"

schema:
  name: SemanticSearchSchema
  required: [query]
  fields:
    query: { type: string, max_length: 5000 }
    top_k: { type: integer, min: 1, max: 100, default: 10 }
    filters: { type: object, optional: true }
    response_fields: { type: array, items: { type: string }, optional: true }

pipeline:
  embed:
    prefix: "query: "
    model_field: embedding_model

  search:
    db_type_field: vec_db_type

  post_process:
    - stage: normalize_scores
      config:
        enabled: false  # opt-in
    - stage: response_projection
      config:
        fields_param: response_fields
    - stage: format_response
      config:
        type: json_array
```

## Full Request/Response Example

```json
// Request — without projection
{
  "capability": "search.semantic",
  "params": {
    "query": "machine learning transformers",
    "top_k": 3
  }
}

// Response
[
  {
    "key": "doc-001",
    "score": 0.92,
    "metadata": {"type": "doc", "source": "arxiv", "title": "Attention Is All You Need"}
  },
  {
    "key": "doc-002",
    "score": 0.87,
    "metadata": {"type": "doc", "source": "arxiv", "title": "BERT"}
  },
  {
    "key": "note-001",
    "score": 0.65,
    "metadata": {"type": "note", "source": "local"}
  }
]

// Request — with response_fields
{
  "capability": "search.semantic",
  "params": {
    "query": "machine learning transformers",
    "top_k": 3,
    "response_fields": ["key", "score", "metadata.title"]
  }
}

// Response (projected)
[
  {"key": "doc-001", "score": 0.92, "metadata": {"title": "Attention Is All You Need"}},
  {"key": "doc-002", "score": 0.87, "metadata": {"title": "BERT"}},
  {"key": "note-001", "score": 0.65, "metadata": {"title": null}}
]
```

## Error Cases

| Condition | Error | Code |
|-----------|-------|------|
| Empty query | ValidationError | INPUT_INVALID |
| top_k out of range | ValidationError | PARAM_OUT_OF_RANGE |
| filters not valid JSON | ValidationError | FILTERS_INVALID |
| VecDB search fails | VectorDBError | SEARCH_FAILURE |

## Filter Syntax

Filters are passed directly to `vec_db.search()`. Each adapter implements its own filter semantics:

```json
// FAISS: post-filter on metadata dict
{"type": "doc"}

// pgvector: SQL WHERE clause equivalent
{"source": "arxiv", "version": {"$gte": 2}}
```

The filter format is adapter-specific. The pipeline passes filters through without transformation.
