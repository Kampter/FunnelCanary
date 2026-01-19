"""Unit tests for the web_search tool.

Test cases based on boundary testing plan:
- W01: Normal search (returns results)
- W02: Result limit (max 5)
- W03: No results
- W04: Network error
- W05: Timeout
- W06: TTL verification
"""

from unittest.mock import MagicMock, patch

import httpx
import pytest

from funnel_canary.tools.categories.web import _web_search, WEB_SEARCH_TTL


class TestWebSearchSuccess:
    """Test cases for successful web search operations."""

    # =========================================================================
    # W01: Normal search (returns results)
    # =========================================================================

    @pytest.mark.unit
    @pytest.mark.tools
    def test_normal_search_with_results(self, check_success):
        """W01: Normal search returns results."""
        html_response = '''
        <html><body>
        <div class="result">
            <a class="result__a" href="#">Python Tutorial - Learn Python</a>
            <a class="result__snippet">Learn Python programming language basics</a>
            <a class="result__url">https://python.org/tutorial</a>
        </div>
        <div class="result">
            <a class="result__a" href="#">Python Documentation</a>
            <a class="result__snippet">Official Python documentation and guides</a>
            <a class="result__url">https://docs.python.org</a>
        </div>
        </body></html>
        '''

        with patch("httpx.Client") as mock_client:
            mock_response = MagicMock()
            mock_response.text = html_response
            mock_response.raise_for_status = MagicMock()

            mock_instance = MagicMock()
            mock_instance.post.return_value = mock_response
            mock_client.return_value.__enter__ = MagicMock(return_value=mock_instance)
            mock_client.return_value.__exit__ = MagicMock(return_value=False)

            result = _web_search("python tutorial")

            check_success(result)
            assert "Python" in result.content
            assert result.observation.metadata["query"] == "python tutorial"
            assert result.observation.metadata["result_count"] >= 1

    @pytest.mark.unit
    @pytest.mark.tools
    def test_search_results_numbered(self, check_success):
        """Search results should be numbered."""
        html_response = '''
        <html><body>
        <a class="result__a">Result One</a>
        <a class="result__snippet">Snippet one</a>
        <a class="result__url">https://one.com</a>
        <a class="result__a">Result Two</a>
        <a class="result__snippet">Snippet two</a>
        <a class="result__url">https://two.com</a>
        </body></html>
        '''

        with patch("httpx.Client") as mock_client:
            mock_response = MagicMock()
            mock_response.text = html_response
            mock_response.raise_for_status = MagicMock()

            mock_instance = MagicMock()
            mock_instance.post.return_value = mock_response
            mock_client.return_value.__enter__ = MagicMock(return_value=mock_instance)
            mock_client.return_value.__exit__ = MagicMock(return_value=False)

            result = _web_search("test query")

            check_success(result)
            assert "1." in result.content

    # =========================================================================
    # W02: Result limit (max 5)
    # =========================================================================

    @pytest.mark.unit
    @pytest.mark.tools
    def test_result_limit_max_5(self, check_success):
        """W02: Results should be limited to 5."""
        # Create HTML with more than 5 results
        results_html = ""
        for i in range(10):
            results_html += f'''
            <a class="result__a">Result {i}</a>
            <a class="result__snippet">Snippet {i}</a>
            <a class="result__url">https://example{i}.com</a>
            '''

        html_response = f"<html><body>{results_html}</body></html>"

        with patch("httpx.Client") as mock_client:
            mock_response = MagicMock()
            mock_response.text = html_response
            mock_response.raise_for_status = MagicMock()

            mock_instance = MagicMock()
            mock_instance.post.return_value = mock_response
            mock_client.return_value.__enter__ = MagicMock(return_value=mock_instance)
            mock_client.return_value.__exit__ = MagicMock(return_value=False)

            result = _web_search("many results")

            check_success(result)
            # Should have at most 5 results
            assert result.observation.metadata["result_count"] <= 5

    # =========================================================================
    # W03: No results
    # =========================================================================

    @pytest.mark.unit
    @pytest.mark.tools
    def test_no_results_found(self, check_success):
        """W03: Handle case when no results found."""
        html_response = "<html><body><div>No results found</div></body></html>"

        with patch("httpx.Client") as mock_client:
            mock_response = MagicMock()
            mock_response.text = html_response
            mock_response.raise_for_status = MagicMock()

            mock_instance = MagicMock()
            mock_instance.post.return_value = mock_response
            mock_client.return_value.__enter__ = MagicMock(return_value=mock_instance)
            mock_client.return_value.__exit__ = MagicMock(return_value=False)

            result = _web_search("xyznonexistent123456")

            check_success(result)
            assert "未找到" in result.content
            assert result.observation.confidence == 0.5  # Lower confidence for no results
            assert result.observation.metadata["result_count"] == 0

    # =========================================================================
    # W06: TTL verification
    # =========================================================================

    @pytest.mark.unit
    @pytest.mark.tools
    def test_ttl_is_set(self):
        """W06: Verify TTL is set correctly."""
        html_response = '''
        <html><body>
        <a class="result__a">Test Result</a>
        <a class="result__snippet">Test snippet</a>
        <a class="result__url">https://test.com</a>
        </body></html>
        '''

        with patch("httpx.Client") as mock_client:
            mock_response = MagicMock()
            mock_response.text = html_response
            mock_response.raise_for_status = MagicMock()

            mock_instance = MagicMock()
            mock_instance.post.return_value = mock_response
            mock_client.return_value.__enter__ = MagicMock(return_value=mock_instance)
            mock_client.return_value.__exit__ = MagicMock(return_value=False)

            result = _web_search("test")

            assert result.observation.ttl_seconds == WEB_SEARCH_TTL
            assert result.observation.ttl_seconds == 3600  # 1 hour


