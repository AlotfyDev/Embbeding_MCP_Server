"""CLI entry point for Embedding MCP Server.

Usage:
    python -m embedding_mcp local [--model-type e5-small] [--model-path PATH] [--vec-db-type faiss] [--vec-db-path PATH] [--device cpu]
    python -m embedding_mcp network [--host 127.0.0.1] [--port 8000] [--model-type e5-small] [--model-path PATH] [--vec-db-type faiss] [--vec-db-path PATH] [--device cpu]
"""
from __future__ import annotations

import argparse
import logging
import signal

from embedding_mcp.mcp_local import run_local_server
from embedding_mcp.mcp_network import run_network_server


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Embedding MCP Server (unified CLI)"
    )
    subparsers = parser.add_subparsers(dest="command", required=True, help="Subcommand")

    local_parser = subparsers.add_parser("local", help="Run local stdio server")
    local_parser.add_argument("--model-type", default="e5-small", help="Model type: e5-small or e5-base")
    local_parser.add_argument("--model-path", default="models/multilingual-e5-small/onnx", help="Path to ONNX model directory")
    local_parser.add_argument("--vec-db-type", default="faiss", help="Vector DB type")
    local_parser.add_argument("--vec-db-path", default="data/vectors", help="Vector DB path")
    local_parser.add_argument("--device", default="cpu", choices=["cpu", "cuda"], help="Device for inference")

    net_parser = subparsers.add_parser("network", help="Run network SSE server")
    net_parser.add_argument("--host", default="127.0.0.1", help="Bind address")
    net_parser.add_argument("--port", type=int, default=8000, help="Bind port; use 0 for OS-assigned")
    net_parser.add_argument("--model-type", default="e5-small", help="Model type")
    net_parser.add_argument("--model-path", default="models/multilingual-e5-small/onnx", help="ONNX model path")
    net_parser.add_argument("--vec-db-type", default="faiss", help="Vector DB type")
    net_parser.add_argument("--vec-db-path", default="data/vectors", help="Vector DB path")
    net_parser.add_argument("--device", default="cpu", choices=["cpu", "cuda"], help="Inference device")

    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO)
    signal.signal(signal.SIGINT, lambda s, f: None)
    signal.signal(signal.SIGTERM, lambda s, f: None)

    if args.command == "local":
        run_local_server(
            model_type=args.model_type,
            model_path=args.model_path,
            vec_db_type=args.vec_db_type,
            vec_db_path=args.vec_db_path,
            device=args.device,
        )
    elif args.command == "network":
        port = args.port
        if port == 0:
            from embedding_mcp.mcp_network.utils.port import find_free_port
            port = find_free_port()
            logging.getLogger(__name__).info("Assigned ephemeral port: %d", port)

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