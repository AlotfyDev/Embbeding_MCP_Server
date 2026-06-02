"""Batch document ingestion pipeline."""
from __future__ import annotations

from typing import Any

from embedding_mcp.pipelines.base import PipelineStage, StageValidationError, StageContext
from embedding_mcp.pipelines.base import StageValidationError
from embedding_mcp.embedding_model import EmbeddingModel
from embedding_mcp.vector_db.base import VectorDB


class ValidateBatchStage(PipelineStage):
    """Validate batch input parameters."""

    @property
    def name(self) -> str:
        return "validate_input"

    @property
    def description(self) -> str:
        return "Validate batch of documents"

    def __init__(self, max_batch_size: int = 32):
        self._max_batch_size = max_batch_size

    def validate(self, ctx: StageContext) -> bool:
        items = ctx.input_data.get("items")
        if not items:
            raise StageValidationError("items must be provided")
        if not isinstance(items, list):
            raise StageValidationError("items must be an array")
        return True

    def execute(self, ctx: StageContext) -> StageContext:
        items = ctx.input_data.get("items", [])

        if len(items) == 0:
            raise StageValidationError("items array must not be empty")

        if len(items) > self._max_batch_size:
            raise StageValidationError(
                f"batch exceeds max_batch_size={self._max_batch_size}"
            )

        ctx.output_data["items"] = items
        return ctx


class BatchIngestPipeline:
    """Batch document ingestion pipeline.

    Validates, processes, and stores multiple documents.
    """
    capability = "document.ingest.batch"
    version = "1.0"
    description = "Embed and store multiple documents in batch"

    def __init__(self, model: EmbeddingModel, vec_db: VectorDB,
                 max_batch_size: int = 32, schema=None):
        self._model = model
        self._vec_db = vec_db
        self._max_batch_size = max_batch_size
        self._schema = schema

    def execute(self, **params) -> dict:
        """Execute batch ingestion.

        Args:
            items: List of {"key": str, "text": str, "metadata": dict}

        Returns:
            {"status": "stored", "count": int}
        """
        from embedding_mcp.pipelines.stages.validation import ValidateInputStage
        from embedding_mcp.pipelines.stages.embed.passage_embed import PassageEmbedStage

        ctx = StageContext(input_data=params)
        stages: list[PipelineStage] = [
            ValidateBatchStage(self._max_batch_size),
        ]

        if self._schema:
            stages.append(ValidateInputStage(self._schema))

        for stage in stages:
            ctx = stage.execute(ctx)

        items = ctx.output_data.get("items", [])

        # Process and store in chunks
        stored = 0
        for i in range(0, len(items), self._max_batch_size):
            chunk = items[i:i + self._max_batch_size]
            texts = [item.get("text", "") for item in chunk]
            vectors = self._model.embed_batch(texts)
            db_items = []
            for j, item in enumerate(chunk):
                db_items.append((
                    item.get("key"),
                    vectors[j],
                    item.get("metadata")
                ))
            self._vec_db.store_batch(db_items)
            stored += len(db_items)

        return {"status": "stored", "count": stored}