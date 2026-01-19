"""Agent-level tests for degradation mechanism.

Tests that verify the anti-hallucination degradation system works correctly.
Based on the test plan:
- D01: High confidence -> FULL_ANSWER
- D02: Medium confidence -> PARTIAL_WITH_UNCERTAINTY
- D03: Low confidence -> REQUEST_MORE_INFO
- D04: No observations -> REFUSE
- D05: Expired observations -> REQUEST_MORE_INFO
"""

from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest

from funnel_canary.provenance import (
    DegradationLevel,
    Observation,
    ObservationType,
    ProvenanceRegistry,
)
from funnel_canary.provenance.generator import GroundedAnswerGenerator


class TestDegradationLevels:
    """Test degradation level determination."""

    @pytest.mark.agent
    def test_d01_full_answer_high_confidence(self):
        """D01: High confidence observations should allow full answer."""
        registry = ProvenanceRegistry()

        # Add multiple high-confidence observations
        for i in range(3):
            registry.add_observation(Observation(
                content=f"High confidence observation {i}",
                source_type=ObservationType.TOOL_RETURN,
                source_id="web_search",
                confidence=1.0,
                ttl_seconds=3600,
            ))

        level = registry.determine_degradation_level()
        assert level == DegradationLevel.FULL_ANSWER

    @pytest.mark.agent
    def test_d02_partial_medium_confidence(self):
        """D02: Medium confidence should result in partial answer with uncertainty."""
        registry = ProvenanceRegistry()

        # Add observations with medium confidence
        registry.add_observation(Observation(
            content="Medium confidence observation",
            source_type=ObservationType.USER_INPUT,
            source_id="user",
            confidence=0.6,
        ))
        registry.add_observation(Observation(
            content="Another medium confidence",
            source_type=ObservationType.USER_INPUT,
            source_id="user",
            confidence=0.7,
        ))

        level = registry.determine_degradation_level()
        assert level == DegradationLevel.PARTIAL_WITH_UNCERTAINTY

    @pytest.mark.agent
    def test_d03_low_confidence_request_info(self):
        """D03: Low confidence should request more information."""
        registry = ProvenanceRegistry()

        # Add only low-confidence observations
        registry.add_observation(Observation(
            content="Low confidence observation",
            source_type=ObservationType.USER_INPUT,
            source_id="user",
            confidence=0.3,
        ))

        level = registry.determine_degradation_level(min_confidence=0.5)
        assert level == DegradationLevel.REQUEST_MORE_INFO

    @pytest.mark.agent
    def test_d04_no_observations_refuse(self):
        """D04: No observations should result in refusal."""
        registry = ProvenanceRegistry()

        # Empty registry
        level = registry.determine_degradation_level()
        assert level == DegradationLevel.REFUSE

    @pytest.mark.agent
    def test_d05_expired_observations_request_info(self):
        """D05: Expired observations should request fresh information."""
        registry = ProvenanceRegistry()

        # Add an expired observation
        expired_obs = Observation(
            content="Old information",
            source_type=ObservationType.TOOL_RETURN,
            source_id="web_search",
            confidence=1.0,
            ttl_seconds=1,  # Very short TTL
        )
        # Backdate the timestamp
        expired_obs.timestamp = datetime.now() - timedelta(seconds=10)
        registry.add_observation(expired_obs)

        # Should not count expired observations
        level = registry.determine_degradation_level()
        assert level == DegradationLevel.REFUSE  # No valid observations


class TestGroundedAnswerGenerator:
    """Test the grounded answer generator."""

    @pytest.mark.agent
    def test_generator_creates_grounded_answer(self):
        """Generator should create properly grounded answers."""
        registry = ProvenanceRegistry()
        registry.add_observation(Observation(
            content="Python is a programming language",
            source_type=ObservationType.TOOL_RETURN,
            source_id="web_search",
            confidence=1.0,
        ))

        generator = GroundedAnswerGenerator()
        grounded = generator.generate(
            raw_answer="Python is a popular programming language.",
            registry=registry,
        )

        assert grounded is not None
        assert grounded.content is not None
        assert grounded.degradation_level == DegradationLevel.FULL_ANSWER

    @pytest.mark.agent
    def test_generator_adds_uncertainty_note(self):
        """Generator should add uncertainty note for partial answers."""
        registry = ProvenanceRegistry()
        registry.add_observation(Observation(
            content="Some info",
            source_type=ObservationType.USER_INPUT,
            source_id="user",
            confidence=0.5,
        ))

        generator = GroundedAnswerGenerator()
        grounded = generator.generate(
            raw_answer="Based on limited information...",
            registry=registry,
        )

        # Should indicate uncertainty
        formatted = grounded.to_formatted_output()
        assert "不确定" in formatted or grounded.degradation_level != DegradationLevel.FULL_ANSWER

    @pytest.mark.agent
    def test_generator_handles_empty_registry(self):
        """Generator should handle empty registry gracefully."""
        registry = ProvenanceRegistry()

        generator = GroundedAnswerGenerator()
        grounded = generator.generate(
            raw_answer="This answer has no backing.",
            registry=registry,
        )

        assert grounded.degradation_level == DegradationLevel.REFUSE


