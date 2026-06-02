"""Embedding MCP Server package - standalone embedding services."""
from embedding_mcp.config import Settings
from embedding_mcp.embedding_model.e5_model import create_embedding_model
from embedding_mcp.vector_db import create_vector_db, SearchResult
from embedding_mcp.embedding_service.service import EmbeddingService

__all__ = [
    "Settings",
    "create_embedding_model",
    "create_vector_db",
    "SearchResult",
    "EmbeddingService",
]