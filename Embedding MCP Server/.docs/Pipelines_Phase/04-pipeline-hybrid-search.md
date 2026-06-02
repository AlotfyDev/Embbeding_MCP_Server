# Pipeline: search.hybrid

## Capability

`search.hybrid` — Hybrid search combining semantic similarity with keyword-based score boosting.

## Pipeline Stages

```
Input: {query, keywords, top_k?, boost_factor?, response_fields?}
    │
    ▼
┌────────────────────────────────────────────┐
│ 1. validate_input                          │
│    • query: non-empty                      │
│    • keywords: non-empty array[string]      │
│    • top_k: 1–100                          │
│    • boost_factor: ≥ 0                     │
└──────────────────┬─────────────────────────┘
                   ▼
┌────────────────────────────────────────────┐
│ 2. semantic_search                         │
│    • run search.semantic with top_k * 2    │
│      (over-fetch for re-ranking room)      │
└──────────────────┬─────────────────────────┘
                   ▼
┌────────────────────────────────────────────┐
│ 3. keyword_boost                           │
│    • for each result:                      │
│      matches = count keywords in text      │
│      score += matches * boost_factor       │
└──────────────────┬─────────────────────────┘
                   ▼
┌────────────────────────────────────────────┐
│ 4. re_sort                                 │
│    • sort descending by boosted score      │
└──────────────────┬─────────────────────────┘
                   ▼
┌────────────────────────────────────────────┐
│ 5. truncate                                │
│    • slice top_k from sorted results       │
└──────────────────┬─────────────────────────┘
                   ▼
┌────────────────────────────────────────────┐
│ 6. response_projection (optional)          │
└────────────────────────────────────────────┘
    │
    ▼
Output: list[{key, score, metadata, ...}]
```

## Input Schema

| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| `query` | string | yes | 1 ≤ len ≤ max_text_length |
| `keywords` | array[string] | yes | at least 1 keyword |
| `top_k` | int | no | 1–100, default 10 |
| `boost_factor` | float | no | ≥ 0, default 0.1 |
| `response_fields` | array[string] | no | field projection |

## Stages Detail

### 1. validate_input

```python
def validate_input(query: str, keywords: list[str], top_k: int, boost_factor: float) -> dict:
    if not query or not query.strip():
        raise ValidationError("query must be non-empty")
    if not keywords or len(keywords) == 0:
        raise ValidationError("keywords must be non-empty")
    if top_k < 1 or top_k > 100:
        raise ValidationError("top_k must be between 1 and 100")
    if boost_factor < 0:
        raise ValidationError("boost_factor must be ≥ 0")
    return {
        "query": query.strip(),
        "keywords": [kw.strip().lower() for kw in keywords],
        "top_k": top_k or 10,
        "boost_factor": boost_factor or 0.1,
    }
```

### 2. semantic_search

```python
def semantic_search(query: str, top_k: int, model: EmbeddingModel, vec_db: VectorDB) -> list[SearchResult]:
    query_vec = model.embed_query("query: " + query)
    return vec_db.search(query_vec, top_k * 2)  # over-fetch
```

### 3. keyword_boost

```python
def keyword_boost(results: list[SearchResult], keywords: list[str], boost_factor: float) -> list[SearchResult]:
    for r in results:
        text_content = r.metadata.get("text", "")
        matches = sum(1 for kw in keywords if kw in text_content.lower())
        r.score += matches * boost_factor
    return results
```

### 4. re_sort

```python
def re_sort(results: list[SearchResult]) -> list[SearchResult]:
    return sorted(results, key=lambda r: r.score, reverse=True)
```

### 5. truncate

```python
def truncate(results: list[SearchResult], top_k: int) -> list[SearchResult]:
    return results[:top_k]
```

### 6. response_projection

Identical to `search.semantic` post-processing (see `10-response-projection-format.md`).

## Config Example

```yaml
# pipelines/hybrid-search.yaml
capability: search.hybrid
version: "1.0"
description: "Hybrid search with semantic + keyword boosting"

schema:
  name: HybridSearchSchema
  required: [query, keywords]
  fields:
    query: { type: string, max_length: 5000 }
    keywords: { type: array, items: { type: string }, min_items: 1 }
    top_k: { type: integer, min: 1, max: 100, default: 10 }
    boost_factor: { type: number, min: 0, default: 0.1 }
    response_fields: { type: array, items: { type: string }, optional: true }

pipeline:
  semantic_search:
    over_fetch_factor: 2
    embed:
      prefix: "query: "
      model_field: embedding_model
    search:
      db_type_field: vec_db_type

  keyword_boost:
    match_field: metadata.text
    case_insensitive: true
    configurable:
      - boost_factor

  post_process:
    - stage: response_projection
      config:
        fields_param: response_fields
    - stage: format_response
      config:
        type: json_array
```

## Full Request/Response Example

```json
// Request
{
  "capability": "search.hybrid",
  "params": {
    "query": "neural network architectures",
    "keywords": ["transformer", "attention", "encoder"],
    "top_k": 5,
    "boost_factor": 0.15,
    "response_fields": ["key", "score", "metadata.type"]
  }
}

// Internal intermediate state (before truncation)
// top_k=5, over_fetch=10 results

// Result example (truncated to 5)
[
  {"key": "doc-001", "score": 1.07, "metadata": {"type": "doc"}},
  //   ^ 0.92 semantic + 1 match * 0.15 = 1.07
  {"key": "doc-003", "score": 1.02, "metadata": {"type": "doc"}},
  //   ^ 0.72 semantic + 2 matches * 0.15 = 1.02
  {"key": "doc-002", "score": 0.87, "metadata": {"type": "doc"}},
  //   ^ 0.87 semantic + 0 matches = 0.87
  {"key": "note-001", "score": 0.75, "metadata": {"type": "note"}},
  {"key": "note-002", "score": 0.60, "metadata": {"type": "note"}}
]
```

## Score Calculation

```
final_score = semantic_score + (keyword_match_count * boost_factor)
```

| Variable | Default | Source |
|----------|---------|--------|
| semantic_score | — | vec_db.search cosine similarity |
| keyword_match_count | — | count of keywords found in metadata.text |
| boost_factor | 0.1 | config (per-request overridable) |

## Configurable Parameters

These can be set per-pipeline in YAML or overridden per-request:

| Parameter | Default | Scope |
|-----------|---------|-------|
| `boost_factor` | 0.1 | pipeline / request |
| `over_fetch_factor` | 2 | pipeline only |

## Error Cases

| Condition | Error | Code |
|-----------|-------|------|
| Empty keywords array | ValidationError | INPUT_INVALID |
| boost_factor negative | ValidationError | PARAM_INVALID |
| Semantic search fails | VectorDBError | SEARCH_FAILURE |

## Implementation Note

The current `EmbeddingService.hybrid_search()` already implements this logic at `embedding_service/service.py:81-90`. The pipeline wraps it as a composable stage sequence, adding response projection and config-driven parameters.
