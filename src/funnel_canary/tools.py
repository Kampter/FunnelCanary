"""Tool definitions and execution for FunnelCanary agent."""

import contextlib
import io
import re
from html.parser import HTMLParser
from typing import Any

import httpx


# Tool definitions for OpenAI function calling
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "web_search",
            "description": "搜索互联网获取最新信息。当需要查询实时数据、新闻、天气、汇率等信息时使用。",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "搜索关键词",
                    }
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read_url",
            "description": "读取指定URL的网页内容。当需要获取特定网页的详细信息时使用。",
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {
                        "type": "string",
                        "description": "要读取的URL地址",
                    }
                },
                "required": ["url"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "ask_user",
            "description": "向用户询问澄清信息。当问题不明确或需要用户提供更多信息时使用。",
            "parameters": {
                "type": "object",
                "properties": {
                    "question": {
                        "type": "string",
                        "description": "要询问用户的问题",
                    }
                },
                "required": ["question"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "python_exec",
            "description": "执行Python代码进行计算。当需要进行数学计算、数据处理或逻辑运算时使用。",
            "parameters": {
                "type": "object",
                "properties": {
                    "code": {
                        "type": "string",
                        "description": "要执行的Python代码",
                    }
                },
                "required": ["code"],
            },
        },
    },
]


class HTMLTextExtractor(HTMLParser):
    """Simple HTML parser that extracts text content."""

    def __init__(self):
        super().__init__()
        self.text_parts: list[str] = []
        self.skip_tags = {"script", "style", "noscript"}
        self.current_skip = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in self.skip_tags:
            self.current_skip = True

    def handle_endtag(self, tag: str) -> None:
        if tag in self.skip_tags:
            self.current_skip = False

    def handle_data(self, data: str) -> None:
        if not self.current_skip:
            text = data.strip()
            if text:
                self.text_parts.append(text)

    def get_text(self) -> str:
        return " ".join(self.text_parts)


def extract_text_from_html(html: str) -> str:
    """Extract readable text from HTML content."""
    parser = HTMLTextExtractor()
    parser.feed(html)
    return parser.get_text()


def web_search(query: str) -> str:
    """Search the web using DuckDuckGo HTML search.

    Args:
        query: Search query string.

    Returns:
        Search results as formatted text.
    """
    try:
        url = "https://html.duckduckgo.com/html/"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }

        with httpx.Client(timeout=30, follow_redirects=True) as client:
            response = client.post(url, data={"q": query}, headers=headers)
            response.raise_for_status()
            html = response.text

        # Extract search results
        results = []

        # Find result snippets using regex
        # DuckDuckGo HTML format: result__snippet class contains the description
        snippet_pattern = r'class="result__snippet"[^>]*>(.*?)</a>'
        title_pattern = r'class="result__a"[^>]*>(.*?)</a>'

        snippets = re.findall(snippet_pattern, html, re.DOTALL)
        titles = re.findall(title_pattern, html, re.DOTALL)

        for i, (title, snippet) in enumerate(zip(titles[:5], snippets[:5])):
            # Clean HTML tags
            title_clean = re.sub(r'<[^>]+>', '', title).strip()
            snippet_clean = re.sub(r'<[^>]+>', '', snippet).strip()
            if title_clean and snippet_clean:
                results.append(f"{i+1}. {title_clean}\n   {snippet_clean}")

        if results:
            return "\n\n".join(results)
        else:
            return f"未找到与 '{query}' 相关的搜索结果"

    except httpx.HTTPError as e:
        return f"搜索失败: {e}"
    except Exception as e:
        return f"搜索出错: {e}"


def read_url(url: str) -> str:
    """Read and extract text content from a URL.

    Args:
        url: The URL to fetch.

    Returns:
        Extracted text content from the page.
    """
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }

        with httpx.Client(timeout=30, follow_redirects=True) as client:
            response = client.get(url, headers=headers)
            response.raise_for_status()
            html = response.text

        text = extract_text_from_html(html)

        # Limit text length to avoid token overflow
        max_length = 4000
        if len(text) > max_length:
            text = text[:max_length] + "...[内容已截断]"

        return text if text else "无法提取页面内容"

    except httpx.HTTPError as e:
        return f"读取URL失败: {e}"
    except Exception as e:
        return f"读取出错: {e}"


def ask_user(question: str) -> str:
    """Ask the user a clarifying question.

    Args:
        question: The question to ask.

    Returns:
        User's response.
    """
    print(f"\n❓ Agent 询问: {question}")
    response = input("您的回答: ")
    return response


def python_exec(code: str) -> str:
    """Execute Python code in a sandboxed environment.

    Args:
        code: Python code to execute.

    Returns:
        Output from the code execution.
    """
    # Create a restricted globals environment
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
    import math
    import datetime
    import json
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


def execute_tool(name: str, arguments: dict[str, Any]) -> str:
    """Execute a tool by name with given arguments.

    Args:
        name: Tool name.
        arguments: Tool arguments.

    Returns:
        Tool execution result.
    """
    if name == "web_search":
        return web_search(arguments["query"])
    elif name == "read_url":
        return read_url(arguments["url"])
    elif name == "ask_user":
        return ask_user(arguments["question"])
    elif name == "python_exec":
        return python_exec(arguments["code"])
    else:
        return f"未知工具: {name}"
