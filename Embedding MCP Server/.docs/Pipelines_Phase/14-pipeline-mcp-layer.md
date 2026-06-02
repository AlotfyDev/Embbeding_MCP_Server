# 14. MCP Layer — طبقة MCP تفصيلية لكل Pipeline مع Thin Handlers

## Principle: Thin Handler Architecture

الـ MCP tool handler لا يحتوي أي business logic. كل handler هو مجرد **موجّه** (3 أسطر كحد أقصى) يقرأ parameters من الطلب، يبني `StageContext`، ويستدعي `CapabilityRouter.route()`. الـ business logic كله داخل pipeline stages.

```
MCP Tool (request from client)
    │
    ▼
Handler (3 أسطر كحد أقصى)
    │  - يقرأ capability (أو يستخدم default)
    │  - يبني StageContext(capability=..., input_data=...)
    │  - يستدعي router.route(capability, ctx)
    ▼
CapabilityRouter
    │  - SchemaValidationMiddleware.validate()
    │  - يختار Pipeline المسجل للـ capability
    │  - ينفذ pipeline.execute(**params)
    ▼
Pipeline (chain of stages)
    │  validate → pre_process → embed → store/search → post_process
    ▼
Response (JSON serialized)
```

## Current Handlers (قبل التحديث)

```python
# mcp_local/handlers.py — الحالي
def handle_embed(service, text: str) -> str:
    vector = service.embed_text(text)
    return json.dumps({"vector": vector, "dim": len(vector)})

def handle_search(service, query, top_k=10, filters="{}"):
    results = service.search_similar(query, top_k, json.loads(filters))
    return json.dumps([r.to_dict() for r in results])
```

هذه الـ handlers تستدعي `service` مباشرة — أي business logic (اختيار model prefix, format response, validation) موجود في الـ handler أو في الـ service.

## Updated Handlers (بعد التحديث — Thin)

```python
# mcp_local/handlers.py — بعد التحديث
from __future__ import annotations

import json

from pipelines.base import StageContext
from pipelines.router import CapabilityRouter


def handle_embed(router: CapabilityRouter,
                 text: str,
                 capability: str = "document.embed",
                 **kwargs) -> str:
    ctx = StageContext(
        capability=capability,
        input_data={"text": text, **kwargs},
    )
    result = router.route(capability, ctx)
    return json.dumps(result, ensure_ascii=False)


def handle_search(router: CapabilityRouter,
                  query: str,
                  top_k: int = 10,
                  filters: str = "{}",
                  capability: str = "search.semantic",
                  **kwargs) -> str:
    parsed_filters = json.loads(filters) if filters else {}
    ctx = StageContext(
        capability=capability,
        input_data={
            "query": query,
            "top_k": top_k,
            "filters": parsed_filters,
            **kwargs,
        },
    )
    result = router.route(capability, ctx)
    return json.dumps(result, ensure_ascii=False)


def handle_store(router: CapabilityRouter,
                 key: str,
                 text: str,
                 metadata: str = "{}",
                 capability: str = "document.ingest",
                 **kwargs) -> str:
    parsed_meta = json.loads(metadata) if metadata != "{}" else {}
    ctx = StageContext(
        capability=capability,
        input_data={
            "key": key,
            "text": text,
            "metadata": parsed_meta,
            **kwargs,
        },
    )
    result = router.route(capability, ctx)
    return json.dumps(result, ensure_ascii=False)


def handle_store_batch(router: CapabilityRouter,
                       items: str,
                       capability: str = "document.ingest.batch",
                       **kwargs) -> str:
    parsed = json.loads(items)
    ctx = StageContext(
        capability=capability,
        input_data={"items": parsed, **kwargs},
    )
    result = router.route(capability, ctx)
    return json.dumps(result, ensure_ascii=False)


def handle_delete(router: CapabilityRouter,
                  key: str,
                  capability: str = "document.delete",
                  **kwargs) -> str:
    ctx = StageContext(
        capability=capability,
        input_data={"key": key, **kwargs},
    )
    result = router.route(capability, ctx)
    return json.dumps(result, ensure_ascii=False)


def handle_count(router: CapabilityRouter,
                 capability: str = "document.count",
                 **kwargs) -> str:
    ctx = StageContext(
        capability=capability,
        input_data={**kwargs},
    )
    result = router.route(capability, ctx)
    return json.dumps(result, ensure_ascii=False)


def handle_health(router: CapabilityRouter,
                  capability: str = "system.health",
                  **kwargs) -> str:
    ctx = StageContext(
        capability=capability,
        input_data={**kwargs},
    )
    result = router.route(capability, ctx)
    return json.dumps(result, ensure_ascii=False)
```

