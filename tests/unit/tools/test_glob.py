"""Unit tests for the Glob tool.

Test cases based on boundary testing plan:
- G01: Simple pattern (*.py)
- G02: Recursive pattern (**/*.py)
- G03: No match pattern
- G04: Exactly 100 results
- G05: Over 100 results (truncation)
- G06: Non-existent path
- G07: File path instead of directory
- G08: Sort by modification time
"""

import time

import pytest

from funnel_canary.tools.categories.filesystem import _glob_files, GLOB_MAX_RESULTS


class TestGlobTool:
    """Test cases for the Glob tool."""

    # =========================================================================
    # G01: Simple pattern (*.py)
    # =========================================================================

    @pytest.mark.unit
    @pytest.mark.tools
    def test_glob_simple_pattern(self, structured_dir, check_success):
        """G01: Match top-level .py files with simple pattern."""
        result = _glob_files("*.py", str(structured_dir))

        check_success(result)
        assert "main.py" in result.content
        # Should not include nested files with non-recursive pattern
        assert result.observation.metadata["match_count"] == 1

    @pytest.mark.unit
    @pytest.mark.tools
    def test_glob_simple_md_pattern(self, structured_dir, check_success):
        """Match markdown files with simple pattern."""
        result = _glob_files("*.md", str(structured_dir))

        check_success(result)
        assert "README.md" in result.content

    # =========================================================================
    # G02: Recursive pattern (**/*.py)
    # =========================================================================

    @pytest.mark.unit
    @pytest.mark.tools
    def test_glob_recursive_pattern(self, structured_dir, check_success):
        """G02: Match all .py files recursively."""
        result = _glob_files("**/*.py", str(structured_dir))

        check_success(result)
        # Should include all Python files
        content = result.content
        assert "main.py" in content
        assert "app.py" in content
        assert "utils.py" in content
        assert "core.py" in content
        assert "test_main.py" in content
        assert "test_app.py" in content
        assert result.observation.metadata["match_count"] == 6

    @pytest.mark.unit
    @pytest.mark.tools
    def test_glob_recursive_subdir(self, structured_dir, check_success):
        """Match files in specific subdirectory recursively."""
        result = _glob_files("**/*.py", str(structured_dir / "src"))

        check_success(result)
        assert "app.py" in result.content
        assert "core.py" in result.content
        # Should not include files outside src
        assert "main.py" not in result.content

    # =========================================================================
    # G03: No match pattern
    # =========================================================================

    @pytest.mark.unit
    @pytest.mark.tools
    def test_glob_no_match(self, structured_dir, check_success):
        """G03: Return message when no files match."""
        result = _glob_files("*.xyz", str(structured_dir))

        check_success(result)
        assert "未找到匹配" in result.content
        assert "*.xyz" in result.content
        assert result.observation.metadata["match_count"] == 0

    @pytest.mark.unit
    @pytest.mark.tools
    def test_glob_no_match_recursive(self, structured_dir, check_success):
        """No match with recursive pattern."""
        result = _glob_files("**/*.nonexistent", str(structured_dir))

        check_success(result)
        assert "未找到匹配" in result.content

    # =========================================================================
    # G04 & G05: Result limits and truncation
    # =========================================================================

    @pytest.mark.unit
    @pytest.mark.tools
    def test_glob_exactly_100_results(self, temp_dir, check_success):
        """G04: Handle exactly 100 results without truncation."""
        # Create exactly 100 files
        for i in range(100):
            (temp_dir / f"file_{i:03d}.txt").write_text(f"content {i}")

        result = _glob_files("*.txt", str(temp_dir))

        check_success(result)
        assert result.observation.metadata["match_count"] == 100
        assert result.observation.metadata["truncated"] is False
        assert "已截断" not in result.content

    @pytest.mark.unit
    @pytest.mark.tools
    def test_glob_over_100_results_truncated(self, many_files_dir, check_success):
        """G05: Truncate results when over 100 files."""
        result = _glob_files("*.txt", str(many_files_dir))

        check_success(result)
        assert result.observation.metadata["match_count"] == GLOB_MAX_RESULTS
        assert result.observation.metadata["truncated"] is True
        assert "已截断" in result.content
        assert str(GLOB_MAX_RESULTS) in result.content

    # =========================================================================
    # G06: Non-existent path
    # =========================================================================

    @pytest.mark.unit
    @pytest.mark.tools
    def test_glob_nonexistent_path(self, check_failure):
        """G06: Return error for non-existent base path."""
        result = _glob_files("*.py", "/nonexistent/path/to/search")

        check_failure(result, "路径不存在")

    # =========================================================================
    # G07: File path instead of directory
    # =========================================================================

    @pytest.mark.unit
    @pytest.mark.tools
    def test_glob_file_path_fails(self, sample_file, check_failure):
        """G07: Return error when path is a file, not directory."""
        result = _glob_files("*.txt", str(sample_file))

        check_failure(result, "路径不是目录")

    # =========================================================================
    # G08: Sort by modification time
    # =========================================================================

    @pytest.mark.unit
    @pytest.mark.tools
    def test_glob_sorted_by_mtime(self, temp_dir, check_success):
        """G08: Results should be sorted by modification time (newest first)."""
        # Create files with different mtimes
        file1 = temp_dir / "first.txt"
        file1.write_text("first")

        time.sleep(0.1)  # Small delay to ensure different mtime

        file2 = temp_dir / "second.txt"
        file2.write_text("second")

        time.sleep(0.1)

        file3 = temp_dir / "third.txt"
        file3.write_text("third")

        result = _glob_files("*.txt", str(temp_dir))

        check_success(result)
        lines = result.content.strip().split("\n")
        # Most recent file should be first
        assert lines[0] == "third.txt"
        assert lines[1] == "second.txt"
        assert lines[2] == "first.txt"

    # =========================================================================
    # Additional edge cases
    # =========================================================================

    @pytest.mark.unit
    @pytest.mark.tools
    def test_glob_default_path(self, check_success):
        """Test glob with default path (current directory)."""
        result = _glob_files("*.py")  # No path specified

        # Should succeed (may or may not find files depending on CWD)
        # At minimum, it should not error
        assert result.observation is not None

    @pytest.mark.unit
    @pytest.mark.tools
    def test_glob_metadata(self, structured_dir):
        """Verify metadata is correctly populated."""
        result = _glob_files("**/*.py", str(structured_dir))

        assert result.observation.metadata is not None
        assert result.observation.metadata["pattern"] == "**/*.py"
        assert "base_path" in result.observation.metadata
        assert "match_count" in result.observation.metadata
        assert "truncated" in result.observation.metadata

    @pytest.mark.unit
    @pytest.mark.tools
    def test_glob_observation_source(self, structured_dir):
        """Verify observation source is correctly set."""
        result = _glob_files("*.py", str(structured_dir))

        from funnel_canary.provenance import ObservationType

        assert result.observation.source_type == ObservationType.TOOL_RETURN
        assert result.observation.source_id == "Glob"
        assert result.observation.confidence == 1.0
        assert result.observation.ttl_seconds is None

    @pytest.mark.unit
    @pytest.mark.tools
    def test_glob_only_files_not_directories(self, structured_dir, check_success):
        """Ensure glob only returns files, not directories."""
        result = _glob_files("*", str(structured_dir))

        check_success(result)
        content = result.content
        # Should include files but not directory names as matches
        assert "main.py" in content
        assert "README.md" in content
