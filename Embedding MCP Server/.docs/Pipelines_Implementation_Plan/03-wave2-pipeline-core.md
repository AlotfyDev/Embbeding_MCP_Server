# Wave 2: Pipeline Core - Base Classes and Stage System

## Objective
Create the composable pipeline infrastructure and stage functions.

## Files to Create

### 1. `embedding_mcp/pipelines/base.py`
```python
# CapabilityPipeline protocol
# - capability: str
# - version: str
# - description: str
# - execute(**params) -> Any

# Stage type definition
# - Callable[[dict], dict] for transform stages
```

### 2. `embedding_mcp/pipelines/stages/__init__.py`
```python
# Stage function exports
```

### 3. `embedding_mcp/pipelines/stages/validation.py`
```python
# Stage functions:
# - validate_input(data: dict, schema: DocumentSchema) -> dict
# - strip_whitespace(data: dict) -> dict
# - normalize_whitespace(text: str) -> str
# - validate_text_length(text: str, max_length: int) -> str
```

### 4. `embedding_mcp/pipelines/stages/embed.py`
```python
# Stage functions:
# - embed_text(text: str, model: EmbeddingModel) -> dict
# - embed_batch(items: list[dict], model: EmbeddingModel, batch_size: int) -> dict
# - embed_query(query: str, model: EmbeddingModel) -> dict
```

### 5. `embedding_mcp/pipelines/stages/store.py`
```python
# Stage functions:
# - store_vector(key: str, vector: list[float], metadata: dict, vec_db: VectorDB) -> dict
# - store_batch_vectors(items: list[dict], vec_db: VectorDB) -> dict
```

### 6. `embedding_mcp/pipelines/stages/search.py`
```python
# Stage functions:
# - search_similar(query: str, top_k: int, vec_db: VectorDB, model: EmbeddingModel) -> list[SearchResult]
```

### 7. `embedding_mcp/pipelines/stages/projection.py`
```python
# Stage functions:
# - response_projection(data: Any, fields: list[str] | None) -> Any
# - normalize_scores(results: list[SearchResult]) -> list[SearchResult]
# - format_response(data: Any, fields: list[str]) -> dict
```

## Implementation Steps

1. Define CapabilityPipeline Protocol with execute() signature
2. Create validation stages (strip, normalize, validate)
3. Create embedding stages wrapping model methods
4. Create store/search stages wrapping vec_db methods
5. Add response projection logic (dot notation field filtering)
6. Add format_response helper for consistent output

## Dependencies
- Wave 1 (Schema system) completed
- Existing EmbeddingModel and VectorDB

## Verification
- Unit tests for each stage function
- Stage composition tests (pipe stages together)
- Projection tests (nested field filtering)