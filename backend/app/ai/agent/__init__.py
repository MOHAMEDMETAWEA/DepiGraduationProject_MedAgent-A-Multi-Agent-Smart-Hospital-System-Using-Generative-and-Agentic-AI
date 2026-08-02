"""Agent module — tool registry, agent loop, and base classes."""

from app.ai.agent.base import Tool
from app.ai.agent.registry import ToolRegistry


def make_register_tool(registry: ToolRegistry):

    def decorator(tool_cls: type[Tool]) -> type[Tool]:
        instance = tool_cls()
        registry.register(instance)
        return tool_cls

    return decorator
