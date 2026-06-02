"""Thin handlers for embedding MCP tools - no business logic here."""
from __future__ import annotations

import json


def handle_embed(service, text: str) -> str:
    vector = service.embed_text(text)
    return json.dumps({"vector": vector, "dim": len(vector)}, ensure_ascii=False)


def handle_search(service, query: str, top_k: int = 10, filters: str = "{}") -> str:
    parsed_filters = json.loads(filters) if filters else {}
    results = service.search_similar(query, top_k, parsed_filters)
    return json.dumps([r.to_dict() for r in results], ensure_ascii=False)


def handle_store(service, key: str, text: str, metadata: str = "{}") -> str:
    parsed = json.loads(metadata) if metadata != "{}" else {}
    service.embed_document(text, key, parsed)
    return json.dumps({"status": "stored", "key": key}, ensure_ascii=False)


def handle_store_batch(service, items: str) -> str:
    parsed = json.loads(items)
    count = service.embed_batch_documents(parsed)
    return json.dumps({"status": "stored", "count": count}, ensure_ascii=False)


def handle_delete(service, key: str) -> str:
    service.delete_document(key)
    return json.dumps({"status": "deleted", "key": key}, ensure_ascii=False)


def handle_count(service) -> str:
    return json.dumps({"count": service.document_count()}, ensure_ascii=False)


def handle_health(service) -> str:
    return json.dumps(service.health(), ensure_ascii=False)