class TestWebSearchErrors:
    """Test cases for web search error handling."""

    # =========================================================================
    # W04: Network error
    # =========================================================================

    @pytest.mark.unit
    @pytest.mark.tools
    def test_network_error(self, check_failure):
        """W04: Handle network errors gracefully."""
        with patch("httpx.Client") as mock_client:
            mock_instance = MagicMock()
            mock_instance.post.side_effect = httpx.HTTPError("Connection failed")
            mock_client.return_value.__enter__ = MagicMock(return_value=mock_instance)
            mock_client.return_value.__exit__ = MagicMock(return_value=False)

            result = _web_search("test query")

            check_failure(result, "搜索失败")

    @pytest.mark.unit
    @pytest.mark.tools
    def test_http_error_status(self, check_failure):
        """Handle HTTP error status codes."""
        with patch("httpx.Client") as mock_client:
            mock_response = MagicMock()
            mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
                "Server error",
                request=MagicMock(),
                response=MagicMock(status_code=500),
            )

            mock_instance = MagicMock()
            mock_instance.post.return_value = mock_response
            mock_client.return_value.__enter__ = MagicMock(return_value=mock_instance)
            mock_client.return_value.__exit__ = MagicMock(return_value=False)

            result = _web_search("test query")

            check_failure(result)

    # =========================================================================
    # W05: Timeout
    # =========================================================================

    @pytest.mark.unit
    @pytest.mark.tools
    def test_timeout_error(self, check_failure):
        """W05: Handle timeout errors."""
        with patch("httpx.Client") as mock_client:
            mock_instance = MagicMock()
            mock_instance.post.side_effect = httpx.TimeoutException("Request timed out")
            mock_client.return_value.__enter__ = MagicMock(return_value=mock_instance)
            mock_client.return_value.__exit__ = MagicMock(return_value=False)

            result = _web_search("test query")

            check_failure(result)


class TestWebSearchMetadata:
    """Test cases for web search metadata and observation."""

    @pytest.mark.unit
    @pytest.mark.tools
    def test_observation_source(self):
        """Verify observation source is correctly set."""
        html_response = '''
        <html><body>
        <a class="result__a">Test</a>
        <a class="result__snippet">Test snippet</a>
        </body></html>
        '''

        with patch("httpx.Client") as mock_client:
            mock_response = MagicMock()
            mock_response.text = html_response
            mock_response.raise_for_status = MagicMock()

            mock_instance = MagicMock()
            mock_instance.post.return_value = mock_response
            mock_client.return_value.__enter__ = MagicMock(return_value=mock_instance)
            mock_client.return_value.__exit__ = MagicMock(return_value=False)

            result = _web_search("test")

            from funnel_canary.provenance import ObservationType

            assert result.observation.source_type == ObservationType.TOOL_RETURN
            assert result.observation.source_id == "web_search"

    @pytest.mark.unit
    @pytest.mark.tools
    def test_metadata_contains_query(self):
        """Verify metadata contains the query."""
        html_response = '<html><body></body></html>'

        with patch("httpx.Client") as mock_client:
            mock_response = MagicMock()
            mock_response.text = html_response
            mock_response.raise_for_status = MagicMock()

            mock_instance = MagicMock()
            mock_instance.post.return_value = mock_response
            mock_client.return_value.__enter__ = MagicMock(return_value=mock_instance)
            mock_client.return_value.__exit__ = MagicMock(return_value=False)

            result = _web_search("my test query")

            assert result.observation.metadata["query"] == "my test query"

    @pytest.mark.unit
    @pytest.mark.tools
    def test_metadata_contains_timestamp(self):
        """Verify metadata contains a timestamp."""
        html_response = '<html><body></body></html>'

        with patch("httpx.Client") as mock_client:
            mock_response = MagicMock()
            mock_response.text = html_response
            mock_response.raise_for_status = MagicMock()

            mock_instance = MagicMock()
            mock_instance.post.return_value = mock_response
            mock_client.return_value.__enter__ = MagicMock(return_value=mock_instance)
            mock_client.return_value.__exit__ = MagicMock(return_value=False)

            result = _web_search("test")

            assert "timestamp" in result.observation.metadata

    @pytest.mark.unit
    @pytest.mark.tools
    def test_observation_scope(self):
        """Verify observation scope contains query."""
        html_response = '<html><body></body></html>'

        with patch("httpx.Client") as mock_client:
            mock_response = MagicMock()
            mock_response.text = html_response
            mock_response.raise_for_status = MagicMock()

            mock_instance = MagicMock()
            mock_instance.post.return_value = mock_response
            mock_client.return_value.__enter__ = MagicMock(return_value=mock_instance)
            mock_client.return_value.__exit__ = MagicMock(return_value=False)

            result = _web_search("test query")

            assert "search:" in result.observation.scope
            assert "test query" in result.observation.scope
