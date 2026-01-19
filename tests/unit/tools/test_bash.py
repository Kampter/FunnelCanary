"""Unit tests for the Bash tool.

Test cases based on boundary testing plan:
- B01: Simple command (echo hello)
- B02: Dangerous command (rm -rf /)
- B03: Dangerous command (rm -rf ~)
- B04: Fork bomb
- B05: mkfs command
- B06: Case-insensitive dangerous command
- B07: Default timeout
- B08: Timeout upper limit
- B09: Negative timeout
- B10: Timeout trigger
- B11: Non-zero return code
- B12: stderr output
"""

import pytest

from funnel_canary.tools.categories.compute import (
    _bash_exec,
    _is_command_safe,
    BASH_DEFAULT_TIMEOUT,
    BASH_MAX_TIMEOUT,
    BASH_COMMAND_BLACKLIST,
)


class TestBashToolSafety:
    """Test cases for Bash tool security checks."""

    # =========================================================================
    # B02: Dangerous command (rm -rf /)
    # =========================================================================

    @pytest.mark.unit
    @pytest.mark.tools
    def test_block_rm_rf_root(self, check_failure):
        """B02: Block rm -rf / command."""
        result = _bash_exec("rm -rf /")

        check_failure(result, "安全检查失败")
        assert "危险操作" in result.error_message

    @pytest.mark.unit
    @pytest.mark.tools
    def test_block_rm_rf_root_wildcard(self, check_failure):
        """Block rm -rf /* command."""
        result = _bash_exec("rm -rf /*")

        check_failure(result, "安全检查失败")

    # =========================================================================
    # B03: Dangerous command (rm -rf ~)
    # =========================================================================

    @pytest.mark.unit
    @pytest.mark.tools
    def test_block_rm_rf_home(self, check_failure):
        """B03: Block rm -rf ~ command."""
        result = _bash_exec("rm -rf ~")

        check_failure(result, "安全检查失败")

    @pytest.mark.unit
    @pytest.mark.tools
    def test_block_rm_rf_home_slash(self, check_failure):
        """Block rm -rf ~/ command."""
        result = _bash_exec("rm -rf ~/")

        check_failure(result, "安全检查失败")

    # =========================================================================
    # B04: Fork bomb
    # =========================================================================

    @pytest.mark.unit
    @pytest.mark.tools
    def test_block_fork_bomb(self, check_failure):
        """B04: Block fork bomb pattern."""
        result = _bash_exec(":(){:|:&};:")

        check_failure(result, "安全检查失败")

    # =========================================================================
    # B05: mkfs command
    # =========================================================================

    @pytest.mark.unit
    @pytest.mark.tools
    def test_block_mkfs(self, check_failure):
        """B05: Block mkfs commands."""
        result = _bash_exec("mkfs.ext4 /dev/sda")

        check_failure(result, "安全检查失败")

    @pytest.mark.unit
    @pytest.mark.tools
    def test_block_dd_if(self, check_failure):
        """Block dd if= command."""
        result = _bash_exec("dd if=/dev/zero of=/dev/sda")

        check_failure(result, "安全检查失败")

    # =========================================================================
    # B06: Case-insensitive dangerous command
    # =========================================================================

    @pytest.mark.unit
    @pytest.mark.tools
    def test_block_uppercase_rm(self, check_failure):
        """B06: Block dangerous commands regardless of case."""
        result = _bash_exec("RM -RF /")

        check_failure(result, "安全检查失败")

    @pytest.mark.unit
    @pytest.mark.tools
    def test_block_mixed_case(self, check_failure):
        """Block mixed case dangerous commands."""
        result = _bash_exec("Rm -Rf ~/")

        check_failure(result, "安全检查失败")

    # =========================================================================
    # Additional dangerous commands
    # =========================================================================

    @pytest.mark.unit
    @pytest.mark.tools
    def test_block_shutdown(self, check_failure):
        """Block shutdown command."""
        result = _bash_exec("shutdown -h now")

        check_failure(result, "安全检查失败")

    @pytest.mark.unit
    @pytest.mark.tools
    def test_block_reboot(self, check_failure):
        """Block reboot command."""
        result = _bash_exec("reboot")

        check_failure(result, "安全检查失败")

    @pytest.mark.unit
    @pytest.mark.tools
    def test_block_dev_write(self, check_failure):
        """Block writing to /dev/sda."""
        result = _bash_exec("> /dev/sda")

        check_failure(result, "安全检查失败")

    @pytest.mark.unit
    @pytest.mark.tools
    def test_block_chmod_777_root(self, check_failure):
        """Block chmod -R 777 /."""
        result = _bash_exec("chmod -R 777 /")

        check_failure(result, "安全检查失败")


class TestBashToolSafetyChecker:
    """Test the _is_command_safe function directly."""

    @pytest.mark.unit
    @pytest.mark.tools
    def test_safe_command(self):
        """Test that safe commands pass."""
        is_safe, error = _is_command_safe("echo hello")
        assert is_safe is True
        assert error is None

    @pytest.mark.unit
    @pytest.mark.tools
    def test_all_blacklist_items_blocked(self):
        """Verify key blacklist items are blocked."""
        # Test specific dangerous commands that should definitely be blocked
        dangerous_commands = [
            "rm -rf /",
            "rm -rf ~",
            "dd if=/dev/zero of=/dev/sda",
            "mkfs.ext4 /dev/sda",
            ":(){:|:&};:",
            "shutdown -h now",
            "chmod -R 777 /etc",
        ]
        for dangerous_cmd in dangerous_commands:
            is_safe, error = _is_command_safe(dangerous_cmd)
            assert is_safe is False, f"Command should be blocked: {dangerous_cmd}"
            assert error is not None


