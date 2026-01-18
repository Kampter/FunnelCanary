"""Base classes for the tool system."""

from dataclasses import dataclass, field
from typing import Any, Callable, Protocol

from ..cognitive.safety import ToolRisk


@dataclass
class ToolParameter:
    """Definition of a tool parameter."""

    name: str
    type: str
    description: str
    required: bool = True


@dataclass
class ToolMetadata:
    """Metadata describing a tool."""

    name: str
    description: str
    category: str
    parameters: list[ToolParameter] = field(default_factory=list)
    skill_bindings: list[str] = field(default_factory=list)
    risk_level: ToolRisk = ToolRisk.SAFE

    def to_openai_schema(self) -> dict[str, Any]:
        """Convert to OpenAI function calling schema."""
        properties = {}
        required = []

        for param in self.parameters:
            properties[param.name] = {
                "type": param.type,
                "description": param.description,
            }
            if param.required:
                required.append(param.name)

        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": properties,
                    "required": required,
                },
            },
        }


class ToolExecutor(Protocol):
    """Protocol for tool execution functions."""

    def __call__(self, **kwargs: Any) -> str: ...


@dataclass
class Tool:
    """A complete tool with metadata and executor."""

    metadata: ToolMetadata
    execute: ToolExecutor

    @property
    def name(self) -> str:
        return self.metadata.name

    @property
    def category(self) -> str:
        return self.metadata.category

    def to_openai_schema(self) -> dict[str, Any]:
        return self.metadata.to_openai_schema()


def tool(
    name: str,
    description: str,
    category: str,
    parameters: list[ToolParameter] | None = None,
    skill_bindings: list[str] | None = None,
    risk_level: ToolRisk = ToolRisk.SAFE,
) -> Callable[[ToolExecutor], Tool]:
    """Decorator to create a tool from a function.

    Usage:
        @tool(
            name="web_search",
            description="Search the web",
            category="web",
            parameters=[ToolParameter("query", "string", "Search query")],
            risk_level=ToolRisk.SAFE,
        )
        def web_search(query: str) -> str:
            ...
    """

    def decorator(func: ToolExecutor) -> Tool:
        metadata = ToolMetadata(
            name=name,
            description=description,
            category=category,
            parameters=parameters or [],
            skill_bindings=skill_bindings or [],
            risk_level=risk_level,
        )
        return Tool(metadata=metadata, execute=func)

    return decorator
