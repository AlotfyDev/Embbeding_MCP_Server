"""Tests for Settings configuration validation."""
from __future__ import annotations

import pytest

from embedding_mcp.config.settings import Settings


class TestConfig:
    def test_default_values(self):
        config = Settings()
        assert config.embedding_model == "e5-small"
        assert config.embedding_dim == 384
        assert config.vec_db_type == "faiss"
        assert config.max_batch_size == 32
        assert config.mcp_transport == "local"

    def test_validate_model_valid(self):
        config = Settings(embedding_model="e5-small")
        assert config.embedding_model == "e5-small"
        config = Settings(embedding_model="e5-base", embedding_dim=768)
        assert config.embedding_model == "e5-base"

    def test_validate_model_invalid_raises(self):
        with pytest.raises(ValueError, match="Unsupported model"):
            Settings(embedding_model="invalid-model")

    def test_validate_vec_db_valid(self):
        for db_type in ("faiss", "pgvector", "falkordb", "ladybug", "kuzu"):
            config = Settings(vec_db_type=db_type)
            assert config.vec_db_type == db_type

    def test_validate_vec_db_invalid_raises(self):
        with pytest.raises(ValueError, match="Unsupported vector DB"):
            Settings(vec_db_type="invalid-db")

    def test_validate_batch_size_out_of_range(self):
        with pytest.raises(ValueError, match="between 1 and 128"):
            Settings(max_batch_size=0)
        with pytest.raises(ValueError, match="between 1 and 128"):
            Settings(max_batch_size=129)

    def test_validate_batch_size_edge(self):
        assert Settings(max_batch_size=1).max_batch_size == 1
        assert Settings(max_batch_size=128).max_batch_size == 128

    def test_validate_text_length_out_of_range(self):
        with pytest.raises(ValueError, match="between 1 and 100000"):
            Settings(max_text_length=0)
        with pytest.raises(ValueError, match="between 1 and 100000"):
            Settings(max_text_length=100001)

    def test_validate_text_length_edge(self):
        assert Settings(max_text_length=1).max_text_length == 1
        assert Settings(max_text_length=100000).max_text_length == 100000

    def test_max_text_length_default(self):
        assert Settings().max_text_length == 5000

    def test_validate_transport_valid(self):
        assert Settings(mcp_transport="local").mcp_transport == "local"
        assert Settings(mcp_transport="network").mcp_transport == "network"

    def test_validate_transport_invalid_raises(self):
        with pytest.raises(ValueError, match="Unsupported transport"):
            Settings(mcp_transport="invalid")

    def test_cross_field_dim_match(self):
        with pytest.raises(ValueError, match="requires dim=384"):
            Settings(embedding_model="e5-small", embedding_dim=768)
        with pytest.raises(ValueError, match="requires dim=768"):
            Settings(embedding_model="e5-base", embedding_dim=384)

    def test_cross_field_dim_match_succeeds(self):
        config = Settings(embedding_model="e5-small", embedding_dim=384)
        assert config.embedding_dim == 384
        config = Settings(embedding_model="e5-base", embedding_dim=768)
        assert config.embedding_dim == 768
