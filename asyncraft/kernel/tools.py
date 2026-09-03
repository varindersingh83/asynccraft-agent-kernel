"""Tool registry and typed tool definitions."""

from abc import ABC, abstractmethod
from typing import Any, Callable
from pydantic import BaseModel, Field


class ToolDefinition(BaseModel):
    """Metadata for a tool in the registry."""

    name: str
    description: str
    requires_approval: bool = True
    parameters_schema: dict[str, Any]


class ToolResult(BaseModel):
    """Result of a tool execution."""

    success: bool
    data: dict[str, Any] = Field(default_factory=dict)
    error: str | None = None


class Tool(ABC):
    """Base class for typed tools."""

    @property
    @abstractmethod
    def name(self) -> str:
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        pass

    @property
    def requires_approval(self) -> bool:
        return True

    @abstractmethod
    async def execute(self, **kwargs: Any) -> ToolResult:
        pass

    @abstractmethod
    def preview(self, **kwargs: Any) -> str:
        """Generate human-readable preview of what this tool will do."""
        pass

    def to_definition(self) -> ToolDefinition:
        return ToolDefinition(
            name=self.name,
            description=self.description,
            requires_approval=self.requires_approval,
            parameters_schema={},
        )


class ToolRegistry:
    """Registry of available tools."""

    def __init__(self) -> None:
        self._tools: dict[str, Tool] = {}

    def register(self, tool: Tool) -> None:
        self._tools[tool.name] = tool

    def get(self, name: str) -> Tool | None:
        return self._tools.get(name)

    def list_tools(self) -> list[ToolDefinition]:
        return [tool.to_definition() for tool in self._tools.values()]

    def get_tool_names(self) -> list[str]:
        return list(self._tools.keys())


_global_registry = ToolRegistry()


def get_tool_registry() -> ToolRegistry:
    return _global_registry


def register_tool(tool: Tool) -> None:
    _global_registry.register(tool)
