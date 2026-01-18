"""Skill system for FunnelCanary.

Provides:
- SkillMetadata: Lightweight skill description
- Skill: Full skill with content
- SkillRegistry: Discovery and loading
- Loader utilities for YAML/Markdown parsing
"""

from .loader import load_full_skill, load_skill_metadata, parse_skill_file
from .models import Skill, SkillMetadata, SkillTriggers
from .registry import SkillRegistry

__all__ = [
    "Skill",
    "SkillMetadata",
    "SkillTriggers",
    "SkillRegistry",
    "load_skill_metadata",
    "load_full_skill",
    "parse_skill_file",
]
