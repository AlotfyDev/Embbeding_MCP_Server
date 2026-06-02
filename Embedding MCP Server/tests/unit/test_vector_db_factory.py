"""Tests for the Vector DB factory function."""
from __future__ import annotations

from unittest.mock import patch

import pytest

from embedding_mcp.vector_db.factory import create_vector_db


class TestVectorDBFactory:
    def test_create_faiss_adapter(self):
        with patch("embedding_mcp.vector_db.factory.FAISSAdapter") as MockFAISS:
            result = create_vector_db("faiss", "/tmp/test", 384)
        MockFAISS.assert_called_once_with("/tmp/test", 384)
        assert result == MockFAISS.return_value

    def test_create_pgvector_raises_without_conn_str(self):
        """PgVector requires conn_str in kwargs; without it, ValueError."""
        with pytest.raises(ValueError, match="conn_str is required"):
            create_vector_db("pgvector", "/tmp/test", 384)

    def test_create_pgvector_with_conn_str(self):
        with patch("embedding_mcp.vector_db.pgvector_adapter.PgVectorAdapter") as MockPG:
            result = create_vector_db("pgvector", "/tmp/test", 768, conn_str="postgresql://localhost:5432/db")
        MockPG.assert_called_once_with("postgresql://localhost:5432/db", 768)
        assert result == MockPG.return_value

    def test_create_falkordb_adapter(self):
        with patch("embedding_mcp.vector_db.falkordb_adapter.FalkorDBAdapter") as MockFalkor:
            result = create_vector_db("falkordb", "/tmp/test", 384, host="myhost", port=1234)
        MockFalkor.assert_called_once_with(host="myhost", port=1234, dim=384)
        assert result == MockFalkor.return_value

    def test_create_falkordb_defaults(self):
        with patch("embedding_mcp.vector_db.falkordb_adapter.FalkorDBAdapter") as MockFalkor:
            create_vector_db("falkordb", "/tmp/test", 384)
        MockFalkor.assert_called_once_with(host="localhost", port=6379, dim=384)

    def test_create_ladybug_adapter(self):
        with patch("embedding_mcp.vector_db.ladybug_adapter.LadybugAdapter") as MockLadybug:
            result = create_vector_db("ladybug", "/data/test", 384)
        MockLadybug.assert_called_once_with("/data/test", 384)
        assert result == MockLadybug.return_value

    def test_create_kuzu_adapter(self):
        with patch("embedding_mcp.vector_db.kuzudb_adapter.KuzuDBAdapter") as MockKuzu:
            result = create_vector_db("kuzu", "/tmp/kuzu", 768)
        MockKuzu.assert_called_once_with("/tmp/kuzu", 768)
        assert result == MockKuzu.return_value

    def test_unsupported_type_raises(self):
        with pytest.raises(ValueError, match="Unsupported vector DB type"):
            create_vector_db("invalid_type", "/tmp/test", 384)
