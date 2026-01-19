"""Unit tests for the python_exec tool.

Test cases based on boundary testing plan:
- P01: Simple print
- P02: math module
- P03: datetime module
- P04: json module
- P05: No output
- P06: Forbidden import os
- P07: Forbidden open()
- P08: Forbidden eval()
- P09: Syntax error
- P10: Runtime error (ZeroDivisionError)
- P11: Built-in functions
"""

import pytest

from funnel_canary.tools.categories.compute import _python_exec


class TestPythonExecAllowedOperations:
    """Test cases for allowed Python operations."""

    # =========================================================================
    # P01: Simple print
    # =========================================================================

    @pytest.mark.unit
    @pytest.mark.tools
    def test_simple_print(self, check_success):
        """P01: Execute simple print statement."""
        result = _python_exec('print("hi")')

        check_success(result)
        assert "hi" in result.content

    @pytest.mark.unit
    @pytest.mark.tools
    def test_print_multiple_args(self, check_success):
        """Print with multiple arguments."""
        result = _python_exec('print("hello", "world")')

        check_success(result)
        assert "hello world" in result.content

    # =========================================================================
    # P02: math module
    # =========================================================================

    @pytest.mark.unit
    @pytest.mark.tools
    def test_math_sqrt(self, check_success):
        """P02: Use math.sqrt function."""
        result = _python_exec('print(math.sqrt(16))')

        check_success(result)
        assert "4.0" in result.content

    @pytest.mark.unit
    @pytest.mark.tools
    def test_math_pi(self, check_success):
        """Use math.pi constant."""
        result = _python_exec('print(round(math.pi, 2))')

        check_success(result)
        assert "3.14" in result.content

    @pytest.mark.unit
    @pytest.mark.tools
    def test_math_ceil_floor(self, check_success):
        """Use math.ceil and math.floor."""
        result = _python_exec('print(math.ceil(3.2), math.floor(3.8))')

        check_success(result)
        assert "4" in result.content
        assert "3" in result.content

    # =========================================================================
    # P03: datetime module
    # =========================================================================

    @pytest.mark.unit
    @pytest.mark.tools
    def test_datetime_now(self, check_success):
        """P03: Use datetime.now()."""
        result = _python_exec('print(datetime.datetime.now().year)')

        check_success(result)
        # Should contain a year (4 digits)
        assert any(char.isdigit() for char in result.content)

    @pytest.mark.unit
    @pytest.mark.tools
    def test_datetime_date(self, check_success):
        """Use datetime.date."""
        result = _python_exec('print(datetime.date(2024, 1, 1))')

        check_success(result)
        assert "2024" in result.content

    # =========================================================================
    # P04: json module
    # =========================================================================

    @pytest.mark.unit
    @pytest.mark.tools
    def test_json_dumps(self, check_success):
        """P04: Use json.dumps."""
        result = _python_exec('print(json.dumps({"key": "value"}))')

        check_success(result)
        assert '"key"' in result.content
        assert '"value"' in result.content

    @pytest.mark.unit
    @pytest.mark.tools
    def test_json_loads(self, check_success):
        """Use json.loads."""
        result = _python_exec('data = json.loads(\'{"a": 1}\')\nprint(data["a"])')

        check_success(result)
        assert "1" in result.content

    # =========================================================================
    # P05: No output
    # =========================================================================

    @pytest.mark.unit
    @pytest.mark.tools
    def test_no_output(self, check_success):
        """P05: Code with no output."""
        result = _python_exec('x = 1')

        check_success(result)
        # Should indicate no output or successful completion
        assert "无输出" in result.content or "完成" in result.content

    @pytest.mark.unit
    @pytest.mark.tools
    def test_only_assignment(self, check_success):
        """Only variable assignments."""
        result = _python_exec('x = 1\ny = 2\nz = x + y')

        check_success(result)

    # =========================================================================
    # P11: Built-in functions
    # =========================================================================

    @pytest.mark.unit
    @pytest.mark.tools
    def test_builtin_len(self, check_success):
        """P11: Use len() built-in."""
        result = _python_exec('print(len([1, 2, 3]))')

        check_success(result)
        assert "3" in result.content

    @pytest.mark.unit
    @pytest.mark.tools
    def test_builtin_sum(self, check_success):
        """Use sum() built-in."""
        result = _python_exec('print(sum([1, 2, 3, 4, 5]))')

        check_success(result)
        assert "15" in result.content

    @pytest.mark.unit
    @pytest.mark.tools
    def test_builtin_sorted(self, check_success):
        """Use sorted() built-in."""
        result = _python_exec('print(sorted([3, 1, 4, 1, 5]))')

        check_success(result)
        assert "[1, 1, 3, 4, 5]" in result.content

    @pytest.mark.unit
    @pytest.mark.tools
    def test_builtin_range(self, check_success):
        """Use range() built-in."""
        result = _python_exec('print(list(range(5)))')

        check_success(result)
        assert "[0, 1, 2, 3, 4]" in result.content

    @pytest.mark.unit
    @pytest.mark.tools
    def test_builtin_filter_map(self, check_success):
        """Use filter() and map()."""
        result = _python_exec('print(list(map(lambda x: x*2, filter(lambda x: x>2, [1,2,3,4]))))')

        check_success(result)
        assert "[6, 8]" in result.content

    @pytest.mark.unit
    @pytest.mark.tools
    def test_list_comprehension(self, check_success):
        """Use list comprehension."""
        result = _python_exec('print([x**2 for x in range(5)])')

        check_success(result)
        assert "[0, 1, 4, 9, 16]" in result.content


