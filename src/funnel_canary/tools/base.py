"""Base classes for the tool system."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Protocol

from ..cognitive.safety import ToolRisk
from ..provenance import Observation, ObservationType


@dataclass
class ToolParameter:
    """Definition of a tool parameter."""

    name: str
    type: str
    description: str
    required: bool = True


@dataclass
class ToolResult:
    """Result of a tool execution with provenance information.

    Wraps the raw result with an Observation for provenance tracking.
    """

    content: str                    # The raw result content
    observation: Observation        # Provenance observation
    success: bool = True            # Whether execution succeeded
    error_message: str | None = None  # Error message if failed

    @classmethod
    def from_success(
        cls,
        content: str,
        tool_name: str,
        confidence: float = 1.0,
        ttl_seconds: int | None = None,
        scope: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> "ToolResult":
        """Create a successful result with observation."""
        observation = Observation(
            content=content[:500],  # Limit stored content
            source_type=ObservationType.TOOL_RETURN,
            source_id=tool_name,
            timestamp=datetime.now(),
            confidence=confidence,
            scope=scope,
            ttl_seconds=ttl_seconds,
            metadata=metadata or {},
        )
        return cls(content=content, observation=observation, success=True)

    @classmethod
    def from_error(
        cls,
        error_message: str,
        tool_name: str,
    ) -> "ToolResult":
        """Create a failed result with low-confidence observation."""
        observation = Observation(
            content=f"工具执行失败: {error_message}",
            source_type=ObservationType.TOOL_RETURN,
            source_id=tool_name,
            timestamp=datetime.now(),
            confidence=0.0,  # No confidence in failed result
            scope="error",
            metadata={"error": error_message},
        )
        return cls(
            content=error_message,
            observation=observation,
            success=False,
            error_message=error_message,
        )


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
    """Protocol for tool execution functions.

    Tools can return either:
    - str: Legacy simple string result
    - ToolResult: Result with provenance information (v0.0.4)
    """

    def __call__(self, **kwargs: Any) -> str | ToolResult: ...


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
