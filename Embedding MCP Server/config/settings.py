"""Configuration layer using Pydantic BaseSettings.

Priority: environment variables > .env file > defaults.
"""
from __future__ import annotations

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    embedding_model: str = "e5-small"
    embedding_model_path: str = "models/multilingual-e5-small/onnx"
    embedding_device: str = "cpu"
    embedding_dim: int = 384
    max_batch_size: int = 32
    max_text_length: int = 5000

    vec_db_type: str = "faiss"
    vec_db_path: str = "data/vectors"
    pgvector_conn_str: str = ""
    falkordb_host: str = "localhost"
    falkordb_port: int = 6379

    mcp_transport: str = "local"
    mcp_host: str = "0.0.0.0"
    mcp_port: int = 8000

    cache_size: int = 1000
    request_timeout: int = 30

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @field_validator("embedding_model")
    @classmethod
    def validate_model(cls, v: str) -> str:
        allowed = {"e5-small", "e5-base"}
        if v not in allowed:
            raise ValueError(f"Unsupported model '{v}'. Choices: {allowed}")
        return v

    @field_validator("vec_db_type")
    @classmethod
    def validate_vec_db(cls, v: str) -> str:
        allowed = {"faiss", "pgvector", "falkordb", "ladybug", "kuzu"}
        if v not in allowed:
            raise ValueError(f"Unsupported vector DB '{v}'. Choices: {allowed}")
        return v

    @field_validator("mcp_transport")
    @classmethod
    def validate_transport(cls, v: str) -> str:
        allowed = {"local", "network"}
        if v not in allowed:
            raise ValueError(f"Unsupported transport '{v}'. Choices: {allowed}")
        return v

    @field_validator("max_batch_size")
    @classmethod
    def validate_batch(cls, v: int) -> int:
        if v < 1 or v > 128:
            raise ValueError("max_batch_size must be between 1 and 128")
        return v

    @field_validator("max_text_length")
    @classmethod
    def validate_text_length(cls, v: int) -> int:
        if v < 1 or v > 100000:
            raise ValueError("max_text_length must be between 1 and 100000")
        return v

    @model_validator(mode="after")
    def validate_dim_match(self):
        expected = {"e5-small": 384, "e5-base": 768}
        if self.embedding_dim != expected.get(self.embedding_model):
            raise ValueError(
                f"{self.embedding_model} requires dim={expected[self.embedding_model]}"
            )
        return self
