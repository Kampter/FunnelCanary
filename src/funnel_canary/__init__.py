"""FunnelCanary - AI Agent for closed-loop problem solving.

v0.0.2 Features:
- Skill system with progressive loading
- Context management with sliding window
- Persistent memory across sessions
- Modular prompt building
- Tool registry with categories
"""

from .agent import ProblemSolvingAgent
from .config import Config
from .context import ContextManager, Summarizer
from .memory import Fact, MemoryStore, SessionSummary
from .prompts import PromptBuilder
from .skills import Skill, SkillMetadata, SkillRegistry
from .tools import Tool, ToolMetadata, ToolRegistry, create_default_registry

__version__ = "0.0.2"
__all__ = [
    # Main agent
    "ProblemSolvingAgent",
    # Config
    "Config",
    # Context
    "ContextManager",
    "Summarizer",
    # Memory
    "MemoryStore",
    "Fact",
    "SessionSummary",
    # Prompts
    "PromptBuilder",
    # Skills
    "SkillRegistry",
    "SkillMetadata",
    "Skill",
    # Tools
    "ToolRegistry",
    "Tool",
    "ToolMetadata",
    "create_default_registry",
]