class TestBashToolExecution:
    """Test cases for Bash tool execution."""

    # =========================================================================
    # B01: Simple command (echo hello)
    # =========================================================================

    @pytest.mark.unit
    @pytest.mark.tools
    def test_simple_echo(self, check_success):
        """B01: Execute simple echo command."""
        result = _bash_exec("echo hello")

        check_success(result)
        assert "hello" in result.content

    @pytest.mark.unit
    @pytest.mark.tools
    def test_echo_with_variable(self, check_success):
        """Execute echo with shell variable."""
        result = _bash_exec("echo $HOME")

        check_success(result)
        # Should contain a path (home directory)
        assert "/" in result.content

    # =========================================================================
    # B07: Default timeout
    # =========================================================================

    @pytest.mark.unit
    @pytest.mark.tools
    def test_default_timeout(self):
        """B07: Verify default timeout is applied."""
        result = _bash_exec("echo test")

        assert result.observation.metadata["timeout"] == BASH_DEFAULT_TIMEOUT

    # =========================================================================
    # B08: Timeout upper limit
    # =========================================================================

    @pytest.mark.unit
    @pytest.mark.tools
    def test_timeout_capped_at_max(self):
        """B08: Timeout should be capped at maximum value."""
        result = _bash_exec("echo test", timeout=600)

        # Should be capped at BASH_MAX_TIMEOUT (300)
        assert result.observation.metadata["timeout"] == BASH_MAX_TIMEOUT

    # =========================================================================
    # B09: Negative timeout
    # =========================================================================

    @pytest.mark.unit
    @pytest.mark.tools
    def test_negative_timeout_uses_default(self):
        """B09: Negative timeout should use default."""
        result = _bash_exec("echo test", timeout=-1)

        assert result.observation.metadata["timeout"] == BASH_DEFAULT_TIMEOUT

    @pytest.mark.unit
    @pytest.mark.tools
    def test_zero_timeout_uses_default(self):
        """Zero timeout should use default."""
        result = _bash_exec("echo test", timeout=0)

        assert result.observation.metadata["timeout"] == BASH_DEFAULT_TIMEOUT

    # =========================================================================
    # B10: Timeout trigger
    # =========================================================================

    @pytest.mark.unit
    @pytest.mark.tools
    def test_timeout_triggered(self, check_failure):
        """B10: Command should timeout when exceeding limit."""
        result = _bash_exec("sleep 10", timeout=1)

        check_failure(result, "超时")
        assert "1秒" in result.error_message

    # =========================================================================
    # B11: Non-zero return code
    # =========================================================================

    @pytest.mark.unit
    @pytest.mark.tools
    def test_nonzero_return_code(self, check_failure):
        """B11: Return error for non-zero exit code."""
        result = _bash_exec("exit 1")

        check_failure(result)
        # Should indicate failure

    @pytest.mark.unit
    @pytest.mark.tools
    def test_command_not_found(self, check_failure):
        """Command not found should return error."""
        result = _bash_exec("nonexistent_command_xyz")

        check_failure(result)

    # =========================================================================
    # B12: stderr output
    # =========================================================================

    @pytest.mark.unit
    @pytest.mark.tools
    def test_stderr_output_included(self, check_failure):
        """B12: stderr output should be included in result."""
        result = _bash_exec("ls /nonexistent_directory_xyz")

        check_failure(result)
        # Should contain stderr marker or error message
        assert "[stderr]" in result.content or "No such file" in result.content.lower() or "不存在" in result.content

    @pytest.mark.unit
    @pytest.mark.tools
    def test_stderr_with_stdout(self, check_success):
        """Both stdout and stderr should be captured."""
        # This command outputs to both stdout and stderr on success
        result = _bash_exec("echo out && echo err >&2")

        # The command succeeds even with stderr output
        check_success(result)
        assert "out" in result.content

    # =========================================================================
    # Additional execution tests
    # =========================================================================

    @pytest.mark.unit
    @pytest.mark.tools
    def test_command_with_args(self, check_success):
        """Execute command with arguments."""
        result = _bash_exec("echo -n test")

        check_success(result)
        assert "test" in result.content

    @pytest.mark.unit
    @pytest.mark.tools
    def test_piped_command(self, check_success):
        """Execute piped command."""
        result = _bash_exec("echo hello | tr 'h' 'H'")

        check_success(result)
        assert "Hello" in result.content

    @pytest.mark.unit
    @pytest.mark.tools
    def test_metadata_populated(self, check_success):
        """Verify metadata is correctly populated."""
        result = _bash_exec("echo test")

        check_success(result)
        assert result.observation.metadata["command"] == "echo test"
        assert result.observation.metadata["return_code"] == 0
        assert "has_output" in result.observation.metadata

    @pytest.mark.unit
    @pytest.mark.tools
    def test_observation_source(self):
        """Verify observation source is correctly set."""
        result = _bash_exec("echo test")

        from funnel_canary.provenance import ObservationType

        assert result.observation.source_type == ObservationType.TOOL_RETURN
        assert result.observation.source_id == "Bash"
        assert result.observation.confidence == 0.9  # Shell commands have slightly lower confidence

    @pytest.mark.unit
    @pytest.mark.tools
    def test_command_with_no_output(self, check_success):
        """Command with no output should still succeed."""
        result = _bash_exec("true")

        check_success(result)
        assert "成功" in result.content or result.content == ""