**قاعدة الـ 3 أسطر**: كل handler يتبع نفس النمط:
1. بناء `StageContext` مع `capability` و `input_data`
2. استدعاء `router.route(capability, ctx)`
3. إرجاع `json.dumps(result)`

## Updated MCP Tools (7 أدوات أساسية + أدوات خاصة بالـ pipelines)

### الـ 7 Tools الحالية — مع إضافة `capability` و `response_fields`

```python
# mcp_local/tools.py — بعد التحديث
TOOL_DEFINITIONS: dict[str, dict] = {
    "embed_text": {
        "description": "Embed text to vector using specified pipeline capability",
        "input_schema": {
            "type": "object",
            "properties": {
                "text": {"type": "string", "description": "Text to embed"},
                "capability": {
                    "type": "string",
                    "description": "Pipeline capability",
                    "default": "document.embed",
                },
                "prefix": {
                    "type": "string",
                    "description": "Embedding prefix",
                    "default": "passage",
                    "enum": ["passage", "query", "none"],
                },
                "response_fields": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Fields to include in response",
                },
            },
            "required": ["text"],
        },
    },
    "search_similar": {
        "description": "Semantic search for similar documents",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query text"},
                "top_k": {"type": "integer", "description": "Number of results", "default": 10},
                "filters": {"type": "string", "description": "JSON filters", "default": "{}"},
                "capability": {
                    "type": "string",
                    "description": "Pipeline capability",
                    "default": "search.semantic",
                },
                "response_fields": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Fields to include in response",
                },
                "boost_factor": {
                    "type": "number",
                    "description": "Keyword boost factor (hybrid search only)",
                },
            },
            "required": ["query"],
        },
    },
    "store_document": {
        "description": "Embed and store a document",
        "input_schema": {
            "type": "object",
            "properties": {
                "key": {"type": "string", "description": "Document key/ID"},
                "text": {"type": "string", "description": "Document text"},
                "metadata": {"type": "string", "description": "JSON metadata", "default": "{}"},
                "capability": {
                    "type": "string",
                    "default": "document.ingest",
                },
                "pre_process": {
                    "type": "object",
                    "description": "Pre-processing config override",
                    "properties": {
                        "strip": {"type": "boolean", "default": True},
                        "normalize": {"type": "boolean", "default": True},
                        "max_length": {"type": "integer"},
                    },
                },
                "embed_config": {
                    "type": "object",
                    "description": "Embedding config override",
                    "properties": {
                        "prefix": {"type": "string"},
                        "model": {"type": "string"},
                    },
                },
                "store_config": {
                    "type": "object",
                    "description": "Storage config override",
                    "properties": {
                        "db_type": {"type": "string"},
                        "index_params": {"type": "object"},
                    },
                },
            },
            "required": ["key", "text"],
        },
    },
    "store_batch": {
        "description": "Embed and store multiple documents",
        "input_schema": {
            "type": "object",
            "properties": {
                "items": {
                    "type": "string",
                    "description": "JSON array of {text, key, metadata}",
                },
                "capability": {"type": "string", "default": "document.ingest.batch"},
                "response_fields": {
                    "type": "array",
                    "items": {"type": "string"},
                },
            },
            "required": ["items"],
        },
    },
    "delete_document": {
        "description": "Delete a document by key",
        "input_schema": {
            "type": "object",
            "properties": {
                "key": {"type": "string", "description": "Document key to delete"},
                "capability": {"type": "string", "default": "document.delete"},
            },
            "required": ["key"],
        },
    },
    "count_documents": {
        "description": "Count stored documents",
        "input_schema": {
            "type": "object",
            "properties": {
                "capability": {"type": "string", "default": "document.count"},
            },
        },
    },
    "health": {
        "description": "Check system health",
        "input_schema": {
            "type": "object",
            "properties": {
                "capability": {"type": "string", "default": "system.health"},
            },
        },
    },
}
```

