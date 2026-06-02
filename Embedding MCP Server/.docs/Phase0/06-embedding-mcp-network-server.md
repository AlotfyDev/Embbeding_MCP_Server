# خادم MCP الشبكي للتضمين — Embedding Network MCP Server (SSE)

## الفرق عن Local

**نفس الـ Service، نفس الـ Handlers، الفرق الوحيد هو الـ Transport.**

| البعد | Local (Stdio) | Network (SSE) |
|-------|---------------|---------------|
| Transport | stdin/stdout | Server-Sent Events |
| مناسب لـ | sub-process (MCP host) | remote access / web clients |
| استقبال host/port | لا | FastMCP(..., host=host, port=port) |
| CORS | غير مطلوب | يمكن إضافته (Starlette middleware) |

## Shared Handlers — لا تكرار

يُستورد من `embedding_mcp_local.handlers` مباشرة. **Zero duplication — نفس الدوال بالضبط.**

```python
from smart_task.embedding_mcp_local.handlers import (
    handle_embed,
    handle_search,
    handle_store,
    handle_store_batch,
    handle_delete,
    handle_count,
    handle_health,
)
```

## هيكل الملفات

```
smart_task/embedding_mcp_network/
    __init__.py         ← CLI main() + run_network_server()
    __main__.py         ← python -m hook
    network_server.py   ← create_sse_app(): ينشئ FastMCP مع SSE transport
```

## network_server.py — نمط create_sse_app

```python
"""
SSE server wiring — creates FastMCP app with SSE transport.

Imports handlers from ``smart_task.embedding_mcp_local.handlers`` (no duplication).
Uses FastMCP.run(transport="sse") for simplified SSE server setup.
"""

from __future__ import annotations

import logging

from mcp import McpError
from mcp.server import FastMCP
from mcp.types import ErrorData

from smart_task.embedding_mcp_local.handlers import (
    handle_count,
    handle_delete,
    handle_embed,
    handle_health,
    handle_search,
    handle_store,
    handle_store_batch,
)

logger = logging.getLogger(__name__)


def create_sse_app(service, repo, host: str = "127.0.0.1", port: int = 8100) -> FastMCP:
    app = FastMCP("embedding-mcp-network", host=host, port=port)

    # ------------------------------------------------------------------
    @app.tool()
    async def embed_text(text: str) -> str:
        try:
            return handle_embed(service, text)
        except ValueError as e:
            raise McpError(ErrorData(code=-32602, message=str(e)))
        except Exception:
            logger.exception("embed_text failed")
            raise McpError(ErrorData(code=-32603, message=str(e)))

    # ------------------------------------------------------------------
    @app.tool()
    async def search_similar(query: str, top_k: int = 10) -> str:
        try:
            return handle_search(service, query, top_k)
        except ValueError as e:
            raise McpError(ErrorData(code=-32602, message=str(e)))
        except Exception:
            logger.exception("search_similar failed")
            raise McpError(ErrorData(code=-32603, message=str(e)))

    # ------------------------------------------------------------------
    @app.tool()
    async def store_document(key: str, text: str, metadata: str = "{}") -> str:
        try:
            return handle_store(service, key, text, metadata)
        except ValueError as e:
            raise McpError(ErrorData(code=-32602, message=str(e)))
        except Exception:
            logger.exception("store_document failed")
            raise McpError(ErrorData(code=-32603, message=str(e)))

    # ------------------------------------------------------------------
    @app.tool()
    async def store_batch(items: str) -> str:
        try:
            return handle_store_batch(service, items)
        except ValueError as e:
            raise McpError(ErrorData(code=-32602, message=str(e)))
        except Exception:
            logger.exception("store_batch failed")
            raise McpError(ErrorData(code=-32603, message=str(e)))

    # ------------------------------------------------------------------
    @app.tool()
    async def delete_document(key: str) -> str:
        try:
            return handle_delete(service, key)
        except ValueError as e:
            raise McpError(ErrorData(code=-32602, message=str(e)))
        except Exception:
            logger.exception("delete_document failed")
            raise McpError(ErrorData(code=-32603, message=str(e)))

    # ------------------------------------------------------------------
    @app.tool()
    async def count_documents() -> str:
        try:
            return handle_count(service)
        except ValueError as e:
            raise McpError(ErrorData(code=-32602, message=str(e)))
        except Exception:
            logger.exception("count_documents failed")
            raise McpError(ErrorData(code=-32603, message=str(e)))

    # ------------------------------------------------------------------
    @app.tool()
    async def health() -> str:
        try:
            return handle_health(service)
        except ValueError as e:
            raise McpError(ErrorData(code=-32602, message=str(e)))
        except Exception:
            logger.exception("health failed")
            raise McpError(ErrorData(code=-32603, message=str(e)))

    return app
```

