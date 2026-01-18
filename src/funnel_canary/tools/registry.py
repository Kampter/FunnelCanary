"""Tool registry for managing and accessing tools."""

from typing import Any

from .base import Tool, ToolResult


class ExecutionResult:
    """Result of a tool execution via registry.

    Wraps the content string and optional ToolResult for provenance.
    """

    def __init__(
        self,
        content: str,
        tool_result: ToolResult | None = None,
        success: bool = True,
    ):
        self.content = content
        self.tool_result = tool_result
        self.success = success

    @property
    def observation(self):
        """Get the observation from the tool result."""
        return self.tool_result.observation if self.tool_result else None


class ToolRegistry:
    """Registry for managing tools.

    Supports:
    - Tool registration by category
    - Tool lookup by name
    - Filtering tools by skill binding
    - Converting to OpenAI schema
    - Provenance tracking via ToolResult
    """

    def __init__(self) -> None:
        self._tools: dict[str, Tool] = {}
        self._categories: dict[str, list[str]] = {}

    def register(self, tool: Tool) -> None:
        """Register a tool.

        Args:
            tool: Tool instance to register.
        """
        self._tools[tool.name] = tool

        if tool.category not in self._categories:
            self._categories[tool.category] = []
        if tool.name not in self._categories[tool.category]:
            self._categories[tool.category].append(tool.name)

    def get(self, name: str) -> Tool | None:
        """Get a tool by name.

        Args:
            name: Tool name.

        Returns:
            Tool if found, None otherwise.
        """
        return self._tools.get(name)

    def get_by_category(self, category: str) -> list[Tool]:
        """Get all tools in a category.

        Args:
            category: Category name.

        Returns:
            List of tools in the category.
        """
        tool_names = self._categories.get(category, [])
        return [self._tools[name] for name in tool_names]

    def get_for_skill(self, skill_tools: list[str]) -> list[Tool]:
        """Get tools that are bound to a skill.

        Args:
            skill_tools: List of tool names declared by a skill.

        Returns:
            List of matching tools.
        """
        return [
            self._tools[name]
            for name in skill_tools
            if name in self._tools
        ]

    def get_all(self) -> list[Tool]:
        """Get all registered tools.

        Returns:
            List of all tools.
        """
        return list(self._tools.values())

    def execute(self, name: str, arguments: dict[str, Any]) -> ExecutionResult:
        """Execute a tool by name.

        Args:
            name: Tool name.
            arguments: Tool arguments.

        Returns:
            ExecutionResult with content and optional provenance.
        """
        tool = self._tools.get(name)
        if tool is None:
            return ExecutionResult(
                content=f"未知工具: {name}",
                tool_result=None,
                success=False,
            )

        try:
            result = tool.execute(**arguments)

            # Handle both string and ToolResult returns
            if isinstance(result, ToolResult):
                return ExecutionResult(
                    content=result.content,
                    tool_result=result,
                    success=result.success,
                )
            else:
                # Legacy string return - wrap in ExecutionResult without provenance
                return ExecutionResult(
                    content=str(result),
                    tool_result=None,
                    success=True,
                )

        except TypeError as e:
            return ExecutionResult(
                content=f"参数错误: {e}",
                tool_result=ToolResult.from_error(f"参数错误: {e}", name),
                success=False,
            )
        except Exception as e:
            return ExecutionResult(
                content=f"执行错误: {type(e).__name__}: {e}",
                tool_result=ToolResult.from_error(f"{type(e).__name__}: {e}", name),
                success=False,
            )

    def execute_simple(self, name: str, arguments: dict[str, Any]) -> str:
        """Execute a tool and return only the content string.

        Legacy method for backwards compatibility.

        Args:
            name: Tool name.
            arguments: Tool arguments.

        Returns:
            Tool execution result as string.
        """
        result = self.execute(name, arguments)
        return result.content

    def to_openai_schema(self, tools: list[Tool] | None = None) -> list[dict[str, Any]]:
        """Convert tools to OpenAI function calling schema.

        Args:
            tools: Optional list of specific tools. If None, uses all tools.

        Returns:
            List of OpenAI tool schemas.
        """
        if tools is None:
            tools = self.get_all()
        return [tool.to_openai_schema() for tool in tools]

    @property
    def categories(self) -> list[str]:
        """Get all category names."""
        return list(self._categories.keys())

    def __len__(self) -> int:
        return len(self._tools)

    def __contains__(self, name: str) -> bool:
        return name in self._tools
