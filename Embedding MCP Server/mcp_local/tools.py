"""Tool definitions for embedding MCP server."""
from __future__ import annotations

TOOL_DEFINITIONS: dict[str, dict] = {
    "embed_text": {
        "description": "Embed text to vector",
        "input_schema": {
            "type": "object",
            "properties": {
                "text": {"type": "string", "description": "Text to embed"}
            },
            "required": ["text"]
        }
    },
    "search_similar": {
        "description": "Semantic search for similar documents",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query text"},
                "top_k": {"type": "integer", "description": "Number of results", "default": 10},
                "filters": {"type": "string", "description": "JSON filters", "default": "{}"}
            },
            "required": ["query"]
        }
    },
    "store_document": {
        "description": "Embed and store a document",
        "input_schema": {
            "type": "object",
            "properties": {
                "key": {"type": "string", "description": "Document key/ID"},
                "text": {"type": "string", "description": "Document text"},
                "metadata": {"type": "string", "description": "JSON metadata", "default": "{}"}
            },
            "required": ["key", "text"]
        }
    },
    "store_batch": {
        "description": "Embed and store multiple documents",
        "input_schema": {
            "type": "object",
            "properties": {
                "items": {"type": "string", "description": "JSON array of {text, key, metadata}"}
            },
            "required": ["items"]
        }
    },
    "delete_document": {
        "description": "Delete a document by key",
        "input_schema": {
            "type": "object",
            "properties": {
                "key": {"type": "string", "description": "Document key to delete"}
            },
            "required": ["key"]
        }
    },
    "count_documents": {
        "description": "Count stored documents",
        "input_schema": {"type": "object", "properties": {}}
    },
    "health": {
        "description": "Check system health",
        "input_schema": {"type": "object", "properties": {}}
    }
}