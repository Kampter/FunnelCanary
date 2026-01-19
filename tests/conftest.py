"""Shared pytest fixtures for FunnelCanary tests."""

import os
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from funnel_canary.provenance import Observation, ObservationType, ProvenanceRegistry
from funnel_canary.tools.base import ToolResult


# =============================================================================
# Path fixtures
# =============================================================================


@pytest.fixture
def temp_dir():
    """Create a temporary directory for test files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def sample_file(temp_dir):
    """Create a sample text file."""
    file_path = temp_dir / "sample.txt"
    file_path.write_text("Hello, World!\nThis is a test file.\n")
    return file_path


@pytest.fixture
def sample_python_file(temp_dir):
    """Create a sample Python file."""
    file_path = temp_dir / "sample.py"
    file_path.write_text('print("Hello from Python")\n')
    return file_path


@pytest.fixture
def large_file(temp_dir):
    """Create a file larger than 100KB."""
    file_path = temp_dir / "large.txt"
    file_path.write_bytes(b"x" * 100_001)  # Just over 100KB
    return file_path


@pytest.fixture
def exact_100kb_file(temp_dir):
    """Create a file exactly 100KB."""
    file_path = temp_dir / "exact_100kb.txt"
    file_path.write_bytes(b"x" * 100_000)
    return file_path


@pytest.fixture
def binary_file(temp_dir):
    """Create a binary file with non-UTF8 content."""
    file_path = temp_dir / "binary.bin"
    file_path.write_bytes(bytes(range(256)))
    return file_path


@pytest.fixture
def utf8_chinese_file(temp_dir):
    """Create a file with UTF-8 Chinese content."""
    file_path = temp_dir / "chinese.txt"
    file_path.write_text("这是中文内容\n测试UTF-8编码\n", encoding="utf-8")
    return file_path


@pytest.fixture
def empty_file(temp_dir):
    """Create an empty file."""
    file_path = temp_dir / "empty.txt"
    file_path.touch()
    return file_path


@pytest.fixture
def no_permission_file(temp_dir):
    """Create a file with no read permissions."""
    file_path = temp_dir / "no_permission.txt"
    file_path.write_text("secret content")
    file_path.chmod(0o000)
    yield file_path
    # Restore permissions for cleanup
    file_path.chmod(0o644)


# =============================================================================
# Directory fixtures for Glob tests
# =============================================================================


@pytest.fixture
def structured_dir(temp_dir):
    """Create a structured directory for glob testing."""
    # Create directories
    (temp_dir / "src").mkdir()
    (temp_dir / "src" / "module").mkdir()
    (temp_dir / "tests").mkdir()
    (temp_dir / "docs").mkdir()

    # Create Python files
    (temp_dir / "main.py").write_text("# main")
    (temp_dir / "src" / "app.py").write_text("# app")
    (temp_dir / "src" / "utils.py").write_text("# utils")
    (temp_dir / "src" / "module" / "core.py").write_text("# core")
    (temp_dir / "tests" / "test_main.py").write_text("# test main")
    (temp_dir / "tests" / "test_app.py").write_text("# test app")

    # Create markdown files
    (temp_dir / "README.md").write_text("# README")
    (temp_dir / "docs" / "guide.md").write_text("# Guide")

    return temp_dir


@pytest.fixture
def many_files_dir(temp_dir):
    """Create a directory with more than 100 files."""
    for i in range(150):
        (temp_dir / f"file_{i:03d}.txt").write_text(f"content {i}")
    return temp_dir


# =============================================================================
# Provenance fixtures
# =============================================================================


@pytest.fixture
def provenance_registry():
    """Create a fresh ProvenanceRegistry."""
    return ProvenanceRegistry()


@pytest.fixture
def observation_tool_return():
    """Create a tool return observation."""
    return Observation(
        content="Search result: Python is a programming language",
        source_type=ObservationType.TOOL_RETURN,
        source_id="web_search",
        confidence=1.0,
        ttl_seconds=3600,
        scope="search:python",
    )


@pytest.fixture
def observation_user_input():
    """Create a user input observation."""
    return Observation(
        content="I want to learn about Python",
        source_type=ObservationType.USER_INPUT,
        source_id="user",
        confidence=0.8,
        scope="problem_statement",
    )


@pytest.fixture
def observation_expired():
    """Create an expired observation."""
    from datetime import datetime, timedelta

    obs = Observation(
        content="Old data",
        source_type=ObservationType.TOOL_RETURN,
        source_id="web_search",
        confidence=1.0,
        ttl_seconds=1,  # 1 second TTL
        scope="search:old",
    )
    # Backdate the timestamp
    obs.timestamp = datetime.now() - timedelta(seconds=10)
    return obs


# =============================================================================
# Mock fixtures
# =============================================================================


@pytest.fixture
def mock_httpx_client():
    """Mock httpx client for web tests."""
    with patch("httpx.Client") as mock:
        client_instance = MagicMock()
        mock.return_value.__enter__ = MagicMock(return_value=client_instance)
        mock.return_value.__exit__ = MagicMock(return_value=False)
        yield client_instance


@pytest.fixture
def mock_successful_search_response():
    """Mock a successful search response."""
    html = '''
    <html>
    <body>
    <a class="result__a" href="#">Python Tutorial</a>
    <a class="result__snippet">Learn Python programming from scratch</a>
    <a class="result__url">https://example.com/python</a>
    </body>
    </html>
    '''
    response = MagicMock()
    response.text = html
    response.status_code = 200
    response.raise_for_status = MagicMock()
    return response


@pytest.fixture
def mock_empty_search_response():
    """Mock an empty search response."""
    html = "<html><body></body></html>"
    response = MagicMock()
    response.text = html
    response.status_code = 200
    response.raise_for_status = MagicMock()
    return response


# =============================================================================
# Agent fixtures
# =============================================================================


@pytest.fixture
def mock_openai_client():
    """Mock OpenAI client for agent tests."""
    with patch("funnel_canary.agent.OpenAI") as mock:
        client_instance = MagicMock()
        mock.return_value = client_instance
        yield client_instance


@pytest.fixture
def mock_config():
    """Mock configuration for agent tests."""
    from funnel_canary.config import Config

    return Config(
        api_key="test-api-key",
        base_url="https://api.test.com/v1",
        model_name="gpt-4-test",
    )


# =============================================================================
# Helper functions
# =============================================================================


def assert_tool_result_success(result: ToolResult) -> None:
    """Assert that a tool result is successful."""
    assert result.success is True
    assert result.error_message is None
    assert result.content is not None
    assert result.observation is not None


def assert_tool_result_failure(result: ToolResult, expected_message: str = None) -> None:
    """Assert that a tool result is a failure."""
    assert result.success is False
    assert result.error_message is not None
    if expected_message:
        assert expected_message in result.error_message


# Make helpers available as fixtures
@pytest.fixture
def check_success():
    """Fixture to access assert_tool_result_success helper."""
    return assert_tool_result_success


@pytest.fixture
def check_failure():
    """Fixture to access assert_tool_result_failure helper."""
    return assert_tool_result_failure
