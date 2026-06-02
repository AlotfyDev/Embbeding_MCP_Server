# Pipelines Phase Implementation Plan - Index

## Overview

This document series details the implementation plan for the Pipelines Phase, which adds capability-oriented pipelines to the Embedding MCP Server.

## Waves Summary

| File | Wave | Duration | Description |
|------|------|----------|-------------|
| `01-architecture-overview.md` | - | - | Current state analysis and target architecture |
| `02-wave1-schema-foundation.md` | 1 | 1-2 days | Schema Enforcement Layer (FieldDef, DocumentSchema, SchemaRegistry) |
| `03-wave2-pipeline-core.md` | 2 | 2-3 days | Pipeline base classes and composable stage functions |
| `04-wave3-capability-router.md` | 3 | 1-2 days | CapabilityRouter and PipelineRegistry |
| `05-wave4-pipeline-implementations.md` | 4 | 2-3 days | 8 capability pipelines (ingest, search, compare, delete, count, health) |
| `06-wave5-configuration-yaml.md` | 5 | 1 day | YAML parsing and config-driven pipeline instantiation |
| `07-wave6-mcp-integration.md` | 6 | 1 day | MCP handler refactoring to use router |
| `08-wave7-testing-verification.md` | 7 | 1-2 days | Comprehensive testing for all components |
| `09-wave8-finalization.md` | 8 | 1 day | Documentation and production readiness |

## Target Capabilities

| # | Capability | Phases | Status |
|---|------------|--------|--------|
| 01 | `document.ingest` | validate → pre_process → embed → store → post_process | Wave 4 |
| 02 | `document.ingest.batch` | validate_all → pre_process → embed_batch → store_batch → post_process | Wave 4 |
| 03 | `search.semantic` | validate → embed_query → search → score_norm → projection | Wave 4 |
| 04 | `search.hybrid` | validate → semantic_search → keyword_boost → re_sort → truncate → projection | Wave 4 |
| 05 | `document.compare` | validate → embed_a → embed_b → compute_similarity → format | Wave 4 |
| 06 | `document.delete` | validate_key → vec_db.delete → format | Wave 4 |
| 06 | `document.count` | vec_db.count → format | Wave 4 |
| 06 | `system.health` | check_model → check_vec_db → aggregate | Wave 4 |

## Key Design Principles

1. **No Hardcoded Values** - Everything from config (Settings)
2. **Thin Handlers** - MCP handlers delegate to router, no business logic
3. **Composable Stages** - Reusable functions across pipelines
4. **Backward Compatible** - Existing MCP tools work identically
5. **Schema-Driven** - Validation rules in YAML, not code

## File Structure After Implementation

```
embedding_mcp/
├── schema/
│   ├── __init__.py
│   ├── field_def.py
│   ├── registry.py
│   └── errors.py
├── pipelines/
│   ├── __init__.py
│   ├── base.py
│   ├── router.py
│   ├── registry.py
│   ├── config_loader.py
│   ├── document_ingest.py
│   ├── batch_ingest.py
│   ├── semantic_search.py
│   ├── hybrid_search.py
│   ├── doc_compare.py
│   ├── doc_delete.py
│   ├── doc_count.py
│   ├── system_health.py
│   └── stages/
│       ├── __init__.py
│       ├── validation.py
│       ├── embed.py
│       ├── store.py
│       ├── search.py
│       └── projection.py
├── mcp_local/
│   └── handlers.py (updated)
└── mcp_network/
    └── handlers.py (unchanged, imports from mcp_local)
```