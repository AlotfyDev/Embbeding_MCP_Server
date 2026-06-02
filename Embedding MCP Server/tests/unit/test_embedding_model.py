"""Tests for EmbeddingModel interface using MockEmbeddingModel."""
from __future__ import annotations

import pytest


class TestEmbeddingModel:
    def test_embed_returns_list_of_floats(self, mock_model):
        vec = mock_model.embed("hello world")
        assert isinstance(vec, list)
        assert len(vec) == mock_model.dim
        assert all(isinstance(v, float) for v in vec)

    def test_embed_batch_returns_correct_count(self, mock_model):
        texts = ["hello", "world", "foo", "bar"]
        results = mock_model.embed_batch(texts)
        assert len(results) == 4
        for r in results:
            assert len(r) == mock_model.dim

    def test_embed_query_differs_from_embed(self, mock_model):
        doc_vec = mock_model.embed("test query")
        query_vec = mock_model.embed_query("test query")
        assert doc_vec != query_vec

    def test_dim_property(self, mock_model):
        assert mock_model.dim == 384

    def test_embed_empty_string(self, mock_model):
        vec = mock_model.embed("")
        assert isinstance(vec, list)
        assert len(vec) == mock_model.dim

    def test_embed_batch_empty_list(self, mock_model):
        results = mock_model.embed_batch([])
        assert results == []

    def test_embed_batch_tracks_calls(self, mock_model):
        texts = ["doc1", "doc2"]
        mock_model.embed_batch(texts)
        assert mock_model.embed_batch_calls == [["doc1", "doc2"]]
