"""Tests for batch and semantic search pipelines."""
from __future__ import annotations

import pytest


class TestBatchIngestPipeline:
    """Tests for batch ingestion pipeline."""

    def test_validate_batch_stage(self):
        from embedding_mcp.pipelines.batch_ingest import ValidateBatchStage
        from embedding_mcp.pipelines.base import StageContext

        stage = ValidateBatchStage(max_batch_size=32)
        ctx = StageContext(input_data={"items": [{"key": "k1", "text": "hello"}]})
        result = stage.execute(ctx)
        assert len(result.output_data.get("items", [])) == 1

    def test_validate_empty_batch(self):
        from embedding_mcp.pipelines.batch_ingest import ValidateBatchStage
        from embedding_mcp.pipelines.base import StageContext, StageValidationError

        stage = ValidateBatchStage(max_batch_size=32)
        ctx = StageContext(input_data={"items": []})
        with pytest.raises(StageValidationError):
            stage.execute(ctx)


class TestSemanticSearchPipeline:
    """Tests for semantic search pipeline."""

    def test_validation_empty_query(self):
        from embedding_mcp.pipelines.semantic_search import SemanticSearchPipeline
        from embedding_mcp.pipelines.base import StageValidationError

        pipeline = SemanticSearchPipeline(
            model=type('M', (), {'embed_query': lambda s, t: [0.1]*384})(),
            vec_db=type('DB', (), {'search': lambda s, v, k, f=None: []})()
        )
        with pytest.raises(StageValidationError):
            pipeline.execute(query="")

    def test_validation_query_too_long(self):
        from embedding_mcp.pipelines.semantic_search import SemanticSearchPipeline
        from embedding_mcp.pipelines.base import StageValidationError

        pipeline = SemanticSearchPipeline(
            model=type('M', (), {'embed_query': lambda s, t: [0.1]*384})(),
            vec_db=type('DB', (), {'search': lambda s, v, k, f=None: []})(),
            max_text_length=100
        )
        with pytest.raises(StageValidationError):
            pipeline.execute(query="a" * 150)


class TestHybridSearchPipeline:
    """Tests for hybrid search pipeline."""

    def test_validation_keywords_required(self):
        from embedding_mcp.pipelines.hybrid_search import HybridSearchPipeline
        from embedding_mcp.pipelines.base import StageValidationError

        pipeline = HybridSearchPipeline(
            model=type('M', (), {'embed_query': lambda s, t: [0.1]*384})(),
            vec_db=type('DB', (), {'search': lambda s, v, k, f=None: []})()
        )
        with pytest.raises(StageValidationError):
            pipeline.execute(query="test", keywords=[])


class TestDocumentComparePipeline:
    """Tests for document comparison pipeline."""

    def test_similarity_computation(self):
        from embedding_mcp.pipelines.doc_compare import DocumentComparePipeline

        model = type('M', (), {
            'embed': lambda s, t: [1.0, 0.0, 0.0],
            'dim': 3
        })()
        pipeline = DocumentComparePipeline(model=model)
        result = pipeline.execute(key_a="same", key_b="same")
        assert result["similarity"] == 1.0

    def test_validation_empty_key(self):
        from embedding_mcp.pipelines.doc_compare import DocumentComparePipeline
        from embedding_mcp.pipelines.base import StageValidationError

        pipeline = DocumentComparePipeline(model=type('M', (), {'embed': lambda s, t: [0.1]*384, 'dim': 384})())
        with pytest.raises(StageValidationError):
            pipeline.execute(key_a="", key_b="test")