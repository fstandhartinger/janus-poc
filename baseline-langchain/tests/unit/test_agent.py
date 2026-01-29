"""Unit tests for agent setup."""

from janus_baseline_langchain.agent import SYSTEM_PROMPT, create_agent
from janus_baseline_langchain.config import Settings


def test_system_prompt_includes_tools() -> None:
    prompt = SYSTEM_PROMPT.lower()
    assert "image" in prompt
    assert "speech" in prompt
    assert "search" in prompt


def test_create_agent_with_tools() -> None:
    settings = Settings(use_model_router=False)
    agent = create_agent(settings)
    tool_names = {tool.name for tool in agent.tools}
    assert "image_generation" in tool_names
    assert "text_to_speech" in tool_names
    assert "web_search" in tool_names