### Pipeline-Specific Tools (جديدة — لكل capability tool مخصص)

```python
# pipelines/tools/ingestion_tool.py — Tool مخصص لـ document ingestion
TOOL_DEFINITIONS["ingest_document"] = {
    "description": "Ingest a document with full pipeline control",
    "input_schema": {
        "type": "object",
        "properties": {
            "key": {"type": "string", "description": "Unique document key"},
            "text": {"type": "string", "description": "Document content"},
            "metadata": {
                "type": "string",
                "description": "JSON metadata (title, tags, source, etc.)",
            },
            "pre_process": {
                "type": "object",
                "description": "Pre-processing overrides",
                "properties": {
                    "strip": {"type": "boolean", "default": True},
                    "normalize": {"type": "boolean", "default": True},
                    "max_length": {"type": "integer"},
                    "chunk_size": {"type": "integer"},
                    "chunk_overlap": {"type": "integer"},
                },
            },
            "embed_config": {
                "type": "object",
                "description": "Embedding overrides",
                "properties": {
                    "prefix": {"type": "string", "default": "passage"},
                    "model": {"type": "string", "description": "Override embedding model"},
                },
            },
            "store_config": {
                "type": "object",
                "description": "Storage overrides",
                "properties": {
                    "db_type": {"type": "string", "description": "Vector DB type override"},
                    "index_params": {
                        "type": "object",
                        "description": "Faiss index parameters",
                        "properties": {
                            "metric": {"type": "string", "enum": ["cosine", "l2", "ip"]},
                            "nlist": {"type": "integer"},
                        },
                    },
                },
            },
            "response_fields": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Response field projection",
            },
        },
        "required": ["key", "text"],
    },
}


# pipelines/tools/search_tool.py — Tool مخصص لـ hybrid search
TOOL_DEFINITIONS["search_hybrid"] = {
    "description": "Hybrid semantic + keyword search",
    "input_schema": {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "Search query"},
            "top_k": {"type": "integer", "default": 10, "description": "Final result count"},
            "filters": {"type": "string", "description": "JSON object filters"},
            "boost_factor": {
                "type": "number",
                "default": 0.5,
                "description": "Keyword score boost (0 = semantic only, 1 = balanced)",
            },
            "semantic_top_k": {
                "type": "integer",
                "default": 50,
                "description": "Initial semantic retrieval count (before re-rank)",
            },
            "response_fields": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Fields in response (e.g. ['key', 'score', 'text'])",
            },
            "min_score": {
                "type": "number",
                "description": "Minimum similarity threshold",
            },
        },
        "required": ["query"],
    },
}


# pipelines/tools/compare_tool.py — Tool مخصص لـ document comparison
TOOL_DEFINITIONS["compare_documents"] = {
    "description": "Compare two documents by their keys",
    "input_schema": {
        "type": "object",
        "properties": {
            "key_a": {"type": "string", "description": "First document key"},
            "key_b": {"type": "string", "description": "Second document key"},
            "metric": {
                "type": "string",
                "enum": ["cosine", "euclidean", "dot"],
                "default": "cosine",
                "description": "Similarity metric",
            },
            "response_fields": {
                "type": "array",
                "items": {"type": "string"},
            },
        },
        "required": ["key_a", "key_b"],
    },
}
```

## Updated `local_server.py` — مع router injection

