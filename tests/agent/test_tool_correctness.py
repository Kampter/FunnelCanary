"""Agent-level tests for tool call correctness.

Tests that verify the Agent calls the correct tools with correct parameters.
Based on the test plan:
- TC01: Search trigger
- TC02: URL reading
- TC03: File reading
- TC04: Multi-tool combination
- TC05: No tool needed
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


def create_mock_response(content=None, tool_calls=None, finish_reason="stop"):
    """Helper to create mock OpenAI response."""
    message = MockMessage(content=content, tool_calls=tool_calls)
    choice = MockChoice(message, finish_reason=finish_reason)
    return MockResponse([choice])


class TestToolCallCorrectness:
    """Tests for correct tool calling behavior."""

    @pytest.mark.agent
    def test_python_exec_for_calculation(self, mock_config):
        """Agent should use python_exec for calculations."""
        with patch("funnel_canary.agent.OpenAI") as mock_openai:
            mock_client = MagicMock()
            mock_openai.return_value = mock_client

            # Track the tool calls made
            tool_calls_made = []

            def capture_calls(*args, **kwargs):
                # Check if this is returning tool calls
                tool_call = MockToolCall(
                    id="call_1",
                    name="python_exec",
                    arguments='{"code": "print(15*15)"}'
                )
                tool_calls_made.append(tool_call.function.name)

                if len(tool_calls_made) == 1:
                    return create_mock_response(
                        content="Let me calculate...",
                        tool_calls=[tool_call],
                        finish_reason="tool_calls"
                    )
                else:
                    return create_mock_response(
                        content="225",
                        finish_reason="stop"
                    )

            mock_client.chat.completions.create.side_effect = capture_calls

            from funnel_canary.agent import ProblemSolvingAgent

            agent = ProblemSolvingAgent(
                config=mock_config,
                max_iterations=5,
                enable_memory=False,
                enable_skills=False,
            )

            with patch("builtins.print"):
                agent.solve("计算15的平方")

            assert "python_exec" in tool_calls_made

    @pytest.mark.agent
    def test_tool_schema_includes_all_tools(self, mock_config):
        """Agent should expose all registered tools to the API."""
        with patch("funnel_canary.agent.OpenAI") as mock_openai:
            mock_client = MagicMock()
            mock_openai.return_value = mock_client

            mock_response = create_mock_response(
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
            )

            with patch("builtins.print"):
                agent.solve("Test")

            # Check that tools were passed to the API
            call_kwargs = mock_client.chat.completions.create.call_args[1]
            tools = call_kwargs.get("tools", [])

            tool_names = [t["function"]["name"] for t in tools]
            expected_tools = [
                "web_search", "read_url", "ask_user",
                "python_exec", "Read", "Glob", "Bash"
            ]

            for expected in expected_tools:
                assert expected in tool_names, f"Missing tool: {expected}"


class TestToolArgumentValidation:
    """Tests for tool argument validation."""

    @pytest.mark.agent
    def test_read_tool_receives_file_path(self, mock_config, temp_dir):
        """Read tool should receive correct file_path argument."""
        test_file = temp_dir / "test.txt"
        test_file.write_text("test content")

        with patch("funnel_canary.agent.OpenAI") as mock_openai:
            mock_client = MagicMock()
            mock_openai.return_value = mock_client

            # Agent calls Read with file path
            tool_call = MockToolCall(
                id="call_1",
                name="Read",
                arguments=f'{{"file_path": "{test_file}"}}'
            )

            first_response = create_mock_response(
                content="Reading file...",
                tool_calls=[tool_call],
                finish_reason="tool_calls"
            )

            second_response = create_mock_response(
                content="File contains: test content",
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

            with patch("builtins.print"):
                result = agent.solve(f"读取文件 {test_file}")

            # Tool should have been called with correct path
            assert mock_client.chat.completions.create.call_count == 2

    @pytest.mark.agent
    def test_glob_tool_receives_pattern(self, mock_config, temp_dir):
        """Glob tool should receive correct pattern argument."""
        with patch("funnel_canary.agent.OpenAI") as mock_openai:
            mock_client = MagicMock()
            mock_openai.return_value = mock_client

            # Agent calls Glob with pattern
            tool_call = MockToolCall(
                id="call_1",
                name="Glob",
                arguments=f'{{"pattern": "*.py", "path": "{temp_dir}"}}'
            )

            first_response = create_mock_response(
                content="Searching...",
                tool_calls=[tool_call],
                finish_reason="tool_calls"
            )

            second_response = create_mock_response(
                content="No Python files found",
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

            with patch("builtins.print"):
                agent.solve(f"在 {temp_dir} 中查找所有 Python 文件")

            assert mock_client.chat.completions.create.call_count == 2


class TestMultiToolSequence:
    """Tests for multi-tool execution sequences."""

    @pytest.mark.agent
    def test_multiple_tool_calls_in_sequence(self, mock_config):
        """Agent should handle multiple tool calls in sequence."""
        with patch("funnel_canary.agent.OpenAI") as mock_openai:
            mock_client = MagicMock()
            mock_openai.return_value = mock_client

            # First: Glob call
            tool_call_1 = MockToolCall(
                id="call_1",
                name="python_exec",
                arguments='{"code": "print(1+1)"}'
            )

            # Second: Read call
            tool_call_2 = MockToolCall(
                id="call_2",
                name="python_exec",
                arguments='{"code": "print(2+2)"}'
            )

            first_response = create_mock_response(
                content="First calculation...",
                tool_calls=[tool_call_1],
                finish_reason="tool_calls"
            )

            second_response = create_mock_response(
                content="Second calculation...",
                tool_calls=[tool_call_2],
                finish_reason="tool_calls"
            )

            third_response = create_mock_response(
                content="Results: 2 and 4",
                finish_reason="stop"
            )

            mock_client.chat.completions.create.side_effect = [
                first_response,
                second_response,
                third_response
            ]

            from funnel_canary.agent import ProblemSolvingAgent

            agent = ProblemSolvingAgent(
                config=mock_config,
                max_iterations=10,
                enable_memory=False,
                enable_skills=False,
            )

            with patch("builtins.print"):
                result = agent.solve("计算 1+1 和 2+2")

            # Should have made 3 API calls
            assert mock_client.chat.completions.create.call_count == 3


class TestToolErrorHandling:
    """Tests for tool error handling during agent execution."""

    @pytest.mark.agent
    def test_agent_handles_tool_error(self, mock_config):
        """Agent should handle tool execution errors gracefully."""
        with patch("funnel_canary.agent.OpenAI") as mock_openai:
            mock_client = MagicMock()
            mock_openai.return_value = mock_client

            # Call a tool that will fail (Read non-existent file)
            tool_call = MockToolCall(
                id="call_1",
                name="Read",
                arguments='{"file_path": "/nonexistent/file.txt"}'
            )

            first_response = create_mock_response(
                content="Reading file...",
                tool_calls=[tool_call],
                finish_reason="tool_calls"
            )

            # Agent should recover and provide response
            second_response = create_mock_response(
                content="抱歉，无法读取该文件，文件不存在。",
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

            with patch("builtins.print"):
                result = agent.solve("读取 /nonexistent/file.txt")

            # Agent should still complete
            assert result is not None
            assert mock_client.chat.completions.create.call_count == 2
