# Implementation Plan: Pipelines Phase Architecture

## Current State Analysis (Phase 0)

### Existing Components
```
embedding_mcp/
├── embedding_model/
│   ├── base.py              # EmbeddingModel ABC (complete)
│   ├── e5_model.py          # E5SmallONNX, E5BaseLarge (complete)
│   └── factory.py           # create_embedding_model (to verify)
├── vector_db/
│   ├── base.py              # VectorDB ABC, SearchResult (complete)
│   ├── faiss_adapter.py     # FAISSAdapter (complete)
│   └── factory.py           # create_vector_db (to verify)
├── embedding_service/
│   └── service.py           # EmbeddingService (partial - needs count_documents method)
└── mcp_local/
    ├── local_server.py      # FastMCP tool registration (complete)
    └── handlers.py          # Thin handlers (complete)
```

### Architecture Gap
- No schema validation layer
- No capability router
- No pipeline stage system
- No response projection
- MCP handlers call service directly (no indirection)

## Target Architecture (Pipelines Phase)

```
pipelines/
├── __init__.py
├── router.py                # CapabilityRouter class
├── base.py                  # CapabilityPipeline protocol
├── config_loader.py         # YAML → pipeline instantiation
├── registry.py              # PipelineRegistry
├── stages/
│   ├── __init__.py
│   ├── validation.py        # validate_input stage functions
│   ├── embed.py             # embed, embed_batch, embed_query stages
│   ├── store.py             # store, store_batch stages
│   ├── search.py            # search stages
│   ├── comparison.py        # compare, similarity stages
│   └── projection.py        # response_projection stage
└── schemas/
    ├── registry.py          # SchemaRegistry
    ├── field_def.py         # FieldDef, FieldType
    └── errors.py            # SchemaValidationError
```

## Layer Mapping

| Layer | Phase 0 | Pipelines Phase |
|-------|---------|-----------------|
| 1 | N/A | Toolbox (pure stage functions) |
| 2 | Settings | Schema/POD definitions |
| 3 | Service | Pipeline stages + Orchestration |
| 4 | MCP handlers | CapabilityRouter + Thin handlers |

## Data Flow

```
Request (capability + params)
    │
    ▼
┌─────────────────────────────┐
│ SchemaEnforcementLayer      │  ← Validates input against registered schema
└──────────┬──────────────────┘
           │
           ▼
┌─────────────────────────────┐
│ CapabilityRouter            │  ← Maps capability → pipeline
└──────────┬──────────────────┘
           │
           ▼
┌─────────────────────────────┐
│ Pipeline (ordered stages)   │  ← Executes stage functions
│   • validate_input          │
│   • pre_process             │
│   • embed                   │
│   • store/search            │
│   • post_process            │
└──────────┬──────────────────┘
           │
           ▼
┌─────────────────────────────┐
│ ResponseProjection          │  ← Filters response fields
└─────────────────────────────┘
```