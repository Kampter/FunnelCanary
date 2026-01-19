"""Filesystem-related tools (Agent SDK compatible).

Provides file reading and searching capabilities inspired by Anthropic Agent SDK.
"""

import fnmatch
from pathlib import Path

from ..base import Tool, ToolMetadata, ToolParameter, ToolResult
from ...cognitive.safety import ToolRisk

# Configuration
FILE_READ_MAX = 100_000  # 100KB max file size
GLOB_MAX_RESULTS = 100   # Maximum number of files to return


def _read_file(file_path: str) -> ToolResult:
    """Read content from a local file.

    Args:
        file_path: Path to the file to read.

    Returns:
        ToolResult with file content and provenance information.
    """
    tool_name = "Read"

    try:
        path = Path(file_path).resolve()

        # Security check: file must exist
        if not path.exists():
            return ToolResult.from_error(f"文件不存在: {file_path}", tool_name)

        # Security check: must be a file, not a directory
        if not path.is_file():
            return ToolResult.from_error(f"路径不是文件: {file_path}", tool_name)

        # Check file size
        file_size = path.stat().st_size
        if file_size > FILE_READ_MAX:
            return ToolResult.from_error(
                f"文件过大 ({file_size} bytes > {FILE_READ_MAX} bytes): {file_path}",
                tool_name,
            )

        # Read file content
        try:
            content = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            # Try reading as binary and decode with fallback
            content = path.read_bytes().decode("utf-8", errors="replace")

        return ToolResult.from_success(
            content=content,
            tool_name=tool_name,
            confidence=1.0,  # Deterministic file read
            ttl_seconds=None,  # No expiration for local files
            scope=f"file:{path}",
            metadata={
                "file_path": str(path),
                "file_size": file_size,
                "encoding": "utf-8",
            },
        )

    except PermissionError:
        return ToolResult.from_error(f"权限不足: {file_path}", tool_name)
    except Exception as e:
        return ToolResult.from_error(f"读取文件失败: {type(e).__name__}: {e}", tool_name)


def _glob_files(pattern: str, path: str = ".") -> ToolResult:
    """Search for files matching a glob pattern.

    Args:
        pattern: Glob pattern to match (e.g., "**/*.py", "*.md").
        path: Base directory to search in (default: current directory).

    Returns:
        ToolResult with list of matching files and provenance information.
    """
    tool_name = "Glob"

    try:
        base_path = Path(path).resolve()

        # Security check: base path must exist
        if not base_path.exists():
            return ToolResult.from_error(f"路径不存在: {path}", tool_name)

        # Security check: must be a directory
        if not base_path.is_dir():
            return ToolResult.from_error(f"路径不是目录: {path}", tool_name)

        # Find matching files
        if "**" in pattern:
            # Recursive glob
            matches = list(base_path.glob(pattern))
        else:
            # Non-recursive glob
            matches = list(base_path.glob(pattern))

        # Filter to only files (not directories)
        file_matches = [m for m in matches if m.is_file()]

        # Sort by modification time (newest first)
        file_matches.sort(key=lambda x: x.stat().st_mtime, reverse=True)

        # Limit results
        truncated = len(file_matches) > GLOB_MAX_RESULTS
        if truncated:
            file_matches = file_matches[:GLOB_MAX_RESULTS]

        # Format output
        if file_matches:
            # Convert to relative paths for cleaner output
            try:
                relative_paths = [str(m.relative_to(base_path)) for m in file_matches]
            except ValueError:
                # If relative path fails, use absolute paths
                relative_paths = [str(m) for m in file_matches]

            content = "\n".join(relative_paths)
            if truncated:
                content += f"\n\n[结果已截断，仅显示前 {GLOB_MAX_RESULTS} 个文件]"
        else:
            content = f"未找到匹配 '{pattern}' 的文件"

        return ToolResult.from_success(
            content=content,
            tool_name=tool_name,
            confidence=1.0,  # Deterministic file search
            ttl_seconds=None,  # No expiration for local operations
            scope=f"glob:{path}:{pattern}",
            metadata={
                "pattern": pattern,
                "base_path": str(base_path),
                "match_count": len(file_matches),
                "truncated": truncated,
            },
        )

    except PermissionError:
        return ToolResult.from_error(f"权限不足: {path}", tool_name)
    except Exception as e:
        return ToolResult.from_error(f"搜索文件失败: {type(e).__name__}: {e}", tool_name)


# Tool definitions
Read = Tool(
    metadata=ToolMetadata(
        name="Read",
        description="读取本地文件内容。用于代码分析、文档查阅等场景。",
        category="filesystem",
        parameters=[
            ToolParameter(
                name="file_path",
                type="string",
                description="要读取的文件路径",
                required=True,
            )
        ],
        skill_bindings=["code_analysis", "deep_research"],
        risk_level=ToolRisk.SAFE,
    ),
    execute=_read_file,
)

Glob = Tool(
    metadata=ToolMetadata(
        name="Glob",
        description="按模式搜索文件。用于探索文件结构、查找特定类型的文件。支持 **/*.py 等通配符模式。",
        category="filesystem",
        parameters=[
            ToolParameter(
                name="pattern",
                type="string",
                description="Glob 模式，如 '*.py' 或 '**/*.md'",
                required=True,
            ),
            ToolParameter(
                name="path",
                type="string",
                description="搜索的基础目录（默认为当前目录）",
                required=False,
            ),
        ],
        skill_bindings=["code_analysis", "deep_research", "planning"],
        risk_level=ToolRisk.SAFE,
    ),
    execute=_glob_files,
)

# Export all tools from this category
FILESYSTEM_TOOLS = [Read, Glob]
