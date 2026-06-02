"""Tests for thin MCP handler functions."""
from __future__ import annotations

import json

import pytest

from embedding_mcp.mcp_local.handlers import (
    handle_embed,
    handle_search,
    handle_store,
    handle_store_batch,
    handle_delete,
    handle_count,
    handle_health,
)


class TestHandlers:
    def test_handle_embed(self, service):
        result = handle_embed(service, "hello world")
        data = json.loads(result)
        assert "vector" in data
        assert "dim" in data
        assert data["dim"] == service._model.dim
        assert len(data["vector"]) == data["dim"]

    def test_handle_search(self, service, mock_vec_db):
        dim = service._model.dim
        mock_vec_db.store("doc1", [0.1] * dim, {"text": "hello"})
        result = handle_search(service, "hello", top_k=5)
        data = json.loads(result)
        assert isinstance(data, list)
        assert len(data) >= 1
        assert "key" in data[0]
        assert "score" in data[0]

    def test_handle_search_with_filters(self, service, mock_vec_db):
        dim = service._model.dim
        mock_vec_db.store("a", [0.1] * dim, {"type": "animal"})
        mock_vec_db.store("b", [0.9] * dim, {"type": "plant"})
        result = handle_search(service, "test", filters='{"type": "animal"}')
        data = json.loads(result)
        assert all(r["metadata"]["type"] == "animal" for r in data)

    def test_handle_store(self, service):
        result = handle_store(service, "key1", "some text", '{"source": "test"}')
        data = json.loads(result)
        assert data == {"status": "stored", "key": "key1"}

    def test_handle_store_no_metadata(self, service):
        result = handle_store(service, "key2", "plain text")
        data = json.loads(result)
        assert data["status"] == "stored"
        assert data["key"] == "key2"

    def test_handle_store_batch(self, service):
        items = json.dumps([
            {"text": "doc1", "key": "k1"},
            {"text": "doc2", "key": "k2"},
        ])
        result = handle_store_batch(service, items)
        data = json.loads(result)
        assert data["status"] == "stored"
        assert data["count"] == 2

    def test_handle_delete(self, service, mock_vec_db):
        mock_vec_db.store("del_key", [0.1] * mock_vec_db.dim)
        result = handle_delete(service, "del_key")
        data = json.loads(result)
        assert data == {"status": "deleted", "key": "del_key"}

    def test_handle_count(self, service, mock_vec_db):
        mock_vec_db.store("k", [0.1] * mock_vec_db.dim)
        result = handle_count(service)
        data = json.loads(result)
        assert data == {"count": 1}

    def test_handle_health(self, service):
        result = handle_health(service)
        data = json.loads(result)
        assert "status" in data
        assert "model" in data
        assert "vector_db" in data
