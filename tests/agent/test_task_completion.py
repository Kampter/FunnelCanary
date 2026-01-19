"""Agent-level tests for task completion.

Tests that verify the Agent can complete various types of tasks.
Based on the test plan:
- TC01: Simple calculation
- TC02: Network search
- TC03: Multi-step task
- TC04: File analysis
- TC05: Ambiguous question
- TC06: Impossible task
"""

from unittest.mock import MagicMock, patch

import pytest


class MockMessage:
    """Mock OpenAI message object."""

    def __init__(self, content=None, tool_calls=None):
        self.role = "assistant"
        self.content = content
        self.tool_calls = tool_calls


class MockToolCall:
    """Mock OpenAI tool call object."""

    def __init__(self, id, name, arguments):
        self.id = id
        self.function = MagicMock()
        self.function.name = name
        self.function.arguments = arguments


class MockChoice:
    """Mock OpenAI choice object."""

    def __init__(self, message, finish_reason="stop"):
        self.message = message
        self.finish_reason = finish_reason


class MockResponse:
    """Mock OpenAI response object."""

    def __init__(self, choices):
        self.choices = choices


def create_mock_openai_response(content=None, tool_calls=None, finish_reason="stop"):
    """Helper to create mock OpenAI response."""
    message = MockMessage(content=content, tool_calls=tool_calls)
    choice = MockChoice(message, finish_reason=finish_reason)
    return MockResponse([choice])


class TestTaskCompletionBasic:
    """Basic task completion tests."""

    @pytest.mark.agent
    def test_agent_initialization(self, mock_config):
        """Test that agent can be initialized."""
        with patch("funnel_canary.agent.OpenAI"):
            from funnel_canary.agent import ProblemSolvingAgent

            agent = ProblemSolvingAgent(
                config=mock_config,
                max_iterations=5,
                enable_memory=False,
                enable_skills=False,
                enable_cognitive=True,
                enable_grounding=True,
            )

            assert agent.config == mock_config
            assert agent.max_iterations == 5
            assert agent.enable_grounding is True

    @pytest.mark.agent
    def test_simple_direct_answer(self, mock_config):
        """TC01: Agent can provide simple direct answers."""
        with patch("funnel_canary.agent.OpenAI") as mock_openai:
            mock_client = MagicMock()
            mock_openai.return_value = mock_client

            # Mock a direct answer without tool calls
            mock_response = create_mock_openai_response(
                content="1 + 1 = 2。这是一个简单的加法运算。",
                finish_reason="stop"
            )
            mock_client.chat.completions.create.return_value = mock_response

            from funnel_canary.agent import ProblemSolvingAgent

            agent = ProblemSolvingAgent(
                config=mock_config,
                max_iterations=5,
                enable_memory=False,
                enable_skills=False,
            )

            result = agent.solve("1+1等于多少")

            assert "2" in result
            # Should not require multiple iterations for simple math
            mock_client.chat.completions.create.assert_called()


class TestTaskCompletionWithTools:
    """Task completion tests involving tool usage."""

    @pytest.mark.agent
    def test_tool_call_execution(self, mock_config):
        """TC02: Agent can execute tool calls."""
        with patch("funnel_canary.agent.OpenAI") as mock_openai:
            mock_client = MagicMock()
            mock_openai.return_value = mock_client

            # First response: tool call
            tool_call = MockToolCall(
                id="call_1",
                name="python_exec",
                arguments='{"code": "print(2+2)"}'
            )
            first_response = create_mock_openai_response(
                content="让我计算一下...",
                tool_calls=[tool_call],
                finish_reason="tool_calls"
            )

            # Second response: final answer
            second_response = create_mock_openai_response(
                content="计算结果是4。",
                finish_reason="stop"
            )

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
            )

            # Suppress print output during test
            with patch("builtins.print"):
                result = agent.solve("计算2+2")

            assert mock_client.chat.completions.create.call_count == 2