class TestPythonExecForbiddenOperations:
    """Test cases for forbidden Python operations."""

    # =========================================================================
    # P06: Forbidden import os
    # =========================================================================

    @pytest.mark.unit
    @pytest.mark.tools
    def test_import_os_forbidden(self, check_failure):
        """P06: Import os should be forbidden."""
        result = _python_exec('import os')

        check_failure(result)

    @pytest.mark.unit
    @pytest.mark.tools
    def test_import_subprocess_forbidden(self, check_failure):
        """Import subprocess should be forbidden."""
        result = _python_exec('import subprocess')

        check_failure(result)

    @pytest.mark.unit
    @pytest.mark.tools
    def test_import_sys_forbidden(self, check_failure):
        """Import sys should be forbidden."""
        result = _python_exec('import sys')

        check_failure(result)

    # =========================================================================
    # P07: Forbidden open()
    # =========================================================================

    @pytest.mark.unit
    @pytest.mark.tools
    def test_open_forbidden(self, check_failure):
        """P07: open() function should be forbidden."""
        result = _python_exec('f = open("test.txt")')

        check_failure(result)

    @pytest.mark.unit
    @pytest.mark.tools
    def test_open_with_context_manager(self, check_failure):
        """open() with context manager should be forbidden."""
        result = _python_exec('with open("test.txt") as f: pass')

        check_failure(result)

    # =========================================================================
    # P08: Forbidden eval()
    # =========================================================================

    @pytest.mark.unit
    @pytest.mark.tools
    def test_eval_forbidden(self, check_failure):
        """P08: eval() should be forbidden."""
        result = _python_exec('eval("1+1")')

        check_failure(result)

    @pytest.mark.unit
    @pytest.mark.tools
    def test_exec_forbidden(self, check_failure):
        """exec() should be forbidden."""
        result = _python_exec('exec("print(1)")')

        check_failure(result)

    @pytest.mark.unit
    @pytest.mark.tools
    def test_compile_forbidden(self, check_failure):
        """compile() should be forbidden."""
        result = _python_exec('compile("1+1", "", "eval")')

        check_failure(result)


class TestPythonExecErrors:
    """Test cases for Python error handling."""

    # =========================================================================
    # P09: Syntax error
    # =========================================================================

    @pytest.mark.unit
    @pytest.mark.tools
    def test_syntax_error(self, check_failure):
        """P09: Syntax error should be reported."""
        result = _python_exec('print(')

        check_failure(result, "SyntaxError")

    @pytest.mark.unit
    @pytest.mark.tools
    def test_indentation_error(self, check_failure):
        """Indentation error should be reported."""
        result = _python_exec('if True:\nprint("wrong indent")')

        check_failure(result)

    # =========================================================================
    # P10: Runtime error (ZeroDivisionError)
    # =========================================================================

    @pytest.mark.unit
    @pytest.mark.tools
    def test_zero_division_error(self, check_failure):
        """P10: ZeroDivisionError should be reported."""
        result = _python_exec('print(1/0)')

        check_failure(result, "ZeroDivisionError")

    @pytest.mark.unit
    @pytest.mark.tools
    def test_name_error(self, check_failure):
        """NameError should be reported."""
        result = _python_exec('print(undefined_variable)')

        check_failure(result, "NameError")

    @pytest.mark.unit
    @pytest.mark.tools
    def test_type_error(self, check_failure):
        """TypeError should be reported."""
        result = _python_exec('print("hello" + 123)')

        check_failure(result, "TypeError")

    @pytest.mark.unit
    @pytest.mark.tools
    def test_index_error(self, check_failure):
        """IndexError should be reported."""
        result = _python_exec('lst = [1, 2, 3]\nprint(lst[10])')

        check_failure(result, "IndexError")

    @pytest.mark.unit
    @pytest.mark.tools
    def test_key_error(self, check_failure):
        """KeyError should be reported."""
        result = _python_exec('d = {"a": 1}\nprint(d["b"])')

        check_failure(result, "KeyError")


class TestPythonExecMetadata:
    """Test cases for metadata and observation."""

    @pytest.mark.unit
    @pytest.mark.tools
    def test_metadata_code_length(self):
        """Verify code_length metadata."""
        code = 'print("hello")'
        result = _python_exec(code)

        assert result.observation.metadata["code_length"] == len(code)

    @pytest.mark.unit
    @pytest.mark.tools
    def test_metadata_has_output(self):
        """Verify has_output metadata."""
        result = _python_exec('print("output")')
        assert result.observation.metadata["has_output"] is True

        result2 = _python_exec('x = 1')
        assert result2.observation.metadata["has_output"] is False

    @pytest.mark.unit
    @pytest.mark.tools
    def test_observation_source(self):
        """Verify observation source is correctly set."""
        result = _python_exec('print(1)')

        from funnel_canary.provenance import ObservationType

        assert result.observation.source_type == ObservationType.TOOL_RETURN
        assert result.observation.source_id == "python_exec"
        assert result.observation.confidence == 1.0
        assert result.observation.ttl_seconds is None

    @pytest.mark.unit
    @pytest.mark.tools
    def test_observation_scope(self):
        """Verify observation scope."""
        result = _python_exec('print(1)')

        assert result.observation.scope == "computation"