```python
# mcp_local/local_server.py — بعد التحديث
from __future__ import annotations

import logging

from mcp import McpError
from mcp.server import FastMCP
from mcp.types import ErrorData

logger = logging.getLogger(__name__)


def build_server(router) -> FastMCP:
    """Build MCP server with CapabilityRouter injection."""
    app = FastMCP("embedding-mcp-local")

    @app.tool()
    async def embed_text(text: str,
                         capability: str = "document.embed",
                         **kwargs) -> str:
        try:
            from .handlers import handle_embed
            return handle_embed(router, text, capability=capability, **kwargs)
        except ValueError as e:
            raise McpError(ErrorData(code=-32602, message=str(e)))
        except Exception as e:
            logger.exception("embed_text failed")
            raise McpError(ErrorData(code=-32603, message=str(e)))

    @app.tool()
    async def search_similar(query: str,
                             top_k: int = 10,
                             filters: str = "{}",
                             capability: str = "search.semantic",
                             **kwargs) -> str:
        try:
            from .handlers import handle_search
            return handle_search(router, query, top_k, filters,
                                 capability=capability, **kwargs)
        except ValueError as e:
            raise McpError(ErrorData(code=-32602, message=str(e)))
        except Exception as e:
            logger.exception("search_similar failed")
            raise McpError(ErrorData(code=-32603, message=str(e)))

    @app.tool()
    async def store_document(key: str,
                             text: str,
                             metadata: str = "{}",
                             capability: str = "document.ingest",
                             **kwargs) -> str:
        try:
            from .handlers import handle_store
            return handle_store(router, key, text, metadata,
                                capability=capability, **kwargs)
        except ValueError as e:
            raise McpError(ErrorData(code=-32602, message=str(e)))
        except Exception as e:
            logger.exception("store_document failed")
            raise McpError(ErrorData(code=-32603, message=str(e)))

    @app.tool()
    async def store_batch(items: str,
                          capability: str = "document.ingest.batch",
                          **kwargs) -> str:
        try:
            from .handlers import handle_store_batch
            return handle_store_batch(router, items,
                                      capability=capability, **kwargs)
        except ValueError as e:
            raise McpError(ErrorData(code=-32602, message=str(e)))
        except Exception as e:
            logger.exception("store_batch failed")
            raise McpError(ErrorData(code=-32603, message=str(e)))

    @app.tool()
    async def delete_document(key: str,
                              capability: str = "document.delete",
                              **kwargs) -> str:
        try:
            from .handlers import handle_delete
            return handle_delete(router, key,
                                 capability=capability, **kwargs)
        except ValueError as e:
            raise McpError(ErrorData(code=-32602, message=str(e)))
        except Exception as e:
            logger.exception("delete_document failed")
            raise McpError(ErrorData(code=-32603, message=str(e)))

    @app.tool()
    async def count_documents(capability: str = "document.count",
                              **kwargs) -> str:
        try:
            from .handlers import handle_count
            return handle_count(router,
                                capability=capability, **kwargs)
        except ValueError as e:
            raise McpError(ErrorData(code=-32602, message=str(e)))
        except Exception as e:
            logger.exception("count_documents failed")
            raise McpError(ErrorData(code=-32603, message=str(e)))

    @app.tool()
    async def health(capability: str = "system.health",
                     **kwargs) -> str:
        try:
            from .handlers import handle_health
            return handle_health(router,
                                 capability=capability, **kwargs)
        except ValueError as e:
            raise McpError(ErrorData(code=-32602, message=str(e)))
        except Exception as e:
            logger.exception("health failed")
            raise McpError(ErrorData(code=-32603, message=str(e)))

    # NEW: Pipeline-specific tools
    @app.tool()
    async def ingest_document(key: str,
                              text: str,
                              metadata: str = "{}",
                              pre_process: dict | None = None,
                              embed_config: dict | None = None,
                              store_config: dict | None = None,
                              response_fields: list[str] | None = None) -> str:
        try:
            from .handlers import handle_store
            return handle_store(
                router, key, text, metadata,
                capability="document.ingest",
                pre_process=pre_process,
                embed_config=embed_config,
                store_config=store_config,
                response_fields=response_fields,
            )
        except ValueError as e:
            raise McpError(ErrorData(code=-32602, message=str(e)))
        except Exception as e:
            logger.exception("ingest_document failed")
            raise McpError(ErrorData(code=-32603, message=str(e)))

    @app.tool()
    async def search_hybrid(query: str,
                            top_k: int = 10,
                            filters: str = "{}",
                            boost_factor: float = 0.5,
                            semantic_top_k: int = 50,
                            response_fields: list[str] | None = None,
                            min_score: float | None = None) -> str:
        try:
            from .handlers import handle_search
            return handle_search(
                router, query, top_k, filters,
                capability="search.hybrid",
                boost_factor=boost_factor,
                semantic_top_k=semantic_top_k,
                response_fields=response_fields,
                min_score=min_score,
            )
        except ValueError as e:
            raise McpError(ErrorData(code=-32602, message=str(e)))
        except Exception as e:
            logger.exception("search_hybrid failed")
            raise McpError(ErrorData(code=-32603, message=str(e)))

    @app.tool()
    async def compare_documents(key_a: str,
                                key_b: str,
                                metric: str = "cosine",
                                response_fields: list[str] | None = None) -> str:
        try:
            ctx = StageContext(
                capability="document.compare",
                input_data={
                    "key_a": key_a,
                    "key_b": key_b,
                    "metric": metric,
                    "response_fields": response_fields or [],
                },
            )
            result = router.route("document.compare", ctx)
            return json.dumps(result, ensure_ascii=False)
        except ValueError as e:
            raise McpError(ErrorData(code=-32602, message=str(e)))
        except Exception as e:
            logger.exception("compare_documents failed")
            raise McpError(ErrorData(code=-32603, message=str(e)))

    return app
```

