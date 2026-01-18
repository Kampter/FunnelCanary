"""Skill registry for discovery and management."""

from pathlib import Path

from .loader import load_full_skill, load_skill_metadata
from .models import Skill, SkillMetadata


class SkillRegistry:
    """Registry for discovering and loading skills.

    Implements progressive disclosure:
    - Level 1: Metadata loaded at startup (lightweight)
    - Level 2: Full content loaded on demand
    - Level 3: Resources loaded on demand
    """

    def __init__(self, skills_dir: Path | str | None = None) -> None:
        """Initialize the registry.

        Args:
            skills_dir: Directory containing skill definitions.
                        If None, uses default 'skills' directory.
        """
        if skills_dir is None:
            # Default to 'skills' directory relative to project root
            self._skills_dir = Path(__file__).parent.parent.parent.parent / "skills"
        else:
            self._skills_dir = Path(skills_dir)

        self._metadata_cache: dict[str, SkillMetadata] = {}
        self._skill_cache: dict[str, Skill] = {}

    def discover_skills(self) -> list[SkillMetadata]:
        """Scan and load skill metadata from disk.

        Only loads YAML frontmatter, not full content.

        Returns:
            List of discovered skill metadata.
        """
        self._metadata_cache.clear()

        if not self._skills_dir.exists():
            return []

        for skill_dir in self._skills_dir.iterdir():
            if not skill_dir.is_dir():
                continue

            skill_file = skill_dir / "SKILL.md"
            if not skill_file.exists():
                continue

            metadata = load_skill_metadata(skill_file)
            if metadata:
                self._metadata_cache[metadata.name] = metadata

        return list(self._metadata_cache.values())

    def match_skill(self, problem: str) -> SkillMetadata | None:
        """Find a skill that matches the given problem.

        Args:
            problem: Problem statement to match.

        Returns:
            Matching SkillMetadata or None.
        """
        for metadata in self._metadata_cache.values():
            if metadata.matches(problem):
                return metadata
        return None

    def get_metadata(self, name: str) -> SkillMetadata | None:
        """Get skill metadata by name.

        Args:
            name: Skill name.

        Returns:
            SkillMetadata or None.
        """
        return self._metadata_cache.get(name)

    def load_full_skill(self, name: str) -> Skill | None:
        """Load the complete skill with content and resources.

        Uses caching to avoid repeated file reads.

        Args:
            name: Skill name.

        Returns:
            Full Skill or None.
        """
        # Check cache first
        if name in self._skill_cache:
            return self._skill_cache[name]

        # Get metadata
        metadata = self._metadata_cache.get(name)
        if not metadata:
            return None

        # Load full skill
        skill_path = Path(metadata.path)
        skill = load_full_skill(skill_path)

        if skill:
            self._skill_cache[name] = skill

        return skill

    def get_all_metadata(self) -> list[SkillMetadata]:
        """Get all discovered skill metadata.

        Returns:
            List of all skill metadata.
        """
        return list(self._metadata_cache.values())

    def clear_cache(self) -> None:
        """Clear all caches."""
        self._metadata_cache.clear()
        self._skill_cache.clear()

    @property
    def skills_dir(self) -> Path:
        """Get the skills directory path."""
        return self._skills_dir

    def __len__(self) -> int:
        return len(self._metadata_cache)

    def __contains__(self, name: str) -> bool:
        return name in self._metadata_cache
