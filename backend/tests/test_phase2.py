"""Core tests for Phase 2 — Tool ABC, Registry, and Agent."""

from typing import Any

import pytest
from app.ai.agent.agent import AgentEvent
from app.ai.agent.base import Tool
from app.ai.agent.registry import ToolRegistry
from pydantic import BaseModel, Field

# ── Dummy tool for testing ──


class DummyInput(BaseModel):
    query: str = Field(min_length=1)


class DummyTool(Tool):
    """A test tool that echoes back the query."""

    @property
    def name(self) -> str:
        return "dummy_tool"

    @property
    def description(self) -> str:
        return "Echoes the query back"

    @property
    def input_schema(self) -> type[BaseModel]:
        return DummyInput

    @property
    def output_schema(self) -> type[BaseModel] | None:
        return None

    async def run(self, input_data: BaseModel) -> dict[str, Any]:
        if not isinstance(input_data, DummyInput):
            raise TypeError("Expected DummyInput")
        return {"echo": input_data.query, "status": "ok"}


# ── Tests ──


class TestToolABC:
    """Verify Tool abstract base class works correctly."""

    def test_tool_has_required_properties(self):
        tool = DummyTool()
        assert tool.name == "dummy_tool"
        assert tool.description == "Echoes the query back"
        assert tool.input_schema == DummyInput
        assert tool.output_schema is None

    @pytest.mark.asyncio(loop_scope="session")
    async def test_tool_run(self):
        tool = DummyTool()
        result = await tool.run(DummyInput(query="test query"))
        assert result["echo"] == "test query"
        assert result["status"] == "ok"

    def test_tool_type_check(self):
        tool = DummyTool()
        with pytest.raises(TypeError):
            import asyncio

            asyncio.run(tool.run("not a BaseModel"))


class TestToolRegistry:
    """Verify ToolRegistry register, list, get, to_openai_schema."""

    def test_register_and_get(self):
        registry = ToolRegistry()
        tool = DummyTool()
        registry.register(tool)
        assert registry.get("dummy_tool") is tool
        assert registry.get("nonexistent") is None

    def test_list(self):
        registry = ToolRegistry()
        registry.register(DummyTool())
        assert len(registry.list_all()) == 1

    def test_to_openai_schema(self):
        registry = ToolRegistry()
        registry.register(DummyTool())
        schemas = registry.to_openai_schema()
        assert len(schemas) == 1
        func = schemas[0]
        assert func["type"] == "function"
        assert func["function"]["name"] == "dummy_tool"
        assert "parameters" in func["function"]


class TestAgentEvent:
    """Verify AgentEvent serialization."""

    def test_event_serialization(self):
        event = AgentEvent(type="token", content="Hello")
        d = event.model_dump()
        assert d["type"] == "token"
        assert d["content"] == "Hello"
        assert d["data"] == {}

    def test_event_with_data(self):
        event = AgentEvent(
            type="triage",
            data={"level": "urgent", "score": 72},
        )
        d = event.model_dump()
        assert d["data"]["level"] == "urgent"
