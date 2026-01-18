"""Prompt builder for assembling modular prompts."""

from typing import TYPE_CHECKING

from .base import (
    BASE_SYSTEM_PROMPT,
    COGNITIVE_CONTEXT_TEMPLATE,
    MEMORY_CONTEXT_TEMPLATE,
    SKILL_CONTEXT_TEMPLATE,
    TOOL_GUIDANCE_TEMPLATE,
)
from .components import (
    CALCULATION_COMPONENT,
    CLARIFICATION_COMPONENT,
    GROUNDING_COMPONENT,
    PROVENANCE_CONTEXT_TEMPLATE,
    RESEARCH_COMPONENT,
    THINKING_COMPONENT,
)
from .output_formats import OUTPUT_FORMATS

if TYPE_CHECKING:
    from ..memory.models import Fact
    from ..provenance import ProvenanceRegistry
    from ..skills.models import Skill
    from ..tools import ToolRegistry


class PromptBuilder:
    """Builder for constructing modular system prompts.

    Assembles prompts from:
    - Base system prompt
    - Prompt components (thinking, clarification, grounding, etc.)
    - Skill-specific instructions
    - Output format templates
    - Memory context
    - Tool descriptions
    - Provenance context (for anti-hallucination)
    """

    def __init__(self) -> None:
        self._components: list[str] = []
        self._skill: "Skill | None" = None
        self._output_format: str = "default"
        self._memory_facts: list["Fact"] = []
        self._tool_descriptions: str = ""
        self._cognitive_context: str = ""
        self._grounding_enabled: bool = False
        self._provenance_context: str = ""

    def with_component(self, component_name: str) -> "PromptBuilder":
        """Add a prompt component.

        Args:
            component_name: One of 'thinking', 'clarification', 'research',
                          'calculation', 'grounding'.

        Returns:
            Self for chaining.
        """
        components_map = {
            "thinking": THINKING_COMPONENT,
            "clarification": CLARIFICATION_COMPONENT,
            "research": RESEARCH_COMPONENT,
            "calculation": CALCULATION_COMPONENT,
            "grounding": GROUNDING_COMPONENT,
        }
        if component_name in components_map:
            self._components.append(components_map[component_name])
        return self

    def with_skill(self, skill: "Skill") -> "PromptBuilder":
        """Add skill-specific instructions.

        Args:
            skill: Loaded skill with full content.

        Returns:
            Self for chaining.
        """
        self._skill = skill
        return self

    def with_output_format(self, format_name: str) -> "PromptBuilder":
        """Set the output format.

        Args:
            format_name: One of 'default', 'research', 'calculation',
                        'decomposition', 'grounded', 'partial', 'refuse'.

        Returns:
            Self for chaining.
        """
        if format_name in OUTPUT_FORMATS:
            self._output_format = format_name
        return self

    def with_memory(self, facts: list["Fact"]) -> "PromptBuilder":
        """Add memory context.

        Args:
            facts: List of relevant facts from memory.

        Returns:
            Self for chaining.
        """
        self._memory_facts = facts
        return self

    def with_tools(self, registry: "ToolRegistry") -> "PromptBuilder":
        """Add tool descriptions from registry.

        Args:
            registry: Tool registry to get descriptions from.

        Returns:
            Self for chaining.
        """
        descriptions = []
        for tool in registry.get_all():
            descriptions.append(f"- {tool.name}: {tool.metadata.description}")
        self._tool_descriptions = "\n".join(descriptions)
        return self

    def with_cognitive_state(self, cognitive_context: str) -> "PromptBuilder":
        """Add cognitive state context.

        Args:
            cognitive_context: Cognitive state context string from CognitiveState.to_context().

        Returns:
            Self for chaining.
        """
        self._cognitive_context = cognitive_context
        return self

    def with_grounding_enforcement(self) -> "PromptBuilder":
        """Enable grounding enforcement for anti-hallucination.

        This adds the grounding component and switches to grounded output format.

        Returns:
            Self for chaining.
        """
        self._grounding_enabled = True
        # Add grounding component if not already added
        if GROUNDING_COMPONENT not in self._components:
            self._components.append(GROUNDING_COMPONENT)
        # Switch to grounded output format
        self._output_format = "grounded"
        return self

    def with_provenance_context(
        self,
        registry: "ProvenanceRegistry",
        max_observations: int = 5
    ) -> "PromptBuilder":
        """Add provenance context from the registry.

        Args:
            registry: ProvenanceRegistry with current observations.
            max_observations: Maximum number of observations to include.

        Returns:
            Self for chaining.
        """
        self._provenance_context = registry.to_context(max_observations)
        return self

    def build(self) -> str:
        """Build the final system prompt.

        Returns:
            Assembled system prompt string.
        """
        parts = [BASE_SYSTEM_PROMPT]

        # Add tool guidance if available
        if self._tool_descriptions:
            parts.append(
                TOOL_GUIDANCE_TEMPLATE.format(tool_descriptions=self._tool_descriptions)
            )

        # Add components
        for component in self._components:
            parts.append(component)

        # Add skill context if available
        if self._skill:
            parts.append(
                SKILL_CONTEXT_TEMPLATE.format(
                    skill_name=self._skill.metadata.name,
                    skill_content=self._skill.content,
                )
            )

        # Add memory context if available
        if self._memory_facts:
            memory_content = "\n".join(
                f"- {fact.content}" for fact in self._memory_facts
            )
            parts.append(MEMORY_CONTEXT_TEMPLATE.format(memory_content=memory_content))

        # Add provenance context if available (for grounding)
        if self._provenance_context:
            parts.append(
                PROVENANCE_CONTEXT_TEMPLATE.format(
                    provenance_context=self._provenance_context
                )
            )

        # Add cognitive context if available
        if self._cognitive_context:
            parts.append(
                COGNITIVE_CONTEXT_TEMPLATE.format(cognitive_context=self._cognitive_context)
            )

        # Add output format
        output_format = OUTPUT_FORMATS.get(self._output_format, OUTPUT_FORMATS["default"])
        parts.append(output_format)

        return "\n".join(parts)

    def reset(self) -> "PromptBuilder":
        """Reset the builder to initial state.

        Returns:
            Self for chaining.
        """
        self._components = []
        self._skill = None
        self._output_format = "default"
        self._memory_facts = []
        self._tool_descriptions = ""
        self._cognitive_context = ""
        self._grounding_enabled = False
        self._provenance_context = ""
        return self
