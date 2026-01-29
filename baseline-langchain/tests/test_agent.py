"""Tests for the LangChain agent configuration."""

from langchain.agents import AgentExecutor

from janus_baseline_langchain.agent import create_agent
from janus_baseline_langchain.config import Settings


def test_create_agent_includes_tools() -> None:
    settings = Settings(
        openai_api_key="test-key",
        chutes_api_key="test-key",
        tavily_api_key="test-key",
    )
    agent = create_agent(settings)
    assert isinstance(agent, AgentExecutor)
    tool_names = {tool.name for tool in agent.tools}
    assert {
        "image_generation",
        "text_to_speech",
        "music_generation",
        "audio_generation",
        "video_generation",
        "web_search",
        "deep_research",
        "code_execution",
        "clone_repository",
        "list_repository_files",
        "read_repository_file",
        "write_file",
        "read_file",
        "create_directory",
    }.issubset(tool_names)


def test_create_agent_memory_tool_toggle() -> None:
    settings = Settings(
        openai_api_key="test-key",
        chutes_api_key="test-key",
        tavily_api_key="test-key",
        enable_memory_feature=True,
    )

    agent = create_agent(settings)
    tool_names = {tool.name for tool in agent.tools}
    assert "investigate_memory" not in tool_names

    agent = create_agent(
        settings,
        user_id="user-1",
        enable_memory=True,
        has_memory_context=True,
    )
    tool_names = {tool.name for tool in agent.tools}
    assert "investigate_memory" in tool_names
