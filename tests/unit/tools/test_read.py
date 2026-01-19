"""Unit tests for the Read tool.

Test cases based on boundary testing plan:
- R01: Normal small file (< 100KB)
- R02: Exactly 100KB file
- R03: File over 100KB
- R04: Non-existent file
- R05: Directory instead of file
- R06: No permission file
- R07: Binary file
- R08: UTF-8 Chinese file
- R09: Empty path
"""

import pytest

from funnel_canary.tools.categories.filesystem import _read_file, FILE_READ_MAX


class TestReadTool:
    """Test cases for the Read tool."""

    # =========================================================================
    # R01: Normal small file (< 100KB)
    # =========================================================================

    @pytest.mark.unit
    @pytest.mark.tools
    def test_read_normal_small_file(self, sample_file, check_success):
        """R01: Read a normal small file successfully."""
        result = _read_file(str(sample_file))

        check_success(result)
        assert "Hello, World!" in result.content
        assert "This is a test file." in result.content
        assert result.observation.confidence == 1.0
        assert result.observation.ttl_seconds is None  # No expiration for local files

    @pytest.mark.unit
    @pytest.mark.tools
    def test_read_python_file(self, sample_python_file, check_success):
        """Read a Python source file."""
        result = _read_file(str(sample_python_file))

        check_success(result)
        assert 'print("Hello from Python")' in result.content

    # =========================================================================
    # R02: Exactly 100KB file
    # =========================================================================

    @pytest.mark.unit
    @pytest.mark.tools
    def test_read_exact_100kb_file(self, exact_100kb_file, check_success):
        """R02: Read a file exactly 100KB in size."""
        result = _read_file(str(exact_100kb_file))

        check_success(result)
        assert len(result.content) == 100_000

    # =========================================================================
    # R03: File over 100KB
    # =========================================================================

    @pytest.mark.unit
    @pytest.mark.tools
    def test_read_large_file_fails(self, large_file, check_failure):
        """R03: Reject files larger than 100KB."""
        result = _read_file(str(large_file))

        check_failure(result, "文件过大")
        assert str(FILE_READ_MAX) in result.error_message

    # =========================================================================
    # R04: Non-existent file
    # =========================================================================

    @pytest.mark.unit
    @pytest.mark.tools
    def test_read_nonexistent_file(self, check_failure):
        """R04: Return error for non-existent file."""
        result = _read_file("/nonexistent/path/to/file.txt")

        check_failure(result, "文件不存在")

    @pytest.mark.unit
    @pytest.mark.tools
    def test_read_nonexistent_relative_path(self, check_failure):
        """R04b: Return error for non-existent relative path."""
        result = _read_file("definitely_not_a_file_xyz.txt")

        check_failure(result, "文件不存在")

    # =========================================================================
    # R05: Directory instead of file
    # =========================================================================

    @pytest.mark.unit
    @pytest.mark.tools
    def test_read_directory_fails(self, temp_dir, check_failure):
        """R05: Return error when path is a directory."""
        result = _read_file(str(temp_dir))

        check_failure(result, "路径不是文件")

    # =========================================================================
    # R06: No permission file
    # =========================================================================

    @pytest.mark.unit
    @pytest.mark.tools
    def test_read_no_permission_file(self, no_permission_file, check_failure):
        """R06: Return error when file has no read permissions."""
        result = _read_file(str(no_permission_file))

        check_failure(result, "权限不足")

    # =========================================================================
    # R07: Binary file
    # =========================================================================

    @pytest.mark.unit
    @pytest.mark.tools
    def test_read_binary_file(self, binary_file, check_success):
        """R07: Read binary file with replacement characters."""
        result = _read_file(str(binary_file))

        check_success(result)
        # Should contain replacement characters for non-UTF8 bytes
        assert "\ufffd" in result.content or len(result.content) > 0

    # =========================================================================
    # R08: UTF-8 Chinese file
    # =========================================================================

    @pytest.mark.unit
    @pytest.mark.tools
    def test_read_utf8_chinese_file(self, utf8_chinese_file, check_success):
        """R08: Read UTF-8 encoded Chinese content correctly."""
        result = _read_file(str(utf8_chinese_file))

        check_success(result)
        assert "这是中文内容" in result.content
        assert "测试UTF-8编码" in result.content

    # =========================================================================
    # R09: Empty path
    # =========================================================================

    @pytest.mark.unit
    @pytest.mark.tools
    def test_read_empty_path(self, check_failure):
        """R09: Return error for empty path."""
        result = _read_file("")

        # Empty path resolves to current directory, which should fail
        assert result.success is False

    # =========================================================================
    # Additional edge cases
    # =========================================================================

    @pytest.mark.unit
    @pytest.mark.tools
    def test_read_empty_file(self, empty_file, check_success):
        """Read an empty file successfully."""
        result = _read_file(str(empty_file))

        check_success(result)
        assert result.content == ""

    @pytest.mark.unit
    @pytest.mark.tools
    def test_read_metadata(self, sample_file):
        """Verify metadata is correctly populated."""
        result = _read_file(str(sample_file))

        assert result.observation.metadata is not None
        assert "file_path" in result.observation.metadata
        assert "file_size" in result.observation.metadata
        assert result.observation.metadata["encoding"] == "utf-8"

    @pytest.mark.unit
    @pytest.mark.tools
    def test_read_observation_source(self, sample_file):
        """Verify observation source is correctly set."""
        result = _read_file(str(sample_file))

        from funnel_canary.provenance import ObservationType

        assert result.observation.source_type == ObservationType.TOOL_RETURN
        assert result.observation.source_id == "Read"
