"""Vector DB Adapter package."""
from embedding_mcp.vector_db.base import VectorDB, SearchResult
from embedding_mcp.vector_db.factory import create_vector_db

__all__ = ["VectorDB", "SearchResult", "create_vector_db"]