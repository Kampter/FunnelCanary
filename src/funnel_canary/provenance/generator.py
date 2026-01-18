"""Grounded answer generator for anti-hallucination outputs.

Generates answers with proper provenance tracking and degradation logic
based on the four axioms of the anti-hallucination system.
"""

from dataclasses import dataclass, field

from .models import (
    Claim,
    ClaimType,
    DegradationLevel,
    Observation,
    ProvenanceRegistry,
)


@dataclass
class GroundedAnswer:
    """A grounded answer with full provenance tracking."""

    content: str                            # The answer content
    degradation_level: DegradationLevel     # How much the answer was degraded
    observations_used: list[str] = field(default_factory=list)  # Observation IDs
    claims: list[Claim] = field(default_factory=list)  # Claims in the answer
    high_confidence_parts: list[str] = field(default_factory=list)
    medium_confidence_parts: list[str] = field(default_factory=list)
    low_confidence_parts: list[str] = field(default_factory=list)
    limitations: list[str] = field(default_factory=list)
    suggested_actions: list[str] = field(default_factory=list)

    def to_formatted_output(self) -> str:
        """Generate formatted output string."""
        parts = []

        # Header based on degradation level
        if self.degradation_level == DegradationLevel.FULL_ANSWER:
            parts.append("【完整回答】\n")
        elif self.degradation_level == DegradationLevel.PARTIAL_WITH_UNCERTAINTY:
            parts.append("【部分回答】\n⚠️ 部分信息存在不确定性\n")
        elif self.degradation_level == DegradationLevel.REQUEST_MORE_INFO:
            parts.append("【信息不足】\n❓ 需要更多信息才能完整回答\n")
        else:  # REFUSE
            parts.append("【无法回答】\n❌ 当前没有足够的观测数据\n")

        # Main content
        parts.append(self.content)

        # Confidence breakdown if not full answer
        if self.degradation_level != DegradationLevel.FULL_ANSWER:
            parts.append("\n\n【置信度评估】")

            if self.high_confidence_parts:
                parts.append("\n✅ 高置信度：")
                for p in self.high_confidence_parts:
                    parts.append(f"\n  - {p}")

            if self.medium_confidence_parts:
                parts.append("\n⚠️ 中置信度：")
                for p in self.medium_confidence_parts:
                    parts.append(f"\n  - {p}")

            if self.low_confidence_parts:
                parts.append("\n❓ 低置信度：")
                for p in self.low_confidence_parts:
                    parts.append(f"\n  - {p}")

        # Limitations
        if self.limitations:
            parts.append("\n\n【信息局限性】")
            for lim in self.limitations:
                parts.append(f"\n- {lim}")

        # Suggested actions
        if self.suggested_actions:
            parts.append("\n\n【建议】")
            for action in self.suggested_actions:
                parts.append(f"\n- {action}")

        return "".join(parts)


