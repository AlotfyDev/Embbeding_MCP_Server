"""E5 model implementations using ONNX Runtime."""
from __future__ import annotations

import numpy as np
from typing import Optional

from embedding_mcp.embedding_model import EmbeddingModel


class E5Base(EmbeddingModel):
    """E5 model implementation with ONNX Runtime."""

    _MAX_BATCH_SIZE = 32

    def __init__(self, model_path: str, device: str = "cpu"):
        import onnxruntime as ort
        from transformers import AutoTokenizer

        providers = ["CUDAExecutionProvider", "CPUExecutionProvider"] if device == "cuda" else ["CPUExecutionProvider"]
        self._session = ort.InferenceSession(f"{model_path}/model.onnx", providers=providers)
        self._tokenizer = AutoTokenizer.from_pretrained(model_path)
        self._max_length = 512
        self._prefix_passage = "passage: "
        self._prefix_query = "query: "

    def _encode(self, text: str, prefix: str = "") -> list[float]:
        inputs = self._tokenizer(
            prefix + text,
            max_length=self._max_length,
            padding="max_length",
            truncation=True,
            return_tensors="np",
        )
        outputs = self._session.run(
            None,
            {"input_ids": inputs["input_ids"], "attention_mask": inputs["attention_mask"]},
        )[0]

        mask = inputs["attention_mask"][:, :, np.newaxis]
        embedding = (outputs * mask).sum(axis=1) / mask.sum(axis=1)
        norm = np.linalg.norm(embedding)
        return (embedding / norm).tolist()[0]

    def embed(self, text: str) -> list[float]:
        return self._encode(text, prefix=self._prefix_passage)

    def embed_query(self, text: str) -> list[float]:
        return self._encode(text, prefix=self._prefix_query)

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        results = []
        for i in range(0, len(texts), self._MAX_BATCH_SIZE):
            batch = texts[i : i + self._MAX_BATCH_SIZE]
            results.extend(self._encode_batch(batch))
        return results

    def _encode_batch(self, texts: list[str]) -> list[list[float]]:
        inputs = self._tokenizer(
            [self._prefix_passage + t for t in texts],
            max_length=self._max_length,
            padding="max_length",
            truncation=True,
            return_tensors="np",
        )
        outputs = self._session.run(
            None,
            {"input_ids": inputs["input_ids"], "attention_mask": inputs["attention_mask"]},
        )[0]

        mask = inputs["attention_mask"][:, :, np.newaxis]
        embeddings = (outputs * mask).sum(axis=1) / mask.sum(axis=1)
        norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
        normalized = embeddings / norms
        return normalized.tolist()

    @property
    def dim(self) -> int:
        return 384


class E5Small(E5Base):
    """E5-small variant (384 dimensions, BERT-based)."""

    def __init__(self, model_path: str, device: str = "cpu"):
        super().__init__(model_path, device)
        self._max_length = 512

    @property
    def dim(self) -> int:
        return 384


class E5BaseLarge(E5Base):
    """E5-base variant (768 dimensions, XLM-RoBERTa-based)."""

    def __init__(self, model_path: str, device: str = "cpu"):
        super().__init__(model_path, device)
        self._max_length = 514

    @property
    def dim(self) -> int:
        return 768


def create_embedding_model(model_type: str, model_path: str, device: str = "cpu") -> EmbeddingModel:
    """Create an embedding model based on type."""
    if model_type == "e5-small":
        return E5Small(model_path, device)
    elif model_type == "e5-base":
        return E5BaseLarge(model_path, device)
    else:
        raise ValueError(f"Unsupported model type: {model_type}")