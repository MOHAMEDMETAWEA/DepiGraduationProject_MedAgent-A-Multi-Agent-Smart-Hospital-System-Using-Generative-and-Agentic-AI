"""Abstract base for pluggable LLM providers."""

from abc import ABC, abstractmethod
from collections.abc import AsyncGenerator
from typing import Any


class LLMProvider(ABC):
    """Protocol for LLM backends. Implementations handle inference and streaming."""

    @abstractmethod
    async def generate_stream(
        self,
        messages: list[dict[str, str]],
        tools: list[dict[str, Any]] | None = None,
        max_tokens: int = 1024,
        temperature: float = 0.3,
    ) -> AsyncGenerator[dict[str, Any], None]:
        """
        Stream tokens from the LLM one at a time.

        Yields events as dicts:
          {"type": "token", "content": "..."}
          {"type": "tool_call", "name": "...", "args": {...}}
          {"type": "done", "usage": {...}}
        """
        ...

    @abstractmethod
    async def generate(
        self,
        messages: list[dict[str, str]],
        tools: list[dict[str, Any]] | None = None,
        max_tokens: int = 1024,
        temperature: float = 0.3,
    ) -> dict[str, Any]:
        """Non-streaming generation. Returns full response at once.

        Result keys: "content", "tool_calls", "usage".
        """
        ...
