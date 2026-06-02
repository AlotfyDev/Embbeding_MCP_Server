"""FalkorDB vector database adapter - Graph + Vector search."""
from __future__ import annotations

from embedding_mcp.embedding_service.exceptions import DimensionMismatchError
from embedding_mcp.vector_db.base import VectorDB, SearchResult

try:
    from redis import Redis
except ImportError:
    Redis = None


class FalkorDBAdapter(VectorDB):
    """FalkorDB (RedisGraph) vector database adapter."""

    def __init__(self, host: str = "localhost", port: int = 6379, dim: int = 384):
        if Redis is None:
            raise ImportError("redis package is required for FalkorDBAdapter. Install with: pip install redis")
        self._dim = dim
        self._conn = Redis(host=host, port=port, decode_responses=True)
        self._graph_name = "embedding_graph"
        self._init_index()

    def _init_index(self) -> None:
        try:
            self._conn.execute_command(
                "GRAPH.QUERY", self._graph_name,
                f"CREATE VECTOR INDEX FOR (n:Embedding) ON (n.embedding) DIMENSION {self._dim}",
            )
        except Exception:
            pass  # index already exists

    def store(self, key: str, vector: list[float], metadata: dict | None = None) -> None:
        if len(vector) != self._dim:
            raise DimensionMismatchError(f"Vector length {len(vector)} does not match expected {self._dim}")
        import json
        meta_json = json.dumps(metadata or {})
        vec_str = "[" + ",".join(str(v) for v in vector) + "]"
        self._conn.execute_command(
            "GRAPH.QUERY", self._graph_name,
            f"MERGE (n:Embedding {{key: $key}}) "
            f"SET n.embedding = vecf32({vec_str}), n.metadata = '{meta_json}'",
            params={"key": key},
        )

    def store_batch(self, items: list[tuple[str, list[float], dict | None]]) -> None:
        import json
        for key, vector, metadata in items:
            if len(vector) != self._dim:
                raise DimensionMismatchError(f"Vector length {len(vector)} does not match expected {self._dim}")
            meta_json = json.dumps(metadata or {})
            vec_str = "[" + ",".join(str(v) for v in vector) + "]"
            self._conn.execute_command(
                "GRAPH.QUERY", self._graph_name,
                f"MERGE (n:Embedding {{key: $key}}) "
                f"SET n.embedding = vecf32({vec_str}), n.metadata = '{meta_json}'",
                params={"key": key},
            )

    def search(self, vector: list[float], top_k: int = 10, filters: dict | None = None) -> list[SearchResult]:
        if len(vector) != self._dim:
            raise DimensionMismatchError(f"Vector length {len(vector)} does not match expected {self._dim}")
        import json
        vec_str = "[" + ",".join(str(v) for v in vector) + "]"
        if filters:
            conditions = " AND ".join(f"n.metadata =~ '.*\"{k}\":\\s*\"{v}\".*'" for k, v in filters.items())
            query = (
                f"WITH vecf32({vec_str}) AS qv "
                f"CALL db.idx.vector.queryNodes('Embedding', 'embedding', {top_k}, qv) "
                f"YIELD node, score "
                f"WHERE {conditions} "
                f"RETURN node.key AS key, score, node.metadata AS metadata"
            )
        else:
            query = (
                f"WITH vecf32({vec_str}) AS qv "
                f"CALL db.idx.vector.queryNodes('Embedding', 'embedding', {top_k}, qv) "
                f"YIELD node, score "
                f"RETURN node.key AS key, score, node.metadata AS metadata"
            )
        result = self._conn.execute_command("GRAPH.RO_QUERY", self._graph_name, query)
        results: list[SearchResult] = []
        if result and len(result) > 1:
            for row in result[1]:
                if row:
                    key = row[0]
                    score = float(row[1])
                    meta_raw = row[2]
                    meta = json.loads(meta_raw) if isinstance(meta_raw, str) else (meta_raw or {})
                    results.append(SearchResult(key=key, score=score, metadata=meta))
        return results

    def delete(self, key: str) -> None:
        result = self._conn.execute_command(
            "GRAPH.QUERY", self._graph_name,
            "MATCH (n:Embedding {key: $key}) DELETE n",
            params={"key": key},
        )
        if result and len(result) > 1 and result[1] and result[1][0] and result[1][0][0] == 0:
            raise KeyError(f"Key {key} not found")

    def count(self) -> int:
        result = self._conn.execute_command(
            "GRAPH.RO_QUERY", self._graph_name,
            "MATCH (n:Embedding) RETURN COUNT(n) AS cnt",
        )
        if result and len(result) > 1 and result[1]:
            return int(result[1][0][0])
        return 0

    def clear(self) -> None:
        self._conn.execute_command(
            "GRAPH.QUERY", self._graph_name,
            "MATCH (n:Embedding) DELETE n",
        )
