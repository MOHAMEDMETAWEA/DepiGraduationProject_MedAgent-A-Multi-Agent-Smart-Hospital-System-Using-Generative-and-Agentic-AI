from abc import ABC, abstractmethod
from typing import Any

from pydantic import BaseModel


class Tool(ABC):
    @property
    @abstractmethod
    def name(self) -> str:
        """Unique tool name exposed to the LLM."""
        ...

    @property
    @abstractmethod
    def description(self) -> str:
        """Human-readable description of what the tool does."""
        ...

    @property
    @abstractmethod
    def input_schema(self) -> type[BaseModel]:
        """Pydantic model describing expected input fields."""
        ...

    @property
    def output_schema(self) -> type[BaseModel] | None:
        """Pydantic model describing output shape. None if unstructured."""
        return None

    @abstractmethod
    async def run(self, input_data: BaseModel) -> dict[str, Any]:
        """Execute the tool with validated input. Returns result dict."""
        ...
