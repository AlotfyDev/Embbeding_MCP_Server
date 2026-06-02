"""Embedding MCP Local Server - stdio transport for local AI clients.

Usage:
    python -m embedding_mcp.mcp_local [--model-path PATH]
"""
from __future__ import annotations

import argparse
import logging
import signal

from embedding_mcp.config import Settings
from embedding_mcp.model import create_embedding_model
from embedding_mcp.vector_db import create_vector_db
from embedding_mcp.service import EmbeddingService
from embedding_mcp.mcp_local.local_server import build_server

logger = logging.getLogger(__name__)


def run_local_server(
    model_type: str = "e5-small",
    model_path: str = "models/multilingual-e5-small/onnx",
    vec_db_type: str = "faiss",
    vec_db_path: str = "data/vectors",
    device: str = "cpu",
) -> None:
    model = create_embedding_model(model_type, model_path, device)
    vec_db = create_vector_db(vec_db_type, vec_db_path, dim=model.dim)
    service = EmbeddingService(model, vec_db)
    server = build_server(service)
    server.run(transport="stdio")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Embedding MCP Local Server (stdio)"
    )
    parser.add_argument(
        "--model-type",
        default="e5-small",
        help="Model type: e5-small or e5-base (default: e5-small)",
    )
    parser.add_argument(
        "--model-path",
        default="models/multilingual-e5-small/onnx",
        help="Path to ONNX model directory",
    )
    parser.add_argument(
        "--vec-db-type",
        default="faiss",
        help="Vector DB type: faiss (default)",
    )
    parser.add_argument(
        "--vec-db-path",
        default="data/vectors",
        help="Vector DB path (default: data/vectors)",
    )
    parser.add_argument(
        "--device",
        default="cpu",
        choices=["cpu", "cuda"],
        help="Device for inference (default: cpu)",
    )
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO)
    signal.signal(signal.SIGINT, lambda s, f: None)
    signal.signal(signal.SIGTERM, lambda s, f: None)

    run_local_server(
        model_type=args.model_type,
        model_path=args.model_path,
        vec_db_type=args.vec_db_type,
        vec_db_path=args.vec_db_path,
        device=args.device,
    )


if __name__ == "__main__":
    main()