## Consumer Control — كل parameter إضافي يمرر إلى `StageContext`

كل extra parameter (مثل `pre_process`, `embed_config`, `store_config`, `boost_factor`, `min_score`) يمرر عبر `**kwargs` ويصل إلى `StageContext.input_data`. الـ pipeline stages تقرأ هذه القيم وتستخدمها كـ **overrides** للـ config الأساسي:

```
Input: store_document(key="doc1", text="...",
       pre_process={"strip": True, "max_length": 512})

التدفق:
1. handler → StageContext(input_data={"key": "doc1", "text": "...",
                           "pre_process": {"strip": True, "max_length": 512}})
2. pipeline → validate stage → validate(stage_ctx)
3. pre_process/strip stage → execute(stage_ctx):
       config.strip = stage_ctx.input_data.get("pre_process", {}).get("strip", True)
4. pre_process/truncate stage → execute(stage_ctx):
       max_len = stage_ctx.input_data.get("pre_process", {}).get("max_length", None)
       if max_len: truncate(text, max_len)
```

بهذه الطريقة، الـ MCP client يتحكم في **كل مرحلة** من pipeline عبر parameters إضافية، بدون تغيير الـ YAML config أو إعادة تشغيل السيرفر.

## Backward Compatibility — الـ 7 أدوات القديمة تستمر في العمل

عندما لا يوفر الـ client `capability` parameter، يستخدم الـ handler القيمة الافتراضية (`default`). هذا يعني أن أي client قديم (لا يعرف عن pipelines) سيستمر في العمل:

```python
# عميل قديم — لا capability parameter
handle_store(router, key="doc1", text="hello")
# → capability defaults to "document.ingest"
# → نفس السلوك القديم (embed + store)

# عميل جديد — مع capability parameter
handle_store(router, key="doc1", text="hello",
             capability="document.ingest.custom",
             pre_process={"strip": False})
# → capability مختلف → pipeline مختلف → سلوك مختلف
```

قاعدة الـ fallback:
- إذا لم يقدم الـ client `capability` → استخدم `default` المحدد في توقيع الـ handler
- إذا قدم `capability` معرف → استخدم pipeline المسجل لذلك الـ capability
- إذا قدم `capability` غير معروف → `CapabilityRouter` يرمي `UnknownCapabilityError`

