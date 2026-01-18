"""Compute tools for calculations and code execution."""

import contextlib
import datetime
import io
import json
import math
from typing import Any

from ..base import Tool, ToolMetadata, ToolParameter


def _python_exec(code: str) -> str:
    """Execute Python code in a sandboxed environment.

    Args:
        code: Python code to execute.

    Returns:
        Output from the code execution.
    """
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
        return output.strip() if output.strip() else "代码执行完成（无输出）"

    except Exception as e:
        return f"执行错误: {type(e).__name__}: {e}"


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

# Export all tools from this category
COMPUTE_TOOLS = [python_exec]
