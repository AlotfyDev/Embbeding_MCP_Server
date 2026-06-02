# Wave 6: MCP Integration and Handler Refactoring

## Objective
Integrate pipelines with existing MCP server, preserving backward compatibility.

## Files to Modify

### 1. `embedding_mcp/mcp_local/local_server.py`
```python
# Current: Direct service calls
# Future: Router calls

# Change from:
@app.tool()
async def embed_text(text: str) -> str:
    return handle_embed(service, text)

# To:
@app.tool()
async def embed_text(text: str) -> str:
    return handle_via_router(router, "document.ingest", text=text, key=f"inline-{uuid()}")
```

### 2. `embedding_mcp/mcp_local/handlers.py`
```python
# Add router-based handlers:
# - handle_via_router(router, capability, **params) -> str
# - route_and_project(router, capability, response_fields, **params) -> str
```

## Integration Strategy

### Phase 1: Dual Mode
- MCP handlers delegate to both service AND router
- Feature flag to choose mode
- Verify identical outputs

### Phase 2: Router Primary
- Handlers call router.route()
- Service becomes stage implementation detail
- All business logic in stages

### Phase 3: Cleanup
- Remove direct service calls from handlers
- Thin wrappers preserved

## Handler Refactoring

### Before (Current)
```python
def handle_search(service, query: str, top_k: int = 10, filters: str = "{}") -> str:
    parsed_filters = json.loads(filters) if filters else {}
    results = service.search_similar(query, top_k, parsed_filters)
    return json.dumps([r.to_dict() for r in results], ensure_ascii=False)
```

### After (Router-Based)
```python
def handle_search(router, query: str, top_k: int = 10, filters: str = "{}", response_fields: str = "[]") -> str:
    parsed_filters = json.loads(filters) if filters else {}
    parsed_fields = json.loads(response_fields) if response_fields else None
    result = router.route(
        "search.semantic",
        query=query,
        top_k=top_k,
        filters=parsed_filters,
        response_fields=parsed_fields,
    )
    return json.dumps(result, ensure_ascii=False)
```

## Network Server Update

### `embedding_mcp/mcp_network/network_server.py`
- No changes needed (imports handlers from mcp_local)
- Same router-based approach
- SSE transport preserved

## Response Projection Integration

For pipelines that support `response_fields`:
- `search.semantic`: Filter key, score, nested metadata
- `search.hybrid`: Same as semantic
- `document.ingest`: Filter status, key, dim
- `document.compare`: Filter similarity, key_a, key_b

## Verification
- Integration tests: MCP → Router → Pipeline
- Backward compatibility tests (same request/response format)
- Error format tests (McpError codes preserved)
- Projection tests (field filtering works in MCP context)