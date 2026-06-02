# Response Projection Format — تشكيل المخرجات حسب الطلب

## Concept

Response projection allows clients to specify which fields they want in the response, reducing payload size and hiding irrelevant data. Inspired by GraphQL field selection but implemented as a simple array of field paths.

## How It Works

The client passes `response_fields` in the request params. The pipeline filters the response dict to include only the specified fields.

## Projection Rules

| Rule | Behavior |
|------|----------|
| No `response_fields` | Return full response (all fields) |
| Empty array `[]` | Return empty dict `{}` |
| `["key", "score"]` | Return only `key` and `score` |
| `["metadata.type"]` | Return nested `metadata` with only `type` |
| `["key", "metadata.type", "metadata.source"]` | Return `key` + filtered `metadata` |
| Unknown field | Silently omitted (no error) |

## Examples

### Example 1: Without projection

```json
// Request — no response_fields
{"capability": "search.semantic", "params": {"query": "transformers"}}

// Full response
{
  "key": "doc-001",
  "score": 0.95,
  "metadata": {
    "type": "doc",
    "source": "arxiv",
    "title": "Attention Is All You Need",
    "year": 2017,
    "authors": ["Vaswani et al."]
  }
}
```

### Example 2: Simple field selection

```json
// Request
{
  "capability": "search.semantic",
  "params": {
    "query": "transformers",
    "response_fields": ["key", "score"]
  }
}

// Response
{"key": "doc-001", "score": 0.95}
```

### Example 3: Nested field selection

```json
// Request
{
  "capability": "search.semantic",
  "params": {
    "query": "transformers",
    "response_fields": ["key", "metadata.title", "metadata.year"]
  }
}

// Response
{
  "key": "doc-001",
  "metadata": {
    "title": "Attention Is All You Need",
    "year": 2017
  }
}
```

### Example 4: Array of results

```json
// Request
{
  "capability": "search.semantic",
  "params": {
    "query": "transformers",
    "top_k": 2,
    "response_fields": ["key", "score"]
  }
}

// Response
[
  {"key": "doc-001", "score": 0.95},
  {"key": "doc-002", "score": 0.87}
]
```

### Example 5: Single-document response (ingest)

```json
// Request
{
  "capability": "document.ingest",
  "params": {
    "key": "doc-001",
    "text": "Attention mechanism..."
  }
}

// Full response (no projection)
{"status": "stored", "key": "doc-001", "dim": 384}

// With projection
{"capability": "document.ingest", "params": {"key": "doc-001", "text": "...", "response_fields": ["status"]}}

// Response
{"status": "stored"}
```

## Implementation

```python
# concept
def project_response(data: dict | list, fields: list[str] | None) -> dict | list:
    """Filter response data to only include specified fields.

    Args:
        data: Response dict or list of dicts
        fields: Dot-notation field paths, e.g. ["key", "metadata.type"]

    Returns:
        Filtered response (same structure as input)
    """
    if fields is None or len(fields) == 0:
        return data

    if isinstance(data, list):
        return [project_response(item, fields) for item in data]

    if not isinstance(data, dict):
        return data

    result = {}
    for field in fields:
        parts = field.split(".")
        current = data
        valid = True

        for part in parts:
            if isinstance(current, dict) and part in current:
                current = current[part]
            else:
                valid = False
                break

        if valid:
            # Build nested structure
            target = result
            for i, part in enumerate(parts):
                if i == len(parts) - 1:
                    target[part] = current
                else:
                    if part not in target:
                        target[part] = {}
                    target = target[part]

    return result
```

## Supported Response Types

| Pipeline | Response Structure | Projection Support |
|----------|-------------------|--------------------|
| `document.ingest` | `{status, key, dim}` | yes |
| `document.ingest.batch` | `{status, count}` | yes |
| `search.semantic` | `[{key, score, metadata}]` | yes (per item) |
| `search.hybrid` | `[{key, score, metadata}]` | yes (per item) |
| `document.compare` | `{similarity, key_a, key_b}` | yes |
| `document.delete` | `{status, key}` | yes |
| `document.count` | `{count}` | yes |
| `system.health` | `{status, model, vector_db}` | yes |

## Config Integration

In pipeline YAML:

```yaml
pipeline:
  post_process:
    - stage: response_projection
      config:
        fields_param: response_fields   # read fields from request param
        enabled: true                    # can disable per pipeline
```

## Field Path Syntax

| Syntax | Meaning | Example |
|--------|---------|---------|
| `key` | Top-level field | `{"key": "doc-001"}` |
| `metadata.type` | Nested field | `{"metadata": {"type": "doc"}}` |
| `metadata.authors` | Array field (returns full array) | `{"metadata": {"authors": ["Vaswani et al."]}}` |
| `metadata.authors.0` | Array index (optional extension) | `{"metadata": {"authors": "Vaswani et al."}}` |

## Performance

Projection runs in **post_process** after the pipeline executes. It transforms the output dict in memory:
- **O(n)** where n = response dict size
- **Negligible** overhead for typical responses (< 1ms)
- Cuts network payload significantly (especially for large metadata)

## Client Usage Convention

```python
# Python client example
client.search_similar(
    query="transformer models",
    top_k=5,
    response_fields=["key", "score", "metadata.title"]
)
# → returns only requested fields
```

## Comparison with GraphQL

| Concern | Response Projection | GraphQL |
|---------|-------------------|---------|
| Complexity | Simple array of field paths | Query language + resolver |
| Nesting | Dot notation | Nested query blocks |
| Aliasing | Not supported | Supported |
| Computed fields | Not supported | Supported via resolvers |
| Overhead | None (post-process transform) | Parsing + validation |
| When to use | Simple field masking | Complex data graphs |

Response projection is intentionally simpler — it's a post-processing filter, not a query language.
