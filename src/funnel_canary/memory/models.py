"""Data models for the memory system."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class Fact:
    """A learned fact stored in memory."""

    content: str
    category: str = "general"
    source: str = "conversation"
    confidence: float = 1.0
    created_at: datetime = field(default_factory=datetime.now)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "content": self.content,
            "category": self.category,
            "source": self.source,
            "confidence": self.confidence,
            "created_at": self.created_at.isoformat(),
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Fact":
        """Create from dictionary."""
        created_at = data.get("created_at")
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at)
        else:
            created_at = datetime.now()

        return cls(
            content=data["content"],
            category=data.get("category", "general"),
            source=data.get("source", "conversation"),
            confidence=data.get("confidence", 1.0),
            created_at=created_at,
            metadata=data.get("metadata", {}),
        )


@dataclass
class UserPreference:
    """A user preference."""

    key: str
    value: Any
    updated_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "key": self.key,
            "value": self.value,
            "updated_at": self.updated_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "UserPreference":
        """Create from dictionary."""
        updated_at = data.get("updated_at")
        if isinstance(updated_at, str):
            updated_at = datetime.fromisoformat(updated_at)
        else:
            updated_at = datetime.now()

        return cls(
            key=data["key"],
            value=data["value"],
            updated_at=updated_at,
        )


@dataclass
class SessionSummary:
    """Summary of a conversation session."""

    session_id: str
    summary: str
    key_topics: list[str] = field(default_factory=list)
    facts_learned: list[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "session_id": self.session_id,
            "summary": self.summary,
            "key_topics": self.key_topics,
            "facts_learned": self.facts_learned,
            "created_at": self.created_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SessionSummary":
        """Create from dictionary."""
        created_at = data.get("created_at")
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at)
        else:
            created_at = datetime.now()

        return cls(
            session_id=data["session_id"],
            summary=data["summary"],
            key_topics=data.get("key_topics", []),
            facts_learned=data.get("facts_learned", []),
            created_at=created_at,
        )
