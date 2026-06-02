"""Integration tests for Settings and factory wiring."""
from __future__ import annotations

import os
import pytest
from embedding_mcp.config.settings import Settings
from embedding_mcp.vector_db.factory import create_vector_db


class TestConfigIntegration:
    def test_settings_with_env_override(self, monkeypatch):
        monkeypatch.setenv("EMBEDDING_MODEL", "e5-base")
        monkeypatch.setenv("EMBEDDING_DIM", "768")
        settings = Settings()
        assert settings.embedding_model == "e5-base"
        assert settings.embedding_dim == 768

    def test_settings_from_dotenv(self, tmp_path, monkeypatch):
        env_file = tmp_path / ".env"
        env_file.write_text(
            "EMBEDDING_MODEL=e5-base\n"
            "EMBEDDING_DIM=768\n"
            "VEC_DB_TYPE=faiss\n"
        )
        monkeypatch.chdir(tmp_path)
        settings = Settings(_env_file=str(env_file))
        assert settings.embedding_model == "e5-base"
        assert settings.embedding_dim == 768
        assert settings.vec_db_type == "faiss"

    def test_factory_with_real_settings(self, tmp_path):
        settings = Settings(
            embedding_model="e5-small",
            embedding_dim=384,
            vec_db_type="faiss",
            vec_db_path=str(tmp_path / "vectors"),
        )
        db = create_vector_db(
            db_type=settings.vec_db_type,
            db_path=settings.vec_db_path,
            dim=settings.embedding_dim,
        )
        assert db.dim == 384
        assert db.count() == 0
        db.store("test_key", [0.1] * 384, {"src": "factory_test"})
        assert db.count() == 1

    def test_invalid_env_values(self, monkeypatch):
        monkeypatch.setenv("EMBEDDING_MODEL", "invalid-model")
        with pytest.raises(ValueError, match="Unsupported model"):
            Settings()

        monkeypatch.setenv("EMBEDDING_MODEL", "e5-small")
        monkeypatch.setenv("VEC_DB_TYPE", "nonexistent-db")
        with pytest.raises(ValueError, match="Unsupported vector DB"):
            Settings()

    def test_dimension_validation(self, monkeypatch):
        monkeypatch.setenv("EMBEDDING_MODEL", "e5-base")
        monkeypatch.setenv("EMBEDDING_DIM", "384")
        with pytest.raises(ValueError, match="requires dim=768"):
            Settings()
