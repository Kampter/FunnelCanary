"""Unit tests for the read_url tool.

Test cases based on boundary testing plan:
- U01: Normal page (successful extraction)
- U02: Content over 4000 characters (truncation)
- U03: Empty page (low confidence)
- U04: HTTP 404 error
- U05: SSL error
- U06: Timeout
- U07: Redirect handling
- U08: TTL verification
"""

from unittest.mock import MagicMock, patch

import httpx
import pytest

from funnel_canary.tools.categories.web import _read_url, WEB_PAGE_TTL


class TestReadUrlSuccess:
    """Test cases for successful URL reading operations."""

    # =========================================================================
    # U01: Normal page (successful extraction)
    # =========================================================================

    @pytest.mark.unit
    @pytest.mark.tools
    def test_normal_page_extraction(self, check_success):
        """U01: Successfully extract content from a normal page."""
        html_response = '''
        <html>
        <head><title>Test Page</title></head>
        <body>
            <h1>Hello World</h1>
            <p>This is a test paragraph with useful content.</p>
            <script>console.log("ignored");</script>
            <style>.ignored { color: red; }</style>
        </body>
        </html>
        '''

        with patch("httpx.Client") as mock_client:
            mock_response = MagicMock()
            mock_response.text = html_response
            mock_response.raise_for_status = MagicMock()

            mock_instance = MagicMock()
            mock_instance.get.return_value = mock_response
            mock_client.return_value.__enter__ = MagicMock(return_value=mock_instance)
            mock_client.return_value.__exit__ = MagicMock(return_value=False)

            result = _read_url("https://example.com")

            check_success(result)
            assert "Hello World" in result.content
            assert "test paragraph" in result.content
            # Script and style content should be excluded
            assert "console.log" not in result.content
            assert ".ignored" not in result.content

    @pytest.mark.unit
    @pytest.mark.tools
    def test_extracts_multiple_paragraphs(self, check_success):
        """Extract content from multiple paragraphs."""
        html_response = '''
        <html><body>
            <p>First paragraph content.</p>
            <p>Second paragraph content.</p>
            <p>Third paragraph content.</p>
        </body></html>
        '''

        with patch("httpx.Client") as mock_client:
            mock_response = MagicMock()
            mock_response.text = html_response
            mock_response.raise_for_status = MagicMock()

            mock_instance = MagicMock()
            mock_instance.get.return_value = mock_response
            mock_client.return_value.__enter__ = MagicMock(return_value=mock_instance)
            mock_client.return_value.__exit__ = MagicMock(return_value=False)

            result = _read_url("https://example.com")

            check_success(result)
            assert "First paragraph" in result.content
            assert "Second paragraph" in result.content
            assert "Third paragraph" in result.content

    # =========================================================================
    # U02: Content over 4000 characters (truncation)
    # =========================================================================

    @pytest.mark.unit
    @pytest.mark.tools
    def test_long_content_truncated(self, check_success):
        """U02: Content longer than 4000 characters is truncated."""
        # Create HTML with very long content
        long_text = "A" * 5000
        html_response = f'<html><body><p>{long_text}</p></body></html>'

        with patch("httpx.Client") as mock_client:
            mock_response = MagicMock()
            mock_response.text = html_response
            mock_response.raise_for_status = MagicMock()

            mock_instance = MagicMock()
            mock_instance.get.return_value = mock_response
            mock_client.return_value.__enter__ = MagicMock(return_value=mock_instance)
            mock_client.return_value.__exit__ = MagicMock(return_value=False)

            result = _read_url("https://example.com")

            check_success(result)
            assert "已截断" in result.content
            assert result.observation.metadata["truncated"] is True
            # Content should be limited
            assert len(result.content) < 5000

    @pytest.mark.unit
    @pytest.mark.tools
    def test_exactly_4000_chars_not_truncated(self, check_success):
        """Content exactly 4000 characters is not truncated."""
        # Create HTML with exactly 4000 chars of content
        text = "A" * 4000
        html_response = f'<html><body><p>{text}</p></body></html>'

        with patch("httpx.Client") as mock_client:
            mock_response = MagicMock()
            mock_response.text = html_response
            mock_response.raise_for_status = MagicMock()

            mock_instance = MagicMock()
            mock_instance.get.return_value = mock_response
            mock_client.return_value.__enter__ = MagicMock(return_value=mock_instance)
            mock_client.return_value.__exit__ = MagicMock(return_value=False)

            result = _read_url("https://example.com")

            check_success(result)
            assert result.observation.metadata.get("truncated", False) is False

    # =========================================================================
    # U03: Empty page (low confidence)
    # =========================================================================

    @pytest.mark.unit
    @pytest.mark.tools
    def test_empty_page_content(self, check_success):
        """U03: Empty page returns low confidence."""
        html_response = '<html><body><script>only script</script></body></html>'

        with patch("httpx.Client") as mock_client:
            mock_response = MagicMock()
            mock_response.text = html_response
            mock_response.raise_for_status = MagicMock()

            mock_instance = MagicMock()
            mock_instance.get.return_value = mock_response
            mock_client.return_value.__enter__ = MagicMock(return_value=mock_instance)
            mock_client.return_value.__exit__ = MagicMock(return_value=False)

            result = _read_url("https://example.com")

            check_success(result)
            # Should have lower confidence for empty content
            assert result.observation.confidence == 0.3
            assert "无法提取" in result.content

    # =========================================================================
    # U08: TTL verification
    # =========================================================================

    @pytest.mark.unit
    @pytest.mark.tools
    def test_ttl_is_set(self):
        """U08: Verify TTL is set correctly."""
        html_response = '<html><body><p>Test content</p></body></html>'

        with patch("httpx.Client") as mock_client:
            mock_response = MagicMock()
            mock_response.text = html_response
            mock_response.raise_for_status = MagicMock()

            mock_instance = MagicMock()
            mock_instance.get.return_value = mock_response
            mock_client.return_value.__enter__ = MagicMock(return_value=mock_instance)
            mock_client.return_value.__exit__ = MagicMock(return_value=False)

            result = _read_url("https://example.com")

            assert result.observation.ttl_seconds == WEB_PAGE_TTL
            assert result.observation.ttl_seconds == 7200  # 2 hours


