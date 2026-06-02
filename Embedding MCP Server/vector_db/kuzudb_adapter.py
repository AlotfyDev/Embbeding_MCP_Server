"""Kùzu vector database adapter - Embedded graph database with vector support."""
from __future__ import annotations

import json
from pathlib import Path

from embedding_mcp.embedding_service.exceptions import DimensionMismatchError
from embedding_mcp.vector_db.base import VectorDB, SearchResult

try:
    import kuzu
except ImportError:
    kuzu = None


class KuzuDBAdapter(VectorDB):
    """Kùzu embedded vector database adapter."""

    def __init__(self, db_path: str, dim: int):
        if kuzu is None:
            raise ImportError("kuzu package is required for KuzuDBAdapter. Install with: pip install kuzu")
        self._dim = dim
        self._db_path = Path(db_path)
        self._db_path.mkdir(parents=True, exist_ok=True)
        self._db = kuzu.Database(str(self._db_path / "kuzu_vec"))
        self._conn = kuzu.Connection(self._db)
        self._init_schema()

    def _init_schema(self) -> None:
        try:
            self._conn.execute(
                f"CREATE NODE TABLE IF NOT EXISTS Embedding("
                f"  key STRING,"
                f"  embedding FLOAT[{self._dim}],"
                f"  metadata JSON,"
                f"  PRIMARY KEY(key)"
                f")"
            )
        except Exception:
            pass  # table already exists

    def _serialize_embedding(self, vector: list[float]) -> str:
        return "[" + ",".join(str(v) for v in vector) + "]"

    def _check_dim(self, vector: list[float]) -> None:
        if len(vector) != self._dim:
            raise DimensionMismatchError(f"Vector length {len(vector)} does not match expected {self._dim}")

    def store(self, key: str, vector: list[float], metadata: dict | None = None) -> None:
        self._check_dim(vector)
        meta_json = json.dumps(metadata or {})
        vec_str = self._serialize_embedding(vector)
        self._conn.execute(
            f"MERGE (e:Embedding {{key: $key}}) "
            f"SET e.embedding = {vec_str}::FLOAT[{self._dim}], e.metadata = '{meta_json}'::JSON",
            params={"key": key},
        )

    def store_batch(self, items: list[tuple[str, list[float], dict | None]]) -> None:
        for key, vector, metadata in items:
            self._check_dim(vector)
        for key, vector, metadata in items:
            self.store(key, vector, metadata)

    def search(self, vector: list[float], top_k: int = 10, filters: dict | None = None) -> list[SearchResult]:
        self._check_dim(vector)
        vec_str = self._serialize_embedding(vector)
        if filters:
            conditions = " AND ".join(
                f"CAST(e.metadata, 'STRING') LIKE '%\"{k}\": \"{v}\"%'" for k, v in filters.items()
            )
            query = (
                f"MATCH (e:Embedding) "
                f"WHERE {conditions} "
                f"RETURN e.key, array_cosine_similarity(e.embedding, {vec_str}::FLOAT[{self._dim}]) AS score, "
                f"  e.metadata "
                f"ORDER BY score DESC "
                f"LIMIT {top_k}"
            )
        else:
            query = (
                f"MATCH (e:Embedding) "
                f"RETURN e.key, array_cosine_similarity(e.embedding, {vec_str}::FLOAT[{self._dim}]) AS score, "
                f"  e.metadata "
                f"ORDER BY score DESC "
                f"LIMIT {top_k}"
            )
        result = self._conn.execute(query)
        results: list[SearchResult] = []
        while result.has_next():
            row = result.get_next()
            key = row[0]
            score = float(row[1])
            meta_raw = row[2]
            meta = json.loads(meta_raw) if isinstance(meta_raw, str) else (meta_raw or {})
            results.append(SearchResult(key=key, score=score, metadata=meta))
        return results

    def delete(self, key: str) -> None:
        self._conn.execute(
            "MATCH (e:Embedding WHERE e.key = $key) DELETE e",
            params={"key": key},
        )

    def count(self) -> int:
        result = self._conn.execute("MATCH (e:Embedding) RETURN COUNT(*) AS cnt")
        if result.has_next():
            return int(result.get_next()[0])
        return 0

    def clear(self) -> None:
        self._conn.execute("MATCH (e:Embedding) DELETE e")
