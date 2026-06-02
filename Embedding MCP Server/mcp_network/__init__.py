"""MCP Network Server - SSE transport over HTTP for remote AI clients.

Usage:
    python -m embedding_mcp.mcp_network --port 8000
"""
from __future__ import annotations

import argparse
import logging
import signal

from embedding_mcp.config import Settings
from embedding_mcp.model import create_embedding_model
from embedding_mcp.vector_db import create_vector_db
from embedding_mcp.service import EmbeddingService
from embedding_mcp.mcp_network.network_server import create_sse_app
from embedding_mcp.mcp_network.utils.port import find_free_port

logger = logging.getLogger(__name__)


def run_network_server(
    model_type: str = "e5-small",
    model_path: str = "models/multilingual-e5-small/onnx",
    vec_db_type: str = "faiss",
    vec_db_path: str = "data/vectors",
    device: str = "cpu",
    host: str = "127.0.0.1",
    port: int = 8000,
) -> None:
    model = create_embedding_model(model_type, model_path, device)
    vec_db = create_vector_db(vec_db_type, vec_db_path, dim=model.dim)
    service = EmbeddingService(model, vec_db)
    app = create_sse_app(service, host=host, port=port)
    logger.info("Embedding MCP Network server starting on %s:%s", host, port)
    app.run(transport="sse")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Embedding MCP Network Server (SSE)"
    )
    parser.add_argument("--host", default="127.0.0.1", help="Bind address")
    parser.add_argument("--port", type=int, default=8000, help="Bind port; use 0 for OS-assigned")
    parser.add_argument("--model-type", default="e5-small", help="Model type")
    parser.add_argument("--model-path", default="models/multilingual-e5-small/onnx", help="ONNX model path")
    parser.add_argument("--vec-db-type", default="faiss", help="Vector DB type")
    parser.add_argument("--vec-db-path", default="data/vectors", help="Vector DB path")
    parser.add_argument("--device", default="cpu", choices=["cpu", "cuda"], help="Inference device")

    args = parser.parse_args()

    port = args.port
    if port == 0:
        port = find_free_port()
        logger.info("Assigned ephemeral port: %d", port)

    logging.basicConfig(level=logging.INFO)
    signal.signal(signal.SIGINT, lambda s, f: None)
    signal.signal(signal.SIGTERM, lambda s, f: None)

    run_network_server(
        model_type=args.model_type,
        model_path=args.model_path,
        vec_db_type=args.vec_db_type,
        vec_db_path=args.vec_db_path,
        device=args.device,
        host=args.host,
        port=port,
    )


if __name__ == "__main__":
    main()