class TestReadUrlErrors:
    """Test cases for URL reading error handling."""

    # =========================================================================
    # U04: HTTP 404 error
    # =========================================================================

    @pytest.mark.unit
    @pytest.mark.tools
    def test_http_404_error(self, check_failure):
        """U04: Handle 404 Not Found error."""
        with patch("httpx.Client") as mock_client:
            mock_response = MagicMock()
            mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
                "Not Found",
                request=MagicMock(),
                response=MagicMock(status_code=404),
            )

            mock_instance = MagicMock()
            mock_instance.get.return_value = mock_response
            mock_client.return_value.__enter__ = MagicMock(return_value=mock_instance)
            mock_client.return_value.__exit__ = MagicMock(return_value=False)

            result = _read_url("https://example.com/notfound")

            check_failure(result, "读取URL失败")

    @pytest.mark.unit
    @pytest.mark.tools
    def test_http_500_error(self, check_failure):
        """Handle 500 Internal Server Error."""
        with patch("httpx.Client") as mock_client:
            mock_response = MagicMock()
            mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
                "Server Error",
                request=MagicMock(),
                response=MagicMock(status_code=500),
            )

            mock_instance = MagicMock()
            mock_instance.get.return_value = mock_response
            mock_client.return_value.__enter__ = MagicMock(return_value=mock_instance)
            mock_client.return_value.__exit__ = MagicMock(return_value=False)

            result = _read_url("https://example.com")

            check_failure(result)

    # =========================================================================
    # U05: SSL error
    # =========================================================================

    @pytest.mark.unit
    @pytest.mark.tools
    def test_ssl_error(self, check_failure):
        """U05: Handle SSL certificate errors."""
        with patch("httpx.Client") as mock_client:
            mock_instance = MagicMock()
            mock_instance.get.side_effect = httpx.HTTPError("SSL certificate error")
            mock_client.return_value.__enter__ = MagicMock(return_value=mock_instance)
            mock_client.return_value.__exit__ = MagicMock(return_value=False)

            result = _read_url("https://example.com")

            check_failure(result)

    # =========================================================================
    # U06: Timeout
    # =========================================================================

    @pytest.mark.unit
    @pytest.mark.tools
    def test_timeout_error(self, check_failure):
        """U06: Handle timeout errors."""
        with patch("httpx.Client") as mock_client:
            mock_instance = MagicMock()
            mock_instance.get.side_effect = httpx.TimeoutException("Request timed out")
            mock_client.return_value.__enter__ = MagicMock(return_value=mock_instance)
            mock_client.return_value.__exit__ = MagicMock(return_value=False)

            result = _read_url("https://example.com")

            check_failure(result)

    # =========================================================================
    # U07: Redirect handling
    # =========================================================================

    @pytest.mark.unit
    @pytest.mark.tools
    def test_redirect_followed(self, check_success):
        """U07: Redirects should be followed automatically."""
        # Note: httpx with follow_redirects=True handles this internally
        html_response = '<html><body><p>Final destination</p></body></html>'

        with patch("httpx.Client") as mock_client:
            mock_response = MagicMock()
            mock_response.text = html_response
            mock_response.raise_for_status = MagicMock()

            mock_instance = MagicMock()
            mock_instance.get.return_value = mock_response
            mock_client.return_value.__enter__ = MagicMock(return_value=mock_instance)
            mock_client.return_value.__exit__ = MagicMock(return_value=False)

            result = _read_url("https://example.com/redirect")

            check_success(result)
            assert "Final destination" in result.content


