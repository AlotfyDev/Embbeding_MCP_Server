"""Integration tests for MCP Local Server tools — via FastMCP.call_tool."""
from __future__ import annotations

import json
import pytest
from embedding_mcp.mcp_local.local_server import build_server


@pytest.fixture
def test_app(service_with_faiss):
    return build_server(service_with_faiss)


@pytest.mark.asyncio
async def test_embed_text_tool(test_app):
    result = await test_app.call_tool("embed_text", {"text": "test text"})
    data = json.loads(result[0][0].text)
    assert "vector" in data
    assert data["dim"] == 384
    assert len(data["vector"]) == 384


@pytest.mark.asyncio
async def test_store_document_then_search(test_app):
    await test_app.call_tool("store_document", {"key": "k1", "text": "document text", "metadata": "{}"})
    await test_app.call_tool("store_document", {"key": "k2", "text": "another document", "metadata": "{}"})
    result = await test_app.call_tool("search_similar", {"query": "document", "top_k": 5, "filters": "{}"})
    data = json.loads(result[0][0].text)
    assert len(data) > 0
    keys = [r["key"] for r in data]
    assert "k1" in keys or "k2" in keys


@pytest.mark.asyncio
async def test_count_documents(test_app):
    await test_app.call_tool("store_document", {"key": "a", "text": "first", "metadata": "{}"})
    await test_app.call_tool("store_document", {"key": "b", "text": "second", "metadata": "{}"})
    result = await test_app.call_tool("count_documents", {})
    data = json.loads(result[0][0].text)
    assert data["count"] == 2


@pytest.mark.asyncio
async def test_delete_document(test_app):
    await test_app.call_tool("store_document", {"key": "delme", "text": "delete this", "metadata": "{}"})
    result = await test_app.call_tool("count_documents", {})
    assert json.loads(result[0][0].text)["count"] == 1
    await test_app.call_tool("delete_document", {"key": "delme"})
    result = await test_app.call_tool("count_documents", {})
    assert json.loads(result[0][0].text)["count"] == 0


@pytest.mark.asyncio
async def test_store_batch(test_app):
    items = json.dumps([
        {"text": "batch doc 1", "key": "b1", "metadata": {"batch": 1}},
        {"text": "batch doc 2", "key": "b2", "metadata": {"batch": 1}},
        {"text": "batch doc 3", "key": "b3", "metadata": {"batch": 1}},
    ])
    result = await test_app.call_tool("store_batch", {"items": items})
    data = json.loads(result[0][0].text)
    assert data["status"] == "stored"
    assert data["count"] == 3

    result = await test_app.call_tool("count_documents", {})
    assert json.loads(result[0][0].text)["count"] == 3


@pytest.mark.asyncio
async def test_health_tool(test_app):
    result = await test_app.call_tool("health", {})
    data = json.loads(result[0][0].text)
    assert data["status"] == "ok"
    assert "dim=" in data["model"]


@pytest.mark.asyncio
async def test_invalid_input_returns_mcp_error(test_app):
    with pytest.raises(Exception) as excinfo:
        await test_app.call_tool("embed_text", {"text": ""})
    assert "must not be empty" in str(excinfo.value)


@pytest.mark.asyncio
async def test_large_batch_realistic(test_app):
    items = json.dumps([
        {"text": f"bulk document {i}", "key": f"bulk{i}", "metadata": {"idx": i}}
        for i in range(50)
    ])
    result = await test_app.call_tool("store_batch", {"items": items})
    data = json.loads(result[0][0].text)
    assert data["count"] == 50

    result = await test_app.call_tool("count_documents", {})
    assert json.loads(result[0][0].text)["count"] == 50
