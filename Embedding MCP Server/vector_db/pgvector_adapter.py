"""PgVector vector database adapter - PostgreSQL with pgvector extension."""
from __future__ import annotations

from embedding_mcp.embedding_service.exceptions import DimensionMismatchError
from embedding_mcp.vector_db.base import VectorDB, SearchResult

try:
    import asyncpg
except ImportError:
    asyncpg = None


class PgVectorAdapter(VectorDB):
    """PostgreSQL + pgvector vector database adapter."""

    def __init__(self, conn_str: str, dim: int):
        if asyncpg is None:
            raise ImportError("asyncpg is required for PgVectorAdapter. Install with: pip install embedding-mcp[pgvector]")
        self._conn_str = conn_str
        self._dim = dim
        self._pool = None

    async def _ensure_pool(self) -> None:
        if self._pool is None:
            self._pool = await asyncpg.create_pool(self._conn_str, min_size=1, max_size=5)
            async with self._pool.acquire() as conn:
                await conn.execute(
                    "CREATE EXTENSION IF NOT EXISTS vector"
                )
                await conn.execute(
                    "CREATE TABLE IF NOT EXISTS vec_embeddings ("
                    "  key TEXT PRIMARY KEY,"
                    "  embedding vector($1),"
                    "  metadata JSONB"
                    ")",
                    self._dim,
                )
                await conn.execute(
                    "CREATE INDEX IF NOT EXISTS idx_vec_embeddings_ivfflat "
                    "ON vec_embeddings USING ivfflat (embedding vector_cosine_ops)"
                )

    def store(self, key: str, vector: list[float], metadata: dict | None = None) -> None:
        if len(vector) != self._dim:
            raise DimensionMismatchError(f"Vector length {len(vector)} does not match expected {self._dim}")
        import asyncio
        asyncio.run(self._store_async(key, vector, metadata or {}))

    async def _store_async(self, key: str, vector: list[float], metadata: dict) -> None:
        await self._ensure_pool()
        async with self._pool.acquire() as conn:
            await conn.execute(
                "INSERT INTO vec_embeddings (key, embedding, metadata) "
                "VALUES ($1, $2::vector, $3::jsonb) "
                "ON CONFLICT (key) DO UPDATE SET embedding = $2::vector, metadata = $3::jsonb",
                key, vector, metadata,
            )

    def store_batch(self, items: list[tuple[str, list[float], dict | None]]) -> None:
        for key, vector, _ in items:
            if len(vector) != self._dim:
                raise DimensionMismatchError(f"Vector length {len(vector)} does not match expected {self._dim}")
        import asyncio
        asyncio.run(self._store_batch_async(items))

    async def _store_batch_async(self, items: list[tuple[str, list[float], dict | None]]) -> None:
        await self._ensure_pool()
        async with self._pool.acquire() as conn:
            async with conn.transaction():
                for key, vector, metadata in items:
                    await conn.execute(
                        "INSERT INTO vec_embeddings (key, embedding, metadata) "
                        "VALUES ($1, $2::vector, $3::jsonb) "
                        "ON CONFLICT (key) DO UPDATE SET embedding = $2::vector, metadata = $3::jsonb",
                        key, vector, metadata or {},
                    )

    def search(self, vector: list[float], top_k: int = 10, filters: dict | None = None) -> list[SearchResult]:
        if len(vector) != self._dim:
            raise DimensionMismatchError(f"Vector length {len(vector)} does not match expected {self._dim}")
        import asyncio
        return asyncio.run(self._search_async(vector, top_k, filters))

    async def _search_async(self, vector: list[float], top_k: int, filters: dict | None) -> list[SearchResult]:
        await self._ensure_pool()
        async with self._pool.acquire() as conn:
            if filters:
                rows = await conn.fetch(
                    "SELECT key, embedding, metadata, "
                    "  embedding <=> $1::vector AS score "
                    "FROM vec_embeddings "
                    "WHERE TRUE " + "".join(
                    f" AND metadata->>'{k}' = ${i + 2}" for i, k in enumerate(filters)
                    ) + " "
                    "ORDER BY embedding <=> $1::vector "
                    "LIMIT $2",
                    vector, top_k, *[str(v) for v in filters.values()],
                )
            else:
                rows = await conn.fetch(
                    "SELECT key, embedding, metadata, "
                    "  embedding <=> $1::vector AS score "
                    "FROM vec_embeddings "
                    "ORDER BY embedding <=> $1::vector "
                    "LIMIT $2",
                    vector, top_k,
                )
            return [
                SearchResult(key=row["key"], score=float(row["score"]), metadata=dict(row["metadata"]))
                for row in rows
            ]

    def delete(self, key: str) -> None:
        import asyncio
        asyncio.run(self._delete_async(key))

    async def _delete_async(self, key: str) -> None:
        await self._ensure_pool()
        async with self._pool.acquire() as conn:
            result = await conn.execute("DELETE FROM vec_embeddings WHERE key = $1", key)
            if result == "DELETE 0":
                raise KeyError(f"Key {key} not found")

    def count(self) -> int:
        import asyncio
        return asyncio.run(self._count_async())

    async def _count_async(self) -> int:
        await self._ensure_pool()
        async with self._pool.acquire() as conn:
            row = await conn.fetchval("SELECT COUNT(*) FROM vec_embeddings")
            return row or 0

    def clear(self) -> None:
        import asyncio
        asyncio.run(self._clear_async())

    async def _clear_async(self) -> None:
        await self._ensure_pool()
        async with self._pool.acquire() as conn:
            await conn.execute("TRUNCATE TABLE vec_embeddings")