class TestReadUrlMetadata:
    """Test cases for URL reading metadata and observation."""

    @pytest.mark.unit
    @pytest.mark.tools
    def test_observation_source(self):
        """Verify observation source is correctly set."""
        html_response = '<html><body><p>Test</p></body></html>'

        with patch("httpx.Client") as mock_client:
            mock_response = MagicMock()
            mock_response.text = html_response
            mock_response.raise_for_status = MagicMock()

            mock_instance = MagicMock()
            mock_instance.get.return_value = mock_response
            mock_client.return_value.__enter__ = MagicMock(return_value=mock_instance)
            mock_client.return_value.__exit__ = MagicMock(return_value=False)

            result = _read_url("https://example.com")

            from funnel_canary.provenance import ObservationType

            assert result.observation.source_type == ObservationType.TOOL_RETURN
            assert result.observation.source_id == "read_url"

    @pytest.mark.unit
    @pytest.mark.tools
    def test_metadata_contains_url(self):
        """Verify metadata contains the URL."""
        html_response = '<html><body><p>Test</p></body></html>'

        with patch("httpx.Client") as mock_client:
            mock_response = MagicMock()
            mock_response.text = html_response
            mock_response.raise_for_status = MagicMock()

            mock_instance = MagicMock()
            mock_instance.get.return_value = mock_response
            mock_client.return_value.__enter__ = MagicMock(return_value=mock_instance)
            mock_client.return_value.__exit__ = MagicMock(return_value=False)

            result = _read_url("https://test.example.com/page")

            assert result.observation.metadata["url"] == "https://test.example.com/page"

    @pytest.mark.unit
    @pytest.mark.tools
    def test_metadata_contains_content_length(self):
        """Verify metadata contains content length."""
        html_response = '<html><body><p>Some text here</p></body></html>'

        with patch("httpx.Client") as mock_client:
            mock_response = MagicMock()
            mock_response.text = html_response
            mock_response.raise_for_status = MagicMock()

            mock_instance = MagicMock()
            mock_instance.get.return_value = mock_response
            mock_client.return_value.__enter__ = MagicMock(return_value=mock_instance)
            mock_client.return_value.__exit__ = MagicMock(return_value=False)

            result = _read_url("https://example.com")

            assert "content_length" in result.observation.metadata
            assert result.observation.metadata["content_length"] > 0

    @pytest.mark.unit
    @pytest.mark.tools
    def test_observation_scope(self):
        """Verify observation scope contains URL."""
        html_response = '<html><body><p>Test</p></body></html>'

        with patch("httpx.Client") as mock_client:
            mock_response = MagicMock()
            mock_response.text = html_response
            mock_response.raise_for_status = MagicMock()

            mock_instance = MagicMock()
            mock_instance.get.return_value = mock_response
            mock_client.return_value.__enter__ = MagicMock(return_value=mock_instance)
            mock_client.return_value.__exit__ = MagicMock(return_value=False)

            result = _read_url("https://example.com/test")

            assert "url:" in result.observation.scope
            assert "https://example.com/test" in result.observation.scope

    @pytest.mark.unit
    @pytest.mark.tools
    def test_successful_confidence(self):
        """Verify confidence for successful extraction."""
        html_response = '<html><body><p>Content here</p></body></html>'

        with patch("httpx.Client") as mock_client:
            mock_response = MagicMock()
            mock_response.text = html_response
            mock_response.raise_for_status = MagicMock()

            mock_instance = MagicMock()
            mock_instance.get.return_value = mock_response
            mock_client.return_value.__enter__ = MagicMock(return_value=mock_instance)
            mock_client.return_value.__exit__ = MagicMock(return_value=False)

            result = _read_url("https://example.com")

            assert result.observation.confidence == 1.0