class TestTaskCompletionProvenance:
    """Task completion tests with provenance tracking."""

    @pytest.mark.agent
    def test_provenance_tracking_enabled(self, mock_config):
        """Agent should track provenance when enabled."""
        with patch("funnel_canary.agent.OpenAI") as mock_openai:
            mock_client = MagicMock()
            mock_openai.return_value = mock_client

            mock_response = create_mock_openai_response(
                content="Answer",
                finish_reason="stop"
            )
            mock_client.chat.completions.create.return_value = mock_response

            from funnel_canary.agent import ProblemSolvingAgent

            agent = ProblemSolvingAgent(
                config=mock_config,
                max_iterations=5,
                enable_memory=False,
                enable_skills=False,
                enable_grounding=True,
            )

            with patch("builtins.print"):
                agent.solve("Test question")

            # Provenance should be enabled
            assert agent.enable_grounding is True
            # Should have at least the initial user observation
            assert agent.get_observation_count() >= 1

    @pytest.mark.agent
    def test_tool_results_tracked_in_provenance(self, mock_config):
        """Tool results should be added to provenance registry."""
        with patch("funnel_canary.agent.OpenAI") as mock_openai:
            mock_client = MagicMock()
            mock_openai.return_value = mock_client

            # First response: tool call
            tool_call = MockToolCall(
                id="call_1",
                name="python_exec",
                arguments='{"code": "print(42)"}'
            )
            first_response = create_mock_openai_response(
                content="Computing...",
                tool_calls=[tool_call],
                finish_reason="tool_calls"
            )

            # Second response: final answer
            second_response = create_mock_openai_response(
                content="Result is 42",
                finish_reason="stop"
            )

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
                agent.solve("What is 6 times 7?")

            # Should have observations: user input + tool result
            assert agent.get_observation_count() >= 2


class TestTaskCompletionEdgeCases:
    """Edge case tests for task completion."""

    @pytest.mark.agent
    def test_max_iterations_limit(self, mock_config):
        """Agent should stop at max iterations."""
        with patch("funnel_canary.agent.OpenAI") as mock_openai:
            mock_client = MagicMock()
            mock_openai.return_value = mock_client

            # Always return tool calls (never stop)
            tool_call = MockToolCall(
                id="call_1",
                name="python_exec",
                arguments='{"code": "print(1)"}'
            )
            response = create_mock_openai_response(
                content="Continuing...",
                tool_calls=[tool_call],
                finish_reason="tool_calls"
            )
            mock_client.chat.completions.create.return_value = response

            from funnel_canary.agent import ProblemSolvingAgent

            agent = ProblemSolvingAgent(
                config=mock_config,
                max_iterations=3,  # Low limit
                enable_memory=False,
                enable_skills=False,
            )

            with patch("builtins.print"):
                result = agent.solve("Infinite loop test")

            # Should hit max iterations
            assert "最大迭代" in result or mock_client.chat.completions.create.call_count <= 3

    @pytest.mark.agent
    def test_api_error_handling(self, mock_config):
        """Agent should handle API errors gracefully."""
        with patch("funnel_canary.agent.OpenAI") as mock_openai:
            mock_client = MagicMock()
            mock_openai.return_value = mock_client

            # Simulate API error
            mock_client.chat.completions.create.side_effect = Exception("API Error")

            from funnel_canary.agent import ProblemSolvingAgent

            agent = ProblemSolvingAgent(
                config=mock_config,
                max_iterations=3,
                enable_memory=False,
                enable_skills=False,
            )

            with patch("builtins.print"):
                result = agent.solve("Test with error")

            # Should return some result despite error
            assert result is not None
            assert len(result) > 0

    @pytest.mark.agent
    def test_empty_response_handling(self, mock_config):
        """Agent should handle empty responses."""
        with patch("funnel_canary.agent.OpenAI") as mock_openai:
            mock_client = MagicMock()
            mock_openai.return_value = mock_client

            # Empty content response
            mock_response = create_mock_openai_response(
                content="",
                finish_reason="stop"
            )
            mock_client.chat.completions.create.return_value = mock_response

            from funnel_canary.agent import ProblemSolvingAgent

            agent = ProblemSolvingAgent(
                config=mock_config,
                max_iterations=3,
                enable_memory=False,
                enable_skills=False,
            )

            with patch("builtins.print"):
                result = agent.solve("Empty response test")

            # Should still return something
            assert result is not None
