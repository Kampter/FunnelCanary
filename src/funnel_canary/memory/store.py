"""Memory store for persistent storage of facts and preferences."""

import json
from pathlib import Path
from typing import Any

from .models import Fact, SessionSummary, UserPreference


class MemoryStore:
    """Persistent storage for agent memory.

    Stores:
    - Facts learned during conversations
    - User preferences
    - Session summaries
    """

    def __init__(self, base_dir: Path | str | None = None) -> None:
        """Initialize the memory store.

        Args:
            base_dir: Base directory for storage.
                      If None, uses '.funnel_canary/memory' in current directory.
        """
        if base_dir is None:
            self._base_dir = Path.cwd() / ".funnel_canary" / "memory"
        else:
            self._base_dir = Path(base_dir)

        self._facts_file = self._base_dir / "facts.json"
        self._preferences_file = self._base_dir / "preferences.json"
        self._summaries_dir = self._base_dir / "session_summaries"

        # In-memory caches
        self._facts: list[Fact] = []
        self._preferences: dict[str, UserPreference] = {}

        # Ensure directories exist and load data
        self._ensure_directories()
        self._load_data()

    def _ensure_directories(self) -> None:
        """Create necessary directories if they don't exist."""
        self._base_dir.mkdir(parents=True, exist_ok=True)
        self._summaries_dir.mkdir(parents=True, exist_ok=True)

    def _load_data(self) -> None:
        """Load data from disk."""
        # Load facts
        if self._facts_file.exists():
            try:
                data = json.loads(self._facts_file.read_text(encoding="utf-8"))
                self._facts = [Fact.from_dict(f) for f in data]
            except (json.JSONDecodeError, KeyError):
                self._facts = []

        # Load preferences
        if self._preferences_file.exists():
            try:
                data = json.loads(self._preferences_file.read_text(encoding="utf-8"))
                self._preferences = {
                    p["key"]: UserPreference.from_dict(p) for p in data
                }
            except (json.JSONDecodeError, KeyError):
                self._preferences = {}

    def _save_facts(self) -> None:
        """Save facts to disk."""
        data = [f.to_dict() for f in self._facts]
        self._facts_file.write_text(
            json.dumps(data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def _save_preferences(self) -> None:
        """Save preferences to disk."""
        data = [p.to_dict() for p in self._preferences.values()]
        self._preferences_file.write_text(
            json.dumps(data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    # Facts API
    def add_fact(self, fact: Fact) -> None:
        """Add a fact to memory.

        Args:
            fact: Fact to store.
        """
        self._facts.append(fact)
        self._save_facts()

    def get_facts(self, category: str | None = None) -> list[Fact]:
        """Get facts, optionally filtered by category.

        Args:
            category: Optional category filter.

        Returns:
            List of matching facts.
        """
        if category is None:
            return self._facts.copy()
        return [f for f in self._facts if f.category == category]

    def get_relevant_facts(
        self,
        query: str,
        limit: int = 5,
    ) -> list[Fact]:
        """Get facts relevant to a query.

        Uses simple keyword matching. Can be enhanced with embeddings.

        Args:
            query: Query string.
            limit: Maximum number of facts to return.

        Returns:
            List of relevant facts.
        """
        query_lower = query.lower()
        query_words = set(query_lower.split())

        scored_facts = []
        for fact in self._facts:
            fact_words = set(fact.content.lower().split())
            overlap = len(query_words & fact_words)
            if overlap > 0:
                scored_facts.append((overlap, fact))

        # Sort by relevance score
        scored_facts.sort(key=lambda x: x[0], reverse=True)
        return [f for _, f in scored_facts[:limit]]

    def clear_facts(self) -> None:
        """Clear all facts."""
        self._facts = []
        self._save_facts()

    # Preferences API
    def set_preference(self, key: str, value: Any) -> None:
        """Set a user preference.

        Args:
            key: Preference key.
            value: Preference value.
        """
        self._preferences[key] = UserPreference(key=key, value=value)
        self._save_preferences()

    def get_preference(self, key: str, default: Any = None) -> Any:
        """Get a user preference.

        Args:
            key: Preference key.
            default: Default value if not found.

        Returns:
            Preference value or default.
        """
        pref = self._preferences.get(key)
        return pref.value if pref else default

    def get_all_preferences(self) -> dict[str, Any]:
        """Get all preferences.

        Returns:
            Dictionary of all preferences.
        """
        return {k: v.value for k, v in self._preferences.items()}

    # Session summaries API
    def save_session_summary(self, summary: SessionSummary) -> None:
        """Save a session summary.

        Args:
            summary: Session summary to save.
        """
        filename = f"{summary.session_id}.json"
        filepath = self._summaries_dir / filename
        filepath.write_text(
            json.dumps(summary.to_dict(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def get_session_summary(self, session_id: str) -> SessionSummary | None:
        """Get a session summary by ID.

        Args:
            session_id: Session ID.

        Returns:
            SessionSummary or None.
        """
        filepath = self._summaries_dir / f"{session_id}.json"
        if not filepath.exists():
            return None

        try:
            data = json.loads(filepath.read_text(encoding="utf-8"))
            return SessionSummary.from_dict(data)
        except (json.JSONDecodeError, KeyError):
            return None

    def get_recent_summaries(self, limit: int = 5) -> list[SessionSummary]:
        """Get recent session summaries.

        Args:
            limit: Maximum number of summaries.

        Returns:
            List of recent summaries.
        """
        summaries = []
        for filepath in sorted(
            self._summaries_dir.glob("*.json"),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )[:limit]:
            try:
                data = json.loads(filepath.read_text(encoding="utf-8"))
                summaries.append(SessionSummary.from_dict(data))
            except (json.JSONDecodeError, KeyError):
                continue
        return summaries

    def build_memory_context(self, query: str) -> str:
        """Build memory context string for prompt injection.

        Args:
            query: Current query for relevance matching.

        Returns:
            Formatted memory context string.
        """
        parts = []

        # Add relevant facts
        relevant_facts = self.get_relevant_facts(query, limit=3)
        if relevant_facts:
            facts_text = "\n".join(f"- {f.content}" for f in relevant_facts)
            parts.append(f"相关事实：\n{facts_text}")

        # Add preferences if any
        prefs = self.get_all_preferences()
        if prefs:
            prefs_text = "\n".join(f"- {k}: {v}" for k, v in prefs.items())
            parts.append(f"用户偏好：\n{prefs_text}")

        return "\n\n".join(parts) if parts else ""

    @property
    def fact_count(self) -> int:
        """Get the number of stored facts."""
        return len(self._facts)

    @property
    def base_dir(self) -> Path:
        """Get the base directory path."""
        return self._base_dir
