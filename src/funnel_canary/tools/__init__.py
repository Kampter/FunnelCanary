"""Refactored tool system for FunnelCanary.

This module provides a registry-based tool system with:
- Metadata-driven tool definitions
- Category-based organization
- Skill binding support
- OpenAI function calling schema generation
- Provenance tracking via ToolResult
"""

from .base import Tool, ToolMetadata, ToolParameter, ToolResult, tool
from .categories import COMPUTE_TOOLS, INTERACTION_TOOLS, WEB_TOOLS
from .registry import ExecutionResult, ToolRegistry


def create_default_registry() -> ToolRegistry:
    """Create a registry with all default tools.

    Returns:
        ToolRegistry with all built-in tools registered.
    """
    registry = ToolRegistry()

    # Register all category tools
    for tool_instance in WEB_TOOLS:
        registry.register(tool_instance)
    for tool_instance in INTERACTION_TOOLS:
        registry.register(tool_instance)
    for tool_instance in COMPUTE_TOOLS:
        registry.register(tool_instance)

    return registry


__all__ = [
    "Tool",
    "ToolMetadata",
    "ToolParameter",
    "ToolResult",
    "tool",
    "ToolRegistry",
    "ExecutionResult",
    "create_default_registry",
    "WEB_TOOLS",
    "INTERACTION_TOOLS",
    "COMPUTE_TOOLS",
]
