"""Ladybug vector database adapter - LadybugDB client."""
from __future__ import annotations

import json
from pathlib import Path

from embedding_mcp.embedding_service.exceptions import DimensionMismatchError
from embedding_mcp.vector_db.base import VectorDB, SearchResult

try:
    from ladybug import LadybugClient
except ImportError:
    LadybugClient = None


class LadybugAdapter(VectorDB):
    """LadybugDB vector database adapter via LadybugClient or lbug.exe."""

    def __init__(self, db_path: str, dim: int):
        self._dim = dim
        self._db_path = Path(db_path)
        self._db_path.mkdir(parents=True, exist_ok=True)
        self._client: LadybugClient | None = None
        if LadybugClient is not None:
            self._client = LadybugClient(str(self._db_path / "vectors.lbug"))
        self._data: dict[str, tuple[list[float], dict]] = {}

    def _check_dim(self, vector: list[float]) -> None:
        if len(vector) != self._dim:
            raise DimensionMismatchError(f"Vector length {len(vector)} does not match expected {self._dim}")

    def store(self, key: str, vector: list[float], metadata: dict | None = None) -> None:
        self._check_dim(vector)
        if self._client is not None:
            self._client.store(key, vector, metadata)
        else:
            self._data[key] = (vector, metadata or {})

    def store_batch(self, items: list[tuple[str, list[float], dict | None]]) -> None:
        for key, vector, metadata in items:
            self._check_dim(vector)
        if self._client is not None:
            for key, vector, metadata in items:
                self._client.store(key, vector, metadata)
        else:
            for key, vector, metadata in items:
                self._data[key] = (vector, metadata or {})

    def search(self, vector: list[float], top_k: int = 10, filters: dict | None = None) -> list[SearchResult]:
        self._check_dim(vector)
        if self._client is not None:
            raw = self._client.search(vector, top_k)
            results = []
            for key, score, meta in raw:
                if filters and not self._matches_filters(meta, filters):
                    continue
                results.append(SearchResult(key=key, score=float(score), metadata=meta))
            return results
        else:
            import numpy as np
            query = np.array(vector, dtype=np.float32)
            scored = []
            for key, (vec, meta) in self._data.items():
                if filters and not self._matches_filters(meta, filters):
                    continue
                score = float(np.dot(query, np.array(vec, dtype=np.float32)))
                scored.append((score, key, meta))
            scored.sort(key=lambda x: x[0], reverse=True)
            return [SearchResult(key=k, score=s, metadata=m) for s, k, m in scored[:top_k]]

    def delete(self, key: str) -> None:
        if self._client is not None:
            self._client.delete(key)
        elif key in self._data:
            del self._data[key]
        else:
            raise KeyError(f"Key {key} not found")

    def count(self) -> int:
        if self._client is not None:
            return self._client.count()
        return len(self._data)

    def clear(self) -> None:
        if self._client is not None:
            self._client.clear()
        self._data.clear()

    def _matches_filters(self, metadata: dict, filters: dict) -> bool:
        for key, value in filters.items():
            if key not in metadata or metadata[key] != value:
                return False
        return True