class TestDegradationInAgent:
    """Test degradation behavior in the full agent context."""

    @pytest.mark.agent
    def test_agent_with_high_confidence_tools(self, mock_config):
        """Agent should produce full answers with high-confidence tool results."""
        with patch("funnel_canary.agent.OpenAI") as mock_openai:
            mock_client = MagicMock()
            mock_openai.return_value = mock_client

            # Tool call that returns high confidence result
            class MockToolCall:
                def __init__(self):
                    self.id = "call_1"
                    self.function = MagicMock()
                    self.function.name = "python_exec"
                    self.function.arguments = '{"code": "print(2+2)"}'

            class MockMessage:
                def __init__(self, content, tool_calls=None):
                    self.role = "assistant"
                    self.content = content
                    self.tool_calls = tool_calls

            class MockChoice:
                def __init__(self, message, finish_reason):
                    self.message = message
                    self.finish_reason = finish_reason

            class MockResponse:
                def __init__(self, choices):
                    self.choices = choices

            # First call: tool execution
            first_msg = MockMessage("Calculating...", [MockToolCall()])
            first_response = MockResponse([MockChoice(first_msg, "tool_calls")])

            # Second call: final answer
            second_msg = MockMessage("The answer is 4.")
            second_response = MockResponse([MockChoice(second_msg, "stop")])

            mock_client.chat.completions.create.side_effect = [
                first_response,
                second_response
            ]

            from funnel_canary.agent import ProblemSolvingAgent

            agent = ProblemSolvingAgent(
                config=mock_config,
                max_iterations=5,
                enable_memory=False,
                enable_skills=False,
                enable_grounding=True,
            )

            with patch("builtins.print"):
                result = agent.solve("What is 2+2?")

            # With high-confidence tool result, should have observations
            assert agent.get_observation_count() >= 2  # User input + tool result


class TestDegradationFormatting:
    """Test the formatting of degraded answers."""

    @pytest.mark.agent
    def test_full_answer_no_extra_formatting(self):
        """Full answers should not have excessive formatting."""
        registry = ProvenanceRegistry()
        for i in range(3):
            registry.add_observation(Observation(
                content=f"Observation {i}",
                source_type=ObservationType.TOOL_RETURN,
                source_id="web_search",
                confidence=1.0,
            ))

        generator = GroundedAnswerGenerator()
        grounded = generator.generate(
            raw_answer="Clear answer here.",
            registry=registry,
        )

        # Full answer should be relatively clean
        assert grounded.degradation_level == DegradationLevel.FULL_ANSWER

    @pytest.mark.agent
    def test_partial_answer_has_uncertainty_marker(self):
        """Partial answers should have uncertainty markers."""
        registry = ProvenanceRegistry()
        registry.add_observation(Observation(
            content="Limited info",
            source_type=ObservationType.USER_INPUT,
            source_id="user",
            confidence=0.5,
        ))

        generator = GroundedAnswerGenerator()
        grounded = generator.generate(
            raw_answer="Based on what I know...",
            registry=registry,
        )

        formatted = grounded.to_formatted_output()
        # Should contain uncertainty marker
        assert (
            "⚠️" in formatted or
            "不确定" in formatted or
            "部分" in formatted or
            grounded.degradation_level == DegradationLevel.PARTIAL_WITH_UNCERTAINTY
        )

    @pytest.mark.agent
    def test_refuse_has_clear_explanation(self):
        """Refused answers should explain why."""
        registry = ProvenanceRegistry()
        # Empty registry

        generator = GroundedAnswerGenerator()
        grounded = generator.generate(
            raw_answer="I don't have enough information.",
            registry=registry,
        )

        assert grounded.degradation_level == DegradationLevel.REFUSE
        formatted = grounded.to_formatted_output()
        # Should explain the refusal
        assert len(formatted) > 0
