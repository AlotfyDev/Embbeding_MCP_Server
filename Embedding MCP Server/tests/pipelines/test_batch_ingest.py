"""Tests for batch ingest pipeline - chunking, embedding, and storage."""
from __future__ import annotations

import pytest

from embedding_mcp.pipelines.batch_ingest import (
    ChunkingStage,
    BatchEmbedStage,
    BatchStoreStage,
    BatchIngestPipeline,
    create_batch_ingest_pipeline,
)
from embedding_mcp.pipelines.base import StageContext, StageValidationError


class TestChunkingStage:
    """Tests for document chunking stage."""

    def test_chunk_single_short_document(self):
        stage = ChunkingStage(chunk_size=512, chunk_overlap=64)
        ctx = StageContext(input_data={
            "documents": [{"text": "This is a short document."}],
        })
        result = stage.execute(ctx)

        assert len(result.output_data["chunks"]) == 1
        assert result.output_data["chunks"][0]["text"] == "This is a short document."
        assert result.output_data["chunk_count"] == 1

    def test_chunk_long_document(self):
        stage = ChunkingStage(chunk_size=50, chunk_overlap=10)
        ctx = StageContext(input_data={
            "documents": [{"text": "a" * 200}],
        })
        result = stage.execute(ctx)

        chunks = result.output_data["chunks"]
        assert len(chunks) == 5  # With overlap: 50, 40, 40, 40, 40
        assert sum(len(c["text"]) for c in chunks) >= 200

    def test_chunk_respects_overlap(self):
        stage = ChunkingStage(chunk_size=50, chunk_overlap=10)
        text = "a" * 100
        ctx = StageContext(input_data={"documents": [{"text": text}]})
        result = stage.execute(ctx)

        chunks = result.output_data["chunks"]
        assert len(chunks) == 2
        # Verify overlap
        assert chunks[0]["text"][-10:] == chunks[1]["text"][:10]

    def test_chunk_document_with_key(self):
        stage = ChunkingStage(chunk_size=512, chunk_overlap=64)
        ctx = StageContext(input_data={
            "documents": [{"text": "test", "key": "doc1"}],
        })
        result = stage.execute(ctx)

        assert result.output_data["chunks"][0]["key"] == "doc1_chunk_0"

    def test_chunk_multiple_documents(self):
        stage = ChunkingStage(chunk_size=512, chunk_overlap=64)
        ctx = StageContext(input_data={
            "documents": [
                {"text": "doc1", "key": "k1"},
                {"text": "doc2", "key": "k2"},
            ],
        })
        result = stage.execute(ctx)

        assert len(result.output_data["chunks"]) == 2
        assert result.output_data["original_document_count"] == 2

    def test_chunk_with_default_metadata(self):
        stage = ChunkingStage(chunk_size=512, chunk_overlap=64)
        ctx = StageContext(input_data={
            "documents": [{"text": "test", "key": "k1"}],
            "default_metadata": {"source": "api"},
        })
        result = stage.execute(ctx)

        assert result.output_data["chunks"][0]["metadata"]["source"] == "api"

    def test_chunk_validates_missing_documents(self):
        stage = ChunkingStage()
        ctx = StageContext(input_data={})

        with pytest.raises(ValueError, match="No documents"):
            stage.validate(ctx)

    def test_chunk_validates_non_list(self):
        stage = ChunkingStage()
        ctx = StageContext(input_data={"documents": "not a list"})

        with pytest.raises(ValueError, match="must be a list"):
            stage.validate(ctx)


class TestBatchEmbedStage:
    """Tests for batch embedding stage."""

    def test_embed_chunks(self, mock_model):
        stage = BatchEmbedStage(model=mock_model)
        ctx = StageContext(output_data={
            "chunks": [
                {"text": "hello", "key": "k1"},
                {"text": "world", "key": "k2"},
            ],
        })
        result = stage.execute(ctx)

        assert len(result.output_data["embedded_chunks"]) == 2
        assert result.output_data["total_embedded"] == 2
        assert len(result.output_data["embedded_chunks"][0]["vector"]) == mock_model.dim

    def test_embed_validates_missing_model(self):
        stage = BatchEmbedStage()
        ctx = StageContext(output_data={"chunks": []})

        with pytest.raises(ValueError, match="EmbeddingModel not injected"):
            stage.validate(ctx)

    def test_embed_validates_no_chunks(self):
        stage = BatchEmbedStage(model=type('M', (), {'dim': 384})())
        ctx = StageContext(output_data={})

        with pytest.raises(ValueError, match="No chunks to embed"):
            stage.validate(ctx)


