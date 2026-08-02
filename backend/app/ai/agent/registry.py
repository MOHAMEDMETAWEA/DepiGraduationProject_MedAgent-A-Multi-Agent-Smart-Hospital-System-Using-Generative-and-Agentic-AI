"""Tool registry — collects and exposes tools to the LLM agent."""

from app.ai.agent.base import Tool


class ToolRegistry:
    def __init__(self):

        self._tools: dict[str, Tool] = {}

    def register(self, tool: Tool) -> None:
        """Register a tool instance manually."""
        self._tools[tool.name] = tool

    def list_all(self) -> list[Tool]:
        """Return all registered tools."""
        return list(self._tools.values())

    def get(self, name: str) -> Tool | None:
        """Get a tool by name. Returns None if not found."""
        return self._tools.get(name)

    def to_openai_schema(self) -> list[dict]:

        schemas = []
        for tool in self._tools.values():
            params = tool.input_schema.model_json_schema()

            schemas.append(
                {
                    "type": "function",
                    "function": {
                        "name": tool.name,
                        "description": tool.description,
                        "parameters": params,
                    },
                }
            )
        return schemas
