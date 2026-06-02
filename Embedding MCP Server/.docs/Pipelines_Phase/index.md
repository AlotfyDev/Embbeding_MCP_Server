# Pipelines Phase — فهرس المسارات

## Overview

This phase defines **capability-oriented pipelines** that wrap `EmbeddingService` into composable, configurable execution flows. Each pipeline maps a capability name → ordered stages → response format.

---

## Pipeline Index

| # | Capability | وصف | Stages | Phase 0 Dependencies |
|---|-----------|------|--------|---------------------|
| 01 | `document.ingest` | تضمين وتخزين وثيقة مفردة مع metadata | validate → pre_process → embed → store → post_process | EmbeddingService.embed_document, VectorDB.store, Settings.max_text_length |
| 02 | `document.ingest.batch` | تضمين وتخزين مجموعة وثائق دفعة واحدة | validate_all → pre_process → embed_batch → store_batch → post_process | EmbeddingService.embed_batch_documents, VectorDB.store_batch, Settings.max_batch_size |
| 03 | `search.semantic` | بحث دلالي باستخدام query embedding | validate → embed_query → search → score_norm → response_projection | EmbeddingService.search_similar, VectorDB.search, Settings.embedding_model |
| 04 | `search.hybrid` | بحث هجين (semantic + keyword boosting) | validate → semantic_search → keyword_boost → re_sort → truncate → projection | EmbeddingService.hybrid_search, SearchResult.metadata |
| 05 | `document.compare` | مقارنة وثيقتين عبر cosine similarity | validate → embed_a → embed_b → compute_similarity → format | EmbeddingService.compare_docs, EmbeddingModel.embed |
| 06 | `document.delete` | حذف وثيقة من vector DB | validate_key → vec_db.delete → format | VectorDB.delete |
| 06 | `document.count` | عد الوثائق المخزنة | vec_db.count → format | VectorDB.count |
| 06 | `system.health` | فحص صحة النظام | check_model → check_vec_db → format | EmbeddingService.health |

---

## Layers Involved

```
request (capability + params)
    │
    ▼
┌─────────────────────────────┐
│ CapabilityRouter            │   ← 07-capability-router.md
│  • route(capability, params)│
└──────────┬──────────────────┘
           │
           ▼
┌─────────────────────────────┐
│ SchemaEnforcementLayer      │   ← 08-schema-enforcement-layer.md
│  • validate input vs schema │
└──────────┬──────────────────┘
           │
           ▼
┌─────────────────────────────┐
│ Pipeline (ordered stages)   │   ← 01-06 pipeline specs
│  pre_process → embed → ... │
└──────────┬──────────────────┘
           │
           ▼
┌─────────────────────────────┐
│ ResponseProjection          │   ← 10-response-projection-format.md
│  • filter response fields  │
└─────────────────────────────┘
```

## Config-Based Definition

Every pipeline is defined in YAML (see `09-pipeline-config-format.md`). The YAML declares:
- schema (input validation rules)
- pipeline stages (ordered transformations)
- embed/store configuration (prefix, model field, batch size)
- post-processing (response format)

## File Map

| File | Topic |
|------|-------|
| `01-pipeline-document-ingestion.md` | Single document ingest |
| `02-pipeline-batch-ingestion.md` | Batch document ingest |
| `03-pipeline-semantic-search.md` | Semantic search |
| `04-pipeline-hybrid-search.md` | Hybrid search (semantic + keyword) |
| `05-pipeline-document-comparison.md` | Document comparison |
| `06-pipeline-document-management.md` | Delete, count, health |
| `07-capability-router.md` | Request routing by capability |
| `08-schema-enforcement-layer.md` | Input/output schema enforcement |
| `09-pipeline-config-format.md` | YAML format for pipeline definitions |
| `10-response-projection-format.md` | Response field projection |