## Response Projection — `response_fields` يتحكم في شكل المخرج

`ResponseProjectorStage` (من `10-response-projection-format.md`) يقرأ `input_data["response_fields"]` ويصفي الـ output:

```python
# post_process/response_projector.py
class ResponseProjectorStage(PostProcessStage):
    @property
    def name(self) -> str:
        return "response_projector"

    def execute(self, ctx: StageContext) -> StageContext:
        fields = ctx.input_data.get("response_fields", [])
        if not fields:
            return ctx  # no projection — return full output

        output = ctx.output_data
        if isinstance(output, list):
            ctx.output_data = [
                {k: item[k] for k in fields if k in item}
                for item in output
            ]
        elif isinstance(output, dict):
            ctx.output_data = {
                k: output[k] for k in fields if k in output
            }
        return ctx
```

مثال:
```python
# Input: search_hybrid(query="AI", response_fields=["key", "score"])
# Output (بدون projection):
#   [{"key": "doc1", "score": 0.92, "text": "...", "metadata": {...}}, ...]
# Output (مع projection):
#   [{"key": "doc1", "score": 0.92}, ...]
```

## Error Handling — `McpError` يبقى كما هو

الـ pipeline قد يرمي `StageError` بأكواد مختلفة. الـ handler يحوّل أي `StageError` إلى `McpError` بشكل موحد:

```python
# pipelines/errors.py — mapping StageError → McpError
def stage_error_to_mcp_error(error: StageError) -> McpError:
    code_map = {
        "STAGE_VALIDATION_ERROR": -32602,  # Invalid params
        "STAGE_ERROR": -32603,             # Internal error
        "PIPELINE_ERRORS": -32603,         # Internal error
        "UNKNOWN_CAPABILITY": -32602,      # Invalid params
        "INTERNAL_ERROR": -32603,          # Internal error
    }
    mcp_code = code_map.get(error.code, -32603)
    return McpError(ErrorData(code=mcp_code, message=str(error)))
```

```python
# في local_server.py — inside each tool
try:
    result = handle_search(router, query, top_k, filters, ...)
    return result
except StageError as e:
    raise stage_error_to_mcp_error(e)
except ValueError as e:
    raise McpError(ErrorData(code=-32602, message=str(e)))
except Exception as e:
    logger.exception("... failed")
    raise McpError(ErrorData(code=-32603, message=str(e)))
```

بما أن `StageError` يرث من `Exception`، وأكواد الخطأ فيها معلومة (`code`)، نستطيع mapping دقيق إلى MCP error codes. الـ client (MCP host) يستقبل نفس شكل الخطأ السابق — بدون تغيير في واجهة المستخدم.

## Complete Flow: Hybrid Search مع Per-Stage Control

