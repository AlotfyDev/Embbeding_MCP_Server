# Wave 4: Pipeline Implementations

## Objective
Implement the 8 capability pipelines from the specification.

## Pipelines to Implement

### 1. `document.ingest` Pipeline
**File:** `embedding_mcp/pipelines/document_ingest.py`

**Stages:**
```
validate_input → pre_process → embed → store → post_process
```

**Params:** key, text, metadata?
**Output:** {status, key, dim}

### 2. `document.ingest.batch` Pipeline
**File:** `embedding_mcp/pipelines/batch_ingest.py`

**Stages:**
```
validate_all → pre_process → embed_batch → store_batch → post_process
```

**Params:** items: [{key, text, metadata?}, ...]
**Output:** {status, count}

**Key Logic:**
- Validates all items before processing
- Chunks by max_batch_size
- All-or-nothing transaction

### 3. `search.semantic` Pipeline
**File:** `embedding_mcp/pipelines/semantic_search.py`

**Stages:**
```
validate_input → embed_query → search → score_norm → response_projection
```

**Params:** query, top_k?, filters?, response_fields?
**Output:** [{key, score, metadata}]

### 4. `search.hybrid` Pipeline
**File:** `embedding_mcp/pipelines/hybrid_search.py`

**Stages:**
```
validate_input → semantic_search → keyword_boost → re_sort → truncate → projection
```

**Params:** query, keywords, top_k?, boost_factor?, response_fields?
**Output:** [{key, score, metadata}]

**Key Logic:**
- Over-fetches (top_k * 2)
- Boosts score: +matches * boost_factor
- Re-sorts and truncates

### 5. `document.compare` Pipeline
**File:** `embedding_mcp/pipelines/doc_compare.py`

**Stages:**
```
validate_input → embed_a → embed_b → compute_similarity → format
```

**Params:** key_a, key_b
**Output:** {similarity, key_a, key_b}

**Future Enhancement:** Add fetch_vectors stage when VectorDB.get_vector_by_key() exists

### 6. `document.delete` Pipeline
**File:** `embedding_mcp/pipelines/doc_delete.py`

**Stages:**
```
validate_key → vec_db.delete → format_response
```

**Params:** key
**Output:** {status, key}

### 7. `document.count` Pipeline
**File:** `embedding_mcp/pipelines/doc_count.py`

**Stages:**
```
vec_db.count → format_response
```

**Params:** (none)
**Output:** {count}

### 8. `system.health` Pipeline
**File:** `embedding_mcp/pipelines/system_health.py`

**Stages:**
```
check_model → check_vec_db → aggregate → format_response
```

**Params:** (none)
**Output:** {status, model, vector_db}

**Key Logic:**
- Non-fatal errors (reports in response)
- Probes model with test embed
- Reports vec_db count

## Implementation Pattern

All pipelines follow:
```python
class DocumentIngestPipeline:
    capability = "document.ingest"
    version = "1.0"
    
    def __init__(self, model: EmbeddingModel, vec_db: VectorDB, schema: DocumentSchema):
        self._model = model
        self._vec_db = vec_db
        self._schema = schema
    
    def execute(self, **params) -> dict:
        # Execute stages in order
        data = stages.validate_input(params, self._schema)
        data = stages.pre_process(data)
        data = stages.embed(data, self._model)
        data = stages.store(data, self._vec_db)
        return stages.post_process(data)
```

## Verification
- Integration tests for each pipeline
- End-to-end tests with router
- Response format tests (match spec examples)