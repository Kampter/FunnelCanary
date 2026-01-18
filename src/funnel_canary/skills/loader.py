"""YAML/Markdown loader for skill definitions."""

import re
from pathlib import Path
from typing import Any

import yaml

from .models import Skill, SkillMetadata, SkillTriggers


def parse_skill_file(content: str) -> tuple[dict[str, Any], str]:
    """Parse a SKILL.md file with YAML frontmatter.

    Args:
        content: File content with YAML frontmatter.

    Returns:
        Tuple of (frontmatter dict, markdown content).
    """
    # Match YAML frontmatter between --- markers
    pattern = r'^---\s*\n(.*?)\n---\s*\n(.*)$'
    match = re.match(pattern, content, re.DOTALL)

    if not match:
        # No frontmatter, treat entire content as markdown
        return {}, content

    yaml_content = match.group(1)
    markdown_content = match.group(2)

    try:
        frontmatter = yaml.safe_load(yaml_content) or {}
    except yaml.YAMLError:
        frontmatter = {}

    return frontmatter, markdown_content


def load_skill_metadata(skill_path: Path) -> SkillMetadata | None:
    """Load skill metadata from a SKILL.md file.

    Only parses the YAML frontmatter, not the full content.

    Args:
        skill_path: Path to SKILL.md file.

    Returns:
        SkillMetadata or None if parsing fails.
    """
    try:
        content = skill_path.read_text(encoding="utf-8")
        frontmatter, _ = parse_skill_file(content)

        if not frontmatter:
            return None

        # Parse triggers
        triggers_data = frontmatter.get("triggers", {})
        triggers = SkillTriggers(
            keywords=triggers_data.get("keywords", []),
        )

        return SkillMetadata(
            name=frontmatter.get("name", skill_path.parent.name),
            description=frontmatter.get("description", ""),
            version=frontmatter.get("version", "1.0"),
            tools=frontmatter.get("tools", []),
            triggers=triggers,
            resources=frontmatter.get("resources", []),
            path=str(skill_path),
        )

    except Exception:
        return None


def load_full_skill(skill_path: Path) -> Skill | None:
    """Load a complete skill including content and resources.

    Args:
        skill_path: Path to SKILL.md file.

    Returns:
        Skill or None if loading fails.
    """
    try:
        content = skill_path.read_text(encoding="utf-8")
        frontmatter, markdown_content = parse_skill_file(content)

        if not frontmatter:
            return None

        # Load metadata
        triggers_data = frontmatter.get("triggers", {})
        triggers = SkillTriggers(
            keywords=triggers_data.get("keywords", []),
        )

        metadata = SkillMetadata(
            name=frontmatter.get("name", skill_path.parent.name),
            description=frontmatter.get("description", ""),
            version=frontmatter.get("version", "1.0"),
            tools=frontmatter.get("tools", []),
            triggers=triggers,
            resources=frontmatter.get("resources", []),
            path=str(skill_path),
        )

        # Load resource files if specified
        resources_content = {}
        skill_dir = skill_path.parent
        for resource_name in metadata.resources:
            resource_path = skill_dir / resource_name
            if resource_path.exists():
                try:
                    resources_content[resource_name] = resource_path.read_text(
                        encoding="utf-8"
                    )
                except Exception:
                    pass

        return Skill(
            metadata=metadata,
            content=markdown_content.strip(),
            resources_content=resources_content,
        )

    except Exception:
        return None
