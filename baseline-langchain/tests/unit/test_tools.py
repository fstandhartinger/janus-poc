"""Unit tests for LangChain tool metadata."""

from janus_baseline_langchain.tools import image_generation_tool, text_to_speech_tool, web_search_tool


def test_image_tool_description() -> None:
    assert "image" in image_generation_tool.description.lower()


def test_tts_tool_description() -> None:
    assert "speech" in text_to_speech_tool.description.lower()


def test_web_search_tool_description() -> None:
    assert web_search_tool is not None
    assert "search" in web_search_tool.description.lower()
