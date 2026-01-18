"""Cognitive state tracking for agent decision making."""

from dataclasses import dataclass, field
from typing import Any


@dataclass
class UncertaintyZone:
    """Represents an area of uncertainty in the problem understanding."""

    category: str  # "goal_clarity", "data_sufficiency", "solution_viability"
    description: str
    severity: float = 0.5  # 0.0 (minor) to 1.0 (critical)

    def __str__(self) -> str:
        return f"{self.category}: {self.description}"


@dataclass
class CognitiveState:
    """
    Simplified cognitive state tracking for human-like decision making.

    Follows the principle of minimal tracking - only essential fields
    to enable strategy branching without over-engineering.

    v0.0.4: Added observation tracking for provenance-aware decisions.
    """

    # Core confidence tracking
    confidence: float = 0.0  # Overall confidence [0.0, 1.0]

    # Uncertainty tracking (simplified to string list)
    uncertainties: list[str] = field(default_factory=list)

    # Progress tracking
    iteration_count: int = 0
    stall_count: int = 0  # Consecutive iterations without progress

    # Last action tracking (for stall detection)
    last_action_type: str = ""
    last_tool_used: str = ""

    # Problem understanding
    goal_statement: str = ""
    current_hypothesis: str = ""

    # Observation tracking (v0.0.4)
    observation_count: int = 0
    observation_confidence_sum: float = 0.0
    has_tool_observations: bool = False

    def update_confidence(self, new_confidence: float) -> None:
        """Update overall confidence level."""
        self.confidence = max(0.0, min(1.0, new_confidence))

    def add_uncertainty(self, uncertainty: str) -> None:
        """Add a new uncertainty area."""
        if uncertainty not in self.uncertainties:
            self.uncertainties.append(uncertainty)

    def remove_uncertainty(self, uncertainty: str) -> None:
        """Remove a resolved uncertainty."""
        if uncertainty in self.uncertainties:
            self.uncertainties.remove(uncertainty)

    def increment_iteration(self) -> None:
        """Increment iteration counter."""
        self.iteration_count += 1

    def mark_progress(self) -> None:
        """Mark that progress was made, reset stall counter."""
        self.stall_count = 0

    def mark_stall(self) -> None:
        """Mark that no progress was made, increment stall counter."""
        self.stall_count += 1

    def has_stalled(self, threshold: int = 3) -> bool:
        """Check if agent has stalled for too many iterations."""
        return self.stall_count >= threshold

    def record_observation(self, confidence: float) -> None:
        """Record a new observation (v0.0.4).

        Args:
            confidence: Confidence level of the observation.
        """
        self.observation_count += 1
        self.observation_confidence_sum += confidence
        self.has_tool_observations = True

    def get_average_observation_confidence(self) -> float:
        """Get average confidence of recorded observations."""
        if self.observation_count == 0:
            return 0.0
        return self.observation_confidence_sum / self.observation_count

    def to_context(self) -> str:
        """
        Generate cognitive context for prompt injection.
        Strictly controlled to ~100 tokens max.
        """
        lines = []

        if self.confidence < 0.5:
            lines.append(f"当前置信度较低 ({self.confidence:.0%})")

        if self.uncertainties:
            # Only show first 2 uncertainties
            uncertainties_str = ", ".join(self.uncertainties[:2])
            lines.append(f"不确定区域: {uncertainties_str}")

        if self.stall_count >= 2:
            lines.append("进展缓慢，考虑切换策略")

        # v0.0.4: Add observation status
        if self.observation_count == 0 and self.iteration_count > 0:
            lines.append("注意：尚未获取任何观测数据")
        elif self.observation_count > 0:
            avg_conf = self.get_average_observation_confidence()
            if avg_conf < 0.6:
                lines.append(f"观测数据置信度较低 ({avg_conf:.0%})")

        return "\n".join(lines) if lines else ""

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "confidence": self.confidence,
            "uncertainties": self.uncertainties,
            "iteration_count": self.iteration_count,
            "stall_count": self.stall_count,
            "goal_statement": self.goal_statement,
            "observation_count": self.observation_count,
            "average_observation_confidence": self.get_average_observation_confidence(),
        }
