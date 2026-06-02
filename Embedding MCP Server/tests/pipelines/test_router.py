"""Tests for CapabilityRouter."""
from __future__ import annotations

import pytest

from embedding_mcp.pipelines.base import Pipeline
from embedding_mcp.pipelines.router import CapabilityRouter, UnknownCapabilityError


class MockPipeline:
    """Mock pipeline for testing."""

    def __init__(self, capability: str):
        self.capability = capability
        self.version = "1.0"

    def execute(self, **params):
        return {"capability": self.capability, "params": params}


class TestCapabilityRouter:
    """Test CapabilityRouter operations."""

    def test_register_and_route(self):
        router = CapabilityRouter()
        pipeline = MockPipeline("test.capability")
        router.register(pipeline)

        result = router.route("test.capability", foo="bar")
        assert result["capability"] == "test.capability"
        assert result["params"]["foo"] == "bar"

    def test_unknown_capability(self):
        router = CapabilityRouter()
        with pytest.raises(UnknownCapabilityError) as exc:
            router.route("unknown.capability")

        assert "Unknown capability" in str(exc.value)

    def test_unregister(self):
        router = CapabilityRouter()
        pipeline = MockPipeline("test.capability")
        router.register(pipeline)
        router.unregister("test.capability")

        with pytest.raises(UnknownCapabilityError):
            router.route("test.capability")

    def test_capabilities_list(self):
        router = CapabilityRouter()
        router.register(MockPipeline("cap.a"))
        router.register(MockPipeline("cap.b"))

        assert set(router.capabilities) == {"cap.a", "cap.b"}

    def test_duplicate_registration(self):
        router = CapabilityRouter()
        router.register(MockPipeline("test"))
        with pytest.raises(ValueError):
            router.register(MockPipeline("test"))