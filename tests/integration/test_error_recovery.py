"""Integration tests for error recovery mechanisms.

Tests the system's ability to handle and recover from errors gracefully.
"""

from unittest.mock import MagicMock, patch

import pytest

from funnel_canary.tools import create_default_registry


class TestToolErrorRecovery:
    """Test error recovery in tool execution."""

    @pytest.mark.integration
    def test_file_tool_recovers_from_missing_file(self):
        """Read tool should gracefully handle missing files."""
        registry = create_default_registry()

        result = registry.execute("Read", {
            "file_path": "/this/file/does/not/exist.txt"
        })

        assert result.success is False
        assert "文件不存在" in result.content
        # Should still have an observation (for auditing)
        assert result.observation is not None

    @pytest.mark.integration
    def test_glob_tool_recovers_from_invalid_path(self):
        """Glob tool should gracefully handle invalid paths."""
        registry = create_default_registry()

        result = registry.execute("Glob", {
            "pattern": "*.py",
            "path": "/invalid/directory/path"
        })

        assert result.success is False
        assert "路径不存在" in result.content

    @pytest.mark.integration
    def test_bash_blocks_dangerous_commands(self):
        """Bash tool should block dangerous commands."""
        registry = create_default_registry()

        dangerous_commands = [
            "rm -rf /",
            "rm -rf ~",
            "dd if=/dev/zero",
            ":(){:|:&};:",
        ]

        for cmd in dangerous_commands:
            result = registry.execute("Bash", {"command": cmd})
            assert result.success is False, f"Command should be blocked: {cmd}"
            assert "安全检查" in result.content

    @pytest.mark.integration
    def test_python_exec_recovers_from_syntax_error(self):
        """Python exec should handle syntax errors."""
        registry = create_default_registry()

        result = registry.execute("python_exec", {
            "code": "print('missing paren'"
        })

        assert result.success is False
        assert "SyntaxError" in result.content

    @pytest.mark.integration
    def test_python_exec_recovers_from_runtime_error(self):
        """Python exec should handle runtime errors."""
        registry = create_default_registry()

        result = registry.execute("python_exec", {
            "code": "x = 1/0"
        })

        assert result.success is False
        assert "ZeroDivisionError" in result.content

    @pytest.mark.integration
    def test_bash_timeout_recovery(self):
        """Bash tool should handle timeouts gracefully."""
        registry = create_default_registry()

        result = registry.execute("Bash", {
            "command": "sleep 10",
            "timeout": 1
        })

        assert result.success is False
        assert "超时" in result.content


class TestWebToolErrorRecovery:
    """Test error recovery in web tools."""

    @pytest.mark.integration
    def test_web_search_network_error(self):
        """Web search should handle network errors."""
        import httpx

        with patch("httpx.Client") as mock_client:
            mock_instance = MagicMock()
            mock_instance.post.side_effect = httpx.HTTPError("Network error")
            mock_client.return_value.__enter__ = MagicMock(return_value=mock_instance)
            mock_client.return_value.__exit__ = MagicMock(return_value=False)

            registry = create_default_registry()
            result = registry.execute("web_search", {"query": "test"})

            assert result.success is False
            assert "搜索失败" in result.content

    @pytest.mark.integration
    def test_read_url_404_error(self):
        """Read URL should handle 404 errors."""
        import httpx

        with patch("httpx.Client") as mock_client:
            mock_response = MagicMock()
            mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
                "Not Found",
                request=MagicMock(),
                response=MagicMock(status_code=404),
            )

            mock_instance = MagicMock()
            mock_instance.get.return_value = mock_response
            mock_client.return_value.__enter__ = MagicMock(return_value=mock_instance)
            mock_client.return_value.__exit__ = MagicMock(return_value=False)

            registry = create_default_registry()
            result = registry.execute("read_url", {"url": "https://example.com/404"})

            assert result.success is False
            assert "读取URL失败" in result.content


class TestInteractionToolErrorRecovery:
    """Test error recovery in interaction tools."""

    @pytest.mark.integration
    def test_ask_user_eof_error(self):
        """Ask user should handle EOF gracefully."""
        with patch("builtins.input", side_effect=EOFError()):
            with patch("builtins.print"):
                registry = create_default_registry()
                result = registry.execute("ask_user", {"question": "Test?"})

                assert result.success is False
                assert "取消" in result.content

    @pytest.mark.integration
    def test_ask_user_keyboard_interrupt(self):
        """Ask user should handle Ctrl+C gracefully."""
        with patch("builtins.input", side_effect=KeyboardInterrupt()):
            with patch("builtins.print"):
                registry = create_default_registry()
                result = registry.execute("ask_user", {"question": "Test?"})

                assert result.success is False
                assert "取消" in result.content


class TestErrorObservations:
    """Test that errors still create proper observations."""

    @pytest.mark.integration
    def test_failed_tool_creates_observation(self):
        """Failed tools should still create observations for auditing."""
        registry = create_default_registry()

        result = registry.execute("Read", {
            "file_path": "/nonexistent/file.txt"
        })

        # Even on failure, observation should exist
        assert result.observation is not None
        # Confidence should be 0 for failures
        assert result.observation.confidence == 0.0
        # Scope should indicate error
        assert result.observation.scope == "error"

    @pytest.mark.integration
    def test_error_observation_contains_error_info(self):
        """Error observations should contain error information."""
        registry = create_default_registry()

        result = registry.execute("python_exec", {
            "code": "raise ValueError('test error')"
        })

        assert result.observation is not None
        assert "error" in result.observation.metadata