## كيف يعمل SSE Transport بالضبط (هام)

عند استدعاء `app.run(transport="sse")`، FastMCP library تقوم داخليًا بـ:

1. استدعاء `FastMCP.sse_app()` التي تبني Starlette application مع:
   - `Route("/sse", GET)` — SSE endpoint لكل client
   - `Mount("/messages/", POST)` — لتلقي رسائل JSON من client
   - يستخدم `SseServerTransport` من `mcp.server.sse`

2. تشغيل `uvicorn.Server(config).serve()` لإدارة Starlette app

**أي: أنت لا تحتاج لاستدعاء Uvicorn بنفسك — FastMCP.run(transport="sse") يفعل ذلك تلقائيًا.**

## __init__.py — نمط الـ CLI

```python
"""
Embedding MCP Network Server — SSE transport over HTTP.

Usage::

    smart-task-embedding-network [--host HOST] [--port PORT] [--db-path PATH] [--model-path PATH] [--vec-db-type TYPE]
    python -m smart_task.embedding_mcp_network
"""

from __future__ import annotations

import argparse
import logging
import signal

from smart_task.repository import Repository
from smart_task.embedding.service import EmbeddingService
from smart_task.embedding.model_factory import EmbeddingModelFactory
from smart_task.embedding.vector_db_factory import VectorDBFactory
from smart_task.embedding_mcp_network.network_server import create_sse_app

logger = logging.getLogger("smart_task.embedding_mcp_network")

running = True


def _handle_signal(signum, frame):
    global running
    running = False


def run_network_server(db_path: str = "smart_task.db", model_path: str = "models/multilingual-e5-small/onnx", vec_db_type: str = "faiss", host: str = "127.0.0.1", port: int = 8100) -> None:
    repo = Repository(db_path)
    model = EmbeddingModelFactory.create(model_path)
    vec_db = VectorDBFactory.create(vec_db_type, dim=model.dim)
    service = EmbeddingService(model, vec_db)
    app = create_sse_app(service, repo, host=host, port=port)
    logger.info("Embedding MCP Network server starting on %s:%s", host, port)
    app.run(transport="sse")


def main() -> None:
    parser = argparse.ArgumentParser(description="Embedding MCP Network Server (SSE)")
    parser.add_argument("--host", default="127.0.0.1", help="Bind address")
    parser.add_argument("--port", type=int, default=8100, help="Bind port")
    parser.add_argument("--db-path", default="smart_task.db", help="Path to SQLite database")
    parser.add_argument("--model-path", default="models/multilingual-e5-small/onnx", help="Path to ONNX embedding model")
    parser.add_argument("--vec-db-type", default="faiss", help="Vector DB type: faiss | pgvector")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO)
    signal.signal(signal.SIGINT, _handle_signal)
    signal.signal(signal.SIGTERM, _handle_signal)

    run_network_server(
        db_path=args.db_path,
        model_path=args.model_path,
        vec_db_type=args.vec_db_type,
        host=args.host,
        port=args.port,
    )
```

## Error Response Format

نفس نمط Local Server — جميع الأخطاء عبر McpError:

| McpError Code | Python Exception | السبب |
|---------------|-----------------|------|
| `-32602` | `ValueError` | خطأ في المدخلات |
| `-32603` | `Exception` | خطأ داخلي (موديل، Vector DB) |

```json
{
  "error": {
    "code": -32602,
    "message": "text must not be empty"
  }
}
```

## Dual Run Modes

يمكن تشغيل نفس الـ Embedding Server في وضعين بتغيير `transport` فقط:

```python
server.run(transport="stdio")  # Local — stdin/stdout
server.run(transport="sse")    # Network — HTTP/SSE مع Uvicorn داخلي
```

لكن عمليًا، كل Transport له package منفصل (`embedding_mcp_local` و `embedding_mcp_network`) لأن الـ CLI args والـ dependencies مختلفة. الـ Handlers مشتركة (لا تكرار)، والـ tools متطابقة.

## Tool Summary

نفس أدوات Local Server بالضبط — الـ 7 tools (embed_text, search_similar, store_document, store_batch, delete_document, count_documents, health) مع نفس التواقيع ونفس نمط الأخطاء، ونفس الـ handlers.
