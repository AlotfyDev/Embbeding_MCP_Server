# Wave 7: Testing and Verification

## Objective
Ensure all pipelines work correctly through comprehensive testing.

## Test Categories

### Unit Tests

#### Schema Layer
- `test_schema_field_def.py`: FieldType, FieldDef creation
- `test_schema_validation.py`: validate() for each type
- `test_nested_fields.py`: "metadata.type" resolution
- `test_schema_errors.py`: SchemaValidationError raised correctly

#### Pipeline Stages
- `test_stage_validation.py`: Strip, normalize, validate
- `test_stage_embed.py`: Embed with/without prefixes
- `test_stage_store.py`: Store single and batch
- `test_stage_search.py`: Search with filters
- `test_stage_projection.py`: Field filtering, nested paths

#### Router
- `test_router_registration.py`: register/unregister
- `test_router_routing.py`: route() with valid/invalid capabilities
- `test_router_middleware.py`: Middleware chain ordering

### Integration Tests

#### Pipeline End-to-End
- `test_document_ingest_pipeline.py`: Full ingest flow
- `test_batch_ingest_pipeline.py`: Batch processing
- `test_semantic_search_pipeline.py`: Search + projection
- `test_hybrid_search_pipeline.py`: Semantic + keyword boost
- `test_doc_compare_pipeline.py`: Similarity calculation
- `test_doc_delete_pipeline.py`: Delete operation
- `test_doc_count_pipeline.py`: Count operation
- `test_system_health_pipeline.py`: Health check

### MCP Integration Tests
- `test_mcp_via_router.py`: All 7 tools via router
- `test_mcp_error_format.py`: McpError format preserved
- `test_mcp_projection.py`: response_fields in MCP context

## Test Data

### Sample Documents
```python
TEST_DOCS = [
    {"key": "doc-001", "text": "Attention mechanism revolutionized NLP.", "metadata": {"type": "doc", "source": "arxiv"}},
    {"key": "doc-002", "text": "Transformer models use self-attention mechanisms.", "metadata": {"type": "doc"}},
    {"key": "note-001", "text": "Review: read the BERT paper.", "metadata": {"type": "note"}},
]
```

## Performance Benchmarks

### Target Metrics (from PerformanceGuidelines.md)
- Logging Latency: < 1μs for single operation
- Batch Throughput: > 100K items/second
- Cache Operations: < 100μs
- Cross-Language Overhead: < 15μs per call

### Benchmark Tests
- `test_stage_performance.py`: Each stage < 100μs
- `test_pipeline_performance.py`: Full pipeline timing
- `test_projection_performance.py`: < 1ms for response filtering

## Verification Checklist

### Schema Enforcement
- [ ] All required fields validated
- [ ] Type constraints enforced
- [ ] Enum values validated
- [ ] Regex patterns matched
- [ ] Default values applied
- [ ] Nested path support works

### Router Integration
- [ ] All 8 capabilities registered
- [ ] Unknown capability returns proper error
- [ ] Middleware executes in order
- [ ] Errors normalized to PipelineError format

### MCP Compatibility
- [ ] Existing tool signatures preserved
- [ ] Error codes match Phase 0 (-32602, -32603)
- [ ] Response format unchanged
- [ ] response_fields parameter works

### Performance
- [ ] Each stage < 100μs
- [ ] Pipeline overhead < 5% vs direct service call
- [ ] Projection < 1ms
- [ ] Memory overhead < 10%

## Test Execution

### Unit Tests
```bash
pytest tests/unit/ -v --tb=short
```

### Integration Tests
```bash
pytest tests/integration/ -v --tb=short
```

### Coverage Target
- Schema layer: 100%
- Pipeline stages: 100%
- Router: 100%
- Integration: 90%

### CI Integration
```yaml
- name: Test Pipelines
  run: |
    pytest tests/unit/test_schema*.py tests/unit/test_stages*.py
    pytest tests/integration/test_pipeline*.py
    pytest tests/integration/test_mcp_via_router*.py
```