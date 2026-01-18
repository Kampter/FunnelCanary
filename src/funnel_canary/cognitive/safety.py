"""Tool safety and minimal commitment policy."""

from enum import Enum, auto


class ToolRisk(Enum):
    """Risk levels for tool execution."""

    SAFE = auto()      # Read-only, no side effects
    LOW = auto()       # Reversible side effects
    MEDIUM = auto()    # Recoverable side effects
    HIGH = auto()      # Irreversible side effects


class MinimalCommitmentPolicy:
    """
    Implements minimal commitment principle:
    - Prefer reversible actions when confidence is low
    - Only execute high-risk actions when confidence is high
    """

    # Confidence thresholds for each risk level
    THRESHOLDS = {
        ToolRisk.SAFE: 0.0,      # Always allowed
        ToolRisk.LOW: 0.3,       # Low confidence OK
        ToolRisk.MEDIUM: 0.5,    # Medium confidence required
        ToolRisk.HIGH: 0.8,      # High confidence required
    }

    def should_proceed(self, risk_level: ToolRisk, confidence: float) -> bool:
        """
        Determine if a tool should be executed given current confidence.

        Args:
            risk_level: The risk level of the tool
            confidence: Current cognitive confidence [0.0, 1.0]

        Returns:
            True if tool execution should proceed
        """
        threshold = self.THRESHOLDS.get(risk_level, 1.0)
        return confidence >= threshold

    def rank_tools(
        self,
        tools: list[tuple[str, ToolRisk]],
        confidence: float,
    ) -> list[str]:
        """
        Rank tools by safety, filtering out those that shouldn't be used.

        Args:
            tools: List of (tool_name, risk_level) tuples
            confidence: Current cognitive confidence

        Returns:
            List of tool names that are safe to use, sorted by safety
        """
        # Filter allowed tools
        allowed = [
            (name, risk)
            for name, risk in tools
            if self.should_proceed(risk, confidence)
        ]

        # Sort by risk level (safest first)
        risk_order = {
            ToolRisk.SAFE: 0,
            ToolRisk.LOW: 1,
            ToolRisk.MEDIUM: 2,
            ToolRisk.HIGH: 3,
        }
        allowed.sort(key=lambda x: risk_order[x[1]])

        return [name for name, _ in allowed]
