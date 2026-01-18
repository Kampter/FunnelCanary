"""Data models for the skill system."""

from dataclasses import dataclass, field


@dataclass
class SkillTriggers:
    """Triggers that can activate a skill."""

    keywords: list[str] = field(default_factory=list)

    def matches(self, text: str) -> bool:
        """Check if text matches any trigger keyword.

        Args:
            text: Text to check against triggers.

        Returns:
            True if any keyword is found in text.
        """
        text_lower = text.lower()
        return any(kw.lower() in text_lower for kw in self.keywords)


@dataclass
class SkillMetadata:
    """Metadata for a skill (loaded at startup).

    This is the lightweight representation loaded during discovery.
    """

    name: str
    description: str
    version: str = "1.0"
    tools: list[str] = field(default_factory=list)
    triggers: SkillTriggers = field(default_factory=SkillTriggers)
    resources: list[str] = field(default_factory=list)
    path: str = ""

    def matches(self, problem: str) -> bool:
        """Check if this skill matches a problem.

        Args:
            problem: Problem statement to match against.

        Returns:
            True if the skill should be activated.
        """
        return self.triggers.matches(problem)


@dataclass
class Skill:
    """Full skill with metadata and content.

    This is the complete representation loaded on demand.
    """

    metadata: SkillMetadata
    content: str
    resources_content: dict[str, str] = field(default_factory=dict)

    @property
    def name(self) -> str:
        return self.metadata.name

    @property
    def tools(self) -> list[str]:
        return self.metadata.tools
