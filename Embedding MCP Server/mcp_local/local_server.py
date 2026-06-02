"""MCP server wiring for local stdio transport."""
from __future__ import annotations

import logging

from mcp import McpError
from mcp.server import FastMCP
from mcp.types import ErrorData

logger = logging.getLogger(__name__)


def build_server(service) -> FastMCP:
    app = FastMCP("embedding-mcp-local")

    @app.tool()
    async def embed_text(text: str) -> str:
        try:
            from .handlers import handle_embed
            return handle_embed(service, text)
        except ValueError as e:
            raise McpError(ErrorData(code=-32602, message=str(e)))
        except Exception as e:
            logger.exception("embed_text failed")
            raise McpError(ErrorData(code=-32603, message=str(e)))

    @app.tool()
    async def search_similar(query: str, top_k: int = 10, filters: str = "{}") -> str:
        try:
            from embedding_mcp.mcp_local.handlers import handle_search
            return handle_search(service, query, top_k, filters)
        except ValueError as e:
            raise McpError(ErrorData(code=-32602, message=str(e)))
        except Exception as e:
            logger.exception("search_similar failed")
            raise McpError(ErrorData(code=-32603, message=str(e)))

    @app.tool()
    async def store_document(key: str, text: str, metadata: str = "{}") -> str:
        try:
            from embedding_mcp.mcp_local.handlers import handle_store
            return handle_store(service, key, text, metadata)
        except ValueError as e:
            raise McpError(ErrorData(code=-32602, message=str(e)))
        except Exception as e:
            logger.exception("store_document failed")
            raise McpError(ErrorData(code=-32603, message=str(e)))

    @app.tool()
    async def store_batch(items: str) -> str:
        try:
            from embedding_mcp.mcp_local.handlers import handle_store_batch
            return handle_store_batch(service, items)
        except ValueError as e:
            raise McpError(ErrorData(code=-32602, message=str(e)))
        except Exception as e:
            logger.exception("store_batch failed")
            raise McpError(ErrorData(code=-32603, message=str(e)))

    @app.tool()
    async def delete_document(key: str) -> str:
        try:
            from embedding_mcp.mcp_local.handlers import handle_delete
            return handle_delete(service, key)
        except ValueError as e:
            raise McpError(ErrorData(code=-32602, message=str(e)))
        except Exception as e:
            logger.exception("delete_document failed")
            raise McpError(ErrorData(code=-32603, message=str(e)))

    @app.tool()
    async def count_documents() -> str:
        try:
            from embedding_mcp.mcp_local.handlers import handle_count
            return handle_count(service)
        except ValueError as e:
            raise McpError(ErrorData(code=-32602, message=str(e)))
        except Exception as e:
            logger.exception("count_documents failed")
            raise McpError(ErrorData(code=-32603, message=str(e)))

    @app.tool()
    async def health() -> str:
        try:
            from embedding_mcp.mcp_local.handlers import handle_health
            return handle_health(service)
        except ValueError as e:
            raise McpError(ErrorData(code=-32602, message=str(e)))
        except Exception as e:
            logger.exception("health failed")
            raise McpError(ErrorData(code=-32603, message=str(e)))

    return app