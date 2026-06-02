"""Shared type aliases for Embedding MCP Server."""
from __future__ import annotations

from typing import Any

Vector = list[float]
BatchVectors = list[list[float]]
Metadata = dict[str, Any]
EmbeddingItem = dict[str, Any]
EmbeddingItems = list[EmbeddingItem]
