"""Unit tests for tool registration and discovery."""

from janus_baseline_agent_cli.config import Settings
from janus_baseline_agent_cli.tools import get_registered_tools


def test_default_tools_registered() -> None:
    """Default tools are available."""
    tools = get_registered_tools()
    assert "web_search" in tools
    assert "code_execution" in tools


def test_tool_schema_valid() -> None:
    """Tool schemas are valid JSON Schema."""
    tools = get_registered_tools()
    for tool in tools.values():
        assert "name" in tool
        assert "description" in tool
        assert "parameters" in tool
        assert tool["parameters"].get("type") == "object"


def test_disable_tools() -> None:
    """Tools can be disabled via config."""
    settings = Settings(enable_web_search=False)
    tools = get_registered_tools(settings)
    assert "web_search" not in tools


def test_memory_tool_excluded_by_default() -> None:
    tools = get_registered_tools()
    assert "investigate_memory" not in tools


def test_memory_tool_included_when_enabled() -> None:
    tools = get_registered_tools(include_memory_tool=True)
    assert "investigate_memory" in tools
