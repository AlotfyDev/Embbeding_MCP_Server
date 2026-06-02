# خادم MCP المحلي للتضمين — Embedding Local MCP Server (Stdio)

## مبدأ Thin Handler

نفس نمط Smart Task: **الـ Handler لا يحتوي Business Logic.** يستدعي Service method واحد، يرجع JSON. كل المنطق في الـ Service.

```
✅ handler.handle_embed(service, text)  # Thin — يستدعي Service فقط
❌ service.embed_text(text)             # Thick — منطق في غير محله
❌ if len(text) > 5000: ...             # Business Logic في Handler
```

## هيكل الملفات

```
smart_task/embedding_mcp_local/
    __init__.py         ← CLI main() + run_local_server()
    __main__.py         ← python -m hook
    local_server.py     ← build_server(): ينشئ FastMCP ويسجل tools
    handlers.py         ← handler functions (thin wrappers)
    tools.py            ← Tool metadata / JSON Schemas
```

## __init__.py — نمط الـ CLI والـ Wiring

```python
from smart_task.repository import Repository
from smart_task.embedding.service import EmbeddingService
from smart_task.embedding.model_factory import EmbeddingModelFactory
from smart_task.embedding.vector_db_factory import VectorDBFactory
from smart_task.embedding_mcp_local.local_server import build_server

def run_local_server(db_path: str, model_path: str, vec_db_type: str) -> None:
    repo = Repository(db_path)
    model = EmbeddingModelFactory.create(model_path)
    vec_db = VectorDBFactory.create(vec_db_type, dim=model.dim)
    service = EmbeddingService(model, vec_db)
    server = build_server(service, repo)
    server.run(transport="stdio")

def main() -> None:
    parser = argparse.ArgumentParser(description="Embedding MCP Local Server")
    parser.add_argument("--db-path", default="smart_task.db")
    parser.add_argument("--model-path", default="models/multilingual-e5-small/onnx")
    parser.add_argument("--vec-db-type", default="faiss")
    args = parser.parse_args()
    signal.signal(signal.SIGINT, _handle_signal)
    signal.signal(signal.SIGTERM, _handle_signal)
    run_local_server(args.db_path, args.model_path, args.vec_db_type)
```

## local_server.py — نمط build_server + async @app.tool()

```python
from mcp import McpError
from mcp.server import FastMCP
from mcp.types import ErrorData
from smart_task.embedding_mcp_local import handlers

def build_server(service, repo) -> FastMCP:
    app = FastMCP("embedding-mcp-local")

    @app.tool()
    async def embed_text(text: str) -> str:
        try:
            return handlers.handle_embed(service, text)
        except ValueError as e:
            raise McpError(ErrorData(code=-32602, message=str(e)))
        except Exception as e:
            logger.exception("embed_text failed")
            raise McpError(ErrorData(code=-32603, message=str(e)))

    @app.tool()
    async def search_similar(query: str, top_k: int = 10) -> str:
        try:
            return handlers.handle_search(service, query, top_k)
        except ValueError as e:
            raise McpError(ErrorData(code=-32602, message=str(e)))
        except Exception as e:
            logger.exception("search_similar failed")
            raise McpError(ErrorData(code=-32603, message=str(e)))

    # @app.tool() store_document, store_batch, delete_document, count_documents, health
    # — نفس النمط: try/handle_xxx/except ValueError/except Exception

    return app
```

كل Tool تتبع نفس النمط: `handlers.handle_xxx(service, ...)` → `ValueError` → `-32602` / `Exception` → `-32603`.

الـ tools المسجلة: **embed_text, search_similar, store_document, store_batch, delete_document, count_documents, health** — 7 tools.

## handlers.py — نمط الـ thin handlers

```python
import json

def handle_embed(service, text: str) -> str:
    vector = service.embed_text(text)
    return json.dumps({"vector": vector, "dim": len(vector), "model": "e5-small"})

def handle_search(service, query: str, top_k: int) -> str:
    results = service.search_similar(query, top_k)
    return json.dumps([r.to_dict() for r in results], ensure_ascii=False)

def handle_store(service, key: str, text: str, metadata: str) -> str:
    parsed = json.loads(metadata) if metadata != "{}" else {}
    service.embed_document(text, key, parsed)
    return json.dumps({"status": "stored", "key": key})

def handle_store_batch(service, items: str) -> str:
    parsed = json.loads(items)
    count = service.embed_batch_documents(parsed)
    return json.dumps({"status": "stored", "count": count})

def handle_delete(service, key: str) -> str:
    service.delete_document(key)
    return json.dumps({"status": "deleted", "key": key})

def handle_count(service) -> str:
    return json.dumps({"count": service.document_count()})

def handle_health(service) -> str:
    return json.dumps(service.health(), ensure_ascii=False)
```

## tools.py — نمط الـ static metadata (اختياري)

```python
TOOL_DEFINITIONS = {
    "embed_text": {
        "description": "Embed text to vector",
        "input_schema": {
            "type": "object",
            "properties": {"text": {"type": "string"}},
            "required": ["text"]
        }
    },
    "search_similar": {
        "description": "Semantic search",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string"},
                "top_k": {"type": "integer", "default": 10}
            },
            "required": ["query"]
        }
    },
    # store_document, store_batch, delete_document, count_documents, health — نفس النمط
}
```

## Error Handling Pattern

كل tool تتبع:

```python
try:
    return handlers.handle_xxx(service, ...)
except ValueError as e:
    raise McpError(ErrorData(code=-32602, message=str(e)))
except Exception as e:
    logger.exception("xxx failed")
    raise McpError(ErrorData(code=-32603, message=str(e)))
```

| McpError Code | Python Exception | السبب |
|---------------|-----------------|------|
| `-32602` | `ValueError` | خطأ في المدخلات |
| `-32603` | `Exception` | خطأ داخلي (موديل، Vector DB) |

**لا Business Logic في الـ tools أو handlers — فقط استدعاء Service وتحويل الأخطاء إلى McpError.**

## Startup Flow

```
1. CLI parsing → args
2. Repository(db_path)
3. EmbeddingModelFactory.create(model_path) → EmbeddingModel
4. VectorDBFactory.create(vec_db_type, dim=model.dim) → VectorDB
5. EmbeddingService(model, vec_db)    ← التحقق من تطابق dim
6. build_server(service, repo)        ← FastMCP + 7 tools
7. server.run(transport="stdio")      ← Stdio Transport
```

## Tool Summary

| الـ Tool | الإدخال | الإرجاع | الوظيفة |
|----------|---------|---------|---------|
| `embed_text` | text | vector + dim + model | تضمين نص |
| `search_similar` | query, top_k | SearchResult[] | بحث دلالي |
| `store_document` | key, text, metadata | {status, key} | تخزين + تضمين |
| `store_batch` | items (JSON) | {status, count} | تخزين مجموعة |
| `delete_document` | key | {status, key} | حذف وثيقة |
| `count_documents` | — | {count} | عدد الوثائق |
| `health` | — | health status | صحة النظام |
