# Wave 3: Capability Router and Registration

## Objective
Build the central routing system that maps capability strings to pipeline instances.

## Files to Create

### 1. `embedding_mcp/pipelines/router.py`
```python
# CapabilityRouter class
# - register(pipeline: CapabilityPipeline) -> None
# - unregister(capability: str) -> None
# - route(capability: str, **params) -> Any
# - capabilities -> list[str]

# Middleware support:
# - add_middleware(middleware) -> None
# - execute_chain(ctx: dict) -> Any
```

### 2. `embedding_mcp/pipelines/registry.py`
```python
# PipelineRegistry class
# - register(capability: str, pipeline: CapabilityPipeline)
# - get(capability: str) -> CapabilityPipeline | None
# - discover(directory: str) -> None (scan *.yaml)
```

### 3. `embedding_mcp/pipelines/middleware/validation.py`
```python
# SchemaValidationMiddleware
# - process(ctx: dict) -> dict
# - Validates params against registered schema
```

### 4. `embedding_mcp/pipelines/middleware/error_handling.py`
```python
# ErrorHandlingMiddleware
# - process(ctx: dict) -> dict
# - Catches exceptions, raises PipelineError
```

## Implementation Steps

1. Create CapabilityRouter with _pipelines dict and register/unregister methods
2. Implement route() with UnknownCapabilityError handling
3. Add middleware chain support
4. Create SchemaValidationMiddleware using SchemaRegistry
5. Create ErrorHandlingMiddleware for uniform error handling
6. Add PipelineRegistry for pipeline lifecycle management

## Error Classes

| Code | HTTP-like Status | Source |
|------|-----------------|--------|
| UNKNOWN_CAPABILITY | 404 | Router |
| VALIDATION_ERROR | 400 | Pipeline validation stage |
| SCHEMA_VIOLATION | 422 | Schema enforcement layer |
| MODEL_FAILURE | 500 | Embedding model |
| DB_ERROR | 500 | VectorDB |
| INTERNAL_ERROR | 500 | Unhandled exception |

## Verification
- Unit tests for router registration
- Unit tests for route() with valid/invalid capabilities
- Unit tests for middleware chain ordering
- Error handling tests (uniform error format)