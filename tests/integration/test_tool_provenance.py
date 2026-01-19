"""Integration tests for tool results and provenance tracking.

Tests the flow of tool results to the provenance system.
"""

from unittest.mock import MagicMock, patch

import pytest

from funnel_canary.provenance import ObservationType, ProvenanceRegistry
from funnel_canary.tools import ToolRegistry, create_default_registry


class TestToolProvenanceIntegration:
    """Test tool results integrate with provenance system."""

    @pytest.mark.integration
    def test_tool_registry_creates_observations(self):
        """Tool execution should create observations."""
        registry = create_default_registry()
        provenance = ProvenanceRegistry()

        # Execute a tool
        result = registry.execute("python_exec", {"code": "print(1+1)"})

        # Result should contain an observation
        assert result.observation is not None
        assert result.observation.source_type == ObservationType.TOOL_RETURN
        assert result.observation.source_id == "python_exec"

        # Observation can be added to provenance registry
        provenance.add_observation(result.observation)
        assert provenance.get_observation_count() == 1

    @pytest.mark.integration
    def test_multiple_tool_executions_tracked(self):
        """Multiple tool executions create distinct observations."""
        registry = create_default_registry()
        provenance = ProvenanceRegistry()

        # Execute multiple tools
        result1 = registry.execute("python_exec", {"code": "print(1)"})
        result2 = registry.execute("python_exec", {"code": "print(2)"})

        provenance.add_observation(result1.observation)
        provenance.add_observation(result2.observation)

        assert provenance.get_observation_count() == 2
        # Should have distinct IDs
        assert result1.observation.id != result2.observation.id

    @pytest.mark.integration
    def test_tool_error_creates_low_confidence_observation(self):
        """Tool errors should create observations with 0 confidence."""
        registry = create_default_registry()

        # Execute a tool that will fail
        result = registry.execute("Read", {"file_path": "/nonexistent/file.txt"})

        assert result.success is False
        assert result.observation is not None
        assert result.observation.confidence == 0.0

    @pytest.mark.integration
    def test_tool_ttl_propagates_to_observation(self):
        """Tool TTL configuration should propagate to observations."""
        # Web search has a 1-hour TTL
        html_response = '<html><body><a class="result__a">Test</a><a class="result__snippet">Test</a></body></html>'

        with patch("httpx.Client") as mock_client:
            mock_response = MagicMock()
            mock_response.text = html_response
            mock_response.raise_for_status = MagicMock()

            mock_instance = MagicMock()
            mock_instance.post.return_value = mock_response
            mock_client.return_value.__enter__ = MagicMock(return_value=mock_instance)
            mock_client.return_value.__exit__ = MagicMock(return_value=False)

            registry = create_default_registry()
            result = registry.execute("web_search", {"query": "test"})

            assert result.observation.ttl_seconds == 3600  # 1 hour


class TestToolRegistryCategories:
    """Test tool registry organization and categories."""

    @pytest.mark.integration
    def test_registry_has_all_tool_categories(self):
        """Registry should include tools from all categories."""
        registry = create_default_registry()

        all_tools = registry.get_all()
        tool_names = [t.name for t in all_tools]

        # Check for tools from each category
        assert "web_search" in tool_names  # web
        assert "read_url" in tool_names    # web
        assert "python_exec" in tool_names  # compute
        assert "Bash" in tool_names         # compute
        assert "Read" in tool_names         # filesystem
        assert "Glob" in tool_names         # filesystem
        assert "ask_user" in tool_names     # interaction

    @pytest.mark.integration
    def test_registry_filters_by_skill(self):
        """Registry should filter tools by skill binding."""
        registry = create_default_registry()

        # Get tools for research skill
        research_tools = registry.get_for_skill(["web_search", "read_url"])
        tool_names = [t.name for t in research_tools]

        assert "web_search" in tool_names
        assert "read_url" in tool_names

    @pytest.mark.integration
    def test_tool_schema_generation(self):
        """Tool registry should generate valid OpenAI schema."""
        registry = create_default_registry()
        tools = registry.get_all()

        schema = registry.to_openai_schema(tools)

        assert isinstance(schema, list)
        for tool_schema in schema:
            assert "type" in tool_schema
            assert tool_schema["type"] == "function"
            assert "function" in tool_schema
            assert "name" in tool_schema["function"]
            assert "description" in tool_schema["function"]
            assert "parameters" in tool_schema["function"]


class TestToolProvenanceFlow:
    """Test the complete flow from tool to provenance."""

    @pytest.mark.integration
    def test_filesystem_tools_flow(self, temp_dir):
        """Test filesystem tools create proper observations."""
        registry = create_default_registry()
        provenance = ProvenanceRegistry()

        # Create test file
        test_file = temp_dir / "test.py"
        test_file.write_text("print('hello')")

        # Use Glob to find file
        glob_result = registry.execute("Glob", {
            "pattern": "*.py",
            "path": str(temp_dir),
        })
        provenance.add_observation(glob_result.observation)

        # Use Read to read file
        read_result = registry.execute("Read", {
            "file_path": str(test_file),
        })
        provenance.add_observation(read_result.observation)

        assert provenance.get_observation_count() == 2

        # Both should have high confidence
        valid_obs = provenance.get_valid_observations(min_confidence=0.9)
        assert len(valid_obs) == 2

    @pytest.mark.integration
    def test_compute_tool_flow(self):
        """Test compute tools create proper observations."""
        registry = create_default_registry()
        provenance = ProvenanceRegistry()

        # Simple Python execution that doesn't require imports
        python_result = registry.execute("python_exec", {
            "code": "print(4 * 4)",
        })
        if python_result.observation:
            provenance.add_observation(python_result.observation)

        # Bash execution
        bash_result = registry.execute("Bash", {
            "command": "echo test",
        })
        if bash_result.observation:
            provenance.add_observation(bash_result.observation)

        assert provenance.get_observation_count() == 2

        # Verify observations exist
        obs_bash = provenance.get_observations_by_source("Bash")
        assert len(obs_bash) == 1
        assert obs_bash[0].confidence == 0.9  # Bash has 0.9 confidence
