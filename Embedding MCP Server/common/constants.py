"""Shared constants for Embedding MCP Server."""

MAX_TEXT_LENGTH = 5000

DEFAULT_MODEL_TYPES = {"e5-small", "e5-base"}
DEFAULT_VEC_DB_TYPES = {"faiss", "pgvector", "falkordb", "kuzu", "ladybug"}

DEFAULT_MODEL_PATH = "models/multilingual-e5-small/onnx"
DEFAULT_VEC_DB_PATH = "data/vectors"
DEFAULT_DEVICE = "cpu"
