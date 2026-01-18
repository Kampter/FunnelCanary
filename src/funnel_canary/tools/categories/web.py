"""Web-related tools."""

import re
from html.parser import HTMLParser

import httpx

from ..base import Tool, ToolMetadata, ToolParameter


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


def _web_search(query: str) -> str:
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

        results = []

        snippet_pattern = r'class="result__snippet"[^>]*>(.*?)</a>'
        title_pattern = r'class="result__a"[^>]*>(.*?)</a>'

        snippets = re.findall(snippet_pattern, html, re.DOTALL)
        titles = re.findall(title_pattern, html, re.DOTALL)

        for i, (title, snippet) in enumerate(zip(titles[:5], snippets[:5])):
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


def _read_url(url: str) -> str:
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

        max_length = 4000
        if len(text) > max_length:
            text = text[:max_length] + "...[内容已截断]"

        return text if text else "无法提取页面内容"

    except httpx.HTTPError as e:
        return f"读取URL失败: {e}"
    except Exception as e:
        return f"读取出错: {e}"


# Tool definitions
web_search = Tool(
    metadata=ToolMetadata(
        name="web_search",
        description="搜索互联网获取最新信息。当需要查询实时数据、新闻、天气、汇率等信息时使用。",
        category="web",
        parameters=[
            ToolParameter(
                name="query",
                type="string",
                description="搜索关键词",
                required=True,
            )
        ],
        skill_bindings=["research"],
    ),
    execute=_web_search,
)

read_url = Tool(
    metadata=ToolMetadata(
        name="read_url",
        description="读取指定URL的网页内容。当需要获取特定网页的详细信息时使用。",
        category="web",
        parameters=[
            ToolParameter(
                name="url",
                type="string",
                description="要读取的URL地址",
                required=True,
            )
        ],
        skill_bindings=["research"],
    ),
    execute=_read_url,
)

# Export all tools from this category
WEB_TOOLS = [web_search, read_url]
