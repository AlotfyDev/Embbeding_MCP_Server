"""Embedding stages for document and query processing."""
from embedding_mcp.pipelines.stages.embed.base import EmbedStage
from embedding_mcp.pipelines.stages.embed.passage_embed import PassageEmbedStage
from embedding_mcp.pipelines.stages.embed.query_embed import QueryEmbedStage

__all__ = ["EmbedStage", "PassageEmbedStage", "QueryEmbedStage"]