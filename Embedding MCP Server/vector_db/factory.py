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
            For pgvector: conn_str (required)
            For falkordb: host (default "localhost"), port (default 6379)

    Returns:
        VectorDB implementation
    """
    if db_type == "faiss":
        return FAISSAdapter(db_path, dim)

    if db_type == "pgvector":
        from embedding_mcp.vector_db.pgvector_adapter import PgVectorAdapter
        conn_str = kwargs.get("conn_str")
        if not conn_str:
            raise ValueError("conn_str is required for pgvector adapter")
        return PgVectorAdapter(conn_str, dim)

    if db_type == "falkordb":
        from embedding_mcp.vector_db.falkordb_adapter import FalkorDBAdapter
        return FalkorDBAdapter(
            host=kwargs.get("host", "localhost"),
            port=kwargs.get("port", 6379),
            dim=dim,
        )

    if db_type == "ladybug":
        from embedding_mcp.vector_db.ladybug_adapter import LadybugAdapter
        return LadybugAdapter(db_path, dim)

    if db_type == "kuzu":
        from embedding_mcp.vector_db.kuzudb_adapter import KuzuDBAdapter
        return KuzuDBAdapter(db_path, dim)

    raise ValueError(f"Unsupported vector DB type: {db_type}")