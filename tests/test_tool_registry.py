import json

import pytest

from backend.tools.registry import ToolRegistry


@pytest.mark.asyncio
async def test_dispatch_raw_returns_structured_result():
    registry = ToolRegistry()

    @registry.register(
        name="structured_tool",
        description="Returns a structured payload",
        parameters={"type": "object", "properties": {}},
    )
    def structured_tool(query: str) -> dict:
        return {"status": "ok", "query": query}

    result = await registry.dispatch_raw("structured_tool", {"query": "计算机"})

    assert result == {"status": "ok", "query": "计算机"}


@pytest.mark.asyncio
async def test_dispatch_preserves_string_boundary_for_agents():
    registry = ToolRegistry()

    @registry.register(
        name="structured_tool",
        description="Returns a structured payload",
        parameters={"type": "object", "properties": {}},
    )
    def structured_tool(query: str) -> dict:
        return {"status": "ok", "query": query}

    result = await registry.dispatch("structured_tool", {"query": "计算机"})

    assert json.loads(result) == {"status": "ok", "query": "计算机"}


@pytest.mark.asyncio
async def test_dispatch_keeps_legacy_string_result_unchanged():
    registry = ToolRegistry()

    @registry.register(
        name="legacy_tool",
        description="Returns a string payload",
        parameters={"type": "object", "properties": {}},
    )
    def legacy_tool() -> str:
        return '{"status":"ok"}'

    assert await registry.dispatch("legacy_tool", {}) == '{"status":"ok"}'


@pytest.mark.asyncio
async def test_dispatch_raw_returns_structured_error_for_unknown_tool():
    registry = ToolRegistry()

    result = await registry.dispatch_raw("missing_tool", {})

    assert result == {"error": "Unknown tool: missing_tool"}
