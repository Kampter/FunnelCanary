"""Modular prompt system for FunnelCanary.

This module provides:
- Base system prompts
- Reusable prompt components
- Output format templates
- PromptBuilder for assembling prompts
"""

from .base import (
    BASE_SYSTEM_PROMPT,
    MEMORY_CONTEXT_TEMPLATE,
    SKILL_CONTEXT_TEMPLATE,
    TOOL_GUIDANCE_TEMPLATE,
)
from .builder import PromptBuilder
from .components import (
    CALCULATION_COMPONENT,
    CLARIFICATION_COMPONENT,
    RESEARCH_COMPONENT,
    THINKING_COMPONENT,
)
from .output_formats import OUTPUT_FORMATS

# Legacy export for backward compatibility
SYSTEM_PROMPT = BASE_SYSTEM_PROMPT + OUTPUT_FORMATS["default"]

__all__ = [
    # Builder
    "PromptBuilder",
    # Base
    "BASE_SYSTEM_PROMPT",
    "TOOL_GUIDANCE_TEMPLATE",
    "MEMORY_CONTEXT_TEMPLATE",
    "SKILL_CONTEXT_TEMPLATE",
    # Components
    "THINKING_COMPONENT",
    "CLARIFICATION_COMPONENT",
    "RESEARCH_COMPONENT",
    "CALCULATION_COMPONENT",
    # Output formats
    "OUTPUT_FORMATS",
    # Legacy
    "SYSTEM_PROMPT",
]
