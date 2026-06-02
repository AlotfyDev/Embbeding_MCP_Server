# Capability Router — توجيه الطلبات حسب capability

## Concept

The CapabilityRouter is the **entry point** for all pipeline execution. It maps a capability string (e.g. `"document.ingest"`) to a registered pipeline, validates the input schema, executes the pipeline, and returns the projected response.

## Architecture

```
Incoming Request
    │
    ▼
┌─────────────────────────────────────────────┐
│             CapabilityRouter                 │
│                                              │
│  1. resolve pipeline by capability string    │
│  2. middleware: schema validation            │
│  3. pipeline.execute(params)                 │
│  4. error handling (uniform)                 │
│  5. return result                            │
└─────────────────────────────────────────────┘
    │
    ▼
  Pipeline (ordered stages)
```

## Design (Prototype)

```python
# concept — design only, not implementation
from typing import Any, Protocol

class CapabilityPipeline(Protocol):
    capability: str
    version: str

    def execute(self, **params) -> Any:
        ...


class CapabilityRouter:
    """Routes requests to the appropriate pipeline by capability name."""

    def __init__(self):
        self._pipelines: dict[str, CapabilityPipeline] = {}
        self._middleware = []

    def register(self, pipeline: CapabilityPipeline) -> None:
        """Register a pipeline by its capability name."""
        if pipeline.capability in self._pipelines:
            raise ValueError(f"Pipeline '{pipeline.capability}' already registered")
        self._pipelines[pipeline.capability] = pipeline

    def unregister(self, capability: str) -> None:
        """Remove a registered pipeline."""
        self._pipelines.pop(capability, None)

    def route(self, capability: str, **params) -> Any:
        """Execute a pipeline by capability name.

        Args:
            capability: e.g. "document.ingest", "search.semantic"
            **params: pipeline-specific input parameters

        Returns:
            Pipeline output (dict or list)

        Raises:
            UnknownCapabilityError: if capability not registered
        """
        if capability not in self._pipelines:
            raise UnknownCapabilityError(
                f"Unknown capability: '{capability}'. "
                f"Available: {list(self._pipelines.keys())}"
            )

        pipeline = self._pipelines[capability]

        # Apply middleware chain
        ctx = {"capability": capability, "params": params}
        for mw in self._middleware:
            ctx = mw.process(ctx)

        # Execute pipeline
        result = pipeline.execute(**ctx["params"])

        return result

    @property
    def capabilities(self) -> list[str]:
        return list(self._pipelines.keys())
```

## Middleware Chain

Middleware wraps every route call. Built-in middleware:

| Middleware | Order | Purpose |
|-----------|-------|---------|
| `SchemaValidationMiddleware` | 1st | Validate params against registered schema |
| `ErrorHandlingMiddleware` | 2nd | Catch and normalize exceptions |
| `LoggingMiddleware` | 3rd | Log request/response (optional) |

```python
# concept
class SchemaValidationMiddleware:
    def __init__(self, schema_registry: SchemaRegistry):
        self._registry = schema_registry

    def process(self, ctx: dict) -> dict:
        schema = self._registry.get(ctx["capability"])
        if schema:
            ctx["params"] = schema.validate(ctx["params"])
        return ctx


class ErrorHandlingMiddleware:
    def process(self, ctx: dict) -> dict:
        try:
            return ctx
        except ValidationError as e:
            raise PipelineError(code="VALIDATION_ERROR", message=str(e), http_status=400)
        except SchemaValidationError as e:
            raise PipelineError(code="SCHEMA_VIOLATION", message=str(e), http_status=422)
        except VectorDBError as e:
            raise PipelineError(code="DB_ERROR", message=str(e), http_status=500)
        except Exception as e:
            raise PipelineError(code="INTERNAL_ERROR", message=str(e), http_status=500)
```

## Error Handling (Uniform)

All errors flow through a single error format:

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "text must not be empty",
    "capability": "document.ingest",
    "timestamp": "2026-06-02T10:30:00Z"
  }
}
```

### Error Codes

| Code | HTTP-like Status | Source |
|------|-----------------|--------|
| `UNKNOWN_CAPABILITY` | 404 | Router |
| `VALIDATION_ERROR` | 400 | Pipeline validation stage |
| `SCHEMA_VIOLATION` | 422 | Schema enforcement layer |
| `MODEL_FAILURE` | 500 | Embedding model |
| `DB_ERROR` | 500 | VectorDB |
| `INTERNAL_ERROR` | 500 | Unhandled exception |

## Registration API

```python
# concept — how pipelines get registered
router = CapabilityRouter()

# Method 1: Direct registration
router.register(DocumentIngestPipeline())

# Method 2: Load from YAML config
router.load_from_config("pipelines/document-ingest.yaml")

# Method 3: Auto-discover directory
router.discover("pipelines/")  # scan *.yaml files
```

## Pipeline Interface

```python
# concept — what every pipeline must implement
class BasePipeline:
    """Abstract base for all pipelines."""

    capability: str
    version: str
    description: str = ""

    def execute(self, **params) -> Any:
        """Execute the full pipeline. Override in subclass."""
        raise NotImplementedError
```

## Consumer Identity (Optional)

For multi-tenant scenarios, the router can accept a `consumer_id`:

```python
def route(self, capability: str, consumer_id: str | None = None, **params) -> Any:
    ctx = {"capability": capability, "consumer_id": consumer_id, "params": params}
    # Consumer-aware middleware can enforce:
    #   - rate limits per consumer
    #   - schema overrides per consumer
    #   - audit logging per consumer
    return self._execute_chain(ctx)
```

## Full Request Routing Flow

```json
// Incoming request
{
  "capability": "search.semantic",
  "params": {
    "query": "transformer models",
    "top_k": 5
  }
}

// Router internal flow
1. Router.route("search.semantic", query="transformer models", top_k=5)
2. Lookup pipeline: search.semantic → SemanticSearchPipeline
3. Middleware: SchemaValidation → validates query, top_k
4. Pipeline.execute(query="transformer models", top_k=5)
5. → validate_input → embed_query → search → post_process
6. Return [{"key": "doc-001", "score": 0.92, ...}, ...]
```

## Error Handling Example

```json
// Request with invalid capability
{"capability": "search.unknown", "params": {}}

// Response
{
  "error": {
    "code": "UNKNOWN_CAPABILITY",
    "message": "Unknown capability: 'search.unknown'. Available: ['document.ingest', 'document.ingest.batch', 'search.semantic', 'search.hybrid', 'document.compare', 'document.delete', 'document.count', 'system.health']"
  }
}
```

## Relationship to MCP Handlers

The current MCP handlers (`handlers.py`) are thin wrappers around `EmbeddingService`. In the Pipelines Phase, they can be refactored to delegate to the router:

```python
# Current (thin handler)
def handle_search(service, query, top_k=10, filters="{}"):
    results = service.search_similar(query, top_k, json.loads(filters))
    return json.dumps([r.to_dict() for r in results])

# Future (router delegation)
def handle_search(router, query, top_k=10, filters="{}"):
    result = router.route("search.semantic",
        query=query,
        top_k=top_k,
        filters=json.loads(filters),
    )
    return json.dumps(result)
```

This preserves the thin-handler pattern while gaining pipeline composability.
