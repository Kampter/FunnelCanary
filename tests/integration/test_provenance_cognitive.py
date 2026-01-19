"""Integration tests for provenance and cognitive systems.

Tests the interaction between:
- ProvenanceRegistry and CognitiveState
- StrategyGate with provenance information
- Observation-based decision making
"""

from datetime import datetime, timedelta

import pytest

from funnel_canary.cognitive import CognitiveState, MinimalCommitmentPolicy, StrategyGate
from funnel_canary.cognitive.strategy import StrategyDecision
from funnel_canary.provenance import (
    Claim,
    ClaimType,
    DegradationLevel,
    Observation,
    ObservationType,
    ProvenanceRegistry,
)


class TestProvenanceRegistryIntegration:
    """Integration tests for ProvenanceRegistry."""

    @pytest.mark.integration
    def test_registry_add_and_retrieve_observations(self, provenance_registry):
        """Test adding and retrieving observations."""
        obs1 = Observation(
            content="First observation",
            source_type=ObservationType.TOOL_RETURN,
            source_id="web_search",
            confidence=1.0,
        )
        obs2 = Observation(
            content="Second observation",
            source_type=ObservationType.USER_INPUT,
            source_id="user",
        )

        provenance_registry.add_observation(obs1)
        provenance_registry.add_observation(obs2)

        assert provenance_registry.get_observation_count() == 2
        assert provenance_registry.get_observation(obs1.id) is not None
        assert provenance_registry.get_observation(obs2.id) is not None

    @pytest.mark.integration
    def test_expired_observations_filtered(self, provenance_registry):
        """Test that expired observations are filtered out."""
        valid_obs = Observation(
            content="Valid observation",
            source_type=ObservationType.TOOL_RETURN,
            source_id="web_search",
            ttl_seconds=3600,
        )
        expired_obs = Observation(
            content="Expired observation",
            source_type=ObservationType.TOOL_RETURN,
            source_id="web_search",
            ttl_seconds=1,
        )
        # Backdate the expired observation
        expired_obs.timestamp = datetime.now() - timedelta(seconds=10)

        provenance_registry.add_observation(valid_obs)
        provenance_registry.add_observation(expired_obs)

        valid_observations = provenance_registry.get_valid_observations()
        assert len(valid_observations) == 1
        assert valid_observations[0].id == valid_obs.id

    @pytest.mark.integration
    def test_claim_confidence_computation(self, provenance_registry):
        """Test claim confidence based on source observations."""
        obs1 = Observation(
            content="High confidence obs",
            source_type=ObservationType.TOOL_RETURN,
            source_id="web_search",
            confidence=1.0,
        )
        obs2 = Observation(
            content="User input",
            source_type=ObservationType.USER_INPUT,
            source_id="user",
            confidence=0.8,
        )

        provenance_registry.add_observation(obs1)
        provenance_registry.add_observation(obs2)

        claim = Claim(
            statement="Combined claim",
            claim_type=ClaimType.FACT,
            source_observations=[obs1.id, obs2.id],
        )

        provenance_registry.add_claim(claim)

        # Confidence should be minimum of source observations
        assert claim.confidence == 0.8


