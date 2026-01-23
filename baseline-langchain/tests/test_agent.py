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
        "web_search",
        "code_execution",
    }.issubset(tool_names)
