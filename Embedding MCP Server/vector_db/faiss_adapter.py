"""FAISS vector database adapter."""
from __future__ import annotations

import os
import pickle
from pathlib import Path

import faiss
import numpy as np

from embedding_mcp.vector_db.base import VectorDB, SearchResult


class DimensionMismatchError(RuntimeError):
    """Raised when vector dimension doesn't match expected."""
    pass


class FAISSAdapter(VectorDB):
    """FAISS in-memory vector database with disk persistence."""

    def __init__(self, db_path: str, dim: int):
        self._dim = dim
        self._db_path = Path(db_path)
        self._index = faiss.IndexFlatIP(dim)
        self._keys: list[str] = []
        self._metadata: dict[str, dict] = {}
        self._load()

    def store(self, key: str, vector: list[float], metadata: dict | None = None) -> None:
        if len(vector) != self._dim:
            raise DimensionMismatchError(f"Vector length {len(vector)} does not match expected {self._dim}")
        vec = np.array([vector], dtype=np.float32)
        self._index.add(vec)
        self._keys.append(key)
        if metadata:
            self._metadata[key] = metadata
        self._save()

    def store_batch(self, items: list[tuple[str, list[float], dict | None]]) -> None:
        for key, vector, _ in items:
            if len(vector) != self._dim:
                raise DimensionMismatchError(f"Vector length {len(vector)} does not match expected {self._dim}")
        vectors = np.array([v for _, v, _ in items], dtype=np.float32)
        self._index.add(vectors)
        self._keys.extend([k for k, _, _ in items])
        for key, _, metadata in items:
            if metadata:
                self._metadata[key] = metadata
        self._save()

    def search(self, vector: list[float], top_k: int = 10, filters: dict | None = None) -> list[SearchResult]:
        if len(vector) != self._dim:
            raise DimensionMismatchError(f"Vector length {len(vector)} does not match expected {self._dim}")
        vec = np.array([vector], dtype=np.float32)
        scores, indices = self._index.search(vec, top_k)

        results = []
        for score, idx in zip(scores[0], indices[0]):
            if idx == -1:
                continue
            key = self._keys[idx]
            meta = self._metadata.get(key, {})
            if filters and not self._matches_filters(meta, filters):
                continue
            results.append(SearchResult(key=key, score=float(score), metadata=meta))
        return results

    def delete(self, key: str) -> None:
        if key not in self._metadata:
            raise KeyError(f"Key {key} not found")
        idx = self._keys.index(key)
        self._reindex_without(key, idx)

    def count(self) -> int:
        return len(self._keys)

    def clear(self) -> None:
        self._index = faiss.IndexFlatIP(self._dim)
        self._keys.clear()
        self._metadata.clear()
        self._save()

    def _matches_filters(self, metadata: dict, filters: dict) -> bool:
        for key, value in filters.items():
            if key not in metadata or metadata[key] != value:
                return False
        return True

    def _save(self) -> None:
        self._db_path.mkdir(parents=True, exist_ok=True)
        faiss.write_index(self._index, str(self._db_path / "index.faiss"))
        with open(self._db_path / "meta.pkl", "wb") as f:
            pickle.dump({"keys": self._keys, "metadata": self._metadata}, f)

    def _load(self) -> None:
        if (self._db_path / "index.faiss").exists():
            self._index = faiss.read_index(str(self._db_path / "index.faiss"))
            with open(self._db_path / "meta.pkl", "rb") as f:
                data = pickle.load(f)
                self._keys = data.get("keys", [])
                self._metadata = data.get("metadata", {})

    def _reindex_without(self, key_to_remove: str, remove_idx: int) -> None:
        all_vectors = np.vstack([self._index.reconstruct(i) for i in range(self._index.ntotal)])
        all_keys = [k for k in self._keys if k != key_to_remove]
        all_metadata = {k: v for k, v in self._metadata.items() if k != key_to_remove}

        self._index = faiss.IndexFlatIP(self._dim)
        self._index.add(all_vectors)
        self._keys = all_keys
        self._metadata = all_metadata
        self._save()