```
MCP Client Request:
    search_hybrid(
        query="Attention mechanism",
        top_k=5,
        capability="search.hybrid",
        response_fields=["key", "score"],
        boost_factor=0.3,
        min_score=0.5,
        semantic_top_k=50,
    )

تدفق التنفيذ:
1. local_server.py → app.tool("search_hybrid") تستقبل الطلب
       │
       ├─ ترسل parameters إلى handle_search(router, ...)
       │
2. handle_search → تبني StageContext:
       │   StageContext(
       │       capability="search.hybrid",
       │       input_data={
       │           "query": "Attention mechanism",
       │           "top_k": 5,
       │           "response_fields": ["key", "score"],
       │           "boost_factor": 0.3,
       │           "min_score": 0.5,
       │           "semantic_top_k": 50,
       │       }
       │   )
       │
3. router.route("search.hybrid", ctx)
       │
       ├─ SchemaValidationMiddleware.validate(ctx)
       │      top_k ∈ [1, 1000], query not empty, boost_factor ∈ [0, 1]
       │
       ├─ Pipeline.execute(**ctx.input_data)
       │      │
       │      ├─ validate stage:
       │      │      query non-empty, top_k > 0
       │      │
       │      ├─ embed (query_embed) stage:
       │      │      prefix = "query: "
       │      │      vector = model.embed("query: Attention mechanism")
       │      │      ctx.metadata["query_vector"] = vector
       │      │
       │      ├─ search (semantic) stage:
       │      │      results = vec_db.search(vector, top_k=50)
       │      │      # uses semantic_top_k from input_data
       │      │      ctx.output_data = results  # 50 results
       │      │
       │      ├─ hybrid_boost stage:
       │      │      boost_factor = ctx.input_data.get("boost_factor", 0.3)
       │      │      keyword_scores = bm25.score(query)
       │      │      for r in results:
       │      │          r.score = (1 - boost_factor) * r.vector_score
       │      │                 + boost_factor * keyword_scores.get(r.key, 0)
       │      │
       │      ├─ re_sort stage (part of post_process):
       │      │      results.sort(key=lambda r: r.score, reverse=True)
       │      │
       │      ├─ truncate stage:
       │      │      ctx.output_data = results[:top_k]
       │      │      # top_k = 5 from input_data
       │      │
       │      └─ response_projector stage:
       │             fields = ["key", "score"] from input_data
       │             ctx.output_data = [
       │                 {"key": r.key, "score": r.score}
       │                 for r in ctx.output_data
       │             ]
       │
       └─ Return ctx.output_data (list of 5 dicts)

4. handler → json.dumps(result)
       → '[{"key": "doc1", "score": 0.92}, {"key": "doc3", "score": 0.87}, ...]'

5. MCP Client يستقبل JSON array — 5 results, كل result يحتوي key + score فقط
```

## Summary: MCP Layer Architecture

```
                    ┌──────────────────────────────────────┐
                    │          MCP Client                  │
                    │  (Claude Desktop, VS Code, etc.)     │
                    └────────────────┬─────────────────────┘
                                    │  tool call
                                    ▼
                    ┌──────────────────────────────────────┐
                    │      local_server.py (FastMCP)       │
                    │  ← tool decorators → 7 old + 3 new   │
                    └────────────────┬─────────────────────┘
                                    │  parameters + capability
                                    ▼
                    ┌──────────────────────────────────────┐
                    │        handlers.py (Thin)            │
                    │  ← 3 أسطر كحد أقصى                   │
                    │  ← يبني StageContext                 │
                    │  ← يستدعي router.route()             │
                    └────────────────┬─────────────────────┘
                                    │  StageContext
                                    ▼
                    ┌──────────────────────────────────────┐
                    │      CapabilityRouter                │
                    │  ← يختار Pipeline من registry        │
                    │  ← يمرر context                      │
                    └────────────────┬─────────────────────┘
                                    │
                                    ▼
                    ┌──────────────────────────────────────┐
                    │         Pipeline (stages chain)      │
                    │  validate → pre_process → embed →    │
                    │  store/search/compare → post_process │
                    └────────────────┬─────────────────────┘
                                    │  ctx.output_data
                                    ▼
                    ┌──────────────────────────────────────┐
                    │     JSON Response (← handler)        │
                    │  ← serialized with json.dumps()      │
                    └──────────────────────────────────────┘
```

## Key Design Rules

| Rule | Description |
|------|-------------|
| **Thin Handler** | Handler ≤ 3 lines. No business logic. Only `StageContext` construction + `router.route()` + `json.dumps()`. |
| **Consumer Control** | Every extra parameter reaches `StageContext.input_data` and overrides stage config. |
| **Backward Compatibility** | Missing `capability` → uses default. Old clients work unchanged. |
| **Response Projection** | `response_fields` filters output via `ResponseProjectorStage`. |
| **Error Normalization** | `StageError.code` → MCP error code. No change to client error interface. |
| **Pipeline-Specific Tools** | Each capability can have its own MCP tool with detailed input schema. |
| **No Direct Service Access** | Handlers never call `service.embed_text()` or `service.search_similar()` directly. All logic goes through pipelines. |
| **Zero Config Change** | Adding new capability = add tool definition + handler + pipeline YAML. No changes to existing tools. |