class TestBatchStoreStage:
    """Tests for batch storage stage."""

    def test_store_embedded_chunks(self, mock_vec_db):
        stage = BatchStoreStage(vec_db=mock_vec_db)
        ctx = StageContext(output_data={
            "embedded_chunks": [
                {"key": "k1", "vector": [0.1] * 384, "metadata": {"idx": 0}},
                {"key": "k2", "vector": [0.2] * 384, "metadata": {"idx": 1}},
            ],
        })
        result = stage.execute(ctx)

        assert result.output_data["stored_count"] == 2
        assert result.output_data["status"] == "batch_completed"

    def test_store_validates_missing_vec_db(self):
        stage = BatchStoreStage()
        ctx = StageContext(output_data={"embedded_chunks": []})

        with pytest.raises(ValueError, match="VectorDB not injected"):
            stage.validate(ctx)

    def test_store_validates_no_embedded_chunks(self):
        stage = BatchStoreStage(vec_db=type('DB', (), {'dim': 384})())
        ctx = StageContext(output_data={})

        with pytest.raises(ValueError, match="No embedded chunks"):
            stage.validate(ctx)


class TestBatchIngestPipeline:
    """Tests for complete batch ingest pipeline."""

    def test_pipeline_creates_correct_capability(self):
        pipeline = BatchIngestPipeline()
        assert pipeline.capability == "document.batch_ingest"
        assert len(pipeline.stages) == 3

    def test_pipeline_full_execution(self, mock_model, mock_vec_db):
        pipeline = BatchIngestPipeline(
            embedder=BatchEmbedStage(model=mock_model),
            storer=BatchStoreStage(vec_db=mock_vec_db),
        )
        result = pipeline.execute(
            documents=[{"text": "test document", "key": "test_key"}],
        )

        assert result["status"] == "batch_completed"
        assert result["stored_count"] == 1

    def test_pipeline_empty_documents(self, mock_model, mock_vec_db):
        pipeline = BatchIngestPipeline(
            embedder=BatchEmbedStage(model=mock_model),
            storer=BatchStoreStage(vec_db=mock_vec_db),
        )
        result = pipeline.execute(documents=[])
        assert result["stored_count"] == 0

    def test_factory_creates_pipeline(self, mock_model, mock_vec_db):
        pipeline = create_batch_ingest_pipeline(
            chunk_size=256,
            chunk_overlap=32,
            model=mock_model,
            vec_db=mock_vec_db,
        )
        assert pipeline.capability == "document.batch_ingest"
        assert len(pipeline.stages) == 3


class TestPipelineIntegration:
    """Integration tests for batch ingestion with real components."""

    def test_end_to_end_chunking_to_storage(self, mock_model, mock_vec_db):
        stage = ChunkingStage(chunk_size=100, chunk_overlap=20)
        ctx = StageContext(input_data={
            "documents": [{"text": "a" * 250, "key": "doc1", "metadata": {"type": "test"}}],
        })

        ctx = stage.execute(ctx)
        assert ctx.output_data["chunk_count"] == 3

        embed_stage = BatchEmbedStage(model=mock_model)
        ctx = embed_stage.execute(ctx)
        assert ctx.output_data["total_embedded"] == 3

        store_stage = BatchStoreStage(vec_db=mock_vec_db)
        ctx = store_stage.execute(ctx)
        assert ctx.output_data["stored_count"] == 3
        assert mock_vec_db.count() == 3

    def test_chunk_metadata_preserved(self, mock_model, mock_vec_db):
        stage = ChunkingStage(chunk_size=100, chunk_overlap=20)
        ctx = StageContext(input_data={
            "documents": [{"text": "test", "key": "k1", "metadata": {"author": "me"}}],
        })

        ctx = stage.execute(ctx)
        embed_stage = BatchEmbedStage(model=mock_model)
        ctx = embed_stage.execute(ctx)

        chunks = ctx.output_data["embedded_chunks"]
        assert chunks[0]["metadata"]["author"] == "me"
        assert chunks[0]["metadata"]["chunk_index"] == 0