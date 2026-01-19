"""Unit tests for the ask_user tool.

Test cases based on boundary testing plan:
- A01: Normal input (returns response)
- A02: Empty input
- A03: EOF (Ctrl+D)
- A04: Ctrl+C (KeyboardInterrupt)
- A05: Confidence verification (80%)
- A06: No TTL
"""

from unittest.mock import patch

import pytest

from funnel_canary.tools.categories.interaction import _ask_user, USER_INPUT_CONFIDENCE


class TestAskUserSuccess:
    """Test cases for successful ask_user operations."""

    # =========================================================================
    # A01: Normal input (returns response)
    # =========================================================================

    @pytest.mark.unit
    @pytest.mark.tools
    def test_normal_input(self, check_success):
        """A01: Normal user input returns successfully."""
        with patch("builtins.input", return_value="user response"):
            with patch("builtins.print"):  # Suppress output
                result = _ask_user("What is your name?")

                check_success(result)
                assert result.content == "user response"

    @pytest.mark.unit
    @pytest.mark.tools
    def test_input_with_spaces(self, check_success):
        """User input with spaces is preserved."""
        with patch("builtins.input", return_value="  spaced input  "):
            with patch("builtins.print"):
                result = _ask_user("Question?")

                check_success(result)
                assert result.content == "  spaced input  "

    @pytest.mark.unit
    @pytest.mark.tools
    def test_input_with_special_chars(self, check_success):
        """User input with special characters is preserved."""
        with patch("builtins.input", return_value="Hello! @#$%^&*()"):
            with patch("builtins.print"):
                result = _ask_user("Question?")

                check_success(result)
                assert result.content == "Hello! @#$%^&*()"

    @pytest.mark.unit
    @pytest.mark.tools
    def test_input_with_chinese(self, check_success):
        """User input with Chinese characters is preserved."""
        with patch("builtins.input", return_value="中文输入测试"):
            with patch("builtins.print"):
                result = _ask_user("请输入中文：")

                check_success(result)
                assert result.content == "中文输入测试"

    # =========================================================================
    # A02: Empty input
    # =========================================================================

    @pytest.mark.unit
    @pytest.mark.tools
    def test_empty_input(self, check_success):
        """A02: Empty input is allowed and returns empty string."""
        with patch("builtins.input", return_value=""):
            with patch("builtins.print"):
                result = _ask_user("Can be empty?")

                check_success(result)
                assert result.content == ""

    # =========================================================================
    # A05: Confidence verification (80%)
    # =========================================================================

    @pytest.mark.unit
    @pytest.mark.tools
    def test_confidence_is_80_percent(self):
        """A05: User input confidence should be 80%."""
        with patch("builtins.input", return_value="answer"):
            with patch("builtins.print"):
                result = _ask_user("Question?")

                assert result.observation.confidence == USER_INPUT_CONFIDENCE
                assert result.observation.confidence == 0.8

    # =========================================================================
    # A06: No TTL
    # =========================================================================

    @pytest.mark.unit
    @pytest.mark.tools
    def test_no_ttl(self):
        """A06: User input has no TTL (never expires)."""
        with patch("builtins.input", return_value="answer"):
            with patch("builtins.print"):
                result = _ask_user("Question?")

                assert result.observation.ttl_seconds is None


class TestAskUserErrors:
    """Test cases for ask_user error handling."""

    # =========================================================================
    # A03: EOF (Ctrl+D)
    # =========================================================================

    @pytest.mark.unit
    @pytest.mark.tools
    def test_eof_error(self, check_failure):
        """A03: Handle EOF (Ctrl+D) gracefully."""
        with patch("builtins.input", side_effect=EOFError()):
            with patch("builtins.print"):
                result = _ask_user("Question?")

                check_failure(result, "用户取消输入")

    # =========================================================================
    # A04: Ctrl+C (KeyboardInterrupt)
    # =========================================================================

    @pytest.mark.unit
    @pytest.mark.tools
    def test_keyboard_interrupt(self, check_failure):
        """A04: Handle Ctrl+C gracefully."""
        with patch("builtins.input", side_effect=KeyboardInterrupt()):
            with patch("builtins.print"):
                result = _ask_user("Question?")

                check_failure(result, "用户取消输入")


class TestAskUserMetadata:
    """Test cases for ask_user metadata and observation."""

    @pytest.mark.unit
    @pytest.mark.tools
    def test_observation_source_type(self):
        """Verify observation source type is TOOL_RETURN."""
        with patch("builtins.input", return_value="answer"):
            with patch("builtins.print"):
                result = _ask_user("Question?")

                from funnel_canary.provenance import ObservationType

                assert result.observation.source_type == ObservationType.TOOL_RETURN
                assert result.observation.source_id == "ask_user"

    @pytest.mark.unit
    @pytest.mark.tools
    def test_metadata_contains_question(self):
        """Verify metadata contains the question asked."""
        with patch("builtins.input", return_value="answer"):
            with patch("builtins.print"):
                result = _ask_user("What is your favorite color?")

                assert result.observation.metadata["question"] == "What is your favorite color?"

    @pytest.mark.unit
    @pytest.mark.tools
    def test_observation_scope(self):
        """Verify observation scope is 'user_input'."""
        with patch("builtins.input", return_value="answer"):
            with patch("builtins.print"):
                result = _ask_user("Question?")

                assert result.observation.scope == "user_input"

    @pytest.mark.unit
    @pytest.mark.tools
    def test_prints_question(self):
        """Verify the question is printed to the user."""
        with patch("builtins.input", return_value="answer"):
            with patch("builtins.print") as mock_print:
                _ask_user("Test question?")

                # Verify print was called with the question
                mock_print.assert_called()
                call_args = str(mock_print.call_args)
                assert "Test question?" in call_args


class TestAskUserConstant:
    """Test cases for ask_user constants."""

    @pytest.mark.unit
    @pytest.mark.tools
    def test_user_input_confidence_constant(self):
        """Verify USER_INPUT_CONFIDENCE constant value."""
        assert USER_INPUT_CONFIDENCE == 0.8