class TestDegradationLevels:
    """Integration tests for degradation level determination."""

    @pytest.mark.integration
    def test_full_answer_with_high_confidence(self, provenance_registry):
        """High confidence observations should allow full answer."""
        for i in range(3):
            provenance_registry.add_observation(Observation(
                content=f"Observation {i}",
                source_type=ObservationType.TOOL_RETURN,
                source_id="web_search",
                confidence=1.0,
            ))

        level = provenance_registry.determine_degradation_level()
        assert level == DegradationLevel.FULL_ANSWER

    @pytest.mark.integration
    def test_partial_with_medium_confidence(self, provenance_registry):
        """Medium confidence should result in partial answer."""
        provenance_registry.add_observation(Observation(
            content="Medium confidence obs",
            source_type=ObservationType.USER_INPUT,
            source_id="user",
            confidence=0.6,
        ))

        level = provenance_registry.determine_degradation_level()
        assert level == DegradationLevel.PARTIAL_WITH_UNCERTAINTY

    @pytest.mark.integration
    def test_request_more_info_with_low_confidence(self, provenance_registry):
        """Low confidence should request more info."""
        provenance_registry.add_observation(Observation(
            content="Low confidence obs",
            source_type=ObservationType.USER_INPUT,
            source_id="user",
            confidence=0.3,
        ))

        level = provenance_registry.determine_degradation_level(min_confidence=0.5)
        assert level == DegradationLevel.REQUEST_MORE_INFO

    @pytest.mark.integration
    def test_refuse_with_no_observations(self, provenance_registry):
        """No observations should result in refusal."""
        level = provenance_registry.determine_degradation_level()
        assert level == DegradationLevel.REFUSE


class TestCognitiveStateWithProvenance:
    """Integration tests for CognitiveState with provenance tracking."""

    @pytest.mark.integration
    def test_cognitive_state_records_observations(self):
        """Test that CognitiveState can record observations."""
        state = CognitiveState(goal_statement="Test goal")

        state.record_observation(1.0)  # High confidence
        state.record_observation(0.8)  # Medium confidence

        assert state.observation_count == 2
        # Average confidence should influence state
        assert state.get_average_observation_confidence() == 0.9

    @pytest.mark.integration
    def test_strategy_gate_with_provenance(self):
        """Test StrategyGate uses provenance for decisions."""
        state = CognitiveState(goal_statement="Test goal", confidence=0.5)
        gate = StrategyGate(confidence_threshold=0.7)

        registry = ProvenanceRegistry()
        # Add high-confidence observations
        for i in range(3):
            registry.add_observation(Observation(
                content=f"Observation {i}",
                source_type=ObservationType.TOOL_RETURN,
                source_id="web_search",
                confidence=1.0,
            ))

        # Gate should consider provenance
        path = gate.evaluate(state, provenance_registry=registry)

        # With high-confidence observations, should be able to conclude
        assert path.decision in [StrategyDecision.CONTINUE, StrategyDecision.CONCLUDE]


class TestMinimalCommitmentPolicy:
    """Integration tests for MinimalCommitmentPolicy."""

    @pytest.mark.integration
    def test_policy_allows_safe_tools_always(self):
        """Safe tools should be allowed regardless of confidence."""
        from funnel_canary.cognitive.safety import ToolRisk

        policy = MinimalCommitmentPolicy()

        assert policy.should_proceed(ToolRisk.SAFE, 0.0)
        assert policy.should_proceed(ToolRisk.SAFE, 0.5)
        assert policy.should_proceed(ToolRisk.SAFE, 1.0)

    @pytest.mark.integration
    def test_policy_blocks_high_risk_with_low_confidence(self):
        """High risk tools should be blocked with low confidence."""
        from funnel_canary.cognitive.safety import ToolRisk

        policy = MinimalCommitmentPolicy()

        assert not policy.should_proceed(ToolRisk.HIGH, 0.5)
        assert policy.should_proceed(ToolRisk.HIGH, 0.8)

    @pytest.mark.integration
    def test_policy_ranks_tools_by_safety(self):
        """Tools should be ranked by safety level."""
        from funnel_canary.cognitive.safety import ToolRisk

        policy = MinimalCommitmentPolicy()

        tools = [
            ("high_risk_tool", ToolRisk.HIGH),
            ("safe_tool", ToolRisk.SAFE),
            ("medium_tool", ToolRisk.MEDIUM),
        ]

        ranked = policy.rank_tools(tools, confidence=0.5)

        # Only safe and medium should be allowed at 0.5 confidence
        assert "high_risk_tool" not in ranked
        assert "safe_tool" in ranked
        assert "medium_tool" in ranked
        # Safe should come first
        assert ranked.index("safe_tool") < ranked.index("medium_tool")
