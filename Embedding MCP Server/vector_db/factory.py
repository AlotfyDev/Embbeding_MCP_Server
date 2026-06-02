"""Vector DB Factory for creating database adapters."""
from __future__ import annotations

from embedding_mcp.vector_db.base import VectorDB
from embedding_mcp.vector_db.faiss_adapter import FAISSAdapter


def create_vector_db(db_type: str, db_path: str, dim: int, **kwargs) -> VectorDB:
    """Create a vector database adapter.

    Args:
        db_type: One of "faiss", "pgvector", "falkordb", "ladybug", "kuzu"
        db_path: Path for local database storage
        dim: Embedding dimension
        **kwargs: Additional database-specific options

    Returns:
        VectorDB implementation
    """
    if db_type == "faiss":
        return FAISSAdapter(db_path, dim)
    else:
        raise ValueError(f"Unsupported vector DB type: {db_type}")