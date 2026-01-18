"""Context management for FunnelCanary.

Provides:
- ContextManager: Sliding window with automatic summarization
- Summarizer: History compression utilities
"""

from .manager import ContextManager
from .summarizer import Summarizer, create_llm_summarizer

__all__ = [
    "ContextManager",
    "Summarizer",
    "create_llm_summarizer",
]
