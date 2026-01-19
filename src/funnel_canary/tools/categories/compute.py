"""Compute tools for calculations and code execution.

Includes Python sandbox execution and shell command execution (Agent SDK compatible).
"""

import contextlib
import datetime
import io
import json
import math
import subprocess
from typing import Any

from ..base import Tool, ToolMetadata, ToolParameter, ToolResult
from ...cognitive.safety import ToolRisk


# Python execution results don't expire (deterministic)
PYTHON_EXEC_TTL = None


def _python_exec(code: str) -> ToolResult:
    """Execute Python code in a sandboxed environment.

    Args:
        code: Python code to execute.

    Returns:
        ToolResult with execution output and provenance information.
    """
    tool_name = "python_exec"

    safe_builtins = {
        "abs": abs,
        "all": all,
        "any": any,
        "bool": bool,
        "dict": dict,
        "enumerate": enumerate,
        "filter": filter,
        "float": float,
        "int": int,
        "len": len,
        "list": list,
        "map": map,
        "max": max,
        "min": min,
        "pow": pow,
        "print": print,
        "range": range,
        "reversed": reversed,
        "round": round,
        "set": set,
        "sorted": sorted,
        "str": str,
        "sum": sum,
        "tuple": tuple,
        "zip": zip,
        "__import__": lambda name: __import__(name) if name in ["math", "datetime", "json", "re"] else None,
    }

    safe_globals: dict[str, Any] = {"__builtins__": safe_builtins}

    # Allow importing safe modules
    safe_globals["math"] = math
    safe_globals["datetime"] = datetime
    safe_globals["json"] = json

    # Capture stdout
    stdout_capture = io.StringIO()

    try:
        with contextlib.redirect_stdout(stdout_capture):
            exec(code, safe_globals)

        output = stdout_capture.getvalue()
        result_content = output.strip() if output.strip() else "代码执行完成（无输出）"

        return ToolResult.from_success(
            content=result_content,
            tool_name=tool_name,
            confidence=1.0,  # Deterministic computation
            ttl_seconds=PYTHON_EXEC_TTL,
            scope="computation",
            metadata={
                "code_length": len(code),
                "has_output": bool(output.strip()),
            },
        )

    except Exception as e:
        return ToolResult.from_error(f"执行错误: {type(e).__name__}: {e}", tool_name)


# Tool definitions
python_exec = Tool(
    metadata=ToolMetadata(
        name="python_exec",
        description="执行Python代码进行计算。当需要进行数学计算、数据处理或逻辑运算时使用。",
        category="compute",
        parameters=[
            ToolParameter(
                name="code",
                type="string",
                description="要执行的Python代码",
                required=True,
            )
        ],
        skill_bindings=["calculation", "problem_decomposition"],
    ),
    execute=_python_exec,
)

# Bash tool configuration
BASH_DEFAULT_TIMEOUT = 30  # Default timeout in seconds
BASH_MAX_TIMEOUT = 300     # Maximum timeout in seconds

# Dangerous commands that should be blocked
BASH_COMMAND_BLACKLIST = [
    "rm -rf /",
    "rm -rf /*",
    "rm -rf ~",
    "rm -rf ~/",
    "dd if=",
    "mkfs",
    "shutdown",
    "reboot",
    "poweroff",
    "init 0",
    "init 6",
    ":(){:|:&};:",  # Fork bomb
    "> /dev/sda",
    "mv /* ",
    "chmod -R 777 /",
]


def _is_command_safe(command: str) -> tuple[bool, str | None]:
    """Check if a command is safe to execute.

    Args:
        command: The shell command to check.

    Returns:
        Tuple of (is_safe, error_message).
    """
    command_lower = command.lower().strip()

    for dangerous in BASH_COMMAND_BLACKLIST:
        if dangerous.lower() in command_lower:
            return False, f"命令包含危险操作: {dangerous}"

    return True, None


def _bash_exec(command: str, timeout: int = BASH_DEFAULT_TIMEOUT) -> ToolResult:
    """Execute a shell command.

    Args:
        command: Shell command to execute.
        timeout: Timeout in seconds (default: 30, max: 300).

    Returns:
        ToolResult with command output and provenance information.
    """
    tool_name = "Bash"

    # Validate timeout
    if timeout <= 0:
        timeout = BASH_DEFAULT_TIMEOUT
    if timeout > BASH_MAX_TIMEOUT:
        timeout = BASH_MAX_TIMEOUT

    # Security check
    is_safe, error_msg = _is_command_safe(command)
    if not is_safe:
        return ToolResult.from_error(f"安全检查失败: {error_msg}", tool_name)

    try:
        # Execute command
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=None,  # Use current directory
        )

        # Combine stdout and stderr
        output_parts = []
        if result.stdout:
            output_parts.append(result.stdout)
        if result.stderr:
            output_parts.append(f"[stderr]\n{result.stderr}")

        output = "\n".join(output_parts).strip()

        if result.returncode == 0:
            content = output if output else "命令执行成功（无输出）"
            return ToolResult.from_success(
                content=content,
                tool_name=tool_name,
                confidence=0.9,  # Shell commands may have side effects
                ttl_seconds=None,  # Output may change on next run
                scope=f"bash:{command[:50]}",
                metadata={
                    "command": command,
                    "return_code": result.returncode,
                    "has_output": bool(output),
                    "timeout": timeout,
                },
            )
        else:
            # Command failed but executed
            error_output = output if output else f"命令返回错误码: {result.returncode}"
            return ToolResult.from_error(error_output, tool_name)

    except subprocess.TimeoutExpired:
        return ToolResult.from_error(f"命令执行超时 ({timeout}秒)", tool_name)
    except Exception as e:
        return ToolResult.from_error(f"执行命令失败: {type(e).__name__}: {e}", tool_name)


Bash = Tool(
    metadata=ToolMetadata(
        name="Bash",
        description="执行 Shell 命令。用于系统操作、文件处理、自动化任务等。",
        category="compute",
        parameters=[
            ToolParameter(
                name="command",
                type="string",
                description="要执行的 Shell 命令",
                required=True,
            ),
            ToolParameter(
                name="timeout",
                type="integer",
                description="超时时间（秒），默认 30 秒，最大 300 秒",
                required=False,
            ),
        ],
        skill_bindings=["code_analysis", "planning"],
        risk_level=ToolRisk.MEDIUM,
    ),
    execute=_bash_exec,
)

# Export all tools from this category
COMPUTE_TOOLS = [python_exec, Bash]
