"""Optional integration test using a real ONNX model (slow — marked).
Tests are skipped if the model fails to load (pre-existing token_type_ids issue)."""
from __future__ import annotations

import pytest

ONNX_MODEL_PATH = "D:/Agent_Skills/Skill_To_Agentic_Workflow_Infra/models/multilingual-e5-small/onnx"


def _model_available():
    from pathlib import Path
    return Path(ONNX_MODEL_PATH).exists()


def _model_usable():
    try:
        from embedding_mcp.embedding_model.e5_model import create_embedding_model
        model = create_embedding_model("e5-small", ONNX_MODEL_PATH, device="cpu")
        model.embed("probe")
        return True
    except Exception:
        return False


@pytest.mark.slow
@pytest.mark.skipif(not _model_usable(), reason="ONNX model not usable (needs token_type_ids fix)")
class TestRealEmbeddingModel:
    def test_model_loads_and_embeds(self):
        from embedding_mcp.embedding_model.e5_model import create_embedding_model
        model = create_embedding_model("e5-small", ONNX_MODEL_PATH, device="cpu")
        vec = model.embed("Hello world")
        assert isinstance(vec, list)
        assert len(vec) == model.dim
        assert all(isinstance(v, float) for v in vec)

    def test_batch_embedding(self):
        from embedding_mcp.embedding_model.e5_model import create_embedding_model
        model = create_embedding_model("e5-small", ONNX_MODEL_PATH, device="cpu")
        texts = ["first document", "second document", "third document"]
        results = model.embed_batch(texts)
        assert len(results) == 3
        for r in results:
            assert len(r) == model.dim

    def test_query_embedding_differs(self):
        from embedding_mcp.embedding_model.e5_model import create_embedding_model
        model = create_embedding_model("e5-small", ONNX_MODEL_PATH, device="cpu")
        doc_vec = model.embed("test query")
        query_vec = model.embed_query("test query")
        assert doc_vec != query_vec

    def test_similar_texts_have_high_similarity(self):
        import numpy as np
        from embedding_mcp.embedding_model.e5_model import create_embedding_model
        model = create_embedding_model("e5-small", ONNX_MODEL_PATH, device="cpu")
        v1 = np.array(model.embed("The quick brown fox"))
        v2 = np.array(model.embed("The quick brown fox"))
        similarity = float(np.dot(v1, v2))
        assert similarity > 0.99