class GroundedAnswerGenerator:
    """Generates grounded answers with degradation logic.

    Implements Axiom D: Any unverifiable part must be explicitly degraded.

    Degradation decision logic:
    - confidence >= 0.8 and sufficient observations → FULL_ANSWER
    - confidence >= 0.5 and some observations → PARTIAL_WITH_UNCERTAINTY
    - has observations but confidence < 0.5 → REQUEST_MORE_INFO
    - no valid observations → REFUSE
    """

    def __init__(
        self,
        confidence_threshold_full: float = 0.8,
        confidence_threshold_partial: float = 0.5,
        min_observations_for_answer: int = 1,
    ) -> None:
        """Initialize the generator.

        Args:
            confidence_threshold_full: Minimum confidence for full answer.
            confidence_threshold_partial: Minimum confidence for partial answer.
            min_observations_for_answer: Minimum observations needed.
        """
        self.confidence_threshold_full = confidence_threshold_full
        self.confidence_threshold_partial = confidence_threshold_partial
        self.min_observations_for_answer = min_observations_for_answer

    def determine_degradation(
        self,
        registry: ProvenanceRegistry,
    ) -> DegradationLevel:
        """Determine the appropriate degradation level.

        Args:
            registry: ProvenanceRegistry with current observations.

        Returns:
            Appropriate DegradationLevel.
        """
        return registry.determine_degradation_level(
            required_observations=self.min_observations_for_answer,
            min_confidence=self.confidence_threshold_partial,
        )

    def generate(
        self,
        raw_answer: str,
        registry: ProvenanceRegistry,
        claims: list[Claim] | None = None,
    ) -> GroundedAnswer:
        """Generate a grounded answer with provenance.

        Args:
            raw_answer: The raw LLM-generated answer.
            registry: ProvenanceRegistry with observations.
            claims: Optional list of claims in the answer.

        Returns:
            GroundedAnswer with full provenance and degradation.
        """
        claims = claims or []
        degradation_level = self.determine_degradation(registry)

        # Get all valid observations
        valid_obs = registry.get_valid_observations()
        observations_used = [obs.id for obs in valid_obs]

        # Categorize claims by confidence
        high_conf = []
        medium_conf = []
        low_conf = []

        for claim in claims:
            claim.update_confidence(registry.observations)
            if claim.confidence >= 0.8:
                high_conf.append(claim.statement[:100])
            elif claim.confidence >= 0.5:
                medium_conf.append(claim.statement[:100])
            else:
                low_conf.append(claim.statement[:100])

        # Generate limitations
        limitations = self._generate_limitations(registry, valid_obs)

        # Generate suggested actions based on degradation level
        suggested_actions = self._generate_suggestions(degradation_level, registry)

        # Process content based on degradation level
        content = self._process_content(
            raw_answer, degradation_level, registry
        )

        return GroundedAnswer(
            content=content,
            degradation_level=degradation_level,
            observations_used=observations_used,
            claims=claims,
            high_confidence_parts=high_conf,
            medium_confidence_parts=medium_conf,
            low_confidence_parts=low_conf,
            limitations=limitations,
            suggested_actions=suggested_actions,
        )

    def _process_content(
        self,
        raw_answer: str,
        degradation_level: DegradationLevel,
        registry: ProvenanceRegistry,
    ) -> str:
        """Process content based on degradation level."""
        if degradation_level == DegradationLevel.FULL_ANSWER:
            return raw_answer

        elif degradation_level == DegradationLevel.PARTIAL_WITH_UNCERTAINTY:
            # Add uncertainty markers to the content
            return raw_answer + "\n\n⚠️ 注意：以上部分内容基于有限的观测数据，可能存在不确定性。"

        elif degradation_level == DegradationLevel.REQUEST_MORE_INFO:
            return (
                "基于现有观测数据，我只能提供以下有限信息：\n\n"
                + raw_answer
                + "\n\n❓ 需要更多信息才能给出完整回答。"
            )

        else:  # REFUSE
            return (
                "抱歉，我目前没有足够的观测数据来回答这个问题。\n\n"
                "为避免提供不准确的信息，我选择不进行猜测。"
            )

    def _generate_limitations(
        self,
        registry: ProvenanceRegistry,
        valid_obs: list[Observation],
    ) -> list[str]:
        """Generate limitation notes."""
        limitations = []

        # Check for time-sensitive data
        for obs in valid_obs:
            if obs.ttl_seconds:
                remaining = obs.remaining_ttl()
                if remaining is not None and remaining < 1800:  # Less than 30 min
                    limitations.append(
                        f"部分数据（来自{obs.source_id}）即将过期，建议重新获取"
                    )
                    break

        # Check for expired data
        expired = registry.invalidate_expired()
        if expired:
            limitations.append(f"有 {len(expired)} 条观测数据已过期")

        # Check observation coverage
        obs_sources = set(obs.source_id for obs in valid_obs)
        if len(obs_sources) == 1:
            limitations.append("信息仅来自单一来源，建议交叉验证")

        return limitations

    def _generate_suggestions(
        self,
        degradation_level: DegradationLevel,
        registry: ProvenanceRegistry,
    ) -> list[str]:
        """Generate suggested actions based on degradation level."""
        suggestions = []

        if degradation_level == DegradationLevel.REQUEST_MORE_INFO:
            suggestions.append("可以尝试使用 web_search 工具搜索更多相关信息")
            suggestions.append("或者您可以提供更多具体的背景信息")

        elif degradation_level == DegradationLevel.REFUSE:
            suggestions.append("请提供更多关于问题的具体信息")
            suggestions.append("可以尝试将问题分解为更小的、可搜索的部分")

        elif degradation_level == DegradationLevel.PARTIAL_WITH_UNCERTAINTY:
            # Check what might improve confidence
            if registry.get_observation_count() < 3:
                suggestions.append("获取更多相关数据可以提高答案的可信度")

        return suggestions

    def format_provenance_summary(
        self,
        registry: ProvenanceRegistry,
    ) -> str:
        """Generate a summary of provenance for display.

        Args:
            registry: ProvenanceRegistry with observations.

        Returns:
            Formatted provenance summary string.
        """
        valid_obs = registry.get_valid_observations()
        expired_ids = registry.invalidate_expired()

        lines = ["【观测数据摘要】"]

        if valid_obs:
            lines.append(f"有效观测: {len(valid_obs)} 条")
            for obs in valid_obs[:5]:  # Show up to 5
                source_label = obs.source_id
                conf = f"{obs.confidence:.0%}"
                lines.append(f"  - [{obs.id}] {source_label} (置信度: {conf})")
        else:
            lines.append("无有效观测数据")

        if expired_ids:
            lines.append(f"已过期: {len(expired_ids)} 条")

        return "\n".join(lines)
